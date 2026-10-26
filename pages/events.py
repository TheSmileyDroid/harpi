from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import AsyncGenerator, Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from quart import Blueprint, Response
from quart_schema import document_response

from pages.api import (
    current_actor,
    current_guild_id,
    load_allowed_guild_ids,
)
from src.panel import state
from src.panel.sampler import GuildSampler, get_sampler
from src.panel.schemas import (
    SSE_EVENTS,
    Directory,
    Heartbeat,
    Position,
    Presence,
    ReloadEvent,
    SseEnvelope,
    StatusSnapshot,
)
from src.storage.registry import Actor

bp = Blueprint("events", __name__)

SHELL_ASSETS: tuple[Path, ...] = (
    Path("web/src/app.html"),
    Path("web/src/app.css"),
)

_EVENT_NAMES = {model: name for name, model in SSE_EVENTS.items()}

TICK_SECONDS = 5.0

FrameQueue = asyncio.Queue[tuple[str, BaseModel]]


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


def _visible_directory(
    directory: Directory, allowed_guilds: frozenset[int]
) -> Directory:
    return directory.model_copy(
        update={
            "guilds": [
                guild
                for guild in directory.guilds
                if int(guild.id) in allowed_guilds
            ]
        }
    )


def _opening_frames(
    sampler: GuildSampler, allowed_guilds: frozenset[int]
) -> list[str]:
    frames: list[str] = []
    snapshot = sampler.current()
    if snapshot is not None:
        frames.append(_frame(StatusSnapshot, snapshot))
    directory = sampler.directory()
    if directory is not None:
        frames.append(
            _frame(Directory, _visible_directory(directory, allowed_guilds))
        )
    return frames


async def _next_frame(
    queued: FrameQueue, timeout: float, allowed_guilds: frozenset[int]
) -> str | None:
    with contextlib.suppress(TimeoutError):
        name, payload = await asyncio.wait_for(queued.get(), timeout)
        if isinstance(payload, Directory):
            payload = _visible_directory(payload, allowed_guilds)
        return _frame(SSE_EVENTS[name], payload)
    return None


async def _periodic_frames(
    sampler: GuildSampler,
    guild_id: int | None,
    actor: Actor | None,
    previous_presence: Presence,
) -> tuple[list[str], Presence]:
    frames: list[str] = []
    presence = previous_presence
    if sampler.healthy:
        frames.append(_frame(Position, sampler.position()))
        presence = await state.presence(guild_id, actor)
        if presence != previous_presence:
            frames.append(_frame(Presence, presence))
    frames.append(_frame(Heartbeat, Heartbeat()))
    return frames, presence


def _reload_frame(
    previous: dict[str, float],
) -> tuple[str | None, dict[str, float]]:
    current = _snapshot()
    if current == previous:
        return None, previous
    return _frame(ReloadEvent, {"scope": "shell"}), current


async def _stream(
    guild_id: int | None,
    actor: Actor | None,
    allowed_guilds: frozenset[int],
) -> AsyncGenerator[str, None]:
    resolved = state.resolve_guild_id(guild_id, allowed_guilds)
    sampler = get_sampler(resolved)
    queued = await sampler.subscribe()
    try:
        yield ": connected\n\n"
        for frame in _opening_frames(sampler, allowed_guilds):
            yield frame
        previous_presence = await state.presence(resolved, actor)
        yield _frame(Presence, previous_presence)
        previous_shell = _snapshot()
        deadline = time.monotonic() + TICK_SECONDS
        while True:
            timeout = max(0.0, deadline - time.monotonic())
            queued_frame = await _next_frame(queued, timeout, allowed_guilds)
            if queued_frame is not None:
                yield queued_frame
            if time.monotonic() < deadline:
                continue
            deadline = time.monotonic() + TICK_SECONDS
            frames, previous_presence = await _periodic_frames(
                sampler, resolved, actor, previous_presence
            )
            for frame in frames:
                yield frame
            reload_frame, previous_shell = _reload_frame(previous_shell)
            if reload_frame is not None:
                yield reload_frame
    finally:
        sampler.unsubscribe(queued)


@bp.get("/api/events")
@document_response(SseEnvelope, 200)
async def events():
    allowed_guilds = await load_allowed_guild_ids()
    return Response(
        _stream(current_guild_id(), current_actor(), allowed_guilds),
        mimetype="text/event-stream",
    )
