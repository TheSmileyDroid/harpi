"""Tests for the per-guild panel sampler."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, cast

import pytest

from src import bot_state
from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.music.ytmusic import YTMusicData
from src.panel import sampler, state
from src.panel.schemas import Directory, StatusSnapshot

from tests.fakes import (
    GUILD_A,
    FakeBot,
    FakeGuild,
    FakeSession,
    playing_status,
)

EMPTY_DIRECTORY = Directory(guild_id=None, guilds=[], channels=[])


def snap(
    progress: float = 1.0,
    online: bool = True,
    title: str = "Now Track",
) -> StatusSnapshot:
    return StatusSnapshot.model_validate({
        "bot": {"online": online},
        "guild_id": "1",
        "connection": {"connected": True, "channel_id": "10"},
        "playback": {
            "guild_id": "1",
            "connected": True,
            "is_playing": True,
            "is_paused": False,
            "current_music": {
                "title": title,
                "url": "https://example.com/track",
                "uploader": "Artist",
                "duration": 120,
                "thumbnail": "https://example.com/thumb.jpg",
            },
            "queue": [],
            "layers": [],
            "loop_mode": "OFF",
            "volume": 1.0,
            "progress": progress,
            "channel_id": "10",
        },
    })


def scripted(monkeypatch, values: list[StatusSnapshot]) -> None:
    remaining = list(values)

    async def provider(guild_id: int | None) -> StatusSnapshot:
        del guild_id
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    monkeypatch.setattr(state, "status_snapshot", provider)
    monkeypatch.setattr(
        state, "directory_snapshot", lambda guild_id: EMPTY_DIRECTORY
    )


async def drain(queue: asyncio.Queue[tuple[str, Any]]) -> list[str]:
    names: list[str] = []
    while not queue.empty():
        names.append(queue.get_nowait()[0])
    return names


async def open_sampler(guild_id: int | None = None):
    guild = sampler.GuildSampler(guild_id)
    queue = await guild.subscribe()
    await drain(queue)
    return guild, queue


def test_the_status_key_ignores_progress():
    first = sampler.without_progress(snap(progress=1.0))
    second = sampler.without_progress(snap(progress=99.0))

    assert first == second


async def test_progress_alone_does_not_republish_the_snapshot(monkeypatch):
    scripted(monkeypatch, [snap(progress=1.0), snap(progress=1.2)])
    guild, queue = await open_sampler()

    await guild.sample()

    assert await drain(queue) == []
    guild.unsubscribe(queue)


async def test_position_tracks_every_sample_without_a_frame(monkeypatch):
    scripted(monkeypatch, [snap(progress=1.0), snap(progress=1.4)])
    guild, queue = await open_sampler()

    await guild.sample()

    assert guild.position().progress == pytest.approx(1.4)
    assert await drain(queue) == []
    guild.unsubscribe(queue)


async def test_a_progress_jump_publishes_a_position_frame(monkeypatch):
    scripted(monkeypatch, [snap(progress=1.0), snap(progress=9.0)])
    guild, queue = await open_sampler()

    await guild.sample()

    name, payload = queue.get_nowait()
    assert name == "position"
    assert payload.progress == pytest.approx(9.0)
    guild.unsubscribe(queue)


async def test_a_state_change_publishes_the_snapshot(monkeypatch):
    scripted(monkeypatch, [snap(online=True), snap(online=False)])
    guild, queue = await open_sampler()

    await guild.sample()

    name, payload = queue.get_nowait()
    assert name == "status"
    assert payload.bot.online is False
    guild.unsubscribe(queue)


async def test_a_directory_change_publishes_the_listing(monkeypatch):
    scripted(monkeypatch, [snap()])
    listing = Directory(
        guild_id="1",
        guilds=[],
        channels=[],
    )
    directories = iter([EMPTY_DIRECTORY, listing, listing])
    monkeypatch.setattr(
        state, "directory_snapshot", lambda guild_id: next(directories)
    )
    guild, queue = await open_sampler()

    await guild.sample()

    name, payload = queue.get_nowait()
    assert name == "directory"
    assert payload.guild_id == "1"
    guild.unsubscribe(queue)


async def test_a_failing_sample_keeps_the_sampler_alive(monkeypatch):
    calls = {"count": 0}

    async def provider(guild_id: int | None) -> StatusSnapshot:
        del guild_id
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("bot loop unavailable")
        return snap()

    monkeypatch.setattr(state, "status_snapshot", provider)
    monkeypatch.setattr(
        state, "directory_snapshot", lambda guild_id: EMPTY_DIRECTORY
    )
    guild = sampler.GuildSampler(None)

    await guild.sample()
    assert guild.healthy is False
    assert guild.current() is None

    await guild.sample()
    assert guild.healthy is True
    assert guild.current() is not None


async def test_unsubscribing_stops_the_poll(monkeypatch):
    scripted(monkeypatch, [snap()])
    guild, queue = await open_sampler()
    assert guild._task is not None

    guild.unsubscribe(queue)

    assert guild._task is None


class ThreadedBot(FakeBot):
    """A bot whose loop lives in another thread, as production does."""

    def __init__(self, loop: asyncio.AbstractEventLoop, session: FakeSession):
        super().__init__([FakeGuild(GUILD_A, "Alpha")], session)
        self._loop = loop

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def is_ready(self) -> bool:
        return True

    def is_closed(self) -> bool:
        return False


async def test_the_sampler_reaches_a_bot_loop_in_another_thread():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        bot = ThreadedBot(loop, FakeSession(playing_status()))
        bot_state.init_bot(cast(HarpiBot, bot))
        guild = sampler.GuildSampler(GUILD_A)

        await guild.subscribe()

        current = guild.current()
        assert current is not None
        assert current.model_dump()["playback"]["current_music"]["title"] == (
            "Now Track"
        )
        assert guild.healthy is True
    finally:
        bot_state._bot_ref = None
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        loop.close()


async def test_a_mutation_pushes_to_an_already_open_stream(monkeypatch):
    monkeypatch.setattr(sampler, "POLL_SECONDS", 5)
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        session = FakeSession(playing_status())
        bot = ThreadedBot(loop, session)
        bot_state.init_bot(cast(HarpiBot, bot))
        guild = sampler.GuildSampler(GUILD_A)
        queued = await guild.subscribe()

        session._status = playing_status(
            current_music=YTMusicData({
                "title": "Pushed Track",
                "url": "https://example.com/pushed",
                "duration": 90,
            })
        )
        guild.poke()

        name, payload = await asyncio.wait_for(queued.get(), 2)
        assert name == "status"
        assert payload.model_dump()["playback"]["current_music"]["title"] == (
            "Pushed Track"
        )
    finally:
        bot_state._bot_ref = None
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        loop.close()


async def test_two_streams_receive_the_same_change(monkeypatch):
    holder = {"status": snap(online=True)}

    async def provider(guild_id: int | None) -> StatusSnapshot:
        del guild_id
        return holder["status"]

    monkeypatch.setattr(state, "status_snapshot", provider)
    monkeypatch.setattr(
        state, "directory_snapshot", lambda guild_id: EMPTY_DIRECTORY
    )
    guild = sampler.GuildSampler(None)
    first = await guild.subscribe()
    second = await guild.subscribe()

    holder["status"] = snap(online=False)
    await guild.sample()

    first_kind, first_payload = first.get_nowait()
    second_kind, second_payload = second.get_nowait()
    assert first_kind == second_kind == "status"
    assert first_payload.model_dump()["bot"]["online"] is False
    assert second_payload.model_dump()["bot"]["online"] is False
    guild.unsubscribe(first)
    guild.unsubscribe(second)


class RecordingSampler:
    def __init__(self) -> None:
        self.poked = 0

    def poke(self) -> None:
        self.poked += 1


def test_poke_sampler_wakes_only_a_registered_sampler(monkeypatch):
    recorded = RecordingSampler()
    monkeypatch.setattr(sampler, "_samplers", {7: recorded})

    sampler.poke_sampler(7)
    sampler.poke_sampler(8)

    assert recorded.poked == 1
