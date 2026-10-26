"""Contract tests for the JSON API.

These drive the app at its HTTP seam: session exchange and rejection, the
status payload, the machine-readable error envelope, and a real read of
the SSE stream against a running server.
"""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
import uvicorn

from app import app as quart_app
from src import bot_state as deps
from src.harpi_lib.audio.session import LayerInfo, LoopMode
from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.music.ytmusic import YTMusicData
from src.panel import state
from src.storage import clear_registry, init_registry
from src.storage.database import Database
from src.storage.registry import Actor, SqliteRegistry
from tests.fakes import (
    GUILD_A,
    GUILD_B,
    FakeBot,
    FakeGuild,
    FakeSession,
    found_track,
    patch_search,
    playing_status,
)

SECRET = "test-secret"
CHANNEL_ID = 42
SNOWFLAKE = 734174030701264912


class ApiBot(FakeBot):
    """The panel fakes plus the readiness calls server truth needs."""

    def __init__(
        self,
        guilds: list[FakeGuild],
        session: FakeSession | None = None,
        ready: bool = True,
        closed: bool = False,
    ) -> None:
        super().__init__(guilds, session)
        self._ready = ready
        self._closed = closed

    def is_ready(self) -> bool:
        return self._ready and not self._closed

    def is_closed(self) -> bool:
        return self._closed


class ApiSession(FakeSession):
    """The panel fake plus the transport verbs the JSON API dispatches to."""

    async def pause(self) -> None:
        self.calls.append("pause")
        if self._status is not None:
            self._status = replace(self._status, is_paused=True)

    async def resume(self) -> None:
        self.calls.append("resume")
        if self._status is not None:
            self._status = replace(self._status, is_paused=False)

    async def set_loop(self, loop_mode) -> None:
        self.calls.append(("set_loop", loop_mode))
        if self._status is not None:
            self._status = replace(self._status, loop_mode=loop_mode)

    async def seek(self, value: float, absolute: bool = False) -> None:
        self.calls.append(("seek", value, absolute))
        if self._status is not None and absolute:
            self._status = replace(self._status, progress=value)

    async def set_volume(self, value: float) -> None:
        self.calls.append(("set_volume", value))
        if self._status is not None:
            self._status = replace(
                self._status, volume=max(0.0, min(1.0, value))
            )

    async def add_layer(self, value: str) -> str:  # ty: ignore[invalid-method-override]
        self.calls.append(("add_layer", value))
        assert self._status is not None
        layer_id = f"layer-{len(self._status.layers) + 1}"
        layer = LayerInfo(id=layer_id, title=value, url=value, volume=0.5)
        self._status = replace(
            self._status, layers=(*self._status.layers, layer)
        )
        return layer_id

    async def remove_layer(self, value: str) -> bool:  # ty: ignore[invalid-method-override]
        self.calls.append(("remove_layer", value))
        if self._status is None:
            return False
        kept = tuple(
            layer for layer in self._status.layers if layer.id != value
        )
        if len(kept) == len(self._status.layers):
            return False
        self._status = replace(self._status, layers=kept)
        return True

    async def set_layer_volume(self, layer_id: str, value: float) -> bool:  # ty: ignore[invalid-method-override]
        self.calls.append(("set_layer_volume", layer_id, value))
        if self._status is None:
            return False
        found = False
        layers = []
        for layer in self._status.layers:
            if layer.id == layer_id:
                found = True
                layers.append(replace(layer, volume=max(0.0, min(1.0, value))))
            else:
                layers.append(layer)
        if not found:
            return False
        self._status = replace(self._status, layers=tuple(layers))
        return True


@pytest.fixture
def bot() -> ApiBot:
    return ApiBot(
        [FakeGuild(GUILD_A, "Alpha Guild")],
        ApiSession(playing_status(channel_id=CHANNEL_ID)),
    )


