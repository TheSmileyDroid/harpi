from __future__ import annotations

import asyncio
from typing import cast

import discord
from discord.ext.commands import Bot
from loguru import logger

from src.harpi_lib.audio.session import PlaybackSession


class SessionManager:
    """Registers and owns a :class:`PlaybackSession` per guild.

    Every verb must be awaited from the bot's event loop: ``connect`` and
    ``disconnect`` call discord.py voice APIs that only the bot loop may
    touch (docs/adr/0002).
    """

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

        When the bot already occupies the requested channel the existing
        voice client is adopted rather than rejoined, so a panel reconnect
        while the bot is in voice is cheap and never fails on a duplicate
        connection.  Moving to a different channel retires the old client
        first.  A prior manager session is reused when it already wraps the
        adopted client, otherwise it is cleaned up once the new client is
        secured.
        """
        guild = self.resolve_guild(self._bot, guild_id)
        channel = self.resolve_voice_channel(guild, channel_id)

        existing = self._sessions.get(guild_id)
        voice_client = await self._acquire_voice_client(guild, channel)

        if (
            existing is not None
            and getattr(existing, "_voice_client", None) is voice_client
        ):
            logger.info(
                f"Reused session for guild {guild.name} on channel {channel.name}"
            )
            return existing

        if existing is not None:
            existing.cleanup()
            self._sessions.pop(guild_id, None)

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

    async def _acquire_voice_client(
        self, guild: discord.Guild, channel: discord.VoiceChannel
    ) -> discord.VoiceClient:
        """Return a voice client for *channel*, adopting a live connection.

        A bot already sitting in *channel* yields its client untouched; a bot
        in another channel is disconnected before the new join, which keeps
        ``channel.connect`` from raising on a duplicate connection.
        """
        current = cast("discord.VoiceClient | None", guild.voice_client)
        if current is not None and current.is_connected():
            if getattr(current.channel, "id", None) == channel.id:
                return current
            await self._release_voice_client(current, guild.id)
        return await self._join_channel(channel)

    async def _release_voice_client(
        self, voice_client: discord.VoiceClient, guild_id: int
    ) -> None:
        try:
            await voice_client.disconnect()
        except Exception:
            logger.opt(exception=True).warning(
                f"Error disconnecting existing voice client for guild {guild_id}"
            )

    async def _join_channel(
        self, channel: discord.VoiceChannel
    ) -> discord.VoiceClient:
        try:
            return await channel.connect()
        except discord.ClientException as e:
            raise ValueError(f"Cannot connect to voice channel: {e}") from e
        except asyncio.TimeoutError as e:
            raise ValueError("Voice connection timed out") from e

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

        When no session is registered but the bot still occupies a voice
        channel, that orphaned client is disconnected instead of raising, so
        the panel can always release the bot.  The registry entry is removed
        before the voice client is asked to disconnect, so the
        ``on_voice_state_update`` event that discord.py fires for this
        deliberate leave finds no session and does nothing.
        """
        session = self._sessions.get(guild_id)
        if session is None:
            await self._disconnect_orphaned_voice(guild_id)
            return

        del self._sessions[guild_id]
        try:
            session.cleanup()
        except Exception:
            logger.opt(exception=True).warning(
                f"Error cleaning up session for guild {guild_id}"
            )
        await session.leave()
        logger.info(f"Disconnected and cleaned up guild {guild_id}")

    async def _disconnect_orphaned_voice(self, guild_id: int) -> None:
        guild = self._bot.get_guild(guild_id)
        voice_client = getattr(guild, "voice_client", None)
        if voice_client is None or not voice_client.is_connected():
            raise ValueError("Guilda não conectada")
        await voice_client.disconnect()
        logger.info(f"Disconnected orphaned voice client for guild {guild_id}")

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
