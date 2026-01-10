"""O executável do bot."""

from __future__ import annotations

import os
import sys

import psutil
from discord.guild import Guild
from dotenv import load_dotenv
from loguru import logger
from quart import Quart, jsonify, render_template, session
from quart_cors import cors

from common.botsync import run_async
from router.guild import music
from src.discord_bot import get_bot_instance, run_bot_in_background

assert load_dotenv(), "dot env not loaded"
logger.remove()
logger.add("spam.log", level="DEBUG")
logger.add(sys.stdout, level="INFO")

app = Quart(__name__)

app = cors(app, allow_origin="*")

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.environ.get("SECRET_KEY")


def _guild_to_dict(guild: Guild):
    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None,
    }


guilds: list[Guild] | None = None


async def _get_guilds() -> list[Guild]:
    global guilds
    if guilds is not None:
        return guilds
    bot = get_bot_instance()
    if not bot:
        return []

    async def load_guild():
        return [guild async for guild in bot.fetch_guilds(limit=150)]

    guilds = run_async(bot, load_guild()) or []
    return guilds


@app.route("/components/guilds")
async def guild():
    guilds = await _get_guilds()
    return await render_template("components/guild_list.html", guilds=guilds)


@app.route("/api/guilds")
async def api_guilds():
    guilds_list = await _get_guilds()
    return jsonify([_guild_to_dict(g) for g in guilds_list])


@app.route("/api/guild/select/<int:guild_id>", methods=["POST"])
async def api_select_guild(guild_id: int):
    bot = get_bot_instance()

    if bot and bot.is_ready():
        guild = bot.get_guild(guild_id)
        if guild:
            session["guild_id"] = guild_id
            return jsonify({"success": True, "guild": _guild_to_dict(guild)})

    return jsonify(
        {"success": False, "error": "Guild not found or bot not ready"}
    ), 404


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


@app.before_serving
async def startup():
    try:
        run_bot_in_background()
        logger.info("Discord bot initialization started")
    except Exception as e:
        logger.error(f"Failed to start Discord bot: {e}")


asgi_app = app
