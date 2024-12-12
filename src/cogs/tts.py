import discord
from discord.ext import commands
from discord.ext.commands.context import Context

from src.HarpiLib.say import say


class TTSCog(commands.Cog):
    """TTS Cog."""

    @commands.hybrid_command(name="f", description="Fala um texto")
    @discord.app_commands.describe(
        text="Texto a ser falado",
    )
    async def tts(self, ctx: Context, *, text: str) -> None:
        """Text-To-Speech.

        Permite falar (Usando TTS do Google Translate)
        em um canal de voz.
        """
        await say(ctx, text)
        await ctx.send("OK", ephemeral=True, delete_after=5)
