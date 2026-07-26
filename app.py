"""O executável do bot."""

from __future__ import annotations

import os
import sys

import psutil
from loguru import logger
from pydantic import BaseModel
from quart import Quart, redirect, url_for
from quart_cors import cors
from quart_schema import QuartSchema, validate_response

from src.api import guild, music, html_routes, htmx_routes
from src.discord_bot import run_bot_in_background

logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app = cors(app, allow_origin="*")

QuartSchema(app)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.environ.get("SECRET_KEY")


# ==========================================================================
# Jinja2 Template Filters
# ==========================================================================


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


@app.template_filter()
def format_percent(value: float, decimals: int = 1) -> str:
    """Format a float as percentage string."""
    return f"{value:.{decimals}f}%"


# ==========================================================================
# API Routes
# ==========================================================================


class ServerStatusModel(BaseModel):
    cpu: float
    memory_total: int
    memory_available: int
    memory_percent: float
    memory_used: int
    memory_free: int


@app.route("/api/serverstatus")
@validate_response(ServerStatusModel)
def api_serverstatus():
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


# ==========================================================================
# HTML / HTMX Routes
# ==========================================================================


@app.route("/")
async def index():
    """Redirect root to dashboard."""
    return redirect(url_for("html_routes.dashboard"))


app.register_blueprint(guild.bp)
app.register_blueprint(music.bp)
app.register_blueprint(html_routes.bp)
app.register_blueprint(htmx_routes.bp)


@app.before_serving
async def startup():
    try:
        run_bot_in_background()
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


asgi_app = app
