"""RPG Dice Cog module."""

import discord.ext.commands
from discord import Message
from discord.ext.commands import Cog, command
from discord.ext.commands.context import Context

from src.HarpiLib.math.parser import DiceParser


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
        parser = DiceParser()
        if not parser.is_valid_dice_string(message.content):
            return
        response = parser.roll(message.content)
        await message.reply(response)

    @command(
        name="d", aliases=["dado", "rolar", "roll", "r", "math", "calc", "m"]
    )
    async def roll(self, ctx: Context, *, args: str) -> None:
        """Comando para rolar dados.

        Args:
            ctx (Context)
            args (str): String com a quantidade e o tipo de dado a ser rolado
            (ex: 2d6 ou 1d20+5)


        """
        parser = DiceParser()
        response = parser.roll(args)
        await ctx.reply(response)
