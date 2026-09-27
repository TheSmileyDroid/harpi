from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
import json
import re

from loguru import logger
from quart import Blueprint, make_response, render_template, request, session
from jinja2_fragments.quart import render_block

from src.bot_state import get_bot
from src.harpi_lib.music.ytmusic import YTMusicData
from src.harpi_lib.parse import parse_finite_float
from src.panel import actions, state

bp = Blueprint("music", __name__)

# htmx sends the HX-Target header (the id from hx-target); renaming an id
# means editing this set and the template together.
_TARGET_BLOCKS: frozenset[str] = frozenset({
    "now_playing",
    "queue",
    "layers",
    "side_panel",
    "selector",
    "status_panels",
    "transport",
    "search",
    "search_dropdown",
})

# Side panel tabs: which fragment the panel shows. The server owns the
# choice, so polls and full-page renders never lose it.
_MUSIC_TABS: frozenset[str] = frozenset({"queue", "layers"})

# Successful confirmations the panel surfaces as transient amber toasts.
# The server declares the event; the client listener in layout.html
# renders it. Errors NEVER appear here — they go to panel_error, red.
_TOAST_MESSAGES: dict[str, str] = {
    "add": "Adicionado à fila",
    "add_layer": "Virou camada",
    "set_volume": "Volume alterado",
    "set_layer_volume": "Volume da camada alterado",
    "seek": "Posição ajustada",
}

# htmx reads this response header and dispatches the event with its
# JSON payload as detail; one body listener renders the toast.
TOAST_EVENT = "harpi:toast"

# A pasted link is the whole term, not a search that happens to contain
# a URL; only then does it bypass the dropdown and go straight to the queue.
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def looks_like_url(term: str) -> bool:
    """True when *term* is one http(s) URL (a pasted link)."""
    return bool(_URL_PATTERN.fullmatch(term.strip()))


def _guild_id() -> int | None:
    raw = session.get("guild_id")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _selected_guild_id(guilds: list[dict[str, Any]]) -> int | None:
    """The cookie's guild id, but only when the bot still sees that guild.

    A stale cookie (the bot left the guild, or the id never existed) must
    not render as a selection nothing can back up: it is cleared here so
    the broken link line never comes back.
    """
    guild_id = _guild_id()
    if guild_id is not None and any(g["id"] == guild_id for g in guilds):
        return guild_id
    session.pop("guild_id", None)
    return None


async def _status() -> dict[str, Any] | None:
    return await state.guild_status(_guild_id())


async def _context() -> dict[str, Any]:
    guilds = await state.list_guilds()
    guild_id = _selected_guild_id(guilds)
    channels: list[dict[str, Any]] = []
    if guild_id is not None:
        channels = state.list_voice_channels(guild_id)
    return {
        "guilds": guilds,
        "selected_guild_id": guild_id,
        "channels": channels,
        "status": await state.guild_status(guild_id),
    }


def _float_value(raw: str | None) -> float:
    value = parse_finite_float(raw)
    if value is None:
        raise ValueError("Valor numérico inválido")
    return value


_STRING_ACTIONS: dict[str, Callable[[int, str | None], Awaitable[Any]]] = {
    "add": actions.add_track,
    "add_layer": actions.add_layer,
    "remove": actions.remove_track,
    "remove_layer": actions.remove_layer,
    "set_loop": actions.set_loop,
}

_NUMERIC_ACTIONS: dict[str, Callable[[int, float | None], Awaitable[Any]]] = {
    "set_volume": actions.set_volume,
    "seek": actions.seek,
}

_SIMPLE_ACTIONS: dict[str, Callable[[int], Awaitable[Any]]] = {
    "toggle_pause": actions.toggle_pause,
    "pause": actions.pause,
    "resume": actions.resume,
    "skip": actions.skip,
    "previous": actions.previous,
    "stop": actions.stop,
    "clear_queue": actions.clear_queue,
    "clear_layers": actions.clear_layers,
}


async def _numeric_or_simple(
    guild_id: int, action: str, value: str | None, form: Any
) -> None:
    numeric = _NUMERIC_ACTIONS.get(action)
    if numeric is not None:
        await numeric(guild_id, _float_value(value) if value else None)
        return
    if action == "set_layer_volume":
        await actions.set_layer_volume(
            guild_id,
            form.get("layer_id") or "",
            _float_value(value) if value else None,
        )
        return
    simple = _SIMPLE_ACTIONS.get(action)
    if simple is not None:
        await simple(guild_id)


async def _session_action(action: str, form: Any) -> str | None:
    """Run the session verb *action* expects; return a panel warning, if any."""
    guild_id = _guild_id()
    if guild_id is None:
        raise ValueError("Nenhum servidor selecionado")
    actions.require_session(guild_id)
    value = form.get("value")
    handler = _STRING_ACTIONS.get(action)
    if handler is not None:
        result = await handler(guild_id, value)
        return result if action == "add" else None
    await _numeric_or_simple(guild_id, action, value, form)
    return None


