"""Source manager for live soundboard audio control."""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.HarpiLib.api import HarpiAPI


class SoundboardSourceManager:
    """Manages individual audio sources for the live soundboard.

    Each source node maps to a background layer in the SoundboardController.
    """

    def __init__(self, api: HarpiAPI, guild_id: int):
        self.api = api
        self.guild_id = guild_id
        self._node_to_layer: dict[str, str] = {}

    async def start_source(
        self,
        node_id: str,
        url: str,
        volume: float = 100,
        channel_id: int | None = None,
    ) -> str:
        """Start a source and return its layer ID.

        Args:
            node_id: Unique identifier for the source node.
            url: Audio URL to play.
            volume: Initial volume (0-200).
            channel_id: Voice channel to connect to if not connected.

        Returns:
            The layer ID assigned to this source.
        """
        if node_id in self._node_to_layer:
            self.stop_source(node_id)

        layer_id = await self.api.add_background_audio(
            self.guild_id, channel_id or 0, url
        )

        self._node_to_layer[node_id] = layer_id

        if volume != 100:
            self.set_volume(node_id, volume)

        logger.info(f"Started source {node_id} -> layer {layer_id}")
        return layer_id

    def stop_source(self, node_id: str) -> None:
        """Stop a source by its node ID."""
        if node_id not in self._node_to_layer:
            return

        layer_id = self._node_to_layer[node_id]
        try:
            self.api.remove_background_audio(self.guild_id, layer_id)
            logger.info(f"Stopped source {node_id} (layer {layer_id})")
        except Exception as e:
            logger.warning(f"Error stopping source {node_id}: {e}")
        finally:
            del self._node_to_layer[node_id]

    def set_volume(self, node_id: str, volume: float) -> None:
        """Set volume for a source.

        Args:
            node_id: The source node ID.
            volume: Volume level (0-200, will be converted to 0-1 range).
        """
        if node_id not in self._node_to_layer:
            return

        layer_id = self._node_to_layer[node_id]
        normalized_volume = max(0.0, min(2.0, volume / 100.0))

        try:
            self.api.set_background_volume(
                self.guild_id, layer_id, normalized_volume
            )
            logger.debug(f"Set volume for {node_id} to {volume}%")
        except Exception as e:
            logger.warning(f"Error setting volume for {node_id}: {e}")

    def stop_all(self) -> None:
        """Stop all sources for this guild."""
        for node_id in list(self._node_to_layer.keys()):
            self.stop_source(node_id)

        try:
            self.api.clean_background_audios(self.guild_id)
        except Exception as e:
            logger.warning(f"Error cleaning background audios: {e}")

        logger.info(f"Stopped all sources for guild {self.guild_id}")

    def get_active_sources(self) -> list[dict[str, Any]]:
        """Get list of active sources."""
        return [
            {"node_id": node_id, "layer_id": layer_id}
            for node_id, layer_id in self._node_to_layer.items()
        ]
