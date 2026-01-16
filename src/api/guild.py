"""Guild API"""

import asyncio

from discord import Guild, VoiceChannel
from discord.ext.commands import Bot
from loguru import logger
from quart import Blueprint, jsonify, request, session

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


def _guild_to_dict(guild: Guild):
    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None,
    }


def _channel_to_dict(channel: VoiceChannel):
    return {
        "id": str(channel.id),
        "name": channel.name,
    }


@bp.route("/api/guilds")
async def api_guilds():
    guilds_list = await _get_guilds()
    return jsonify([_guild_to_dict(g) for g in guilds_list])


@bp.route("/api/guilds/<int:guild_id>/channels")
async def get_channels(guild_id: int):
    bot = get_bot_instance()
    guild = bot.get_guild(guild_id)
    if not guild:
        return jsonify([]), 404

    channel: str | None = None
    if (guild_config := bot.api.get_guild_config(guild_id)) and (
        voice_channel := guild_config.channel
    ):
        channel = str(voice_channel.id)

    logger.debug(f"Connected to channel {channel}.")

    return jsonify(
        {
            "channels": [_channel_to_dict(c) for c in guild.voice_channels],
            "current_channel": channel,
        }
    ), 200


@bp.route("/api/guild/select/<int:guild_id>", methods=["POST"])
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


@bp.route("/api/guilds/<int:guild_id>/select-channel", methods=["POST"])
async def select_channel(guild_id: int):
    bot = get_bot_instance()
    data = await request.get_json()
    if not data:
        return jsonify(
            {
                "success": False,
                "error": "Expected channelId to be passed through POST body.",
            }
        ), 400
    channel_id = int(data.get("channelId"))
    logger.info(f"Connecting to channel {channel_id}.")
    run_async(bot, bot.api.connect_to_voice(guild_id, channel_id))

    return jsonify({"success": True}), 201
