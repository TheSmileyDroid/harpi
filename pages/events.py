from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator, Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from quart import Blueprint, Response
from quart_schema import document_response

from pages.api import current_actor, current_guild_id
from src.panel import state
from src.panel.schemas import (
    SSE_EVENTS,
    Presence,
    ReloadEvent,
    SseEnvelope,
    StatusSnapshot,
)
from src.storage.registry import Actor

_EVENT_NAMES = {model: name for name, model in SSE_EVENTS.items()}

bp = Blueprint("events", __name__)

SHELL_ASSETS: tuple[Path, ...] = (
    Path("web/src/app.html"),
    Path("web/src/app.css"),
)

POLL_SECONDS = 0.5
HEARTBEAT_SECONDS = 5.0


def _snapshot(assets: Iterable[Path] = SHELL_ASSETS) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for asset in assets:
        if asset.is_dir():
            for file in asset.rglob("*"):
                if file.is_file():
                    snapshot[str(file)] = file.stat().st_mtime
        elif asset.is_file():
            snapshot[str(asset)] = asset.stat().st_mtime
    return snapshot


def _frame(model: type[BaseModel], data: Any) -> str:
    payload = data.model_dump() if isinstance(data, BaseModel) else data
    return f"event: {_EVENT_NAMES[model]}\ndata: {json.dumps(payload)}\n\n"


async def _stream(
    guild_id: int | None, actor: Actor | None
) -> AsyncGenerator[str, None]:
    previous_shell = _snapshot()
    previous_status = await state.status_snapshot(guild_id)
    previous_presence = await state.presence(guild_id, actor)
    last_presence = time.monotonic()
    yield ": connected\n\n"
    yield _frame(StatusSnapshot, previous_status)
    yield _frame(Presence, previous_presence)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        current_shell = _snapshot()
        if current_shell != previous_shell:
            previous_shell = current_shell
            yield _frame(ReloadEvent, {"scope": "shell"})
        current_status = await state.status_snapshot(guild_id)
        if current_status != previous_status:
            previous_status = current_status
            yield _frame(StatusSnapshot, current_status)
        if time.monotonic() - last_presence >= HEARTBEAT_SECONDS:
            last_presence = time.monotonic()
            current_presence = await state.presence(guild_id, actor)
            if current_presence != previous_presence:
                previous_presence = current_presence
                yield _frame(Presence, current_presence)


@bp.get("/api/events")
@document_response(SseEnvelope, 200)
def events():
    return Response(
        _stream(current_guild_id(), current_actor()),
        mimetype="text/event-stream",
    )
