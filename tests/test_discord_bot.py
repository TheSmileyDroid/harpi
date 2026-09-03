"""Tests for the Discord bot assembly entry points.

``get_token`` and the guards of ``run_bot_in_background`` are pure logic
and are tested directly.  ``create_bot`` is exercised against a real
``HarpiBot`` construction (no network: the client is never started).
The gateway connection inside the background thread is genuinely
untestable without a live Discord connection and is deliberately not
faked; everything around it is.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

import src.discord_bot as discord_bot_module
from src import bot_state
from src.bot_state import init_bot
from src.config import Settings
from src.discord_bot import create_bot, get_token, run_bot_in_background
from src.harpi_lib.harpi_bot import HarpiBot


def _settings(token: str | None = None) -> Settings:
    return Settings(
        discord_token=token,
        prefix="-",
        host="127.0.0.1",
        port=8000,
        reload=False,
        secret_key="secret",
    )


# --- get_token -----------------------------------------------------------------


def test_get_token_returns_the_configured_token():
    assert get_token(_settings("abc")) == "abc"


def test_get_token_rejects_a_missing_token():
    with pytest.raises(ValueError, match="DISCORD_TOKEN"):
        get_token(_settings(None))


# --- create_bot ----------------------------------------------------------------


async def test_create_bot_registers_all_cogs_and_the_session_listener():
    client = await create_bot(_settings("abc"))

    cog_names = {type(cog).__name__ for cog in client.cogs.values()}
    assert {"TTSCog", "MusicCog", "GeneralCog", "DiceCog"} <= cog_names

    extra_events = {
        event
        for event, handlers in client.extra_events.items()
        for handler in handlers
        if getattr(handler, "__name__", "") == "on_voice_state_update"
    }
    assert "on_voice_state_update" in extra_events


# --- run_bot_in_background -------------------------------------------------------


def test_run_bot_in_background_rejects_a_missing_token():
    with pytest.raises(ValueError, match="DISCORD_TOKEN"):
        run_bot_in_background(_settings(None))


def test_run_bot_in_background_skips_when_the_bot_is_already_running(
    monkeypatch,
):
    init_bot(cast(HarpiBot, SimpleBot()))

    def fail(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("no thread must be started")

    monkeypatch.setattr(discord_bot_module.threading, "Thread", fail)
    try:
        run_bot_in_background(_settings("abc"))
    finally:
        bot_state._bot_ref = None


class SimpleBot:
    pass


def test_run_bot_in_background_creates_and_starts_the_bot_in_a_thread(
    monkeypatch,
):
    import threading

    started = threading.Event()
    failing = {"create": False}

    class StartableBot:
        async def start(self, token: str) -> None:
            started.set()

    async def fake_create_bot(settings: Settings) -> Any:
        if failing["create"]:
            raise RuntimeError("boom")
        return StartableBot()

    monkeypatch.setattr(discord_bot_module, "create_bot", fake_create_bot)

    # Record the thread at creation instead of fishing for it in
    # threading.enumerate(): the fake bot starts instantly, so the daemon
    # thread could already be gone (and the hunt raise StopIteration)
    # before we looked.
    created: list[threading.Thread] = []
    real_thread = threading.Thread

    def recording_thread(*args: Any, **kwargs: Any) -> threading.Thread:
        thread = real_thread(*args, **kwargs)
        created.append(thread)
        return thread

    monkeypatch.setattr(
        discord_bot_module.threading, "Thread", recording_thread
    )

    run_bot_in_background(_settings("abc"))

    assert created, "run_bot_in_background must start a thread"
    thread = created[0]
    assert started.wait(timeout=5)
    thread.join(timeout=5)
    assert not thread.is_alive()

    # The guard resets once the bot reference exists; drop it for later tests.
    bot_state._bot_ref = None
