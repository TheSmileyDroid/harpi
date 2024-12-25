"""Ai COG."""

from typing import cast

from discord.ext import commands

from src.cogs.music import MusicCog
from src.HarpiLib.ai.gemini import Gemini
from src.HarpiLib.ai.tools import AiTools
from src.HarpiLib.say import say


class AiCog(commands.Cog):
    """Ai chat COG."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.music_cog: MusicCog = cast(MusicCog, bot.get_cog("MusicCog"))
        self.ai_map: dict[int, Gemini] = {}
        self.ai_tools = AiTools(bot)

        self.base_ai = Gemini

    @commands.command(aliases=["c", ""])
    async def chat(self, ctx: commands.Context, *, message: str) -> None:
        """Chat with Gemini AI."""
        guild = ctx.guild
        if not guild:
            return

        response = self.ai_map.get(guild.id, self.base_ai()).get_response(
            message,
            await self.ai_tools.get_tools(guild.id, ctx.channel.id),
        )
        slices = [
            response[i : i + 2000] for i in range(0, len(response), 2000)
        ]
        for slice_ in slices:
            await ctx.send(slice_)

    @commands.command(aliases=[])
    async def fc(self, ctx: commands.Context, *, message: str) -> None:
        """Chat with Gemini AI."""
        guild = ctx.guild
        if not guild:
            return

        response = self.ai_map.get(guild.id, self.base_ai()).get_response(
            message,
            await self.ai_tools.get_tools(guild.id, ctx.channel.id),
        )
        if len(response) < 1000:
            await say(ctx, response)

        slices = [
            response[i : i + 2000] for i in range(0, len(response), 2000)
        ]
        for slice_ in slices:
            await ctx.send(slice_)

    @commands.command()
    async def reset_chat(self, ctx: commands.Context) -> None:
        """Reset chat session."""
        guild = ctx.guild
        if guild:
            self.ai_map.get(guild.id, self.base_ai()).reset_chat()
            await ctx.send("Chat resetado.")
