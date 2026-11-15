"""The daily job that forgets presence rows past the retention window."""

from __future__ import annotations

import asyncio

from loguru import logger

from src.config import Settings
from src.panel import periodic, state

RETENTION_INTERVAL_SECONDS = state.SECONDS_PER_DAY


async def purge_once(settings: Settings) -> None:
    """One pass; storage being unavailable is logged, never raised."""
    try:
        await state.purge_history(settings.retention_days)
    except Exception as e:
        logger.opt(exception=True).error(f"History retention failed: {e}")


async def run_daily(settings: Settings) -> None:
    while True:
        await purge_once(settings)
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)


def start_daily_purge(settings: Settings) -> asyncio.Task[None]:
    return periodic.start("harpi-retention", run_daily(settings))
