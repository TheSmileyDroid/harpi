"""Type-proof selection for the guild selector partial.

The partial compares ``guild.id`` against ``selected_guild_id``. Across the
session/template boundary the values can come back as different types even
when they represent the same id, so the comparison stringifies both sides.
These tests render the real ``partials/_guild_selector.html`` inside a Quart
app context (the partial calls ``url_for``) and assert the ``selected``
attribute lands on the right option for both int and string inputs.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from quart import Blueprint, Quart, render_template

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"


def _make_app() -> Quart:
    app = Quart(
        __name__,
        template_folder=str(TEMPLATES_DIR),
    )
    app.secret_key = "test"

    bp = Blueprint("htmx_routes", __name__)

    @bp.route("/htmx/channels")
    async def htmx_channels():
        return ""

    @bp.route("/api/guild/select-channel")
    async def guild_select_channel():
        return ""

    app.register_blueprint(bp)
    return app


def _guilds() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(id=123, name="Alpha Guild"),
        SimpleNamespace(id=456, name="Beta Guild"),
    ]


async def _render(selected_guild_id) -> str:
    app = _make_app()
    ctx = app.test_request_context("/")
    await ctx.push()
    try:
        return await render_template(
            "partials/_guild_selector.html",
            guilds=_guilds(),
            selected_guild_id=selected_guild_id,
            channels=[],
        )
    finally:
        await ctx.pop()


@pytest.mark.asyncio
async def test_selected_attribute_for_string_selected_guild_id():
    html = await _render(selected_guild_id="456")
    assert '<option value="456" selected>' in html
    assert '<option value="123" selected>' not in html


@pytest.mark.asyncio
async def test_selected_attribute_for_int_selected_guild_id():
    html = await _render(selected_guild_id=456)
    assert '<option value="456" selected>' in html
    assert '<option value="123" selected>' not in html


@pytest.mark.asyncio
async def test_no_selected_attribute_when_selection_missing():
    html = await _render(selected_guild_id=None)
    assert '<option value="456" selected>' not in html
    assert '<option value="123" selected>' not in html
