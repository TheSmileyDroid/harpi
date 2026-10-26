"""The periodic disk check behind the operator's disk-pressure alert."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

import psutil
from loguru import logger

from src import alerts
from src.config import Settings

DISK_CHECK_INTERVAL_SECONDS = 300
DISK_PRESSURE_PERCENT = 85.0


class DiskPressureWatch:
    """Alerts once when usage crosses the threshold and again after a drop."""

    def __init__(self, threshold: float = DISK_PRESSURE_PERCENT) -> None:
        self._threshold = threshold
        self._over_threshold = False

    def observe(self, percent: float, *, path: str) -> bool:
        over = percent >= self._threshold
        crossed = over and not self._over_threshold
        self._over_threshold = over
        if crossed:
            alerts.notify(
                "disk_pressure",
                f"{path} at {percent:.0f}% used "
                f"(threshold {self._threshold:.0f}%)",
            )
        return crossed


def data_volume(settings: Settings) -> Path:
    return Path(settings.db_path).resolve().parent


def disk_usage_percent(path: Path) -> float:
    return psutil.disk_usage(str(path)).percent


def check_once(
    settings: Settings,
    watch: DiskPressureWatch,
    *,
    usage: Callable[[Path], float] = disk_usage_percent,
) -> bool:
    path = data_volume(settings)
    try:
        percent = usage(path)
    except OSError as error:
        logger.error(f"Disk check failed for {path}: {error}")
        return False
    return watch.observe(percent, path=str(path))


async def run_periodically(
    settings: Settings,
    watch: DiskPressureWatch | None = None,
) -> None:
    watch = DiskPressureWatch() if watch is None else watch
    while True:
        check_once(settings, watch)
        await asyncio.sleep(DISK_CHECK_INTERVAL_SECONDS)


def start_disk_watch(settings: Settings) -> asyncio.Task[None]:
    return asyncio.create_task(run_periodically(settings), name="harpi-disk")


async def stop_disk_watch(task: asyncio.Task[None]) -> None:
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
