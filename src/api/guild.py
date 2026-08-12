from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Guild

from src.api.deps import get_bot, run_on_bot_loop

if TYPE_CHECKING:
    from discord.ext.commands import Bot

guilds: list[Guild] | None = None


async def _fetch_guilds(bot: "Bot") -> list[Guild]:
    """Fetch the guilds the bot can see (runs on the bot's event loop)."""
    return [guild async for guild in bot.fetch_guilds(limit=150)]


async def _get_guilds() -> list[Guild]:
    """Load guilds the bot is connected to."""
    global guilds
    if guilds is not None:
        return guilds
    bot = get_bot()
    if not bot:
        return []
    guilds = await run_on_bot_loop(_fetch_guilds(bot)) or []
    return guilds
