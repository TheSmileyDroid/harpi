from __future__ import annotations

import asyncio
import base64
import hashlib
import re
from pathlib import Path

from loguru import logger
from quart import (
    Quart,
    Response,
    g,
    has_request_context,
    request,
    send_from_directory,
    session,
)
from quart_schema import QuartSchema
from werkzeug.exceptions import HTTPException
from werkzeug.wsgi import host_is_trusted

from pages.api import bp as api_bp
from pages.api import error_response
from pages.auth import CALLBACK_PATH as AUTH_CALLBACK_PATH
from pages.auth import LOGIN_PATH as AUTH_LOGIN_PATH
from pages.auth import LOGOUT_PATH as AUTH_LOGOUT_PATH
from pages.auth import bp as auth_bp
from pages.contract import ContractOpenAPIProvider
from pages.events import bp as events_bp

from src import alerts
from src.config import Settings
from src.discord_bot import run_bot_in_background
from src.logging_setup import configure_logging
from src.panel import backup, disk_pressure, login, retention, state
from src.security_log import alert_for_status, event_for_request, record_event
from src.storage import clear_registry, get_registry, init_registry
from src.storage.database import Database
from src.storage.registry import SqliteRegistry

BOOT_SETTINGS = Settings.from_env()
configure_logging(BOOT_SETTINGS)

WEB_BUILD = Path(__file__).resolve().parent / "web" / "build"

app = Quart(__name__, static_folder=None)


def configure_panel_session(settings: Settings) -> None:
    secure = not settings.insecure_cookies
    app.config.update(
        SESSION_COOKIE_NAME=login.cookie_name(secure=secure),
        SESSION_COOKIE_SECURE=secure,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_PATH="/",
        SESSION_COOKIE_DOMAIN=None,
        PERMANENT_SESSION_LIFETIME=login.SESSION_LIFETIME,
        SESSION_REFRESH_EACH_REQUEST=False,
        TRUSTED_HOSTS=settings.trusted_hosts,
    )
    app.secret_key = settings.secret_key


INLINE_SCRIPT = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script>", re.DOTALL)


def inline_script_hashes(build_dir: Path) -> tuple[str, ...]:
    index = build_dir / "index.html"
    if not index.is_file():
        return ()
    bodies = INLINE_SCRIPT.findall(index.read_text(encoding="utf-8"))
    return tuple(
        "'sha256-"
        + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
        + "'"
        for body in bodies
        if body.strip()
    )


def content_security_policy(build_dir: Path) -> str:
    hashes = inline_script_hashes(build_dir)
    script_src = (
        "'self' " + " ".join(hashes) if hashes else "'self' 'unsafe-inline'"
    )
    return (
        "default-src 'self'; "
        f"script-src {script_src}; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data: https://i.ytimg.com; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )


def build_security_headers(build_dir: Path) -> dict[str, str]:
    return {
        "Strict-Transport-Security": "max-age=31536000",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        ),
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": content_security_policy(build_dir),
    }


DOCUMENTATION_PATHS: frozenset[str] = frozenset({
    "/openapi.json",
    "/docs",
    "/redocs",
    "/scalar",
})

MAX_REQUEST_BODY_BYTES = 64 * 1024


def configure_security(settings: Settings) -> None:
    app.config["PUBLIC_MODE"] = settings.public_mode
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BODY_BYTES
    app.config["SECURITY_HEADERS"] = build_security_headers(WEB_BUILD)


app.config["TEMPLATES_AUTO_RELOAD"] = True
app.url_map.merge_slashes = False
configure_panel_session(BOOT_SETTINGS)
configure_security(BOOT_SETTINGS)

QuartSchema(app, openapi_provider_class=ContractOpenAPIProvider)

PUBLIC_API_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("GET", AUTH_LOGIN_PATH),
    ("GET", AUTH_CALLBACK_PATH),
    ("POST", AUTH_LOGOUT_PATH),
})

API_ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    500: "internal_error",
}


def _is_api_path() -> bool:
    path = request.path
    return path == "/api" or path.startswith("/api/")


@app.before_request
def guard_trusted_host():
    if not has_request_context():
        return None
    if host_is_trusted(request.host, app.config["TRUSTED_HOSTS"]):
        return None
    if _is_api_path():
        return error_response("bad_request", "Untrusted host", 400)
    return Response("Bad Request", status=400)


