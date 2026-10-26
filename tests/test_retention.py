"""The daily retention job keeps running when storage is missing or broken."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import cast

from src.config import Settings
from src.panel import retention, state
from src.storage import clear_registry, init_registry
from src.storage.registry import PurgedHistory, Registry

NOW = 1_700_000_000


class BrokenRegistry:
    async def purge_history(self, *, before: int) -> PurgedHistory:
        raise RuntimeError("database is locked")


class RecordingRegistry:
    def __init__(self) -> None:
        self.cutoffs: list[int] = []

    async def purge_history(self, *, before: int) -> PurgedHistory:
        self.cutoffs.append(before)
        return PurgedHistory(viewers=0, connection_events=0)


def _settings() -> Settings:
    return replace(Settings.from_env(), retention_days=30)


async def test_purge_once_is_a_no_op_without_storage():
    clear_registry()

    await retention.purge_once(_settings())


async def test_purge_once_swallows_a_storage_failure():
    init_registry(cast(Registry, BrokenRegistry()))
    try:
        await retention.purge_once(_settings())
    finally:
        clear_registry()


async def test_start_daily_purge_purges_at_once_and_stop_cancels():
    registry = RecordingRegistry()
    init_registry(cast(Registry, registry))
    try:
        task = retention.start_daily_purge(_settings())
        for _ in range(3):
            await asyncio.sleep(0)
        await retention.stop_daily_purge(task)
    finally:
        clear_registry()

    assert len(registry.cutoffs) == 1
    assert task.cancelled()


def test_retention_cutoff_subtracts_the_configured_days():
    assert (
        state.retention_cutoff(30, now=NOW) == NOW - 30 * state.SECONDS_PER_DAY
    )
