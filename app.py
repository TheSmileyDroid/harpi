from __future__ import annotations

import os
import sys

import psutil
from loguru import logger
from pydantic import BaseModel
from quart import Quart, request
from quart_cors import cors
from quart_schema import QuartSchema, validate_response

from src.api import html_routes, htmx_routes, music
from src.discord_bot import run_bot_in_background

logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app = cors(app, allow_origin="*")

QuartSchema(app)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.environ.get("SECRET_KEY")


@app.template_filter()
def format_duration(seconds: int) -> str:
    """Format seconds to M:SS or H:MM:SS."""
    if not seconds or seconds < 0:
        return "0:00"
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


@app.template_filter()
def format_bytes(value: int) -> str:
    """Format bytes to human readable."""
    if not value:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    v = float(value)
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return f"{v:.1f} {units[i]}"


class ServerStatusModel(BaseModel):
    cpu: float
    memory_total: int
    memory_available: int
    memory_percent: float
    memory_used: int
    memory_free: int


@app.route("/api/serverstatus")
@validate_response(ServerStatusModel)
def api_server_status():
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    return ServerStatusModel(
        cpu=cpu_percent,
        memory_total=mem.total,
        memory_available=mem.available,
        memory_percent=mem.percent,
        memory_used=mem.used,
        memory_free=mem.free,
    )


app.register_blueprint(html_routes.bp)
app.register_blueprint(htmx_routes.bp)
app.register_blueprint(music.bp)


@app.before_request
async def throttle_music_actions():
    """Throttle mutating music endpoints to protect the voice path."""
    from src.api.rate_limit import MUSIC_ACTION_LIMITER

    if request.method not in {"POST", "DELETE"}:
        return None
    if not request.path.startswith("/api/music/"):
        return None
    if MUSIC_ACTION_LIMITER.allow(request.remote_addr or "unknown"):
        return None
    return "Too many requests", 429, {"Retry-After": "1"}


@app.before_serving
async def startup():
    try:
        run_bot_in_background()
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


asgi_app = app
