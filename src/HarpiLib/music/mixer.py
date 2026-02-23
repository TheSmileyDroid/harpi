from src.HarpiLib.music.soundboard import SoundboardController
import concurrent.futures
import threading
from typing import Callable, override

import discord
import numpy as np
from loguru import logger


class MixerSource(discord.AudioSource):
    def __init__(self, soundboard: SoundboardController):
        self._lock: threading.Lock = threading.Lock()
        self.has_active_tracks: bool = False
        self.soundboard: SoundboardController = soundboard
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

    def add_observer(self, event: str, callback: Callable):
        if event not in self._observers:
            self._observers[event] = []
        self._observers[event].append(callback)

    def remove_observer(self, event: str, callback: Callable):
        if event in self._observers and callback in self._observers[event]:
            self._observers[event].remove(callback)

    def _notify_observers(self, event: str, **kwargs):
        if event in self._observers:
            for callback in self._observers[event]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    logger.error(
                        f"Error in observer callback for {event}: {e}"
                    )

    def _read_track(self, track: discord.AudioSource):
        try:
            return track.read()
        except Exception as e:
            logger.error(f"Error reading track: {e}")
            return b""

    @override
    def read(self):
        mixed_audio = np.zeros(
            self.SAMPLES_PER_FRAME * self.CHANNELS, dtype=np.int32
        )

        to_remove: list[discord.AudioSource] = []
        has_active_tracks = False

        sources_to_read: list[tuple[str, discord.AudioSource]] = []
        sources_to_read = self.soundboard.get_playing_sounds()

        for _, source in sources_to_read:
            if source not in self.pending_futures:
                self.pending_futures[source] = self.executor.submit(
                    self._read_track, source
                )

        active_sources = {s for _, s in sources_to_read}
        for s in list(self.pending_futures.keys()):
            if s not in active_sources:
                self.pending_futures[s].cancel()
                del self.pending_futures[s]

        current_futures = [
            self.pending_futures[s]
            for _, s in sources_to_read
            if s in self.pending_futures
        ]

        if current_futures:
            concurrent.futures.wait(current_futures, timeout=self.READ_TIMEOUT)

        for source_type, source_obj in sources_to_read:
            if source_obj not in self.pending_futures:
                continue

            future = self.pending_futures[source_obj]

            if not future.done():
                has_active_tracks = True
                continue

            del self.pending_futures[source_obj]

            try:
                data = future.result()
            except Exception as e:
                logger.error(
                    f"Unexpected error in thread for {source_type}: {e}"
                )
                data = b""

            should_remove = False
            if not data:
                should_remove = True
            else:
                has_active_tracks = True
                audio_chunk = np.frombuffer(data, dtype=np.int16)

                if len(audio_chunk) < len(mixed_audio):
                    padded = np.zeros(len(mixed_audio), dtype=np.int16)
                    padded[: len(audio_chunk)] = audio_chunk
                    audio_chunk = padded
                    should_remove = True

                mixed_audio += audio_chunk

            if should_remove:
                to_remove.append(source_obj)
                if source_type == "track":
                    self._notify_observers("track_end", to_remove=[source_obj])
                elif source_type == "queue":
                    self._notify_observers("queue_end")
                    self.soundboard._on_track_finished(source_obj)
                elif source_type == "tts":
                    self.soundboard.set_tts_track(None)
                elif source_type == "button":
                    pass

        for source in to_remove:
            self.soundboard.remove_finished_source(source)

        self.has_active_tracks = has_active_tracks

        _ = np.clip(mixed_audio, -32768, 32767, out=mixed_audio)

        return mixed_audio.astype(np.int16).tobytes()

    @override
    def cleanup(self):
        for future in self.pending_futures.values():
            future.cancel()
        self.pending_futures.clear()

        self.executor.shutdown(wait=False)
