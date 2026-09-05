"""Integration tests: panel route → run_on_bot_loop → real PlaybackSession.

Unlike ``test_music_page.py`` (which stops at a FakeSession recording verb
calls), these tests run the whole stack offline: the real ``SessionManager``
connects a ``FakeVoiceClient`` through a ``FakeChannel``, the real
``PlaybackSession`` queues and plays through the real mixer/controller, and
only the yt-dlp seam is faked.  A regression in the route-to-session wiring
or in the session verbs the panel calls shows up here.
"""

from __future__ import annotations

import asyncio
import json
import os
from types import SimpleNamespace
from typing import Any, ClassVar, cast

# pi-lens-ignore: reportMissingImports
import pytest

from app import app as quart_app
from src import bot_state as deps
from src.bot_state import run_on_bot_loop
from pages import music as guild_module
import src.harpi_lib.audio.session as session_module
from src.harpi_lib.audio.session import LoopMode, PlaybackSession
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


class PanelGuild(FakeGuild):
    """A FakeGuild that also exposes ``voice_channels`` for the panel."""

    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)
        channel = FakeChannel(self)
        self._channels[channel.id] = channel
        self.voice_channels = [channel]


class PanelBot:
    """Minimal bot duck-type: enough for SessionManager and the panel."""

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


class StageSourceFactory:
    """Fake YoutubeDLSource seam whose loads fail when told to.

    Serves the same source kind for queue tracks and layers, so one patch
    covers both panel flows.
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
    """A panel bot whose yt-dlp seam is faked in session and panel."""
    monkeypatch.setattr(session_module, "YTMusicData", FakeMusicDataFactory)
    monkeypatch.setattr(session_module, "YoutubeDLSource", StageSourceFactory)
    monkeypatch.setattr(guild_module, "YTMusicData", FakeMusicDataFactory)
    return PanelBot(PanelGuild(GUILD_ID))


@pytest.fixture
def client(bot: PanelBot):
    os.environ["DISCORD_TOKEN"] = "test"
    os.environ["SECRET_KEY"] = "test-secret"
    quart_app.secret_key = "test-secret"
    quart_app.config["TESTING"] = True
    deps.init_bot(cast(Any, bot))
    yield quart_app.test_client()
    deps._bot_ref = None


async def _connect(client) -> PanelBot:
    """Drive the panel's connect action and return the wired bot."""
    await client.get(f"/music?guild_id={GUILD_ID}")
    response = await client.post(
        "/music",
        form={
            "action": "connect",
            "guild_id": GUILD_ID,
            "channel_id": CHANNEL_ID,
        },
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )
    assert response.status_code == 200
    return cast(PanelBot, deps.get_bot())


def _session(bot: PanelBot) -> PlaybackSession:
    connected = bot.sessions.get(GUILD_ID)
    assert connected is not None
    return connected


async def _status(bot: PanelBot):
    return await _session(bot).sample_status()


async def _post(client, action: str, target: str, **fields: str):
    form = {"action": action, **fields}
    return await client.post(
        "/music",
        form=form,
        headers={"HX-Request": "true", "HX-Target": target},
    )


async def test_connect_through_the_panel_starts_a_real_session(
    client, bot: PanelBot
):
    await _connect(client)

    session_obj = _session(bot)
    assert isinstance(session_obj, PlaybackSession)
    status = await session_obj.sample_status()
    assert status.connected is True
    assert status.channel_id == CHANNEL_ID


async def test_panel_add_searches_and_starts_playing(client, bot: PanelBot):
    await _connect(client)

    response = await _post(client, "add", "queue", value=SEARCH_TERM)

    assert response.status_code == 200
    status = await _status(bot)
    assert status.current_music is not None
    assert status.current_music.title == SEARCH_TERM
    assert status.queue == ()


async def test_panel_add_while_playing_extends_the_queue(
    client, bot: PanelBot
):
    await _connect(client)
    await _post(client, "add", "queue", value="first")

    response = await _post(client, "add", "queue", value="second")

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "second" in body
    status = await _status(bot)
    assert status.current_music is not None
    assert status.current_music.title == "first"
    assert [track.title for track in status.queue] == ["second"]


