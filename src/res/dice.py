from discord import Embed
from discord.ext import commands
from discord.ext.commands.context import Context

from .utils.dice_roller import DiceHandler, RandomDiceRoller
from .utils.send import EmbeddedMessage


class Dice(commands.Cog):
    @commands.command(name="d", aliases=["dado", "rolar", "roll", "r"])
    async def roll(self, ctx: Context, *, args: str) -> None:
        """Rola um dado. Exemplo: -d 1d20+3"""
        dice_handler = DiceHandler(RandomDiceRoller())
        result = dice_handler.froll(args)
        embed: Embed = Embed(color=0x00FF00).add_field(
            name="Resultado", value=result
        )
        await EmbeddedMessage(ctx, embed).send()


async def setup(bot):
    await bot.add_cog(Dice(bot))
