from discord import Embed, Message
import discord
from discord.ext import commands
import discord.ext.commands
from discord.ext.commands.context import Context

import discord.ext

from .utils.send import EmbeddedMessage
import re
from dataclasses import dataclass
from typing import List, Tuple
import random


@dataclass
class DiceComponent:
    count: int
    sides: int
    modifier: int = 0

    def roll(self):
        rolls = [random.randint(1, self.sides) for _ in range(self.count)]
        return rolls, sum(rolls) + self.modifier

    def __str__(self):
        if self.sides == 0:
            return str(self.modifier)
        return f"{self.count}d{self.sides}" + (
            f"+{self.modifier}" if self.modifier else ""
        )


class DiceParser:
    def __init__(self, dice_string: str):
        self.dice_string = dice_string
        self.components: List[Tuple[str, DiceComponent]] = []

    def is_valid_dice_string(self):
        # This regex pattern matches the entire string
        pattern = r"^([+-]?(\d*d\d*|\d+))+$"
        return re.match(pattern, self.dice_string.replace(" ", "")) is not None

    def _parse(self):
        pattern = r"([+-]?)(\d*d?\d*)"
        matches = re.findall(pattern, self.dice_string.replace(" ", ""))

        for sign, value in matches:
            if len(value) == 0:
                continue
            if "d" in value:
                count, sides = map(lambda x: int(x) if x else 1, value.split("d"))
                if sides == 1:
                    sides = 20
                self.components.append((sign, DiceComponent(count, sides)))
            else:
                self.components.append((sign, DiceComponent(0, 0, int(value))))

    def roll(self):
        if self.is_valid_dice_string():
            self._parse()
        else:
            raise ValueError("Invalid dice string")
        total = 0
        results: list[str] = []
        for sign, component in self.components:
            rolls, result = component.roll()
            if sign == "-":
                total -= result
            else:
                total += result
            if component.sides != 0:
                results.append(f"[{self._format_rolls(rolls, component.sides)}]")
            else:
                results.append("")
        return total, results

    def _format_rolls(self, rolls, sides):
        return ", ".join(
            f"**{roll}**" if roll == sides else str(roll) for roll in rolls
        )


class DiceCog(commands.Cog):
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return

        parser = DiceParser(message.content)
        if not parser.is_valid_dice_string():
            return
        total, results = parser.roll()
        text = ""
        for component, result in zip(parser.components, results):
            text += f"{component[0]}{component[1]}{result}"
        text += " = " + str(total)
        embed: Embed = Embed(color=0x00DD33).add_field(name="", value=text)
        await message.reply(embed=embed)

    @commands.command(name="d", aliases=["dado", "rolar", "roll", "r"])
    async def roll(self, ctx: Context, *, args: str) -> None:
        """Comando para rolar dados

        Args:
            ctx (Context)
            args (str): String com a quantidade e o tipo de dado a ser rolado (ex: 2d6 ou 1d20+5)
        """
        parser = DiceParser(args)
        total, results = parser.roll()
        text = ""
        for component, result in zip(parser.components, results):
            text += f"{component[0]}{component[1]}{result}"
        text += " = " + str(total)
        embed: Embed = Embed(color=0x00DD33).add_field(name="", value=text)
        await EmbeddedMessage(ctx, embed).send()


if __name__ == "__main__":
    parser = DiceParser("2d20+1d8")
    total, results = parser.roll()

    print(f"Dice string: {parser.dice_string}")
    print("\nRoll breakdown: ", results)
    for component, result in zip(parser.components, results):
        print(f"{component[1]}{result}")
    print(f"\nTotal result: {total}")
