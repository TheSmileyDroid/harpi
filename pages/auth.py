from __future__ import annotations

from typing import Any

from loguru import logger
from quart import Blueprint, redirect, request, session
from quart_schema import validate_response

from src import discord_oauth
from src.config import Settings
from src.panel import state
from src.panel.schemas import Authenticated
from src.storage.registry import Actor

bp = Blueprint("auth", __name__)

LOGIN_PATH = "/api/auth/discord"
CALLBACK_PATH = "/api/auth/discord/callback"
LOGOUT_PATH = "/api/logout"
PANEL_PATH = "/"
ISSUER = "https://discord.com"


def _back_to_panel(reason: str | None = None) -> str:
    return PANEL_PATH if reason is None else f"{PANEL_PATH}?auth={reason}"


@bp.get(LOGIN_PATH)
def discord_login():
    settings = Settings.from_env()
    client_id = settings.discord_client_id
    if not client_id:
        return redirect(_back_to_panel("unconfigured"))
    verifier = discord_oauth.new_verifier()
    state_token = discord_oauth.new_state()
    session["oauth_state"] = state_token
    session["oauth_verifier"] = verifier
    return redirect(
        discord_oauth.authorize_url(
            client_id,
            settings.discord_redirect_uri,
            state_token,
            discord_oauth.challenge_for(verifier),
        )
    )


def _valid_callback() -> tuple[str, str] | None:
    expected = session.pop("oauth_state", None)
    verifier = session.pop("oauth_verifier", None)
    issuer = request.args.get("iss")
    code = request.args.get("code")
    if issuer not in (None, ISSUER):
        return None
    if not code or not expected or not verifier:
        return None
    if request.args.get("state") != expected:
        return None
    return code, verifier


async def _admitted_user(
    client_id: str, redirect_uri: str, code: str, verifier: str
) -> dict[str, Any] | None:
    token = await discord_oauth.exchange_code(
        client_id, redirect_uri, code, verifier
    )
    user = await discord_oauth.fetch_user(token["access_token"])
    user_guilds = await discord_oauth.fetch_guild_ids(token["access_token"])
    if not user_guilds & await state.bot_guild_ids():
        return None
    return user


@bp.get(CALLBACK_PATH)
async def discord_callback():
    settings = Settings.from_env()
    client_id = settings.discord_client_id
    if not client_id:
        return redirect(_back_to_panel("unconfigured"))
    if request.args.get("error"):
        return redirect(_back_to_panel("cancelled"))
    credentials = _valid_callback()
    if credentials is None:
        return redirect(_back_to_panel("failed"))
    code, verifier = credentials
    try:
        user = await _admitted_user(
            client_id, settings.discord_redirect_uri, code, verifier
        )
    except (discord_oauth.OAuthError, KeyError, TypeError):
        return redirect(_back_to_panel("failed"))
    except Exception:
        return redirect(_back_to_panel("unavailable"))
    if user is None:
        return redirect(_back_to_panel("denied"))
    await _establish_session(user)
    return redirect(_back_to_panel())


async def _establish_session(user: dict[str, Any]) -> None:
    user_id = str(user.get("id"))
    username = str(user.get("username") or user_id)
    display_name = user.get("global_name")
    session.permanent = True
    session["authenticated"] = True
    session["user_id"] = user_id
    session["username"] = username
    session["display_name"] = display_name or ""
    try:
        await state.sign_in(
            Actor(
                id=user_id,
                username=username,
                display_name=display_name,
            )
        )
    except Exception:
        logger.opt(exception=True).error(
            "Could not record panel sign-in in storage"
        )


@bp.post(LOGOUT_PATH)
@validate_response(Authenticated, 200)
async def logout():
    user_id = session.get("user_id")
    if user_id:
        try:
            await state.leave(str(user_id))
        except Exception:
            logger.opt(exception=True).error(
                "Could not clear panel presence in storage"
            )
    session.clear()
    return {"authenticated": False}
