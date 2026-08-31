from __future__ import annotations

from typing import cast

import discord
from discord import Guild, Member, Message, StageChannel
from discord.ext.commands import Cog, CommandError, Context, command

from src.harpi_lib.audio.session import (
    LOOP_MODE_ALIASES,
    PlaybackSession,
    SessionStatus,
)
from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.parse import parse_finite_float


def _queue_message(status: SessionStatus) -> str:
    message_lines = []
    if status.current_music:
        message_lines.append(
            f"**Tocando agora:** {status.current_music.title} "
            + f"({status.current_music.duration})"
        )
    if status.queue:
        message_lines.append("**Próximas na fila:**")
        for idx, music in enumerate(status.queue, start=1):
            message_lines.append(f"{idx}. {music.title} ({music.duration})")
    else:
        message_lines.append("A fila está vazia.")
    return "\n".join(message_lines)


def _layers_message(status: SessionStatus) -> str:
    if not status.layers:
        return "Nenhum layer de áudio de fundo adicionado"
    message_lines = ["**Layers de áudio de fundo:**"]
    for idx, layer in enumerate(status.layers, start=1):
        message_lines.append(f"{idx}. {layer.title}")
    return "\n".join(message_lines)


class MusicCog(Cog):
    def __init__(self, bot: HarpiBot) -> None:
        """Initialize the music cog."""
        super().__init__()

        self.bot: HarpiBot = bot

    async def _resolve_voice_context(
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

    async def _require_session(self, ctx: Context) -> PlaybackSession | None:
        """Resolve the user's voice context and return the guild's session.

        Returns ``None`` and announces "Guilda não conectada" when the guild
        has no session.  When a session exists its announcer is bound to
        ``ctx.send`` so load failures are announced in the channel.
        """
        guild, _, _ = await self._resolve_voice_context(ctx)
        session = self.bot.sessions.get(guild.id)
        if session is None:
            await ctx.send("Guilda não conectada")
            return None
        session.set_announcer(ctx.send)
        return session

    async def _simple_verb(self, ctx: Context, verb: str, reply: str) -> None:
        """Run *verb* on the session and send *reply*."""
        async with ctx.typing():
            session = await self._require_session(ctx)
            if session is None:
                return
            await getattr(session, verb)()
            _ = await ctx.send(reply)

    async def _connect_session(
        self, ctx: Context, *, force: bool
    ) -> PlaybackSession:
        """Resolve the user's voice context and return the guild's session.

        With *force* set the session is re-created by connecting afresh
        (join); otherwise an existing session is reused (play).  The
        session's announcer is bound to ``ctx.send`` so load failures are
        announced in the channel.
        """
        guild, voice_channel, _ = await self._resolve_voice_context(ctx)
        if force:
            session = await self.bot.sessions.connect(
                guild.id, voice_channel.id
            )
        else:
            session = await self.bot.sessions.ensure(
                guild.id, voice_channel.id
            )
        session.set_announcer(ctx.send)
        return session

    @command("join")
    async def join(self, ctx: Context) -> Message:
        """Join the user's voice channel.

        Args:
             ctx (Context): Command context.

        """
        try:
            _ = await self._connect_session(ctx, force=True)
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
        session = await self._connect_session(ctx, force=False)
        try:
            count = await session.play(link)
        except ValueError as e:
            await ctx.send(str(e))
            return
        await ctx.send(f"Adicionada(s) {count} música(s) à fila.")

    @command("stop")
    async def stop(self, ctx: Context) -> None:
        """Stop the current song.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        await self._simple_verb(ctx, "stop", "Música parada")

    @command("skip")
    async def skip(self, ctx: Context) -> None:
        """Skip the current song.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        await self._simple_verb(ctx, "skip", "Música pulada")

    @command("seek")
    async def seek(self, ctx: Context, position: str) -> None:
        """Seek to a position in the current track.

        Arguments:
            ctx (Context): Command context.
            position (str): Absolute position in seconds, or a +/- offset for relative seek.

        Raises:
            CommandError: If the user is not in a voice channel.

        """
        async with ctx.typing():
            session = await self._require_session(ctx)
            if session is None:
                return
            target = parse_finite_float(position)
            if target is None:
                _ = await ctx.send("Posição inválida")
                return
            absolute = not position.startswith(("+", "-"))
            try:
                moved = await session.seek(target, absolute=absolute)
            except ValueError:
                _ = await ctx.send("Posição inválida")
                return
            if moved:
                _ = await ctx.send("Posição alterada")

    @command("disconnect")
    async def disconnect(self, ctx: Context) -> None:
        """Disconnect the bot from the current voice channel.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the bot is not in a voice channel.
        """
        async with ctx.typing():
            guild, _, _ = await self._resolve_voice_context(ctx)
            try:
                await self.bot.sessions.disconnect(guild.id)
            except ValueError as e:
                _ = await ctx.send(str(e))
                return
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
            session = await self._require_session(ctx)
            if session is None:
                return
            loop_mode = LOOP_MODE_ALIASES.get(mode) if mode else None
            if loop_mode is None:
                _ = await ctx.send(
                    "Modo de loop inválido. Use off, track ou queue."
                )
                return
            await session.set_loop(loop_mode)
            _ = await ctx.send(f"Loop mode: {loop_mode.name}")

    @command("volume")
    async def volume(self, ctx: Context, level: str | None = None) -> None:
        """Show or set the music volume (0.0-2.0).

        Arguments:
            ctx (Context): Command context.
            level (str | None): New volume level, or omit to show the current one.

        """
        async with ctx.typing():
            session = await self._require_session(ctx)
            if session is None:
                return
            if level is None:
                _ = await ctx.send(
                    f"Volume atual: {session.status.volume:.2f}"
                )
                return
            target = parse_finite_float(level)
            if target is None:
                _ = await ctx.send("Volume inválido")
                return
            await session.set_volume(target)
            _ = await ctx.send(
                f"Volume definido para {session.status.volume:.2f}"
            )

    @command("pause")
    async def pause(self, ctx: Context) -> None:
        """Pause the current track.

        Arguments:
            ctx (Context): Command context.

        """
        await self._simple_verb(ctx, "pause", "Música pausada")

    @command("resume")
    async def resume(self, ctx: Context) -> None:
        """Resume the current track.

        Arguments:
            ctx (Context): Command context.

        """
        await self._simple_verb(ctx, "resume", "Música retomada")

    @command("list", aliases=["queue", "q"])
    async def list_queue(self, ctx: Context) -> None:
        """List the current music queue.

        Args:
            ctx (Context): Command context.

        Raises:
            CommandError: If the user is not in a voice channel.
            CommandError: If the user is not in a guild.

        """
        async with ctx.typing():
            session = await self._require_session(ctx)
            if session is None:
                return
            _ = await ctx.send(_queue_message(session.status))

    @command("add_layer")
    async def add_layer(self, ctx: Context, *, link: str) -> None:
        """Add a background audio layer.

        Arguments:
            ctx (Context): Command context.
            link (str): Link of the audio to play.

        """
        session = await self._connect_session(ctx, force=False)
        try:
            await session.add_layer(link)
        except ValueError as e:
            _ = await ctx.send(str(e))
            return
        _ = await ctx.send(f"Adicionado **{link}** ao mixer.")

    @command("remove_layer")
    async def remove_layer(self, ctx: Context, index: int) -> None:
        """Remove a specific layer by index.

        Args:
            ctx (Context): Command context.
            index (int): Index of the layer to remove (based on list_layers).

        """
        async with ctx.typing():
            session = await self._require_session(ctx)
            if session is None:
                return
            status = session.status
            if index < 1 or index > len(status.layers):
                _ = await ctx.send("Layer inválido.")
                return
            layer = status.layers[index - 1]
            await session.remove_layer(layer.id)
            _ = await ctx.send(f"Layer removido: {layer.title}")

    @command("clean_layers")
    async def clean_layers(self, ctx: Context) -> None:
        """Clear all background audio layers.

        Arguments:
            ctx (Context): Command context.

        """
        await self._simple_verb(
            ctx, "clear_layers", "Layers de áudio de fundo limpos."
        )

    @command("list_layers")
    async def list_layers(self, ctx: Context) -> None:
        """List the background audio layers.

        Arguments:
            ctx (Context): Command context.

        """
        async with ctx.typing():
            session = await self._require_session(ctx)
            if session is None:
                return
            _ = await ctx.send(_layers_message(session.status))
