from io import BytesIO
from os import makedirs
from discord.ext.commands.context import Context
from discord.ext import commands
import discord
from gtts import gTTS


from src.modules.utils.aichat import AIChat
from src.modules.utils.guild import guild_data
from src.modules.utils.musicdata import FFmpegPCMAudio


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
    fp = BytesIO()
    tts = gTTS(text=text, lang='pt', tld='com.br')
    tts.write_to_fp(fp)
    makedirs('.audios', exist_ok=True)
    tts.save(f".audios/{guild(ctx).id}.mp3")
    fp.seek(0)
    voice.play(FFmpegPCMAudio(fp.read(), pipe=True))


class TTS(commands.Cog):

    @commands.command(name='f')
    async def tts(self, ctx, *, text: str):
        await say(ctx, text)

    @commands.command(name='fc', aliases=['fchat'])
    async def fchat(self, ctx, *, text: str):
        chat: AIChat = guild_data.chat(ctx)
        response = chat.chat(ctx, text)
        if response.startswith('Harpi:'):
            response = response[6:]
        await say(ctx, response)


async def setup(bot):
    await bot.add_cog(TTS(bot))
