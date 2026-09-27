"""Tests for the dev-loop SSE channel under /api/events."""

from __future__ import annotations

import os

from app import app as quart_app
from pages import events


def test_events_route_is_registered():
    paths = {rule.rule for rule in quart_app.url_map.iter_rules()}

    assert "/api/events" in paths


def test_events_returns_an_event_stream():
    response = events.events()

    assert response.content_type.startswith("text/event-stream")


async def test_shell_changes_emits_a_reload_when_assets_move(monkeypatch):
    snapshots = iter([{"app.html": 1.0}, {"app.html": 2.0}])
    monkeypatch.setattr(events, "POLL_SECONDS", 0)
    monkeypatch.setattr(events, "_snapshot", lambda: next(snapshots))

    stream = events._shell_changes()
    assert await anext(stream) == ": connected\n\n"
    frame = await anext(stream)

    assert frame == 'event: reload\ndata: {"scope": "shell"}\n\n'
    await stream.aclose()


async def test_shell_changes_stays_quiet_when_assets_hold_still(monkeypatch):
    monkeypatch.setattr(events, "POLL_SECONDS", 0)
    monkeypatch.setattr(events, "_snapshot", lambda: {"app.html": 1.0})

    stream = events._shell_changes()
    assert await anext(stream) == ": connected\n\n"
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
