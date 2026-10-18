"""Discord OAuth panel authentication over the app's HTTP seam.

The Discord network is faked at ``discord_oauth._fetch_json``; the bot is a
fake, so the shared-guild check runs through the real ``state.list_guilds``.
"""

from __future__ import annotations

import json
from typing import Any, cast

import pytest

from app import app as quart_app
from src import bot_state as deps
from src import discord_oauth
from src.harpi_lib.harpi_bot import HarpiBot
from src.panel import state
from tests.fakes import GUILD_A, FakeBot, FakeGuild

CLIENT_ID = "891732797054681119"
SECRET = "test-secret"
STATE = "the-state-nonce"
VERIFIER = "the-code-verifier"


class AuthBot(FakeBot):
    def is_ready(self) -> bool:
        return True

    def is_closed(self) -> bool:
        return False


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    monkeypatch.setenv("DISCORD_CLIENT_ID", CLIENT_ID)
    monkeypatch.delenv("DISCORD_REDIRECT_URI", raising=False)
    quart_app.secret_key = SECRET
    quart_app.config["TESTING"] = True
    deps.init_bot(cast(HarpiBot, AuthBot([FakeGuild(GUILD_A, "Alpha Guild")])))
    yield quart_app.test_client()
    deps._bot_ref = None


def fake_discord(monkeypatch: pytest.MonkeyPatch, guild_ids: list[int]):
    async def fetch(method: str, url: str, **kwargs: Any) -> Any:
        del method, kwargs
        if url == discord_oauth.TOKEN_ENDPOINT:
            return {"access_token": "the-token"}
        if url == discord_oauth.USER_ENDPOINT:
            return {"id": "555", "username": "harpi-user"}
        if url == discord_oauth.GUILDS_ENDPOINT:
            return [{"id": str(guild_id)} for guild_id in guild_ids]
        raise AssertionError(url)

    monkeypatch.setattr(discord_oauth, "_fetch_json", fetch)


async def _begin(client) -> None:
    async with client.session_transaction() as stored:
        stored["oauth_state"] = STATE
        stored["oauth_verifier"] = VERIFIER


async def _callback(client, **params: str):
    return await client.get(
        "/api/auth/discord/callback",
        query_string={"code": "abc", "state": STATE, **params},
    )


async def _stored(client) -> dict[str, Any]:
    async with client.session_transaction() as stored:
        return dict(stored)


def test_pkce_challenge_matches_the_rfc7636_vector():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

    assert discord_oauth.challenge_for(verifier) == (
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


def test_states_and_verifiers_are_fresh_each_call():
    assert discord_oauth.new_state() != discord_oauth.new_state()
    assert discord_oauth.new_verifier() != discord_oauth.new_verifier()


async def test_fetch_guild_ids_pages_past_the_first_page(monkeypatch):
    pages = [
        [{"id": str(index)} for index in range(1, 201)],
        [{"id": "500"}],
    ]
    cursors = []

    async def fetch(method: str, url: str, **kwargs: Any) -> Any:
        del method, url
        cursors.append(kwargs["params"]["after"])
        return pages.pop(0)

    monkeypatch.setattr(discord_oauth, "_fetch_json", fetch)

    ids = await discord_oauth.fetch_guild_ids("token")

    assert len(ids) == 201
    assert 500 in ids
    assert cursors == [0, 200]


async def test_fetch_guild_ids_stops_on_an_empty_page(monkeypatch):
    async def fetch(method: str, url: str, **kwargs: Any) -> Any:
        del method, url, kwargs
        return []

    monkeypatch.setattr(discord_oauth, "_fetch_json", fetch)

    assert await discord_oauth.fetch_guild_ids("token") == set()


async def test_fetch_json_wraps_a_transport_failure(monkeypatch):
    class DownSession:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs

        async def __aenter__(self) -> None:
            raise discord_oauth.aiohttp.ClientError("down")

        async def __aexit__(self, *args: Any) -> bool:
            return False

    monkeypatch.setattr(discord_oauth.aiohttp, "ClientSession", DownSession)

    with pytest.raises(discord_oauth.OAuthError):
        await discord_oauth._fetch_json("GET", "https://example.com")


def test_authorize_url_carries_pkce_and_scopes():
    url = discord_oauth.authorize_url(
        CLIENT_ID, "http://localhost:8000/cb", STATE, "chal"
    )

    assert url.startswith(discord_oauth.AUTHORIZE_ENDPOINT + "?")
    assert "code_challenge=chal" in url
    assert "code_challenge_method=S256" in url
    assert "scope=identify+guilds" in url
    assert f"state={STATE}" in url


async def test_login_redirects_to_discord_and_stores_the_pkce_pair(client):
    response = await client.get("/api/auth/discord")

    assert response.status_code == 302
    location = response.headers["Location"]
    assert location.startswith(discord_oauth.AUTHORIZE_ENDPOINT)
    stored = await _stored(client)
    assert stored["oauth_state"]
    assert stored["oauth_verifier"]
    assert f"state={stored['oauth_state']}" in location
    assert stored["oauth_verifier"] not in location


async def test_login_without_configuration_returns_to_the_panel(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DISCORD_CLIENT_ID", raising=False)

    response = await client.get("/api/auth/discord")

    assert response.status_code == 302
    assert response.headers["Location"] == "/?auth=unconfigured"


async def test_callback_opens_a_session_for_a_shared_guild_member(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    response = await _callback(client)

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    stored = await _stored(client)
    assert stored["authenticated"] is True
    assert stored["user_id"] == "555"
    assert stored["username"] == "harpi-user"
    assert "oauth_state" not in stored


async def test_callback_denies_a_stranger(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [999])
    await _begin(client)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=denied"
    assert (await _stored(client)).get("authenticated") is not True


async def test_callback_rejects_a_state_mismatch(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    response = await client.get(
        "/api/auth/discord/callback",
        query_string={"code": "abc", "state": "forged"},
    )

    assert response.headers["Location"] == "/?auth=failed"


async def test_callback_rejects_a_foreign_issuer(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    response = await _callback(client, iss="https://evil.example")

    assert response.headers["Location"] == "/?auth=failed"


async def test_callback_without_a_verifier_fails(client):
    response = await client.get(
        "/api/auth/discord/callback?code=abc&state=whatever"
    )

    assert response.headers["Location"] == "/?auth=failed"


async def test_callback_reports_a_cancelled_authorization(client):
    response = await client.get(
        "/api/auth/discord/callback?error=access_denied"
    )

    assert response.headers["Location"] == "/?auth=cancelled"


async def test_callback_maps_a_discord_refusal_to_failed(
    client, monkeypatch: pytest.MonkeyPatch
):
    async def refuse(method: str, url: str, **kwargs: Any) -> Any:
        del method, url, kwargs
        raise discord_oauth.OAuthError("nope")

    monkeypatch.setattr(discord_oauth, "_fetch_json", refuse)
    await _begin(client)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=failed"


async def test_callback_reports_the_bot_loop_unavailable(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    async def boom() -> set[int]:
        raise RuntimeError("bot loop down")

    monkeypatch.setattr(state, "bot_guild_ids", boom)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=unavailable"


async def test_callback_without_configuration_returns_to_the_panel(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DISCORD_CLIENT_ID", raising=False)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=unconfigured"


async def test_logout_clears_the_session(client):
    async with client.session_transaction() as stored:
        stored["authenticated"] = True

    response = await client.post("/api/logout")

    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {"authenticated": False}
    assert (await _stored(client)).get("authenticated") is not True


async def test_logout_is_reachable_without_a_session(client):
    response = await client.post("/api/logout")

    assert response.status_code == 200
