"""Soundboard controller that manages all audio sources for a guild.

Thread safety
-------------
All mutable state is protected by ``self._lock``.  Callbacks registered
via ``on_queue_empty`` are invoked **outside** the lock to prevent
deadlocks if a callback needs to re-enter the controller.
"""

from src.harpi_lib.musicdata.ytmusicdata import UniqueAudioSource
from typing import Callable
from collections.abc import Iterable
import threading
import uuid

import discord


class SoundboardController:
    """Manages all audio sources for a guild: queue tracks, layers, button sounds, and TTS."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._layers: dict[str, discord.AudioSource] = {}
        self._button_sounds: dict[str, discord.AudioSource] = {}
        self._queue: list[discord.AudioSource] = []
        self._current_queue_source: discord.AudioSource | None = None
        self._tts_track: discord.AudioSource | None = None
        self._on_queue_empty_callbacks: list[Callable] = []

    # --- Private helpers ---

    @staticmethod
    def _safe_cleanup(source: discord.AudioSource | None) -> None:
        """Call cleanup() on a source if it exists and the source is not None."""
        if source is not None and hasattr(source, "cleanup"):
            source.cleanup()

    def _cleanup_collection(
        self, sources: Iterable[discord.AudioSource]
    ) -> None:
        """Cleanup every source in an iterable."""
        for source in sources:
            self._safe_cleanup(source)

    def _clear_queue_source(self) -> None:
        """Cleanup and nullify the current queue source. Caller must hold lock."""
        self._safe_cleanup(self._current_queue_source)
        self._current_queue_source = None

    def _clear_tts_track(self) -> None:
        """Cleanup and nullify the TTS track. Caller must hold lock."""
        self._safe_cleanup(self._tts_track)
        self._tts_track = None

    def _advance_queue(self) -> list[Callable]:
        """Pop next track from queue or return empty-callbacks to fire.

        Caller must hold lock.  Returns a list of callbacks that the caller
        must invoke **after** releasing the lock to avoid deadlock.
        """
        if self._queue:
            self._current_queue_source = self._queue.pop(0)
            return []
        else:
            self._current_queue_source = None
            return list(self._on_queue_empty_callbacks)

    # --- Public API ---

    def get_playing_sounds(self) -> list[tuple[str, discord.AudioSource]]:
        """Return a list of (type, source) tuples of all currently active sounds for the mixer."""
        with self._lock:
            sounds: list[tuple[str, discord.AudioSource]] = []
            for source in self._layers.values():
                sounds.append(("track", source))
            for source in self._button_sounds.values():
                sounds.append(("button", source))
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

    def add_button_sound(self, source: discord.AudioSource) -> str:
        """Add a short button sound effect and return its generated ID."""
        button_id = str(uuid.uuid4())
        with self._lock:
            self._button_sounds[button_id] = source
        return button_id

    def remove_button_sound(self, button_id: str) -> None:
        """Remove a button sound effect by its ID."""
        with self._lock:
            if button_id in self._button_sounds:
                source = self._button_sounds.pop(button_id)
                self._safe_cleanup(source)

    def set_queue_source(self, source: discord.AudioSource | None) -> None:
        """Set the current queue track, cleaning up any previous one."""
        with self._lock:
            self._safe_cleanup(self._current_queue_source)
            self._current_queue_source = source

    def get_queue_source(self) -> discord.AudioSource | None:
        """Return the current queue track, or None if nothing is playing."""
        with self._lock:
            return self._current_queue_source

    def clear_queue_source(self) -> None:
        """Clear the current queue track with cleanup."""
        with self._lock:
            self._clear_queue_source()

    def add_to_queue(self, source: discord.AudioSource) -> None:
        """Add a track to the playback queue, or start playing immediately if queue is empty."""
        with self._lock:
            if self._current_queue_source is None:
                self._current_queue_source = source
            else:
                self._queue.append(source)

    def clear_queue(self) -> None:
        """Clear all queued tracks and the current queue source with cleanup."""
        with self._lock:
            self._cleanup_collection(self._queue)
            self._queue.clear()
            self._clear_queue_source()

    def on_queue_empty(self, callback: Callable) -> None:
        """Register a callback to be invoked when the queue becomes empty."""
        with self._lock:
            self._on_queue_empty_callbacks.append(callback)

    def _on_track_finished(self, source: discord.AudioSource) -> None:
        """Handle track completion by cleaning up the source and advancing the queue.

        Callbacks are invoked outside the lock to avoid deadlock.
        """
        callbacks: list[Callable] = []
        with self._lock:
            if self._current_queue_source == source:
                self._safe_cleanup(source)
                callbacks = self._advance_queue()
        for cb in callbacks:
            cb()

    def set_tts_track(self, source: discord.AudioSource | None) -> None:
        """Set or clear the TTS audio source, cleaning up any previous one."""
        with self._lock:
            self._clear_tts_track()
            self._tts_track = source

    def remove_finished_source(self, source: discord.AudioSource) -> None:
        """Remove a finished source from whichever collection it belongs to.

        Callbacks are invoked outside the lock to avoid deadlock.
        """
        callbacks: list[Callable] = []
        with self._lock:
            for layer_id, src in list(self._layers.items()):
                if src == source:
                    del self._layers[layer_id]
                    self._safe_cleanup(source)
                    return
            for button_id, src in list(self._button_sounds.items()):
                if src == source:
                    del self._button_sounds[button_id]
                    self._safe_cleanup(source)
                    return
            if source in self._queue:
                self._queue.remove(source)
                self._safe_cleanup(source)
                return
            if self._tts_track == source:
                self._safe_cleanup(source)
                self._tts_track = None
            if self._current_queue_source == source:
                self._safe_cleanup(source)
                callbacks = self._advance_queue()
        for cb in callbacks:
            cb()

    def cleanup_all(self) -> None:
        """Clean up all audio sources and release resources."""
        with self._lock:
            self._cleanup_collection(self._layers.values())
            self._layers.clear()

            self._cleanup_collection(self._button_sounds.values())
            self._button_sounds.clear()

            self._cleanup_collection(self._queue)
            self._queue.clear()

            self._clear_queue_source()
            self._clear_tts_track()