@pytest.fixture
def client(bot: ApiBot, storage, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    quart_app.secret_key = SECRET
    quart_app.config["TESTING"] = True
    deps.init_bot(cast(HarpiBot, bot))
    yield quart_app.test_client()
    deps._bot_ref = None


@pytest.fixture
async def storage(tmp_path):
    database = Database(tmp_path / "panel.db")
    await database.open()
    registry = SqliteRegistry(database)
    init_registry(registry)
    yield registry
    clear_registry()
    await database.close()


async def _login(
    client, guild_ids: Iterable[int] | None = None, user_id: str = "555"
):
    async with client.session_transaction() as stored:
        stored["authenticated"] = True
        stored["user_id"] = user_id
        stored["username"] = "panel-user"
    allowed = (
        frozenset(guild.id for guild in deps.get_bot().guilds)
        if guild_ids is None
        else frozenset(guild_ids)
    )
    await state.record_user_guilds(
        Actor(id=user_id, username="panel-user"), allowed
    )


async def _second_actor(guild_ids: Iterable[int]):
    other = quart_app.test_client()
    await _login(other, guild_ids, user_id="777")
    return other


async def _refresh_current_music(bot: ApiBot, title: str) -> None:
    bot.sessions._session = FakeSession(
        playing_status(
            channel_id=CHANNEL_ID,
            current_music=YTMusicData({
                "title": title,
                "url": f"https://example.com/{title}",
                "duration": 60,
            }),
        )
    )


@asynccontextmanager
async def _running_app(app) -> AsyncGenerator[int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        yield port
    finally:
        server.should_exit = True
        await task
        sock.close()


async def _read_status_frame(http: httpx.AsyncClient) -> dict[str, Any]:
    async with http.stream("GET", "/api/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = response.aiter_lines()
        assert await anext(lines) == ": connected"
        assert await anext(lines) == ""
        assert await anext(lines) == "event: status"
        data = await anext(lines)
        assert data.startswith("data: ")
        return json.loads(data.removeprefix("data: "))


async def _read_presence_frame(http: httpx.AsyncClient) -> dict[str, Any]:
    async with http.stream("GET", "/api/events") as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        while True:
            line = await anext(lines)
            if line == "event: presence":
                data = await anext(lines)
                return json.loads(data.removeprefix("data: "))


async def _read_directory_frame(http: httpx.AsyncClient) -> dict[str, Any]:
    async with http.stream("GET", "/api/events") as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        while True:
            line = await anext(lines)
            if line == "event: directory":
                data = await anext(lines)
                return json.loads(data.removeprefix("data: "))


async def test_session_probe_rejects_an_anonymous_call(client):
    response = await client.get("/api/session")

    assert response.status_code == 401


@pytest.mark.parametrize(
    "path",
    ["/api", "/api/session", "/api/status", "/api/events", "/api/guilds"],
)
async def test_guarded_endpoints_reject_anonymous_calls(client, path: str):
    response = await client.get(path)

    assert response.status_code == 401
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "unauthorized"


@pytest.mark.parametrize("path", ["/api/connect", "/api/disconnect"])
async def test_guarded_mutations_reject_anonymous_calls(client, path: str):
    response = await client.post(path, json={})

    assert response.status_code == 401
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "unauthorized"


async def test_selection_rejects_anonymous_calls(client):
    response = await client.post("/api/selection", json={})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "path",
    ["/api/search", "/api/queue", "/api/queue/remove", "/api/queue/clear"],
)
async def test_search_and_queue_paths_reject_anonymous_calls(
    client, path: str
):
    response = await client.post(path, json={})

    assert response.status_code == 401
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "unauthorized"


async def test_session_check_reports_a_valid_session(client):
    await _login(client)

    response = await client.get("/api/session")

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {"authenticated": True}


async def test_unknown_api_path_is_rejected_before_routing(client):
    response = await client.get("/api/definitely-missing")

    assert response.status_code == 401


async def test_authenticated_unknown_api_path_uses_the_error_envelope(client):
    await _login(client)

    response = await client.get("/api/definitely-missing")

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


async def test_non_api_404_keeps_the_html_default(client):
    response = await client.get("/definitely-missing")

    assert response.status_code == 404
    assert response.content_type.startswith("text/html")


async def test_authenticated_wrong_method_uses_the_error_envelope(client):
    await _login(client)

    response = await client.post("/api/status")

    assert response.status_code == 405
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "method_not_allowed"


async def test_authenticated_doubled_slash_path_stays_in_the_envelope(client):
    await _login(client)

    response = await client.get("/api//status")

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


async def test_status_reports_no_selection(client):
    await _login(client)

    response = await client.get("/api/status")

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {
        "bot": {"online": True},
        "guild_id": None,
        "connection": {"connected": False, "channel_id": None},
        "playback": None,
    }


async def test_status_reports_the_selected_guild_playback(client):
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = str(GUILD_A)

    response = await client.get("/api/status")

    assert response.status_code == 200
    body = json.loads(await response.get_data())
    assert body["guild_id"] == str(GUILD_A)
    assert body["connection"] == {
        "connected": True,
        "channel_id": str(CHANNEL_ID),
    }
    assert body["playback"]["current_music"]["title"] == "Now Track"
    assert body["playback"]["is_playing"] is True


def _occupy_voice(bot: ApiBot, channel_id: int = CHANNEL_ID) -> None:
    bot._guilds[GUILD_A].voice_client = SimpleNamespace(
        channel=SimpleNamespace(id=channel_id),
        is_connected=lambda: True,
    )


async def test_status_falls_back_to_the_voice_guild(client, bot: ApiBot):
    await _login(client)
    _occupy_voice(bot)

    response = await client.get("/api/status")

    body = json.loads(await response.get_data())
    assert body["guild_id"] == str(GUILD_A)
    assert body["connection"] == {
        "connected": True,
        "channel_id": str(CHANNEL_ID),
    }


async def test_status_shows_physical_voice_without_a_session(
    client, bot: ApiBot
):
    await _login(client)
    bot.sessions._session = None
    _occupy_voice(bot)

    response = await client.get("/api/status")

    body = json.loads(await response.get_data())
    assert body["guild_id"] == str(GUILD_A)
    assert body["connection"] == {
        "connected": True,
        "channel_id": str(CHANNEL_ID),
    }
    assert body["playback"] is None


async def test_mutations_reach_the_voice_guild_without_a_selection(
    client, bot: ApiBot
):
    await _login(client)
    _occupy_voice(bot)

    response = await client.post(
        "/api/queue", json={"url": "https://example.com/song"}
    )

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert ("play", "https://example.com/song") in session_obj.calls


async def test_disconnect_clears_an_orphaned_voice_client(client, bot: ApiBot):
    await _login(client)
    bot.sessions._session = None
    _occupy_voice(bot)

    response = await client.post("/api/disconnect")

    assert response.status_code == 200
    assert bot.sessions.disconnect_calls == [GUILD_A]


async def test_disconnect_does_not_reach_another_guild(client, bot: ApiBot):
    await _login(client)
    bot.sessions._session = None
    async with client.session_transaction() as stored:
        stored["guild_id"] = str(GUILD_A)
    bot._guilds[GUILD_B] = FakeGuild(GUILD_B, "Beta Guild")
    bot._guilds[GUILD_B].voice_client = SimpleNamespace(
        channel=SimpleNamespace(id=CHANNEL_ID),
        is_connected=lambda: True,
    )

    response = await client.post("/api/disconnect")

    assert response.status_code == 200
    assert bot.sessions.disconnect_calls == []


async def test_status_reports_the_bot_offline(client, bot: ApiBot):
    await _login(client)
    bot._closed = True

    response = await client.get("/api/status")

    assert json.loads(await response.get_data())["bot"] == {"online": False}


async def test_status_maps_an_unexpected_failure_to_an_envelope(
    client, monkeypatch: pytest.MonkeyPatch
):
    await _login(client)

    async def boom(guild_id: int | None) -> dict[str, Any]:
        raise RuntimeError("status exploded")

    monkeypatch.setattr("pages.api.state.status_snapshot", boom)
    monkeypatch.setitem(quart_app.config, "TESTING", False)

    response = await client.get("/api/status")

    assert response.status_code == 500
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "internal_error"


async def test_guild_list_reports_only_shared_guilds(client):
    await _login(client)

    response = await client.get("/api/guilds")

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {
        "guilds": [{"id": str(GUILD_A), "name": "Alpha Guild"}]
    }


async def test_guild_list_hides_a_guild_the_actor_does_not_belong_to(
    client, bot: ApiBot
):
    await _login(client, [GUILD_A])
    bot._guilds[GUILD_B] = FakeGuild(GUILD_B, "Beta Guild")

    listed = await client.get("/api/guilds")
    ids = [
        guild["id"] for guild in json.loads(await listed.get_data())["guilds"]
    ]
    assert ids == [str(GUILD_A)]

    bot._guilds.pop(GUILD_A)
    gone = await client.get("/api/guilds")
    assert json.loads(await gone.get_data())["guilds"] == []


async def test_channel_list_reports_the_guilds_voice_channels(client):
    await _login(client)

    response = await client.get(f"/api/guilds/{GUILD_A}/channels")

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {
        "channels": [{"id": str(GUILD_A * 10), "name": "Channel 1"}]
    }


async def test_channel_list_rejects_an_unshared_guild(client):
    await _login(client)

    response = await client.get("/api/guilds/99999/channels")

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


async def test_snowflake_ids_stay_exact_over_the_json_api(client, bot: ApiBot):
    bot._guilds[SNOWFLAKE] = FakeGuild(SNOWFLAKE, "The Nosbor's Hand")
    await _login(client)

    response = await client.get("/api/guilds")
    guilds = json.loads(await response.get_data())["guilds"]
    served = next(g for g in guilds if g["name"] == "The Nosbor's Hand")
    assert served["id"] == str(SNOWFLAKE)

    channels = await client.get(f"/api/guilds/{SNOWFLAKE}/channels")
    assert channels.status_code == 200
    listed = json.loads(await channels.get_data())["channels"]
    assert listed[0]["id"] == str(SNOWFLAKE * 10)

    connected = await client.post(
        "/api/connect",
        json={
            "guild_id": str(SNOWFLAKE),
            "channel_id": str(SNOWFLAKE * 10),
        },
    )
    assert connected.status_code == 200
    assert json.loads(await connected.get_data())["guild_id"] == str(SNOWFLAKE)
    assert bot.sessions.connect_calls == [(SNOWFLAKE, SNOWFLAKE * 10)]


async def test_connect_tolerates_a_leading_zero_digit_string(
    client, bot: ApiBot
):
    await _login(client)

    response = await client.post(
        "/api/connect",
        json={"guild_id": str(GUILD_A), "channel_id": f"0{GUILD_A * 10}"},
    )

    assert response.status_code == 200
    assert bot.sessions.connect_calls == [(GUILD_A, GUILD_A * 10)]


async def test_connect_dispatches_and_records_the_selection(
    client, bot: ApiBot
):
    await _login(client)

    response = await client.post(
        "/api/connect",
        json={"guild_id": str(GUILD_A), "channel_id": str(GUILD_A * 10)},
    )

    assert response.status_code == 200
    assert bot.sessions.connect_calls == [(GUILD_A, GUILD_A * 10)]
    body = json.loads(await response.get_data())
    assert body["guild_id"] == str(GUILD_A)
    assert body["connection"] == {
        "connected": True,
        "channel_id": str(CHANNEL_ID),
    }
    async with client.session_transaction() as stored:
        assert stored["guild_id"] == str(GUILD_A)


async def test_connect_rejects_an_unshared_guild(client, bot: ApiBot):
    await _login(client)

    response = await client.post(
        "/api/connect", json={"guild_id": "99999", "channel_id": "10"}
    )

    assert response.status_code == 404
    assert bot.sessions.connect_calls == []


async def test_connect_rejects_a_non_numeric_guild_id(client, bot: ApiBot):
    await _login(client)

    response = await client.post(
        "/api/connect", json={"guild_id": "\u00b2", "channel_id": "10"}
    )

    assert response.status_code == 404
    assert bot.sessions.connect_calls == []


async def test_connect_rejects_a_channel_outside_the_guild(
    client, bot: ApiBot
):
    await _login(client)

    response = await client.post(
        "/api/connect", json={"guild_id": str(GUILD_A), "channel_id": "11"}
    )

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"
    assert bot.sessions.connect_calls == []


async def test_connect_answers_with_the_same_truth_as_status(
    client, bot: ApiBot
):
    await _login(client)

    response = await client.post(
        "/api/connect",
        json={"guild_id": str(GUILD_A), "channel_id": str(GUILD_A * 10)},
    )
    status = await client.get("/api/status")

    assert json.loads(await response.get_data()) == json.loads(
        await status.get_data()
    )


async def test_selection_persists_the_guild_and_channel(client, storage):
    await _login(client)

    response = await client.post(
        "/api/selection",
        json={"guild_id": str(GUILD_A), "channel_id": str(GUILD_A * 10)},
    )

    assert response.status_code == 200
    body = json.loads(await response.get_data())
    assert body["guild_id"] == str(GUILD_A)
    viewers = await storage.viewers(str(GUILD_A))
    assert [viewer.user_id for viewer in viewers] == ["555"]
    assert viewers[0].channel_id == str(GUILD_A * 10)
    assert viewers[0].channel_name == f"Channel {GUILD_A}"
    async with client.session_transaction() as stored:
        assert stored["guild_id"] == str(GUILD_A)


async def test_selection_clears_the_guild(client, storage):
    await _login(client)
    await _select_guild(client)

    response = await client.post("/api/selection", json={})

    assert response.status_code == 200
    body = json.loads(await response.get_data())
    assert body["guild_id"] is None
    assert await storage.viewers(str(GUILD_A)) == []
    async with client.session_transaction() as stored:
        assert "guild_id" not in stored


async def test_selection_rejects_an_unshared_guild(client, storage):
    await _login(client)

    response = await client.post("/api/selection", json={"guild_id": "99999"})

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


async def test_selection_rejects_a_channel_outside_the_guild(client, storage):
    await _login(client)

    response = await client.post(
        "/api/selection",
        json={"guild_id": str(GUILD_A), "channel_id": "11"},
    )

    assert response.status_code == 404


async def test_connect_records_the_connection_event(client, storage):
    await _login(client)

    response = await client.post(
        "/api/connect",
        json={"guild_id": str(GUILD_A), "channel_id": str(GUILD_A * 10)},
    )

    assert response.status_code == 200
    last = await storage.last_connection(str(GUILD_A))
    assert last is not None
    assert last.action == "connect"
    assert last.actor_name == "panel-user"
    assert last.channel_name == f"Channel {GUILD_A}"
    viewers = await storage.viewers(str(GUILD_A))
    assert viewers[0].channel_id == str(GUILD_A * 10)


async def test_disconnect_answers_with_the_same_truth_as_status(
    client, bot: ApiBot
):
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = str(GUILD_A)

    response = await client.post("/api/disconnect")
    status = await client.get("/api/status")

    assert response.status_code == 200
    assert bot.sessions.disconnect_calls == [GUILD_A]
    assert json.loads(await response.get_data()) == json.loads(
        await status.get_data()
    )


async def test_disconnect_records_the_release(client, bot: ApiBot, storage):
    await _login(client)
    await _select_guild(client)

    response = await client.post("/api/disconnect")

    assert response.status_code == 200
    last = await storage.last_connection(str(GUILD_A))
    assert last is not None
    assert last.action == "disconnect"
    assert last.actor_name == "panel-user"
    assert last.channel_id == str(CHANNEL_ID)


async def test_disconnect_without_a_selection_is_idempotent(
    client, bot: ApiBot
):
    await _login(client)

    response = await client.post("/api/disconnect")

    assert response.status_code == 200
    assert bot.sessions.disconnect_calls == []
    assert json.loads(await response.get_data())["guild_id"] is None


async def test_disconnect_keeps_the_selection(client, bot: ApiBot):
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = str(GUILD_A)

    await client.post("/api/disconnect")

    async with client.session_transaction() as stored:
        assert stored["guild_id"] == str(GUILD_A)
    response = await client.get("/api/status")
    assert json.loads(await response.get_data())["guild_id"] == str(GUILD_A)


async def test_status_drops_a_selection_the_bot_no_longer_shares(client):
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = "99999"

    response = await client.get("/api/status")

    body = json.loads(await response.get_data())
    assert body["guild_id"] is None
    assert body["connection"] == {"connected": False, "channel_id": None}


async def test_search_returns_results(client, monkeypatch: pytest.MonkeyPatch):
    await _login(client)
    patch_search(monkeypatch, [found_track()])

    response = await client.post("/api/search", json={"term": "found track"})

    assert response.status_code == 200
    body = json.loads(await response.get_data())
    assert body["results"] == [
        {
            "title": "Found Track",
            "url": "https://www.youtube.com/watch?v=found",
            "uploader": "Artist",
            "duration": 30,
            "thumbnail": "https://img.example.com/found.jpg",
        }
    ]


@pytest.mark.parametrize("payload", [{}, {"term": ""}, {"term": "   "}])
async def test_search_without_a_term_returns_no_results(client, payload):
    await _login(client)

    response = await client.post("/api/search", json=payload)

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {"results": []}


async def test_search_without_matches_returns_no_results(
    client, monkeypatch: pytest.MonkeyPatch
):
    await _login(client)
    patch_search(monkeypatch, [])

    response = await client.post("/api/search", json={"term": "nothing"})

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {"results": []}


async def _select_guild(client) -> None:
    async with client.session_transaction() as stored:
        stored["guild_id"] = str(GUILD_A)


async def test_queue_dispatches_and_answers_with_the_same_truth_as_status(
    client, bot: ApiBot
):
    await _login(client)
    await _select_guild(client)

    response = await client.post(
        "/api/queue", json={"url": "https://example.com/song"}
    )
    status = await client.get("/api/status")

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert ("play", "https://example.com/song") in session_obj.calls
    assert json.loads(await response.get_data()) == json.loads(
        await status.get_data()
    )


async def test_queue_trims_a_padded_url(client, bot: ApiBot):
    await _login(client)
    await _select_guild(client)

    response = await client.post(
        "/api/queue", json={"url": "  https://example.com/song  "}
    )

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert ("play", "https://example.com/song") in session_obj.calls


async def test_queue_remove_dispatches_and_answers_with_the_same_truth_as_status(
    client, bot: ApiBot
):
    await _login(client)
    await _select_guild(client)

    response = await client.post(
        "/api/queue/remove", json={"url": "https://example.com/song"}
    )
    status = await client.get("/api/status")

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert ("remove", "https://example.com/song") in session_obj.calls
    assert json.loads(await response.get_data()) == json.loads(
        await status.get_data()
    )


async def test_queue_clear_dispatches_and_answers_with_the_same_truth_as_status(
    client, bot: ApiBot
):
    await _login(client)
    await _select_guild(client)

    response = await client.post("/api/queue/clear")
    status = await client.get("/api/status")

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert "clear_queue" in session_obj.calls
    assert json.loads(await response.get_data()) == json.loads(
        await status.get_data()
    )


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/queue", {"url": "https://example.com/song"}),
        ("/api/queue/remove", {"url": "https://example.com/song"}),
        ("/api/queue/clear", {}),
    ],
)
async def test_queue_mutations_require_a_live_session(
    client, bot: ApiBot, path: str, payload: dict[str, Any]
):
    await _login(client)
    await _select_guild(client)
    bot.sessions._session = None

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/queue", {"url": "https://example.com/song"}),
        ("/api/queue/remove", {"url": "https://example.com/song"}),
        ("/api/queue/clear", {}),
    ],
)
async def test_queue_mutations_require_a_shared_selection(
    client, path: str, payload: dict[str, Any]
):
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = "99999"

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/queue", {}),
        ("/api/queue", {"url": ""}),
        ("/api/queue", {"url": 42}),
        ("/api/queue/remove", {}),
        ("/api/queue/remove", {"url": 42}),
    ],
)
async def test_queue_mutations_require_a_url(
    client, path: str, payload: dict[str, Any]
):
    await _login(client)
    await _select_guild(client)

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


