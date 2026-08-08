"""Panel music API read-model tests.

``get_music_data`` is the single reader the panel JSON and the HTMX
fragments share.  It must consume the session status snapshot, not the
legacy guild config, so these tests pin the projection from a
:class:`SessionStatus` into the panel's :class:`MusicStatusResponse` and
the async bridge that samples the session on the bot loop.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest

import src.api.deps as deps
import src.api.music as music_module
from src.api.music import build_music_status, get_music_data
from src.api.server_status import get_server_status
from src.harpi_lib.audio.session import LoopMode, PlaybackSession, SessionStatus
from src.harpi_lib.music.ytmusicdata import YTMusicData
from tests.conftest import (
    GUILD_ID,
    FakeChannel,
    FakeGuild,
    FakeMusicData,
    FakeVoiceClient,
)


def _fake_bot(
    session: PlaybackSession | None, *, ready: bool = True
) -> SimpleNamespace:
    guild = FakeGuild(GUILD_ID)
    if session is not None:
        guild.voice_client = cast(FakeVoiceClient, session._voice_client)

    class _Sessions:
        def get(self, guild_id: int) -> PlaybackSession | None:
            return session if guild_id == GUILD_ID else None

    return SimpleNamespace(
        loop=asyncio.get_running_loop(),
        latency=0.25,
        is_ready=lambda: ready,
        get_guild=lambda guild_id: guild if guild_id == GUILD_ID else None,
        sessions=_Sessions(),
        api=SimpleNamespace(
            get_guild_config=lambda guild_id: None,
        ),
    )


def _install_bot(monkeypatch: pytest.MonkeyPatch, bot: SimpleNamespace) -> None:
    monkeypatch.setattr(deps, "_bot_ref", bot)


async def _make_session() -> PlaybackSession:
    guild = FakeGuild(GUILD_ID)
    channel = FakeChannel(guild)
    session = PlaybackSession(
        guild_id=GUILD_ID,
        voice_client=await channel.connect(),
        loop=asyncio.get_running_loop(),
    )
    session.start()
    return session


def _track(title: str, duration: int = 180) -> YTMusicData:
    return FakeMusicData(title, duration=duration)


async def test_get_music_data_returns_none_for_an_unknown_guild(monkeypatch):
    bot = SimpleNamespace(
        loop=asyncio.get_running_loop(),
        get_guild=lambda guild_id: None,
        sessions=SimpleNamespace(get=lambda guild_id: None),
    )
    _install_bot(monkeypatch, bot)

    assert await get_music_data(999) is None


async def test_get_music_data_returns_empty_for_a_guild_without_a_session(monkeypatch):
    _install_bot(monkeypatch, _fake_bot(None))

    status = await get_music_data(GUILD_ID)

    assert status is not None
    assert status.current_music is None
    assert status.queue == []
    assert status.is_playing is False
    assert status.is_paused is False


async def test_get_music_data_projects_the_session_snapshot(monkeypatch):
    session = await _make_session()
    session._queue = [_track("two", duration=200)]
    session._current_music = _track("one", duration=180)
    session._volume = 1.5
    session._loop_mode = LoopMode.QUEUE
    cast(FakeVoiceClient, session._voice_client)._paused = True
    _install_bot(monkeypatch, _fake_bot(session))

    status = await get_music_data(GUILD_ID)

    assert status is not None
    assert status.current_music is not None
    assert status.current_music.title == "one"
    assert status.current_music.duration == 180
    assert status.queue == [music_module.QueueItemResponse(
        title="two", duration=200, url="https://example.com/two"
    )]
    assert status.is_paused is True
    assert status.loop_mode == "queue"
    assert status.volume == pytest.approx(1.5)


def test_build_music_status_projects_progress_in_milliseconds():
    status = SessionStatus(
        guild_id=GUILD_ID,
        connected=True,
        is_playing=True,
        is_paused=False,
        current_music=_track("one"),
        progress=12.25,
        volume=0.7,
    )

    response = build_music_status(status)

    assert response.progress == 12250
    assert response.volume == pytest.approx(0.7)
    assert response.loop_mode == "off"


async def test_get_server_status_counts_sessions_with_queued_music(monkeypatch):
    session = await _make_session()
    session._queue = [_track("two"), _track("three")]
    bot = _fake_bot(session)
    _install_bot(monkeypatch, bot)

    status = await get_server_status(
        [SimpleNamespace(id=GUILD_ID), SimpleNamespace(id=999)],
        bot=cast(Any, bot),
    )

    assert status["music_guilds"] == 1
    assert status["queue_total"] == 2
    assert status["bot_connected"] is True
    assert status["bot_latency"] == pytest.approx(250.0)


async def test_get_server_status_ignores_guilds_without_sessions(monkeypatch):
    bot = _fake_bot(None, ready=False)
    _install_bot(monkeypatch, bot)

    status = await get_server_status(
        [SimpleNamespace(id=GUILD_ID)],
        bot=cast(Any, bot),
    )

    assert status["music_guilds"] == 0
    assert status["queue_total"] == 0
    assert status["bot_connected"] is False
