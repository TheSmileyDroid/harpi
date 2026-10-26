"""Registry backups stay readable, bounded, and provably restorable."""

from __future__ import annotations

import asyncio
import stat
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from src.config import Settings
from src.panel import backup
from src.storage.database import Database
from src.storage.registry import Actor, Place, SqliteRegistry

ALICE = Actor(id="555", username="alice", display_name="Alice")
VOICE = Place(
    guild_id="7",
    guild_name="Alpha Guild",
    channel_id="42",
    channel_name="Voice Channel",
)
NOW = 1_700_000_000
MOMENT = datetime(2026, 10, 26, 12, 0, 0, tzinfo=UTC)


async def _seeded(tmp_path: Path) -> Database:
    database = Database(tmp_path / "harpi.db")
    await database.open()
    registry = SqliteRegistry(database)
    await registry.select(ALICE, VOICE, now=NOW)
    await registry.record_connection(ALICE, VOICE, "connect", now=NOW)
    await registry.record_user_guilds(ALICE, ["7"], now=NOW)
    return database


async def test_a_backup_is_readable_with_the_same_row_counts(tmp_path):
    database = await _seeded(tmp_path)
    try:
        target = backup.backup_database(
            database.path, tmp_path / "backups", moment=MOMENT
        )

        assert target.exists()
        assert backup.table_counts(target) == backup.table_counts(
            database.path
        )
        assert backup.table_counts(target)["users"] == 1
    finally:
        await database.close()


async def test_a_backup_is_owner_only(tmp_path):
    database = await _seeded(tmp_path)
    try:
        target = backup.backup_database(
            database.path, tmp_path / "backups", moment=MOMENT
        )
    finally:
        await database.close()

    assert stat.S_IMODE(target.stat().st_mode) == 0o600


async def test_the_restore_check_matches_the_live_counts(tmp_path):
    database = await _seeded(tmp_path)
    try:
        target = backup.backup_database(
            database.path, tmp_path / "backups", moment=MOMENT
        )
        check = backup.restore_check(
            target, expected=backup.table_counts(database.path)
        )
    finally:
        await database.close()

    assert check.matches is True
    assert check.restored == check.expected


async def test_the_restore_check_detects_a_mismatch(tmp_path):
    database = await _seeded(tmp_path)
    registry = SqliteRegistry(database)
    try:
        target = backup.backup_database(
            database.path, tmp_path / "backups", moment=MOMENT
        )
        await registry.sign_in(Actor(id="999", username="late"))
        check = backup.restore_check(
            target, expected=backup.table_counts(database.path)
        )
    finally:
        await database.close()

    assert check.matches is False
    assert check.restored["users"] == 1
    assert check.expected["users"] == 2


async def test_retention_keeps_only_the_newest_backups(tmp_path):
    database = await _seeded(tmp_path)
    directory = tmp_path / "backups"
    try:
        for second in range(5):
            backup.backup_database(
                database.path,
                directory,
                moment=MOMENT.replace(second=second),
                keep=3,
            )
    finally:
        await database.close()

    kept = sorted(path.name for path in directory.iterdir())
    assert kept == [
        "harpi-20261026T120002Z.db",
        "harpi-20261026T120003Z.db",
        "harpi-20261026T120004Z.db",
    ]
    assert backup.latest_backup(directory) == directory / kept[-1]


async def test_backup_once_writes_under_the_work_directory(tmp_path):
    database = await _seeded(tmp_path)
    settings = replace(
        Settings.from_env(),
        db_path=str(database.path),
        work_dir=str(tmp_path / "work"),
    )
    try:
        target = await backup.backup_once(settings)
    finally:
        await database.close()

    assert target is not None
    assert target.parent == tmp_path / "work" / "backups"
    assert target.exists()


async def test_backup_once_swallows_a_storage_failure(tmp_path):
    settings = replace(
        Settings.from_env(),
        db_path=str(tmp_path),
        work_dir=str(tmp_path / "work"),
    )

    assert await backup.backup_once(settings) is None


async def test_start_daily_backup_runs_at_once_and_stop_cancels(
    monkeypatch, tmp_path
):
    calls: list[Settings] = []

    async def record(settings: Settings) -> Path | None:
        calls.append(settings)
        return None

    monkeypatch.setattr(backup, "backup_once", record)
    settings = replace(
        Settings.from_env(),
        db_path=str(tmp_path / "harpi.db"),
        work_dir=str(tmp_path / "work"),
    )

    task = backup.start_daily_backup(settings)
    for _ in range(3):
        await asyncio.sleep(0)
    await backup.stop_daily_backup(task)

    assert len(calls) == 1
    assert task.cancelled()
