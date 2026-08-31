"""Web-route tests for the index and status pages.

These drive ``pages.index`` through Quart's test client with a fake bot
stored in ``bot_state``, asserting what the rendered HTML contains.  No
real Discord connection is involved.
"""

from __future__ import annotations

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

    def is_ready(self) -> bool:
        return self._ready

    def is_closed(self) -> bool:
        return self._closed


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


async def test_status_component_reflects_the_connection_state(client):
    deps.init_bot(cast(HarpiBot, FakeBot(ready=True, closed=False)))
    online = await client.get("/status")
    assert online.status_code == 200
    assert "ONLINE" in (await online.get_data()).decode()

    deps._bot_ref = cast(HarpiBot, FakeBot(ready=False, closed=True))
    offline = await client.get("/status")
    assert offline.status_code == 200
    assert "OFFLINE" in (await offline.get_data()).decode()
