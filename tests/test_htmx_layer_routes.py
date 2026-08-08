"""Layer routing tests for the HTMX panel routes.

The HTMX layer actions must funnel through the session via the
``_session_action`` helper — the same ``run_on_bot_loop`` bridge the
playback controls use — never through the legacy guild config.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest

import src.api.deps as deps
import src.api.htmx_routes as htmx_module
import src.harpi_lib.audio.session as session_module
from src.harpi_lib.audio.session import PlaybackSession
from tests.conftest import (
    GUILD_ID,
    FakeChannel,
    FakeGuild,
    FakeLayerSource,
    FakeLayerSourceFactory,
    FakeMusicDataFactory,
    FakeVoiceClient,
)


async def _make_session() -> PlaybackSession:
    guild = FakeGuild(GUILD_ID)
    channel = FakeChannel(guild)
    session = PlaybackSession(
        guild_id=GUILD_ID,
        voice_client=await channel.connect(),
        loop=asyncio.get_running_loop(),
    )
    session.start()
    return session


def _install_layer_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_module, "YTMusicData", FakeMusicDataFactory)
    monkeypatch.setattr(
        session_module, "YoutubeDLSource", FakeLayerSourceFactory
    )


def _fake_bot(session: PlaybackSession) -> SimpleNamespace:
    guild = FakeGuild(GUILD_ID)
    guild.voice_client = cast(FakeVoiceClient, session._voice_client)

    class _Sessions:
        def get(self, guild_id: int) -> PlaybackSession | None:
            return session if guild_id == GUILD_ID else None

    return SimpleNamespace(
        loop=asyncio.get_running_loop(),
        is_ready=lambda: True,
        get_guild=lambda guild_id: guild if guild_id == GUILD_ID else None,
        sessions=_Sessions(),
    )


async def _add_layer(
    session: PlaybackSession, monkeypatch: pytest.MonkeyPatch, title: str
) -> FakeLayerSource:
    _install_layer_fakes(monkeypatch)
    await session.add_layer(title)
    return cast(FakeLayerSource, session._layers[f"layer-{title}"])


def _stub_layers_render(
    monkeypatch: pytest.MonkeyPatch,
) -> list[str]:
    rendered: list[str] = []

    async def _fake_layers(guild_id: str) -> str:
        rendered.append(guild_id)
        return "layers"

    monkeypatch.setattr(htmx_module, "htmx_music_layers", _fake_layers)
    return rendered


async def test_layer_remove_routes_through_the_session(monkeypatch):
    session = await _make_session()
    layer = await _add_layer(session, monkeypatch, "rain")
    monkeypatch.setattr(deps, "_bot_ref", _fake_bot(session))
    rendered = _stub_layers_render(monkeypatch)

    html = await htmx_module.api_music_layer_remove(str(GUILD_ID), "layer-rain")

    assert html == "layers"
    assert rendered == [str(GUILD_ID)]
    assert session.status.layers == ()
    assert layer.cleaned_up is True


async def test_layer_clean_routes_through_the_session(monkeypatch):
    session = await _make_session()
    layer = await _add_layer(session, monkeypatch, "rain")
    monkeypatch.setattr(deps, "_bot_ref", _fake_bot(session))
    rendered = _stub_layers_render(monkeypatch)

    html = await htmx_module.api_music_layers_clean(str(GUILD_ID))

    assert html == "layers"
    assert rendered == [str(GUILD_ID)]
    assert session.status.layers == ()
    assert layer.cleaned_up is True
