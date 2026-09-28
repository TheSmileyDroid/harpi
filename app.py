from __future__ import annotations

import sys
from datetime import timedelta

from loguru import logger
from quart import Quart, request, session
from werkzeug.exceptions import HTTPException

from pages.api import bp as api_bp
from pages.api import error_response
from pages.events import bp as events_bp
from pages.index import bp as index_bp
from pages.music import bp as music_bp

from src.config import Settings
from src.discord_bot import run_bot_in_background

logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.secret_key = Settings.from_env().secret_key
app.url_map.merge_slashes = False

PUBLIC_API_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/api/session"),
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


@app.template_filter()
def format_duration(seconds: int) -> str:
    """Format seconds to M:SS or H:MM:SS."""
    if not seconds or seconds < 0:
        return "0:00"
    try:
        total_sec = int(seconds)
    except (TypeError, ValueError):
        return "0:00"
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


app.register_blueprint(index_bp)
app.register_blueprint(music_bp)
app.register_blueprint(events_bp)
app.register_blueprint(api_bp)


@app.before_serving
def startup():
    try:
        run_bot_in_background(Settings.from_env())
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


asgi_app = app
