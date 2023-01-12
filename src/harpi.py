import discord
import logging
import os
from discord.ext import commands

handler = logging.FileHandler(filename='discord.log',
                              encoding='utf-8',
                              mode='w')


class Harpi(commands.Bot):
    prefix = '-'

    async def on_ready(self):
        print(f'Logado como {self.user}!')

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Comando não encontrado.")
        else:
            raise error


intents = discord.Intents.all()

token: str = str(os.getenv('DISCORD_ID'))

client = Harpi(command_prefix=Harpi.prefix, intents=intents)

client.run(token, log_handler=handler, log_level=logging.DEBUG)
