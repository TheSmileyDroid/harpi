"""HTMX fragment routes - partial HTML fragments for dynamic UI updates.

These routes return HTML fragments that HTMX uses to update parts of
the page without a full reload. They are the "partials" of the HTMX
application.
"""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from loguru import logger
from quart import Blueprint, render_template, request, session

from src.api.deps import get_bot, get_api, run_on_bot_loop
from src.api.guild import _get_guilds
from src.api.music import (
    DEFAULT_VOLUME,
    SEEK_TIMEOUT_SECONDS,
    _get_session,
    get_music_data,
)
from src.api.server_status import get_server_status

if TYPE_CHECKING:
    from src.harpi_lib.audio.session import PlaybackSession


bp = Blueprint("htmx_routes", __name__)


# ==========================================================================
# Helpers
# ==========================================================================


async def _parse_json_or_form() -> dict[str, Any]:
    """Parse request data from either JSON body or URL-encoded form."""
    if request.content_type and "json" in request.content_type:
        return await request.get_json(force=True) or {}
    form = await request.form
    return dict(form)


async def _session_action(
    guild_id: str,
    action: Callable[["PlaybackSession"], Coroutine[Any, Any, Any]],
) -> None:
    """Run a session verb on the bot loop when a session exists.

    Every panel action that touches playback funnels through here so the
    event-loop seam stays the single ``run_on_bot_loop`` bridge.
    """
    session = _get_session(int(guild_id))
    if session is not None:
        await run_on_bot_loop(action(session))


# ==========================================================================
# Server Status (Dashboard)
# ==========================================================================


@bp.route("/htmx/server/status")
async def htmx_server_status():
    """Server status cards fragment - polled every 5s."""
    bot = get_bot()
    guilds = await _get_guilds()
    status = await get_server_status(guilds, bot=bot)

    context = {
        **status,
        "guild_count": len(guilds),
        "user_count": sum(g.member_count or 0 for g in guilds)
        if guilds
        else 0,
    }

    return await render_template("partials/_server_status.html", **context)


# ==========================================================================
# Guild / Channel Selectors
# ==========================================================================


@bp.route("/htmx/channels")
async def htmx_channels():
    """Channel selector fragment - triggered when guild changes.

    Accepts guild_id as query param (sent by HTMX via hx-include).
    """
    guild_id = request.args.get("guild_id") or session.get("guild_id")
    bot = get_bot()
    guild = bot.get_guild(int(guild_id)) if guild_id else None
    channels = guild.voice_channels if guild else []

    context = {
        "channels": channels,
        "selected_channel_id": session.get("channel_id"),
    }

    return await render_template("partials/_channel_selector.html", **context)


# ==========================================================================
# Music Queue
# ==========================================================================


@bp.route("/htmx/music/<guild_id>/queue")
async def htmx_music_queue(guild_id: str):
    """Music queue fragment - polled every 3s."""
    queue = []
    current_track = None
    paused = False

    try:
        music_data = await get_music_data(int(guild_id))
        if music_data:
            queue = music_data.queue
            current_track = music_data.current_music
            paused = music_data.is_paused
    except Exception as e:
        logger.opt(exception=True).error(f"Error getting music queue: {e}")

    context = {
        "queue": queue,
        "current_track": current_track,
        "paused": paused,
        "guild_id": guild_id,
    }

    return await render_template("partials/_music_queue.html", **context)


# ==========================================================================
# Music Layers
# ==========================================================================


@bp.route("/htmx/music/<guild_id>/layers")
async def htmx_music_layers(guild_id: str):
    """Background layers fragment - polled every 3s."""
    layers = []

    try:
        music_data = await get_music_data(int(guild_id))
        if music_data:
            layers = music_data.layers
    except Exception as e:
        logger.opt(exception=True).error(f"Error getting music layers: {e}")

    context = {
        "layers": layers,
        "guild_id": guild_id,
    }

    return await render_template("partials/_music_layers.html", **context)


# ==========================================================================
# Playback Controls
# ==========================================================================


