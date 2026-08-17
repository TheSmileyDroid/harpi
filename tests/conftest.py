"""Shared fakes for the session lifecycle tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import discord

from src.harpi_lib.music.ytmusicdata import YTMusicData

GUILD_ID = 1
CHANNEL_ID = 10
BOT_USER_ID = 1234


class FakeVoiceClient(discord.VoiceClient):
    """Stands in for a real voice client without a websocket or channel."""

    def __init__(
        self,
        guild: FakeGuild | None = None,
        channel: FakeChannel | None = None,
    ) -> None:
        self._guild = guild
        self.channel = channel  # type: ignore
        self.played_source: discord.AudioSource | None = None
        self.disconnected = False
        self._playing = False
        self._paused = False

    def play(
        self,
        source: discord.AudioSource,
        **kwargs: Any,
    ) -> None:
        self.played_source = source
        self._playing = True

    def is_playing(self) -> bool:
        return self._playing

    def is_paused(self) -> bool:
        return self._paused

    def is_connected(self) -> bool:
        return not self.disconnected

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    async def disconnect(self, *, force: bool = False) -> None:
        self.disconnected = True
        self._playing = False
        self._paused = False
        if self._guild is not None:
            self._guild.voice_client = None


class FakeSource(discord.AudioSource):
    """Audio source that records whether it was cleaned up."""

    def __init__(self) -> None:
        self.cleaned_up = False
        self.volume = 1.0
        self.music_data: Any = None

    def read(self) -> bytes:
        return b""

    def cleanup(self) -> None:
        self.cleaned_up = True


class FakeMusicData(YTMusicData):
    """Minimal YTMusicData stand-in for session tests."""

    def __init__(self, title: str, duration: int = 180) -> None:
        super().__init__({
            "title": title,
            "url": f"https://example.com/{title}",
            "duration": duration,
        })


class FakeMusicDataFactory:
    """Fake YTMusicData stand-in whose ``from_url`` splits on commas."""

    @classmethod
    async def from_url(cls, url: str) -> list[FakeMusicData]:
        return [
            FakeMusicData(part.strip())
            for part in url.split(",")
            if part.strip()
        ]


class FakeLayerSource(FakeSource):
    """Audio source carrying the metadata a background layer needs."""

    def __init__(
        self,
        title: str = "Layer",
        url: str = "https://example.com/layer",
        volume: float = 0.7,
        layer_id: str | None = None,
    ) -> None:
        super().__init__()
        self.id = layer_id or f"layer-{title}"
        self.title = title
        self.url = url
        self.volume = volume


class FakeLayerSourceFactory:
    """Fake YoutubeDLSource stand-in that yields layer sources."""

    @classmethod
    async def from_music_data(
        cls, music_data: Any, volume: float = 0.3
    ) -> FakeLayerSource:
        return FakeLayerSource(
            title=music_data.title,
            url=music_data.url,
            volume=volume,
            layer_id=f"layer-{music_data.title}",
        )


class FakeTTSSource(FakeSource):
    """Fake FastStartFFmpegPCMAudio stand-in; records the audio stream.

    The session's ``play_tts`` verb constructs it like the real class:
    ``FakeTTSSource(audio, pipe=True)``.
    """

    def __init__(
        self,
        source: Any = None,
        *,
        pipe: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.source = source
        self.pipe = pipe


class FakeSourceFactory:
    """Fake YoutubeDLSource stand-in for session tests.

    Loads succeed by default and return a :class:`FakeSource` that carries
    the loaded ``music_data``.  Patch ``failures`` to simulate load
    failures keyed by track title.
    """

    failures: dict[str, Exception] = {}

    @classmethod
    async def from_music_data(
        cls, music_data: Any, volume: float = 0.3
    ) -> FakeSource:
        failure = cls.failures.get(getattr(music_data, "title", None))
        if failure is not None:
            raise failure
        source = FakeSource()
        source.music_data = music_data
        source.volume = volume
        return source


class FakeAnnouncer:
    """Records the messages a session announces into the channel."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def __call__(self, message: str) -> None:
        self.messages.append(message)


class FakeChannel:
    def __init__(self, guild: FakeGuild) -> None:
        self.guild = guild
        self.id = 42
        self.name = "Voice Channel"
        self.connect_calls = 0

    async def connect(self) -> FakeVoiceClient:
        self.connect_calls += 1
        client = FakeVoiceClient(self.guild, channel=self)
        self.guild.voice_client = client
        return client


class FakeGuild:
    def __init__(self, guild_id: int) -> None:
        self.id = guild_id
        self.name = "Test Guild"
        self.voice_client: FakeVoiceClient | None = None
        self._channels: dict[int, FakeChannel] = {}

    def get_channel(self, channel_id: int) -> FakeChannel | None:
        return self._channels.get(channel_id)


class FakeBot:
    def __init__(self) -> None:
        self.user = SimpleNamespace(id=BOT_USER_ID)
        self._guilds: dict[int, FakeGuild] = {}
        self.loop = asyncio.get_event_loop()

    def get_guild(self, guild_id: int) -> FakeGuild | None:
        return self._guilds.get(guild_id)
