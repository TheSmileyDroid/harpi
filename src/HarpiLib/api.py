from loguru import logger
import enum
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Any, cast

import discord
from discord.channel import VoiceChannel
from discord.ext.commands import Bot, Context

from src.HarpiLib.music.mixer import MixerSource
from src.HarpiLib.music.soundboard import SoundboardController
from src.HarpiLib.musicdata.ytmusicdata import (
    YoutubeDLSource,
    YTMusicData,
)


class LoopMode(enum.Enum):
    OFF = 0
    TRACK = 1
    QUEUE = 2


@dataclass
class SoundboardGraph:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


DEFAULT_GRAPH = SoundboardGraph(
    nodes=[
        {
            "id": "output-1",
            "type": "output",
            "data": {"volume": 100},
            "position": {"x": 400, "y": 300},
        }
    ],
    edges=[],
)


@dataclass
class GuildConfig:
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
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.guilds: dict[int, GuildConfig] = {}

    def _guild(self, guild_id: int) -> discord.Guild:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            raise ValueError("Servidor não encontrado")
        return guild

    def _voice_channel(
        self, guild: discord.Guild, channel_id: int
    ) -> discord.VoiceChannel:
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            raise ValueError("Canal de voz não encontrado")
        return channel

    async def connect_to_voice(
        self, guild_id: int, channel_id: int, ctx: Context | None = None
    ) -> GuildConfig:
        guild = self._guild(guild_id)

        channel = self._voice_channel(guild, channel_id)

        voice: discord.VoiceClient | None = cast(
            "discord.VoiceClient | None", guild.voice_client
        )
        if voice:
            await voice.disconnect()

        vc = await channel.connect()

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
            partial(self._mixer_callback, guild_config=guild_config),
        )
        bg_callback = cast(
            Callable,
            partial(self._background_callback, guild_config=guild_config),
        )
        mixer.add_observer("queue_end", callback)
        mixer.add_observer("track_end", bg_callback)
        guild_config.ctx = ctx
        self.guilds[guild.id] = guild_config
        vc.play(mixer)

        return guild_config

    def _mixer_callback(self, guild_config: GuildConfig):
        _ = self.bot.loop.create_task(self.next_music(guild_config))

    def _background_callback(
        self, guild_config: GuildConfig, to_remove: list[discord.AudioSource]
    ):
        for source in to_remove:
            layer_id = guild_config.controller.get_layer_id(source)
            if layer_id:
                guild_config.controller.remove_layer(layer_id)
                if (
                    guild_config.background
                    and layer_id in guild_config.background
                ):
                    del guild_config.background[layer_id]

    async def next_music(
        self, guild_config: GuildConfig, force_next: bool = False
    ):
        if guild_config.current_music:
            if guild_config.loop == LoopMode.TRACK and not force_next:
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
            guild_config.current_music = None
            guild_config.controller.clear_queue_source()
            return

        music_data = guild_config.queue.pop(0)
        guild_config.current_music = music_data
        source = await YoutubeDLSource.from_music_data(
            music_data, volume=guild_config.volume
        )
        source.volume = guild_config.volume
        guild_config.controller.set_queue_source(source)

    async def add_music_to_queue(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ):
        music_data_list = await YTMusicData.from_url(link)
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            guild_config = await self.connect_to_voice(
                guild_id, channel_id, ctx
            )
        if not guild_config.queue:
            guild_config.queue = []
        guild_config.queue.extend(music_data_list)
        if not guild_config.current_music:
            await self.next_music(guild_config)

    async def stop_music(self, guild_id: int):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if not guild_config.queue:
            guild_config.queue = []
        guild_config.queue.clear()
        guild_config.controller.clear_queue_source()
        guild_config.current_music = None

    async def skip_music(self, guild_id: int):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        await self.next_music(guild_config, force_next=True)

    async def disconnect_voice(self, guild_id: int):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        voice_client = guild_config.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
        del self.guilds[guild_id]

    async def set_loop(self, guild_id: int, loop: LoopMode):
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        guild_config.loop = loop

    def get_guild_config(self, guild_id: int) -> GuildConfig | None:
        return self.guilds.get(guild_id)

    def get_soundboard_graph(self, guild_id: int) -> SoundboardGraph | None:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            return None
        if not guild_config.soundboard_graph:
            guild_config.soundboard_graph = SoundboardGraph(
                nodes=[
                    {
                        "id": "output-1",
                        "type": "output",
                        "data": {"volume": 100},
                        "position": {"x": 400, "y": 300},
                    }
                ],
                edges=[],
            )
        return guild_config.soundboard_graph

    async def update_soundboard_graph(
        self,
        guild_id: int,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> SoundboardGraph:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if not guild_config.soundboard_graph:
            guild_config.soundboard_graph = SoundboardGraph(
                nodes=nodes, edges=edges
            )
            await self._sync_graph_playback(guild_config, nodes, edges)
        else:
            old_edges = guild_config.soundboard_graph.edges
            guild_config.soundboard_graph.nodes = nodes
            guild_config.soundboard_graph.edges = edges
            await self._handle_edge_changes(
                guild_config, nodes, old_edges, edges
            )
        return guild_config.soundboard_graph

    async def _handle_edge_changes(
        self,
        guild_config: GuildConfig,
        nodes: list[dict[str, Any]],
        old_edges: list[dict[str, Any]],
        new_edges: list[dict[str, Any]],
    ) -> None:
        """Handle edge additions and removals to start/stop playback."""
        old_edge_set = {(e.get("source"), e.get("target")) for e in old_edges}
        new_edge_set = {(e.get("source"), e.get("target")) for e in new_edges}

        added_edges = new_edge_set - old_edge_set
        removed_edges = old_edge_set - new_edge_set

        for source, target in added_edges:
            if _has_path_to_output(source, nodes, new_edges):
                node_id = source
                if node_id in guild_config.prepared_sources:
                    try:
                        await self.start_source_playback(
                            guild_config.id, node_id
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to start playback for {node_id}: {e}"
                        )

        affected_sources: set[str] = set()
        for source, target in removed_edges:
            affected_sources.add(source)

        for source_id in affected_sources:
            if not _has_path_to_output(source_id, nodes, new_edges):
                try:
                    await self.stop_source_playback(guild_config.id, source_id)
                except Exception as e:
                    logger.error(
                        f"Failed to stop playback for {source_id}: {e}"
                    )

    async def _sync_graph_playback(
        self,
        guild_config: GuildConfig,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        """Sync playback state with graph - start all sources connected to output."""
        connected_sources = _find_connected_source_nodes(nodes, edges)
        for node_id in connected_sources:
            if node_id in guild_config.prepared_sources:
                try:
                    await self.start_source_playback(guild_config.id, node_id)
                except Exception as e:
                    logger.error(
                        f"Failed to start playback for {node_id}: {e}"
                    )

    async def add_background_audio(
        self,
        guild_id: int,
        channel_id: int,
        link: str,
        ctx: Context | None = None,
    ) -> str:
        music_data_list = await YTMusicData.from_url(link)
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            guild_config = await self.connect_to_voice(
                guild_id, channel_id, ctx
            )
        source = await YoutubeDLSource.from_music_data(music_data_list[0])
        source.volume = 0.7
        layer_id = guild_config.controller.add_layer(source)
        if not guild_config.background:
            guild_config.background = {}
        guild_config.background[layer_id] = source
        return layer_id

    async def prepare_source(
        self,
        guild_id: int,
        node_id: str,
        url: str,
        volume: float = 100.0,
    ) -> str:
        """Prepare a source (load but don't play yet)."""
        music_data_list = await YTMusicData.from_url(url)
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")

        source = await YoutubeDLSource.from_music_data(music_data_list[0])
        source.volume = max(0.0, min(2.0, volume / 100.0))

        guild_config.prepared_sources[node_id] = source
        logger.info(f"Prepared source {node_id} for guild {guild_id}")
        return node_id

    async def start_source_playback(self, guild_id: int, node_id: str) -> None:
        """Start playing a prepared source by adding it to the mixer."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")

        source = guild_config.prepared_sources.get(node_id)
        if not source:
            raise ValueError(f"Prepared source {node_id} not found")

        if guild_config.background is None:
            guild_config.background = {}

        if any(s == source for s in guild_config.background.values()):
            return

        layer_id = guild_config.controller.add_layer(source)
        guild_config.background[layer_id] = source
        logger.info(f"Started playback for prepared source {node_id}")

    async def stop_source_playback(self, guild_id: int, node_id: str) -> None:
        """Stop playing a source but keep it prepared."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")

        if guild_config.background:
            source = guild_config.prepared_sources.get(node_id)
            if source:
                for layer_id, bg_source in list(
                    guild_config.background.items()
                ):
                    if bg_source == source:
                        guild_config.controller.remove_layer(layer_id)
                        del guild_config.background[layer_id]
                        logger.info(f"Stopped playback for source {node_id}")
                        break

    def is_source_playing(self, guild_id: int, node_id: str) -> bool:
        """Check if a source is currently playing."""
        guild_config = self.guilds.get(guild_id)
        if not guild_config or not guild_config.background:
            return False

        if guild_config.background:
            for source in guild_config.background.values():
                layer_node_id = guild_config.controller.get_layer_id(source)
                if layer_node_id == node_id:
                    return True
        return False

    async def play_tts_source(
        self,
        guild_id: int,
        channel_id: int,
        source: discord.AudioSource,
        ctx: Context | None = None,
    ) -> None:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            guild_config = await self.connect_to_voice(
                guild_id, channel_id, ctx
            )
        guild_config.controller.set_tts_track(source)

    async def remove_background_audio(
        self, guild_id: int, layer_id: str
    ) -> YoutubeDLSource:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if (
            not guild_config.background
            or layer_id not in guild_config.background
        ):
            raise ValueError("Layer não encontrado")

        found_layer = guild_config.background.pop(layer_id)
        guild_config.controller.remove_layer(layer_id)
        return found_layer

    async def set_background_volume(
        self, guild_id: int, layer_id: str, volume: float
    ) -> None:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        if (
            not guild_config.background
            or layer_id not in guild_config.background.keys()
        ):
            raise ValueError(
                f"Layer {layer_id} não encontrado em {guild_config.background.keys() if guild_config.background else 'Nenhuma guilda'}"
            )

        guild_config.background[layer_id].volume = max(0.0, min(2.0, volume))

    async def set_music_volume(self, guild_id: int, volume: float) -> None:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")

        guild_config.volume = max(0.0, min(2.0, volume))
        queue_source = guild_config.controller.get_queue_source()
        if queue_source and hasattr(queue_source, "volume"):
            try:
                queue_source.volume = guild_config.volume  # type: ignore
            except Exception as e:
                logger.error(
                    f"Error while setting volume for music in guild {guild_id}: {e}"
                )

    def get_background_audio_status(
        self, guild_id: int
    ) -> list[dict[str, Any]]:
        guild_config = self.guilds.get(guild_id)
        if not guild_config or not guild_config.background:
            return []

        status = []
        for layer_id, source in guild_config.background.items():
            duration = (
                source.data.get("duration", 0)
                if hasattr(source, "data")
                else 0
            )
            status.append(
                {
                    "layer_id": layer_id,
                    "playing": True,
                    "volume": source.volume * 100,
                    "progress": getattr(source, "progress", 0.0),
                    "duration": float(duration) if duration else 0.0,
                    "title": getattr(source, "title", "Unknown"),
                    "url": getattr(source, "url", ""),
                }
            )
        return status

    async def clean_background_audios(self, guild_id: int) -> None:
        guild_config = self.guilds.get(guild_id)
        if not guild_config:
            raise ValueError("Guilda não conectada")
        guild_config.controller.cleanup_all()
        if guild_config.background:
            guild_config.background.clear()
