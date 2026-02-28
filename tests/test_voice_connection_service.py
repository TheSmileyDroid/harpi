"""Tests for VoiceConnectionService — error paths and disconnect cleanup."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from src.harpi_lib.api import GuildConfig
from src.harpi_lib.services.voice_connection import VoiceConnectionService


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    bot.get_guild = MagicMock()
    return bot


@pytest.fixture
def guilds():
    return {}


@pytest.fixture
def on_queue_end():
    return MagicMock()


@pytest.fixture
def on_track_end():
    return MagicMock()


@pytest.fixture
def service(mock_bot, guilds, on_queue_end, on_track_end):
    return VoiceConnectionService(mock_bot, guilds, on_queue_end, on_track_end)


def _make_guild_config(guild_id: int = 1, **kwargs) -> GuildConfig:
    return GuildConfig(
        id=guild_id,
        mixer=MagicMock(),
        controller=MagicMock(),
        **kwargs,
    )


class TestConnectErrorPaths:
    @pytest.mark.asyncio
    async def test_raises_on_client_exception(self, service, mock_bot):
        mock_guild = MagicMock()
        mock_guild.id = 1
        mock_guild.voice_client = None
        mock_bot.get_guild.return_value = mock_guild

        mock_channel = MagicMock(spec=discord.VoiceChannel)
        mock_guild.get_channel.return_value = mock_channel
        mock_channel.connect = AsyncMock(
            side_effect=discord.ClientException("already connected")
        )

        with pytest.raises(ValueError, match="Cannot connect"):
            await service.connect(1, 100)

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self, service, mock_bot):
        mock_guild = MagicMock()
        mock_guild.id = 1
        mock_guild.voice_client = None
        mock_bot.get_guild.return_value = mock_guild

        mock_channel = MagicMock(spec=discord.VoiceChannel)
        mock_guild.get_channel.return_value = mock_channel
        mock_channel.connect = AsyncMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(ValueError, match="timed out"):
            await service.connect(1, 100)

    @pytest.mark.asyncio
    async def test_logs_warning_on_existing_disconnect_error(
        self, service, mock_bot
    ):
        mock_guild = MagicMock()
        mock_guild.id = 1
        existing_vc = MagicMock()
        existing_vc.disconnect = AsyncMock(side_effect=RuntimeError("boom"))
        mock_guild.voice_client = existing_vc
        mock_bot.get_guild.return_value = mock_guild

        mock_channel = MagicMock(spec=discord.VoiceChannel)
        mock_guild.get_channel.return_value = mock_channel

        new_vc = MagicMock()
        new_vc.play = MagicMock()
        mock_channel.connect = AsyncMock(return_value=new_vc)

        from src.harpi_lib.music.mixer import MixerSource

        with patch.object(MixerSource, "add_observer", MagicMock()):
            # Should not raise despite existing disconnect failure
            result = await service.connect(1, 100)
            assert result is not None


class TestDisconnectCleanup:
    @pytest.mark.asyncio
    async def test_disconnect_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.disconnect(999)

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up_prepared_sources(
        self, service, guilds
    ):
        mock_source = MagicMock()
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = True
        mock_vc.disconnect = AsyncMock()

        gc = _make_guild_config(
            guild_id=1,
            voice_client=mock_vc,
            prepared_sources={"s1": mock_source},
        )
        guilds[1] = gc

        await service.disconnect(1)
        mock_source.cleanup.assert_called_once()
        assert 1 not in guilds

    @pytest.mark.asyncio
    async def test_disconnect_handles_controller_cleanup_error(
        self, service, guilds
    ):
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = True
        mock_vc.disconnect = AsyncMock()

        gc = _make_guild_config(guild_id=1, voice_client=mock_vc)
        gc.controller.cleanup_all.side_effect = RuntimeError(
            "controller error"
        )
        guilds[1] = gc

        # Should not raise
        await service.disconnect(1)
        assert 1 not in guilds

    @pytest.mark.asyncio
    async def test_disconnect_handles_mixer_cleanup_error(
        self, service, guilds
    ):
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = True
        mock_vc.disconnect = AsyncMock()

        gc = _make_guild_config(guild_id=1, voice_client=mock_vc)
        gc.mixer.cleanup.side_effect = RuntimeError("mixer error")
        guilds[1] = gc

        # Should not raise
        await service.disconnect(1)
        assert 1 not in guilds

    @pytest.mark.asyncio
    async def test_disconnect_handles_prepared_source_cleanup_error(
        self, service, guilds
    ):
        mock_source = MagicMock()
        mock_source.cleanup.side_effect = RuntimeError("source error")
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = True
        mock_vc.disconnect = AsyncMock()

        gc = _make_guild_config(
            guild_id=1,
            voice_client=mock_vc,
            prepared_sources={"s1": mock_source},
        )
        guilds[1] = gc

        # Should not raise
        await service.disconnect(1)
        assert 1 not in guilds

    @pytest.mark.asyncio
    async def test_disconnect_skips_voice_disconnect_when_not_connected(
        self, service, guilds
    ):
        mock_vc = MagicMock()
        mock_vc.is_connected.return_value = False
        mock_vc.disconnect = AsyncMock()

        gc = _make_guild_config(guild_id=1, voice_client=mock_vc)
        guilds[1] = gc

        await service.disconnect(1)
        mock_vc.disconnect.assert_not_called()
        assert 1 not in guilds

    @pytest.mark.asyncio
    async def test_disconnect_handles_none_voice_client(self, service, guilds):
        gc = _make_guild_config(guild_id=1, voice_client=None)
        guilds[1] = gc

        await service.disconnect(1)
        assert 1 not in guilds
