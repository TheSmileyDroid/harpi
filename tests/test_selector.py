"""Selector partial rendering and 2-step guild/channel semantics.

The merged ``_guild_channel_selector.html`` partial compares ids across the
session/template boundary where values can arrive as str or int, so both
sides are stringified.  The ``guild_select_channel`` route applies exactly
one step per request: a guild change saves and re-renders (no connect), a
channel change connects through the session guild.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from quart import Quart, render_template

import src.api.deps as deps
import src.api.htmx_routes as htmx_module
from tests.conftest import _unformat

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"

GUILD_ID = 123
CHANNEL_ID = 101


def _make_app() -> Quart:
    app = Quart(__name__, template_folder=str(TEMPLATES_DIR))
    app.secret_key = "test"
    app.register_blueprint(htmx_module.bp)
    return app


def _guilds() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(id=123, name="Alpha Guild"),
        SimpleNamespace(id=456, name="Beta Guild"),
    ]


def _channels() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            id=100, name="Alpha Channel", user_limit=0, voice_states=[]
        ),
        SimpleNamespace(
            id=101, name="Beta Channel", user_limit=2, voice_states=[]
        ),
    ]


async def _render(**context: Any) -> str:
    app = _make_app()
    ctx = app.test_request_context("/")
    await ctx.push()
    try:
        return await render_template(
            "partials/_guild_channel_selector.html", **context
        )
    finally:
        await ctx.pop()


def _selector_context(guild_id: Any = None, channel_id: Any = None) -> dict:
    return {
        "guilds": _guilds(),
        "selected_guild_id": guild_id,
        "selected_channel_id": channel_id,
        "channels": _channels(),
        "guild_id": guild_id,
    }


# --- Partial selection (str/int type-proof) ---


@pytest.mark.asyncio
async def test_guild_selected_attribute_for_string_selected_guild_id():
    html = await _render(**_selector_context(guild_id="456"))
    assert _unformat('<option value="456" selected>') in _unformat(html)
    assert _unformat('<option value="123" selected>') not in _unformat(html)


@pytest.mark.asyncio
async def test_guild_selected_attribute_for_int_selected_guild_id():
    html = await _render(**_selector_context(guild_id=456))
    assert _unformat('<option value="456" selected>') in _unformat(html)
    assert _unformat('<option value="123" selected>') not in _unformat(html)


@pytest.mark.asyncio
async def test_no_guild_selected_attribute_when_selection_missing():
    html = await _render(**_selector_context())
    assert _unformat('<option value="456" selected>') not in _unformat(html)
    assert _unformat('<option value="123" selected>') not in _unformat(html)


@pytest.mark.asyncio
async def test_channel_selected_attribute_for_string_selected_channel_id():
    html = await _render(**_selector_context(guild_id=456, channel_id="101"))
    assert _unformat('<option value="101" selected>') in _unformat(html)
    assert _unformat('<option value="100" selected>') not in _unformat(html)


@pytest.mark.asyncio
async def test_channel_selected_attribute_for_int_selected_channel_id():
    html = await _render(**_selector_context(guild_id=456, channel_id=101))
    assert _unformat('<option value="101" selected>') in _unformat(html)
    assert _unformat('<option value="100" selected>') not in _unformat(html)


@pytest.mark.asyncio
@pytest.mark.parametrize("selected_channel_id", [None, "", "0", "999"])
async def test_no_channel_selected_attribute_when_selection_unmatched(
    selected_channel_id,
):
    html = await _render(
        **_selector_context(guild_id=456, channel_id=selected_channel_id)
    )
    assert _unformat('<option value="101" selected>') not in _unformat(html)
    assert _unformat('<option value="100" selected>') not in _unformat(html)


# --- Route semantics: one step per request ---


class FakeSessions:
    def __init__(self, bot: SimpleNamespace) -> None:
        self.bot = bot
        self.connect_calls: list[tuple[int, int]] = []
        self.disconnect_calls: list[int] = []

    async def connect(self, guild_id: int, channel_id: int) -> None:
        self.connect_calls.append((guild_id, channel_id))
        channel = SimpleNamespace(
            id=channel_id, guild=SimpleNamespace(id=guild_id)
        )
        self.bot.voice_clients.append(SimpleNamespace(channel=channel))

    async def disconnect(self, guild_id: int) -> None:
        self.disconnect_calls.append(guild_id)


def _fake_bot(*, ready: bool = True) -> SimpleNamespace:
    async def fetch_guilds(**kwargs):
        for guild in _guilds():
            yield guild

    bot = SimpleNamespace(
        loop=None,
        is_ready=lambda: ready,
        get_guild=lambda gid: SimpleNamespace(
            id=gid, name="Guild", voice_channels=_channels()
        ),
        fetch_guilds=fetch_guilds,
        voice_clients=[],
        sessions=None,
    )
    bot.loop = asyncio.get_event_loop()
    bot.sessions = FakeSessions(bot)
    return bot


def _install_bot(monkeypatch: pytest.MonkeyPatch, bot) -> None:
    monkeypatch.setattr(deps, "_bot_ref", bot)


@pytest.mark.asyncio
async def test_guild_change_saves_and_renders_without_connecting(monkeypatch):
    bot = _fake_bot()
    _install_bot(monkeypatch, bot)
    app = _make_app()
    client = app.test_client()

    response = await client.get("/api/guild/select-channel?guild_id=456")

    assert response.status_code == 200
    assert bot.sessions.connect_calls == []
    html = _unformat(await response.get_data(as_text=True))
    assert _unformat('<option value="456" selected>') in html
    assert 'value="101"' in html  # the new guild's channels are rendered

    async with client.session_transaction() as sess:
        assert sess["guild_id"] == "456"


@pytest.mark.asyncio
async def test_channel_change_connects_through_the_session_guild(monkeypatch):
    bot = _fake_bot()
    _install_bot(monkeypatch, bot)
    app = _make_app()
    client = app.test_client()
    async with client.session_transaction() as sess:
        sess["guild_id"] = "456"

    response = await client.get("/api/guild/select-channel?channel_id=101")

    assert response.status_code == 200
    assert bot.sessions.connect_calls == [(456, 101)]
    html = _unformat(await response.get_data(as_text=True))
    assert _unformat('<option value="101" selected>') in html


@pytest.mark.asyncio
async def test_channel_change_requires_a_session_guild(monkeypatch):
    bot = _fake_bot()
    _install_bot(monkeypatch, bot)
    app = _make_app()
    client = app.test_client()

    response = await client.get("/api/guild/select-channel?channel_id=101")

    assert response.status_code == 400
    assert bot.sessions.connect_calls == []


@pytest.mark.asyncio
async def test_selector_requires_at_least_one_argument(monkeypatch):
    _install_bot(monkeypatch, _fake_bot())
    app = _make_app()
    client = app.test_client()

    response = await client.get("/api/guild/select-channel")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_bot_not_ready_renders_the_selector_with_the_saved_guild(
    monkeypatch,
):
    bot = _fake_bot(ready=False)
    _install_bot(monkeypatch, bot)
    app = _make_app()
    client = app.test_client()

    response = await client.get("/api/guild/select-channel?guild_id=456")

    assert response.status_code == 503
    assert bot.sessions.connect_calls == []
    html = _unformat(await response.get_data(as_text=True))
    assert _unformat('<option value="456" selected>') in html
