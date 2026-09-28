"""Contract tests for the JSON API.

These drive the app at its HTTP seam: session exchange and rejection, the
status payload, the machine-readable error envelope, and a real read of
the SSE stream against a running server.
"""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import httpx
import pytest
import uvicorn

from app import app as quart_app
from src import bot_state as deps
from src.harpi_lib.harpi_bot import HarpiBot
from src.harpi_lib.music.ytmusic import YTMusicData
from tests.test_music_page import (
    GUILD_A,
    FakeBot,
    FakeGuild,
    FakeSession,
    playing_status,
)

PANEL_TOKEN = "test-panel-token"
SECRET = "test-secret"
CHANNEL_ID = 42


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


@pytest.fixture
def bot() -> ApiBot:
    return ApiBot(
        [FakeGuild(GUILD_A, "Alpha Guild")],
        FakeSession(playing_status(channel_id=CHANNEL_ID)),
    )


@pytest.fixture
def client(bot: ApiBot, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.setenv("PANEL_TOKEN", PANEL_TOKEN)
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    quart_app.secret_key = SECRET
    quart_app.config["TESTING"] = True
    deps.init_bot(cast(HarpiBot, bot))
    yield quart_app.test_client()
    deps._bot_ref = None


async def _login(client, token: str = PANEL_TOKEN):
    return await client.post("/api/session", json={"token": token})


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
async def _running_app(app) -> AsyncIterator[int]:
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


async def test_session_exchange_issues_an_http_only_same_site_cookie(client):
    response = await _login(client)

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {"authenticated": True}
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


async def test_session_exchange_rejects_a_bad_token(client):
    response = await _login(client, "wrong")

    assert response.status_code == 401
    assert json.loads(await response.get_data()) == {
        "error": {"code": "unauthorized", "message": "Invalid panel token"}
    }
    assert "Set-Cookie" not in response.headers


async def test_session_exchange_rejects_a_missing_token(client):
    response = await client.post("/api/session", json={})

    assert response.status_code == 401


async def test_session_exchange_rejects_a_non_json_body(client):
    response = await client.post("/api/session", data=b"not json")

    assert response.status_code == 401


async def test_session_exchange_rejects_when_no_token_is_configured(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("PANEL_TOKEN", raising=False)

    response = await _login(client)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "path",
    ["/api", "/api/session", "/api/status", "/api/events"],
)
async def test_guarded_endpoints_reject_anonymous_calls(client, path: str):
    response = await client.get(path)

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
    assert body["guild_id"] == GUILD_A
    assert body["connection"] == {
        "connected": True,
        "channel_id": CHANNEL_ID,
    }
    assert body["playback"]["current_music"]["title"] == "Now Track"
    assert body["playback"]["is_playing"] is True


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
        assert first["guild_id"] == GUILD_A
        assert first["connection"] == {
            "connected": True,
            "channel_id": CHANNEL_ID,
        }
        assert first["playback"]["current_music"]["title"] == "Now Track"

        await _refresh_current_music(bot, "Next Track")
        second = await _read_status_frame(http)

        assert second["playback"]["current_music"]["title"] == "Next Track"
        assert second["playback"]["queue"] == []
