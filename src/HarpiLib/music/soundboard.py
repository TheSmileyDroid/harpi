from src.HarpiLib.musicdata.ytmusicdata import UniqueAudioSource
from typing import Callable
import threading
import uuid

import discord


class SoundboardController:
    def __init__(self):
        self._lock = threading.Lock()
        self._layers: dict[str, discord.AudioSource] = {}
        self._button_sounds: dict[str, discord.AudioSource] = {}
        self._queue: list[discord.AudioSource] = []
        self._current_queue_source: discord.AudioSource | None = None
        self._tts_track: discord.AudioSource | None = None
        self._on_queue_empty_callbacks: list[Callable] = []

    def get_playing_sounds(self) -> list[tuple[str, discord.AudioSource]]:
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
        with self._lock:
            self._layers[source.id] = source
        return source.id

    def remove_layer(self, layer_id: str) -> None:
        with self._lock:
            if layer_id in self._layers:
                source = self._layers.pop(layer_id)
                if hasattr(source, "cleanup"):
                    source.cleanup()

    def get_layer_id(self, source: discord.AudioSource) -> str | None:
        with self._lock:
            for layer_id, src in self._layers.items():
                if src == source:
                    return layer_id
        return None

    def add_button_sound(self, source: discord.AudioSource) -> str:
        button_id = str(uuid.uuid4())
        with self._lock:
            self._button_sounds[button_id] = source
        return button_id

    def remove_button_sound(self, button_id: str) -> None:
        with self._lock:
            if button_id in self._button_sounds:
                source = self._button_sounds.pop(button_id)
                if hasattr(source, "cleanup"):
                    source.cleanup()

    def set_queue_source(self, source: discord.AudioSource | None) -> None:
        with self._lock:
            if self._current_queue_source and hasattr(
                self._current_queue_source, "cleanup"
            ):
                self._current_queue_source.cleanup()
            self._current_queue_source = source

    def get_queue_source(self) -> discord.AudioSource | None:
        with self._lock:
            return self._current_queue_source

    def clear_queue_source(self) -> None:
        with self._lock:
            if self._current_queue_source and hasattr(
                self._current_queue_source, "cleanup"
            ):
                self._current_queue_source.cleanup()
            self._current_queue_source = None

    def add_to_queue(self, source: discord.AudioSource) -> None:
        with self._lock:
            if self._current_queue_source is None:
                self._current_queue_source = source
            else:
                self._queue.append(source)

    def clear_queue(self) -> None:
        with self._lock:
            for source in self._queue:
                if hasattr(source, "cleanup"):
                    source.cleanup()
            self._queue.clear()
            if self._current_queue_source and hasattr(
                self._current_queue_source, "cleanup"
            ):
                self._current_queue_source.cleanup()
            self._current_queue_source = None

    def on_queue_empty(self, callback: Callable) -> None:
        self._on_queue_empty_callbacks.append(callback)

    def _on_track_finished(self, source: discord.AudioSource) -> None:
        with self._lock:
            if self._current_queue_source == source:
                if hasattr(source, "cleanup"):
                    source.cleanup()
                if self._queue:
                    self._current_queue_source = self._queue.pop(0)
                else:
                    self._current_queue_source = None
                    for cb in self._on_queue_empty_callbacks:
                        cb()

    def set_tts_track(self, source: discord.AudioSource | None) -> None:
        with self._lock:
            if self._tts_track and hasattr(self._tts_track, "cleanup"):
                self._tts_track.cleanup()
            self._tts_track = source

    def remove_finished_source(self, source: discord.AudioSource) -> None:
        with self._lock:
            for layer_id, src in list(self._layers.items()):
                if src == source:
                    del self._layers[layer_id]
                    return
            for button_id, src in list(self._button_sounds.items()):
                if src == source:
                    del self._button_sounds[button_id]
                    return
            if source in self._queue:
                self._queue.remove(source)
                if hasattr(source, "cleanup"):
                    source.cleanup()
                return
            if self._tts_track == source:
                if hasattr(source, "cleanup"):
                    source.cleanup()
                self._tts_track = None
            if self._current_queue_source == source:
                if hasattr(source, "cleanup"):
                    source.cleanup()
                if self._queue:
                    self._current_queue_source = self._queue.pop(0)
                else:
                    self._current_queue_source = None
                    for cb in self._on_queue_empty_callbacks:
                        cb()

    def cleanup_all(self) -> None:
        with self._lock:
            for source in self._layers.values():
                if hasattr(source, "cleanup"):
                    source.cleanup()
            self._layers.clear()

            for source in self._button_sounds.values():
                if hasattr(source, "cleanup"):
                    source.cleanup()
            self._button_sounds.clear()

            for source in self._queue:
                if hasattr(source, "cleanup"):
                    source.cleanup()
            self._queue.clear()

            if self._current_queue_source and hasattr(
                self._current_queue_source, "cleanup"
            ):
                self._current_queue_source.cleanup()
            self._current_queue_source = None

            if self._tts_track and hasattr(self._tts_track, "cleanup"):
                self._tts_track.cleanup()
            self._tts_track = None
