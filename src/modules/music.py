import asyncio
import contextlib

import discord
from discord.ext import commands

from src.modules.utils.guild import guild, guild_data
from src.modules.utils.musicdata import MusicData, YoutubeDLSource
from src.modules.utils.send import Message, EmbeddedMessage


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
    async def play(self, ctx: commands.Context, *, args: str):
        data: list[MusicData] = MusicData.from_url(args)
        for music in data:
            guild_data.queue(ctx).append(music)
        _voice_client = await voice_client(ctx)
        if _voice_client.is_playing():
            musics_str = '\n'.join(
                [f'**{music.title}**' for music in data])
            await Message(
                ctx, content=f'Playlist adicionada à fila:\n{musics_str}').send()
            return

        await self.play_current(ctx)
        await Message(
            ctx, f'Tocando **{data[0].title}**').send()
        musics_str = '\n'.join(
            [f'{music.title}' for music in data[1:]])
        if musics_str:
            await Message(
                ctx, f'Playlist adicionada à fila:\n{musics_str}').send()

    async def play_next(self, ctx: commands.Context):
        if guild_data.skip_flag(ctx):
            guild_data.set_skip_flag(ctx, False)
            guild_data.queue(ctx).pop(0)
            await self.play_current(ctx)
            return
        if guild_data.is_looping(ctx):
            return await self.play_current(ctx)
        guild_data.queue(ctx).pop(0)
        await self.play_current(ctx)

    async def play_current(self, ctx: commands.Context):
        with contextlib.suppress(Exception):
            data = guild_data.queue(ctx)[0]
            _voice_client = await voice_client(ctx)
            if _voice_client.is_playing():
                return
            _voice_client.play(
                await YoutubeDLSource.from_music_data(data),  # type: ignore
                after=lambda _: asyncio.run_coroutine_threadsafe(
                    self.play_next(ctx), ctx.bot.loop).result())

            _voice_client.source.volume = guild_data.volume(  # type: ignore
                ctx)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)

        if _voice_client.is_paused():
            return await Message(
                ctx, 'O player já está pausado').send()
        _voice_client.pause()
        await Message(
            ctx, 'Pausado').send()

    @commands.command()
    async def resume(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_paused():
            return await Message(
                ctx, 'O player já está tocando').send()
        _voice_client.resume()
        await Message(
            ctx, 'Continuando').send()

    @commands.command()
    async def stop(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await Message(
                ctx, 'O player já está parado').send()
        _voice_client.stop()
        guild_data.queue(ctx).clear()
        await Message(
            ctx, 'Parado').send()

    @commands.command()
    async def skip(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await Message(
                ctx, 'O player já está parado').send()
        guild_data.set_skip_flag(ctx, True)
        _voice_client.stop()
        await Message(
            ctx, 'Pulando para a próxima música').send()

    @commands.command()
    async def queue(self, ctx: commands.Context):
        _queue = guild_data.queue(ctx)
        if _queue is None:
            return await Message(
                ctx, 'Não há nada na fila').send()
        embed = discord.Embed(title='Fila de músicas')
        for index, data in enumerate(_queue):
            embed.add_field(name=f'{index + 1} - {data.title}',
                            value=f'**{data.url}**')
        embed.set_footer(text='Looping ativado' if guild_data.
                         is_looping(ctx) else 'Looping desativado')
        await EmbeddedMessage(
            ctx, embed=embed).send()

    @commands.command()
    async def remove(self, ctx: commands.Context, args: int):
        _queue = guild_data.queue(ctx)
        if _queue is None:
            return await Message(
                ctx, 'Não há nada na fila').send()
        if args > len(_queue):
            return await Message(
                ctx, 'Índice inválido').send()
        guild_data.queue(ctx).remove(args - 1)
        await Message(
            ctx, f'Removido índice {args}').send()

    @commands.command()
    async def loop(self, ctx: commands.Context):
        guild_data.set_looping(ctx, not guild_data.is_looping(ctx))
        await Message(
            ctx, 'Looping ativado' if guild_data.
            is_looping(ctx) else 'Looping desativado').send()

    @commands.command()
    async def shuffle(self, ctx: commands.Context):
        _queue = guild_data.queue(ctx)
        if _queue is None:
            return await Message(
                ctx, 'Não há nada na fila').send()
        guild_data.shuffle_queue(ctx)
        await Message(
            ctx, 'Fila embaralhada').send()

    @commands.command()
    async def volume(self, ctx: commands.Context, args: int):
        if args > 200 or args < 0:
            return await Message(
                ctx, 'Volume inválido').send()
        _voice_client = await voice_client(ctx)
        guild_data.set_volume(ctx, args / 100)
        if not _voice_client.is_playing():
            return
        _voice_client.source.volume = args / 100  # type: ignore
        await Message(
            ctx, f'Volume alterado para {args}%').send()

    @commands.command()
    async def now(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await Message(
                ctx, 'Não estou tocando nada agora').send()

        await Message(
            ctx,
            f'Tocando **{_voice_client.source.title}**')  # type: ignore

    @commands.command()
    async def join(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        await Message(
            ctx, f'Entrando no canal **{_voice_client.channel}**').send()


async def setup(bot):
    await bot.add_cog(Music(bot))
