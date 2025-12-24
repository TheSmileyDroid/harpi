"""O executável do bot."""

from __future__ import annotations

import asyncio
import logging
import os
import threading

import discord
import discord.ext.commands as cd
from dotenv import load_dotenv

from src.cogs.ai import AiCog
from src.cogs.basic import BasicCog
from src.cogs.dice_cog import DiceCog
from src.cogs.music import MusicCog
from src.cogs.tts import TTSCog
from src.HarpiLib.HarpiBot import HarpiBot

assert load_dotenv(), "dot env not loaded"

terminal_logger = logging.StreamHandler()
# noinspection SpellCheckingInspection
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminal_logger)

background_tasks = set()
bot_instance = None


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
    logging.info("Setting up Discord bot intents...")
    intents = discord.Intents.all()

    logging.info("Creating Discord bot client...")
    client = HarpiBot(command_prefix="-", intents=intents)

    logging.info("Adding cogs to bot...")
    await client.add_cog(TTSCog(client))
    logging.info("Added TTSCog")
    await client.add_cog(MusicCog(client))
    logging.info("Added MusicCog")
    await client.add_cog(BasicCog())
    logging.info("Added BasicCog")
    await client.add_cog(DiceCog(client))
    logging.info("Added DiceCog")
    await client.add_cog(AiCog(client))
    logging.info("Added AiCog")

    logging.info("Bot creation completed")
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
            logging.info("Creating Discord bot instance...")
            # Create and run the bot
            client = loop.run_until_complete(create_bot())
            logging.info("Discord bot instance created successfully")

            # Store bot reference globally
            bot_instance = client
            logging.info("Bot instance stored globally")

            # Run the bot
            logging.info("Starting Discord bot connection...")
            loop.run_until_complete(client.start(get_token()))
        except Exception as e:
            logging.error(f"Error running Discord bot: {e}")
            import traceback

            logging.error(f"Traceback: {traceback.format_exc()}")
        finally:
            loop.close()

    token = os.getenv("DISCORD_TOKEN")
    if not token or type(token) is not str:
        raise ValueError("DISCORD_TOKEN not found in environment variables")

    if bot_instance:
        logging.info("Bot already running, skipping initialization")
        return

    # Start the bot in a daemon thread
    logging.info("Creating background thread for Discord bot...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    logging.info("Starting Discord bot thread...")
    bot_thread.start()

    logging.info("Discord bot started in background thread")


def get_bot_instance():
    """Get the global bot instance."""
    return bot_instance
