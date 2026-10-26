from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger
from quart import Quart, Response, request, send_from_directory, session
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

from src.config import Settings
from src.discord_bot import run_bot_in_background
from src.panel import login, state
from src.storage import clear_registry, get_registry, init_registry
from src.storage.database import Database
from src.storage.registry import SqliteRegistry

logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

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


app.config["TEMPLATES_AUTO_RELOAD"] = True
app.url_map.merge_slashes = False
configure_panel_session(Settings.from_env())

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
    500: "internal_error",
}


def _is_api_path() -> bool:
    path = request.path
    return path == "/api" or path.startswith("/api/")


@app.before_request
def guard_trusted_host():
    if host_is_trusted(request.host, app.config["TRUSTED_HOSTS"]):
        return None
    if _is_api_path():
        return error_response("bad_request", "Untrusted host", 400)
    return Response("Bad Request", status=400)


async def _login_is_current() -> bool:
    if session.get("authenticated") is not True:
        return False
    user_id = session.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        return False
    if not login.within_lifetime(session.get(login.ISSUED_AT_KEY)):
        return False
    epoch = await state.login_epoch(user_id)
    stored_epoch = session.get(login.LOGIN_EPOCH_KEY)
    return (
        epoch is not None
        and isinstance(stored_epoch, int)
        and not isinstance(stored_epoch, bool)
        and stored_epoch == epoch
    )


@app.before_request
async def guard_api():
    if not _is_api_path():
        return None
    if (request.method, request.path) in PUBLIC_API_ROUTES:
        return None
    if await _login_is_current():
        return None
    return error_response("unauthorized", "Authentication required", 401)


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
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


@app.before_serving
async def startup():
    global _database
    settings = Settings.from_env()
    if get_registry() is None:
        try:
            _database = Database(settings.db_path)
            await _database.open()
            init_registry(SqliteRegistry(_database))
            logger.info(f"Panel storage ready at {settings.db_path}")
        except Exception as e:
            _database = None
            logger.opt(exception=True).error(f"Panel storage unavailable: {e}")
    try:
        run_bot_in_background(settings)
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


@app.after_serving
async def shutdown():
    global _database
    database = _database
    _database = None
    clear_registry()
    if database is not None:
        await database.close()


asgi_app = app
