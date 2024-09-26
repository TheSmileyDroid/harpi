#!/usr/bin/env python3
"""O executável do bot."""

import asyncio
import logging
import os

import discord
import discord.ext.commands as cd

from src.cogs.basic import BasicCog
from src.cogs.dice import DiceCog
from src.cogs.music import MusicCog
from src.cogs.tts import TTSCog

terminal_logger = logging.StreamHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminal_logger)


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


async def main() -> None:
    """Executa o bot."""
    intents = discord.Intents.all()

    client = cd.Bot(command_prefix="-", intents=intents)

    await client.add_cog(TTSCog())
    await client.add_cog(MusicCog())
    await client.add_cog(BasicCog())
    await client.add_cog(DiceCog(client))

    await client.start(get_token())


if __name__ == "__main__":
    asyncio.run(main())
