from __future__ import annotations

from typing import Any, cast

import pytest

from src import bot_state as deps
from src.harpi_lib.audio.session import LayerInfo, LoopMode, SessionStatus
from src.panel import actions as panel_actions
from src.panel import serialization as panel_serialization
from src.panel import state as panel_state
from test_index_page import FakeBot as IndexFakeBot
from test_music_page import (
    GUILD_A,
    FakeBot,
    FakeGuild,
    FakeSession,
    FakeSessionManager,
    FailingPlaySession,
    found_track,
    patch_search,
    playing_status,
)


def bind(monkeypatch: pytest.MonkeyPatch, bot: Any) -> None:
    monkeypatch.setattr(deps, "_bot_ref", bot)


class RecordingSession(FakeSession):
    async def pause(self) -> None:
        self.calls.append("pause")

    async def resume(self) -> None:
        self.calls.append("resume")

    async def set_loop(self, mode: LoopMode) -> None:
        self.calls.append(("set_loop", mode))


class IdleSession(FakeSession):
    async def play(self, value: str) -> None:
        self.calls.append(("play", value))


class FailingLayerSession(FakeSession):
    async def add_layer(self, value: str) -> None:
        raise ValueError("layer explodiu")


class ExplodingGuildBot(FakeBot):
    def fetch_guilds(self, limit: int | None = None):
        raise ValueError("guild fetch falhou")


class ExplodingManager(FakeSessionManager):
    async def connect(self, guild_id: int, channel_id: int) -> None:
        raise ValueError("Canal de voz não encontrado")

    async def disconnect(self, guild_id: int) -> None:
        raise ValueError("Guilda não conectada")


@pytest.fixture
def bot(monkeypatch: pytest.MonkeyPatch) -> FakeBot:
    bot = FakeBot([
        FakeGuild(GUILD_A, "Alpha Guild"),
        FakeGuild(2, "Beta Guild"),
    ])
    bind(monkeypatch, bot)
    return bot


@pytest.fixture
def wired(bot: FakeBot) -> FakeBot:
    bot.sessions._session = RecordingSession(playing_status())
    return bot


def session_of(bot: FakeBot) -> RecordingSession:
    return cast(RecordingSession, bot.sessions._session)


def test_bot_connected_reports_ready_and_open(
    monkeypatch: pytest.MonkeyPatch,
):
    bind(monkeypatch, IndexFakeBot(ready=True, closed=False))
    assert panel_state.bot_connected() is True


def test_bot_connected_reports_closing(monkeypatch: pytest.MonkeyPatch):
    bind(monkeypatch, IndexFakeBot(ready=True, closed=True))
    assert panel_state.bot_connected() is False


async def test_list_guilds_returns_plain_records(bot: FakeBot):
    guilds = await panel_state.list_guilds()

    assert guilds == [
        {"id": GUILD_A, "name": "Alpha Guild"},
        {"id": 2, "name": "Beta Guild"},
    ]


async def test_list_guilds_propagates_a_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    bind(monkeypatch, ExplodingGuildBot([]))

    with pytest.raises(ValueError, match="guild fetch falhou"):
        await panel_state.list_guilds()


async def test_list_voice_channels_for_a_known_guild(bot: FakeBot):
    channels = panel_state.list_voice_channels(GUILD_A)

    assert channels == [{"id": GUILD_A * 10, "name": f"Channel {GUILD_A}"}]


async def test_list_voice_channels_for_an_unknown_guild(bot: FakeBot):
    assert panel_state.list_voice_channels(999) == []


async def test_guild_status_without_a_selection(bot: FakeBot):
    assert await panel_state.guild_status(None) is None


async def test_guild_status_without_a_session(bot: FakeBot):
    assert await panel_state.guild_status(GUILD_A) is None


async def test_guild_status_serializes_the_snapshot(wired: FakeBot):
    status = await panel_state.guild_status(GUILD_A)

    assert status is not None
    assert status["loop_mode"] == "OFF"
    assert status["current_music"]["title"] == "Now Track"
    assert status["queue"] == []


