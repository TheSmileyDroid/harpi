"""Start and stop for the panel's periodic jobs."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


def start(name: str, routine: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
    """Run *routine* for the life of the process, under *name*."""
    return asyncio.create_task(routine, name=name)


async def stop_all(tasks: list[asyncio.Task[None]]) -> None:
    """Cancel every task and wait for each one to unwind.

    Cancellation is the expected outcome; the first real failure propagates
    once every task has been awaited.
    """
    for task in tasks:
        task.cancel()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failures = [
        result
        for result in results
        if isinstance(result, BaseException)
        and not isinstance(result, asyncio.CancelledError)
    ]
    if failures:
        raise failures[0]
