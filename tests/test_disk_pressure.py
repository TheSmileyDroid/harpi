"""Disk pressure alerts once per threshold crossing, not per check."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src import alerts
from src.config import Settings
from src.panel import disk_pressure


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    messages: list[tuple[str, str]] = []

    def record(kind: str, detail: str = "") -> None:
        messages.append((kind, detail))

    monkeypatch.setattr(alerts, "notify", record)
    return messages


def test_crossing_the_threshold_alerts_once(sent):
    watch = disk_pressure.DiskPressureWatch(threshold=85.0)

    assert watch.observe(84.0, path="/data") is False
    assert watch.observe(85.0, path="/data") is True
    assert watch.observe(93.0, path="/data") is False
    assert [kind for kind, _ in sent] == ["disk_pressure"]


def test_a_drop_below_the_threshold_rearms_the_alert(sent):
    watch = disk_pressure.DiskPressureWatch(threshold=85.0)
    watch.observe(90.0, path="/data")
    watch.observe(40.0, path="/data")

    assert watch.observe(90.0, path="/data") is True
    assert len(sent) == 2


def test_check_once_reads_the_data_volume(tmp_path, sent):
    settings = replace(
        Settings.from_env(),
        db_path=str(tmp_path / "data" / "harpi.db"),
    )
    watch = disk_pressure.DiskPressureWatch(threshold=80.0)

    crossed = disk_pressure.check_once(
        settings, watch, usage=lambda path: 91.0
    )

    assert crossed is True
    assert sent[0][0] == "disk_pressure"
    assert str(tmp_path / "data") in sent[0][1]


def test_check_once_swallows_an_unreadable_volume(tmp_path, sent):
    settings = replace(
        Settings.from_env(),
        db_path=str(tmp_path / "data" / "harpi.db"),
    )

    def unavailable(path: Path) -> float:
        raise OSError("no such volume")

    crossed = disk_pressure.check_once(
        settings,
        disk_pressure.DiskPressureWatch(),
        usage=unavailable,
    )

    assert crossed is False
    assert sent == []
