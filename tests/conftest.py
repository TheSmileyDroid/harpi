from typing import override

import discord
import numpy as np
import pytest

from src.HarpiLib.music.soundboard import SoundboardController
from src.HarpiLib.music.mixer import MixerSource


SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLES_PER_FRAME = 960
FRAME_SIZE = SAMPLES_PER_FRAME * CHANNELS * 2


class MockAudioSource(discord.AudioSource):
    def __init__(
        self,
        frames: list[bytes] | None = None,
        repeat: bool = False,
        frame_count: int = 10,
    ):
        self._frames = frames
        self._repeat = repeat
        self._frame_count = frame_count
        self._current_frame = 0
        self._cleaned_up = False
        self.read_calls = 0

    @override
    def read(self) -> bytes:
        self.read_calls += 1

        if self._cleaned_up:
            return b""

        if self._frames is not None:
            if self._current_frame >= len(self._frames):
                if self._repeat:
                    self._current_frame = 0
                else:
                    return b""
            frame = self._frames[self._current_frame]
            self._current_frame += 1
            return frame

        if self._current_frame >= self._frame_count:
            return b""
        self._current_frame += 1
        return generate_silence_frame()

    @override
    def cleanup(self) -> None:
        self._cleaned_up = True


class MockYoutubeDLSource:
    def __init__(
        self,
        frames: list[bytes] | None = None,
        repeat: bool = False,
        frame_count: int = 10,
        title: str = "Test Track",
    ):
        self._audio_source = MockAudioSource(
            frames=frames, repeat=repeat, frame_count=frame_count
        )
        self.title = title
        self.url = "https://example.com/test"
        self.id = f"test-{id(self)}"
        self.volume = 0.5
        self._cleaned_up = False

    def read(self) -> bytes:
        return self._audio_source.read()

    def cleanup(self) -> None:
        self._cleaned_up = True
        self._audio_source.cleanup()


def generate_silence_frame() -> bytes:
    return np.zeros(SAMPLES_PER_FRAME * CHANNELS, dtype=np.int16).tobytes()


def generate_tone_frame(frequency: int = 440, amplitude: int = 16000) -> bytes:
    t = np.linspace(0, 20 / 1000, SAMPLES_PER_FRAME, dtype=np.float32)
    left = np.sin(2 * np.pi * frequency * t) * amplitude
    right = np.sin(2 * np.pi * frequency * t) * amplitude
    stereo = np.column_stack((left, right)).astype(np.int16).flatten()
    return stereo.tobytes()


def generate_noise_frame(amplitude: int = 10000) -> bytes:
    noise = np.random.randint(
        -amplitude, amplitude, SAMPLES_PER_FRAME * CHANNELS, dtype=np.int16
    )
    return noise.tobytes()


@pytest.fixture
def silence_frame() -> bytes:
    return generate_silence_frame()


@pytest.fixture
def tone_frame() -> bytes:
    return generate_tone_frame()


@pytest.fixture
def noise_frame() -> bytes:
    return generate_noise_frame()


@pytest.fixture
def mock_audio_source():
    def _create(
        frames: list[bytes] | None = None,
        repeat: bool = False,
        frame_count: int = 10,
    ) -> MockAudioSource:
        return MockAudioSource(
            frames=frames, repeat=repeat, frame_count=frame_count
        )

    return _create


@pytest.fixture
def mock_ytdl_source():
    def _create(
        frames: list[bytes] | None = None,
        repeat: bool = False,
        frame_count: int = 10,
        title: str = "Test Track",
    ) -> MockYoutubeDLSource:
        return MockYoutubeDLSource(
            frames=frames, repeat=repeat, frame_count=frame_count, title=title
        )

    return _create


@pytest.fixture
def soundboard_controller() -> SoundboardController:
    return SoundboardController()


@pytest.fixture
def mixer_source(soundboard_controller: SoundboardController) -> MixerSource:
    return MixerSource(soundboard_controller)
