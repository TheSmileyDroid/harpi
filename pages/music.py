from typing import Any
from collections.abc import Callable
import json
import re

from discord import Guild
from loguru import logger
from quart import Blueprint, make_response, render_template, request, session
from jinja2_fragments.quart import render_block

from src.bot_state import get_bot, run_on_bot_loop
from src.harpi_lib.audio.session import (
    LOOP_MODE_ALIASES,
    LoopMode,
    PlaybackSession,
)
from src.harpi_lib.music.ytmusic import YTMusicData
from src.harpi_lib.parse import parse_finite_float

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

_SESSION_VERBS: frozenset[str] = frozenset({
    "toggle_pause",
    "skip",
    "previous",
    "stop",
    "clear_queue",
    "clear_layers",
})

_SESSION_VALUE_VERBS: dict[str, str] = {
    "remove": "remove",
    "remove_layer": "remove_layer",
    "add": "play",
    "add_layer": "add_layer",
}

SEARCH_RESULT_LIMIT = 5

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


# Shown after an add that left the session with nothing playing and an
# empty queue: every track was skipped while loading and the reason only
# reached the Discord channel, so the panel must speak up too.
_ALL_SKIPPED_WARNING = (
    "As faixas foram adicionadas, mas nenhuma pôde ser tocada. "
    "O motivo foi anunciado no canal do Discord."
)


async def _collect_guilds(bot) -> list[Guild]:
    """Collect guilds from the bot's async generator (runs on bot loop)."""
    return [guild async for guild in bot.fetch_guilds(limit=150)]


async def _get_guilds() -> list[Guild]:
    """Return every guild the bot can see, fresh on each call."""
    bot = get_bot()
    return await run_on_bot_loop(_collect_guilds(bot))


def _guild_id() -> int | None:
    raw = session.get("guild_id")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _guild_id_in(guilds: list[Guild]) -> int | None:
    """The cookie's guild id, but only when the bot still sees that guild.

    A stale cookie (the bot left the guild, or the id never existed) must
    not render as a selection nothing can back up: it is cleared here so
    the broken link line never comes back.
    """
    guild_id = _guild_id()
    if guild_id is not None and any(g.id == guild_id for g in guilds):
        return guild_id
    session.pop("guild_id", None)
    return None


async def _status():
    bot = get_bot()
    guild_id = _guild_id()
    if guild_id is None:
        return None
    session_obj = bot.sessions.get(guild_id)
    if session_obj is None:
        return None
    return await run_on_bot_loop(session_obj.sample_status())


async def _context() -> dict:
    bot = get_bot()
    guild_list = await _get_guilds()
    guild_id = _guild_id_in(guild_list)
    channels = []
    if guild_id is not None:
        guild = bot.get_guild(guild_id)
        if guild:
            channels = guild.voice_channels
    return {
        "guilds": guild_list,
        "selected_guild_id": guild_id,
        "channels": channels,
        "status": await _status(),
    }


def _float_value(raw: str | None) -> float:
    value = parse_finite_float(raw)
    if value is None:
        raise ValueError("Valor numérico inválido")
    return value


def _loop_mode(value: str) -> LoopMode:
    mode = LOOP_MODE_ALIASES.get(value)
    if mode is None:
        raise ValueError("Modo de loop inválido")
    return mode


# Verbs whose single form value must arrive at the session as a float,
# with how the value maps to the session call. The panel bar clicks a
# point on the track, so seek speaks absolute seconds; the panel rejects
# targets outside 0..duration and the session clamps whatever is left.
_NUMERIC_VERBS: dict[str, tuple[str, Callable[[str], float]]] = {
    "set_volume": ("set_volume", _float_value),
    "seek": ("seek", _float_value),
}


def _numeric_call(session_obj: PlaybackSession, action: str, value: str):
    verb, coerce = _NUMERIC_VERBS[action]
    target = coerce(value)
    if action == "seek":
        return session_obj.seek(target, absolute=True)
    return getattr(session_obj, verb)(target)


def _custom_verb_call(session_obj: PlaybackSession, action: str, form: Any):
    """Coroutine for the verbs whose form mapping is not a plain name."""
    value = form.get("value")
    if action == "set_loop" and value:
        return session_obj.set_loop(_loop_mode(value))
    if action == "set_layer_volume" and value:
        return session_obj.set_layer_volume(
            form.get("layer_id") or "", _float_value(value)
        )
    return None


