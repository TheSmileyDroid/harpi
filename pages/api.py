from __future__ import annotations

import hmac
import math
from typing import Any

from quart import Blueprint, Response, jsonify, request, session

from src.config import Settings
from src.harpi_lib.audio.session import LOOP_MODE_ALIASES
from src.panel import actions, state

bp = Blueprint("api", __name__)


def error_response(code: str, message: str, status: int) -> Response:
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    return response


def _int_field(payload: Any, field: str) -> int | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _string_field(payload: Any, field: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _float_field(payload: Any, field: str) -> float | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def current_guild_id() -> int | None:
    raw = session.get("guild_id")
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _live_guild_id() -> int | None:
    guild_id = current_guild_id()
    if guild_id is None or not state.guild_visible(guild_id):
        return None
    if not state.session_exists(guild_id):
        return None
    return guild_id


def _token_matches(candidate: Any) -> bool:
    configured = Settings.from_env().panel_token
    if not configured or not isinstance(candidate, str):
        return False
    return hmac.compare_digest(candidate, configured)


@bp.post("/api/session")
async def create_session() -> Response:
    payload = await request.get_json(silent=True)
    token = payload.get("token") if isinstance(payload, dict) else None
    if not _token_matches(token):
        return error_response("unauthorized", "Invalid panel token", 401)
    session.permanent = True
    session["authenticated"] = True
    return jsonify({"authenticated": True})


@bp.get("/api/session")
def read_session() -> Response:
    return jsonify({"authenticated": True})


@bp.get("/api/status")
async def read_status() -> Response:
    return jsonify(await state.status_snapshot(current_guild_id()))


@bp.get("/api/guilds")
async def read_guilds() -> Response:
    return jsonify({"guilds": await state.list_guilds()})


@bp.get("/api/guilds/<int:guild_id>/channels")
def read_channels(guild_id: int) -> Response:
    if not state.guild_visible(guild_id):
        return error_response("not_found", "Guild not found", 404)
    return jsonify({"channels": state.list_voice_channels(guild_id)})


@bp.post("/api/connect")
async def connect_voice() -> Response:
    payload = await request.get_json(silent=True)
    guild_id = _int_field(payload, "guild_id")
    channel_id = _int_field(payload, "channel_id")
    if guild_id is None or not state.guild_visible(guild_id):
        return error_response("not_found", "Guild not found", 404)
    channel_ids = {
        channel["id"] for channel in state.list_voice_channels(guild_id)
    }
    if channel_id is None or channel_id not in channel_ids:
        return error_response("not_found", "Channel not found", 404)
    await actions.connect(guild_id, channel_id)
    session["guild_id"] = str(guild_id)
    return jsonify(await state.status_snapshot(guild_id))


@bp.post("/api/disconnect")
async def disconnect_voice() -> Response:
    guild_id = current_guild_id()
    if guild_id is not None and state.session_exists(guild_id):
        await actions.disconnect(guild_id)
    return jsonify(await state.status_snapshot(guild_id))


@bp.post("/api/search")
async def api_search() -> Response:
    term = _string_field(await request.get_json(silent=True), "term")
    if term is None:
        return jsonify({"results": []})
    return jsonify({"results": await actions.search_tracks(term)})


@bp.post("/api/queue")
async def queue_track() -> Response:
    return await _mutate_url(actions.add_track)


@bp.post("/api/queue/remove")
async def remove_queued_track() -> Response:
    return await _mutate_url(actions.remove_track)


@bp.post("/api/queue/clear")
async def clear_queued_tracks() -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    await actions.clear_queue(guild)
    return jsonify(await state.status_snapshot(guild))


def _no_live_session() -> Response:
    return error_response(
        "not_found", "No active session for the selected guild", 404
    )


async def _mutate_url(mutation) -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    url = _string_field(await request.get_json(silent=True), "url")
    if url is None:
        return error_response("not_found", "A URL is required", 404)
    await mutation(guild, url)
    return jsonify(await state.status_snapshot(guild))


async def _transport(mutation) -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    await mutation(guild)
    return jsonify(await state.status_snapshot(guild))


@bp.post("/api/playback/pause")
async def playback_pause() -> Response:
    return await _transport(actions.pause)


@bp.post("/api/playback/resume")
async def playback_resume() -> Response:
    return await _transport(actions.resume)


@bp.post("/api/playback/skip")
async def playback_skip() -> Response:
    return await _transport(actions.skip)


@bp.post("/api/playback/previous")
async def playback_previous() -> Response:
    return await _transport(actions.previous)


@bp.post("/api/playback/loop")
async def playback_loop() -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    mode = _string_field(await request.get_json(silent=True), "mode")
    if mode is None or mode not in LOOP_MODE_ALIASES:
        return error_response("not_found", "Unknown loop mode", 404)
    await actions.set_loop(guild, mode)
    return jsonify(await state.status_snapshot(guild))


@bp.post("/api/playback/seek")
async def playback_seek() -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    position = _float_field(await request.get_json(silent=True), "position")
    if position is None or position < 0:
        return error_response("not_found", "Invalid seek position", 404)
    try:
        await actions.seek(guild, position)
    except ValueError:
        return error_response("not_found", "Invalid seek position", 404)
    return jsonify(await state.status_snapshot(guild))


@bp.post("/api/playback/volume")
async def playback_volume() -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    volume = _float_field(await request.get_json(silent=True), "volume")
    if volume is None:
        return error_response("not_found", "Invalid volume", 404)
    await actions.set_volume(guild, volume)
    return jsonify(await state.status_snapshot(guild))


@bp.post("/api/layers")
async def layer_add() -> Response:
    return await _mutate_url(actions.add_layer)


@bp.post("/api/layers/remove")
async def layer_remove() -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    layer_id = _string_field(await request.get_json(silent=True), "layer_id")
    if layer_id is None or not await actions.remove_layer(guild, layer_id):
        return error_response("not_found", "Unknown layer", 404)
    return jsonify(await state.status_snapshot(guild))


@bp.post("/api/layers/volume")
async def layer_volume() -> Response:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    payload = await request.get_json(silent=True)
    layer_id = _string_field(payload, "layer_id")
    volume = _float_field(payload, "volume")
    if layer_id is None or volume is None:
        return error_response("not_found", "Invalid layer volume", 404)
    if not await actions.set_layer_volume(guild, layer_id, volume):
        return error_response("not_found", "Unknown layer", 404)
    return jsonify(await state.status_snapshot(guild))
