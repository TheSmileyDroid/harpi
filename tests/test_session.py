"""Lifecycle tests for PlaybackSession.

The session is the primary seam under test: it owns the voice client, the
controller, and the mixer, and wires the mixer's end-of-track observers to
its own handlers so no outside service needs to.  These tests exercise the
verbs the cogs and routes will call and the wiring the session owns.
"""

import asyncio
from typing import cast

import pytest

import src.harpi_lib.audio.session as session_module
from src.harpi_lib.audio.session import LoopMode, PlaybackSession, SessionStatus
from src.harpi_lib.music.ytmusicdata import ProbeEnvironmentError
from tests.conftest import (
    FakeAnnouncer,
    FakeChannel,
    FakeGuild,
    FakeMusicDataFactory,
    FakeSource,
    FakeSourceFactory,
    FakeVoiceClient,
)


def test_status_snapshot_reads_from_the_voice_client():
    voice_client = FakeVoiceClient()
    voice_client._playing = True
    session = PlaybackSession(guild_id=1, voice_client=voice_client)

    status = session.status

    assert status == SessionStatus(
        guild_id=1, connected=True, is_playing=True, is_paused=False
    )


def test_status_reflects_a_disconnected_voice_client():
    voice_client = FakeVoiceClient()
    voice_client.disconnected = True
    session = PlaybackSession(guild_id=1, voice_client=voice_client)

    status = session.status

    assert status.connected is False


def test_start_plays_the_mixer_on_the_voice_client():
    voice_client = FakeVoiceClient()
    session = PlaybackSession(guild_id=1, voice_client=voice_client)

    session.start()

    assert voice_client.is_playing() is True
    assert voice_client.played_source is session._mixer


def test_cleanup_releases_sources_and_shuts_down_the_mixer():
    session = PlaybackSession(guild_id=1, voice_client=FakeVoiceClient())
    source = FakeSource()
    session._controller.set_queue_source(source)

    session.cleanup()

    assert source.cleaned_up is True
    assert session._controller.get_playing_sounds() == []
    assert session._mixer._shutdown is True


async def test_leave_disconnects_the_voice_client():
    voice_client = FakeVoiceClient()
    session = PlaybackSession(guild_id=1, voice_client=voice_client)

    await session.leave()

    assert voice_client.disconnected is True


async def test_leave_skips_when_already_disconnected():
    voice_client = FakeVoiceClient()
    voice_client.disconnected = True
    session = PlaybackSession(guild_id=1, voice_client=voice_client)

    await session.leave()

    assert voice_client.disconnected is True


def test_mixer_end_of_track_observers_are_wired_to_the_session():
    session = PlaybackSession(guild_id=1, voice_client=FakeVoiceClient())

    assert session._mixer._observers["queue_end"] == [session._on_queue_end]
    assert session._mixer._observers["track_end"] == [session._on_track_end]


def _make_session(
    *,
    loop: asyncio.AbstractEventLoop | None = None,
    announcer: FakeAnnouncer | None = None,
) -> PlaybackSession:
    session = PlaybackSession(guild_id=1, voice_client=FakeVoiceClient(), loop=loop)
    session.start()
    if announcer is not None:
        session.set_announcer(announcer)
    return session


def _install_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_module, "YTMusicData", FakeMusicDataFactory)
    monkeypatch.setattr(session_module, "YoutubeDLSource", FakeSourceFactory)


async def _pump(times: int = 10) -> None:
    for _ in range(times):
        await asyncio.sleep(0)


class SeekSource(FakeSource):
    def __init__(self) -> None:
        super().__init__()
        self.position = 0.0
        self.seek_calls: list[float] = []

    def position_seconds(self) -> float:
        return self.position

    def seek(self, position: float) -> None:
        self.seek_calls.append(position)
        self.position = position


class SeekSourceFactory:
    @classmethod
    async def from_music_data(cls, music_data, volume: float = 0.3) -> SeekSource:
        return SeekSource()


async def test_play_queues_tracks_and_starts_playing(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)

    count = await session.play("one,two")

    assert count == 2
    current = session.status.current_music
    assert current is not None
    assert current.title == "one"
    assert [m.title for m in session.status.queue] == ["two"]
    assert session.status.is_playing is True


async def test_play_appends_to_the_queue_while_a_track_is_playing(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)

    await session.play("one")
    await session.play("two,three")

    assert [m.title for m in session.status.queue] == ["two", "three"]


