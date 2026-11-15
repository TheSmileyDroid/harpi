from __future__ import annotations

import asyncio

import pytest

from src.panel import periodic


async def test_stop_all_cancels_every_task():
    started: list[str] = []

    async def forever(name: str) -> None:
        started.append(name)
        await asyncio.Event().wait()

    tasks = [
        periodic.start("first", forever("first")),
        periodic.start("second", forever("second")),
    ]
    for _ in range(3):
        await asyncio.sleep(0)

    await periodic.stop_all(tasks)

    assert started == ["first", "second"]
    assert all(task.cancelled() for task in tasks)


async def test_stop_all_propagates_a_real_failure():
    async def boom() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("job explodiu")

    task = periodic.start("boom", boom())
    for _ in range(3):
        await asyncio.sleep(0)

    with pytest.raises(RuntimeError, match="job explodiu"):
        await periodic.stop_all([task])
