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

from loguru import logger
import enum
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Any, cast

import discord
from discord.channel import VoiceChannel
from discord.ext.commands import Bot, Context

from src.harpi_lib.music.mixer import MixerSource
from src.harpi_lib.music.soundboard import SoundboardController
from src.harpi_lib.musicdata.ytmusicdata import (
    YoutubeDLSource,
    YTMusicData,
)


class LoopMode(enum.Enum):
    """Enum for loop modes (off, track, queue)."""

    OFF = 0
    TRACK = 1
    QUEUE = 2


@dataclass
class SoundboardGraph:
    """Data container for soundboard node-graph state."""

    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GuildConfig:
    """Per-guild audio configuration state.

    Thread safety: individual field writes are atomic under CPython's GIL.
    See module docstring for the full threading contract.
    """

    id: int
    mixer: MixerSource
    controller: SoundboardController
    ctx: Context | None = None
    voice_client: discord.VoiceClient | None = None
    queue: list[YTMusicData] | None = None
    background: dict[str, YoutubeDLSource] | None = None
    prepared_sources: dict[str, YoutubeDLSource] = field(default_factory=dict)
    current_music: YTMusicData | None = None
    loop: LoopMode = LoopMode.OFF
    channel: VoiceChannel | None = None
    volume: float = 0.7
    soundboard_graph: SoundboardGraph | None = None


def _has_path_to_output(
    node_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> bool:
    """Check if a node has a path to any output node via edges using BFS."""
    output_ids = {n["id"] for n in nodes if n.get("type") == "output"}

    if node_id in output_ids:
        return True

    adjacency: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source and target and source in adjacency:
            adjacency[source].append(target)

    visited = {node_id}
    queue = [node_id]
    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, []):
            if neighbor in output_ids:
                return True
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return False


def _find_connected_source_nodes(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> set[str]:
    """Find all source nodes that have a path to an output node."""
    connected = set()
    for node in nodes:
        if node.get("type") == "sound-source":
            if _has_path_to_output(node["id"], nodes, edges):
                connected.add(node["id"])
    return connected


class HarpiAPI:
    """Thin facade that delegates to specialized service classes.

    All public method signatures are preserved for backward compatibility.
    """

    def __init__(self, bot: Bot) -> None:
        from src.harpi_lib.services.background_audio import (
            BackgroundAudioService,
        )
        from src.harpi_lib.services.music_queue import MusicQueueService
        from src.harpi_lib.services.soundboard_graph import (
            SoundboardGraphService,
        )
        from src.harpi_lib.services.tts import TTSService
        from src.harpi_lib.services.voice_connection import (
            VoiceConnectionService,
        )

        self.bot: Bot = bot
        self.guilds: dict[int, GuildConfig] = {}

        # Build the service graph — music_queue provides the callbacks
        # that voice_connection needs, so we create music_queue first
        # (with a placeholder voice_service) then wire them up.
        self._music_queue = MusicQueueService(bot, self.guilds, None)  # type: ignore[arg-type]
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
        self._soundboard = SoundboardGraphService(bot, self.guilds)
        self._tts = TTSService(bot, self.guilds, self._voice)

    # -- Helpers (kept for callers that import them or patch them) --

    def _guild(self, guild_id: int) -> discord.Guild:
        """Get the discord.py Guild object for a guild ID."""
        return self._voice.resolve_guild(self.bot, guild_id)

    def _voice_channel(
        self, guild: discord.Guild, channel_id: int
    ) -> discord.VoiceChannel:
        """Get the voice channel for a guild and channel ID."""
        return self._voice.resolve_voice_channel(guild, channel_id)

    # -- Voice connection --

    async def connect_to_voice(
        self, guild_id: int, channel_id: int, ctx: Context | None = None
    ) -> GuildConfig:
        """Connect to a voice channel."""
        return await self._voice.connect(guild_id, channel_id, ctx)

    async def disconnect_voice(self, guild_id: int) -> None:
        """Disconnect from a voice channel and clean up."""
        await self._voice.disconnect(guild_id)

    # -- Music queue --

    def _mixer_callback(self, guild_config: GuildConfig) -> None:
        """Forward mixer queue-end events to the music queue service."""
        self._music_queue.on_queue_end(guild_config)

    def _background_callback(
        self, guild_config: GuildConfig, to_remove: list[discord.AudioSource]
    ) -> None:
        """Forward background track-end events to the music queue service."""
        self._music_queue.on_track_end(guild_config, to_remove)

    async def next_music(
        self, guild_config: GuildConfig, force_next: bool = False
    ) -> None:
        """Schedule the next track to play."""
        await self._music_queue.next_music(guild_config, force_next)

    async def add_music_to_queue(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ) -> None:
        """Add a track URL to the music queue."""
        await self._music_queue.add_to_queue(guild_id, channel_id, link, ctx)

    async def stop_music(self, guild_id: int) -> None:
        """Stop current playback and clear the queue."""
        await self._music_queue.stop(guild_id)

    async def skip_music(self, guild_id: int) -> None:
        """Skip the current track and play the next."""
        await self._music_queue.skip(guild_id)

    async def set_loop(self, guild_id: int, loop: LoopMode) -> None:
        """Set the loop mode (off, track, or queue)."""
        await self._music_queue.set_loop(guild_id, loop)

    async def set_music_volume(self, guild_id: int, volume: float) -> None:
        """Set the playback volume for the music queue."""
        await self._music_queue.set_volume(guild_id, volume)

    # -- Background audio --

    async def add_background_audio(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ) -> str:
        """Add a background audio layer from a URL."""
        return await self._background.add(guild_id, channel_id, link, ctx)

    async def remove_background_audio(
        self, guild_id: int, layer_id: str
    ) -> YoutubeDLSource:
        """Remove a background audio layer by ID."""
        return await self._background.remove(guild_id, layer_id)

    async def set_background_volume(
        self, guild_id: int, layer_id: str, volume: float
    ) -> None:
        """Set the volume for a specific background audio layer."""
        await self._background.set_volume(guild_id, layer_id, volume)

    def get_background_audio_status(
        self, guild_id: int
    ) -> list[dict[str, Any]]:
        """Get status info for all background audio layers."""
        return self._background.get_status(guild_id)

    async def clean_background_audios(self, guild_id: int) -> None:
        """Remove all background audio layers."""
        await self._background.clean_all(guild_id)

    # -- Soundboard graph --

    def get_soundboard_graph(self, guild_id: int) -> SoundboardGraph | None:
        """Get the soundboard node graph for a guild."""
        return self._soundboard.get_graph(guild_id)

    async def update_soundboard_graph(
        self,
        guild_id: int,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> SoundboardGraph:
        """Update the soundboard node graph for a guild."""
        return await self._soundboard.update_graph(guild_id, nodes, edges)

    async def prepare_source(
        self,
        guild_id: int,
        node_id: str,
        url: str,
        volume: float = 100.0,
    ) -> str:
        """Prepare a soundboard source (load but don't play yet)."""
        return await self._soundboard.prepare_source(
            guild_id, node_id, url, volume
        )

    async def start_source_playback(self, guild_id: int, node_id: str) -> None:
        """Start playing a prepared soundboard source."""
        await self._soundboard.start_source_playback(guild_id, node_id)

    async def stop_source_playback(self, guild_id: int, node_id: str) -> None:
        """Stop playing a soundboard source but keep it prepared."""
        await self._soundboard.stop_source_playback(guild_id, node_id)

    def is_source_playing(self, guild_id: int, node_id: str) -> bool:
        """Check if a soundboard source is currently playing."""
        return self._soundboard.is_source_playing(guild_id, node_id)

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
