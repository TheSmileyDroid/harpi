"""Discord OAuth2: the authorization code grant with PKCE.

A public client, so no client secret is stored. PKCE proves the code
exchange. Discord advertises ``S256`` in its discovery document and
accepts the ``none`` token auth method.

DOC: https://docs.discord.com/developers/topics/oauth2
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any
from urllib.parse import urlencode

import aiohttp

AUTHORIZE_ENDPOINT = "https://discord.com/oauth2/authorize"
TOKEN_ENDPOINT = "https://discord.com/api/oauth2/token"
USER_ENDPOINT = "https://discord.com/api/users/@me"
GUILDS_ENDPOINT = "https://discord.com/api/users/@me/guilds"
SCOPES = "identify guilds"
GUILDS_PAGE = 200


class OAuthError(RuntimeError):
    """The Discord side refused the exchange."""


def _urlsafe(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def new_state() -> str:
    return secrets.token_urlsafe(32)


def new_verifier() -> str:
    return _urlsafe(secrets.token_bytes(64))


def challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return _urlsafe(digest)


def authorize_url(
    client_id: str, redirect_uri: str, state: str, challenge: str
) -> str:
    query = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "scope": SCOPES,
        "state": state,
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "consent",
    })
    return f"{AUTHORIZE_ENDPOINT}?{query}"


async def _fetch_json(method: str, url: str, **kwargs: Any) -> Any:
    try:
        async with (
            aiohttp.ClientSession() as http,
            http.request(method, url, **kwargs) as response,
        ):
            if response.status >= 400:
                raise OAuthError(await response.text())
            return await response.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as error:
        raise OAuthError(str(error)) from error


async def exchange_code(
    client_id: str, redirect_uri: str, code: str, verifier: str
) -> dict[str, Any]:
    payload = await _fetch_json(
        "POST",
        TOKEN_ENDPOINT,
        data={
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
    )
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise OAuthError("token response carried no access_token")
    return payload


async def fetch_user(access_token: str) -> dict[str, Any]:
    return await _fetch_json(
        "GET",
        USER_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
    )


async def fetch_guild_ids(access_token: str) -> set[int]:
    headers = {"Authorization": f"Bearer {access_token}"}
    ids: set[int] = set()
    after = 0
    while True:
        page = await _fetch_json(
            "GET",
            GUILDS_ENDPOINT,
            headers=headers,
            params={"limit": GUILDS_PAGE, "after": after},
        )
        if not page:
            return ids
        page_ids = [int(guild["id"]) for guild in page]
        ids.update(page_ids)
        after = max(page_ids)
        if len(page) < GUILDS_PAGE:
            return ids