async def test_play_raises_when_nothing_is_found(monkeypatch):
    class EmptyFactory:
        @classmethod
        async def from_url(cls, url: str) -> list:
            return []

    session = _make_session()
    monkeypatch.setattr(session_module, "YTMusicData", EmptyFactory)

    with pytest.raises(ValueError):
        await session.play("nothing")


async def test_stop_clears_the_queue_and_releases_the_current_source(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two")
    source = session._controller.get_queue_source()
    assert source is not None
    fake_source = cast(FakeSource, source)

    await session.stop()

    assert session.status.current_music is None
    assert session.status.queue == ()
    assert fake_source.cleaned_up is True


async def test_skip_advances_to_the_next_track(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two")

    await session.skip()

    current = session.status.current_music
    assert current is not None
    assert current.title == "two"
    assert session.status.queue == ()


async def test_skip_with_an_empty_queue_is_a_noop():
    session = _make_session()

    await session.skip()

    assert session.status.current_music is None


async def test_seek_positions_the_current_track(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await session.play("one")

    moved = await session.seek(30.0, absolute=True)

    assert moved is True
    assert session.status.progress == pytest.approx(30.0)


async def test_seek_without_a_source_reports_no_movement(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)

    moved = await session.seek(30.0, absolute=True)

    assert moved is False


async def test_relative_seek_moves_from_the_current_position(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await session.play("one")
    await session.seek(30.0, absolute=True)

    await session.seek(-10.0)

    assert session.status.progress == pytest.approx(20.0)


async def test_relative_seek_does_not_go_before_the_start(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await session.play("one")

    await session.seek(-1000.0)

    assert session.status.progress == pytest.approx(0.0)


async def test_seek_clamps_to_the_track_duration(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await session.play("one")
    current = session.status.current_music
    assert current is not None
    duration = current.duration
    assert duration is not None

    await session.seek(10000.0, absolute=True)

    assert session.status.progress == pytest.approx(float(duration))


async def test_set_loop_changes_the_loop_mode():
    session = _make_session()

    await session.set_loop(LoopMode.TRACK)

    assert session.status.loop_mode is LoopMode.TRACK


async def test_set_volume_applies_to_the_current_source(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one")

    await session.set_volume(1.5)

    assert session.status.volume == pytest.approx(1.5)
    source = session._controller.get_queue_source()
    assert source is not None
    assert cast(FakeSource, source).volume == pytest.approx(1.5)


async def test_set_volume_clamps_to_the_allowed_range():
    session = _make_session()

    await session.set_volume(5.0)

    assert session.status.volume == pytest.approx(2.0)


async def test_pause_pauses_the_voice_client():
    session = _make_session()

    await session.pause()

    status = session.status
    assert status.is_paused is True
    assert status.is_playing is True


async def test_resume_resumes_the_voice_client():
    session = _make_session()
    await session.pause()

    await session.resume()

    status = session.status
    assert status.is_paused is False
    assert status.is_playing is True


async def test_transient_load_failure_skips_the_track_and_announces(monkeypatch):
    announcer = FakeAnnouncer()
    session = _make_session(announcer=announcer)
    _install_fakes(monkeypatch)
    monkeypatch.setattr(
        FakeSourceFactory, "failures", {"bad": RuntimeError("throttled")}
    )

    await session.play("bad,good")

    current = session.status.current_music
    assert current is not None
    assert current.title == "good"
    assert session.status.queue == ()
    assert announcer.messages == ["'bad' não pôde ser carregada e foi pulada: throttled"]


async def test_all_tracks_failing_transiently_stops_cleanly(monkeypatch):
    announcer = FakeAnnouncer()
    session = _make_session(announcer=announcer)
    _install_fakes(monkeypatch)
    monkeypatch.setattr(
        FakeSourceFactory, "failures", {"bad": RuntimeError("boom"), "good": RuntimeError("boom")}
    )

    await session.play("bad,good")

    assert session.status.current_music is None
    assert session.status.queue == ()
    assert len(announcer.messages) == 2


async def test_environment_failure_stops_playback_and_announces(monkeypatch):
    announcer = FakeAnnouncer()
    session = _make_session(announcer=announcer)
    _install_fakes(monkeypatch)
    monkeypatch.setattr(
        FakeSourceFactory,
        "failures",
        {"bad": ProbeEnvironmentError("ffmpeg missing")},
    )

    await session.play("bad,good")

    assert session.status.current_music is None
    assert [m.title for m in session.status.queue] == ["good"]
    assert len(announcer.messages) == 1
    assert "bad" in announcer.messages[0]
    assert "Parando" in announcer.messages[0]


async def test_queue_end_advances_to_the_next_track(monkeypatch):
    loop = asyncio.get_running_loop()
    session = _make_session(loop=loop)
    _install_fakes(monkeypatch)
    await session.play("one,two")
    first = session.status.current_music
    assert first is not None

    session._on_queue_end()
    await _pump()

    current = session.status.current_music
    assert current is not None
    assert current is not first
    assert current.title == "two"
    assert session.status.queue == ()


async def test_queue_end_with_an_empty_queue_stops_playback(monkeypatch):
    loop = asyncio.get_running_loop()
    session = _make_session(loop=loop)
    _install_fakes(monkeypatch)
    await session.play("one")

    session._on_queue_end()
    await _pump()

    assert session.status.current_music is None
    assert session.status.queue == ()


async def test_track_loop_reloads_the_current_track_on_queue_end(monkeypatch):
    loop = asyncio.get_running_loop()
    session = _make_session(loop=loop)
    _install_fakes(monkeypatch)
    await session.play("one")
    first_source = session._controller.get_queue_source()
    assert first_source is not None
    await session.set_loop(LoopMode.TRACK)

    session._on_queue_end()
    await _pump()

    current = session.status.current_music
    assert current is not None
    assert current.title == "one"
    assert session.status.queue == ()
    reloaded = session._controller.get_queue_source()
    assert reloaded is not None
    assert reloaded is not first_source


async def test_queue_loop_reappends_the_finished_track_on_queue_end(monkeypatch):
    loop = asyncio.get_running_loop()
    session = _make_session(loop=loop)
    _install_fakes(monkeypatch)
    await session.play("one,two")
    await session.set_loop(LoopMode.QUEUE)

    session._on_queue_end()
    await _pump()

    current = session.status.current_music
    assert current is not None
    assert current.title == "two"
    assert [m.title for m in session.status.queue] == ["one"]


async def test_skip_ignores_track_loop(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two")
    await session.set_loop(LoopMode.TRACK)

    await session.skip()

    current = session.status.current_music
    assert current is not None
    assert current.title == "two"


async def test_toggle_pause_pauses_and_resumes(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one")

    await session.toggle_pause()

    assert session.status.is_paused is True

    await session.toggle_pause()

    assert session.status.is_paused is False


async def test_remove_drops_a_waiting_track_from_the_queue(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two,three")

    removed = await session.remove("https://example.com/two")

    assert removed is True
    assert [m.title for m in session.status.queue] == ["three"]


async def test_remove_current_track_skips_to_the_next(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two,three")

    removed = await session.remove("https://example.com/one")

    assert removed is True
    current = session.status.current_music
    assert current is not None
    assert current.title == "two"
    assert [m.title for m in session.status.queue] == ["three"]


async def test_remove_unknown_track_is_a_noop(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two")

    removed = await session.remove("https://example.com/nope")

    assert removed is False
    assert [m.title for m in session.status.queue] == ["two"]


async def test_remove_on_an_empty_session_is_a_noop(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)

    removed = await session.remove("https://example.com/one")

    assert removed is False


async def test_move_reorders_the_waiting_tracks(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two,three,four")

    moved = await session.move("https://example.com/four", 0)

    assert moved is True
    assert [m.title for m in session.status.queue] == ["four", "two", "three"]


async def test_move_does_not_touch_the_current_track(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two,three")

    moved = await session.move("https://example.com/one", 2)

    assert moved is False
    current = session.status.current_music
    assert current is not None
    assert current.title == "one"
    assert [m.title for m in session.status.queue] == ["two", "three"]


async def test_move_unknown_track_is_a_noop(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two,three")

    moved = await session.move("https://example.com/nope", 1)

    assert moved is False
    assert [m.title for m in session.status.queue] == ["two", "three"]


async def test_move_clamps_position_to_the_end(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two,three")

    moved = await session.move("https://example.com/two", 99)

    assert moved is True
    assert [m.title for m in session.status.queue] == ["three", "two"]


async def test_clear_drops_every_waiting_track(monkeypatch):
    session = _make_session()
    _install_fakes(monkeypatch)
    await session.play("one,two,three")

    await session.clear_queue()

    assert session.status.current_music is not None
    assert session.status.queue == ()


async def test_status_carries_the_voice_channel_id():
    guild = FakeGuild(1)
    channel = FakeChannel(guild)
    voice_client = await channel.connect()
    session = PlaybackSession(guild_id=1, voice_client=voice_client)
    session.start()

    assert session.status.channel_id == channel.id
