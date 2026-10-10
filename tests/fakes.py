"""Shared fakes for the HTTP-level tests and the Playwright harness.

These stand in for the bot, its guilds, and a playback session at the API
seam.  They record the session verbs an endpoint reaches and answer the
readiness calls server truth needs, so the JSON contract can be driven over
the app's own HTTP seam without a Discord connection.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from src.harpi_lib.audio.session import LoopMode, SessionStatus
from src.harpi_lib.music.ytmusic import YTMusicData

GUILD_A = 1
GUILD_B = 2


@dataclass
class FakeVoiceChannel:
    id: int
    name: str


class FakeGuild:
    def __init__(self, guild_id: int, name: str) -> None:
        self.id = guild_id
        self.name = name
        self.voice_client = None
        self.voice_channels = [
            FakeVoiceChannel(guild_id * 10, f"Channel {guild_id}")
        ]


class FakeSession:
    def __init__(self, status: SessionStatus | None = None) -> None:
        self._status = status
        self.calls: list[Any] = []

    async def sample_status(self) -> SessionStatus | None:
        return self._status

    async def skip(self) -> None:
        self.calls.append("skip")

    async def clear_queue(self) -> None:
        self.calls.append("clear_queue")

    async def remove(self, value: str) -> None:
        self.calls.append(("remove", value))

    async def remove_layer(self, value: str) -> None:
        self.calls.append(("remove_layer", value))

    async def add_layer(self, value: str) -> None:
        self.calls.append(("add_layer", value))

    async def play(self, value: str) -> None:
        self.calls.append(("play", value))
        self._status = SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": value,
                "url": value,
                "duration": 60,
            }),
        )

    async def seek(self, value: float, absolute: bool = False) -> None:
        self.calls.append(("seek", value, absolute))

    async def set_volume(self, value: float) -> None:
        self.calls.append(("set_volume", value))

    async def set_layer_volume(self, layer_id: str, value: float) -> None:
        self.calls.append(("set_layer_volume", layer_id, value))

    async def previous(self) -> None:
        self.calls.append("previous")


class FailingPlaySession(FakeSession):
    async def play(self, value: str) -> None:
        raise ValueError("yt explodiu")


class FakeSessionManager:
    def __init__(self, session: FakeSession | None = None) -> None:
        self._session = session
        self.connect_calls: list[tuple[int, int]] = []
        self.disconnect_calls: list[int] = []

    def get(self, _guild_id: int) -> FakeSession | None:
        return self._session

    async def connect(self, guild_id: int, channel_id: int) -> None:
        self.connect_calls.append((guild_id, channel_id))

    async def disconnect(self, guild_id: int) -> None:
        self.disconnect_calls.append(guild_id)


class FakeBot:
    def __init__(
        self,
        guilds: list[FakeGuild],
        session: FakeSession | None = None,
    ) -> None:
        self.user = SimpleNamespace(id=1234)
        self._guilds = {g.id: g for g in guilds}
        self.sessions = FakeSessionManager(session)

    @property
    def loop(self):
        return asyncio.get_running_loop()

    @property
    def guilds(self) -> list[FakeGuild]:
        return list(self._guilds.values())

    def get_guild(self, guild_id: int) -> FakeGuild | None:
        return self._guilds.get(guild_id)

    async def fetch_guilds(self, limit: int | None = None):
        del limit
        for guild in self._guilds.values():
            yield guild


class FakeReadyBot:
    """A bot that only answers the readiness calls ``bot_connected`` reads."""

    def __init__(self, ready: bool, closed: bool) -> None:
        self._ready = ready
        self._closed = closed

    def is_ready(self) -> bool:
        return self._ready

    def is_closed(self) -> bool:
        return self._closed


def playing_status(**overrides: Any) -> SessionStatus:
    values: dict[str, Any] = {
        "guild_id": GUILD_A,
        "connected": True,
        "is_playing": True,
        "is_paused": False,
        "current_music": YTMusicData({
            "title": "Now Track",
            "uploader": "Artist",
            "duration": 120,
        }),
        "loop_mode": LoopMode.OFF,
        "volume": 0.7,
        "progress": 0.0,
    }
    values.update(overrides)
    return SessionStatus(**values)


def found_track(**overrides: Any) -> YTMusicData:
    values: dict[str, Any] = {
        "title": "Found Track",
        "url": "https://www.youtube.com/watch?v=found",
        "uploader": "Artist",
        "duration": 30,
        "thumbnails": [
            {"url": "https://img.example.com/found.jpg", "width": 336}
        ],
    }
    values.update(overrides)
    return YTMusicData(values)


def patch_search(monkeypatch, results: list[YTMusicData]) -> None:
    async def fake_from_url(term: str) -> list[YTMusicData]:
        return results

    monkeypatch.setattr(YTMusicData, "from_url", staticmethod(fake_from_url))
