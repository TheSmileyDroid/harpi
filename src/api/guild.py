"""Guild API"""

from __future__ import annotations

import asyncio

from discord import Guild, VoiceChannel
from discord.ext.commands import Bot
from loguru import logger
from pydantic import BaseModel
from quart import Blueprint, session
from quart_schema import validate_request, validate_response

from src.discord_bot import get_bot_instance

bp = Blueprint("guild", __name__)


guilds: list[Guild] | None = None


def run_async(bot: Bot, coro):
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result(timeout=10)
            return result
        else:
            return None
    except Exception as e:
        logger.error(f"Error fetching guilds: {e}")
        return None


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


class ChannelResponse(BaseModel):
    id: str
    name: str


def to_channel_response(channel: VoiceChannel) -> ChannelResponse:
    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
    )


class GuildResponse(BaseModel):
    id: str
    name: str
    icon: str


def to_guild_response(guild: Guild) -> GuildResponse:
    return GuildResponse(
        id=str(guild.id),
        name=guild.name,
        icon=str(guild.icon.url) if guild.icon else "",
    )


@bp.route("/api/guild")
@validate_response(list[GuildResponse])
async def get_guilds():
    guilds_list = await _get_guilds()
    return [to_guild_response(g) for g in guilds_list]


class ChannelsResponse(BaseModel):
    channels: list[ChannelResponse]
    current_channel: str | None


@bp.route("/api/guild/<guild_id>/channels")
@validate_response(ChannelsResponse)
async def get_channels(guild_id: str):
    bot = get_bot_instance()
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return ChannelsResponse(channels=[], current_channel=None), 404

    channel: str | None = None
    if (guild_config := bot.api.get_guild_config(int(guild_id))) and (
        voice_channel := guild_config.channel
    ):
        channel = str(voice_channel.id)

    logger.debug(f"Connected to channel {channel}.")

    return ChannelsResponse(
        channels=[to_channel_response(c) for c in guild.voice_channels],
        current_channel=channel,
    )


class SelectGuildRequest(BaseModel):
    guild_id: str


class GuildSelectResponse(BaseModel):
    success: bool
    guild: GuildResponse | None = None
    error: str | None = None


@bp.route("/api/guild", methods=["POST"])
@validate_request(SelectGuildRequest)
@validate_response(GuildSelectResponse)
async def select_guild(data: SelectGuildRequest):
    bot = get_bot_instance()

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
    guild_id: str
    channel_id: str


class ChannelSelectResponse(BaseModel):
    success: bool
    error: str | None = None


@bp.route("/api/guild/channel", methods=["POST"])
@validate_request(SelectChannelRequest)
@validate_response(ChannelSelectResponse)
async def select_channel(data: SelectChannelRequest):
    bot = get_bot_instance()
    logger.info(f"Connecting to channel {data.channel_id}.")
    run_async(
        bot,
        bot.api.connect_to_voice(int(data.guild_id), int(data.channel_id)),
    )

    return ChannelSelectResponse(success=True), 201
