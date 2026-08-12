from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, TypeVar


if TYPE_CHECKING:
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
    return await asyncio.wait_for(asyncio.wrap_future(future), timeout=timeout)