async def test_search_maps_a_failure_to_the_error_envelope(
    client, monkeypatch: pytest.MonkeyPatch
):
    await _login(client)

    async def boom(term: str) -> list[dict[str, Any]]:
        raise RuntimeError("search exploded")

    monkeypatch.setattr("pages.api.actions.search_tracks", boom)
    monkeypatch.setitem(quart_app.config, "TESTING", False)

    response = await client.post("/api/search", json={"term": "anything"})

    assert response.status_code == 500
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "internal_error"


async def test_sse_stream_reports_and_resyncs_status(client, bot: ApiBot):
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = str(GUILD_A)
    cookie = next(c for c in client.cookie_jar if c.name == "session").value

    async with (
        _running_app(quart_app) as port,
        httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            cookies={"session": cookie},
        ) as http,
    ):
        first = await _read_status_frame(http)
        assert first["bot"] == {"online": True}
        assert first["guild_id"] == str(GUILD_A)
        assert first["connection"] == {
            "connected": True,
            "channel_id": str(CHANNEL_ID),
        }
        assert first["playback"]["current_music"]["title"] == "Now Track"

        await _refresh_current_music(bot, "Next Track")
        second = await _read_status_frame(http)

        assert second["playback"]["current_music"]["title"] == "Next Track"
        assert second["playback"]["queue"] == []


