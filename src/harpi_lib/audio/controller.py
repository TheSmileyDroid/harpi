"""Audio controller that manages all audio sources for a guild.

Thread safety
-------------
All mutable state is protected by ``self._lock``.
"""

from src.harpi_lib.music.ytmusicdata import UniqueAudioSource
from collections.abc import Iterable
import threading

import discord


class AudioController:
    """Manages all audio sources for a guild: queue tracks, layers, button sounds, and TTS."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._layers: dict[str, discord.AudioSource] = {}
        self._current_queue_source: discord.AudioSource | None = None
        self._tts_track: discord.AudioSource | None = None

    # --- Private helpers ---

    @staticmethod
    def _safe_cleanup(source: discord.AudioSource | None) -> None:
        if source is not None and hasattr(source, "cleanup"):
            source.cleanup()

    def _cleanup_collection(
        self, sources: Iterable[discord.AudioSource]
    ) -> None:
        for source in sources:
            self._safe_cleanup(source)

    def _clear_queue_source(self) -> None:
        # Caller must hold lock.
        self._safe_cleanup(self._current_queue_source)
        self._current_queue_source = None

    def _clear_tts_track(self) -> None:
        # Caller must hold lock.
        self._safe_cleanup(self._tts_track)
        self._tts_track = None

    # --- Public API ---

    def get_playing_sounds(self) -> list[tuple[str, discord.AudioSource]]:
        """Return a list of (type, source) tuples of all currently active sounds for the mixer."""
        with self._lock:
            sounds: list[tuple[str, discord.AudioSource]] = []
            for source in self._layers.values():
                sounds.append(("track", source))
            if self._current_queue_source:
                sounds.append(("queue", self._current_queue_source))
            if self._tts_track:
                sounds.append(("tts", self._tts_track))
            return sounds

    def add_layer(self, source: UniqueAudioSource) -> str:
        """Add a background audio layer and return its ID."""
        with self._lock:
            self._layers[source.id] = source
        return source.id

    def remove_layer(self, layer_id: str) -> None:
        """Remove a background audio layer by its ID."""
        with self._lock:
            if layer_id in self._layers:
                source = self._layers.pop(layer_id)
                self._safe_cleanup(source)

    def get_layer_id(self, source: discord.AudioSource) -> str | None:
        """Find and return the layer ID for a given audio source, or None if not found."""
        with self._lock:
            for layer_id, src in self._layers.items():
                if src == source:
                    return layer_id
        return None

    def set_queue_source(self, source: discord.AudioSource | None) -> None:
        """Set the current queue track, cleaning up any previous one."""
        with self._lock:
            self._safe_cleanup(self._current_queue_source)
            self._current_queue_source = source

    def get_queue_source(self) -> discord.AudioSource | None:
        """Return the current queue track, or None if nothing is playing."""
        with self._lock:
            return self._current_queue_source

    def get_queue_position(self) -> float:
        """Return the current queue track position in seconds."""
        with self._lock:
            source = self._current_queue_source
        if source is None or not hasattr(source, "position_seconds"):
            return 0.0
        try:
            return float(source.position_seconds())  # type: ignore
        except Exception:
            return 0.0

    def clear_queue_source(self) -> None:
        """Clear the current queue track with cleanup."""
        with self._lock:
            self._clear_queue_source()

    def _on_track_finished(self, source: discord.AudioSource) -> None:
        """Handle track completion by cleaning up and clearing the current source."""
        with self._lock:
            if self._current_queue_source == source:
                self._clear_queue_source()

    def set_tts_track(self, source: discord.AudioSource | None) -> None:
        """Set or clear the TTS audio source, cleaning up any previous one."""
        with self._lock:
            self._clear_tts_track()
            self._tts_track = source

    def remove_finished_source(self, source: discord.AudioSource) -> None:
        """Remove a finished source from whichever collection it belongs to."""
        with self._lock:
            for layer_id, src in list(self._layers.items()):
                if src == source:
                    del self._layers[layer_id]
                    self._safe_cleanup(source)
                    return
            if self._tts_track == source:
                self._safe_cleanup(source)
                self._tts_track = None
            if self._current_queue_source == source:
                self._clear_queue_source()

    def cleanup_all(self) -> None:
        """Clean up all audio sources and release resources."""
        with self._lock:
            self._cleanup_collection(self._layers.values())
            self._layers.clear()

            self._clear_queue_source()
            self._clear_tts_track()
