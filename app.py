"""O executável do bot."""

from __future__ import annotations
from pydantic import BaseModel

import os
import sys

import psutil
from dotenv import load_dotenv
from loguru import logger
from quart import Quart, jsonify
from quart_cors import cors
from quart_schema import QuartSchema, validate_request, validate_response
from src.api import guild, music, soundboard
from src.discord_bot import run_bot_in_background
from src.harpi_lib.soundboard.websocket import create_socketio_app

assert load_dotenv(), "dot env not loaded"
logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app = cors(app, allow_origin="*")

QuartSchema(app)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.environ.get("SECRET_KEY")


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


app.register_blueprint(music.bp)
app.register_blueprint(guild.bp)
app.register_blueprint(soundboard.bp)


@app.before_serving
async def startup():
    try:
        run_bot_in_background()
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.opt(exception=True).error(f"Failed to start Discord bot: {e}")


asgi_app = app

socketio_app = create_socketio_app()
