"""O executável do bot."""

from __future__ import annotations

import asyncio
import os
import threading

import discord
from dotenv import load_dotenv
from loguru import logger

from src.cogs.basic import BasicCog
from src.cogs.dice_cog import DiceCog
from src.cogs.music import MusicCog
from src.cogs.test import TestCog
from src.cogs.tts import TTSCog
from src.HarpiLib.HarpiBot import HarpiBot

assert load_dotenv(), "dot env not loaded"

background_tasks = set()
bot_instance: HarpiBot | None = None


def get_token() -> str:
    """Obtém o token do bot.

    Raises:
        ValueError: Se o token não estiver definido.

    Returns:
        str: O token do bot.

    """
    token = os.getenv("DISCORD_TOKEN")

    if token:
        return token

    raise ValueError


async def create_bot() -> HarpiBot:
    """Start the bot.

    Returns
    -------
    HarpiBot
        Bot instance

    """
    logger.info("Setting up Discord bot intents...")
    intents = discord.Intents.all()

    logger.info("Creating Discord bot client...")
    prefix = os.getenv("PREFIX") or "-"
    client = HarpiBot(command_prefix=prefix, intents=intents)

    logger.info("Adding cogs to bot...")
    await client.add_cog(TTSCog(client))
    logger.info("Added TTSCog")
    await client.add_cog(MusicCog(client))
    logger.info("Added MusicCog")
    await client.add_cog(BasicCog())
    logger.info("Added BasicCog")
    await client.add_cog(DiceCog(client))
    logger.info("Added DiceCog")
    await client.add_cog(TestCog(client))
    logger.info("Added TestCog")

    logger.info("Bot creation completed")
    return client


def run_bot_in_background():
    """Run the Discord bot in a background thread."""
    global bot_instance

    def run_bot():
        """Function to run in the background thread."""
        global bot_instance
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            logger.info("Creating Discord bot instance...")
            # Create and run the bot
            client = loop.run_until_complete(create_bot())
            logger.info("Discord bot instance created successfully")

            # Store bot reference globally
            bot_instance = client
            logger.info("Bot instance stored globally")

            # Run the bot
            logger.info("Starting Discord bot connection...")
            loop.run_until_complete(client.start(get_token()))
        except Exception as e:
            logger.error(f"Error running Discord bot: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            loop.close()

    token = os.getenv("DISCORD_TOKEN")
    if not token or type(token) is not str:
        raise ValueError("DISCORD_TOKEN not found in environment variables")

    if bot_instance:
        logger.info("Bot already running, skipping initialization")
        return

    # Start the bot in a daemon thread
    logger.info("Creating background thread for Discord bot...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    logger.info("Starting Discord bot thread...")
    bot_thread.start()

    logger.info("Discord bot started in background thread")


def get_bot_instance() -> HarpiBot:
    """Get the global bot instance."""
    assert bot_instance, "Bot does not exists!"
    return bot_instance
