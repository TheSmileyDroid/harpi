from __future__ import annotations

import hmac
from typing import Any

from quart import Blueprint, Response, jsonify, request, session
from quart_schema import document_request, document_response, validate_response

from src.config import Settings
from src.harpi_lib.audio.session import LOOP_MODE_ALIASES
from src.panel import actions, state
from src.panel.schemas import (
    Authenticated,
    ChannelList,
    ConnectRequest,
    ErrorEnvelope,
    GuildList,
    LayerIdRequest,
    LayerVolumeRequest,
    LoopRequest,
    SearchRequest,
    SearchResults,
    SeekRequest,
    SessionRequest,
    StatusSnapshot,
    UrlRequest,
    VolumeRequest,
)

bp = Blueprint("api", __name__)


def error_response(code: str, message: str, status: int) -> Response:
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    return response


def _parse(model: type[Any], payload: Any) -> Any:
    return model.model_validate(payload if isinstance(payload, dict) else {})


def current_guild_id() -> int | None:
    raw = session.get("guild_id")
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _live_guild_id() -> int | None:
    guild_id = state.resolve_guild_id(current_guild_id())
    if guild_id is None or not state.session_exists(guild_id):
        return None
    return guild_id


def _token_matches(candidate: Any) -> bool:
    configured = Settings.from_env().panel_token
    if not configured or not isinstance(candidate, str):
        return False
    return hmac.compare_digest(candidate, configured)


@bp.post("/api/session")
@document_request(SessionRequest)
@document_response(ErrorEnvelope, 401)
@validate_response(Authenticated, 200)
async def create_session() -> Any:
    payload = await request.get_json(silent=True)
    token = payload.get("token") if isinstance(payload, dict) else None
    if not _token_matches(token):
        return error_response("unauthorized", "Invalid panel token", 401)
    session.permanent = True
    session["authenticated"] = True
    return {"authenticated": True}


@bp.get("/api/session")
@validate_response(Authenticated, 200)
def read_session() -> Any:
    return {"authenticated": True}


@bp.get("/api/status")
@validate_response(StatusSnapshot, 200)
async def read_status() -> Any:
    return await state.status_snapshot(current_guild_id())


@bp.get("/api/guilds")
@validate_response(GuildList, 200)
async def read_guilds() -> Any:
    return {"guilds": await state.list_guilds()}


@bp.get("/api/guilds/<int:guild_id>/channels")
@document_response(ErrorEnvelope, 404)
@validate_response(ChannelList, 200)
def read_channels(guild_id: int) -> Any:
    if not state.guild_visible(guild_id):
        return error_response("not_found", "Guild not found", 404)
    return {"channels": state.list_voice_channels(guild_id)}


@bp.post("/api/connect")
@document_request(ConnectRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def connect_voice() -> Any:
    data = _parse(ConnectRequest, await request.get_json(silent=True))
    if data.guild_id is None or not state.guild_visible(int(data.guild_id)):
        return error_response("not_found", "Guild not found", 404)
    guild_id = int(data.guild_id)
    channel_ids = {
        channel.id for channel in state.list_voice_channels(guild_id)
    }
    if data.channel_id is None or data.channel_id not in channel_ids:
        return error_response("not_found", "Channel not found", 404)
    await actions.connect(guild_id, int(data.channel_id))
    session["guild_id"] = str(guild_id)
    return await state.status_snapshot(guild_id)


@bp.post("/api/disconnect")
@validate_response(StatusSnapshot, 200)
async def disconnect_voice() -> Any:
    guild_id = current_guild_id()
    target = state.resolve_guild_id(guild_id)
    if target is not None and (
        state.session_exists(target) or state.voice_active(target)
    ):
        await actions.disconnect(target)
    return await state.status_snapshot(guild_id)


@bp.post("/api/search")
@document_request(SearchRequest)
@validate_response(SearchResults, 200)
async def api_search() -> Any:
    data = _parse(SearchRequest, await request.get_json(silent=True))
    if data.term is None:
        return {"results": []}
    return {"results": await actions.search_tracks(data.term)}


def _no_live_session() -> Response:
    return error_response(
        "not_found", "No active session for the selected guild", 404
    )


async def _mutate_url(mutation: Any) -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    data = _parse(UrlRequest, await request.get_json(silent=True))
    if data.url is None:
        return error_response("not_found", "A URL is required", 404)
    await mutation(guild, data.url)
    return await state.status_snapshot(guild)


async def _transport(mutation: Any) -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    await mutation(guild)
    return await state.status_snapshot(guild)


@bp.post("/api/queue")
@document_request(UrlRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def queue_track() -> Any:
    return await _mutate_url(actions.add_track)


@bp.post("/api/queue/remove")
@document_request(UrlRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def remove_queued_track() -> Any:
    return await _mutate_url(actions.remove_track)


@bp.post("/api/queue/clear")
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def clear_queued_tracks() -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    await actions.clear_queue(guild)
    return await state.status_snapshot(guild)


@bp.post("/api/playback/pause")
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def playback_pause() -> Any:
    return await _transport(actions.pause)


@bp.post("/api/playback/resume")
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def playback_resume() -> Any:
    return await _transport(actions.resume)


@bp.post("/api/playback/skip")
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def playback_skip() -> Any:
    return await _transport(actions.skip)


@bp.post("/api/playback/previous")
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def playback_previous() -> Any:
    return await _transport(actions.previous)


@bp.post("/api/playback/loop")
@document_request(LoopRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def playback_loop() -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    data = _parse(LoopRequest, await request.get_json(silent=True))
    if data.mode is None or data.mode not in LOOP_MODE_ALIASES:
        return error_response("not_found", "Unknown loop mode", 404)
    await actions.set_loop(guild, data.mode)
    return await state.status_snapshot(guild)


@bp.post("/api/playback/seek")
@document_request(SeekRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def playback_seek() -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    data = _parse(SeekRequest, await request.get_json(silent=True))
    if data.position is None or data.position < 0:
        return error_response("not_found", "Invalid seek position", 404)
    try:
        await actions.seek(guild, data.position)
    except ValueError:
        return error_response("not_found", "Invalid seek position", 404)
    return await state.status_snapshot(guild)


@bp.post("/api/playback/volume")
@document_request(VolumeRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def playback_volume() -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    data = _parse(VolumeRequest, await request.get_json(silent=True))
    if data.volume is None:
        return error_response("not_found", "Invalid volume", 404)
    await actions.set_volume(guild, data.volume)
    return await state.status_snapshot(guild)


@bp.post("/api/layers")
@document_request(UrlRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def layer_add() -> Any:
    return await _mutate_url(actions.add_layer)


@bp.post("/api/layers/remove")
@document_request(LayerIdRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def layer_remove() -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    data = _parse(LayerIdRequest, await request.get_json(silent=True))
    if data.layer_id is None or not await actions.remove_layer(
        guild, data.layer_id
    ):
        return error_response("not_found", "Unknown layer", 404)
    return await state.status_snapshot(guild)


@bp.post("/api/layers/volume")
@document_request(LayerVolumeRequest)
@document_response(ErrorEnvelope, 404)
@validate_response(StatusSnapshot, 200)
async def layer_volume() -> Any:
    guild = _live_guild_id()
    if guild is None:
        return _no_live_session()
    data = _parse(LayerVolumeRequest, await request.get_json(silent=True))
    if data.layer_id is None or data.volume is None:
        return error_response("not_found", "Invalid layer volume", 404)
    if not await actions.set_layer_volume(guild, data.layer_id, data.volume):
        return error_response("not_found", "Unknown layer", 404)
    return await state.status_snapshot(guild)