@bp.route("/htmx/music/<guild_id>/playback")
async def htmx_playback_controls(guild_id: str):
    """Playback controls fragment - polled every 2s."""
    current_track = None
    paused = False
    volume = DEFAULT_VOLUME
    loop_mode = "off"
    current_position = 0
    current_position_formatted = "0:00"

    try:
        music_data = await get_music_data(int(guild_id))
        if music_data:
            current_track = music_data.current_music
            paused = music_data.is_paused
            volume = music_data.volume
            loop_mode = music_data.loop_mode
            current_position = music_data.progress
            # Format position
            total_sec = current_position // 1000
            m = total_sec // 60
            s = total_sec % 60
            current_position_formatted = f"{m}:{s:02d}"
    except Exception as e:
        logger.opt(exception=True).error(f"Error getting playback state: {e}")

    context = {
        "current_track": current_track,
        "paused": paused,
        "volume": volume,
        "loop_mode": loop_mode,
        "current_position": current_position,
        "current_position_formatted": current_position_formatted,
        "guild_id": guild_id,
    }

    return await render_template("partials/_playback_controls.html", **context)


# ==========================================================================
# Music Search & Add Layer Modals
# ==========================================================================


@bp.route("/htmx/music/<guild_id>/search")
async def htmx_music_search_modal(guild_id: str):
    """Search modal fragment for adding music."""
    context = {
        "guild_id": guild_id,
    }
    return await render_template(
        "partials/_music_search_modal.html", **context
    )


@bp.route("/htmx/music/<guild_id>/add-layer")
async def htmx_music_add_layer_modal(guild_id: str):
    """Add layer modal fragment."""
    context = {
        "guild_id": guild_id,
    }
    return await render_template(
        "partials/_music_search_modal.html", **context
    )


# ==========================================================================
# Settings Sections
# ==========================================================================


@bp.route("/htmx/settings/<section>")
async def htmx_settings_section(section: str):
    """Settings section fragment."""
    template_map = {
        "general": "partials/_settings_general.html",
        "music": "partials/_settings_general.html",
        "tts": "partials/_settings_general.html",
        "dice": "partials/_settings_general.html",
    }

    template = template_map.get(section, "partials/_settings_general.html")
    context = {
        "config": {
            "DEFAULT_PREFIX": "!",
            "prefix": "!",
            "language": "en",
            "auto_connect": False,
            "debug_mode": False,
        },
        "version": "0.1.0",
    }

    return await render_template(template, **context)


# ==========================================================================
# Music Control Actions (POST) - Return updated HTML fragments
# ==========================================================================


@bp.route("/api/music/<guild_id>/play", methods=["POST"])
async def api_music_play(guild_id: str):
    """Resume playback and return updated controls."""
    try:
        await _session_action(guild_id, lambda s: s.resume())
    except Exception as e:
        logger.opt(exception=True).error(f"Error resuming: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/pause", methods=["POST"])
async def api_music_pause(guild_id: str):
    """Pause playback and return updated controls."""
    try:
        await _session_action(guild_id, lambda s: s.pause())
    except Exception as e:
        logger.opt(exception=True).error(f"Error pausing: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/toggle-pause", methods=["POST"])
async def api_music_toggle_pause(guild_id: str):
    """Toggle pause/resume and return updated controls."""
    try:
        await _session_action(guild_id, lambda s: s.toggle_pause())
    except Exception as e:
        logger.opt(exception=True).error(f"Error toggling pause: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/stop", methods=["POST"])
async def api_music_stop(guild_id: str):
    """Stop playback and return updated controls."""
    try:
        await _session_action(guild_id, lambda s: s.stop())
    except Exception as e:
        logger.opt(exception=True).error(f"Error stopping: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/skip", methods=["POST"])
async def api_music_skip(guild_id: str):
    """Skip to next track and return updated controls."""
    try:
        await _session_action(guild_id, lambda s: s.skip())
    except Exception as e:
        logger.opt(exception=True).error(f"Error skipping: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/previous", methods=["POST"])
async def api_music_previous(guild_id: str):
    """Go to previous track and return updated controls.

    TODO(SMI-38): Implement previous track. Currently no-ops — the API
    has no notion of a track history, so 'previous' cannot navigate back.
    Needs either a history stack or a playlist-level previous support.
    """
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/volume", methods=["POST"])
async def api_music_volume(guild_id: str):
    """Set volume and return updated controls."""
    data = await _parse_json_or_form()
    volume = data.get("volume", DEFAULT_VOLUME)
    try:
        await _session_action(guild_id, lambda s: s.set_volume(float(volume)))
    except Exception as e:
        logger.opt(exception=True).error(f"Error setting volume: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/seek", methods=["POST"])