async def test_sse_stream_emits_the_roster(client, bot: ApiBot, storage):
    await _login(client)
    await _select_guild(client)
    await client.post(
        "/api/connect",
        json={"guild_id": str(GUILD_A), "channel_id": str(GUILD_A * 10)},
    )
    cookie = next(c for c in client.cookie_jar if c.name == "session").value

    async with (
        _running_app(quart_app) as port,
        httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            cookies={"session": cookie},
        ) as http,
    ):
        presence = await _read_presence_frame(http)

    assert presence["guild_id"] == str(GUILD_A)
    assert [viewer["user_id"] for viewer in presence["viewers"]] == ["555"]
    assert presence["viewers"][0]["username"] == "panel-user"
    assert presence["last_connection"]["action"] == "connect"
    assert presence["last_connection"]["actor_name"] == "panel-user"


TRANSPORT_CALLS: list[tuple[str, dict[str, Any], Any]] = [
    ("/api/playback/pause", {}, "pause"),
    ("/api/playback/resume", {}, "resume"),
    ("/api/playback/skip", {}, "skip"),
    ("/api/playback/previous", {}, "previous"),
    ("/api/playback/loop", {"mode": "track"}, ("set_loop", LoopMode.TRACK)),
    ("/api/playback/loop", {"mode": "fila"}, ("set_loop", LoopMode.QUEUE)),
    ("/api/playback/seek", {"position": 30.0}, ("seek", 30.0, True)),
    ("/api/playback/volume", {"volume": 0.5}, ("set_volume", 0.5)),
]


