import discord
from discord.ext import commands

from .interfaces.imusicqueue import IMusicQueue

from .utils.musicplayer import MusicPlayer

from .interfaces.imessageparser import IMessageParser


from .utils.guild import guild, guild_data
from .utils.send import EmbeddedMessage, Message


def voice_state(
    ctx: commands.Context,
) -> discord.VoiceState:
    if not isinstance(ctx.author, discord.Member):
        raise commands.CommandError("Você não está em um canal de voz")
    if ctx.author.voice is None:
        raise commands.CommandError("Você não está em um canal de voz")
    return ctx.author.voice


def voice_channel(
    ctx: commands.Context,
) -> discord.channel.VocalGuildChannel:
    _voice_state = voice_state(ctx)
    if _voice_state.channel is None:
        raise commands.CommandError("Você não está em um canal de voz")
    return _voice_state.channel


async def voice_client(
    ctx: commands.Context,
) -> discord.VoiceClient:
    voice = discord.utils.get(ctx.bot.voice_clients, guild=guild(ctx))
    if voice is None:
        _voice_channel = voice_channel(ctx)
        voice = await _voice_channel.connect()
    return voice


class MessageSender(IMessageParser):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx

    async def send(self, content: str):
        await Message(self.ctx, content).send()


class Music(commands.Cog):
    @commands.command()
    async def play(self, ctx: commands.Context, *, args: str):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).play(args)

    @commands.command()
    async def pause(self, ctx: commands.Context):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).pause()

    @commands.command()
    async def resume(self, ctx: commands.Context):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).resume()

    @commands.command()
    async def stop(self, ctx: commands.Context):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).stop()

    @commands.command()
    async def skip(self, ctx: commands.Context):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).skip()

    @commands.command()
    async def queue(self, ctx: commands.Context):
        _queue: IMusicQueue = guild_data.queue(ctx)
        if _queue is None:
            return await Message(ctx, "Não há nada na fila").send()
        embed = discord.Embed(title="Fila de músicas")
        embed.add_field(
            name="Looping",
            value="Looping ativado"
            if guild_data.is_looping(ctx)
            else "Looping desativado",
            inline=False,
        )
        for index, data in enumerate(_queue):
            embed.add_field(
                name=f"{index} - {data.get_title()}",
                value=f"**{data.get_url()}**",
            )

        embed.set_footer(
            text="Harpi Bot",
        )
        await EmbeddedMessage(ctx, embed=embed).send()

    @commands.command()
    async def remove(self, ctx: commands.Context, args: int):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).remove(args)

    @commands.command()
    async def loop(self, ctx: commands.Context):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).set_loop(loop=not guild_data.is_looping(ctx))

    @commands.command()
    async def set_loop(self, ctx: commands.Context, loop: bool):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).set_loop(loop=loop)

    @commands.command()
    async def shuffle(self, ctx: commands.Context):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).shuffle()

    @commands.command()
    async def volume(self, ctx: commands.Context, args: int):
        await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).set_volume(args)

    @commands.command()
    async def now(self, ctx: commands.Context):
        current = await MusicPlayer(
            guild_data, ctx, await voice_client(ctx), MessageSender(ctx)
        ).get_current()

        if current is None:
            return await Message(ctx, "Não há nada tocando").send()

        embed = discord.Embed(title="Tocando agora")
        embed.add_field(
            name=f"{current.get_title()}",
            value=f"**{current.get_url()}**",
        )
        await EmbeddedMessage(ctx, embed=embed).send()

    @commands.command()
    async def join(self, ctx: commands.Context):
        _voice_client = await voice_client(ctx)
        await Message(
            ctx,
            f"Entrando no canal **{_voice_client.channel}**",
        ).send()


async def setup(bot):
    await bot.add_cog(Music(bot))
