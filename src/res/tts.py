from io import BytesIO
from os import makedirs

import discord
from discord.ext import commands
from discord.ext.commands.context import Context
from gtts import gTTS

from .utils.ytmusicdata import FFmpegPCMAudio


def guild(ctx: Context) -> discord.Guild:
    if ctx.guild is None:
        raise commands.NoPrivateMessage("Este comando não pode ser usado em MP")
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
    pass


async def say(ctx: commands.Context, text: str) -> None:
    voice: discord.VoiceClient = await voice_client(ctx)
    if voice.is_playing():
        raise AlreadyPlaying("Já estou reproduzindo algo")
    fp = BytesIO()
    tts = gTTS(text=text, lang="pt", tld="com.br")
    tts.write_to_fp(fp)
    makedirs(".audios", exist_ok=True)
    tts.save(f".audios/{guild(ctx).id}.mp3")
    fp.seek(0)
    voice.play(FFmpegPCMAudio(fp.read(), pipe=True))


class TTSCog(commands.Cog):
    @commands.hybrid_command(name="f")
    async def tts(self, ctx, *, text: str):
        await say(ctx, text)
