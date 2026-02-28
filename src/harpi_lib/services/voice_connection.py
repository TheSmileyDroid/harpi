"""Voice connection management service.

Thread safety
-------------
``connect_to_voice`` and ``disconnect`` call discord.py APIs which must
run on the **bot's** event loop.  When invoked from Quart handlers (which
run on a separate event loop in a different thread), callers must wrap
calls with ``run_on_bot_loop()`` (see ``src.api.deps``).

The ``guilds`` dict is mutated here (insert in ``connect_to_voice``,
delete in ``disconnect``), but these mutations only happen on the bot's
event loop, so no lock is required.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, cast

import discord
from discord.channel import VoiceChannel
from discord.ext.commands import Bot, Context
from loguru import logger

from src.harpi_lib.music.mixer import MixerSource
from src.harpi_lib.music.soundboard import SoundboardController

if TYPE_CHECKING:
    from src.harpi_lib.api import GuildConfig, SoundboardGraph


class VoiceConnectionService:
    """Manages voice channel connections and guild lifecycle."""

    def __init__(
        self,
        bot: Bot,
        guilds: dict[int, GuildConfig],
        on_queue_end: Callable,
        on_track_end: Callable,
    ) -> None:
        self.bot = bot
        self.guilds = guilds
        self._on_queue_end = on_queue_end
        self._on_track_end = on_track_end

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
    ) -> VoiceChannel:
        """Resolve a voice channel from a guild and channel ID."""
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, VoiceChannel):
            raise ValueError("Canal de voz não encontrado")
        return channel

    async def connect(
        self, guild_id: int, channel_id: int, ctx: Context | None = None
    ) -> GuildConfig:
        """Connect to a voice channel and create a guild config."""
        from src.harpi_lib.api import GuildConfig, SoundboardGraph

        guild = self.resolve_guild(self.bot, guild_id)
        channel = self.resolve_voice_channel(guild, channel_id)

        voice: discord.VoiceClient | None = cast(
            "discord.VoiceClient | None", guild.voice_client
        )
        if voice:
            try:
                await voice.disconnect()
            except Exception:
                logger.opt(exception=True).warning(
                    f"Error disconnecting existing voice client for guild {guild_id}"
                )

        try:
            vc = await channel.connect()
        except discord.ClientException as e:
            raise ValueError(f"Cannot connect to voice channel: {e}") from e
        except asyncio.TimeoutError as e:
            raise ValueError("Voice connection timed out") from e

        controller = SoundboardController()
        mixer = MixerSource(controller)
        guild_config = GuildConfig(
            id=guild.id,
            mixer=mixer,
            controller=controller,
            ctx=ctx,
            voice_client=vc,
            channel=channel,
            soundboard_graph=SoundboardGraph(
                nodes=[
                    {
                        "id": "output-1",
                        "type": "output",
                        "data": {"volume": 100},
                        "position": {"x": 400, "y": 300},
                    }
                ],
                edges=[],
            ),
        )
        callback = cast(
            Callable,
            partial(self._on_queue_end, guild_config=guild_config),
        )
        bg_callback = cast(
            Callable,
            partial(self._on_track_end, guild_config=guild_config),
        )
        mixer.add_observer("queue_end", callback)
        mixer.add_observer("track_end", bg_callback)
        guild_config.ctx = ctx
        self.guilds[guild.id] = guild_config
        vc.play(mixer)
        logger.info(
            f"Connected to voice channel {channel.name} in guild {guild.name}"
        )

        return guild_config

    async def disconnect(self, guild_id: int) -> None:
        """Disconnect from voice and clean up all audio resources."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")

        # Clean up all audio resources before disconnecting
        try:
            guild_config.controller.cleanup_all()
        except Exception:
            logger.opt(exception=True).warning(
                f"Error cleaning up controller for guild {guild_id}"
            )

        # Clean up prepared sources (FFmpeg subprocesses)
        for node_id, source in list(guild_config.prepared_sources.items()):
            try:
                if hasattr(source, "cleanup"):
                    source.cleanup()
            except Exception:
                logger.opt(exception=True).warning(
                    f"Error cleaning up prepared source {node_id}"
                )
        guild_config.prepared_sources.clear()

        # Clean up the mixer's thread pool
        try:
            guild_config.mixer.cleanup()
        except Exception:
            logger.opt(exception=True).warning(
                f"Error cleaning up mixer for guild {guild_id}"
            )

        # Disconnect from voice
        voice_client = guild_config.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()

        del self.guilds[guild_id]
        logger.info(f"Disconnected and cleaned up guild {guild_id}")
