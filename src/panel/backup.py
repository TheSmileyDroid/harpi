"""Daily registry backups and the restore check that proves them.

The copy goes through the SQLite backup API, so the live database keeps
serving reads and writes while the backup is written.
"""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from src import alerts
from src.config import Settings

BACKUP_DIRECTORY_NAME = "backups"
BACKUP_FILE_PREFIX = "harpi-"
BACKUP_FILE_SUFFIX = ".db"
BACKUPS_KEPT = 7
BACKUP_INTERVAL_SECONDS = 24 * 60 * 60
COUNTED_TABLES = ("users", "viewers", "connection_events")
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


@dataclass(frozen=True, slots=True)
class RestoreCheck:
    matches: bool
    expected: dict[str, int]
    restored: dict[str, int]


def backup_directory(settings: Settings) -> Path:
    return Path(settings.work_dir) / BACKUP_DIRECTORY_NAME


def backup_name(moment: datetime) -> str:
    stamp = moment.astimezone(UTC).strftime(TIMESTAMP_FORMAT)
    return f"{BACKUP_FILE_PREFIX}{stamp}{BACKUP_FILE_SUFFIX}"


def backup_database(
    source: str | Path,
    directory: str | Path,
    *,
    moment: datetime | None = None,
    keep: int = BACKUPS_KEPT,
) -> Path:
    """Copy *source* through the SQLite backup API and prune old copies."""
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    moment = datetime.now(UTC) if moment is None else moment
    target = target_directory / backup_name(moment)
    _copy_database(Path(source), target)
    target.chmod(0o600)
    prune_backups(target_directory, keep=keep)
    return target


def prune_backups(
    directory: str | Path, *, keep: int = BACKUPS_KEPT
) -> list[Path]:
    backups = sorted(backup_files(Path(directory)))
    removed = backups[: max(0, len(backups) - keep)]
    for path in removed:
        path.unlink(missing_ok=True)
    return removed


def backup_files(directory: Path) -> list[Path]:
    pattern = f"{BACKUP_FILE_PREFIX}*{BACKUP_FILE_SUFFIX}"
    return [path for path in directory.glob(pattern) if path.is_file()]


def latest_backup(directory: str | Path) -> Path | None:
    backups = sorted(backup_files(Path(directory)))
    return backups[-1] if backups else None


def table_counts(path: str | Path) -> dict[str, int]:
    with sqlite3.connect(Path(path)) as connection:
        return {
            table: _row_count(connection, table) for table in COUNTED_TABLES
        }


def restore_check(
    backup: str | Path, *, expected: dict[str, int] | None = None
) -> RestoreCheck:
    """Restore *backup* into a temporary database and compare row counts."""
    backup_path = Path(backup)
    baseline = table_counts(backup_path) if expected is None else expected
    with tempfile.TemporaryDirectory(prefix="harpi-restore-") as directory:
        restored_path = Path(directory) / backup_path.name
        _copy_database(backup_path, restored_path)
        restored = table_counts(restored_path)
    return RestoreCheck(
        matches=baseline == restored,
        expected=baseline,
        restored=restored,
    )


def _copy_database(source: Path, target: Path) -> None:
    with (
        sqlite3.connect(source) as source_connection,
        sqlite3.connect(target) as target_connection,
    ):
        source_connection.backup(target_connection)


def _row_count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0]) if row is not None else 0


async def backup_once(settings: Settings) -> Path | None:
    """One backup pass plus its restore check; a failure never raises."""
    try:
        target = await asyncio.to_thread(
            backup_database,
            settings.db_path,
            backup_directory(settings),
        )
    except Exception as error:
        logger.opt(exception=True).error(f"Registry backup failed: {error}")
        alerts.notify("server_error", f"registry backup failed: {error}")
        return None
    await _verify_backup(target)
    return target


async def _verify_backup(target: Path) -> None:
    try:
        check = await asyncio.to_thread(restore_check, target)
    except Exception as error:
        logger.opt(exception=True).error(
            f"Registry restore check failed: {error}"
        )
        alerts.notify(
            "server_error", f"registry restore check failed: {error}"
        )
        return
    if check.matches:
        logger.info(f"Registry restore check passed for {target.name}")
        return
    logger.error(
        f"Registry restore check found {check.restored} in {target.name}"
    )
    alerts.notify(
        "server_error", f"registry restore check failed: {target.name}"
    )


async def run_daily(settings: Settings) -> None:
    while True:
        await backup_once(settings)
        await asyncio.sleep(BACKUP_INTERVAL_SECONDS)


def start_daily_backup(settings: Settings) -> asyncio.Task[None]:
    return asyncio.create_task(run_daily(settings), name="harpi-backup")


async def stop_daily_backup(task: asyncio.Task[None]) -> None:
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
