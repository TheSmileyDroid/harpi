from __future__ import annotations

import asyncio
import os
import threading

import discord
from loguru import logger

from src.cogs.basic import GeneralCog
from src.cogs.dice_cog import DiceCog
from src.cogs.music import MusicCog
from src.cogs.tts import TTSCog
from src.api.deps import init_bot
from src.harpi_lib.harpi_bot import HarpiBot


def get_token() -> str:
    token = os.getenv("DISCORD_TOKEN")

    if token:
        return token

    raise ValueError("DISCORD_TOKEN not found in environment variables")


async def create_bot() -> HarpiBot:
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
    await client.add_cog(GeneralCog())
    logger.info("Added BasicCog")
    await client.add_cog(DiceCog(client))
    logger.info("Added DiceCog")

    logger.info("Registering session manager listeners...")
    client.add_listener(client.sessions.on_voice_state_update)
    logger.info("Registered on_voice_state_update listener")

    logger.info("Bot creation completed")
    return client


def run_bot_in_background() -> None:
    """Run the Discord bot in a background thread."""

    def run_bot():
        """Function to run in the background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            logger.info("Creating Discord bot instance...")
            client = loop.run_until_complete(create_bot())
            logger.info("Discord bot instance created successfully")

            init_bot(client)
            logger.info("Bot instance stored in deps")

            logger.info("Starting Discord bot connection...")
            loop.run_until_complete(client.start(get_token()))
        except Exception as e:
            logger.opt(exception=True).error(f"Error running Discord bot: {e}")
        finally:
            loop.close()

    token = os.getenv("DISCORD_TOKEN")
    if not token or type(token) is not str:
        raise ValueError("DISCORD_TOKEN not found in environment variables")

    from src.api.deps import get_bot

    try:
        get_bot()
        logger.info("Bot already running, skipping initialization")
        return
    except AssertionError:
        pass

    # Start the bot in a daemon thread
    logger.info("Creating background thread for Discord bot...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    logger.info("Starting Discord bot thread...")
    bot_thread.start()

    logger.info("Discord bot started in background thread")
