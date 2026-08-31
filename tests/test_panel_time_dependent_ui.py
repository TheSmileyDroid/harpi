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
