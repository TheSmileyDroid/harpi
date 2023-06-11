import discord
import logging
import os
from discord.ext import commands


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
    style="%",
)

handler = logging.FileHandler(
    filename="discord.log", mode="w", encoding="utf-8")


class Harpi(commands.Bot):
    prefix = "-"

    async def setup_hook(self) -> None:
        await self.load_extension("src.modules.tts")
        await self.load_extension("src.modules.music")
        await self.load_extension("src.modules.basic")
        await self.load_extension("src.modules.dice")
        await self.load_extension("src.modules.chat")
        return await super().setup_hook()

    async def on_ready(self):
        print(f"Logado como {self.user}!")
        synced = await self.tree.sync()
        print(f'Synced {len(synced)} commands.')

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Comando não encontrado.")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"Erro ao executar o comando: {error}")
        else:
            await ctx.send(f"Erro desconhecido: {error}")


if __name__ == "__main__":
    intents = discord.Intents.all()
    client = Harpi(command_prefix=Harpi.prefix, intents=intents)
    token: str = str(os.getenv("DISCORD_ID"))
    client.run(token, log_handler=handler, log_level=logging.INFO)
