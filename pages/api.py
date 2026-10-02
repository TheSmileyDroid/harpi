from __future__ import annotations

import hmac
from typing import Any

from quart import Blueprint, Response, jsonify, request, session

from src.config import Settings
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


def current_guild_id() -> int | None:
    raw = session.get("guild_id")
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


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
