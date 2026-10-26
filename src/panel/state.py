from __future__ import annotations

from collections.abc import Iterable

from discord import Guild

from src.bot_state import get_bot, run_on_bot_loop
from src.harpi_lib.harpi_bot import HarpiBot
from src.panel import serialization
from src.panel.schemas import (
    BotStatus,
    Channel,
    Connection,
    Directory,
    Guild as GuildModel,
    PlaybackStatus,
    Presence,
    StatusSnapshot,
)
from src.storage import get_registry
from src.storage.registry import (
    Actor,
    ConnectionAction,
    Place,
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


async def _collect_guild_ids(bot: HarpiBot) -> set[int]:
    return {guild.id async for guild in bot.fetch_guilds(limit=None)}


async def bot_guild_ids() -> set[int]:
    """Every guild the bot is in, fetched so no guild count is capped."""
    return await run_on_bot_loop(_collect_guild_ids(get_bot()))


def list_voice_channels(guild_id: int) -> list[Channel]:
    guild = get_bot().get_guild(guild_id)
    if guild is None:
        return []
    return [
        serialization.channel_data(channel) for channel in guild.voice_channels
    ]


def directory_snapshot(guild_id: int | None) -> Directory:
    """The guilds the bot is in, plus the voice channels of *guild_id*.

    Built from the bot's cached guild objects, so no Discord call happens.
    """
    bot = get_bot()
    resolved = resolve_guild_id(guild_id)
    return Directory(
        guild_id=serialization.optional_snowflake(resolved),
        guilds=[serialization.guild_data(guild) for guild in bot.guilds],
        channels=([] if resolved is None else list_voice_channels(resolved)),
    )


def place_of(guild_id: int, channel_id: int | None) -> Place | None:
    guild = get_bot().get_guild(guild_id)
    if guild is None:
        return None
    channel_name = next(
        (
            channel.name
            for channel in guild.voice_channels
            if channel.id == channel_id
        ),
        None,
    )
    return Place(
        guild_id=str(guild_id),
        guild_name=guild.name,
        channel_id=None if channel_id is None else str(channel_id),
        channel_name=channel_name,
    )


async def sign_in(actor: Actor) -> None:
    registry = get_registry()
    if registry is not None:
        await registry.sign_in(actor)


async def record_user_guilds(actor: Actor, guild_ids: Iterable[int]) -> None:
    registry = get_registry()
    if registry is not None:
        await registry.record_user_guilds(
            actor, [str(guild_id) for guild_id in guild_ids]
        )


async def user_guild_ids(user_id: str) -> frozenset[int]:
    registry = get_registry()
    if registry is None:
        return frozenset()
    return frozenset(
        int(guild_id) for guild_id in await registry.user_guild_ids(user_id)
    )


async def login_epoch(user_id: str) -> int | None:
    registry = get_registry()
    if registry is None:
        return None
    return await registry.login_epoch(user_id)


async def increment_login_epoch(user_id: str) -> int | None:
    registry = get_registry()
    if registry is None:
        return None
    return await registry.increment_login_epoch(user_id)


async def select(
    actor: Actor | None, guild_id: int, channel_id: int | None
) -> None:
    registry = get_registry()
    if registry is None or actor is None:
        return
    place = place_of(guild_id, channel_id)
    if place is not None:
        await registry.select(actor, place)


async def record_connection(
    actor: Actor | None,
    guild_id: int,
    channel_id: int | None,
    action: ConnectionAction,
) -> None:
    registry = get_registry()
    if registry is None:
        return
    place = place_of(guild_id, channel_id)
    if place is not None:
        await registry.record_connection(actor, place, action)


async def leave(user_id: str) -> None:
    registry = get_registry()
    if registry is not None:
        await registry.leave(user_id)


async def presence(guild_id: int | None, actor: Actor | None) -> Presence:
    registry = get_registry()
    if registry is None:
        return Presence(
            guild_id=serialization.optional_snowflake(guild_id),
            viewers=[],
            last_connection=None,
        )
    resolved = resolve_guild_id(guild_id)
    if resolved is None:
        return Presence(guild_id=None, viewers=[], last_connection=None)
    if actor is not None:
        place = place_of(resolved, None)
        if place is not None:
            await registry.touch(actor, place)
    viewers = await registry.viewers(str(resolved))
    last = await registry.last_connection(str(resolved))
    return serialization.presence_data(resolved, viewers, last)


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
