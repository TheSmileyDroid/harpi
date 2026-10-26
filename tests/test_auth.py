"""Discord OAuth panel authentication over the app's HTTP seam.

The Discord network is faked at ``discord_oauth._fetch_json``; the bot is a
fake, so the allowlist admission runs through the real ``state.bot_guild_ids``
and the real registry.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
from typing import Any, cast

import pytest

from app import app as quart_app
from app import configure_panel_session
from src import bot_state as deps
from src import discord_oauth
from src.config import Settings
from src.harpi_lib.harpi_bot import HarpiBot
from src.panel import login, state
from tests.fakes import GUILD_A, GUILD_B, FakeBot, FakeGuild

CLIENT_ID = "891732797054681119"
SECRET = "test-secret"
STATE = "the-state-nonce"
VERIFIER = "the-code-verifier"
ALLOWLIST = f"{GUILD_A},{GUILD_B}"
ABSENT_GUILD = 3


class AuthBot(FakeBot):
    def is_ready(self) -> bool:
        return True

    def is_closed(self) -> bool:
        return False


@pytest.fixture
def client(storage, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.setenv("DISCORD_TOKEN", "test")
    monkeypatch.setenv("DISCORD_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("PANEL_GUILD_ALLOWLIST", ALLOWLIST)
    monkeypatch.delenv("DISCORD_REDIRECT_URI", raising=False)
    monkeypatch.delenv("PANEL_INSECURE_COOKIES", raising=False)
    configure_panel_session(Settings.from_env())
    quart_app.config["TESTING"] = True
    deps.init_bot(
        cast(
            HarpiBot,
            AuthBot([
                FakeGuild(GUILD_A, "Alpha Guild"),
                FakeGuild(GUILD_B, "Beta Guild"),
            ]),
        )
    )
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


def _cookie(response, name: str) -> Any:
    for header in response.headers.getlist("Set-Cookie"):
        jar = SimpleCookie()
        jar.load(header)
        if name in jar:
            return jar[name]
    raise AssertionError(f"no {name} cookie in {response.headers}")


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


async def test_callback_opens_a_session_for_an_allowlisted_member(
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
    assert await state.user_guild_ids("555") == frozenset({GUILD_A})


async def test_login_issues_a_host_only_secure_cookie(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    response = await _callback(client)

    morsel = _cookie(response, login.STRICT_COOKIE_NAME)
    assert morsel["secure"] is True
    assert morsel["httponly"] is True
    assert morsel["samesite"] == "Lax"
    assert morsel["path"] == "/"
    assert morsel["domain"] == ""


async def test_login_cookie_expires_in_seven_days(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    response = await _callback(client)

    morsel = _cookie(response, login.STRICT_COOKIE_NAME)
    expires = parsedate_to_datetime(morsel["expires"])
    remaining = expires - datetime.now(UTC)
    assert timedelta(days=7) - timedelta(minutes=5) <= remaining
    assert remaining <= timedelta(days=7) + timedelta(minutes=5)


async def test_an_authenticated_read_does_not_reissue_the_cookie(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)
    await _callback(client)

    response = await client.get("/api/session")

    assert response.status_code == 200
    assert response.headers.getlist("Set-Cookie") == []


async def test_callback_replaces_the_previous_login(
    client, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    async with client.session_transaction() as stored:
        stored["oauth_state"] = STATE
        stored["oauth_verifier"] = VERIFIER
        stored["authenticated"] = True
        stored["user_id"] = "999"
        stored["username"] = "previous-user"
        stored["guild_id"] = str(GUILD_A)
        stored[login.LOGIN_EPOCH_KEY] = 7

    response = await _callback(client)

    stored = await _stored(client)
    assert stored["user_id"] == "555"
    assert stored["username"] == "harpi-user"
    assert "guild_id" not in stored
    assert stored[login.LOGIN_EPOCH_KEY] == 0
    assert isinstance(stored[login.ISSUED_AT_KEY], int)
    _cookie(response, login.STRICT_COOKIE_NAME)


async def test_logout_revokes_a_replayed_cookie(
    client, storage, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)
    await _callback(client)
    old = next(
        cookie.value
        for cookie in client.cookie_jar
        if cookie.name == login.STRICT_COOKIE_NAME
    )
    assert await storage.login_epoch("555") == 0

    response = await client.post("/api/logout")

    assert response.status_code == 200
    assert await storage.login_epoch("555") == 1
    replay = quart_app.test_client()
    replayed = await replay.get(
        "/api/session",
        headers={"Cookie": f"{login.STRICT_COOKIE_NAME}={old}"},
    )
    assert replayed.status_code == 401


async def test_login_after_logout_adopts_the_current_epoch(
    client, storage, monkeypatch: pytest.MonkeyPatch
):
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)
    await _callback(client)
    await client.post("/api/logout")

    await _begin(client)
    response = await _callback(client)

    assert response.status_code == 302
    assert (await _stored(client))[login.LOGIN_EPOCH_KEY] == 1
    session_check = await client.get("/api/session")
    assert session_check.status_code == 200


@pytest.mark.parametrize("guild_id", [GUILD_A, GUILD_B])
async def test_callback_admits_a_member_of_each_allowlisted_guild(
    client, monkeypatch: pytest.MonkeyPatch, guild_id: int
):
    fake_discord(monkeypatch, [guild_id])
    await _begin(client)

    response = await _callback(client)

    assert response.headers["Location"] == "/"
    assert (await _stored(client))["authenticated"] is True
    assert await state.user_guild_ids("555") == frozenset({guild_id})


async def test_callback_denies_a_member_of_a_guild_outside_the_allowlist(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PANEL_GUILD_ALLOWLIST", str(GUILD_A))
    fake_discord(monkeypatch, [GUILD_B])
    await _begin(client)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=denied"
    assert (await _stored(client)).get("authenticated") is not True
    assert await state.user_guild_ids("555") == frozenset()


async def test_callback_denies_a_member_of_an_allowlisted_guild_the_bot_is_not_in(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PANEL_GUILD_ALLOWLIST", f"{GUILD_A},{ABSENT_GUILD}")
    fake_discord(monkeypatch, [ABSENT_GUILD])
    await _begin(client)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=denied"
    assert (await _stored(client)).get("authenticated") is not True
    assert await state.user_guild_ids("555") == frozenset()


async def test_callback_denies_everyone_when_the_allowlist_is_empty(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PANEL_GUILD_ALLOWLIST", "")
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=denied"
    assert (await _stored(client)).get("authenticated") is not True
    assert await state.user_guild_ids("555") == frozenset()


async def test_callback_denies_everyone_when_the_allowlist_is_malformed(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PANEL_GUILD_ALLOWLIST", f"{GUILD_A},not-a-snowflake")
    fake_discord(monkeypatch, [GUILD_A])
    await _begin(client)

    response = await _callback(client)

    assert response.headers["Location"] == "/?auth=denied"
    assert (await _stored(client)).get("authenticated") is not True
    assert await state.user_guild_ids("555") == frozenset()


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


async def test_insecure_cookies_drop_secure_and_the_host_prefix(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PANEL_INSECURE_COOKIES", "1")
    configure_panel_session(Settings.from_env())
    try:
        fake_discord(monkeypatch, [GUILD_A])
        await _begin(client)

        response = await _callback(client)

        morsel = _cookie(response, login.LOCAL_COOKIE_NAME)
        assert not morsel["secure"]
        assert morsel["httponly"] is True
        assert morsel["samesite"] == "Lax"
        assert morsel["path"] == "/"
        assert morsel["domain"] == ""
    finally:
        monkeypatch.delenv("PANEL_INSECURE_COOKIES", raising=False)
        configure_panel_session(Settings.from_env())
