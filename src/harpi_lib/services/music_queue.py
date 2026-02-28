"""Music queue management service.

Thread safety
-------------
The ``on_queue_end`` and ``on_track_end`` callbacks are invoked from
discord.py's **voice-sending thread** (via ``MixerSource.read()``).  They
must not call asyncio APIs that are not thread-safe or directly mutate
shared data structures that the bot/Quart event loops also access.

* ``on_queue_end`` uses ``asyncio.run_coroutine_threadsafe`` to schedule
  the ``next_music`` coroutine on the bot's event loop.
* ``on_track_end`` uses ``bot.loop.call_soon_threadsafe`` to schedule dict
  mutations on the bot's event loop rather than mutating directly.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Bot, Context
from loguru import logger

from src.harpi_lib.musicdata.ytmusicdata import YoutubeDLSource, YTMusicData

if TYPE_CHECKING:
    from src.harpi_lib.api import GuildConfig, LoopMode
    from src.harpi_lib.services.voice_connection import VoiceConnectionService


class MusicQueueService:
    """Manages the music playback queue."""

    def __init__(
        self,
        bot: Bot,
        guilds: dict[int, GuildConfig],
        voice_service: VoiceConnectionService,
    ) -> None:
        self.bot = bot
        self.guilds = guilds
        self.voice_service = voice_service

    def on_queue_end(self, guild_config: GuildConfig) -> None:
        """Callback when the current track ends.

        Called from the voice-sending thread — uses
        ``run_coroutine_threadsafe`` instead of ``create_task``.
        """
        asyncio.run_coroutine_threadsafe(
            self.next_music(guild_config), self.bot.loop
        )

    def on_track_end(
        self,
        guild_config: GuildConfig,
        to_remove: list[discord.AudioSource],
    ) -> None:
        """Callback when a background track ends.

        Called from the voice-sending thread — schedules dict mutation on
        the bot's event loop via ``call_soon_threadsafe``.
        """
        for source in to_remove:
            layer_id = guild_config.controller.get_layer_id(source)
            if layer_id:
                guild_config.controller.remove_layer(layer_id)
                # Schedule the background-dict mutation on the bot's event loop
                # to avoid cross-thread dict modification.
                self.bot.loop.call_soon_threadsafe(
                    self._remove_background_layer, guild_config, layer_id
                )

    @staticmethod
    def _remove_background_layer(
        guild_config: GuildConfig, layer_id: str
    ) -> None:
        """Remove a background layer entry (runs on the bot's event loop)."""
        if guild_config.background and layer_id in guild_config.background:
            del guild_config.background[layer_id]

    async def next_music(
        self, guild_config: GuildConfig, force_next: bool = False
    ) -> None:
        """Schedule the next track to play."""
        from src.harpi_lib.api import LoopMode

        try:
            await self._next_music_inner(guild_config, force_next)
        except Exception:
            logger.opt(exception=True).error(
                f"Failed to advance queue for guild {guild_config.id}"
            )
            # Clear current track so the queue doesn't get stuck
            guild_config.current_music = None
            guild_config.controller.clear_queue_source()

    async def _next_music_inner(
        self, guild_config: GuildConfig, force_next: bool = False
    ) -> None:
        """Prepare and play the next queued track."""
        from src.harpi_lib.api import LoopMode

        if guild_config.current_music:
            if guild_config.loop == LoopMode.TRACK and not force_next:
                logger.debug(
                    f"Looping track '{guild_config.current_music.title}' "
                    f"in guild {guild_config.id}"
                )
                source = await YoutubeDLSource.from_music_data(
                    guild_config.current_music, volume=guild_config.volume
                )
                source.volume = guild_config.volume
                guild_config.controller.set_queue_source(source)
                return

            if guild_config.loop == LoopMode.QUEUE:
                if not guild_config.queue:
                    guild_config.queue = []
                guild_config.queue.append(guild_config.current_music)

        if not guild_config.queue or len(guild_config.queue) == 0:
            logger.debug(f"Queue empty for guild {guild_config.id}")
            guild_config.current_music = None
            guild_config.controller.clear_queue_source()
            return

        music_data = guild_config.queue.pop(0)
        guild_config.current_music = music_data
        logger.info(
            f"Playing next track '{music_data.title}' in guild {guild_config.id}"
        )
        source = await YoutubeDLSource.from_music_data(
            music_data, volume=guild_config.volume
        )
        source.volume = guild_config.volume
        guild_config.controller.set_queue_source(source)

    async def add_to_queue(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ) -> None:
        """Add a track URL to the music queue."""
        music_data_list = await YTMusicData.from_url(link)
        if not music_data_list:
            raise ValueError(f"No audio found for URL: {link}")
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            guild_config = await self.voice_service.connect(
                guild_id, channel_id, ctx
            )
        if not guild_config.queue:
            guild_config.queue = []
        guild_config.queue.extend(music_data_list)
        logger.info(
            f"Added {len(music_data_list)} track(s) to queue in guild {guild_id}"
        )
        if not guild_config.current_music:
            await self.next_music(guild_config)

    async def stop(self, guild_id: int) -> None:
        """Stop current playback and clear the queue."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if not guild_config.queue:
            guild_config.queue = []
        guild_config.queue.clear()
        guild_config.controller.clear_queue_source()
        guild_config.current_music = None
        logger.info(f"Stopped music and cleared queue in guild {guild_id}")

    async def skip(self, guild_id: int) -> None:
        """Skip the current track and play the next."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        logger.info(f"Skipping track in guild {guild_id}")
        await self.next_music(guild_config, force_next=True)

    async def set_loop(self, guild_id: int, loop: LoopMode) -> None:
        """Set the loop mode (off, track, or queue)."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        guild_config.loop = loop

    async def set_volume(self, guild_id: int, volume: float) -> None:
        """Set the playback volume for the music queue."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")

        guild_config.volume = max(0.0, min(2.0, volume))
        queue_source = guild_config.controller.get_queue_source()
        if queue_source and hasattr(queue_source, "volume"):
            try:
                queue_source.volume = guild_config.volume  # type: ignore
            except Exception as e:
                logger.opt(exception=True).error(
                    f"Error while setting volume for music in guild {guild_id}: {e}"
                )
