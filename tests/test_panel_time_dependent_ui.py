"""Gates for time-dependent panel behavior.

Pollers swap DOM every few seconds, so a bad swap is invisible in a single
request/response test: it only shows up as lost input, closed dropdowns, or
whole-screen fades when the page sits open.  These tests render the real
templates and assert the swap structure so those failure classes stay dead.

History: the status_panels poller once replaced the queue search input every
2s (typed text wiped), and htmx globalViewTransitions plus the root fade CSS
made every poll fade the entire page ~1.5x per second.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast

# pi-lens-ignore: reportMissingImports
import pytest

# Reuse the fakes and fixtures from the page tests so all suites render
# the same pages the same way.  bot must be imported by its own name so the
# aliased client fixture's dependency chain resolves from this module.
from test_index_page import FakeBot as IndexFakeBot

from test_index_page import client as index_client

# bot is resolved through this module's namespace (the aliased music client
# fixture depends on it); it is never called directly here.
# ruff: ignore[unused-import]
from test_music_page import GUILD_A, bot, client as music_client
from src import bot_state as deps
from src.harpi_lib.harpi_bot import HarpiBot

# Which fake client renders which page.  The fixture objects are registered
# with pytest under their import aliases and resolved by name through
# getfixturevalue; the identity check in _fixture_name keeps the strings
# honest if an alias ever changes.
_CLIENT_FOR_PAGE: dict[str, Any] = {
    "/": index_client,
    "/music": music_client,
    f"/music?guild_id={GUILD_A}": music_client,
}


def _fixture_name(client_obj: Any) -> str:
    if client_obj is music_client:
        return "music_client"
    assert client_obj is index_client
    return "index_client"


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

VOID_TAGS = frozenset({
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
})

INTERACTIVE_TAGS = frozenset({"input", "select", "textarea"})


class _Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: Any):
        self.tag = tag
        self.attrs = attrs
        self.parent: _Node | None = parent
        self.children: list[_Node] = []


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root = _Node("#root", {}, None)
        self._stack = [self.root]

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        node = _Node(tag, {k: v or "" for k, v in attrs}, self._stack[-1])
        self._stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return


def _parse(html: str) -> _Node:
    builder = _TreeBuilder()
    builder.feed(html)
    return builder.root


def _walk(node: _Node, include_self: bool = False):
    if include_self:
        yield node
    for child in node.children:
        yield child
        yield from _walk(child)


def _find_by_id(root: _Node, element_id: str) -> _Node | None:
    for node in _walk(root):
        if node.attrs.get("id") == element_id:
            return node
    return None


def _pollers(root: _Node) -> list[_Node]:
    return [
        node
        for node in _walk(root)
        if "every" in node.attrs.get("hx-trigger", "")
    ]


def _swap_scope(root: _Node, poller: _Node) -> list[_Node]:
    target_id = poller.attrs.get("hx-target", "").lstrip("#")
    region = _find_by_id(root, target_id) if target_id else poller
    if region is None:
        return []
    swap = poller.attrs.get("hx-swap", "innerHTML")
    include_self = swap.startswith("outerHTML")
    return list(_walk(region, include_self=include_self))


def _is_preserved(node: _Node) -> bool:
    current: _Node | None = node
    while current is not None:
        if "hx-preserve" in current.attrs and current.attrs.get("id"):
            return True
        current = current.parent
    return False


def _live_controls(scope: list[_Node]) -> list[_Node]:
    found = []
    for node in scope:
        if node.tag not in INTERACTIVE_TAGS:
            continue
        if node.tag == "input" and node.attrs.get("type") == "hidden":
            continue
        found.append(node)
    return found


@pytest.mark.parametrize(
    "page", list(_CLIENT_FOR_PAGE), ids=list(_CLIENT_FOR_PAGE)
)
async def test_poll_swaps_never_destroy_interactive_controls(request, page):
    fixture_name = _fixture_name(_CLIENT_FOR_PAGE[page])
    api_client = request.getfixturevalue(fixture_name)
    if page == "/":
        deps.init_bot(cast(HarpiBot, IndexFakeBot(ready=True, closed=False)))
    response = await api_client.get(page)
    assert response.status_code == 200
    body = (await response.get_data()).decode()
    root = _parse(body)

    for poller in _pollers(root):
        scope = _swap_scope(root, poller)
        for control in _live_controls(scope):
            assert _is_preserved(control), (
                f"poller <{poller.tag} hx-trigger={poller.attrs['hx-trigger']!r}> "
                f"swaps the region containing <{control.tag} {control.attrs}> "
                f"without hx-preserve; every poll cycle would wipe whatever "
                f"the user typed or selected there. Page: {page}"
            )


async def test_search_dropdown_lives_outside_every_poller_swap_scope(
    music_client,
):
    response = await music_client.get(f"/music?guild_id={GUILD_A}")
    assert response.status_code == 200
    body = (await response.get_data()).decode()
    root = _parse(body)

    for poller in _pollers(root):
        scope_ids = {
            node.attrs.get("id") for node in _swap_scope(root, poller)
        }
        assert "search-input" not in scope_ids, (
            f"poller <{poller.attrs['hx-trigger']!r}> swaps the search "
            "input region; every poll would close the dropdown and wipe "
            "the query being typed."
        )
        assert "search_dropdown" not in scope_ids, (
            f"poller <{poller.attrs['hx-trigger']!r}> swaps the search "
            "dropdown region; every poll would kill the open dropdown."
        )


def test_htmx_global_view_transitions_stay_off():
    layout = (TEMPLATES_DIR / "layout.html").read_text()
    meta = re.search(
        r"<meta\s+name=\"htmx-config\"\s+content='([^']*)'", layout
    )
    if meta is None:
        return
    config = json.loads(meta.group(1))
    assert not config.get("globalViewTransitions"), (
        "globalViewTransitions makes EVERY htmx swap (including the 2s "
        "pollers) run a full-page view transition; with the root fade CSS "
        "the whole screen flickers on each poll. Cross-document navigation "
        "transitions via @view-transition CSS are unaffected."
    )


def _progress_seek_script() -> str:
    music = (TEMPLATES_DIR / "pages" / "music.html").read_text()
    match = re.search(
        r'<script id="progress-seek-script">(.*?)</script>', music, re.S
    )
    assert match is not None, "progress-seek-script vanished from the page"
    return match.group(1)


def test_seek_gesture_fires_exactly_one_absolute_seek():
    # Seek restarts FFmpeg ("music does not die while playing"), so a
    # drag must produce ONE absolute seek, on release — never per move.
    # The page is hypermedia-first: the server already gates each POST
    # (test_seek_posts_an_absolute_position); this gate pins the client
    # half, which only exists as this inline script.
    script = _progress_seek_script()

    assert script.count("htmx.ajax(") == 1, (
        "the seek script must hold exactly one htmx.ajax call, fired "
        "only on pointerup; any other call site risks continuous seeking"
    )
    assert "pointerup" in script
    move_block = re.search(
        r'addEventListener\("pointermove", \(evt\) => \{(.*?)\}\);',
        script,
        re.S,
    )
    assert move_block is not None, "drag preview lost"
    assert "htmx.ajax" not in move_block.group(1), (
        "pointermove must never touch the backend; it only paints the "
        "preview (no seek calls during the drag)"
    )


def _volume_slider_script() -> str:
    music = (TEMPLATES_DIR / "pages" / "music.html").read_text()
    match = re.search(
        r'<script id="volume-slider-script">(.*?)</script>', music, re.S
    )
    assert match is not None, "volume-slider-script vanished from the page"
    return match.group(1)


def test_volume_drag_posts_through_the_debounced_channel_only():
    # Dragging fires `input` dozens of times; set_volume must be hit
    # through the throttled+debounced scheduler, never per input event.
    # The page is hypermedia-first: the server already gates each POST
    # (test_volume_rejects_non_finite_values); this gate pins the client
    # half, which only exists as this inline script.
    script = _volume_slider_script()

    assert script.count("htmx.ajax(") == 1, (
        "the volume script must hold exactly one htmx.ajax call site, "
        "reached only through the debounced scheduler"
    )
    assert "setTimeout" in script and "clearTimeout" in script, (
        "the debounced trailing send must exist; without it a fast drag "
        "hammers the endpoint with one POST per input event"
    )
    input_block = re.search(
        r'addEventListener\("input", \(evt\) => \{(.*?)\}\);',
        script,
        re.S,
    )
    assert input_block is not None, "input handler lost"
    assert "htmx.ajax" not in input_block.group(1), (
        "the input handler must only paint the preview and schedule the "
        "send; it must never post directly"
    )


def test_volume_preview_paints_locally():
    script = _volume_slider_script()

    assert "volume-value" in script, (
        "the drag preview rewrites the volume-value readout; if the "
        "template loses it the preview goes silent"
    )


def test_drag_preview_paints_locally_and_holds_the_transport_poll():
    script = _progress_seek_script()

    assert "pointerdown" in script
    assert "progress-times" in script, (
        "the drag preview rewrites the progress-times span; if the "
        "template loses it the preview goes silent"
    )
    assert 'id === "transport"' in script and "htmx:beforeRequest" in script, (
        "the transport poll must be cancelled while a drag is live, or "
        "the 500ms swap snaps the bar back under the pointer"
    )
    assert 'addEventListener("click"' not in script, (
        "a click handler alongside the pointer handlers would fire a "
        "second seek right after pointerup"
    )


def _dialog_script() -> str:
    music = (TEMPLATES_DIR / "pages" / "music.html").read_text()
    match = re.search(
        r'<script id="dialog-script">(.*?)</script>', music, re.S
    )
    assert match is not None, "dialog-script vanished from the page"
    return match.group(1)


def test_confirm_gate_holds_the_first_submit_and_replays_on_confirm():
    # The dialog is a client gate only: the first submit is held, and
    # confirming replays the SAME form untouched (requestSubmit), so the
    # server still receives the original action through its original
    # form — the script never posts on its own behalf.
    script = _dialog_script()

    assert "data-confirm" in script, (
        "the gate must key off the form's server-rendered data-confirm"
    )
    assert "preventDefault" in script and "stopPropagation" in script, (
        "the first submit must be held before htmx (capture phase) or "
        "the destructive action fires without confirmation"
    )
    assert "requestSubmit" in script, (
        "confirmation must replay the original form, keeping hx-target "
        "and the out-of-band error swap intact"
    )
    assert "showModal" in script, (
        "showModal is what traps focus while the dialog is open"
    )


def test_dialogs_close_on_backdrop_and_successful_posts():
    script = _dialog_script()

    assert "evt.target === dialog" in script, (
        "clicking the backdrop must close the dialog, like Esc"
    )
    assert 'hasAttribute("data-close-on-success")' in script, (
        "a successful post from inside a dialog re-renders server "
        "state; the dialog must close itself"
    )


def test_layer_dialog_opens_filled_from_the_server_row():
    script = _dialog_script()

    assert "[data-layer-open]" in script
    assert "dataset.layerId" in script
    assert "dataset.layerVolume" in script, (
        "the slider must open at the layer's server-rendered volume"
    )


def test_volume_script_serves_both_sliders_through_the_form():
    # The layer detail slider rides the same debounced channel as the
    # transport slider: action and swap target come from the slider's
    # own form, so one call site serves set_volume and set_layer_volume.
    script = _volume_slider_script()

    assert 'closest("form")' in script
    assert "FormData" in script, (
        "the posted values must come from the slider's form, not a "
        "hardcoded action"
    )
    assert 'form.getAttribute("hx-post")' in script, (
        "the endpoint and swap target come from the form, so the same "
        "call site serves the transport and the layer dialog"
    )


def _toast_script() -> str:
    layout = (TEMPLATES_DIR / "layout.html").read_text()
    match = re.search(
        r'<script id="toast-script">(.*?)</script>', layout, re.S
    )
    assert match is not None, "toast-script vanished from the layout"
    return match.group(1)


async def test_toasts_live_outside_every_poller_swap_scope(music_client):
    # The toast container and its listener must never be inside a poll
    # swap region: a 2s poll wiping pending toasts (or doubling the
    # listener) defeats the whole feature.
    response = await music_client.get(f"/music?guild_id={GUILD_A}")
    assert response.status_code == 200
    root = _parse((await response.get_data()).decode())

    for poller in _pollers(root):
        scope_ids = {
            node.attrs.get("id") for node in _swap_scope(root, poller)
        }
        assert "toast-container" not in scope_ids, (
            f"poller <{poller.attrs['hx-trigger']!r}> swaps the toast "
            "container; every poll would wipe pending toasts."
        )
        assert "toast-script" not in scope_ids, (
            f"poller <{poller.attrs['hx-trigger']!r}> swaps the toast "
            "listener; every poll would wipe or double it."
        )


async def test_toast_script_binds_once_on_the_full_page_only(music_client):
    full = await music_client.get(f"/music?guild_id={GUILD_A}")
    full_body = (await full.get_data()).decode()
    assert full_body.count('id="toast-script"') == 1

    for target in ("status_panels", "transport", "side_panel"):
        response = await music_client.get(
            "/music", headers={"HX-Request": "true", "HX-Target": target}
        )
        fragment = (await response.get_data()).decode()
        assert 'id="toast-script"' not in fragment, target


def test_toast_script_renders_and_stacks_server_toasts():
    script = _toast_script()

    assert "harpi:toast" in script, (
        "the listener must key off the server-declared event, not "
        "client-side guessing"
    )
    assert 'getElementById("toast-container")' in script, (
        "toasts render into the layout's container only"
    )
    assert "appendChild" in script, (
        "toasts stack — appending, never overwriting an earlier one"
    )
    assert "textContent" in script and "innerHTML" not in script, (
        "the message arrives from the server; render it as text, never "
        "through innerHTML (escaped surface)"
    )
    assert "setTimeout" in script and ".remove()" in script, (
        "each toast must dismiss itself after a few seconds"
    )


def test_toasts_are_amber_and_never_green():
    css = (TEMPLATES_DIR.parent / "static" / "css" / "input.css").read_text()
    match = re.search(r"\.toast \{[^}]*\}", css)
    assert match is not None, "the .toast rule vanished from the CSS"
    rule = match.group(0)
    assert "--color-primary" in rule, "toasts must be amber (primary ink)"
    assert "alert" not in rule and "green" not in rule, (
        "toasts are confirmations: amber only, never the error red and "
        "never green (the design language has no green)"
    )
    assert '"role", "status"' in _toast_script(), (
        "each toast is announced politely via role=status in the "
        "aria-live container"
    )
