from dataclasses import dataclass
from functools import reduce
import random
from discord import Embed, Message
import discord
from discord.ext import commands
import discord.ext.commands
from discord.ext.commands.context import Context

import discord.ext

from .utils.dice_roller import DiceHandler, RandomDiceRoller
from .utils.send import EmbeddedMessage


@dataclass
class DiceResult:
    template: str
    result: int


def recursive_roll(text: str, op: int) -> list[DiceResult]:
    if len(text) == 0:
        return [DiceResult("", 0)]
    next_term = min(text.find("+"), text.find("-")) or len(text)
    if text.find("d") != -1 and text.find("d") > next_term:
        number_of_dices = int(text[: text.find("d")])
        number_of_sides = int(text[text.find("d") + 1 : next_term])
        result = [random.randint(1, number_of_sides) for _ in range(number_of_dices)]

        return [
            DiceResult(
                f'{'+' if op else '-'} {number_of_dices}d{number_of_sides} {result}',
                op * reduce(lambda x, y: x + y, result),
            )
        ] + recursive_roll(text[next_term + 1 :], 1 if text[next_term] == "+" else -1)
    value = int(text[:next_term])

    return [DiceResult(f'{'+' if op else '-'} {value}', op * value)] + recursive_roll(
        text[next_term + 1 :], 1 if text[next_term] == "+" else -1
    )


class DiceCog(commands.Cog):
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

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
