from __future__ import annotations

import os
import sys

from loguru import logger
from quart import Quart
from quart_cors import cors

from pages.index import bp as index_bp
from pages.music import bp as music_bp
from pages.status import bp as status_bp

from src.discord_bot import run_bot_in_background

logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app = cors(app, allow_origin="*")

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


@app.template_filter(name="round")
def format_round(value: str, precision: int = 1) -> str:
    """Format float to a given precision."""
    return f"{str(round(float(value), precision))}"


for _bp in (index_bp, music_bp, status_bp):
    app.register_blueprint(_bp)


@app.before_serving
async def startup():
    try:
        run_bot_in_background()
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


asgi_app = app
