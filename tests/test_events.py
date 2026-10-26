"""Tests for the panel SSE channel under /api/events."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import pytest

from pages import events
from src.panel import rate_limit
from src.panel.schemas import (
    Directory,
    Heartbeat,
    Presence,
    Position,
    StatusSnapshot,
)

from app import app as quart_app

CONNECTED: dict[str, Any] = {
    "bot": {"online": True},
    "guild_id": None,
    "connection": {"connected": False, "channel_id": None},
    "playback": None,
}
EMPTY_PRESENCE = Presence(guild_id=None, viewers=[], last_connection=None)
EMPTY_DIRECTORY = Directory(guild_id=None, guilds=[], channels=[])


class FakeSampler:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        self.sample = StatusSnapshot.model_validate(CONNECTED)
        self.directory_value = EMPTY_DIRECTORY
        self.position_value = Position(progress=0.0)
        self.healthy = True
        self.unsubscribed: list[asyncio.Queue[tuple[str, Any]]] = []

    async def subscribe(self) -> asyncio.Queue[tuple[str, Any]]:
        return self.queue

    def unsubscribe(self, queue: asyncio.Queue[tuple[str, Any]]) -> None:
        self.unsubscribed.append(queue)

    def current(self) -> StatusSnapshot:
        return self.sample

    def directory(self) -> Directory:
        return self.directory_value

    def position(self) -> Position:
        return self.position_value


def _wire(
    monkeypatch,
    sampler: FakeSampler,
    presence: Presence = EMPTY_PRESENCE,
) -> None:
    monkeypatch.setattr(events, "get_sampler", lambda guild_id: sampler)
    monkeypatch.setattr(
        events.state,
        "resolve_guild_id",
        lambda guild_id, allowed: guild_id,
    )

    async def fake_presence(guild_id: int | None, actor: Any) -> Presence:
        del guild_id, actor
        return presence

    monkeypatch.setattr(events.state, "presence", fake_presence)
    monkeypatch.setattr(events, "_snapshot", lambda: {})


async def _open(monkeypatch, sampler: FakeSampler):
    _wire(monkeypatch, sampler)
    stream = events._stream(None, None, frozenset())
    assert await anext(stream) == ": connected\n\n"
    return stream


def test_events_route_is_registered():
    paths = {rule.rule for rule in quart_app.url_map.iter_rules()}

    assert "/api/events" in paths


async def test_stream_opens_with_status_directory_and_presence(monkeypatch):
    sampler = FakeSampler()
    stream = await _open(monkeypatch, sampler)

    assert await anext(stream) == (
        f"event: status\ndata: {json.dumps(CONNECTED)}\n\n"
    )
    assert await anext(stream) == (
        f"event: directory\ndata: {json.dumps(EMPTY_DIRECTORY.model_dump())}\n\n"
    )
    presence = await anext(stream)
    assert presence == (
        f"event: presence\ndata: {json.dumps(EMPTY_PRESENCE.model_dump())}\n\n"
    )
    await stream.aclose()


async def test_a_changed_status_reaches_an_open_stream(monkeypatch):
    sampler = FakeSampler()
    stream = await _open(monkeypatch, sampler)
    for _ in range(2):
        await anext(stream)
    await anext(stream)

    changed = StatusSnapshot.model_validate({
        **CONNECTED,
        "bot": {"online": False},
    })
    sampler.queue.put_nowait(("status", changed))

    frame = await asyncio.wait_for(anext(stream), 1)

    assert frame == (
        f"event: status\ndata: {json.dumps(changed.model_dump())}\n\n"
    )
    await stream.aclose()


async def test_the_tick_sends_position_and_heartbeat(monkeypatch):
    sampler = FakeSampler()
    sampler.position_value = Position(progress=12.5)
    monkeypatch.setattr(events, "TICK_SECONDS", 0)
    stream = await _open(monkeypatch, sampler)
    for _ in range(3):
        await anext(stream)

    position = await asyncio.wait_for(anext(stream), 1)
    heartbeat = await asyncio.wait_for(anext(stream), 1)

    assert position == (
        f"event: position\ndata: {json.dumps({'progress': 12.5})}\n\n"
    )
    assert heartbeat == (
        f"event: heartbeat\ndata: {json.dumps(Heartbeat().model_dump())}\n\n"
    )
    await stream.aclose()


async def test_an_unhealthy_sampler_keeps_the_link_alive(monkeypatch):
    sampler = FakeSampler()
    sampler.healthy = False
    monkeypatch.setattr(events, "TICK_SECONDS", 0)
    stream = await _open(monkeypatch, sampler)
    for _ in range(3):
        await anext(stream)

    frame = await asyncio.wait_for(anext(stream), 1)

    assert frame.startswith("event: heartbeat\ndata:")
    await stream.aclose()


async def test_stream_emits_reload_when_shell_assets_move(monkeypatch):
    snapshots = iter([{"app.html": 1.0}, {"app.html": 2.0}, {"app.html": 2.0}])
    sampler = FakeSampler()
    monkeypatch.setattr(events, "TICK_SECONDS", 0)
    _wire(monkeypatch, sampler)
    monkeypatch.setattr(events, "_snapshot", lambda: next(snapshots))

    stream = events._stream(None, None, frozenset())
    assert await anext(stream) == ": connected\n\n"
    for _ in range(3):
        await anext(stream)

    frames = [await asyncio.wait_for(anext(stream), 1) for _ in range(3)]

    assert any(frame.startswith("event: reload\n") for frame in frames)
    await stream.aclose()


async def test_closing_the_stream_unsubscribes(monkeypatch):
    sampler = FakeSampler()
    stream = await _open(monkeypatch, sampler)

    await stream.aclose()

    assert sampler.unsubscribed == [sampler.queue]


async def test_closing_the_stream_frees_its_slot(monkeypatch):
    sampler = FakeSampler()
    _wire(monkeypatch, sampler)
    slots = rate_limit.StreamSlots(per_user=1, per_guild=1)
    slot = slots.acquire("555", 1)
    assert slot is not None
    stream = events._stream(1, None, frozenset({1}), slot)
    assert await anext(stream) == ": connected\n\n"

    await stream.aclose()

    assert slots.acquire("555", 1) is not None


async def test_a_failing_stream_frees_its_slot(monkeypatch):
    sampler = FakeSampler()
    _wire(monkeypatch, sampler)

    async def explode(guild_id: int | None, actor: Any) -> Presence:
        raise RuntimeError("presence exploded")

    monkeypatch.setattr(events.state, "presence", explode)
    slots = rate_limit.StreamSlots(per_user=1, per_guild=1)
    slot = slots.acquire("555", 1)
    assert slot is not None
    stream = events._stream(1, None, frozenset({1}), slot)
    assert await anext(stream) == ": connected\n\n"
    for _ in range(2):
        await anext(stream)

    with pytest.raises(RuntimeError, match="presence exploded"):
        await anext(stream)

    assert slots.acquire("555", 1) is not None


def test_snapshot_walks_directories(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    asset = nested / "shell.css"
    asset.write_text("x")

    snapshot = events._snapshot((tmp_path,))

    assert str(asset) in snapshot


def test_snapshot_ignores_missing_paths(tmp_path):
    assert events._snapshot((tmp_path / "absent",)) == {}


def test_snapshot_reports_a_rewritten_asset(tmp_path):
    asset = tmp_path / "app.html"
    asset.write_text("one")
    before = events._snapshot((asset,))

    newer = before[str(asset)] + 1
    os.utime(asset, (newer, newer))

    assert events._snapshot((asset,))[str(asset)] == newer
