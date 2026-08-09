"""Type-proof selection for the channel selector partial.

The partial compares ``channel.id`` against ``selected_channel_id``. Across the
session/template boundary the values can come back as different types even
when they represent the same id, so the comparison stringifies both sides.
These tests render the real ``partials/_channel_selector.html`` inside a Quart
app context and assert the ``selected`` attribute lands on the right option
for both int and string inputs.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from quart import Quart, render_template

from tests.conftest import _unformat

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"


def _make_app() -> Quart:
    app = Quart(
        __name__,
        template_folder=str(TEMPLATES_DIR),
    )
    app.secret_key = "test"
    return app


def _channels() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            id=100, name="Alpha Channel", user_limit=0, voice_states=[]
        ),
        SimpleNamespace(
            id=101, name="Beta Channel", user_limit=2, voice_states=[]
        ),
    ]


async def _render(selected_channel_id: str | int | None) -> str:
    app = _make_app()
    ctx = app.app_context()
    await ctx.push()
    try:
        return await render_template(
            "partials/_channel_selector.html",
            channels=_channels(),
            selected_channel_id=selected_channel_id,
        )
    finally:
        await ctx.pop()


@pytest.mark.asyncio
async def test_selected_attribute_for_string_selected_channel_id():
    html = await _render(selected_channel_id="101")
    assert _unformat('<option value="101" selected>') in _unformat(html)
    assert _unformat('<option value="100" selected>') not in _unformat(html)


@pytest.mark.asyncio
async def test_selected_attribute_for_int_selected_channel_id():
    html = await _render(selected_channel_id=101)
    assert _unformat('<option value="101" selected>') in _unformat(html)
    assert _unformat('<option value="100" selected>') not in _unformat(html)


@pytest.mark.asyncio
async def test_no_selected_attribute_when_selection_missing():
    html = await _render(selected_channel_id=None)
    assert '<option value="101" selected>' not in html
    assert '<option value="100" selected>' not in html


@pytest.mark.asyncio
@pytest.mark.parametrize("selected_channel_id", ["", "0", "999"])
async def test_no_selected_attribute_when_selection_unmatched(
    selected_channel_id,
):
    html = await _render(selected_channel_id=selected_channel_id)
    assert '<option value="101" selected>' not in html
    assert '<option value="100" selected>' not in html
