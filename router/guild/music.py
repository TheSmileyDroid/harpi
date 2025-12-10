import logging
from typing import cast

from discord import VoiceClient
from flask import Blueprint, render_template
from flask.globals import session

from src.cogs.music import MusicCog
from src.discord_bot import get_bot_instance
from src.models.guild import AudioSourceTrackedProtocol

bp = Blueprint("music", __name__)


def get_music_status():
    guild_id: int | None = session.get("guild_id")
    bot = get_bot_instance()
    assert bot, "Bot does not exist!"
    guild = bot.get_guild(guild_id) if guild_id else None
    if not guild or not guild_id:
        logging.info("Guild not found!")
    music_cog: MusicCog = cast(MusicCog, bot.cogs["MusicCog"])
    current_music = music_cog.current_music.get(guild_id) if guild_id else None
    queue = music_cog.music_queue.get(guild_id) if guild_id else None
    progress = 0
    voice_client = None

    if (
        (
            voice_client := cast(
                VoiceClient, guild.voice_client if guild else None
            )
        )
        and (source := voice_client.source)  # type: ignore Unknown attribute
    ):
        source = cast(AudioSourceTrackedProtocol, cast(object, source))
        progress = source.progress

    return {
        "current_music": current_music,
        "progress": round(progress),
        "queue": queue,
    }


@bp.route("/music")
def music():
    guild_id: int | None = session.get("guild_id")
    bot = get_bot_instance()
    assert bot, "Bot does not exist!"
    guild = bot.get_guild(guild_id) if guild_id else None
    if not guild:
        logging.info("Guild not found!")
    return render_template(
        "pages/music.html", guild=guild, **get_music_status()
    )


@bp.route("/components/music/playing")
def playing_music():
    return render_template(
        "components/music/playing.html", **get_music_status()
    )
