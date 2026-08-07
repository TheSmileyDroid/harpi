"""SessionManager — the registry and lifecycle for per-guild sessions.

The manager owns the map of guild IDs to :class:`PlaybackSession` objects.
Sessions are created on ``connect``, found by ``get`` / ``ensure``
(connect-if-missing), and torn down by ``disconnect``.  When the bot is
kicked or otherwise unexpectedly leaves a voice channel, the manager's
``on_voice_state_update`` handler cleans the session up so no ghost session
lingers.  This is the seam the cogs, routes, and tests cross instead of the
controller, the mixer, or the voice client directly.

Threading contract
------------------
Every manager verb is async and must be awaited from the **bot's** event
loop: ``connect`` and ``disconnect`` call discord.py voice APIs that only
the bot loop may touch.  The full contract lives in the PlaybackSession
module.
"""

from __future__ import annotations

import asyncio
from typing import cast

import discord
from discord.ext.commands import Bot
from loguru import logger

from src.harpi_lib.audio.session import PlaybackSession


class SessionManager:
    """Registers and owns a :class:`PlaybackSession` per guild."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._sessions: dict[int, PlaybackSession] = {}

    @staticmethod
    def resolve_guild(bot: Bot, guild_id: int) -> discord.Guild:
        """Resolve a guild object from its ID."""
        guild = bot.get_guild(guild_id)
        if not guild:
            raise ValueError("Servidor não encontrado")
        return guild

    @staticmethod
    def resolve_voice_channel(
        guild: discord.Guild, channel_id: int
    ) -> discord.VoiceChannel:
        """Resolve a connectable voice channel from a guild and channel ID."""
        channel = guild.get_channel(channel_id)
        if channel is None or not hasattr(channel, "connect"):
            raise ValueError("Canal de voz não encontrado")
        return cast("discord.VoiceChannel", channel)

    async def connect(self, guild_id: int, channel_id: int) -> PlaybackSession:
        """Connect to a voice channel and register a session for the guild.

        Any session the manager already holds for the guild, and any voice
        client the guild already has, are retired only after the new
        connection succeeds — a failed connect leaves them intact.
        """
        guild = self.resolve_guild(self._bot, guild_id)
        channel = self.resolve_voice_channel(guild, channel_id)

        existing = self._sessions.get(guild_id)
        old_voice = cast("discord.VoiceClient | None", guild.voice_client)

        try:
            voice_client = await channel.connect()
        except discord.ClientException as e:
            raise ValueError(f"Cannot connect to voice channel: {e}") from e
        except asyncio.TimeoutError as e:
            raise ValueError("Voice connection timed out") from e

        if existing is not None:
            existing.cleanup()
            self._sessions.pop(guild_id, None)
        if old_voice is not None and old_voice is not voice_client:
            try:
                await old_voice.disconnect()
            except Exception:
                logger.opt(exception=True).warning(
                    f"Error disconnecting existing voice client for guild {guild_id}"
                )

        session = PlaybackSession(
            guild_id=guild.id,
            voice_client=voice_client,
            loop=self._bot.loop,
        )
        session.start()
        self._sessions[guild.id] = session
        logger.info(
            f"Connected to voice channel {channel.name} in guild {guild.name}"
        )
        return session

    async def ensure(self, guild_id: int, channel_id: int) -> PlaybackSession:
        """Return the guild's session, connecting first if none exists."""
        session = self.get(guild_id)
        if session is None:
            session = await self.connect(guild_id, channel_id)
        return session

    def get(self, guild_id: int) -> PlaybackSession | None:
        """Return the guild's session, or None if it is not connected."""
        return self._sessions.get(guild_id)

    async def disconnect(self, guild_id: int) -> None:
        """Tear the guild's session down: release audio and leave voice.

        The registry entry is removed before the voice client is asked to
        disconnect, so the ``on_voice_state_update`` event that discord.py
        fires for this deliberate leave finds no session and does nothing.
        """
        session = self._sessions.get(guild_id)
        if session is None:
            raise ValueError("Guilda não conectada")

        del self._sessions[guild_id]
        try:
            session.cleanup()
        except Exception:
            logger.opt(exception=True).warning(
                f"Error cleaning up session for guild {guild_id}"
            )
        await session.leave()
        logger.info(f"Disconnected and cleaned up guild {guild_id}")

    async def on_voice_state_update(
        self,
        member: discord.Member,
        _before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Tear down a session when the bot leaves voice unexpectedly.

        Ignores every member that is not the bot, and ignores moves between
        channels (the bot is still in some channel).  A deliberate
        ``disconnect`` removes the session from the registry before the
        voice state change lands, so this handler never double-tears-down.
        """
        user = self._bot.user
        if user is None or member.id != user.id:
            return
        guild = member.guild
        if guild is None:
            return
        if after.channel is not None:
            return
        session = self._sessions.get(guild.id)
        if session is None:
            return
        session.cleanup()
        del self._sessions[guild.id]
        logger.info(
            f"Tore down session for guild {guild.id} after unexpected disconnect"
        )