@pytest.mark.parametrize(("path", "payload", "expected"), TRANSPORT_CALLS)
async def test_transport_dispatches_and_answers_the_same_truth_as_status(
    client, bot: ApiBot, path: str, payload: dict[str, Any], expected: Any
):
    await _login(client)
    await _select_guild(client)

    response = await client.post(path, json=payload)
    status = await client.get("/api/status")

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert expected in session_obj.calls
    assert json.loads(await response.get_data()) == json.loads(
        await status.get_data()
    )


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/playback/loop", {}),
        ("/api/playback/loop", {"mode": 42}),
        ("/api/playback/loop", {"mode": ""}),
        ("/api/playback/loop", {"mode": "bogus"}),
        ("/api/playback/seek", {}),
        ("/api/playback/seek", {"position": "30"}),
        ("/api/playback/seek", {"position": -5.0}),
        ("/api/playback/seek", {"position": float("inf")}),
        ("/api/playback/seek", {"position": 999.0}),
        ("/api/playback/volume", {}),
        ("/api/playback/volume", {"volume": "loud"}),
        ("/api/playback/volume", {"volume": True}),
        ("/api/playback/volume", {"volume": float("nan")}),
    ],
)
async def test_transport_rejects_an_invalid_argument(
    client, bot: ApiBot, path: str, payload: dict[str, Any]
):
    await _login(client)
    await _select_guild(client)

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert session_obj.calls == []


