import logging
import os

import discord
from discord.ext import commands

from src.res.utils.guild import guild_ids

import src.res  # noqa: F401

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)

handler = logging.FileHandler(filename="discord.log", mode="w", encoding="utf-8")


class Harpi(commands.Bot):
    prefix = "-"
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def setup_hook(self) -> None:
        await self.load_extension("src.res")
        return await super().setup_hook()

    async def on_ready(self):
        logging.log(logging.INFO, f"Logado como {self.user}!")
        global bot

        bot = self

        await self.log_guilds()

    async def log_guilds(self):
        logging.log(logging.INFO, "Guilds:")
        async for guild in self.fetch_guilds():
            if guild.id not in guild_ids.keys():
                guild_ids.update({guild.id: guild.name})
            logging.log(logging.INFO, f" - {guild.name}")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Comando não encontrado.")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"Erro ao executar o comando: {error}")
            raise error
        else:
            await ctx.send(f"Erro desconhecido: {error}")


def run_bot(bot: Harpi) -> None:
    token: str = str(os.getenv("DISCORD_ID"))
    handler = logging.FileHandler(filename="discord.log", mode="w", encoding="utf-8")
    terminalLogger = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
        style="%",
        handlers=[handler, terminalLogger],
    )
    bot.run(token, log_level=logging.INFO, root_logger=True)


def create_bot() -> Harpi:
    intents = discord.Intents.all()
    bot = Harpi(command_prefix=Harpi.prefix, intents=intents)
    return bot


if __name__ == "__main__":
    run_bot(bot=create_bot())
