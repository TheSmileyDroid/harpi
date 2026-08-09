"""Routing tests for the TTS cog's chat command.

The TTS command must route through the SessionManager and the
PlaybackSession: it only synthesizes text to audio and hands the resulting
stream to the session, never constructing or importing audio-source
classes.  A recording fake session and manager stand in for the real
objects and a fake gTTS stands in for the synthesizer; the command itself
is real.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from discord.ext.commands import Command, Context

from src.cogs.tts import TTSCog
from src.harpi_lib.harpi_bot import HarpiBot
from tests.conftest import CHANNEL_ID, GUILD_ID


async def _invoke(
    command: Command, cog: TTSCog, ctx: FakeContext, **kwargs: Any
) -> Any:
    """Call a cog command the way the framework would, without a bound bot."""
    callback = cast(Callable[..., Any], command.callback)
    return await callback(cog, cast(Context, ctx), **kwargs)


class RecordingSession:
    """Stands in for a PlaybackSession and records the TTS verb."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.tts_audio: io.BufferedIOBase | None = None

    async def play_tts(self, audio: io.BufferedIOBase) -> None:
        self.calls.append("play_tts")
        self.tts_audio = audio


class RecordingManager:
    """Stands in for a SessionManager and records the verbs it receives."""

    def __init__(self, session: RecordingSession | None) -> None:
        self._session = session
        self.calls: list[str] = []

    async def ensure(self, guild_id: int, channel_id: int) -> RecordingSession:
        self.calls.append(f"ensure:{guild_id}:{channel_id}")
        assert self._session is not None
        return self._session


class FakeHarpiBot:
    def __init__(self, manager: RecordingManager) -> None:
        self.sessions = manager


class FakeContext:
    """Minimal Context stand-in: records sent messages, has a voice author."""

    def __init__(self, guild_id: int = GUILD_ID) -> None:
        self.guild: SimpleNamespace | None = SimpleNamespace(id=guild_id)
        self.author = SimpleNamespace(
            voice=SimpleNamespace(channel=SimpleNamespace(id=CHANNEL_ID))
        )
        self.sent: list[str] = []

    async def send(self, content: str, **kwargs: Any) -> None:
        self.sent.append(content)


class FakeGTTS:
    """Fake gTTS stand-in: writes a fixed byte stream and records its args."""

    def __init__(self, text: str, lang: str, tld: str) -> None:
        self.text = text
        self.lang = lang
        self.tld = tld

    def write_to_fp(self, fp: io.BufferedIOBase) -> None:
        fp.write(b"fake speech")


def _make_cog(
    session: RecordingSession | None,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TTSCog, RecordingSession | None, FakeContext]:
    manager = RecordingManager(session)
    bot = FakeHarpiBot(manager)
    cog = TTSCog(cast(HarpiBot, bot))
    monkeypatch.setattr("src.cogs.tts.gTTS", FakeGTTS)
    ctx = FakeContext()
    return cog, session, ctx


async def test_tts_routes_through_the_session_and_hands_synthesized_audio(
    monkeypatch,
):
    session = RecordingSession()
    cog, session, ctx = _make_cog(session, monkeypatch)
    manager = cast(RecordingManager, cog.bot.sessions)

    await _invoke(cog.tts, cog, ctx, text="olá, aventureiros")

    assert session is not None
    assert manager.calls == [f"ensure:{GUILD_ID}:{CHANNEL_ID}"]
    assert session.calls == ["play_tts"]
    audio = cast(io.BytesIO, session.tts_audio)
    assert audio.getvalue() == b"fake speech"
    assert audio.tell() == 0
    assert ctx.sent == ["OK"]


async def test_tts_requires_a_guild(monkeypatch):
    session = RecordingSession()
    cog, session, ctx = _make_cog(session, monkeypatch)
    ctx.guild = None

    await _invoke(cog.tts, cog, ctx, text="oi")

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Você precisa estar em um servidor."]


async def test_tts_requires_the_user_to_be_in_a_voice_channel(monkeypatch):
    session = RecordingSession()
    cog, session, ctx = _make_cog(session, monkeypatch)
    ctx.author = SimpleNamespace(voice=None)

    await _invoke(cog.tts, cog, ctx, text="oi")

    assert session is not None
    assert session.calls == []
    assert ctx.sent == ["Você precisa estar em um canal de voz."]
