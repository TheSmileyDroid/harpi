from discord.ext import commands
from discord.ext.commands.context import Context

from src.HarpiLib.say import say
from src.cogs.base import TrackedCog


class TTSCog(TrackedCog):
    """TTS Cog for text-to-speech functionality."""

    @commands.command(
        name="tts",
        aliases=["text-to-speech", "falar", "f"],
        help="Fala o texto em um canal de voz.",
    )
    async def tts(self, ctx: Context, *, text: str) -> None:
        """Text-To-Speech.

        Permite falar (Usando TTS do Google Translate)
        em um canal de voz.
        """
        await say(ctx, text)
        await ctx.send("OK", silent=True, delete_after=5)
