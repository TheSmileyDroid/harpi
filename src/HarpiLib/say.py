from io import BytesIO
from pathlib import Path

import discord
import discord.ext
import discord.ext.commands as commands
from gtts import gTTS

from src.HarpiLib.musicdata.ytmusicdata import (
    AudioSourceTracked,
    FFmpegPCMAudio,
)


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
    return _voice_state.channel  # type: ignore reportGeneralType


def guild(ctx: commands.Context) -> discord.Guild:
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            "Este comando não pode ser usado em MP",
        )
    return ctx.guild


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
        AudioSourceTracked(FFmpegPCMAudio(fp.read(), pipe=True)),  # type: ignore reportArgumentType
    )