@app.before_request
def guard_documentation():
    if not has_request_context():
        return None
    if app.config["PUBLIC_MODE"] and request.path in DOCUMENTATION_PATHS:
        return Response("Not Found", status=404)
    return None


@app.after_request
def send_security_headers(response: Response) -> Response:
    response.headers.update(app.config["SECURITY_HEADERS"])
    return response


@app.after_request
def log_security_event(response: Response) -> Response:
    if not has_request_context():
        return response
    event = event_for_request(
        request.method,
        request.path,
        response.status_code,
        response.headers.get("Location"),
    )
    if event is None:
        return response
    user_id = session.get("user_id") or getattr(g, "security_user_id", None)
    record_event(
        event,
        user_id=str(user_id) if user_id else None,
        ip=request.remote_addr,
    )
    return response


@app.after_request
def alert_security_status(response: Response) -> Response:
    if not has_request_context():
        return response
    kind = alert_for_status(response.status_code)
    if kind is not None:
        alerts.notify(
            kind,
            f"{request.method} {request.path} ip={request.remote_addr or '-'}",
        )
    return response


def _session_user_id() -> str | None:
    if session.get("authenticated") is not True:
        return None
    user_id = session.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        return None
    return user_id


def _epochs_match(epoch: object, stored: object) -> bool:
    if not isinstance(epoch, int) or not isinstance(stored, int):
        return False
    if isinstance(stored, bool):
        return False
    return stored == epoch


async def _login_is_current() -> bool:
    user_id = _session_user_id()
    if user_id is None:
        return False
    if not login.within_lifetime(session.get(login.ISSUED_AT_KEY)):
        return False
    epoch = await state.login_epoch(user_id)
    return _epochs_match(epoch, session.get(login.LOGIN_EPOCH_KEY))


@app.before_request
async def guard_api():
    if not has_request_context():
        return None
    if not _is_api_path():
        return None
    g.security_user_id = session.get("user_id")
    if (request.method, request.path) in PUBLIC_API_ROUTES:
        return None
    if await _login_is_current():
        return None
    return error_response("unauthorized", "Authentication required", 401)


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    if not has_request_context():
        return error.get_response()
    if not _is_api_path():
        return error.get_response()
    code = API_ERROR_CODES.get(error.code or 500, "error")
    status = error.code or 500
    message = error.description or "Request failed"
    return error_response(code, message, status)


@app.get("/")
async def panel_index() -> Response:
    return await send_from_directory(WEB_BUILD, "index.html")


@app.get("/<path:filename>")
async def panel_asset(filename: str) -> Response:
    return await send_from_directory(WEB_BUILD, filename)


app.register_blueprint(events_bp)
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)

_database: Database | None = None
_retention_task: asyncio.Task[None] | None = None
_backup_task: asyncio.Task[None] | None = None
_disk_task: asyncio.Task[None] | None = None


@app.before_serving
async def startup():
    global _database, _retention_task, _backup_task, _disk_task
    settings = Settings.from_env()
    alerts.configure_alerts(settings.alert_webhook)
    if get_registry() is None:
        try:
            _database = Database(settings.db_path)
            await _database.open()
            init_registry(SqliteRegistry(_database))
            await state.restrict_user_guilds(settings.guild_allowlist)
            logger.info(f"Panel storage ready at {settings.db_path}")
        except Exception as e:
            _database = None
            logger.opt(exception=True).error(f"Panel storage unavailable: {e}")
    _retention_task = retention.start_daily_purge(settings)
    _backup_task = backup.start_daily_backup(settings)
    _disk_task = disk_pressure.start_disk_watch(settings)
    try:
        run_bot_in_background(settings)
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


@app.after_serving
async def shutdown():
    global _database, _retention_task, _backup_task, _disk_task
    task = _retention_task
    _retention_task = None
    if task is not None:
        await retention.stop_daily_purge(task)
    backup_task = _backup_task
    _backup_task = None
    if backup_task is not None:
        await backup.stop_daily_backup(backup_task)
    disk_task = _disk_task
    _disk_task = None
    if disk_task is not None:
        await disk_pressure.stop_disk_watch(disk_task)
    await alerts.stop_alerts()
    database = _database
    _database = None
    clear_registry()
    if database is not None:
        await database.close()


asgi_app = app
