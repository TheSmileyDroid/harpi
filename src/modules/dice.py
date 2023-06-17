from discord.ext import commands
from discord.ext.commands.context import Context
import logging as log
from src.modules.utils.dice_roller import DiceHandler, RandomDiceRoller


class Dice(commands.Cog):

    @commands.command(name='d', aliases=['dado', 'rolar', 'roll', 'r'])
    async def roll(self, ctx: Context, *, args: str):
        """Rola um dado. Exemplo: -d 1d20+3"""
        try:
            dice_handler = DiceHandler(RandomDiceRoller())
            result = dice_handler.froll(args)
            await ctx.send(result)
        except Exception as e:
            log.error(e)
            await ctx.send("Erro ao executar o comando.")


async def setup(bot):
    await bot.add_cog(Dice(bot))
