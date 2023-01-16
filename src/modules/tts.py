from discord.ext import commands
import discord


def guild(ctx: commands.Context) -> discord.Guild:
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


'''
Usar link do google translate para fazer a conversão de texto para voz
'''


class TTS(commands.Cog):

    @commands.command(name='f')
    async def tts(self, ctx, *, text: str):
        voice: discord.VoiceClient = await voice_client(ctx)
        if voice.is_playing():
            return await ctx.send('Já estou reproduzindo algo')
        voice.play(
            discord.FFmpegPCMAudio(
                f'https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={text}&tl=pt-BR'  # noqa E501
            ))


async def setup(bot):
    await bot.add_cog(TTS(bot))
