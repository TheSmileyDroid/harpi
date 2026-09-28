from __future__ import annotations

import hmac
from typing import Any

from quart import Blueprint, Response, jsonify, request, session

from src.config import Settings
from src.panel import state

bp = Blueprint("api", __name__)


def error_response(code: str, message: str, status: int) -> Response:
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    return response


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
