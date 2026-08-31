"""Web-route tests for the music page.

These drive ``pages.music`` through Quart's test client with a fake bot,
asserting external behaviour: what the rendered HTML contains and which
session verb a POST action reaches.  They do not inspect route internals.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

# pi-lens-ignore: reportMissingImports
import pytest

from app import app as quart_app
from src import bot_state as deps
from src.harpi_lib.audio.session import LayerInfo, LoopMode, SessionStatus
from src.harpi_lib.harpi_bot import HarpiBot
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
        self.voice_channels = [
            FakeVoiceChannel(guild_id * 10, f"Channel {guild_id}")
        ]


class FakeSession:
    def __init__(self, status: SessionStatus | None = None) -> None:
        self._status = status
        self.calls: list[Any] = []

    async def sample_status(self) -> SessionStatus | None:
        return self._status

    async def toggle_pause(self) -> None:
        self.calls.append("toggle_pause")

    async def skip(self) -> None:
        self.calls.append("skip")

    async def stop(self) -> None:
        self.calls.append("stop")

    async def clear_queue(self) -> None:
        self.calls.append("clear_queue")

    async def remove(self, value: str) -> None:
        self.calls.append(("remove", value))

    async def clear_layers(self) -> None:
        self.calls.append("clear_layers")

    async def remove_layer(self, value: str) -> None:
        self.calls.append(("remove_layer", value))

    async def play(self, value: str) -> None:
        self.calls.append(("play", value))
        # The real session starts the added track when idle; the panel's
        # skipped-tracks warning keys off that, so the fake mirrors it.
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

    async def seek(self, value: float) -> None:
        self.calls.append(("seek", value))

    async def set_volume(self, value: float) -> None:
        self.calls.append(("set_volume", value))

    async def set_layer_volume(self, layer_id: str, value: float) -> None:
        self.calls.append(("set_layer_volume", layer_id, value))

    async def previous(self) -> None:
        self.calls.append("previous")


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

    def get_guild(self, guild_id: int) -> FakeGuild | None:
        return self._guilds.get(guild_id)

    async def fetch_guilds(self, limit: int | None = None):
        del limit
        for guild in self._guilds.values():
            yield guild


GUILD_C = 3


@pytest.fixture
def bot() -> FakeBot:
    return FakeBot([
        FakeGuild(GUILD_A, "Alpha Guild"),
        FakeGuild(GUILD_B, "Beta Guild"),
    ])


@pytest.fixture
def client(bot: FakeBot):
    os.environ["DISCORD_TOKEN"] = "test"
    os.environ["SECRET_KEY"] = "test-secret"
    quart_app.secret_key = "test-secret"
    quart_app.config["TESTING"] = True
    deps.init_bot(cast(HarpiBot, bot))
    yield quart_app.test_client()
    deps._bot_ref = None


async def test_full_page_renders_guilds_and_status(client, bot: FakeBot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )

    response = await client.get(f"/music?guild_id={GUILD_A}")

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Alpha Guild" in body
    assert "Beta Guild" in body
    assert "Now Track" in body
    assert "No active session." not in body


async def test_guild_list_reflects_bot_changes_between_requests(
    client, bot: FakeBot
):
    response = await client.get("/music")
    body = (await response.get_data()).decode()
    assert "Alpha Guild" in body
    assert "Beta Guild" in body

    # Bot joins a new guild and one disappears.
    bot._guilds.pop(GUILD_B)
    bot._guilds[GUILD_C] = FakeGuild(GUILD_C, "Gamma Guild")

    response = await client.get("/music")
    body = (await response.get_data()).decode()
    assert "Alpha Guild" in body
    assert "Gamma Guild" in body
    assert "Beta Guild" not in body


async def test_selector_branch_lists_guild_channels_and_persists_selection(
    client,
):
    response = await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Channel 1" in body
    assert "MUSIC CONTROL" not in body

    full = await client.get("/music")
    full_body = (await full.get_data()).decode()
    assert "Channel 1" in full_body


async def test_now_playing_branch_renders_status_block_only(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "now_playing"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Now Track" in body
    assert "MUSIC CONTROL" not in body


async def test_queue_branch_renders_queue_items(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            queue=(YTMusicData({"title": "Queued One", "url": "u1"}),),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    body = (await response.get_data()).decode()
    assert "Queued One" in body
    assert "MUSIC CONTROL" not in body


async def test_layers_branch_renders_layers(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            layers=(
                LayerInfo(id="l1", title="Layer One", url="u", volume=0.7),
            ),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "layers"},
    )

    body = (await response.get_data()).decode()
    assert "Layer One" in body
    assert "MUSIC CONTROL" not in body


async def test_status_panels_branch_renders_the_wrapped_panels(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 120,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "status_panels"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Now Track" in body
    assert "MUSIC CONTROL" not in body


async def test_transport_branch_renders_formatted_progress(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=True,
            is_paused=False,
            current_music=YTMusicData({
                "title": "Now Track",
                "uploader": "Artist",
                "duration": 754,
            }),
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=213.0,
        )
    )
    await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    response = await client.get(
        "/music",
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "3:33" in body
    assert "12:34" in body
    assert "0:03" not in body
    assert "MUSIC CONTROL" not in body


async def test_connect_action_dispatches_to_session_manager(client, bot):
    response = await client.post(
        "/music",
        form={"action": "connect", "guild_id": GUILD_A, "channel_id": 10},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert bot.sessions.connect_calls == [(GUILD_A, 10)]


async def test_disconnect_action_dispatches_to_session_manager(client, bot):
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "disconnect"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert bot.sessions.disconnect_calls == [GUILD_A]


@pytest.mark.parametrize(
    ("action", "value", "expected_call", "target"),
    [
        ("toggle_pause", None, "toggle_pause", "transport"),
        ("skip", None, "skip", "transport"),
        ("toggle_pause", None, "toggle_pause", ""),
        ("skip", None, "skip", ""),
        ("stop", None, "stop", ""),
        ("clear_queue", None, "clear_queue", ""),
        ("remove", "u1", ("remove", "u1"), ""),
        ("clear_layers", None, "clear_layers", ""),
        ("remove_layer", "l1", ("remove_layer", "l1"), ""),
        ("add", "search me", ("play", "search me"), ""),
    ],
)
async def test_action_posts_dispatch_to_session(
    client, bot, action: str, value: str | None, expected_call, target: str
):
    session = FakeSession()
    bot.sessions._session = session
    await client.get(f"/music?guild_id={GUILD_A}")

    data = {"action": action}
    if value is not None:
        data["value"] = value
    headers = {"HX-Request": "true"}
    if target:
        headers["HX-Target"] = target
    await client.post("/music", form=data, headers=headers)

    assert expected_call in session.calls


async def test_non_htmx_post_returns_full_page(client, bot):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post("/music", form={"action": "toggle_pause"})

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "MUSIC CONTROL" in body
    assert bot.sessions._session.calls == ["toggle_pause"]


class ExplodingSessionManager(FakeSessionManager):
    async def connect(self, guild_id: int, channel_id: int) -> None:
        raise ValueError("Canal de voz não encontrado")


class FailingPlaySession(FakeSession):
    async def play(self, value: str) -> None:
        raise ValueError("yt explodiu")


async def test_add_without_session_reports_error(client, bot):
    bot.sessions._session = None
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "add", "value": "warriors"},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Não conectado a um canal de voz" in body
    assert '<div id="panel_error" hx-swap-oob="true">' in body


async def test_add_with_failing_play_surfaces_the_error(client, bot):
    bot.sessions._session = FailingPlaySession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "add", "value": "warriors"},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "yt explodiu" in body
    assert '<div id="panel_error" hx-swap-oob="true">' in body


async def test_successful_add_leaves_the_error_region_empty(client, bot):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "add", "value": "warriors"},
        headers={"HX-Request": "true", "HX-Target": "queue"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert '<div id="panel_error" hx-swap-oob="true">' in body
    assert "panel-error" not in body


async def test_failed_connect_reports_error_and_keeps_no_cookie(client, bot):
    bot.sessions = ExplodingSessionManager()

    response = await client.post(
        "/music",
        form={"action": "connect", "guild_id": GUILD_A, "channel_id": 11},
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Canal de voz não encontrado" in body

    follow_up = await client.get("/music")
    follow_up_body = (await follow_up.get_data()).decode()
    assert "DISCONNECT" not in follow_up_body


async def test_selector_marks_the_connected_channel_selected(client, bot):
    bot.sessions._session = FakeSession(
        SessionStatus(
            guild_id=GUILD_A,
            connected=True,
            is_playing=False,
            is_paused=False,
            loop_mode=LoopMode.OFF,
            volume=0.7,
            progress=0.0,
            channel_id=10,
        )
    )

    response = await client.get(
        f"/music?guild_id={GUILD_A}",
        headers={"HX-Request": "true", "HX-Target": "selector"},
    )

    body = (await response.get_data()).decode()
    collapsed = " ".join(body.split())
    assert '<option value="10" selected >' in collapsed
    assert (
        "selected" not in collapsed.split('<option value="10" selected >')[1]
    )


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
async def test_seek_rejects_non_finite_values(client, bot, value: str):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "seek", "value": value},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Valor numérico inválido" in body


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
async def test_volume_rejects_non_finite_values(client, bot, value: str):
    bot.sessions._session = FakeSession()
    await client.get(f"/music?guild_id={GUILD_A}")

    response = await client.post(
        "/music",
        form={"action": "set_volume", "value": value},
        headers={"HX-Request": "true", "HX-Target": "transport"},
    )

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "Valor numérico inválido" in body
