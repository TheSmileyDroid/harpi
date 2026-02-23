"""Graph execution engine for soundboard audio routing."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from discord import AudioSource
from loguru import logger

from src.HarpiLib.api import HarpiAPI
from src.HarpiLib.musicdata.ytmusicdata import YoutubeDLSource


@dataclass
class NodeContext:
    """Runtime context for a node during execution."""

    node_id: str
    node_type: str
    data: dict[str, Any]
    inputs: list[NodeContext]
    source: AudioSource | None = None


class SoundboardExecutor:
    """Executes soundboard graphs by routing audio through nodes."""

    def __init__(self, api: HarpiAPI):
        self.api = api
        self._active_sources: dict[str, list[AudioSource]] = defaultdict(list)

    def _build_adjacency(
        self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Build adjacency lists for the graph."""
        node_map = {n["id"]: n for n in nodes}
        incoming: dict[str, list[str]] = {nid: [] for nid in node_map}
        outgoing: dict[str, list[str]] = {nid: [] for nid in node_map}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target and source in node_map and target in node_map:
                outgoing[source].append(target)
                incoming[target].append(source)

        return incoming, outgoing

    def _topological_sort(
        self, nodes: list[dict[str, Any]], incoming: dict[str, list[str]]
    ) -> list[str]:
        """Topologically sort nodes (sources first, sinks last)."""
        node_map = {n["id"]: n for n in nodes}
        in_degree = {nid: len(incoming[nid]) for nid in node_map}
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            for neighbor in node_map:
                if current in incoming[neighbor]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        return result

    def _find_output_nodes(
        self, nodes: list[dict[str, Any]], outgoing: dict[str, list[str]]
    ) -> list[str]:
        """Find all output nodes (nodes with no outgoing connections)."""
        return [
            n["id"]
            for n in nodes
            if n.get("type") == "output" or not outgoing.get(n["id"])
        ]

    async def _create_audio_source(
        self, url: str, volume: float
    ) -> AudioSource | None:
        """Create an audio source from a URL."""
        try:
            source = await YoutubeDLSource.from_url(url)
            source.set_volume(volume / 100.0)
            return source
        except Exception as e:
            logger.error(f"Failed to create audio source from {url}: {e}")
            return None

    async def execute(
        self,
        guild_id: int,
        channel_id: int,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> bool:
        """Execute a soundboard graph and start audio playback."""
        logger.info(f"Executing soundboard for guild {guild_id}")

        node_map = {n["id"]: n for n in nodes}
        incoming, outgoing = self._build_adjacency(nodes, edges)
        order = self._topological_sort(nodes, incoming)

        self.stop(guild_id)

        node_contexts: dict[str, NodeContext] = {}

        for node_id in order:
            node = node_map[node_id]
            node_type = node.get("type", "unknown")
            data = node.get("data", {})

            ctx = NodeContext(
                node_id=node_id,
                node_type=node_type,
                data=data,
                inputs=[
                    node_contexts[iid]
                    for iid in incoming[node_id]
                    if iid in node_contexts
                ],
            )
            node_contexts[node_id] = ctx

            if node_type == "sound-source":
                url = data.get("url", "")
                volume = data.get("volume", 100)
                if url:
                    source = await self._create_audio_source(url, volume)
                    if source:
                        ctx.source = source
                        self._active_sources[guild_id].append(source)
                        await self.api.add_background_audio(
                            guild_id, channel_id, url
                        )

            elif node_type == "playlist":
                items = data.get("items", [])
                volume = data.get("volume", 100)
                if items:
                    first_item = items[0]
                    url = first_item.get("url", "")
                    if url:
                        source = await self._create_audio_source(url, volume)
                        if source:
                            ctx.source = source
                            self._active_sources[guild_id].append(source)
                            await self.api.add_background_audio(
                                guild_id, channel_id, url
                            )

            elif node_type in ("group", "mixer"):
                pass

            elif node_type == "output":
                pass

        return True

    def stop(self, guild_id: int) -> None:
        """Stop all soundboard audio for a guild."""
        for source in self._active_sources.get(guild_id, []):
            try:
                source.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up source: {e}")

        if guild_id in self._active_sources:
            del self._active_sources[guild_id]

        try:
            self.api.clean_background_audio(guild_id)
        except Exception as e:
            logger.warning(f"Error cleaning background audio: {e}")

        logger.info(f"Stopped soundboard for guild {guild_id}")
