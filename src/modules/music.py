import asyncio
from discord.ext import commands
from src.modules.errors.bad_link import BadLink
import youtube_dl
import discord

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class MusicData:

    def __init__(self, title, url):
        self.title = title
        self.url = url

    @classmethod
    def from_url(cls, url):
        with ytdl:
            result = ytdl.extract_info(url, download=False)
        if result is None:
            raise BadLink(url)
        video = result['entries'][0] if 'entries' in result else result
        return cls(video['title'], video['webpage_url'])


class YoutubeDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.3):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_music_data(cls, musicdata: MusicData, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(musicdata.url, download=False))
        if data is None:
            raise BadLink(musicdata.url)
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if 'url' in data else ytdl.prepare_filename(
            data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data=data)


class MusicQueue:

    def __init__(self):
        self.queue = {}

    def add(self, guild_id: int, musicdata: MusicData):
        if guild_id not in self.queue:
            self.queue[guild_id] = []
        self.queue[guild_id].append(musicdata)

    def get_current(self, guild_id: int):
        return None if guild_id not in self.queue else self.queue[guild_id][0]

    def get_next(self, guild_id: int):
        if guild_id not in self.queue:
            return None
        self.queue[guild_id].pop(0)
        return self.get_current(guild_id)

    def get_all(self, guild_id: int):
        return None if guild_id not in self.queue else self.queue[guild_id]

    def clear(self, guild_id: int):
        if guild_id in self.queue:
            self.queue[guild_id].clear()

    def remove(self, guild_id: int, index: int):
        if guild_id in self.queue:
            self.queue[guild_id].pop(index)

    def get_index(self, guild_id: int, index: int):
        return self.queue[guild_id][index] if guild_id in self.queue else None


queue = MusicQueue()


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


class Music(commands.Cog):

    @commands.command()
    async def play(self, ctx: commands.Context, *, message: str):
        data = MusicData.from_url(message)
        queue.add(guild(ctx).id, data)
        _voice_client = await voice_client(ctx)
        if _voice_client.is_playing():
            return await ctx.send(f'Adicionado **{data.title}** na fila')

        await self.play_current(ctx)
        await ctx.send(f'Tocando **{data.title}**')

    async def play_next(self, ctx: commands.Context):
        data = queue.get_next(guild(ctx).id)
        if data is None:
            return
        _voice_client = await voice_client(ctx)
        _voice_client.play(await YoutubeDLSource.from_music_data(data),
                           after=lambda _: asyncio.run_coroutine_threadsafe(
                               self.play_next(ctx), ctx.bot.loop).result())

    async def play_current(self, ctx: commands.Context):
        data = queue.get_current(guild(ctx).id)
        if data is None:
            return
        _voice_client = await voice_client(ctx)
        _voice_client.play(await YoutubeDLSource.from_music_data(data),
                           after=lambda _: asyncio.run_coroutine_threadsafe(
                               self.play_next(ctx), ctx.bot.loop).result())

    @commands.command()
    async def pause(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)

        if _voice_client.is_paused():
            return await ctx.send('O player já está pausado')
        _voice_client.pause()
        await ctx.send('Pausado')

    @commands.command()
    async def resume(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_paused():
            return await ctx.send('O player já está tocando')
        _voice_client.resume()
        await ctx.send('Continuando')

    @commands.command()
    async def stop(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await ctx.send('O player já está parado')
        _voice_client.stop()
        queue.clear(guild(ctx).id)
        await ctx.send('Parado')

    @commands.command()
    async def skip(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await ctx.send('O player já está parado')
        _voice_client.stop()
        await self.play_next(ctx)
        await ctx.send('Pulando para a próxima música')


async def setup(bot):
    await bot.add_cog(Music(bot))
