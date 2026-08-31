from __future__ import annotations

import sys

from loguru import logger
from quart import Quart

from pages.index import bp as index_bp
from pages.music import bp as music_bp

from src.config import Settings
from src.discord_bot import run_bot_in_background

logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = Settings.from_env().secret_key


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


@app.before_serving
def startup():
    try:
        run_bot_in_background(Settings.from_env())
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


asgi_app = app
