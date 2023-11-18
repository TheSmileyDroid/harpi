from discord import Embed
from discord.ext import commands
from discord.ext.commands.context import Context

from .utils.dice_roller import DiceHandler, RandomDiceRoller
from .utils.send import EmbeddedMessage


class DiceCog(commands.Cog):
    @commands.command(name="d", aliases=["dado", "rolar", "roll", "r"])
    async def roll(self, ctx: Context, *, args: str) -> None:
        """Comando para rolar dados

        Args:
            ctx (Context)
            args (str): String com a quantidade e o tipo de dado a ser rolado (ex: 2d6 ou 1d20+5)
        """
        dice_handler = DiceHandler(RandomDiceRoller())
        result = dice_handler.froll(args)
        embed: Embed = Embed(color=0x00FF00).add_field(name="Resultado", value=result)
        await EmbeddedMessage(ctx, embed).send()
