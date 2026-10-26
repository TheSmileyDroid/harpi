from __future__ import annotations

from typing import Any

from loguru import logger
from quart import Blueprint, redirect, request, session
from quart_schema import validate_response

from src import discord_oauth
from src.config import Settings
from src.panel import login, state
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
    client_id: str,
    redirect_uri: str,
    code: str,
    verifier: str,
    allowlist: frozenset[int],
) -> tuple[dict[str, Any], frozenset[int]] | None:
    if not allowlist:
        return None
    token = await discord_oauth.exchange_code(
        client_id, redirect_uri, code, verifier
    )
    user = await discord_oauth.fetch_user(token["access_token"])
    user_guilds = await discord_oauth.fetch_guild_ids(token["access_token"])
    allowed = user_guilds & allowlist & await state.bot_guild_ids()
    if not allowed:
        return None
    return user, frozenset(allowed)


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
        admission = await _admitted_user(
            client_id,
            settings.discord_redirect_uri,
            code,
            verifier,
            settings.guild_allowlist,
        )
    except (discord_oauth.OAuthError, KeyError, TypeError):
        return redirect(_back_to_panel("failed"))
    except Exception:
        return redirect(_back_to_panel("unavailable"))
    if admission is None:
        return redirect(_back_to_panel("denied"))
    user, allowed_guilds = admission
    session.clear()
    await _establish_session(user, allowed_guilds)
    return redirect(_back_to_panel())


async def _record_sign_in(
    actor: Actor, allowed_guilds: frozenset[int]
) -> int | None:
    try:
        await state.sign_in(actor)
        await state.record_user_guilds(actor, allowed_guilds)
        return await state.login_epoch(actor.id)
    except Exception:
        logger.opt(exception=True).error(
            "Could not record panel sign-in in storage"
        )
        return None


async def _establish_session(
    user: dict[str, Any], allowed_guilds: frozenset[int]
) -> None:
    user_id = str(user.get("id"))
    username = str(user.get("username") or user_id)
    display_name = user.get("global_name")
    actor = Actor(
        id=user_id,
        username=username,
        display_name=display_name,
    )
    epoch = await _record_sign_in(actor, allowed_guilds)
    session.permanent = True
    session["authenticated"] = True
    session["user_id"] = user_id
    session["username"] = username
    session["display_name"] = display_name or ""
    session[login.ISSUED_AT_KEY] = login.now()
    session[login.LOGIN_EPOCH_KEY] = epoch


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
        try:
            await state.increment_login_epoch(str(user_id))
        except Exception:
            logger.opt(exception=True).error(
                "Could not revoke panel logins in storage"
            )
    session.clear()
    return {"authenticated": False}