def test_status_data_serializes_layers_and_loop_mode():
    status = SessionStatus(
        guild_id=GUILD_A,
        connected=True,
        is_playing=False,
        is_paused=False,
        layers=(
            LayerInfo(
                id="l1",
                title="Layer One",
                url="u",
                volume=0.7,
                thumbnail="t",
            ),
        ),
        loop_mode=LoopMode.QUEUE,
        volume=0.5,
        progress=1.0,
        channel_id=10,
    )

    data = panel_serialization.status_data(status)

    assert data["loop_mode"] == "QUEUE"
    assert data["current_music"] is None
    assert data["layers"] == [
        {
            "id": "l1",
            "title": "Layer One",
            "url": "u",
            "volume": 0.7,
            "thumbnail": "t",
        }
    ]


def test_track_data_carries_the_template_keys():
    data = panel_serialization.track_data(found_track())

    assert data == {
        "title": "Found Track",
        "url": "https://www.youtube.com/watch?v=found",
        "uploader": "Artist",
        "duration": 30,
        "thumbnail": "https://img.example.com/found.jpg",
    }


async def test_connect_records_the_channel(bot: FakeBot):
    await panel_actions.connect(GUILD_A, 10)

    assert bot.sessions.connect_calls == [(GUILD_A, 10)]


async def test_connect_propagates_a_manager_failure(bot: FakeBot):
    bot.sessions = ExplodingManager()

    with pytest.raises(ValueError, match="Canal de voz não encontrado"):
        await panel_actions.connect(GUILD_A, 10)


async def test_disconnect_records_the_guild(bot: FakeBot):
    await panel_actions.disconnect(GUILD_A)

    assert bot.sessions.disconnect_calls == [GUILD_A]


async def test_disconnect_propagates_a_manager_failure(bot: FakeBot):
    bot.sessions = ExplodingManager()

    with pytest.raises(ValueError, match="Guilda não conectada"):
        await panel_actions.disconnect(GUILD_A)


async def test_search_returns_plain_track_records(monkeypatch):
    patch_search(monkeypatch, [found_track()])

    results = await panel_actions.search("found track")

    assert results == [
        {
            "title": "Found Track",
            "url": "https://www.youtube.com/watch?v=found",
            "uploader": "Artist",
            "duration": 30,
            "thumbnail": "https://img.example.com/found.jpg",
        }
    ]


async def test_search_ignores_an_empty_term():
    assert await panel_actions.search("   ") == []


async def test_search_raises_when_nothing_is_found(monkeypatch):
    patch_search(monkeypatch, [])

    with pytest.raises(ValueError, match="Nenhuma música encontrada"):
        await panel_actions.search("nothing")


async def test_require_session_passes_with_a_connected_session(wired: FakeBot):
    panel_actions.require_session(GUILD_A)


async def test_require_session_raises_without_a_connected_session(
    bot: FakeBot,
):
    with pytest.raises(ValueError, match="Não conectado"):
        panel_actions.require_session(GUILD_A)


NO_ARGUMENT_VERBS = [
    panel_actions.clear_queue,
    panel_actions.stop,
    panel_actions.clear_layers,
    panel_actions.toggle_pause,
    panel_actions.pause,
    panel_actions.resume,
    panel_actions.skip,
    panel_actions.previous,
]


@pytest.mark.parametrize("verb", NO_ARGUMENT_VERBS, ids=lambda f: f.__name__)
async def test_no_argument_verbs_reach_the_session(wired: FakeBot, verb):
    await verb(GUILD_A)

    assert verb.__name__ in session_of(wired).calls


@pytest.mark.parametrize("verb", NO_ARGUMENT_VERBS, ids=lambda f: f.__name__)
async def test_no_argument_verbs_fail_without_a_session(bot: FakeBot, verb):
    with pytest.raises(ValueError, match="Não conectado"):
        await verb(GUILD_A)


async def test_set_loop_maps_an_alias(wired: FakeBot):
    await panel_actions.set_loop(GUILD_A, "fila")

    assert session_of(wired).calls == [("set_loop", LoopMode.QUEUE)]


