"""HarpiAPI facade delegating to specialized service classes.

Thread safety
-------------
``HarpiAPI`` owns the ``guilds`` dict (``dict[int, GuildConfig]``) which is
shared between the Quart event loop (HTTP handlers) and the Discord bot's
event loop (running in a background thread).

Individual field mutations on ``GuildConfig`` (e.g. setting ``volume``,
``current_music``, ``loop``) are atomic under CPython's GIL, so they are
safe without explicit locking.  Compound read-modify-write sequences
(e.g. iterating ``queue`` while another thread appends) are technically
racy but acceptable in practice because:

* Queue mutations happen exclusively on the bot's event loop.
* Quart handlers only read queue contents for display purposes.
* The ``guilds`` dict itself is only mutated (insert/delete) from the
  bot's event loop via ``VoiceConnectionService``.

This is an **accepted risk** documented here rather than papered over
with locks that would add complexity without preventing real bugs.
"""

from dataclasses import dataclass

import discord
from discord.channel import VoiceChannel
from discord.ext.commands import Bot, Context

from src.harpi_lib.audio.controller import AudioController
from src.harpi_lib.audio.mixer import MixerSource
from src.harpi_lib.audio.session import LoopMode
from src.harpi_lib.music.ytmusicdata import (
    YoutubeDLSource,
    YTMusicData,
)


@dataclass
class GuildConfig:
    """Per-guild audio configuration state.

    Thread safety: individual field writes are atomic under CPython's GIL.
    See module docstring for the full threading contract.
    """

    id: int
    mixer: MixerSource
    controller: AudioController
    ctx: Context | None = None
    voice_client: discord.VoiceClient | None = None
    queue: list[YTMusicData] | None = None
    background: dict[str, YoutubeDLSource] | None = None
    current_music: YTMusicData | None = None
    loop: LoopMode = LoopMode.OFF
    channel: VoiceChannel | None = None
    volume: float = 0.7


class HarpiAPI:
    """Thin facade that delegates to specialized service classes.

    Retains the music-queue facade for the htmx panel routes while the
    PlaybackSession becomes the surface the cogs use.
    """

    def __init__(self, bot: Bot) -> None:
        from src.harpi_lib.services.background_audio import (
            BackgroundAudioService,
        )
        from src.harpi_lib.services.music_queue import MusicQueueService
        from src.harpi_lib.services.tts import TTSService
        from src.harpi_lib.services.voice_connection import (
            VoiceConnectionService,
        )

        self.bot: Bot = bot
        self.guilds: dict[int, GuildConfig] = {}

        self._music_queue = MusicQueueService(bot, self.guilds, None)
        self._voice = VoiceConnectionService(
            bot,
            self.guilds,
            on_queue_end=self._music_queue.on_queue_end,
            on_track_end=self._music_queue.on_track_end,
        )
        self._music_queue.voice_service = self._voice

        self._background = BackgroundAudioService(
            bot, self.guilds, self._voice
        )
        self._tts = TTSService(bot, self.guilds, self._voice)

    # -- Music queue --

    async def next_music(
        self, guild_config: GuildConfig, force_next: bool = False
    ) -> None:
        """Schedule the next track to play."""
        await self._music_queue.next_music(guild_config, force_next)

    async def set_loop(self, guild_id: int, loop: LoopMode) -> None:
        """Set the loop mode (off, track, or queue)."""
        await self._music_queue.set_loop(guild_id, loop)

    # -- Background audio --

    async def add_background_audio(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ) -> str:
        """Add a background audio layer from a URL."""
        return await self._background.add_layer(
            guild_id, channel_id, link, ctx
        )

    async def remove_background_audio(
        self, guild_id: int, layer_id: str
    ) -> YoutubeDLSource:
        """Remove a background audio layer by ID."""
        return await self._background.remove_layer(guild_id, layer_id)

    async def set_background_volume(
        self, guild_id: int, layer_id: str, volume: float
    ) -> None:
        """Set the volume for a specific background audio layer."""
        await self._background.set_layer_volume(guild_id, layer_id, volume)

    async def clean_background_audios(self, guild_id: int) -> None:
        """Remove all background audio layers."""
        await self._background.remove_all_layers(guild_id)

    # -- TTS --

    async def play_tts_source(
        self,
        guild_id: int,
        channel_id: int,
        source: discord.AudioSource,
        ctx: Context | None = None,
    ) -> None:
        """Play a TTS audio source in a voice channel."""
        await self._tts.play(guild_id, channel_id, source, ctx)

    # -- Guild config --

    def get_guild_config(self, guild_id: int) -> GuildConfig | None:
        """Get the guild configuration for a guild ID, or None if not connected."""
        return self.guilds.get(guild_id)
