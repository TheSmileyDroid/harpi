"""Guild API — guild listing, voice channel info, and guild selection.

Thread safety
-------------
The module-level ``guilds`` cache is populated and read exclusively from
Quart's event loop (single-threaded async).  ``run_async`` is used to
schedule coroutines on the bot's event loop when cross-loop access is
needed.  No lock is required for the cache itself (MEDIUM-1 accepted
risk — only one event loop serves HTTP requests).
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from discord import Guild, VoiceChannel
from discord.ext.commands import Bot
from loguru import logger
from pydantic import BaseModel
from quart import Blueprint, session
from quart_schema import validate_request, validate_response

from src.api.deps import get_api, get_bot

bp = Blueprint("guild", __name__)


guilds: list[Guild] | None = None


_SENTINEL = object()


def run_async(bot: Bot, coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine on the bot's event loop from a sync context."""
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result(timeout=10)
            return result if result is not None else _SENTINEL
        else:
            logger.warning("Bot event loop is closed or unavailable")
            return None
    except Exception as e:
        logger.opt(exception=True).error(f"Error in run_async: {e}")
        return None


async def _get_guilds() -> list[Guild]:
    """Load guilds the bot is connected to."""
    global guilds
    if guilds is not None:
        return guilds
    bot = get_bot()
    if not bot:
        return []

    async def load_guild():
        return [guild async for guild in bot.fetch_guilds(limit=150)]

    guilds = run_async(bot, load_guild()) or []
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
    if (guild_config := get_api().get_guild_config(int(guild_id))) and (
        voice_channel := guild_config.channel
    ):
        channel = str(voice_channel.id)

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
    result = run_async(
        bot,
        get_api().connect_to_voice(int(data.guild_id), int(data.channel_id)),
    )

    if result is None:
        return ChannelSelectResponse(
            success=False, error="Failed to connect to voice channel"
        ), 500

    return ChannelSelectResponse(success=True)
