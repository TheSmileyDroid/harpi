import logging
import os

import discord
from discord.ext import commands

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
    filename="discord.log",
)

handler = logging.FileHandler(filename="discord.log", mode="w", encoding="utf-8")


class Harpi(commands.Bot):
    prefix = "-"

    async def setup_hook(self) -> None:
        await self.load_extension("src.res")
        return await super().setup_hook()

    async def on_ready(self):
        logging.log(logging.INFO, f"Logado como {self.user}!")
        global guild_ids, bot
        from src.res.utils.guild import guild_ids

        bot = self

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


def main(bot: Harpi) -> None:
    token: str = str(os.getenv("DISCORD_ID"))
    bot.run(token, log_handler=handler, log_level=logging.INFO)


def harpi() -> Harpi:
    intents = discord.Intents.all()
    client = Harpi(command_prefix=Harpi.prefix, intents=intents)
    return client


if __name__ == "__main__":
    main(bot=harpi())
