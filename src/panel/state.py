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


def _occupied_channel_id(guild: Guild) -> int | None:
    voice_client = getattr(guild, "voice_client", None)
    if voice_client is None or not voice_client.is_connected():
        return None
    return getattr(getattr(voice_client, "channel", None), "id", None)


def active_voice() -> tuple[int, int] | None:
    """The guild and channel the bot physically occupies, if any."""
    for guild in get_bot().guilds:
        channel_id = _occupied_channel_id(guild)
        if channel_id is not None:
            return guild.id, channel_id
    return None


def voice_active(guild_id: int) -> bool:
    guild = get_bot().get_guild(guild_id)
    return guild is not None and _occupied_channel_id(guild) is not None


def resolve_guild_id(guild_id: int | None) -> int | None:
    """The guild a snapshot should describe: the selection, else the voice one."""
    if guild_id is not None and guild_visible(guild_id):
        return guild_id
    active = active_voice()
    return active[0] if active is not None else None


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
    resolved = resolve_guild_id(guild_id)
    playback = await guild_status(resolved)

    if playback is not None:
        connected = playback.connected
        channel_id = playback.channel_id
    else:
        connected = False
        channel_id = None

    if not connected:
        active = active_voice()
        if active is not None and active[0] == resolved:
            connected = True
            channel_id = serialization.optional_snowflake(active[1])

    return StatusSnapshot(
        bot=BotStatus(online=bot_connected()),
        guild_id=serialization.optional_snowflake(resolved),
        connection=Connection(connected=connected, channel_id=channel_id),
        playback=playback,
    )