@pytest.mark.parametrize(("path", "payload", "expected"), TRANSPORT_CALLS)
async def test_transport_requires_a_live_session(
    client, bot: ApiBot, path: str, payload: dict[str, Any], expected: Any
):
    del expected
    await _login(client)
    await _select_guild(client)
    bot.sessions._session = None

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


@pytest.mark.parametrize(("path", "payload", "expected"), TRANSPORT_CALLS)
async def test_transport_requires_a_shared_selection(
    client, path: str, payload: dict[str, Any], expected: Any
):
    del expected
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = "99999"

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "path",
    [
        "/api/playback/pause",
        "/api/playback/resume",
        "/api/playback/skip",
        "/api/playback/previous",
        "/api/playback/loop",
        "/api/playback/seek",
        "/api/playback/volume",
    ],
)
async def test_transport_paths_reject_anonymous_calls(client, path: str):
    response = await client.post(path, json={})

    assert response.status_code == 401
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "unauthorized"


async def test_seek_accepts_the_exact_track_duration(client, bot: ApiBot):
    await _login(client)
    await _select_guild(client)

    response = await client.post(
        "/api/playback/seek", json={"position": 120.0}
    )

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert ("seek", 120.0, True) in session_obj.calls


async def test_volume_is_clamped_by_the_session(client, bot: ApiBot):
    await _login(client)
    await _select_guild(client)

    response = await client.post("/api/playback/volume", json={"volume": 4.0})

    assert response.status_code == 200
    body = json.loads(await response.get_data())
    assert body["playback"]["volume"] == pytest.approx(1.0)


LAYER_CALLS: list[tuple[str, dict[str, Any], Any]] = [
    (
        "/api/layers",
        {"url": "https://example.com/layer"},
        (
            "add_layer",
            "https://example.com/layer",
        ),
    ),
    (
        "/api/layers/remove",
        {"layer_id": "layer-1"},
        (
            "remove_layer",
            "layer-1",
        ),
    ),
    (
        "/api/layers/volume",
        {"layer_id": "layer-1", "volume": 0.25},
        (
            "set_layer_volume",
            "layer-1",
            0.25,
        ),
    ),
]


async def _seed_layer(client) -> None:
    await client.post("/api/layers", json={"url": "https://example.com/layer"})


