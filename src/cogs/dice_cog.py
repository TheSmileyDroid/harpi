"""RPG Dice Cog module."""

import discord.ext.commands
from discord import Embed, Message
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
        embed = self.generate_embed(parser)
        await message.reply(embed=embed)

    @command(name="d", aliases=["dado", "rolar", "roll", "r"])
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
