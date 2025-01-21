"""RPG Dice Cog module."""

import discord.ext.commands
from discord import Message
from discord.ext.commands import Cog, command
from discord.ext.commands.context import Context

from src.HarpiLib.dice.dice_parser import DiceParser


class DiceCog(Cog):
    """Cog for handling dice."""

    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        """Initialize the cog.

        Args:
            bot (discord.ext.commands.Bot): The bot.

        """
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Listen for messages and roll the dice."""
        if message.author == self.bot.user:
            return

        if not DiceParser.is_valid_dice_string(message.content):
            return
        parser = DiceParser(message.content)
        response = self.generate_response(parser)
        await message.reply(response)

    @command(name="d", aliases=["dado", "rolar", "roll", "r"])
    async def roll(self, ctx: Context, *, args: str) -> None:
        """Comando para rolar dados.

        Args:
            ctx (Context)
            args (str): String com a quantidade e o tipo de dado a ser rolado
            (ex: 2d6 ou 1d20+5)


        """
        parser = DiceParser(args)
        response = self.generate_response(parser)
        await ctx.reply(response)

    @staticmethod
    def generate_response(parser: DiceParser) -> str:
        """Generate a text response with the rolled dice.

        Parameters
        ----------
        parser : DiceParser
            The parser with the dice roll.

        Returns
        -------
        str
            Formatted string with roll results
        """
        rows = parser.roll()
        text = "\n"
        for i, row in enumerate(rows):
            total, results = row
            roll_text = ""

            for component, result in zip(
                parser.component_register[i],
                results,
            ):
                if isinstance(result, (int, float)):
                    roll_text = f"[{result}] {component[0]}{component[1]}"
                else:
                    roll_text += f"{component[0]}{component[1]}{result}"

            text += f"` {total} ` ⟵ {roll_text}"
            if i != len(rows) - 1:
                text += "\n"
        text += "\n"
        return text