async def test_set_loop_ignores_an_empty_mode(wired: FakeBot):
    await panel_actions.set_loop(GUILD_A, None)

    assert session_of(wired).calls == []


async def test_set_loop_rejects_an_unknown_mode(wired: FakeBot):
    with pytest.raises(ValueError, match="Modo de loop inválido"):
        await panel_actions.set_loop(GUILD_A, "sideways")


async def test_set_loop_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.set_loop(GUILD_A, "off")


async def test_add_track_plays_the_link(wired: FakeBot):
    warning = await panel_actions.add_track(GUILD_A, "warriors")

    assert warning is None
    assert ("play", "warriors") in session_of(wired).calls


async def test_add_track_warns_when_everything_was_skipped(bot: FakeBot):
    bot.sessions._session = IdleSession(
        playing_status(current_music=None, queue=())
    )

    warning = await panel_actions.add_track(GUILD_A, "warriors")

    assert warning is not None
    assert "nenhuma pôde ser tocada" in warning


async def test_add_track_propagates_a_play_failure(bot: FakeBot):
    bot.sessions._session = FailingPlaySession()

    with pytest.raises(ValueError, match="yt explodiu"):
        await panel_actions.add_track(GUILD_A, "warriors")


async def test_add_track_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.add_track(GUILD_A, "warriors")


async def test_add_layer_reaches_the_session(wired: FakeBot):
    await panel_actions.add_layer(GUILD_A, "warriors")

    assert ("add_layer", "warriors") in session_of(wired).calls


async def test_add_layer_propagates_a_failure(bot: FakeBot):
    bot.sessions._session = FailingLayerSession()

    with pytest.raises(ValueError, match="layer explodiu"):
        await panel_actions.add_layer(GUILD_A, "warriors")


async def test_add_layer_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.add_layer(GUILD_A, "warriors")


async def test_remove_track_reaches_the_session(wired: FakeBot):
    await panel_actions.remove_track(GUILD_A, "u1")

    assert ("remove", "u1") in session_of(wired).calls


async def test_remove_track_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.remove_track(GUILD_A, "u1")


async def test_remove_layer_reaches_the_session(wired: FakeBot):
    await panel_actions.remove_layer(GUILD_A, "l1")

    assert ("remove_layer", "l1") in session_of(wired).calls


async def test_remove_layer_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.remove_layer(GUILD_A, "l1")


async def test_set_volume_reaches_the_session(wired: FakeBot):
    await panel_actions.set_volume(GUILD_A, 0.8)

    assert ("set_volume", 0.8) in session_of(wired).calls


async def test_set_volume_ignores_none(wired: FakeBot):
    await panel_actions.set_volume(GUILD_A, None)

    assert session_of(wired).calls == []


async def test_set_volume_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.set_volume(GUILD_A, 0.8)


async def test_set_layer_volume_reaches_the_session(wired: FakeBot):
    await panel_actions.set_layer_volume(GUILD_A, "l1", 0.5)

    assert ("set_layer_volume", "l1", 0.5) in session_of(wired).calls


async def test_set_layer_volume_ignores_none(wired: FakeBot):
    await panel_actions.set_layer_volume(GUILD_A, "l1", None)

    assert session_of(wired).calls == []


async def test_set_layer_volume_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.set_layer_volume(GUILD_A, "l1", 0.5)


async def test_seek_reaches_the_session(wired: FakeBot):
    await panel_actions.seek(GUILD_A, 30.0)

    assert ("seek", 30.0, True) in session_of(wired).calls


async def test_seek_ignores_none(wired: FakeBot):
    await panel_actions.seek(GUILD_A, None)

    assert session_of(wired).calls == []


async def test_seek_rejects_a_target_past_the_duration(wired: FakeBot):
    with pytest.raises(ValueError, match="Posição fora"):
        await panel_actions.seek(GUILD_A, 999.0)

    assert session_of(wired).calls == []


async def test_seek_fails_without_a_session(bot: FakeBot):
    with pytest.raises(ValueError, match="Não conectado"):
        await panel_actions.seek(GUILD_A, 30.0)
