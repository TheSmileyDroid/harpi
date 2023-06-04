from discord.ext.commands.context import Context
from discord.ext import commands
import discord
import urllib.parse
from src.modules.utils.aichat import AIChat
from src.modules.utils.guild import guild_data


def guild(ctx: Context) -> discord.Guild:
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            'Este comando não pode ser usado em MP')
    return ctx.guild


def voice_state(ctx: commands.Context) -> discord.VoiceState:
    if not isinstance(ctx.author, discord.Member):
        raise commands.CommandError('Você não está em um canal de voz')
    if ctx.author.voice is None:
        raise commands.CommandError('Você não está em um canal de voz')
    return ctx.author.voice


def voice_channel(ctx: commands.Context) -> discord.VoiceChannel:
    _voice_state = voice_state(ctx)
    if _voice_state.channel is None:
        raise commands.CommandError('Você não está em um canal de voz')
    return _voice_state.channel  # type: ignore


async def voice_client(ctx: commands.Context) -> discord.VoiceClient:
    voice = discord.utils.get(ctx.bot.voice_clients, guild=guild(ctx))
    if voice is None:
        _voice_channel = voice_channel(ctx)
        voice = await _voice_channel.connect()
    return voice


async def say(ctx: commands.Context, text: str):
    voice: discord.VoiceClient = await voice_client(ctx)
    if voice.is_playing():
        return await ctx.send('Já estou reproduzindo algo')
    text = urllib.parse.quote_plus(text)
    voice.play(
        discord.FFmpegPCMAudio(
            f'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={text}&tl=pt-BR'  # noqa E501
        ))


class TTS(commands.Cog):

    @commands.command(name='f')
    async def tts(self, ctx, *, text: str):
        await say(ctx, text)

    @commands.command(name='fc')
    async def fchat(self, ctx, *, text: str):
        chat: AIChat = guild_data.chat(ctx)
        response = chat.chat(ctx, text)
        await say(ctx, response)


async def setup(bot):
    await bot.add_cog(TTS(bot))
