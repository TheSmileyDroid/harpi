"""Lifecycle tests for PlaybackSession.

The session is the primary seam under test: it owns the voice client, the
controller, and the mixer, and wires the mixer's end-of-track observers to
its own handlers so no outside service needs to.  These tests exercise the
verbs the cogs and routes will call and the wiring the session owns.
"""

from src.harpi_lib.audio.session import PlaybackSession, SessionStatus
from tests.conftest import FakeSource, FakeVoiceClient


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
