import logging
import os
import discord
from src.bot.harpi import Harpi
from src.bot.iharpi import IHarpi
import src.res  # noqa: F401

terminalLogger = logging.StreamHandler()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)
logging.getLogger().addHandler(terminalLogger)


def run_bot(bot: IHarpi) -> None:
    token: str = str(os.getenv("DISCORD_ID"))
    bot.run(token, log_level=logging.INFO, root_logger=True)


def create_bot() -> Harpi:
    intents = discord.Intents.all()
    bot = Harpi(command_prefix=Harpi.prefix, intents=intents)
    return bot


if __name__ == "__main__":
    run_bot(bot=create_bot())
