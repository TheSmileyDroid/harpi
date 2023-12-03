import logging
from discord.ext import commands
from src.bot.iharpi import IHarpi

from src.res.utils.guild import guild_ids

logger = logging.getLogger(__name__)


class Harpi(IHarpi):
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
        if isinstance(error, commands.PrivateMessageOnly):
            await ctx.send("Este comando só pode ser usado em DMs.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Faltam argumentos.")
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("Comando não encontrado.")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"Erro ao executar o comando: {error}")
            raise error
        else:
            await ctx.send(f"Erro desconhecido: {error}")