async def _connect(form: Any) -> None:
    try:
        guild_id = int(form["guild_id"])
        channel_id = int(form["channel_id"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Selecione um servidor e um canal") from None
    # The cookie records the selection only after the connect succeeds, so a
    # failed connect never leaves the panel claiming a session it does not have.
    await actions.connect(guild_id, channel_id)
    session["guild_id"] = str(guild_id)


async def _disconnect() -> None:
    guild_id = _guild_id()
    if guild_id is not None:
        session.pop("guild_id", None)
        await actions.disconnect(guild_id)


def _active_tab() -> str:
    tab = session.get("music_tab")
    return tab if tab in _MUSIC_TABS else "queue"


def _handle_show_tab(form: Any) -> None:
    tab = (form.get("value") or "").strip()
    if tab not in _MUSIC_TABS:
        raise ValueError("Aba inválida")
    session["music_tab"] = tab


def _toast_for(action: str, warning: str | None) -> str | None:
    """The toast message for a successful action, if any. A warning (all
    tracks skipped) speaks for itself, so it suppresses the toast."""
    if warning is not None:
        return None
    return _TOAST_MESSAGES.get(action)


async def _handle_action(
    form: Any,
) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Dispatch one panel action; return results, warning and toast."""
    action = (form.get("action") or "").strip()

    if action == "connect":
        await _connect(form)
    elif action == "disconnect":
        await _disconnect()
    elif action == "show_tab":
        _handle_show_tab(form)
    elif action == "search":
        term = (form.get("value") or "").strip()
        if looks_like_url(term):
            # Pasted URL: no dropdown, straight to the queue with the
            # same play semantics as the add action.
            warning = await _session_action("add", {"value": term})
            return [], warning, _toast_for("add", warning)
        return await actions.search(term, YTMusicData), None, None
    else:
        warning = await _session_action(action, form)
        return [], warning, _toast_for(action, warning)
    return [], None, None


async def _block_or_page(
    block: str | None,
    error: str | None,
    search_results: list[dict[str, Any]],
):
    active_tab = _active_tab()
    if not (block and request.headers.get("HX-Request")):
        return await render_template(
            "pages/music.html",
            error=error,
            search_results=search_results,
            active_tab=active_tab,
            **await _context(),
        )
    if block == "selector":
        return await render_block(
            "pages/music.html",
            block,
            error=error,
            search_results=search_results,
            active_tab=active_tab,
            **await _context(),
        )
    return await render_block(
        "pages/music.html",
        block,
        error=error,
        search_results=search_results,
        active_tab=active_tab,
        status=await _status(),
    )


async def _panel_error_oob(error: str | None) -> str:
    """Render the error region for an out-of-band swap inside a fragment."""
    inner = await render_block("pages/music.html", "panel_error", error=error)
    return f'<div id="panel_error" hx-swap-oob="true">{inner}</div>'


async def _handle_music_post() -> tuple[
    list[dict[str, Any]], str | None, str | None
]:
    """Handle a POST to the music page; return (results, error, toast)."""
    try:
        results, warning, toast = await _handle_action(await request.form)
        return results, warning, toast
    except Exception as e:
        logger.opt(exception=True).warning(f"Panel action failed: {e}")
        error = str(e) if str(e) else type(e).__name__
        return [], error, None


async def _render_music_response(
    block: str | None,
    error: str | None,
    search_results: list[dict[str, Any]],
) -> str:
    """Render the music page or fragment, attaching the OOB error on POSTs."""
    response = await _block_or_page(block, error, search_results)
    if (
        request.method == "POST"
        and block
        and request.headers.get("HX-Request")
    ):
        response += await _panel_error_oob(error)
    return response


@bp.route("/music", methods=["GET", "POST"])
async def music():
    guild_id = request.args.get("guild_id")
    if guild_id:
        # Only a guild the bot can see may become the selection; an
        # unknown id in the URL must not poison the cookie.
        try:
            if get_bot().get_guild(int(guild_id)) is not None:
                session["guild_id"] = guild_id
        except ValueError:
            pass
    error: str | None = None
    search_results: list[dict[str, Any]] = []
    toast: str | None = None
    if request.method == "POST":
        search_results, error, toast = await _handle_music_post()
    hx_target = request.headers.get("HX-Target", "")
    block = None
    if hx_target in _TARGET_BLOCKS:
        block = hx_target
    response = await _render_music_response(block, error, search_results)
    if toast is None:
        return response
    # Server-driven toast: htmx reads the header and dispatches the
    # event with the message as detail. Never set on failures — they
    # stay in panel_error, red and persistent.
    declared = await make_response(response)
    declared.headers["HX-Trigger"] = json.dumps({
        TOAST_EVENT: {"message": toast}
    })
    return declared
