from __future__ import annotations

from discord import Guild

from src.bot_state import get_bot, run_on_bot_loop
from src.harpi_lib.harpi_bot import HarpiBot
from src.panel import serialization
from src.panel.schemas import (
    BotStatus,
    Channel,
    Connection,
    Guild as GuildModel,
    PlaybackStatus,
    StatusSnapshot,
)


def bot_connected() -> bool:
    bot = get_bot()
    return bool(bot.is_ready() and not bot.is_closed())


def guild_visible(guild_id: int) -> bool:
    return get_bot().get_guild(guild_id) is not None


def session_exists(guild_id: int) -> bool:
    return get_bot().sessions.get(guild_id) is not None


async def _collect_guilds(bot: HarpiBot) -> list[Guild]:
    return [guild async for guild in bot.fetch_guilds(limit=150)]


async def list_guilds() -> list[GuildModel]:
    guilds = await run_on_bot_loop(_collect_guilds(get_bot()))
    return [serialization.guild_data(guild) for guild in guilds]


def list_voice_channels(guild_id: int) -> list[Channel]:
    guild = get_bot().get_guild(guild_id)
    if guild is None:
        return []
    return [
        serialization.channel_data(channel) for channel in guild.voice_channels
    ]


async def guild_status(guild_id: int | None) -> PlaybackStatus | None:
    if guild_id is None:
        return None
    session_obj = get_bot().sessions.get(guild_id)
    if session_obj is None:
        return None
    status = await run_on_bot_loop(session_obj.sample_status())
    if status is None:
        return None
    return serialization.status_data(status)


async def status_snapshot(guild_id: int | None) -> StatusSnapshot:
    if guild_id is not None and not guild_visible(guild_id):
        guild_id = None
    playback = await guild_status(guild_id)
    return StatusSnapshot(
        bot=BotStatus(online=bot_connected()),
        guild_id=serialization.optional_snowflake(guild_id),
        connection=Connection(
            connected=bool(playback and playback.connected),
            channel_id=playback.channel_id if playback else None,
        ),
        playback=playback,
    )
