"""O executável do bot."""

from __future__ import annotations

import logging
import os

import psutil
from discord.guild import Guild
from dotenv import load_dotenv
from flask import Flask, render_template
from flask.globals import session
from flask.helpers import make_response

from common.botsync import run_async
from router.guild import music
from src.discord_bot import get_bot_instance, run_bot_in_background

assert load_dotenv(), "dot env not loaded"

terminal_logger = logging.StreamHandler()
# noinspection SpellCheckingInspection
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminal_logger)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.environ.get("SECRET_KEY")


@app.route("/")
def index():
    return render_template("base.html")


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
    return render_template("components/guild_list.html", guilds=guilds)


@app.route("/status")
def status():
    """A route to check if the bot is running and ready."""
    status = "Unknown"
    try:
        bot = get_bot_instance()

        if bot and bot.is_ready():
            status = f"Bot is logged in as {bot.user}!"
        else:
            status = "Bot is not connected or has not started yet."
    except Exception as e:
        logging.error(f"Error checking bot status: {e}")
        status = "Error checking bot status."
    return render_template("components/bot_status.html", status=status)


@app.route("/select/guild/<int:guild_id>")
async def select_guild(guild_id: int):
    bot = get_bot_instance()
    guilds = await _get_guilds()

    if bot and bot.is_ready():
        guild = bot.get_guild(guild_id)
        assert guild
        session["guild_id"] = guild_id

    resp = make_response(
        render_template("components/guild_list.html", guilds=guilds)
    )
    resp.headers["HX-Trigger"] = "guild-selected"
    return resp


@app.route("/components/current_guild")
def current_guild():
    guild_id: int | None = session.get("guild_id")
    if not guild_id:
        return render_template("components/current_guild.html", guild=None)

    bot = get_bot_instance()
    if bot and bot.is_ready():
        guild = bot.get_guild(guild_id)
        if guild:
            return render_template(
                "components/current_guild.html", guild=guild
            )

    return render_template("components/current_guild.html", guild=None)


@app.route("/components/serverstatus")
def serverstatus():
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()

    return render_template(
        "components/server_status.html", cpu_percent=cpu_percent, mem=mem
    )


app.register_blueprint(music.bp)

with app.app_context():
    try:
        run_bot_in_background()
        logging.info("Discord bot initialization started")
    except Exception as e:
        logging.error(f"Failed to start Discord bot: {e}")
