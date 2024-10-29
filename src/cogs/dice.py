"""Dice system for Harpi."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import discord
import discord.ext
import discord.ext.commands
from discord import Embed, Message
from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands.context import Context


@dataclass
class DiceComponent:
    """Represents a dice component. With the info count, sides and modifier."""

    count: int
    sides: int
    modifier: int = 0

    def roll(self) -> tuple[list[int], int]:
        """Roll the dice and get the results.

        Returns:
            tuple[list[int], int]: A list with the rolls and the result.

        """
        rolls = [random.randint(1, self.sides) for _ in range(self.count)]  # noqa: S311
        return rolls, sum(rolls) + self.modifier

    def __str__(self) -> str:
        """Get a string representation of the dice roll.

        Returns:
            str: A string representation of the dice roll.

        """
        if self.sides == 0:
            return str(self.modifier)
        return f"{self.count}d{self.sides}" + (
            f"+{self.modifier}" if self.modifier else ""
        )


class DiceParser:
    """Parses a dice string into a list of DiceComponent objects."""

    def __init__(self, dice_string: str) -> None:
        """Initialize the DiceParser with a dice string.

        Parameters
        ----------
        dice_string : str
            The dice string to parse.

        Raises
        ------
        ValueError
            If the dice string is invalid.

        Examples
        --------
        >>> parser = DiceParser(
        ...     "2d6"
        ... )
        >>> len(
        ...     parser.component_register[
        ...         0
        ...     ]
        ... )
        1
        >>> parser = DiceParser(
        ...     "2d6+3+2d"
        ... )
        >>> len(
        ...     parser.component_register[
        ...         0
        ...     ]
        ... )
        3

        """
        self.dice_string = dice_string
        self.component_register: list[list[tuple[str, DiceComponent]]] = []
        if not self.is_valid_dice_string(self.dice_string):
            msg = "Invalid dice string"
            raise ValueError(msg)
        self._parse()

    @staticmethod
    def is_valid_dice_string(dice_string: str) -> bool:
        """Check if it is a valid dice string.

        Returns:
            bool: True if it is a valid dice string, False otherwise.

        >>> parser = DiceParser(
        ...     "2d6"
        ... )
        >>> parser.is_valid_dice_string()
        True
        >>> parser = DiceParser(
        ...     "2#d"
        ... )
        >>> parser.is_valid_dice_string()
        True

        """
        pattern = r"^([+-]?[#]?(\d*d\d*|\d+))+$"
        return re.match(pattern, dice_string.replace(" ", "")) is not None

    def _parse(self) -> None:
        """Parse the dice string and store the results in the `self.results` list.

        Examples
        --------
        >>> parser = DiceParser(
        ...     "2d6"
        ... )
        >>> len(
        ...     parser.component_register
        ... )
        1

        """  # noqa: E501
        components = []
        count_of_rows = 1
        if self.dice_string.count("#") >= 1:
            count_of_rows = int(self.dice_string.split("#")[0])

        _dice_tring = self.dice_string.split("#")[-1].replace(" ", "")

        for i in range(count_of_rows):
            components.append([])
            pattern = r"([+-]?)(\d*d?\d*)"
            matches = re.findall(
                pattern,
                _dice_tring,
            )

            for sign, value in matches:
                if len(value) == 0:
                    continue
                if "d" in value:
                    count, sides = (
                        int(x) if x else 1 for x in value.split("d")
                    )
                    if sides == 1:
                        sides = 20
                    components[i].append((sign, DiceComponent(count, sides)))
                else:
                    components[i].append((
                        sign,
                        DiceComponent(0, 0, int(value)),
                    ))
        self.component_register = components

    def roll(self) -> list[tuple[int, list[str]]]:
        """Roll the dice and return the total and the results.

        Returns:
            tuple[int, list[str]]: The total and the results.

        Examples:
        --------
        >>> parser = DiceParser(
        ...     "2d6"
        ... )
        >>> total, results = (
        ...     parser.roll()
        ... )[0]
        >>> len(results)
        1
        >>> total >= 2 and total <= 12
        True
        >>> parser = DiceParser(
        ...     "2#d+10"
        ... )
        >>> total, results = (
        ...     parser.roll()
        ... )[0]
        >>> len(results)
        2
        >>> total >= 1 and total <= 30
        True
        >>> total, results = (
        ...     parser.roll()
        ... )[1]
        >>> len(results)
        2
        >>> total >= 1 and total <= 30
        True
        >>> len(parser.roll())
        2

        """
        row_results = []

        for components in self.component_register:
            total = 0
            results: list[str] = []
            for sign, component in components:
                rolls, result = component.roll()
                if sign == "-":
                    total -= result
                else:
                    total += result
                if component.sides != 0:
                    results.append(
                        f"[{self._format_rolls(rolls, component.sides)}]",
                    )
                else:
                    results.append("")
            row_results.append((total, results))
        return row_results

    @staticmethod
    def _format_rolls(rolls: list[int], sides: int) -> str:
        """Format the rolls.

        Args:
            rolls (list[int]): The rolls.
            sides (int): The sides of the dice.

        Returns:
            str: The formatted rolls.

        """
        return ", ".join(
            f"**{roll}**" if roll == sides else str(roll) for roll in rolls
        )


class DiceCog(commands.Cog):
    """Cog for handling dice."""

    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        """Initialize the cog.

        Args:
            bot (discord.ext.commands.Bot): The bot.

        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Listen for messages and roll the dice."""
        if message.author == self.bot.user:
            return

        if not DiceParser.is_valid_dice_string(message.content):
            return
        parser = DiceParser(message.content)
        embed = self.generate_embed(parser)
        await message.reply(embed=embed)

    @commands.command(name="d", aliases=["dado", "rolar", "roll", "r"])
    async def roll(self, ctx: Context, *, args: str) -> None:  # noqa: D417
        """Comando para rolar dados.

        Args:
            ctx (Context)
            args (str): String com a quantidade e o tipo de dado a ser rolado
            (ex: 2d6 ou 1d20+5)


        """
        parser = DiceParser(args)
        embed = self.generate_embed(parser)
        await ctx.reply(embed=embed)

    @staticmethod
    def generate_embed(parser: DiceParser) -> Embed:
        """Generate an embed with the rolled dice.

        Parameters
        ----------
        parser : DiceParser
            The parser with the dice roll.

        Returns
        -------
        Embed
            _description_

        """
        rows = parser.roll()
        text = ""
        for i, row in enumerate(rows):
            total, results = row
            for component, result in zip(
                parser.component_register[i],
                results,
            ):
                text += f"{component[0]}{component[1]}{result}"
            text += " = " + str(total)
            if i != len(rows) - 1:
                text += "\n"
        embed: Embed = Embed(color=0x00DD33).add_field(name="", value=text)
        return embed


if __name__ == "__main__":
    import doctest

    doctest.testmod()
