from typing import override

import discord
import numpy as np


class TestToneSource(discord.AudioSource):
    SAMPLE_RATE = 48000
    CHANNELS = 2
    SAMPLES_PER_FRAME = 960
    FRAME_SIZE = SAMPLES_PER_FRAME * CHANNELS * 2

    def __init__(
        self,
        frequency: int = 440,
        duration_ms: int = 1000,
        amplitude: int = 16000,
        name: str = "Test Tone",
    ) -> None:
        self._frequency = frequency
        self._amplitude = amplitude
        self._name = name
        self._frames_total = int(
            (duration_ms / 1000) * (self.SAMPLE_RATE / self.SAMPLES_PER_FRAME)
        )
        self._current_frame = 0
        self._cleaned_up = False
        self._precomputed_frame: bytes = self._generate_tone_frame()

    def _generate_tone_frame(self) -> bytes:
        t = np.linspace(0, 20 / 1000, self.SAMPLES_PER_FRAME, dtype=np.float32)
        tone = np.sin(2 * np.pi * self._frequency * t) * self._amplitude
        stereo = np.column_stack((tone, tone)).astype(np.int16).flatten()
        return stereo.tobytes()

    @override
    def read(self) -> bytes:
        if self._cleaned_up:
            return b""
        if self._current_frame >= self._frames_total:
            return b""
        self._current_frame += 1
        return self._precomputed_frame

    @override
    def cleanup(self) -> None:
        self._cleaned_up = True

    @property
    def frequency(self) -> int:
        return self._frequency

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_finished(self) -> bool:
        return self._current_frame >= self._frames_total


class MultiFrequencyTestSource(discord.AudioSource):
    SAMPLE_RATE = 48000
    CHANNELS = 2
    SAMPLES_PER_FRAME = 960
    FRAME_SIZE = SAMPLES_PER_FRAME * CHANNELS * 2

    def __init__(
        self,
        frequencies: list[int] | None = None,
        duration_per_freq_ms: int = 500,
        amplitude: int = 12000,
        name: str = "Multi-Frequency Test",
    ) -> None:
        self._frequencies = frequencies or [261, 329, 392, 523]
        self._amplitude = amplitude
        self._name = name
        self._frames_per_freq = int(
            (duration_per_freq_ms / 1000)
            * (self.SAMPLE_RATE / self.SAMPLES_PER_FRAME)
        )
        self._current_frame = 0
        self._current_freq_index = 0
        self._cleaned_up = False
        self._precomputed_frames: list[bytes] = self._generate_all_frames()

    def _generate_tone_frame(self, frequency: int) -> bytes:
        t = np.linspace(0, 20 / 1000, self.SAMPLES_PER_FRAME, dtype=np.float32)
        tone = np.sin(2 * np.pi * frequency * t) * self._amplitude
        stereo = np.column_stack((tone, tone)).astype(np.int16).flatten()
        return stereo.tobytes()

    def _generate_all_frames(self) -> list[bytes]:
        return [self._generate_tone_frame(freq) for freq in self._frequencies]

    @override
    def read(self) -> bytes:
        if self._cleaned_up:
            return b""
        if self._current_freq_index >= len(self._frequencies):
            return b""
        frame = self._precomputed_frames[self._current_freq_index]
        self._current_frame += 1
        if self._current_frame >= self._frames_per_freq:
            self._current_frame = 0
            self._current_freq_index += 1
        return frame

    @override
    def cleanup(self) -> None:
        self._cleaned_up = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def current_frequency(self) -> int | None:
        if self._current_freq_index < len(self._frequencies):
            return self._frequencies[self._current_freq_index]
        return None
