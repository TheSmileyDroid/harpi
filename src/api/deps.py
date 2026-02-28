"""Dependency accessors for API route handlers.

Provides a clean interface for route handlers to access the bot and API
without importing directly from the Discord bot lifecycle module.

Thread safety
-------------
``run_on_bot_loop`` schedules a coroutine on the **Discord bot's** event
loop (which runs in a background thread) and awaits the result from the
calling event loop (Quart).  This is the correct way to call discord.py
APIs (e.g. ``channel.connect()``, ``voice_client.disconnect()``) from
Quart handlers, which run on a different event loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, TypeVar

from loguru import logger

if TYPE_CHECKING:
    from src.harpi_lib.api import HarpiAPI
    from src.harpi_lib.harpi_bot import HarpiBot

_bot_ref: HarpiBot | None = None

_T = TypeVar("_T")


def init_bot(bot: HarpiBot) -> None:
    """Store the bot reference. Called once during app startup."""
    global _bot_ref
    _bot_ref = bot


def get_bot() -> HarpiBot:
    """Get the bot instance. Raises if bot hasn't been initialized."""
    assert _bot_ref is not None, "Bot not initialized"
    return _bot_ref


def get_api() -> HarpiAPI:
    """Get the HarpiAPI instance from the bot."""
    return get_bot().api


async def run_on_bot_loop(
    coro: Coroutine[Any, Any, _T], timeout: float = 30.0
) -> _T:
    """Schedule *coro* on the bot's event loop and await the result.

    Use this whenever a Quart handler needs to call a coroutine that
    touches discord.py internals (voice connect/disconnect, etc.).

    Raises:
        TimeoutError: If the coroutine does not complete within *timeout* seconds.
        RuntimeError: If the bot loop is unavailable.
    """
    bot = get_bot()
    loop = bot.loop
    if loop is None or loop.is_closed():
        raise RuntimeError("Bot event loop is closed or unavailable")

    future = asyncio.run_coroutine_threadsafe(coro, loop)
    # Await the concurrent.futures.Future from the current (Quart) loop
    return await asyncio.wrap_future(future)
