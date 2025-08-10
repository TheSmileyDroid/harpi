"""Funções auxiliares para manipulação de áudio compartilhadas entre módulos."""

from __future__ import annotations

from typing import cast

import discord
import discord.ext.commands as commands


def voice_state(ctx: commands.Context) -> discord.VoiceState:
    """Obtém o estado de voz do autor do comando.

    Args:
        ctx (commands.Context): Contexto do comando.

    Raises:
        commands.CommandError: Se o autor não estiver em um canal de voz.

    Returns:
        discord.VoiceState: Estado de voz do autor.
    """
    if not isinstance(ctx.author, discord.Member):
        raise commands.CommandError("Você não está em um canal de voz")
    if ctx.author.voice is None:
        raise commands.CommandError("Você não está em um canal de voz")
    return ctx.author.voice


def voice_channel(ctx: commands.Context) -> discord.VoiceChannel:
    """Obtém o canal de voz do autor do comando.

    Args:
        ctx (commands.Context): Contexto do comando.

    Raises:
        commands.CommandError: Se o autor não estiver em um canal de voz.

    Returns:
        discord.VoiceChannel: Canal de voz do autor.
    """
    _voice_state = voice_state(ctx)
    if _voice_state.channel is None:
        raise commands.CommandError("Você não está em um canal de voz")
    return cast("discord.VoiceChannel", _voice_state.channel)


def guild(ctx: commands.Context) -> discord.Guild:
    """Obtém a guilda do comando.

    Args:
        ctx (commands.Context): Contexto do comando.

    Raises:
        commands.NoPrivateMessage: Se o comando for usado em mensagem privada.

    Returns:
        discord.Guild: Guilda do comando.
    """
    if ctx.guild is None:
        raise commands.NoPrivateMessage(
            "Este comando não pode ser usado em DMs.",
        )
    return ctx.guild


async def voice_client(ctx: commands.Context) -> discord.VoiceClient:
    """Obtém ou cria um cliente de voz.

    Args:
        ctx (commands.Context): Contexto do comando.

    Returns:
        discord.VoiceClient: Cliente de voz.
    """
    voice = cast(
        discord.VoiceClient | None,
        discord.utils.get(ctx.bot.voice_clients, guild=guild(ctx)),
    )
    if voice is None:
        _voice_channel = voice_channel(ctx)
        voice = await _voice_channel.connect()
    return voice


class AlreadyPlaying(commands.CommandError):
    """Exceção lançada quando já há uma reprodução em andamento."""