def _verb_call(session_obj: PlaybackSession, action: str, form: Any):
    """Resolve *action* to the session coroutine to run, or None."""
    value = form.get("value")
    if action in _SESSION_VERBS:
        return getattr(session_obj, action)()
    if action in _SESSION_VALUE_VERBS and value:
        return getattr(session_obj, _SESSION_VALUE_VERBS[action])(value)
    if action in _NUMERIC_VERBS and value:
        return _numeric_call(session_obj, action, value)
    return _custom_verb_call(session_obj, action, form)


async def _run_session_verb(
    session_obj: PlaybackSession, action: str, form: Any
) -> None:
    """Run the session verb *action* expects, adapting the form values."""
    call = _verb_call(session_obj, action, form)
    if call is not None:
        await run_on_bot_loop(call)


async def _reject_seek_out_of_range(
    session_obj: PlaybackSession, form: Any
) -> None:
    """Reject an absolute seek outside 0..duration before it runs.

    The session clamps internally (the Discord command relies on that),
    but a panel POST outside the range means a stale duration on the
    client, so it gets an error instead of a silent snap.
    """
    value = form.get("value") or ""
    if not value:
        return
    target = _float_value(value)
    status = await run_on_bot_loop(session_obj.sample_status())
    current = status.current_music if status else None
    duration = current.duration if current else 0
    if duration and not 0 <= target <= duration:
        raise ValueError("Posição fora da duração da faixa")


async def _dispatch_session_action(
    session_obj: PlaybackSession, action: str, form: Any
) -> str | None:
    """Run the session verb for *action*; return a panel warning, if any."""
    if action == "seek":
        await _reject_seek_out_of_range(session_obj, form)
    await _run_session_verb(session_obj, action, form)
    if action == "add":
        return await _skipped_tracks_warning(session_obj)
    return None


async def _skipped_tracks_warning(session_obj: PlaybackSession) -> str | None:
    """Warn when an add left the session idle: play awaits the first
    advance before returning, so idle here means every track was skipped."""
    status = await run_on_bot_loop(session_obj.sample_status())
    if status.current_music is None and not status.queue:
        return _ALL_SKIPPED_WARNING
    return None


async def _handle_session_action(
    bot: Any, form: Any, action: str
) -> str | None:
    guild_id = _guild_id()
    if guild_id is None:
        raise ValueError("Nenhum servidor selecionado")
    session_obj = bot.sessions.get(guild_id)
    if session_obj is None:
        raise ValueError("Não conectado a um canal de voz")
    return await _dispatch_session_action(session_obj, action, form)


async def _handle_search(form: Any) -> list[YTMusicData]:
    """Resolve a search term or URL into the results the panel lists.

    Runs on the web loop on purpose: yt-dlp work happens in an executor,
    so nothing here touches discord.py internals.
    """
    term = (form.get("value") or "").strip()
    if not term:
        return []
    results = await YTMusicData.from_url(term)
    if not results:
        raise ValueError("Nenhuma música encontrada para esta busca")
    return results[:SEARCH_RESULT_LIMIT]


async def _handle_connect(bot: Any, form) -> None:
    try:
        guild_id = int(form["guild_id"])
        channel_id = int(form["channel_id"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Selecione um servidor e um canal") from None
    # The cookie records the selection only after the connect succeeds, so a
    # failed connect never leaves the panel claiming a session it does not have.
    await run_on_bot_loop(bot.sessions.connect(guild_id, channel_id))
    session["guild_id"] = str(guild_id)


async def _handle_disconnect(bot: Any) -> None:
    guild_id = _guild_id()
    if guild_id is not None:
        session.pop("guild_id", None)
        await run_on_bot_loop(bot.sessions.disconnect(guild_id))


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
) -> tuple[list[YTMusicData], str | None, str | None]:
    """Dispatch one panel action; return results, warning and toast."""
    action = (form.get("action") or "").strip()
    bot = get_bot()

    if action == "connect":
        await _handle_connect(bot, form)
    elif action == "disconnect":
        await _handle_disconnect(bot)
    elif action == "show_tab":
        _handle_show_tab(form)
    elif action == "search":
        term = (form.get("value") or "").strip()
        if looks_like_url(term):
            # Pasted URL: no dropdown, straight to the queue with the
            # same play semantics as the add action.
            warning = await _handle_session_action(bot, {"value": term}, "add")
            return [], warning, _toast_for("add", warning)
        return await _handle_search(form), None, None
    else:
        warning = await _handle_session_action(bot, form, action)
        return [], warning, _toast_for(action, warning)
    return [], None, None


async def _block_or_page(
    block: str | None,
    error: str | None,
    search_results: list[YTMusicData],
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
    list[YTMusicData], str | None, str | None
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
    search_results: list[YTMusicData],
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
    search_results: list[YTMusicData] = []
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
