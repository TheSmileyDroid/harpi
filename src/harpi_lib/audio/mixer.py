"""Audio mixer that reads from multiple sources and mixes them into a single stream.

Thread safety
-------------
``MixerSource.read()`` is called from discord.py's voice-sending thread,
while ``add_observer`` / ``remove_observer`` are called from the bot's
event loop and ``cleanup()`` can be called from either the bot or Quart
event loops.

* ``self._lock`` guards ``_observers`` and the ``_shutdown`` flag.
* Observer lists are snapshot-copied before notification so callbacks
  run without the lock held.
* ``cleanup()`` sets ``_shutdown = True`` under the lock, then tears
  down the executor.  ``read()`` checks ``_shutdown`` early to avoid
  submitting work to a dead pool.
"""

from src.harpi_lib.audio.controller import AudioController
import concurrent.futures
import threading
from typing import Callable, override

import discord
import numpy as np
from loguru import logger


class MixerSource(discord.AudioSource):
    """Read from multiple audio sources and mix them into a single PCM stream."""

    def __init__(self, controller: AudioController) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._shutdown: bool = False
        self.has_active_tracks: bool = False
        self.controller: AudioController = controller
        self._observers: dict[str, list[Callable]] = {}

        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=16, thread_name_prefix="MixerReader"
        )
        self.pending_futures: dict[
            discord.AudioSource, concurrent.futures.Future
        ] = {}
        self.READ_TIMEOUT = 0.05

        self.SAMPLE_RATE: int = 48000
        self.CHANNELS: int = 2
        self.SAMPLES_PER_FRAME: int = 960
        self.FRAME_SIZE: int = self.SAMPLES_PER_FRAME * self.CHANNELS * 2

    def add_observer(self, event: str, callback: Callable) -> None:
        """Register a callback for an event (e.g. 'track_end', 'queue_end')."""
        with self._lock:
            if event not in self._observers:
                self._observers[event] = []
            self._observers[event].append(callback)

    def remove_observer(self, event: str, callback: Callable) -> None:
        """Unregister an event callback."""
        with self._lock:
            if event in self._observers and callback in self._observers[event]:
                self._observers[event].remove(callback)

    def _notify_observers(self, event: str, **kwargs: object) -> None:
        """Invoke all callbacks registered for an event.

        A snapshot of the callback list is taken under the lock so that
        callbacks themselves may safely call ``add_observer`` /
        ``remove_observer`` without deadlocking.
        """
        with self._lock:
            callbacks = list(self._observers.get(event, []))
        for callback in callbacks:
            try:
                callback(**kwargs)
            except Exception as e:
                logger.opt(exception=True).error(
                    f"Error in observer callback for {event}: {e}"
                )

    def _read_track(self, track: discord.AudioSource) -> bytes:
        """Read one frame from a single audio source (runs in thread pool)."""
        try:
            return track.read()
        except Exception as e:
            logger.error(f"Error reading track: {e}")
            return b""

    def _submit_read_futures(
        self, sources: list[tuple[str, discord.AudioSource]]
    ) -> None:
        """Ensure each active source has a pending future.

        Skips submission if the mixer has been shut down.
        """
        if self._shutdown:
            return
        for _, source in sources:
            if source not in self.pending_futures:
                try:
                    self.pending_futures[source] = self.executor.submit(
                        self._read_track, source
                    )
                except RuntimeError:
                    # Executor already shut down — race with cleanup()
                    return

    def _prune_stale_futures(
        self, sources: list[tuple[str, discord.AudioSource]]
    ) -> None:
        """Cancel and remove futures for sources no longer in the active set."""
        active_sources = {s for _, s in sources}
        for s in list(self.pending_futures.keys()):
            if s not in active_sources:
                self.pending_futures[s].cancel()
                del self.pending_futures[s]

    def _await_futures(
        self, sources: list[tuple[str, discord.AudioSource]]
    ) -> None:
        """Wait for all pending futures up to READ_TIMEOUT."""
        current_futures = [
            self.pending_futures[s]
            for _, s in sources
            if s in self.pending_futures
        ]
        if current_futures:
            concurrent.futures.wait(current_futures, timeout=self.READ_TIMEOUT)

    def _collect_and_mix(
        self,
        sources: list[tuple[str, discord.AudioSource]],
        mixed_audio: np.ndarray,
    ) -> tuple[list[discord.AudioSource], bool]:
        """Read completed futures, mix into mixed_audio, return (to_remove, has_active)."""
        to_remove: list[discord.AudioSource] = []
        has_active = False

        for source_type, source_obj in sources:
            if source_obj not in self.pending_futures:
                continue

            future = self.pending_futures[source_obj]
            if not future.done():
                has_active = True
                continue

            del self.pending_futures[source_obj]

            try:
                data = future.result()
            except Exception as e:
                logger.opt(exception=True).error(
                    f"Unexpected error in thread for {source_type}: {e}"
                )
                data = b""

            should_remove = False
            if not data:
                should_remove = True
            else:
                has_active = True
                audio_chunk = np.frombuffer(data, dtype=np.int16)

                if len(audio_chunk) < len(mixed_audio):
                    padded = np.zeros(len(mixed_audio), dtype=np.int16)
                    padded[: len(audio_chunk)] = audio_chunk
                    audio_chunk = padded
                    should_remove = True

                mixed_audio += audio_chunk

            if should_remove:
                to_remove.append(source_obj)
                self._handle_source_removal(source_type, source_obj)

        return to_remove, has_active

    def _handle_source_removal(
        self, source_type: str, source_obj: discord.AudioSource
    ) -> None:
        """Dispatch removal side-effects based on source type."""
        if source_type == "track":
            self._notify_observers("track_end", to_remove=[source_obj])
        elif source_type == "queue":
            self._notify_observers("queue_end")
            self.controller._on_track_finished(source_obj)
        elif source_type == "tts":
            self.controller.set_tts_track(None)
        # "button" sources need no special handling

    @override
    def read(self) -> bytes:
        """Read and mix one frame from all active sources."""
        if self._shutdown:
            return b"\x00" * self.FRAME_SIZE

        mixed_audio = np.zeros(
            self.SAMPLES_PER_FRAME * self.CHANNELS, dtype=np.int32
        )

        sources = self.controller.get_playing_sounds()

        self._submit_read_futures(sources)
        self._prune_stale_futures(sources)
        self._await_futures(sources)

        to_remove, has_active = self._collect_and_mix(sources, mixed_audio)

        for source in to_remove:
            self.controller.remove_finished_source(source)

        self.has_active_tracks = has_active

        np.clip(mixed_audio, -32768, 32767, out=mixed_audio)
        return mixed_audio.astype(np.int16).tobytes()

    @override
    def cleanup(self) -> None:
        """Cancel pending futures and shut down the thread pool.

        Sets the ``_shutdown`` flag so that ``read()`` stops submitting
        new work, then cancels outstanding futures and tears down the
        executor.
        """
        with self._lock:
            self._shutdown = True

        for future in self.pending_futures.values():
            future.cancel()
        self.pending_futures.clear()

        self.executor.shutdown(wait=False)
