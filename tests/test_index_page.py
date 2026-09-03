"""Web-route tests for the index and status pages.

These drive ``pages.index`` through Quart's test client with a fake bot
stored in ``bot_state``, asserting what the rendered HTML contains.  No
real Discord connection is involved.
"""

from __future__ import annotations

import asyncio
import os
from typing import cast

import pytest

from app import app as quart_app
from src import bot_state as deps
from src.harpi_lib.harpi_bot import HarpiBot


class FakeBot:
    def __init__(self, ready: bool, closed: bool) -> None:
        self._ready = ready
        self._closed = closed

    @property
    def loop(self):
        return asyncio.get_running_loop()

    def is_ready(self) -> bool:
        return self._ready

    def is_closed(self) -> bool:
        return self._closed

    async def fetch_guilds(self, limit: int | None = None):
        del limit
        for guild in []:
            yield guild


@pytest.fixture
def client():
    os.environ["DISCORD_TOKEN"] = "test"
    os.environ["SECRET_KEY"] = "test-secret"
    quart_app.secret_key = "test-secret"
    quart_app.config["TESTING"] = True
    yield quart_app.test_client()
    deps._bot_ref = None


async def test_index_reports_the_bot_as_connected(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))

    response = await client.get("/")

    assert response.status_code == 200
    body = (await response.get_data()).decode()
    assert "ONLINE" in body


async def test_index_reports_the_bot_as_offline_when_not_ready(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=False, closed=False)))

    response = await client.get("/")

    assert response.status_code == 200
    assert "OFFLINE" in (await response.get_data()).decode()


async def test_layout_carries_the_design_fonts_not_the_stale_ones(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))
    response = await client.get("/")

    body = (await response.get_data()).decode()
    assert "IBM+Plex+Mono" in body
    assert "Rajdhani" in body
    assert "Fira+Code" not in body
    assert "Share+Tech+Mono" not in body


async def test_layout_has_a_global_htmx_indicator(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))
    response = await client.get("/")

    body = (await response.get_data()).decode()
    assert 'id="global-indicator"' in body


async def test_global_indicator_stays_silent_on_background_polls(client):
    # Story 16: polling swaps are visually silent. The 2s pollers must not
    # flash the global activity bar, so the layout script guards on htmx's
    # `every` trigger. String-level seam: the guard lives in the layout's
    # inline enhancement script, which no JS test harness covers.
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))
    response = await client.get("/")

    body = (await response.get_data()).decode()
    assert 'includes("every")' in body


async def test_home_renders_no_brackets_at_rest(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))

    response = await client.get("/")

    body = (await response.get_data()).decode()
    assert "hud-brackets" not in body


async def test_nav_marks_the_current_page(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))
    home = await client.get("/")
    home_body = (await home.get_data()).decode()
    music = await client.get("/music")
    music_body = (await music.get_data()).decode()

    home_nav = " ".join(home_body[home_body.find("Main navigation") :].split())
    music_nav = " ".join(
        music_body[music_body.find("Main navigation") :].split()
    )

    assert 'aria-current="page" >Home</a' in home_nav
    assert 'aria-current="page" >Music</a' not in home_nav
    assert 'aria-current="page" >Music</a' in music_nav
    assert 'aria-current="page" >Home</a' not in music_nav


async def test_home_has_no_red_when_the_bot_is_online(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))

    response = await client.get("/")

    body = (await response.get_data()).decode()
    assert "bot-offline" not in body


async def test_home_marks_the_chip_offline_in_red_only_when_broken(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=False, closed=True)))

    response = await client.get("/")

    body = (await response.get_data()).decode()
    assert "bot-offline" in body


async def test_status_component_reflects_the_connection_state(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))
    online = await client.get("/status")
    assert online.status_code == 200
    assert "ONLINE" in (await online.get_data()).decode()

    deps._bot_ref = cast(HarpiBot, FakeBot(ready=False, closed=True))
    offline = await client.get("/status")
    assert offline.status_code == 200
    assert "OFFLINE" in (await offline.get_data()).decode()
