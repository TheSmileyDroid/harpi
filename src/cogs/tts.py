from io import BytesIO
from pathlib import Path

import discord
from discord.ext import commands
from discord.ext.commands.context import Context
from gtts import gTTS

from src.HarpiLib.musicdata.ytmusicdata import (
    AudioSourceTracked,
    FFmpegPCMAudio,
)


def guild(ctx: Context) -> discord.Guild:
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            "Este comando não pode ser usado em MP",
        )
    return ctx.guild


def voice_state(ctx: commands.Context) -> discord.VoiceState:
    if not isinstance(ctx.author, discord.Member):
        raise commands.CommandError("Você não está em um canal de voz")
    if ctx.author.voice is None:
        raise commands.CommandError("Você não está em um canal de voz")
    return ctx.author.voice


def voice_channel(ctx: commands.Context) -> discord.VoiceChannel:
    _voice_state = voice_state(ctx)
    if _voice_state.channel is None:
        raise commands.CommandError("Você não está em um canal de voz")
    return _voice_state.channel  # type: ignore


async def voice_client(ctx: commands.Context) -> discord.VoiceClient:
    voice = discord.utils.get(ctx.bot.voice_clients, guild=guild(ctx))
    if voice is None:
        _voice_channel = voice_channel(ctx)
        voice = await _voice_channel.connect()
    return voice


class AlreadyPlaying(commands.CommandError):
    """Musica em andamento."""


async def say(ctx: commands.Context, text: str) -> None:
    voice: discord.VoiceClient = await voice_client(ctx)
    if voice.is_playing():
        raise AlreadyPlaying("Já estou reproduzindo algo")
    fp = BytesIO()
    tts = gTTS(text=text, lang="pt", tld="com.br")
    tts.write_to_fp(fp)
    Path.mkdir(Path(".audios"), exist_ok=True, parents=True)
    tts.save(f".audios/{guild(ctx).id}.mp3")
    fp.seek(0)
    voice.play(
        AudioSourceTracked(FFmpegPCMAudio(fp.read(), pipe=True)),
    )


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
