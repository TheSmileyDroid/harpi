from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from loguru import logger
from quart import Blueprint, render_template, request, session

from src.api.deps import get_bot, run_on_bot_loop
from src.api.music import (
    DEFAULT_VOLUME,
    SEEK_TIMEOUT_SECONDS,
    _get_session,
)
from src.api.panel_context import (
    APP_VERSION,
    get_music_panel,
    selector_context,
    server_status_context,
)

if TYPE_CHECKING:
    from src.harpi_lib.audio.session import PlaybackSession


bp = Blueprint("htmx_routes", __name__)


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


@bp.route("/htmx/server/status")
async def htmx_server_status():
    """Server status cards fragment - polled every 5s."""
    return await render_template(
        "partials/_server_status.html", **await server_status_context()
    )


@bp.route("/htmx/music/<guild_id>/queue")
async def htmx_music_queue(guild_id: str):
    """Music queue fragment - polled every 3s."""
    panel = await get_music_panel(int(guild_id))
    context = {
        "queue": panel.queue,
        "current_track": panel.current_track,
        "paused": panel.paused,
        "guild_id": guild_id,
    }

    return await render_template("partials/_music_queue.html", **context)


@bp.route("/htmx/music/<guild_id>/layers")
async def htmx_music_layers(guild_id: str):
    """Background layers fragment - polled every 3s."""
    panel = await get_music_panel(int(guild_id))
    context = {
        "layers": panel.layers,
        "guild_id": guild_id,
    }

    return await render_template("partials/_music_layers.html", **context)


@bp.route("/htmx/music/<guild_id>/playback")
async def htmx_playback_controls(guild_id: str):
    """Playback controls fragment - polled every 2s."""
    panel = await get_music_panel(int(guild_id))
    context = {
        "current_track": panel.current_track,
        "paused": panel.paused,
        "volume": panel.volume,
        "loop_mode": panel.loop_mode,
        "current_position": panel.current_position,
        "current_position_formatted": panel.current_position_formatted,
        "guild_id": guild_id,
    }

    return await render_template("partials/_playback_controls.html", **context)


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
        "version": APP_VERSION,
    }

    return await render_template(template, **context)


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
    """Go to previous track and return updated controls."""
    # TODO(SMI-38): implement previous track
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
    from src.harpi_lib.audio.session import LOOP_MODE_ALIASES

    loop_mode = LOOP_MODE_ALIASES.get(mode)
    if loop_mode:
        try:
            await _session_action(guild_id, lambda s: s.set_loop(loop_mode))
        except Exception as e:
            logger.opt(exception=True).error(f"Error setting loop: {e}")
    return await htmx_playback_controls(guild_id)


@bp.route("/api/music/<guild_id>/disconnect", methods=["POST"])
async def api_music_disconnect(guild_id: str):
    """Disconnect from voice channel and re-render the selector."""
    try:
        session = _get_session(int(guild_id))
        if session is not None:
            await run_on_bot_loop(get_bot().sessions.disconnect(int(guild_id)))
    except Exception as e:
        logger.opt(exception=True).error(f"Error disconnecting: {e}")
        return str(e), 500

    return await render_template(
        "partials/_guild_channel_selector.html",
        **await selector_context(),
    )


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


@bp.route("/api/music/<guild_id>/layer/remove/<layer_id>", methods=["DELETE"])
async def api_music_layer_remove(guild_id: str, layer_id: str):
    """Remove a background layer."""
    try:
        await _session_action(guild_id, lambda s: s.remove_layer(layer_id))
    except Exception as e:
        logger.opt(exception=True).error(f"Error removing layer: {e}")
    return await htmx_music_layers(guild_id)


@bp.route("/api/music/<guild_id>/layers/clean", methods=["POST"])
async def api_music_layers_clean(guild_id: str):
    """Remove all background layers."""
    try:
        await _session_action(guild_id, lambda s: s.clear_layers())
    except Exception as e:
        logger.opt(exception=True).error(f"Error cleaning layers: {e}")
    return await htmx_music_layers(guild_id)


@bp.route("/api/music/<guild_id>/layer/<layer_id>/volume", methods=["POST"])
async def api_music_layer_volume(guild_id: str, layer_id: str):
    """Set layer volume."""
    data = await _parse_json_or_form()
    volume = data.get("volume", 0.5)
    try:
        await _session_action(
            guild_id, lambda s: s.set_layer_volume(layer_id, float(volume))
        )
    except Exception as e:
        logger.opt(exception=True).error(f"Error setting layer volume: {e}")
    return await htmx_music_layers(guild_id)


@bp.route("/api/settings/<section>", methods=["POST"])
async def api_settings_update(section: str):
    """Update a setting and return a toast notification."""
    # TODO(SMI-38): persist settings to a config file
    data = await _parse_json_or_form()
    logger.debug(f"Settings update for '{section}': {data}")
    return '<div class="toast toast-success">Settings updated</div>'


@bp.route("/api/guild/select-channel")
async def guild_select_channel():
    """Apply one selector step: a guild change or a channel change.

    A guild change saves the guild and re-renders the selector with that
    guild's channels (no connect).  A channel change connects through the
    session guild — never a fresh ``guild_id`` arg — and re-renders the
    selector.  When the bot is not ready the selector still re-renders
    with the saved selection.
    """
    guild_id = request.args.get("guild_id")
    channel_id = request.args.get("channel_id")

    if not guild_id and not channel_id:
        return "guild_id or channel_id required", 400

    if guild_id:
        session["guild_id"] = guild_id
        session.permanent = True

    bot = get_bot()
    if not bot or not bot.is_ready():
        logger.error("Bot is not ready")
        return (
            await render_template(
                "partials/_guild_channel_selector.html",
                **await selector_context(),
            ),
            503,
        )

    if channel_id:
        raw_guild_id = session.get("guild_id")
        if not raw_guild_id:
            return "select a guild first", 400
        try:
            await run_on_bot_loop(
                bot.sessions.connect(int(raw_guild_id), int(channel_id))
            )
        except Exception as e:
            logger.opt(exception=True).error(f"Error connecting to voice: {e}")
            return str(e), 500

    return await render_template(
        "partials/_guild_channel_selector.html",
        **await selector_context(),
    )


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
