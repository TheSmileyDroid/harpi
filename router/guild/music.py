import logging
from typing import cast

from flask import Blueprint, render_template
from flask.globals import session

from src.cogs.music import MusicCog
from src.discord_bot import get_bot_instance

bp = Blueprint("music", __name__)


@bp.route("/music")
def music():
    guild_id: int | None = session.get("guild_id")
    bot = get_bot_instance()
    assert bot, "Bot does not exist!"
    guild = bot.get_guild(guild_id) if guild_id else None
    if not guild:
        logging.info("Guild not found!")
    return render_template("pages/music.html", guild=guild)


@bp.route("/components/music/playing")
def playing_music():
    guild_id: int | None = session.get("guild_id")
    bot = get_bot_instance()
    assert bot, "Bot does not exist!"
    guild = bot.get_guild(guild_id) if guild_id else None
    if not guild or not guild_id:
        logging.info("Guild not found!")
        return "Guild not found!"
    music_cog: MusicCog = cast(MusicCog, bot.cogs["MusicCog"])
    current_music = music_cog.current_music.get(guild_id)
    queue = music_cog.music_queue.get(guild_id)

    return render_template(
        "components/music/playing.html",
        current_music=current_music,
        queue=queue,
    )
