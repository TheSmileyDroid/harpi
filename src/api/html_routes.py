"""HTML page routes - full Jinja2 templates for HTMX UI.

These routes return complete HTML pages that extend base.html.
They are the entry points for the HTMX-based frontend.
"""

from __future__ import annotations

from quart import Blueprint, render_template, session

from src.api.deps import get_bot as get_discord_bot
from src.api.guild import _get_guilds
from src.api.music import get_music_data, DEFAULT_VOLUME
from src.api.server_status import get_server_status

bp = Blueprint("html_routes", __name__)


async def _get_base_context():
    """Build the shared context dict for all page templates."""
    bot = get_discord_bot()
    guilds = await _get_guilds()

    # Get channels for pre-selected guild
    selected_guild_id = session.get("guild_id")
    channels = []
    if selected_guild_id and bot:
        guild = bot.get_guild(int(selected_guild_id))
        if guild:
            channels = guild.voice_channels

    context = {
        "bot_connected": bot.is_ready() if bot else False,
        "guilds": guilds,
        "selected_guild_id": selected_guild_id,
        "selected_channel_id": session.get("channel_id"),
        "channels": channels,
    }
    return context


@bp.route("/dashboard")
async def dashboard():
    """Dashboard page - server status, quick actions, bot info."""
    ctx = await _get_base_context()
    bot = get_discord_bot()

    # Real server status data
    status = get_server_status(ctx["guilds"])

    ctx.update({
        "cpu_percent": status["cpu_percent"],
        "memory_percent": status["memory_percent"],
        "memory_total": status["memory_total"],
        "memory_used": status["memory_used"],
        "guild_count": len(ctx["guilds"]) if ctx["guilds"] else 0,
        "user_count": sum(g.member_count or 0 for g in ctx["guilds"])
        if ctx["guilds"]
        else 0,
        "queue_total": status["queue_total"],
        "music_guilds": status["music_guilds"],
        "uptime_formatted": status["uptime_formatted"],
        "bot_latency": bot.latency * 1000 if bot and bot.latency else 0,
        "bot_user": str(bot.user) if bot and bot.user else "Unknown",
        "bot_id": str(bot.user.id) if bot and bot.user else "Unknown",
        "discord_version": "2.5.2",
        "python_version": "3.13",
        "version": "0.1.0",
    })

    return await render_template("pages/dashboard.html", **ctx)


@bp.route("/music")
async def music_page():
    """Music control page - queue, layers, playback."""
    ctx = await _get_base_context()
    guild_id = session.get("guild_id")

    queue = []
    layers = []
    current_track = None
    paused = False
    volume = DEFAULT_VOLUME
    loop_mode = "off"
    current_position = 0
    current_position_formatted = "0:00"

    if guild_id:
        try:
            music_data = get_music_data(int(guild_id))
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
        "selected_channel": None,  # TODO: resolve from guild config
    })

    return await render_template("pages/music.html", **ctx)


@bp.route("/settings")
async def settings_page():
    """Settings page - general, music, TTS, dice config."""
    ctx = await _get_base_context()

    ctx.update({
        "config": {
            "DEFAULT_PREFIX": "!",
            "prefix": "!",
            "language": "en",
            "auto_connect": False,
            "debug_mode": False,
        },
        "version": "0.1.0",
    })

    return await render_template("pages/settings.html", **ctx)
