import asyncio
import contextlib
from discord.ext import commands
import discord
from src.modules.utils.guild import guild, guild_data
from src.modules.utils.musicdata import MusicData, YoutubeDLSource
from src.modules.utils.send import send_message


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
        data: list[MusicData] = MusicData.from_url(message)
        for music in data:
            guild_data.queue(ctx).append(music)
        _voice_client = await voice_client(ctx)
        if _voice_client.is_playing():
            musics_str = '\n'.join(
                [f'**{music.title}**' for music in data])
            await send_message(
                ctx, content=f'Playlist adicionada à fila:\n{musics_str}')
            return

        await self.play_current(ctx)
        await send_message(
            ctx, f'Tocando **{data[0].title}**')
        musics_str = '\n'.join(
            [f'**{music.title}**' for music in data[1:]])
        if musics_str:
            await send_message(
                ctx, f'Playlist adicionada à fila:\n{musics_str}')

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
                await YoutubeDLSource.from_music_data(data),
                after=lambda _: asyncio.run_coroutine_threadsafe(
                    self.play_next(ctx), ctx.bot.loop).result())

            _voice_client.source.volume = guild_data.volume(  # type: ignore
                ctx)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)

        if _voice_client.is_paused():
            return await send_message(
                ctx, 'O player já está pausado')
        _voice_client.pause()
        await send_message(
            ctx, 'Pausado')

    @commands.command()
    async def resume(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_paused():
            return await send_message(
                ctx, 'O player já está tocando')
        _voice_client.resume()
        await send_message(
            ctx, 'Continuando')

    @commands.command()
    async def stop(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await send_message(
                ctx, 'O player já está parado')
        _voice_client.stop()
        guild_data.queue(ctx).clear()
        await send_message(
            ctx, 'Parado')

    @commands.command()
    async def skip(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await send_message(
                ctx, 'O player já está parado')
        guild_data.set_skip_flag(ctx, True)
        _voice_client.stop()
        await send_message(
            ctx, 'Pulando para a próxima música')

    @commands.command()
    async def queue(self, ctx: commands.Context):
        _queue = guild_data.queue(ctx)
        if _queue is None:
            return await send_message(
                ctx, 'Não há nada na fila')
        embed = discord.Embed(title='Fila de músicas')
        for index, data in enumerate(_queue):
            embed.add_field(name=f'{index + 1} - {data.title}',
                            value=f'**{data.url}**')
        embed.set_footer(text='Looping ativado' if guild_data.
                         is_looping(ctx) else 'Looping desativado')
        await send_message(
            ctx, embed=embed)

    @commands.command()
    async def remove(self, ctx: commands.Context, index: int):
        _queue = guild_data.queue(ctx)
        if _queue is None:
            return await send_message(
                ctx, 'Não há nada na fila')
        if index > len(_queue):
            return await send_message(
                ctx, 'Índice inválido')
        guild_data.queue(ctx).remove(index - 1)
        await send_message(
            ctx, f'Removido índice {index}')

    @commands.command()
    async def loop(self, ctx: commands.Context):
        guild_data.set_looping(ctx, not guild_data.is_looping(ctx))
        await send_message(
            ctx, 'Looping ativado' if guild_data.
            is_looping(ctx) else 'Looping desativado')

    @commands.command()
    async def shuffle(self, ctx: commands.Context):
        _queue = guild_data.queue(ctx)
        if _queue is None:
            return await send_message(
                ctx, 'Não há nada na fila')
        guild_data.queue(ctx).shuffle()  # type: ignore
        await send_message(
            ctx, 'Fila embaralhada')

    @commands.command()
    async def volume(self, ctx: commands.Context, volume: int):
        if volume > 200 or volume < 0:
            return await send_message(
                ctx, 'Volume inválido')
        _voice_client = await voice_client(ctx)
        guild_data.set_volume(ctx, volume / 100)
        if not _voice_client.is_playing():
            return
        _voice_client.source.volume = volume / 100  # type: ignore
        await send_message(
            ctx, f'Volume alterado para {volume}%')

    @commands.command()
    async def now(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        if not _voice_client.is_playing():
            return await send_message(
                ctx, 'Não estou tocando nada agora')

        await send_message(
            ctx,
            f'Tocando **{_voice_client.source.title}**')  # type: ignore

    @commands.command()
    async def join(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        await send_message(
            ctx, f'Entrando no canal **{_voice_client.channel}**')


async def setup(bot):
    await bot.add_cog(Music(bot))
