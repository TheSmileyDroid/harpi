import concurrent.futures
import threading
from typing import Callable, cast, override

import discord
import numpy as np

from src.HarpiLib.musicdata.ytmusicdata import YoutubeDLSource


class MixerSource(discord.AudioSource):
    def __init__(self):
        self.tracks: list[YoutubeDLSource] = []
        self.track_from_queue: YoutubeDLSource | None = None
        self.tts_track: discord.AudioSource | None = None
        self._lock: threading.Lock = threading.Lock()
        self.has_active_tracks: bool = False

        self._observers: dict[str, list[Callable]] = {}

        # Thread pool for parallel reading
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=16, thread_name_prefix="MixerReader"
        )
        # Track pending reads: Source -> Future
        self.pending_futures: dict[
            discord.AudioSource, concurrent.futures.Future
        ] = {}
        self.READ_TIMEOUT = 0.05  # 50ms timeout for gathering audio

        # Audio constants for Discord (48kHz Stereo 16-bit)
        self.SAMPLE_RATE: int = 48000
        self.CHANNELS: int = 2
        self.SAMPLES_PER_FRAME: int = 960  # 20ms of audio
        self.FRAME_SIZE: int = (
            self.SAMPLES_PER_FRAME * self.CHANNELS * 2
        )  # Bytes per frame (3840)

    def add_observer(self, event: str, callback: Callable):
        """Register a callback for an event."""
        if event not in self._observers:
            self._observers[event] = []
        self._observers[event].append(callback)

    def remove_observer(self, event: str, callback: Callable):
        """Remove a callback for an event."""
        if event in self._observers and callback in self._observers[event]:
            self._observers[event].remove(callback)

    def _notify_observers(self, event: str, **kwargs):
        """Notify all observers of an event."""
        if event in self._observers:
            for callback in self._observers[event]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    print(f"Error in observer callback for {event}: {e}")

    def add_track(self, source: YoutubeDLSource):
        """Adds a new audio source (track) to the mixer."""
        with self._lock:
            self.tracks.append(source)

    def set_current_from_queue(self, source: YoutubeDLSource | None):
        """Replace queue music."""
        with self._lock:
            self.track_from_queue = source

    def set_tts_track(self, source: discord.AudioSource | None):
        """Sets the TTS track."""
        with self._lock:
            self.tts_track = source

    def _read_track(self, track: discord.AudioSource):
        """Reads a chunk from a specific track safely."""
        try:
            return track.read()
        except Exception as e:
            print(f"Error reading track: {e}")
            return b""

    @override
    def read(self):
        # Create a buffer of silence (zeros) using int32 to prevent overflow during addition
        # 1920 samples (960 * 2 channels)
        mixed_audio = np.zeros(
            self.SAMPLES_PER_FRAME * self.CHANNELS, dtype=np.int32
        )

        to_remove: list[YoutubeDLSource] = []
        has_active_tracks = False

        # Collect all sources to read from under lock
        sources_to_read: list[tuple[str, discord.AudioSource]] = []
        with self._lock:
            # Regular tracks
            for track in self.tracks:
                sources_to_read.append(("track", track))

            # Queue track
            if self.track_from_queue:
                sources_to_read.append(("queue", self.track_from_queue))

            # TTS track
            if self.tts_track:
                sources_to_read.append(("tts", self.tts_track))

        # Submit tasks for sources that don't have a pending future
        for _, source in sources_to_read:
            if source not in self.pending_futures:
                self.pending_futures[source] = self.executor.submit(
                    self._read_track, source
                )

        # Wait for futures to complete with a timeout
        # We only care about futures for current sources
        current_futures = [
            self.pending_futures[s]
            for _, s in sources_to_read
            if s in self.pending_futures
        ]

        if current_futures:
            concurrent.futures.wait(current_futures, timeout=self.READ_TIMEOUT)

        # Process results
        for source_type, source_obj in sources_to_read:
            # If we don't have a future for this source (weird, but possible if logic changes), skip
            if source_obj not in self.pending_futures:
                continue

            future = self.pending_futures[source_obj]

            if not future.done():
                # Track is lagging/blocking. Treat as silence for this frame.
                # Do NOT remove from pending_futures, so we can pick up the result next time.
                has_active_tracks = True  # Still active, just slow
                continue

            # Future is done, retrieve result and clear from pending
            del self.pending_futures[source_obj]

            try:
                data = future.result()
            except Exception as e:
                print(f"Unexpected error in thread for {source_type}: {e}")
                data = b""

            # Specific logic for each type
            if source_type == "track":
                track = cast(YoutubeDLSource, source_obj)
                if not data:
                    to_remove.append(track)
                    continue

                has_active_tracks = True
                audio_chunk = np.frombuffer(data, dtype=np.int16)

                if len(audio_chunk) < len(mixed_audio):
                    padded = np.zeros(len(mixed_audio), dtype=np.int16)
                    padded[: len(audio_chunk)] = audio_chunk
                    audio_chunk = padded
                    to_remove.append(track)

                mixed_audio += audio_chunk

            elif source_type == "queue":
                to_remove_queue = False
                if not data:
                    to_remove_queue = True
                else:
                    has_active_tracks = True
                    audio_chunk = np.frombuffer(data, dtype=np.int16)

                    if len(audio_chunk) < len(mixed_audio):
                        padded = np.zeros(len(mixed_audio), dtype=np.int16)
                        padded[: len(audio_chunk)] = audio_chunk
                        audio_chunk = padded
                        to_remove_queue = True

                    mixed_audio += audio_chunk

                if to_remove_queue:
                    with self._lock:
                        # Double check it hasn't changed? It shouldn't have in this short time generally,
                        # but technically set_current_from_queue could run.
                        # However, we are just notifying observers and setting to None if it is the same object.
                        if self.track_from_queue == source_obj:
                            self._notify_observers("queue_end")
                            self.track_from_queue = None

            elif source_type == "tts":
                to_remove_tts = False
                if not data:
                    to_remove_tts = True
                else:
                    has_active_tracks = True
                    audio_chunk = np.frombuffer(data, dtype=np.int16)

                    if len(audio_chunk) < len(mixed_audio):
                        padded = np.zeros(len(mixed_audio), dtype=np.int16)
                        padded[: len(audio_chunk)] = audio_chunk
                        audio_chunk = padded
                        to_remove_tts = True

                    mixed_audio += audio_chunk

                if to_remove_tts:
                    with self._lock:
                        if self.tts_track == source_obj:
                            if self.tts_track:
                                self.tts_track.cleanup()
                            self.tts_track = None

        # Clean up finished regular tracks
        with self._lock:
            if to_remove:
                self._notify_observers("track_end", to_remove=to_remove)

            for track in to_remove:
                if track in self.tracks:
                    self.tracks.remove(track)
                    track.cleanup()

        self.has_active_tracks = has_active_tracks

        # Clipping: Ensure values stay within 16-bit integer range (-32768 to 32767)
        _ = np.clip(mixed_audio, -32768, 32767, out=mixed_audio)

        # Convert back to bytes
        return mixed_audio.astype(np.int16).tobytes()

    @override
    def cleanup(self):
        """Cleans up all tracks when the mixer is destroyed."""
        # Cancel any pending futures
        for future in self.pending_futures.values():
            future.cancel()
        self.pending_futures.clear()

        self.executor.shutdown(wait=False)
        with self._lock:
            if self.tracks:
                self._notify_observers("track_end", to_remove=self.tracks)
            if self.tts_track:
                self.tts_track.cleanup()
                self.tts_track = None
            for track in self.tracks:
                track.cleanup()
            self.tracks = []
