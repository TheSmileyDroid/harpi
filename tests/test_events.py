"""Tests for the dev-loop SSE channel under /api/events."""

from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

from pages import events

from app import app as quart_app

Status = dict[str, Any]
Provider = Callable[[int | None], Awaitable[Status]]


def _scripted(values: list[Status]) -> Provider:
    remaining = list(values)
    held = {"last": values[0]}

    async def provider(guild_id: int | None) -> Status:
        del guild_id
        if remaining:
            held["last"] = remaining.pop(0)
        return held["last"]

    return provider


CONNECTED: Status = {
    "bot": {"online": True},
    "guild_id": None,
    "connection": {"connected": False, "channel_id": None},
    "playback": None,
}


def test_events_route_is_registered():
    paths = {rule.rule for rule in quart_app.url_map.iter_rules()}

    assert "/api/events" in paths


async def test_stream_opens_with_connected_then_a_status_snapshot(monkeypatch):
    monkeypatch.setattr(events, "POLL_SECONDS", 0)
    monkeypatch.setattr(events, "_snapshot", lambda: {})
    monkeypatch.setattr(
        events.state, "status_snapshot", _scripted([CONNECTED])
    )

    stream = events._stream(None)
    assert await anext(stream) == ": connected\n\n"
    frame = await anext(stream)

    assert frame == f"event: status\ndata: {json.dumps(CONNECTED)}\n\n"
    await stream.aclose()


async def test_stream_emits_status_when_the_snapshot_changes(monkeypatch):
    changed = {**CONNECTED, "bot": {"online": False}}
    monkeypatch.setattr(events, "POLL_SECONDS", 0)
    monkeypatch.setattr(events, "_snapshot", lambda: {})
    monkeypatch.setattr(
        events.state, "status_snapshot", _scripted([CONNECTED, changed])
    )

    stream = events._stream(None)
    assert await anext(stream) == ": connected\n\n"
    assert await anext(stream) == (
        f"event: status\ndata: {json.dumps(CONNECTED)}\n\n"
    )
    frame = await anext(stream)

    assert frame == f"event: status\ndata: {json.dumps(changed)}\n\n"
    await stream.aclose()


async def test_stream_emits_reload_when_shell_assets_move(monkeypatch):
    snapshots = iter([{"app.html": 1.0}, {"app.html": 2.0}, {"app.html": 2.0}])
    monkeypatch.setattr(events, "POLL_SECONDS", 0)
    monkeypatch.setattr(events, "_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(
        events.state, "status_snapshot", _scripted([CONNECTED])
    )

    stream = events._stream(None)
    assert await anext(stream) == ": connected\n\n"
    assert await anext(stream) == (
        f"event: status\ndata: {json.dumps(CONNECTED)}\n\n"
    )
    frame = await anext(stream)

    assert frame == 'event: reload\ndata: {"scope": "shell"}\n\n'
    await stream.aclose()


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
