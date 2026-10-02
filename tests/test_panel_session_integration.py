"""Integration tests: JSON API → run_on_bot_loop → real PlaybackSession.

These run the whole stack offline: the real ``SessionManager`` connects a
``FakeVoiceClient`` through a ``FakeChannel``, the real ``PlaybackSession``
queues and plays through the real mixer/controller, and only the yt-dlp seam
is faked.  A regression in the endpoint-to-session wiring or in the session
verbs the API calls shows up here.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any, ClassVar, cast

# pi-lens-ignore: reportMissingImports
import pytest

from app import app as quart_app
from src import bot_state as deps
from src.bot_state import run_on_bot_loop
import src.harpi_lib.audio.session as session_module
from src.harpi_lib.audio.session import MAX_VOLUME, LoopMode, PlaybackSession
from src.harpi_lib.audio.session_manager import SessionManager
from src.harpi_lib.music.ytmusic import YTMusicData
from tests.conftest import (
    FakeChannel,
    FakeGuild,
    FakeLayerSource,
    FakeMusicDataFactory,
)
from tests.test_session import SeekSourceFactory

GUILD_ID = 1
CHANNEL_ID = 42
SEARCH_TERM = "warriors"
PANEL_TOKEN = "test-panel-token"


class PanelGuild(FakeGuild):
    """A FakeGuild that also exposes ``voice_channels`` for the API."""

    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)
        channel = FakeChannel(self)
        self._channels[channel.id] = channel
        self.voice_channels = [channel]


class PanelBot:
    """Minimal bot duck-type: enough for SessionManager and the API."""

    def __init__(self, guild: PanelGuild) -> None:
        self.user = SimpleNamespace(id=1234)
        self._guild = guild
        self.sessions = SessionManager(cast(Any, self))

    @property
    def loop(self):
        return asyncio.get_running_loop()

    def get_guild(self, guild_id: int) -> PanelGuild | None:
        return self._guild if guild_id == self._guild.id else None

    async def fetch_guilds(self, limit: int | None = None):
        del limit
        yield self._guild

    def is_ready(self) -> bool:
        return True

    def is_closed(self) -> bool:
        return False


class StageSourceFactory:
    """Fake YoutubeDLSource seam whose loads fail when told to.

    Serves the same source kind for queue tracks and layers, so one patch
    covers both API flows.
    """

    failures: ClassVar[dict[str, Exception]] = {}

    @classmethod
    async def from_music_data(
        cls, music_data: YTMusicData, volume: float = 0.3
    ) -> FakeLayerSource:
        failure = cls.failures.get(music_data.title)
        if failure is not None:
            raise failure
        return FakeLayerSource(
            title=music_data.title,
            url=music_data.url,
            volume=volume,
        )


@pytest.fixture
def bot(monkeypatch: pytest.MonkeyPatch) -> PanelBot:
    """A panel bot whose yt-dlp seam is faked in the session and the API."""
    monkeypatch.setenv("PANEL_TOKEN", PANEL_TOKEN)
    monkeypatch.setattr(session_module, "YTMusicData", FakeMusicDataFactory)
    monkeypatch.setattr(session_module, "YoutubeDLSource", StageSourceFactory)
    monkeypatch.setattr(
        YTMusicData,
        "from_url",
        staticmethod(FakeMusicDataFactory.from_url),
    )
    return PanelBot(PanelGuild(GUILD_ID))


@pytest.fixture
def client(bot: PanelBot, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    quart_app.secret_key = "test-secret"
    quart_app.config["TESTING"] = True
    deps.init_bot(cast(Any, bot))
    yield quart_app.test_client()
    deps._bot_ref = None


async def _login(client):
    response = await client.post("/api/session", json={"token": PANEL_TOKEN})
    assert response.status_code == 200


async def _connect(client) -> PanelBot:
    """Drive the API connect action and return the wired bot."""
    response = await client.post(
        "/api/connect",
        json={"guild_id": GUILD_ID, "channel_id": CHANNEL_ID},
    )
    assert response.status_code == 200
    return cast(PanelBot, deps.get_bot())


def _session(bot: PanelBot) -> PlaybackSession:
    connected = bot.sessions.get(GUILD_ID)
    assert connected is not None
    return connected


async def _status(bot: PanelBot):
    return await _session(bot).sample_status()


async def _post(
    client, path: str, **payload: Any
) -> tuple[int, dict[str, Any]]:
    response = await client.post(path, json=payload)
    body = json.loads(await response.get_data())
    return response.status_code, body


async def test_connect_through_the_api_starts_a_real_session(
    client, bot: PanelBot
):
    await _login(client)

    _, body = await _post(
        client,
        "/api/connect",
        guild_id=GUILD_ID,
        channel_id=CHANNEL_ID,
    )

    session_obj = _session(bot)
    assert isinstance(session_obj, PlaybackSession)
    assert body["connection"] == {
        "connected": True,
        "channel_id": CHANNEL_ID,
    }


async def test_api_add_searches_and_starts_playing(client, bot: PanelBot):
    await _login(client)
    await _connect(client)

    status_code, body = await _post(client, "/api/queue", url=SEARCH_TERM)

    assert status_code == 200
    assert body["playback"]["current_music"]["title"] == SEARCH_TERM
    assert body["playback"]["queue"] == []


async def test_api_add_while_playing_extends_the_queue(client, bot: PanelBot):
    await _login(client)
    await _connect(client)
    await _post(client, "/api/queue", url="first")

    _, body = await _post(client, "/api/queue", url="second")

    assert body["playback"]["current_music"]["title"] == "first"
    assert [track["title"] for track in body["playback"]["queue"]] == [
        "second"
    ]


async def test_search_returns_results_for_queue_and_layer_actions(client):
    await _login(client)

    _, body = await _post(client, "/api/search", term="warriors, imagine")

    titles = [track["title"] for track in body["results"]]
    assert "warriors" in titles
    assert "imagine" in titles


async def test_api_add_layer_reaches_the_session(client, bot: PanelBot):
    await _login(client)
    await _connect(client)

    _, body = await _post(client, "/api/layers", url=SEARCH_TERM)

    assert [layer["title"] for layer in body["playback"]["layers"]] == [
        SEARCH_TERM
    ]


async def test_layer_volume_clamps_at_the_session_boundary(
    client, bot: PanelBot
):
    await _login(client)
    await _connect(client)
    _, added = await _post(client, "/api/layers", url=SEARCH_TERM)
    layer_id = added["playback"]["layers"][0]["id"]

    _, body = await _post(
        client, "/api/layers/volume", layer_id=layer_id, volume=1.5
    )

    assert body["playback"]["layers"][0]["volume"] == pytest.approx(MAX_VOLUME)


async def test_skip_then_previous_replays_the_finished_track(
    client, bot: PanelBot
):
    await _login(client)
    await _connect(client)
    await _post(client, "/api/queue", url="first")
    await _post(client, "/api/queue", url="second")
    _, skipped = await _post(client, "/api/playback/skip")
    assert skipped["playback"]["current_music"]["title"] == "second"

    _, body = await _post(client, "/api/playback/previous")

    assert body["playback"]["current_music"]["title"] == "first"
    assert body["playback"]["queue"] == []


async def test_previous_with_no_history_leaves_the_session_idle(
    client, bot: PanelBot
):
    await _login(client)
    await _connect(client)

    _, body = await _post(client, "/api/playback/previous")

    assert body["playback"]["current_music"] is None


async def test_volume_and_loop_reach_the_session(client, bot: PanelBot):
    await _login(client)
    await _connect(client)

    await _post(client, "/api/playback/volume", volume=0.8)
    _, body = await _post(client, "/api/playback/loop", mode="track")

    status = await _status(bot)
    assert status is not None
    assert status.volume == pytest.approx(0.8)
    assert status.loop_mode is LoopMode.TRACK
    assert body["playback"]["loop_mode"] == "TRACK"


async def test_seek_reaches_the_current_source(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await _login(client)
    await _connect(client)
    await _post(client, "/api/queue", url=SEARCH_TERM)
    source = _session(bot)._controller.get_queue_source()
    assert source is not None

    status_code, _ = await _post(client, "/api/playback/seek", position=30)

    assert status_code == 200
    assert cast(Any, source).seek_calls == [30.0]


async def test_seek_past_the_duration_is_rejected(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await _login(client)
    await _connect(client)
    await _post(client, "/api/queue", url=SEARCH_TERM)
    source = _session(bot)._controller.get_queue_source()
    assert source is not None

    status_code, body = await _post(
        client, "/api/playback/seek", position=10000
    )

    assert status_code == 404
    assert body["error"]["code"] == "not_found"
    assert cast(Any, source).seek_calls == []


async def test_session_seek_clamps_to_the_track_duration(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await _login(client)
    await _connect(client)
    await _post(client, "/api/queue", url=SEARCH_TERM)
    session_obj = _session(bot)
    source = session_obj._controller.get_queue_source()
    assert source is not None

    await run_on_bot_loop(session_obj.seek(10000, absolute=True))

    assert cast(Any, source).seek_calls == [180.0]


async def test_add_that_skips_every_track_answers_an_empty_session(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    await _login(client)
    await _connect(client)
    monkeypatch.setattr(
        StageSourceFactory,
        "failures",
        {SEARCH_TERM: ValueError("probe reprovou o stream")},
    )

    status_code, body = await _post(client, "/api/queue", url=SEARCH_TERM)

    assert status_code == 200
    assert body["playback"]["current_music"] is None
    assert body["playback"]["queue"] == []
