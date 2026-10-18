from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from loguru import logger
from quart import Quart, Response, request, send_from_directory, session
from quart_schema import QuartSchema
from werkzeug.exceptions import HTTPException

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
from src.storage import clear_registry, get_registry, init_registry
from src.storage.database import Database
from src.storage.registry import SqliteRegistry

logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

WEB_BUILD = Path(__file__).resolve().parent / "web" / "build"

app = Quart(__name__, static_folder=None)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.secret_key = Settings.from_env().secret_key
app.url_map.merge_slashes = False

QuartSchema(app, openapi_provider_class=ContractOpenAPIProvider)

PUBLIC_API_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("GET", AUTH_LOGIN_PATH),
    ("GET", AUTH_CALLBACK_PATH),
    ("POST", AUTH_LOGOUT_PATH),
})

API_ERROR_CODES: dict[int, str] = {
    404: "not_found",
    405: "method_not_allowed",
    500: "internal_error",
}


def _is_api_path() -> bool:
    path = request.path
    return path == "/api" or path.startswith("/api/")


@app.before_request
def guard_api():
    if not _is_api_path():
        return None
    if (request.method, request.path) in PUBLIC_API_ROUTES:
        return None
    if session.get("authenticated") is True:
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
