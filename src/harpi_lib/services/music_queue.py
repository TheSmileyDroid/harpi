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
import math
from typing import TYPE_CHECKING, Callable, cast

import discord
from discord.ext.commands import Bot, Context
from loguru import logger

from src.harpi_lib.music.ytmusicdata import YoutubeDLSource, YTMusicData

if TYPE_CHECKING:
    from src.harpi_lib.api import GuildConfig, LoopMode
    from src.harpi_lib.services.voice_connection import VoiceConnectionService


# Fallback seek cap in seconds for tracks with unknown duration.
MAX_SEEK_SECONDS = 4 * 3600

# Max seconds allowed for loading a track's audio source before it is
# treated as failed and skipped.  Covers the fallback extraction budget
# plus the stream playability/silence probe.
TRACK_LOAD_TIMEOUT = 60.0


class MusicQueueService:
    """Manages the music playback queue."""

    def __init__(
        self,
        bot: Bot,
        guilds: dict[int, GuildConfig],
        voice_service: VoiceConnectionService | None = None,
    ) -> None:
        self.bot = bot
        self.guilds = guilds
        self.voice_service = voice_service

    def on_queue_end(self, guild_config: GuildConfig) -> None:
        """Callback when the current track ends.

        Called from the voice-sending thread - uses
        run_coroutine_threadsafe instead of create_task.
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

        Called from the voice-sending thread - schedules dict mutation on
        the bot's event loop via call_soon_threadsafe.
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

        try:
            await self._next_music_inner(guild_config, force_next)
        except Exception:
            logger.opt(exception=True).error(
                f"Failed to advance queue for guild {guild_config.id}"
            )
            # Clear current track so the queue doesn't get stuck
            guild_config.current_music = None
            guild_config.controller.clear_queue_source()

    async def _load_and_play(
        self, guild_config: GuildConfig, music_data: YTMusicData
    ) -> None:
        """Load a source for *music_data* (bounded by a timeout) and set it as current."""
        source = await asyncio.wait_for(
            YoutubeDLSource.from_music_data(
                music_data, volume=guild_config.volume
            ),
            timeout=TRACK_LOAD_TIMEOUT,
        )
        guild_config.controller.set_queue_source(source)

    async def _next_music_inner(
        self, guild_config: GuildConfig, force_next: bool = False
    ) -> None:
        """Prepare and play the next queued track.

        A track that fails to load is skipped and the next one is tried
        instead of stalling or silently killing the queue.
        """
        from src.harpi_lib.api import LoopMode

        if guild_config.current_music:
            if guild_config.loop == LoopMode.TRACK and not force_next:
                logger.debug(
                    f"Looping track '{guild_config.current_music.title}' "
                    f"in guild {guild_config.id}"
                )
                try:
                    await self._load_and_play(
                        guild_config, guild_config.current_music
                    )
                    return
                except Exception as e:
                    logger.warning(
                        f"Failed to reload looping track "
                        f"'{guild_config.current_music.title}' in guild "
                        f"{guild_config.id}: {e}; skipping"
                    )
            elif guild_config.loop == LoopMode.QUEUE:
                if not guild_config.queue:
                    guild_config.queue = []
                guild_config.queue.append(guild_config.current_music)

        while guild_config.queue:
            music_data = guild_config.queue.pop(0)
            guild_config.current_music = music_data
            logger.info(
                f"Playing next track '{music_data.title}' in guild {guild_config.id}"
            )
            try:
                await self._load_and_play(guild_config, music_data)
                return
            except Exception as e:
                logger.warning(
                    f"Skipping unplayable track '{music_data.title}' in guild "
                    f"{guild_config.id}: {e}"
                )

        guild_config.current_music = None
        guild_config.controller.clear_queue_source()

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
            guild_config = (
                await self.voice_service.connect(guild_id, channel_id, ctx)
                if self.voice_service
                else None
            )
        assert guild_config, "Guild config not found"
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

    async def seek(
        self, guild_id: int, position: float, absolute: bool = False
    ) -> None:
        """Seek the current track to a position in seconds."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        source = guild_config.controller.get_queue_source()
        if (
            source is None
            or not hasattr(source, "seek")
            or not hasattr(source, "position_seconds")
        ):
            return
        if not math.isfinite(position):
            raise ValueError("Posição inválida")
        position_seconds = cast(Callable[[], float], source.position_seconds)
        seek = cast(Callable[[float], None], source.seek)
        duration = (
            guild_config.current_music.duration
            if guild_config.current_music
            else 0
        )

        def _seek_in_thread() -> float:
            # Relative offsets are resolved inside the worker so two rapid
            # seeks cannot both read the same pre-seek position and lose a
            # jump.  FFmpeg spawn and teardown block, so this runs off the
            # Quart or bot event loop to avoid freezing either one.
            target = position if absolute else position_seconds() + position
            if not math.isfinite(target):
                raise ValueError("Posição inválida")
            target = max(0.0, target)
            if duration:
                target = min(target, float(duration))
            else:
                target = min(target, MAX_SEEK_SECONDS)
            seek(target)
            return target

        target = await asyncio.to_thread(_seek_in_thread)
        logger.info(f"Seeking to {target:.1f}s in guild {guild_id}")

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