@pytest.mark.parametrize(("path", "payload", "expected"), LAYER_CALLS)
async def test_layer_dispatches_and_answers_the_same_truth_as_status(
    client, bot: ApiBot, path: str, payload: dict[str, Any], expected: Any
):
    await _login(client)
    await _select_guild(client)
    if "layer_id" in payload:
        await _seed_layer(client)

    response = await client.post(path, json=payload)
    status = await client.get("/api/status")

    assert response.status_code == 200
    session_obj = bot.sessions._session
    assert session_obj is not None
    assert expected in session_obj.calls
    assert json.loads(await response.get_data()) == json.loads(
        await status.get_data()
    )


async def test_layer_add_answers_the_created_layer(client, bot: ApiBot):
    await _login(client)
    await _select_guild(client)

    response = await client.post(
        "/api/layers", json={"url": "https://example.com/layer"}
    )

    body = json.loads(await response.get_data())
    assert body["playback"]["layers"] == [
        {
            "id": "layer-1",
            "title": "https://example.com/layer",
            "url": "https://example.com/layer",
            "volume": 0.5,
            "thumbnail": "",
        }
    ]


async def test_layer_remove_answers_the_dropped_layer(client, bot: ApiBot):
    await _login(client)
    await _select_guild(client)
    await _seed_layer(client)

    response = await client.post(
        "/api/layers/remove", json={"layer_id": "layer-1"}
    )

    body = json.loads(await response.get_data())
    assert body["playback"]["layers"] == []


async def test_layer_volume_answers_the_new_gain(client, bot: ApiBot):
    await _login(client)
    await _select_guild(client)
    await _seed_layer(client)

    response = await client.post(
        "/api/layers/volume", json={"layer_id": "layer-1", "volume": 0.25}
    )

    body = json.loads(await response.get_data())
    assert body["playback"]["layers"][0]["volume"] == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/layers", {}),
        ("/api/layers", {"url": ""}),
        ("/api/layers", {"url": 42}),
        ("/api/layers/remove", {}),
        ("/api/layers/remove", {"layer_id": ""}),
        ("/api/layers/remove", {"layer_id": 42}),
        ("/api/layers/remove", {"layer_id": "missing"}),
        ("/api/layers/volume", {}),
        ("/api/layers/volume", {"layer_id": "layer-1"}),
        ("/api/layers/volume", {"layer_id": "layer-1", "volume": "loud"}),
        ("/api/layers/volume", {"layer_id": "layer-1", "volume": True}),
        (
            "/api/layers/volume",
            {"layer_id": "layer-1", "volume": float("nan")},
        ),
        ("/api/layers/volume", {"layer_id": "missing", "volume": 0.5}),
    ],
)
async def test_layer_mutations_reject_an_invalid_argument(
    client, bot: ApiBot, path: str, payload: dict[str, Any]
):
    await _login(client)
    await _select_guild(client)
    await _seed_layer(client)

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


@pytest.mark.parametrize(("path", "payload", "expected"), LAYER_CALLS)
async def test_layer_mutations_require_a_live_session(
    client, bot: ApiBot, path: str, payload: dict[str, Any], expected: Any
):
    del expected
    await _login(client)
    await _select_guild(client)
    bot.sessions._session = None

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


@pytest.mark.parametrize(("path", "payload", "expected"), LAYER_CALLS)
async def test_layer_mutations_require_a_shared_selection(
    client, path: str, payload: dict[str, Any], expected: Any
):
    del expected
    await _login(client)
    async with client.session_transaction() as stored:
        stored["guild_id"] = "99999"

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "path", ["/api/layers", "/api/layers/remove", "/api/layers/volume"]
)
async def test_layer_paths_reject_anonymous_calls(client, path: str):
    response = await client.post(path, json={})

    assert response.status_code == 401
    body = json.loads(await response.get_data())
    assert body["error"]["code"] == "unauthorized"


CROSS_TENANT_MUTATIONS: list[tuple[str, dict[str, Any]]] = [
    ("/api/queue", {"url": "https://example.com/song"}),
    ("/api/queue/remove", {"url": "https://example.com/song"}),
    ("/api/queue/clear", {}),
    ("/api/layers", {"url": "https://example.com/layer"}),
    ("/api/layers/remove", {"layer_id": "layer-1"}),
    ("/api/layers/volume", {"layer_id": "layer-1", "volume": 0.5}),
    *[(path, payload) for path, payload, _ in TRANSPORT_CALLS],
]


def _share_guild_b(bot: ApiBot) -> None:
    bot._guilds[GUILD_B] = FakeGuild(GUILD_B, "Beta Guild")


async def _select(client, guild_id: int) -> None:
    async with client.session_transaction() as stored:
        stored["guild_id"] = str(guild_id)


async def test_each_actor_lists_only_their_own_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])
    other = await _second_actor([GUILD_B])

    mine = json.loads(await (await client.get("/api/guilds")).get_data())
    theirs = json.loads(await (await other.get("/api/guilds")).get_data())

    assert mine == {"guilds": [{"id": str(GUILD_A), "name": "Alpha Guild"}]}
    assert theirs == {"guilds": [{"id": str(GUILD_B), "name": "Beta Guild"}]}


