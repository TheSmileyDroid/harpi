import asyncio
import logging
import os
import discord
import discord.ext.commands as cd
from src.res import TTSCog
from src.res import MusicCog
from src.res import BasicCog
from src.res.dice import DiceCog


terminalLogger = logging.StreamHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminalLogger)


def get_token() -> str:
    token = os.getenv("DISCORD_TOKEN")

    if token:
        return token

    raise Exception("DISCORD_TOKEN not defined")


async def main():
    intents = discord.Intents.all()

    client = cd.Bot(command_prefix="-", intents=intents)

    await client.add_cog(TTSCog())
    await client.add_cog(MusicCog())
    await client.add_cog(BasicCog())
    await client.add_cog(DiceCog(client))

    await client.start(get_token())


if __name__ == "__main__":
    asyncio.run(main())