async def api_music_seek(guild_id: str):
    """Seek to position and return updated controls."""
    data = await _parse_json_or_form()
    position = data.get("position")
    absolute = str(data.get("absolute", "false")).lower() in {
        "true",
        "1",
        "on",
    }
    if position is None:
        return await htmx_playback_controls(guild_id)
    try:
        position_float = float(position)
    except (TypeError, ValueError):
        return await htmx_playback_controls(guild_id)
    if not math.isfinite(position_float):
        return await htmx_playback_controls(guild_id)
    try:
        await asyncio.wait_for(
            _session_action(
                guild_id, lambda s: s.seek(position_float, absolute)
            ),
            timeout=SEEK_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.error(f"Seek timed out for guild {guild_id}")
    except Exception as e:
        logger.opt(exception=True).error(f"Error seeking: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/loop/<mode>", methods=["POST"])
async def api_music_loop(guild_id: str, mode: str):
    """Set loop mode and return updated controls."""
    from src.api.music import LOOP_MODE_ALIASES

    loop_mode = LOOP_MODE_ALIASES.get(mode)
    if loop_mode:
        try:
            await _session_action(guild_id, lambda s: s.set_loop(loop_mode))
        except Exception as e:
            logger.opt(exception=True).error(f"Error setting loop: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/disconnect", methods=["POST"])
async def api_music_disconnect(guild_id: str):
    """Disconnect from voice channel."""
    try:
        session = _get_session(int(guild_id))
        if session is not None:
            await run_on_bot_loop(get_bot().sessions.disconnect(int(guild_id)))
    except Exception as e:
        logger.opt(exception=True).error(f"Error disconnecting: {e}")
    return "", 204  # No content


# ==========================================================================
# Queue Management Actions (POST/DELETE) - Return updated queue HTML
# ==========================================================================


@bp.route(
    "/api/music/<guild_id>/queue/remove/<path:track_url>", methods=["DELETE"]
)
async def api_music_queue_remove(guild_id: str, track_url: str):
    """Remove track from queue by URL."""
    try:
        await _session_action(guild_id, lambda s: s.remove(track_url))
    except Exception as e:
        logger.opt(exception=True).error(f"Error removing track: {e}")
    return await htmx_music_queue(guild_id)


@bp.route(
    "/api/music/<guild_id>/queue/move/<path:track_url>/<int:position>",
    methods=["POST"],
)
async def api_music_queue_move(guild_id: str, track_url: str, position: int):
    """Move track to a new position in the queue."""
    try:
        await _session_action(guild_id, lambda s: s.move(track_url, position))
    except Exception as e:
        logger.opt(exception=True).error(f"Error moving track: {e}")
    return await htmx_music_queue(guild_id)


@bp.route("/api/music/<guild_id>/queue/clear", methods=["POST"])
async def api_music_queue_clear(guild_id: str):
    """Clear the entire queue."""
    try:
        await _session_action(guild_id, lambda s: s.clear_queue())
    except Exception as e:
        logger.opt(exception=True).error(f"Error clearing queue: {e}")
    return await htmx_music_queue(guild_id)


# ==========================================================================
# Layer Management Actions (POST/DELETE) - Return updated layers HTML
# ==========================================================================


@bp.route("/api/music/<guild_id>/layer/remove/<layer_id>", methods=["DELETE"])
async def api_music_layer_remove(guild_id: str, layer_id: str):
    """Remove a background layer."""
    try:
        await get_api().remove_background_audio(int(guild_id), layer_id)
    except Exception as e:
        logger.opt(exception=True).error(f"Error removing layer: {e}")
    return await htmx_music_layers(guild_id)


@bp.route("/api/music/<guild_id>/layers/clean", methods=["POST"])
async def api_music_layers_clean(guild_id: str):
    """Remove all background layers."""
    try:
        await get_api().clean_background_audios(int(guild_id))
    except Exception as e:
        logger.opt(exception=True).error(f"Error cleaning layers: {e}")
    return await htmx_music_layers(guild_id)


@bp.route("/api/music/<guild_id>/layer/<layer_id>/volume", methods=["POST"])
async def api_music_layer_volume(guild_id: str, layer_id: str):
    """Set layer volume."""
    data = await _parse_json_or_form()
    volume = data.get("volume", 0.5)
    try:
        await get_api().set_background_volume(
            int(guild_id), layer_id, float(volume)
        )
    except Exception as e:
        logger.opt(exception=True).error(f"Error setting layer volume: {e}")
    return await htmx_music_layers(guild_id)


@bp.route("/api/music/<guild_id>/layer/<layer_id>/pause", methods=["POST"])
async def api_music_layer_pause(guild_id: str, layer_id: str):
    """Pause a background layer.

    TODO(SMI-38): Implement per-layer pause in BackgroundAudioService.
    The mixer currently handles all layers as one stream, so individual
    layer pausing requires separate per-layer volume/gain control.
    """
    return await htmx_music_layers(guild_id)


@bp.route("/api/music/<guild_id>/layer/<layer_id>/resume", methods=["POST"])
async def api_music_layer_resume(guild_id: str, layer_id: str):
    """Resume a background layer.

    TODO(SMI-38): Implement per-layer resume in BackgroundAudioService.
    See layer/pause — same underlying limitation applies.
    """
    return await htmx_music_layers(guild_id)


# ==========================================================================
# Settings Actions
# ==========================================================================


@bp.route("/api/settings/<section>", methods=["POST"])
async def api_settings_update(section: str):
    """Update a setting and return a toast notification.

    TODO(SMI-38): Persist settings to a config file or database.
    Currently logs the update but does not save it anywhere, so all
    settings are lost on restart.
    """
    data = await _parse_json_or_form()
    logger.debug(f"Settings update for '{section}': {data}")
    return '<div class="toast toast-success">Settings updated</div>'


# ==========================================================================
# Guild / Channel Selection Actions
# ==========================================================================


@bp.route("/api/guild/select-channel", methods=["POST"])
async def guild_select_channel():
    """Select a guild and channel, connect to voice, saving to session."""
    data = await _parse_json_or_form()
    guild_id = data.get("guild_id")
    channel_id = data.get("channel_id")

    if not guild_id or not channel_id:
        return "guild_id and channel_id are required", 400

    # Save to session
    session["guild_id"] = guild_id
    session["channel_id"] = channel_id
    session.permanent = True

    # Actually connect to voice
    try:
        bot = get_bot()
        if bot and bot.is_ready():
            await run_on_bot_loop(
                bot.sessions.connect(int(guild_id), int(channel_id)),
            )
        else:
            logger.error("Bot is not ready")
            return "Bot is not ready", 503
    except Exception as e:
        logger.opt(exception=True).error(f"Error connecting to voice: {e}")
        return str(e), 500

    return "", 204


# ==========================================================================
# Bot Management Actions
# ==========================================================================


@bp.route("/api/bot/restart", methods=["POST"])
async def api_bot_restart():
    """Restart the bot.

    TODO(SMI-38): Implement bot restart. Needs the ability to shut down
    the current bot process and spawn a new one, or use a process
    manager (e.g., systemd, docker) to handle restarts externally.
    """
    return (
        '<div class="toast toast-info">Bot restart not yet implemented</div>'
    )


@bp.route("/api/bot/shutdown", methods=["POST"])
async def api_bot_shutdown():
    """Shutdown the bot.

    TODO(SMI-38): Implement bot shutdown. Needs graceful teardown:
    disconnect from voice channels, save state, then exit the process.
    """
    return (
        '<div class="toast toast-info">Bot shutdown not yet implemented</div>'
    )


# ==========================================================================
# Utility Endpoints
# ==========================================================================


@bp.route("/api/ping")
async def api_ping():
    """Ping endpoint for latency measurement."""
    return "", 204


@bp.route("/api/music/search")
async def api_music_search():
    """Search YouTube for music tracks.

    Query params:
        q: Search query
        guild_id: Guild ID (optional)
    """
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return {"results": []}

    try:
        from src.harpi_lib.music.ytmusicdata import YTMusicData

        results = await YTMusicData.from_url(query)
        formatted = []
        for r in results:
            formatted.append({
                "id": r.url,
                "title": r.title,
                "duration": r.duration,
                "url": r.url,
                "thumbnail": r.thumbnail,
                "uploader": r.uploader,
                "source": "youtube",
            })
        return {"results": formatted}
    except Exception as e:
        logger.opt(exception=True).error(f"Search error for '{query}': {e}")
        return {"results": [], "error": str(e)}