async def test_channel_list_denies_another_actors_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])

    denied = await client.get(f"/api/guilds/{GUILD_B}/channels")
    allowed = await client.get(f"/api/guilds/{GUILD_A}/channels")

    assert denied.status_code == 404
    assert json.loads(await denied.get_data())["error"]["code"] == "not_found"
    assert allowed.status_code == 200
    assert json.loads(await allowed.get_data()) == {
        "channels": [{"id": str(GUILD_A * 10), "name": f"Channel {GUILD_A}"}]
    }


async def test_connect_denies_another_actors_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])

    response = await client.post(
        "/api/connect",
        json={"guild_id": str(GUILD_B), "channel_id": str(GUILD_B * 10)},
    )

    assert response.status_code == 404
    assert (
        json.loads(await response.get_data())["error"]["code"] == "not_found"
    )
    assert bot.sessions.connect_calls == []
    async with client.session_transaction() as stored:
        assert "guild_id" not in stored


async def test_selection_denies_another_actors_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])

    response = await client.post(
        "/api/selection", json={"guild_id": str(GUILD_B)}
    )

    assert response.status_code == 404
    assert (
        json.loads(await response.get_data())["error"]["code"] == "not_found"
    )
    async with client.session_transaction() as stored:
        assert "guild_id" not in stored


async def test_status_hides_another_actors_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])
    await _select(client, GUILD_B)

    response = await client.get("/api/status")

    body = json.loads(await response.get_data())
    assert body["guild_id"] is None
    assert body["connection"] == {"connected": False, "channel_id": None}
    assert body["playback"] is None


async def test_status_does_not_fall_back_to_an_unauthorized_voice_guild(
    client, bot: ApiBot
):
    _share_guild_b(bot)
    bot._guilds[GUILD_B].voice_client = SimpleNamespace(
        channel=SimpleNamespace(id=CHANNEL_ID),
        is_connected=lambda: True,
    )
    await _login(client, [GUILD_A])

    response = await client.get("/api/status")

    assert json.loads(await response.get_data())["guild_id"] is None


@pytest.mark.parametrize(("path", "payload"), CROSS_TENANT_MUTATIONS)
async def test_mutations_deny_another_actors_guild(
    client, bot: ApiBot, path: str, payload: dict[str, Any]
):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])
    await _select(client, GUILD_B)
    session_obj = bot.sessions._session
    assert session_obj is not None
    session_obj.calls.clear()

    response = await client.post(path, json=payload)

    assert response.status_code == 404
    assert (
        json.loads(await response.get_data())["error"]["code"] == "not_found"
    )
    assert session_obj.calls == []


async def test_disconnect_denies_another_actors_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    bot._guilds[GUILD_B].voice_client = SimpleNamespace(
        channel=SimpleNamespace(id=CHANNEL_ID),
        is_connected=lambda: True,
    )
    await _login(client, [GUILD_A])
    await _select(client, GUILD_B)

    response = await client.post("/api/disconnect")

    assert response.status_code == 200
    assert bot.sessions.disconnect_calls == []
    assert json.loads(await response.get_data())["guild_id"] is None


async def test_each_actor_controls_only_their_own_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])
    other = await _second_actor([GUILD_B])
    session_obj = bot.sessions._session
    assert session_obj is not None

    await client.post(
        "/api/selection",
        json={"guild_id": str(GUILD_A), "channel_id": str(GUILD_A * 10)},
    )
    await other.post(
        "/api/selection",
        json={"guild_id": str(GUILD_B), "channel_id": str(GUILD_B * 10)},
    )
    session_obj.calls.clear()

    mine = await client.post(
        "/api/queue", json={"url": "https://example.com/mine"}
    )
    theirs = await other.post(
        "/api/queue", json={"url": "https://example.com/theirs"}
    )

    assert json.loads(await mine.get_data())["guild_id"] == str(GUILD_A)
    assert json.loads(await theirs.get_data())["guild_id"] == str(GUILD_B)
    assert ("play", "https://example.com/mine") in session_obj.calls
    assert ("play", "https://example.com/theirs") in session_obj.calls


async def test_sse_stream_hides_another_actors_guild(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])
    await _select(client, GUILD_B)
    cookie = next(c for c in client.cookie_jar if c.name == "session").value

    async with (
        _running_app(quart_app) as port,
        httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            cookies={"session": cookie},
        ) as http,
    ):
        first = await _read_status_frame(http)

    assert first["guild_id"] is None
    assert first["connection"] == {"connected": False, "channel_id": None}
    assert first["playback"] is None


async def test_sse_directory_lists_only_the_actors_guilds(client, bot: ApiBot):
    _share_guild_b(bot)
    await _login(client, [GUILD_A])
    await _select(client, GUILD_A)
    cookie = next(c for c in client.cookie_jar if c.name == "session").value

    async with (
        _running_app(quart_app) as port,
        httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}",
            cookies={"session": cookie},
        ) as http,
    ):
        directory = await _read_directory_frame(http)

    assert [guild["id"] for guild in directory["guilds"]] == [str(GUILD_A)]
