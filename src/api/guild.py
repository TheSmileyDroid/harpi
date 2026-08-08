"""Guild API - guild listing, voice channel info, and guild selection.

Thread safety
-------------
The module-level guilds cache is populated and read exclusively from
Quart's event loop (single-threaded async).  Anything that touches
discord.py internals (fetching guilds, connecting to voice) is scheduled
onto the bot's event loop via ``run_on_bot_loop`` and awaited, so no
Quart handler blocks the web server waiting on the bot loop.  No lock is
required for the cache itself (MEDIUM-1 accepted risk - only one event
loop serves HTTP requests).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Guild, VoiceChannel
from loguru import logger
from pydantic import BaseModel
from quart import Blueprint, session
from quart_schema import validate_request, validate_response

from src.api.deps import get_bot, run_on_bot_loop

if TYPE_CHECKING:
    from discord.ext.commands import Bot

bp = Blueprint("guild", __name__)


guilds: list[Guild] | None = None


async def _fetch_guilds(bot: "Bot") -> list[Guild]:
    """Fetch the guilds the bot can see (runs on the bot's event loop)."""
    return [guild async for guild in bot.fetch_guilds(limit=150)]


async def _get_guilds() -> list[Guild]:
    """Load guilds the bot is connected to."""
    global guilds
    if guilds is not None:
        return guilds
    bot = get_bot()
    if not bot:
        return []
    guilds = await run_on_bot_loop(_fetch_guilds(bot)) or []
    return guilds


class ChannelResponse(BaseModel):
    """Voice channel information."""

    id: str
    name: str


def to_channel_response(channel: VoiceChannel) -> ChannelResponse:
    """Convert a VoiceChannel to a ChannelResponse."""
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
    )


class GuildResponse(BaseModel):
    """Discord guild information."""

    id: str
    name: str
    icon: str


def to_guild_response(guild: Guild) -> GuildResponse:
    """Convert a Guild to a GuildResponse."""
    return GuildResponse(
        id=str(guild.id),
        name=guild.name,
        icon=str(guild.icon.url) if guild.icon else "",
    )


@bp.route("/api/guild")
@validate_response(list[GuildResponse])
async def get_guilds() -> list[GuildResponse]:
    guilds_list = await _get_guilds()
    return [to_guild_response(g) for g in guilds_list]


class ChannelsResponse(BaseModel):
    """List of voice channels."""

    channels: list[ChannelResponse]
    current_channel: str | None


@bp.route("/api/guild/<guild_id>/channels")
@validate_response(ChannelsResponse)
async def get_channels(
    guild_id: str,
) -> ChannelsResponse | tuple[ChannelsResponse, int]:
    bot = get_bot()
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return ChannelsResponse(channels=[], current_channel=None), 404

    channel: str | None = None
    session = bot.sessions.get(int(guild_id))
    if session is not None:
        status = await run_on_bot_loop(session.sample_status())
        if status.channel_id is not None:
            channel = str(status.channel_id)

    logger.debug(f"Connected to channel {channel}.")

    return ChannelsResponse(
        channels=[to_channel_response(c) for c in guild.voice_channels],
        current_channel=channel,
    )


class SelectGuildRequest(BaseModel):
    """Request to select a guild."""

    guild_id: str


class GuildSelectResponse(BaseModel):
    """Response after selecting a guild."""

    success: bool
    guild: GuildResponse | None = None
    error: str | None = None


@bp.route("/api/guild", methods=["POST"])
@validate_request(SelectGuildRequest)
@validate_response(GuildSelectResponse)
async def select_guild(
    data: SelectGuildRequest,
) -> GuildSelectResponse | tuple[GuildSelectResponse, int]:
    bot = get_bot()

    if bot and bot.is_ready():
        guild = bot.get_guild(int(data.guild_id))
        if guild:
            session["guild_id"] = data.guild_id
            return GuildSelectResponse(
                success=True, guild=to_guild_response(guild)
            )

    return GuildSelectResponse(
        success=False, error="Guild not found or bot not ready"
    ), 404


class SelectChannelRequest(BaseModel):
    """Request to select a voice channel."""

    guild_id: str
    channel_id: str


class ChannelSelectResponse(BaseModel):
    """Response after selecting a channel."""

    success: bool
    error: str | None = None


@bp.route("/api/guild/channel", methods=["POST"])
@validate_request(SelectChannelRequest)
@validate_response(ChannelSelectResponse)
async def select_channel(
    data: SelectChannelRequest,
) -> ChannelSelectResponse | tuple[ChannelSelectResponse, int]:
    bot = get_bot()
    logger.info(f"Connecting to channel {data.channel_id}.")
    try:
        await run_on_bot_loop(
            bot.sessions.connect(int(data.guild_id), int(data.channel_id))
        )
    except Exception as e:
        logger.opt(exception=True).error(
            f"Failed to connect to voice channel {data.channel_id}: {e}"
        )
        return ChannelSelectResponse(
            success=False, error="Failed to connect to voice channel"
        ), 500

    return ChannelSelectResponse(success=True)
