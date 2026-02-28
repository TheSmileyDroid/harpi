"""Music playback cog for Discord."""

from __future__ import annotations

from typing import cast

import discord
from discord import Guild, Member, Message, StageChannel
from discord.ext.commands import Cog, CommandError, Context, command

from src.harpi_lib.api import HarpiAPI, LoopMode
from src.harpi_lib.harpi_bot import HarpiBot

idx_count = 0


class MusicCog(Cog):
    """Discord cog for music playback commands."""

    def __init__(self, bot: HarpiBot) -> None:
        """Initialize the music cog."""
        super().__init__()

        self.bot: HarpiBot = bot
        self.api: HarpiAPI = bot.api

    async def _guild_ctx(
        self, ctx: Context
    ) -> tuple[Guild, discord.VoiceChannel, Member]:
        member: Member = cast(Member, ctx.author)

        if not member.voice:
            _ = await ctx.send("Você não está em um servidor")
            raise CommandError("Você não está em um servidor")

        voice_channel = member.voice.channel

        if voice_channel is None or isinstance(voice_channel, StageChannel):
            _ = await ctx.send("Canal de voz inválido")
            raise CommandError("Canal de voz inválido")

        if not voice_channel:
            _ = await ctx.send("Você não está em um canal de voz")
            raise CommandError("Você não está em um canal de voz")

        guild = cast(Guild, ctx.guild)
        return (guild, voice_channel, member)

    @command("join")
    async def join(self, ctx: Context) -> Message:
        """Join the user's voice channel.

        Args:
             ctx (Context): Command context.

        """
        guild, voice_channel, _ = await self._guild_ctx(ctx)

        try:
            _ = await self.api.connect_to_voice(
                guild.id, voice_channel.id, ctx
            )
        except Exception as e:
            return await ctx.send(str(e))

        return await ctx.send(
            "Conectado e pronto! Adicione músicas usando -play e adicione sons de fundo usando -add_layer!"
        )

    @command("play")
    async def play(self, ctx: Context, *, link: str) -> None:
        """Play a song.

        Arguments:
            ctx (Context): Command context.
            link (str): Link of the song to play.

        """
        guild, voice_channel, _ = await self._guild_ctx(ctx)

        await self.api.add_music_to_queue(
            guild.id, voice_channel.id, link, ctx
        )

    @command("stop")
    async def stop(self, ctx: Context) -> None:
        """Stop the current song.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        async with ctx.typing():
            guild, _, _ = await self._guild_ctx(ctx)
            await self.api.stop_music(guild.id)
            _ = await ctx.send("Música parada")

    @command("skip")
    async def skip(self, ctx: Context) -> None:
        """Skip the current song.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        async with ctx.typing():
            guild, _, _ = await self._guild_ctx(ctx)
            await self.api.skip_music(guild.id)
            _ = await ctx.send("Música pulada")

    @command("disconnect")
    async def disconnect(self, ctx: Context) -> None:
        """Disconnect the bot from the current voice channel.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the bot is not in a voice channel.
        """
        async with ctx.typing():
            guild, _, _ = await self._guild_ctx(ctx)
            await self.api.disconnect_voice(guild.id)
            _ = await ctx.send("Desconectado do canal de voz")

    @command("loop")
    async def loop(self, ctx: Context, mode: str | None) -> None:
        """Loop mode command [off, track, queue].

        Args:
            ctx (Context): Command context.
            mode (str | None): Loop mode [off, track, queue].

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        async with ctx.typing():
            if not ctx.guild:
                raise CommandError
            if mode in {"off", "false", "0", "no", "n"}:
                await self.api.set_loop(ctx.guild.id, LoopMode.OFF)
                _ = await ctx.send("Loop mode: OFF")
            elif mode in {"track", "true", "1", "yes", "y", "musica"}:
                await self.api.set_loop(ctx.guild.id, LoopMode.TRACK)
                _ = await ctx.send("Loop mode: TRACK")
            elif mode in {"queue", "fila"}:
                await self.api.set_loop(ctx.guild.id, LoopMode.QUEUE)
                _ = await ctx.send("Loop mode: QUEUE")
            else:
                _ = await ctx.send(
                    "Modo de loop inválido. Use off, track ou queue."
                )

    @command("list", aliases=["queue", "q"])
    async def list_musics(self, ctx: Context) -> None:
        """List the current music queue.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the user is not in a voice channel.
            CommandError: If the user is not in a guild.

        """
        async with ctx.typing():
            guild, _, _ = await self._guild_ctx(ctx)
            guild_config = self.api.get_guild_config(guild.id)
            if not guild_config:
                raise CommandError("Guild config not found")
            queue = guild_config.queue
            current_music = guild_config.current_music
            message_lines = []
            if current_music:
                message_lines.append(
                    f"**Tocando agora:** {current_music.title} "
                    + f"({current_music.duration})"
                )
            if queue and len(queue) > 0:
                message_lines.append("**Próximas na fila:**")
                for idx, music in enumerate(queue, start=1):
                    message_lines.append(
                        f"{idx}. {music.title} ({music.duration})"
                    )
            else:
                message_lines.append("A fila está vazia.")
            message = "\n".join(message_lines)
            _ = await ctx.send(message)

    @command("add_layer")
    async def add_layer(self, ctx: Context, *, link: str) -> Message:
        """Add a background audio layer.

        Arguments:
            ctx (Context): Command context.
            link (str): Link of the audio to play.

        """
        guild, voice_channel, _ = await self._guild_ctx(ctx)

        try:
            await self.api.add_background_audio(
                guild.id, voice_channel.id, link
            )
        except Exception as e:
            return await ctx.send(str(e))

        return await ctx.send(f"Adicionado **{link}** ao mixer.")

    @command("remove_layer")
    async def remove_layer(self, ctx: Context, index: int) -> Message:
        """Remove a specific layer by index.

        Args:
            ctx (Context): Command context.
            index (int): Index of the layer to remove (based on list_layers).

        """
        guild, _, _ = await self._guild_ctx(ctx)

        try:
            guild_config = self.api.get_guild_config(guild.id)
            if (
                not guild_config
                or not guild_config.background
                or index < 1
                or index > len(guild_config.background)
            ):
                return await ctx.send("Layer inválido.")

            # Get ID from index (background is a dict, convert to list)
            layer_items = list(guild_config.background.items())
            layer_id, layer_source = layer_items[index - 1]
            await self.api.remove_background_audio(guild.id, layer_id)
            return await ctx.send(
                f"Layer removido: {getattr(layer_source, 'title', layer_id)}"
            )
        except Exception as e:
            return await ctx.send(str(e))

    @command("clean_layers")
    async def clean_layers(self, ctx: Context) -> Message:
        """Clear all background audio layers.

        Arguments:
            ctx (Context): Command context.

        """
        guild, _, _ = await self._guild_ctx(ctx)

        try:
            await self.api.clean_background_audios(guild.id)
        except Exception as e:
            return await ctx.send(str(e))

        return await ctx.send("Layers de áudio de fundo limpos.")

    @command("list_layers")
    async def list_layers(self, ctx: Context) -> Message:
        """List the background audio layers.

        Arguments:
            ctx (Context): Command context.

        """
        guild, _, _ = await self._guild_ctx(ctx)

        try:
            guild_config = self.api.get_guild_config(guild.id)
            if not guild_config:
                return await ctx.send("Guilda não conectada")

            if not guild_config.background:
                return await ctx.send(
                    "Nenhum layer de áudio de fundo adicionado"
                )
            message_lines = ["**Layers de áudio de fundo:**"]
            for idx, layer in enumerate(guild_config.background, start=1):
                message_lines.append(f"{idx}. {layer.title}")

            message = "\n".join(message_lines)
            return await ctx.send(message)
        except Exception as e:
            return await ctx.send(str(e))
