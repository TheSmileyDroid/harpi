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
    error_response,
    load_allowed_guild_ids,
)
from src.panel import state
from src.panel.rate_limit import (
    STREAM_RETRY_AFTER_SECONDS,
    StreamSlot,
    StreamSlots,
)
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

STREAM_SLOTS = StreamSlots()

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
    queued: FrameQueue, timeout: float
) -> tuple[str, BaseModel] | None:
    with contextlib.suppress(TimeoutError):
        return await asyncio.wait_for(queued.get(), timeout)
    return None


async def _current_allowed(
    actor: Actor | None, fallback: frozenset[int]
) -> frozenset[int]:
    if actor is None:
        return fallback
    return await state.user_guild_ids(actor.id)


async def _visible_frame(
    name: str,
    payload: BaseModel,
    actor: Actor | None,
    allowed_guilds: frozenset[int],
) -> str:
    if isinstance(payload, Directory):
        allowed_guilds = await _current_allowed(actor, allowed_guilds)
        payload = _visible_directory(payload, allowed_guilds)
    return _frame(SSE_EVENTS[name], payload)


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


async def _advance(
    queued: FrameQueue,
    sampler: GuildSampler,
    guild_id: int | None,
    actor: Actor | None,
    presence: Presence,
    shell: dict[str, float],
    allowed_guilds: frozenset[int],
    deadline: float,
) -> tuple[float, Presence, dict[str, float], list[str]]:
    frames: list[str] = []
    timeout = max(0.0, deadline - time.monotonic())
    queued_item = await _next_frame(queued, timeout)
    if queued_item is not None:
        frames.append(
            await _visible_frame(*queued_item, actor, allowed_guilds)
        )
    if time.monotonic() < deadline:
        return deadline, presence, shell, frames
    deadline = time.monotonic() + TICK_SECONDS
    periodic, presence = await _periodic_frames(
        sampler, guild_id, actor, presence
    )
    frames.extend(periodic)
    reload_frame, shell = _reload_frame(shell)
    if reload_frame is not None:
        frames.append(reload_frame)
    return deadline, presence, shell, frames


async def _steady_frames(
    queued: FrameQueue,
    sampler: GuildSampler,
    guild_id: int | None,
    actor: Actor | None,
    presence: Presence,
    allowed_guilds: frozenset[int],
) -> AsyncGenerator[str, None]:
    shell = _snapshot()
    deadline = time.monotonic() + TICK_SECONDS
    while True:
        allowed_guilds = await _current_allowed(actor, allowed_guilds)
        deadline, presence, shell, frames = await _advance(
            queued,
            sampler,
            guild_id,
            actor,
            presence,
            shell,
            allowed_guilds,
            deadline,
        )
        for frame in frames:
            yield frame


async def _stream(
    guild_id: int | None,
    actor: Actor | None,
    allowed_guilds: frozenset[int],
    slot: StreamSlot | None = None,
) -> AsyncGenerator[str, None]:
    resolved = state.resolve_guild_id(guild_id, allowed_guilds)
    sampler = get_sampler(resolved)
    queued = await sampler.subscribe()
    try:
        yield ": connected\n\n"
        for frame in _opening_frames(sampler, allowed_guilds):
            yield frame
        presence = await state.presence(resolved, actor)
        yield _frame(Presence, presence)
        async for frame in _steady_frames(
            queued, sampler, resolved, actor, presence, allowed_guilds
        ):
            yield frame
    finally:
        sampler.unsubscribe(queued)
        if slot is not None:
            slot.release()


@bp.get("/api/events")
@document_response(SseEnvelope, 200)
async def events():
    allowed_guilds = await load_allowed_guild_ids()
    actor = current_actor()
    guild_id = state.resolve_guild_id(current_guild_id(), allowed_guilds)
    slot = STREAM_SLOTS.acquire(
        actor.id if actor is not None else "", guild_id
    )
    if slot is None:
        response = error_response(
            "too_many_requests", "Too many live streams", 429
        )
        response.headers["Retry-After"] = str(STREAM_RETRY_AFTER_SECONDS)
        return response
    return Response(
        _stream(current_guild_id(), actor, allowed_guilds, slot),
        mimetype="text/event-stream",
    )
