from discord import Embed
from discord.ext import commands
from discord.ext.commands.context import Context
import logging as log
from src.modules.utils.dice_roller import DiceHandler, RandomDiceRoller
from src.modules.utils.send import EmbeddedMessage


class Dice(commands.Cog):

    @commands.command(name='d', aliases=['dado', 'rolar', 'roll', 'r'])
    async def roll(self, ctx: Context, *, args: str):
        """Rola um dado. Exemplo: -d 1d20+3"""
        try:
            dice_handler = DiceHandler(RandomDiceRoller())
            result = dice_handler.froll(args)
            await EmbeddedMessage(ctx, Embed(
                title="Resultado",
                description=f"{result}",
                color=0x00ff00
            )).send()
        except Exception as e:
            log.error(e)
            await ctx.send("Erro ao executar o comando.")


async def setup(bot):
    await bot.add_cog(Dice(bot))
