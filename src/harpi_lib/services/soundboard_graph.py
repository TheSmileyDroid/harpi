"""Soundboard graph management service.

Thread safety
-------------
``prepared_sources`` (``dict[str, YoutubeDLSource]``) on ``GuildConfig``
is written during ``prepare_sources`` (bot event loop) and read during
``play_soundboard``.  Both run on the same event loop so no lock is
needed.  The ``SoundboardController`` used by ``play_soundboard`` has its
own internal lock protecting queue/layer state (see ``soundboard.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.ext.commands import Bot
from loguru import logger

from src.harpi_lib.api import _find_connected_source_nodes, _has_path_to_output
from src.harpi_lib.musicdata.ytmusicdata import YoutubeDLSource, YTMusicData

if TYPE_CHECKING:
    from src.harpi_lib.api import GuildConfig, SoundboardGraph


class SoundboardGraphService:
    """Manages the soundboard node-graph editor state and playback."""

    def __init__(
        self,
        bot: Bot,
        guilds: dict[int, GuildConfig],
    ) -> None:
        self.bot = bot
        self.guilds = guilds

    def get_graph(self, guild_id: int) -> SoundboardGraph | None:
        """Get the soundboard node graph for a guild."""
        from src.harpi_lib.api import SoundboardGraph

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

    async def update_graph(
        self,
        guild_id: int,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> SoundboardGraph:
        """Update the soundboard node graph for a guild."""
        from src.harpi_lib.api import SoundboardGraph

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
                        logger.opt(exception=True).error(
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
                    logger.opt(exception=True).error(
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
                    logger.opt(exception=True).error(
                        f"Failed to start playback for {node_id}: {e}"
                    )

    async def prepare_source(
        self,
        guild_id: int,
        node_id: str,
        url: str,
        volume: float = 100.0,
    ) -> str:
        """Prepare a source (load but don't play yet)."""
        music_data_list = await YTMusicData.from_url(url)
        if not music_data_list:
            raise ValueError(f"No audio found for URL: {url}")
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
