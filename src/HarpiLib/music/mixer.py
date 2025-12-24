import threading
from typing import Callable, override

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

        self.ending_song_observers: Callable | None = None
        self.queue_observers: Callable | None = None

        # Audio constants for Discord (48kHz Stereo 16-bit)
        self.SAMPLE_RATE: int = 48000
        self.CHANNELS: int = 2
        self.SAMPLES_PER_FRAME: int = 960  # 20ms of audio
        self.FRAME_SIZE: int = (
            self.SAMPLES_PER_FRAME * self.CHANNELS * 2
        )  # Bytes per frame (3840)

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

    def _read_track(self, track: YoutubeDLSource):
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

        with self._lock:
            for track in self.tracks:
                data = self._read_track(track)

                # If track is finished or empty
                if not data:
                    to_remove.append(track)
                    continue

                has_active_tracks = True

                # Convert bytes to numpy array (int16)
                # Note: If the chunk is smaller than expected (end of file), we pad it
                audio_chunk = np.frombuffer(data, dtype=np.int16)

                if len(audio_chunk) < len(mixed_audio):
                    # Pad with zeros if chunk is short
                    padded = np.zeros(len(mixed_audio), dtype=np.int16)
                    padded[: len(audio_chunk)] = audio_chunk
                    audio_chunk = padded
                    to_remove.append(
                        track
                    )  # Mark as finished after this partial chunk

                # Add audio to the mix
                mixed_audio += audio_chunk
            if self.track_from_queue:
                to_remove_queue = False
                data = self._read_track(self.track_from_queue)

                # If track is finished or empty
                if not data:
                    to_remove_queue = True
                else:
                    has_active_tracks = True

                    # Convert bytes to numpy array (int16)
                    # Note: If the chunk is smaller than expected (end of file), we pad it
                    audio_chunk = np.frombuffer(data, dtype=np.int16)

                    if len(audio_chunk) < len(mixed_audio):
                        # Pad with zeros if chunk is short
                        padded = np.zeros(len(mixed_audio), dtype=np.int16)
                        padded[: len(audio_chunk)] = audio_chunk
                        audio_chunk = padded
                        to_remove_queue = True

                    # Add audio to the mix
                    mixed_audio += audio_chunk

                if to_remove_queue:
                    if self.queue_observers:
                        self.queue_observers()
                    self.track_from_queue = None

            if self.tts_track:
                to_remove_tts = False
                try:
                    data = self.tts_track.read()
                except Exception as e:
                    print(f"Error reading TTS track: {e}")
                    data = b""

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
                    self.tts_track.cleanup()
                    self.tts_track = None

            # Clean up finished tracks
            if to_remove and self.ending_song_observers:
                self.ending_song_observers(to_remove=to_remove)
            for track in to_remove:
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
        with self._lock:
            if self.tracks and self.ending_song_observers:
                self.ending_song_observers(to_remove=self.tracks)
            if self.tts_track:
                self.tts_track.cleanup()
                self.tts_track = None
            for track in self.tracks:
                track.cleanup()
            self.tracks = []
