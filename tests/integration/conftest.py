import asyncio
import uuid
from typing import override
from unittest.mock import AsyncMock, MagicMock

import discord
import numpy as np
import pytest

from src.harpi_lib.api import GuildConfig, HarpiAPI
from src.harpi_lib.audio.mixer import MixerSource
from src.harpi_lib.audio.controller import AudioController


SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLES_PER_FRAME = 960
FRAME_SIZE = SAMPLES_PER_FRAME * CHANNELS * 2


class FakeAudioSource(discord.AudioSource):
    def __init__(
        self,
        frames: list[bytes] | None = None,
        frame_count: int = 10,
        frame_size: int = FRAME_SIZE,
    ):
        self._frames = frames
        self._frame_count = frame_count
        self._frame_size = frame_size
        self._current_frame = 0
        self._cleaned_up = False
        self.read_calls = 0
        self.id = str(uuid.uuid4())

    @override
    def read(self) -> bytes:
        self.read_calls += 1
        if self._cleaned_up:
            return b""
        if self._frames is not None:
            if self._current_frame >= len(self._frames):
                return b""
            frame = self._frames[self._current_frame]
            self._current_frame += 1
            return frame
        if self._current_frame >= self._frame_count:
            return b""
        self._current_frame += 1
        return generate_silence_frame(self._frame_size)

    @override
    def cleanup(self) -> None:
        self._cleaned_up = True


def generate_silence_frame(size: int = FRAME_SIZE) -> bytes:
    return np.zeros(size // 2, dtype=np.int16).tobytes()


def generate_tone_frame(
    frequency: int = 440, amplitude: int = 16000, size: int = FRAME_SIZE
) -> bytes:
    t = np.linspace(0, 20 / 1000, SAMPLES_PER_FRAME, dtype=np.float32)
    left = np.sin(2 * np.pi * frequency * t) * amplitude
    right = np.sin(2 * np.pi * frequency * t) * amplitude
    stereo = np.column_stack((left, right)).astype(np.int16).flatten()
    return stereo.tobytes()


def generate_noise_frame(
    amplitude: int = 10000, size: int = FRAME_SIZE
) -> bytes:
    noise = np.random.randint(-amplitude, amplitude, size // 2, dtype=np.int16)
    return noise.tobytes()


@pytest.fixture
def audio_frame_factory():
    def _create(
        frame_type: str = "silence",
        count: int = 10,
        frequency: int = 440,
        amplitude: int = 16000,
    ):
        frames = []
        for _ in range(count):
            if frame_type == "silence":
                frames.append(generate_silence_frame())
            elif frame_type == "tone":
                frames.append(generate_tone_frame(frequency, amplitude))
            elif frame_type == "noise":
                frames.append(generate_noise_frame(amplitude))
        return frames

    return _create


@pytest.fixture
def fake_audio_source_factory():
    def _create(
        frames: list[bytes] | None = None,
        frame_count: int = 10,
        frame_size: int = FRAME_SIZE,
    ):
        return FakeAudioSource(
            frames=frames, frame_count=frame_count, frame_size=frame_size
        )

    return _create


@pytest.fixture
def audio_pipeline():
    controller = AudioController()
    mixer = MixerSource(controller)
    return controller, mixer


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    bot.get_guild = MagicMock()
    return bot


@pytest.fixture
def mock_guild():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 12345
    guild.voice_client = None
    guild.get_channel = MagicMock()
    return guild


@pytest.fixture
def mock_voice_channel():
    channel = MagicMock(spec=discord.VoiceChannel)
    channel.id = 67890
    channel.connect = AsyncMock()
    return channel


@pytest.fixture
def mock_voice_client():
    vc = MagicMock()
    vc.is_connected = MagicMock(return_value=True)
    vc.is_playing = MagicMock(return_value=False)
    vc.disconnect = AsyncMock()
    vc.play = MagicMock()
    return vc


@pytest.fixture
def harpi_api_with_guild(
    mock_bot, mock_guild, mock_voice_channel, mock_voice_client
):
    mock_bot.get_guild.return_value = mock_guild
    mock_guild.get_channel.return_value = mock_voice_channel
    mock_voice_channel.connect.return_value = mock_voice_client

    api = HarpiAPI(mock_bot)

    controller = AudioController()
    mixer = MixerSource(controller)
    guild_config = GuildConfig(
        id=12345,
        mixer=mixer,
        controller=controller,
        voice_client=mock_voice_client,
        channel=mock_voice_channel,
    )
    api.guilds[12345] = guild_config

    return api, guild_config
