import asyncio
import logging

from discord.ext.commands import Bot


def run_async(bot: Bot, coro):
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result(timeout=10)
            return result
        else:
            return None
    except Exception as e:
        logging.error(f"Error fetching guilds: {e}")
        return None
