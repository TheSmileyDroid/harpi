"""O executável do bot."""

from __future__ import annotations

import os
import sys

import psutil
from dotenv import load_dotenv
from loguru import logger
from quart import Quart, jsonify
from quart_cors import cors

from src.api import guild, music
from src.discord_bot import run_bot_in_background

assert load_dotenv(), "dot env not loaded"
logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app = cors(app, allow_origin="*")

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.environ.get("SECRET_KEY")


@app.route("/api/serverstatus")
def api_serverstatus():
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    return jsonify(
        {
            "cpu": cpu_percent,
            "memory": {
                "total": mem.total,
                "available": mem.available,
                "percent": mem.percent,
                "used": mem.used,
                "free": mem.free,
            },
        }
    )


app.register_blueprint(music.bp)
app.register_blueprint(guild.bp)


@app.before_serving
async def startup():
    try:
        run_bot_in_background()
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.error(f"Failed to start Discord bot: {e}")


asgi_app = app
