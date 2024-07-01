import asyncio
import logging
import discord
import credentials
import discord.ext.commands as cd
from src.res import TTSCog
from src.res import MusicCog
from src.res import BasicCog

terminalLogger = logging.StreamHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminalLogger)


async def main():
    intents = discord.Intents.all()

    client = cd.Bot(command_prefix="-", intents=intents)

    await client.add_cog(TTSCog())
    await client.add_cog(MusicCog())
    await client.add_cog(BasicCog())

    await client.start(credentials.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