async def test_search_renders_results_with_queue_and_layer_actions(
    client,
):
    await client.get(f"/music?guild_id={GUILD_ID}")

    response = await _post(
        client, "search", "search_dropdown", value="warriors, imagine"
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "warriors" in body
    assert "imagine" in body
    assert "QUEUE" in body
    assert "LAYER" in body
    assert 'name="action" value="add_layer"' in body


async def test_search_result_joins_the_queue_through_the_panel(
    client, bot: PanelBot
):
    await _connect(client)
    await _post(client, "search", "search", value=SEARCH_TERM)
    result_url = f"https://example.com/{SEARCH_TERM}"

    add_response = await _post(client, "add", "queue", value=result_url)

    assert add_response.status_code == 200
    status = await _status(bot)
    assert status.current_music is not None
    # The fake names each result after its input, so this proves the URL
    # the search result advertised is what reached session.play.
    assert status.current_music.title == result_url


async def test_search_result_becomes_a_background_layer(client, bot: PanelBot):
    await _connect(client)

    response = await _post(client, "add_layer", "layers", value=SEARCH_TERM)

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert SEARCH_TERM in body
    status = await _status(bot)
    assert [layer.title for layer in status.layers] == [SEARCH_TERM]


async def test_layer_volume_reaches_the_session(client, bot: PanelBot):
    await _connect(client)
    await _post(client, "add_layer", "layers", value=SEARCH_TERM)
    layer_id = (await _status(bot)).layers[0].id

    response = await _post(
        client,
        "set_layer_volume",
        "layers",
        layer_id=layer_id,
        value="1.5",
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "1.5" in body
    status = await _status(bot)
    assert status.layers[0].volume == pytest.approx(1.5)


async def test_skip_then_previous_replays_the_finished_track(
    client, bot: PanelBot
):
    await _connect(client)
    await _post(client, "add", "queue", value="first")
    await _post(client, "add", "queue", value="second")
    await _post(client, "skip", "transport")
    status = await _status(bot)
    assert status.current_music is not None
    assert status.current_music.title == "second"

    response = await _post(client, "previous", "transport")

    assert response.status_code == 200
    status = await _status(bot)
    assert status.current_music is not None
    assert status.current_music.title == "first"
    # "second" already finished, so it went to history, not back to the queue.
    assert status.queue == ()


async def test_previous_with_no_history_leaves_the_session_idle(
    client, bot: PanelBot
):
    await _connect(client)

    response = await _post(client, "previous", "transport")

    assert response.status_code == 200
    status = await _status(bot)
    assert status.current_music is None


async def test_volume_and_loop_reach_the_session(client, bot: PanelBot):
    await _connect(client)

    await _post(client, "set_volume", "transport", value="1.5")
    response = await _post(client, "set_loop", "transport", value="track")

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "LOOP TRACK" in body
    status = await _status(bot)
    assert status.volume == pytest.approx(1.5)
    assert status.loop_mode is LoopMode.TRACK


async def test_seek_reaches_the_current_source(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await _connect(client)
    await _post(client, "add", "queue", value=SEARCH_TERM)
    source = _session(bot)._controller.get_queue_source()
    assert source is not None

    response = await _post(client, "seek", "transport", value="30")

    assert response.status_code == 200
    assert cast(Any, source).seek_calls == [30.0]


async def test_session_seek_clamps_to_the_track_duration(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    # The panel rejects targets outside 0..duration; the shared session
    # backend still clamps whatever reaches it (the Discord command relies
    # on that).
    monkeypatch.setattr(session_module, "YoutubeDLSource", SeekSourceFactory)
    await _connect(client)
    await _post(client, "add", "queue", value=SEARCH_TERM)
    session_obj = _session(bot)
    source = session_obj._controller.get_queue_source()
    assert source is not None

    await run_on_bot_loop(session_obj.seek(10000, absolute=True))

    assert cast(Any, source).seek_calls == [180.0]


async def test_add_that_skips_every_track_warns_the_panel(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    await _connect(client)
    monkeypatch.setattr(
        StageSourceFactory,
        "failures",
        {SEARCH_TERM: ValueError("probe reprovou o stream")},
    )

    response = await _post(client, "add", "queue", value=SEARCH_TERM)

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "nenhuma pôde ser tocada" in body
    assert '<div id="panel_error" hx-swap-oob="true">' in body
    status = await _status(bot)
    assert status.current_music is None
    assert status.queue == ()


async def test_successful_add_does_not_warn(client, bot: PanelBot):
    """When playback genuinely starts, no skipped-tracks warning fires."""
    await _connect(client)

    response = await _post(client, "add", "queue", value=SEARCH_TERM)

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "nenhuma pôde ser tocada" not in body
    status = await _status(bot)
    assert status.current_music is not None


async def test_successful_add_declares_the_toast_event(client, bot: PanelBot):
    await _connect(client)

    response = await _post(client, "add", "queue", value=SEARCH_TERM)

    payload = json.loads(response.headers["HX-Trigger"])
    assert payload == {"harpi:toast": {"message": "Adicionado à fila"}}


async def test_all_skipped_add_declares_no_toast_event(
    client, monkeypatch: pytest.MonkeyPatch, bot: PanelBot
):
    # The warning speaks for itself in the persistent error region; an
    # amber "queued" toast on top of it would confirm a broken action.
    await _connect(client)
    monkeypatch.setattr(
        StageSourceFactory,
        "failures",
        {SEARCH_TERM: ValueError("probe reprovou o stream")},
    )

    response = await _post(client, "add", "queue", value=SEARCH_TERM)

    assert "nenhuma pôde ser tocada" in (await response.get_data()).decode()
    assert "HX-Trigger" not in response.headers


async def test_full_page_after_connect_lists_the_new_controls(
    client, bot: PanelBot
):
    await _connect(client)

    response = await client.get(f"/music?guild_id={GUILD_ID}")

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "02 // QUEUE" in body
    assert "Search YouTube or paste a URL" in body
    assert "Prev" in body
    assert "LOOP OFF" in body
