"""Módulo responsável por tocar músicas."""

from __future__ import annotations

import enum
import logging
from typing import cast

import discord
import discord.ext
import discord.ext.commands
from discord import Guild, Member, Message
from discord.ext.commands import Cog, CommandError, Context, command

from src.HarpiLib.api import HarpiAPI

from src.HarpiLib.HarpiBot import HarpiBot

logger = logging.getLogger(__name__)


class LoopMode(enum.Enum):
    """Enum que representa o modo de loop."""

    OFF = 0
    TRACK = 1
    QUEUE = 2


idx_count = 0


class MusicCog(Cog):
    """Cog responsável por tocar músicas."""

    def __init__(self, bot: HarpiBot) -> None:
        """Inicializa o cog."""
        super().__init__()

        self.bot: HarpiBot = bot
        self.api: HarpiAPI = bot.api

    async def _guild_ctx(self, ctx: Context):
        member: Member = cast(Member, ctx.author)

        if not member.voice:
            _ = await ctx.send("Você não está em um servidor")
            raise CommandError("Você não está em um servidor")

        voice_channel = member.voice.channel

        if not voice_channel:
            _ = await ctx.send("Você não está em um canal de voz")
            raise CommandError("Você não está em um canal de voz")

        guild = cast(Guild, ctx.guild)
        return (guild, voice_channel, member)

    @command("join")
    async def join(self, ctx: Context) -> Message:
        """Entra no canal de voz do usuário.

        Args:
             ctx (Context): Contexto do comando.

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
        """Toca uma música.

        Arguments:
            ctx (Context): Contexto do comando.
            link (str): Link da música a ser tocada.

        """
        guild, voice_channel, _ = await self._guild_ctx(ctx)

        await self.api.add_music_to_queue(
            guild.id, voice_channel.id, link, ctx
        )

    @command("stop")
    async def stop(self, ctx: Context) -> None:
        """Para a música atual.

        Args:
            ctx (Context): Contexto do comando.

        Raises:
            CommandError: Se o usuário não estiver em um canal de voz.

        """
        async with ctx.typing():
            guild, _, _ = await self._guild_ctx(ctx)
            await self.api.stop_music(guild.id)
            _ = await ctx.send("Música parada")

    @command("skip")
    async def skip(self, ctx: Context) -> None:
        """Pula a música atual.

        Args:
            ctx (Context): Contexto do comando.

        Raises:
            CommandError: Se o usuário não estiver em um canal de voz.

        """
        async with ctx.typing():
            guild, _, _ = await self._guild_ctx(ctx)
            await self.api.skip_music(guild.id)
            _ = await ctx.send("Música pulada")

    @command("disconnect")
    async def disconnect(self, ctx: Context) -> None:
        """Desconecta o bot do canal de voz atual.

        Args:
            ctx (Context): Contexto do comando.

        Raises:
            CommandError: Se o bot não estiver em um canal de voz.
        """
        async with ctx.typing():
            guild, _, _ = await self._guild_ctx(ctx)
            await self.api.disconnect_voice(guild.id)
            _ = await ctx.send("Desconectado do canal de voz")

    @command("loop")
    async def loop(self, ctx: Context, mode: str | None) -> None:
        """Loop mode command [off, track, queue].

        Args:
            ctx (Context): Contexto do comando.
            mode (str | None): Loop mode [off, track, queue].

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        async with ctx.typing():
            if not ctx.guild:
                raise CommandError
            if mode in {"off", "false", "0", "no", "n"}:
                await self.api.set_loop(ctx.guild.id, False)
                _ = await ctx.send("Loop mode: OFF")
            elif mode in {"track", "true", "1", "yes", "y", "musica"}:
                await self.api.set_loop(ctx.guild.id, True)
                _ = await ctx.send("Loop mode: TRACK")
            elif mode in {"queue", "fila"}:
                await self.api.set_loop(ctx.guild.id, True)
                _ = await ctx.send("Loop mode: QUEUE")
            else:
                _ = await ctx.send(
                    "Modo de loop inválido. Use off, track ou queue."
                )

    @command("list", aliases=["queue", "q"])
    async def list_musics(self, ctx: Context) -> None:
        """List the current music queue.

        Args:
            ctx (Context): Contexto do comando.

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
        """Adiciona um layer.

        Arguments:
            ctx (Context): Contexto do comando.
            link (str): Link da música a ser tocada.

        """
        guild, voice_channel, _ = await self._guild_ctx(ctx)

        try:
            await self.api.add_background_audio(
                guild.id, voice_channel.id, link
            )
        except Exception as e:
            return await ctx.send(str(e))

        return await ctx.send(f"Adicionado **{link}** ao mixer.")

    @command("clean_layers")
    async def clean_layers(self, ctx: Context) -> Message:
        """Limpa os layers de áudio de fundo.

        Arguments:
            ctx (Context): Contexto do comando.

        """
        guild, _, _ = await self._guild_ctx(ctx)

        try:
            await self.api.clean_background_audios(guild.id)
        except Exception as e:
            return await ctx.send(str(e))

        return await ctx.send("Layers de áudio de fundo limpos.")

    @command("list_layers")
    async def list_layers(self, ctx: Context) -> Message:
        """Lista os layers de áudio de fundo.

        Arguments:
            ctx (Context): Contexto do comando.

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
