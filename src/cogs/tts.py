import io
from typing import cast

import discord
from discord.ext import commands
from discord.ext.commands.context import Context
from gtts import gTTS

from src.harpi_lib.api import HarpiAPI
from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.musicdata.ytmusicdata import (
    AudioSourceTracked,
    FastStartFFmpegPCMAudio,
)


class TTSCog(commands.Cog):
    """TTS Cog."""

    def __init__(self, bot: HarpiBot) -> None:
        self.bot: HarpiBot = bot
        self.api: HarpiAPI = bot.api

    @commands.command(
        name="tts",
        aliases=["text-to-speech", "falar", "f"],
        help="Fala o texto em um canal de voz.",
    )
    async def tts(self, ctx: Context, *, text: str) -> discord.Message | None:
        """Text-To-Speech.

        Speak text in a voice channel using Google Translate TTS.
        """
        if not ctx.guild:
            return await ctx.send("Você precisa estar em um servidor.")

        member = cast(discord.Member, ctx.author)

        if not member.voice or not member.voice.channel:
            return await ctx.send("Você precisa estar em um canal de voz.")

        if not self.api:
            return await ctx.send("Erro: Sistema de música não inicializado.")

        fp = io.BytesIO()
        tts = gTTS(text=text, lang="pt", tld="com.br")
        tts.write_to_fp(fp)
        _ = fp.seek(0)

        source = AudioSourceTracked(FastStartFFmpegPCMAudio(fp, pipe=True))

        _ = await self.api.play_tts_source(
            ctx.guild.id, member.voice.channel.id, source, ctx
        )
        return await ctx.send("OK", silent=True, delete_after=5)
