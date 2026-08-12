from __future__ import annotations

from typing import cast

from discord import VoiceChannel
from quart import Blueprint, render_template, session

from src.api.deps import get_bot as get_discord_bot
from src.api.guild import _get_guilds
from src.api.music import DEFAULT_VOLUME, get_music_data
from src.api.server_status import get_server_status

bp = Blueprint("html_routes", __name__)


async def _get_base_context():
    """Build the shared context dict for all page templates."""
    bot = get_discord_bot()
    guilds = await _get_guilds()

    raw_guild_id = session.get("guild_id")
    selected_guild_id = int(raw_guild_id) if raw_guild_id else None
    channels = []
    selected_channel: VoiceChannel | None = None
    if selected_guild_id and bot:
        guild = bot.get_guild(selected_guild_id)
        if guild:
            channels = guild.voice_channels

    for voice_client in bot.voice_clients:
        channel = cast(VoiceChannel, voice_client.channel)
        if channel.guild.id == selected_guild_id:
            selected_channel = channel

    return {
        "bot_connected": bot.is_ready() if bot else False,
        "guilds": guilds,
        "selected_guild_id": selected_guild_id,
        "selected_channel_id": selected_channel.id
        if selected_channel
        else None,
        "channels": channels,
    }


@bp.route("/", defaults={"page": "dashboard"})
@bp.route("/pages/<path:page>")
async def route(page):
    ctx = await _get_base_context()
    bot = get_discord_bot()
    status = await get_server_status(ctx["guilds"], bot=bot)
    ctx.update({
        **status,
        "guild_count": len(ctx["guilds"]) if ctx["guilds"] else 0,
        "user_count": sum(g.member_count or 0 for g in ctx["guilds"])
        if ctx["guilds"]
        else 0,
        "bot_user": str(bot.user) if bot and bot.user else "Unknown",
        "bot_id": str(bot.user.id) if bot and bot.user else "Unknown",
        "discord_version": "2.5.2",
        "python_version": "3.13",
        "version": "0.1.0",
    })

    guild_id = ctx["selected_guild_id"]
    channel_id = ctx["selected_channel_id"]
    queue = []
    layers = []
    current_track = None
    paused = False
    volume = DEFAULT_VOLUME
    loop_mode = "off"
    current_position = 0
    current_position_formatted = "0:00"

    if guild_id and channel_id:
        try:
            music_data = await get_music_data(int(guild_id))
            if music_data:
                queue = music_data.queue
                layers = music_data.layers
                current_track = music_data.current_music
                paused = music_data.is_paused
                volume = music_data.volume
                loop_mode = music_data.loop_mode
        except Exception:
            pass

    ctx.update({
        "guild_id": guild_id,
        "queue": queue,
        "layers": layers,
        "current_track": current_track,
        "paused": paused,
        "volume": volume,
        "loop_mode": loop_mode,
        "current_position": current_position,
        "current_position_formatted": current_position_formatted,
        "selected_guild": get_discord_bot().get_guild(int(guild_id))
        if guild_id
        else None,
        "selected_channel": get_discord_bot().get_channel(int(channel_id))
        if channel_id
        else None,
    })

    return await render_template(f"pages/{page}.html", **ctx)
