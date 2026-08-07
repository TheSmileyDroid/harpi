"""Lifecycle tests for SessionManager.

The manager owns the session registry: sessions are created on ``connect``,
found by ``get`` / ``ensure``, and removed by ``disconnect``.  An unexpected
voice disconnect self-cleans through ``on_voice_state_update``.  The fakes
in ``conftest`` stand in for the discord guild/channel/voice-client objects,
so the manager is exercised through the same verbs the cogs and routes will
call.
"""

from types import SimpleNamespace
from typing import cast

import discord
import pytest
from discord.ext.commands import Bot

from src.harpi_lib.audio.session import PlaybackSession
from src.harpi_lib.audio.session_manager import SessionManager
from tests.conftest import (
    BOT_USER_ID,
    CHANNEL_ID,
    GUILD_ID,
    FakeBot,
    FakeChannel,
    FakeGuild,
    FakeSource,
)


def _make_manager() -> tuple[SessionManager, FakeGuild]:
    bot = FakeBot()
    guild = FakeGuild(GUILD_ID)
    guild._channels[CHANNEL_ID] = FakeChannel(guild)
    bot._guilds[GUILD_ID] = guild
    return SessionManager(cast(Bot, bot)), guild


def _member(guild: FakeGuild, member_id: int = BOT_USER_ID) -> discord.Member:
    return cast(discord.Member, SimpleNamespace(id=member_id, guild=guild))


def _voice_state(channel: FakeChannel | None) -> discord.VoiceState:
    return cast(discord.VoiceState, SimpleNamespace(channel=channel))


async def test_connect_creates_and_registers_a_session():
    manager, guild = _make_manager()

    session = await manager.connect(GUILD_ID, CHANNEL_ID)

    assert isinstance(session, PlaybackSession)
    assert session.guild_id == GUILD_ID
    assert manager.get(GUILD_ID) is session
    assert guild.voice_client is not None
    assert guild.voice_client.is_playing() is True


async def test_get_returns_none_when_guild_not_connected():
    manager, _ = _make_manager()

    assert manager.get(GUILD_ID) is None


async def test_ensure_connects_when_no_session_exists():
    manager, guild = _make_manager()

    session = await manager.ensure(GUILD_ID, CHANNEL_ID)

    assert manager.get(GUILD_ID) is session
    assert guild._channels[CHANNEL_ID].connect_calls == 1


async def test_ensure_returns_existing_session_without_reconnecting():
    manager, guild = _make_manager()
    first = await manager.connect(GUILD_ID, CHANNEL_ID)

    second = await manager.ensure(GUILD_ID, CHANNEL_ID)

    assert second is first
    assert guild._channels[CHANNEL_ID].connect_calls == 1


async def test_disconnect_removes_session_and_cleans_up():
    manager, guild = _make_manager()
    session = await manager.connect(GUILD_ID, CHANNEL_ID)
    voice_client = guild.voice_client
    source = FakeSource()
    session._controller.set_queue_source(source)

    await manager.disconnect(GUILD_ID)

    assert manager.get(GUILD_ID) is None
    assert voice_client is not None
    assert voice_client.disconnected is True
    assert source.cleaned_up is True
    assert session._mixer._shutdown is True


async def test_disconnect_raises_when_guild_not_connected():
    manager, _ = _make_manager()

    with pytest.raises(ValueError):
        await manager.disconnect(GUILD_ID)


async def test_unexpected_voice_disconnect_tears_the_session_down():
    manager, guild = _make_manager()
    session = await manager.connect(GUILD_ID, CHANNEL_ID)
    source = FakeSource()
    session._controller.set_queue_source(source)

    await manager.on_voice_state_update(
        _member(guild), _voice_state(FakeChannel(guild)), _voice_state(None)
    )

    assert manager.get(GUILD_ID) is None
    assert source.cleaned_up is True
    assert session._mixer._shutdown is True


async def test_voice_state_update_ignores_other_members():
    manager, guild = _make_manager()
    session = await manager.connect(GUILD_ID, CHANNEL_ID)

    await manager.on_voice_state_update(
        _member(guild, member_id=9999),
        _voice_state(FakeChannel(guild)),
        _voice_state(None),
    )

    assert manager.get(GUILD_ID) is session


async def test_voice_state_update_keeps_session_when_bot_moves_channels():
    manager, guild = _make_manager()
    session = await manager.connect(GUILD_ID, CHANNEL_ID)

    await manager.on_voice_state_update(
        _member(guild),
        _voice_state(FakeChannel(guild)),
        _voice_state(FakeChannel(guild)),
    )

    assert manager.get(GUILD_ID) is session


async def test_connect_reconnects_over_an_existing_voice_client():
    manager, guild = _make_manager()
    first = await manager.connect(GUILD_ID, CHANNEL_ID)
    old_client = guild.voice_client
    assert old_client is not None

    second = await manager.connect(GUILD_ID, CHANNEL_ID)

    assert old_client.disconnected is True
    assert manager.get(GUILD_ID) is second
    assert second is not first


async def test_connect_cleans_up_an_existing_manager_session():
    manager, _ = _make_manager()
    first = await manager.connect(GUILD_ID, CHANNEL_ID)
    source = FakeSource()
    first._controller.set_queue_source(source)

    await manager.connect(GUILD_ID, CHANNEL_ID)

    assert source.cleaned_up is True
    assert first._mixer._shutdown is True


async def test_connect_raises_when_guild_not_found():
    manager = SessionManager(cast(Bot, FakeBot()))

    with pytest.raises(ValueError):
        await manager.connect(99, CHANNEL_ID)


async def test_connect_raises_when_channel_not_found():
    manager, _ = _make_manager()

    with pytest.raises(ValueError):
        await manager.connect(GUILD_ID, 99)
