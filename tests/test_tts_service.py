"""Tests for TTSService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.harpi_lib.api import GuildConfig
from src.harpi_lib.services.tts import TTSService


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    return bot


@pytest.fixture
def guilds():
    return {}


@pytest.fixture
def voice_service():
    vs = MagicMock()
    vs.connect = AsyncMock()
    return vs


@pytest.fixture
def service(mock_bot, guilds, voice_service):
    return TTSService(mock_bot, guilds, voice_service)


def _make_guild_config(guild_id: int = 1, **kwargs) -> GuildConfig:
    return GuildConfig(
        id=guild_id,
        mixer=MagicMock(),
        controller=MagicMock(),
        **kwargs,
    )


class TestPlay:
    @pytest.mark.asyncio
    async def test_sets_tts_track_when_connected(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        guilds[1] = gc
        mock_source = MagicMock()

        await service.play(1, 67890, mock_source)
        gc.controller.set_tts_track.assert_called_once_with(mock_source)

    @pytest.mark.asyncio
    async def test_auto_connects_when_not_connected(
        self, service, guilds, voice_service
    ):
        gc = _make_guild_config(guild_id=1)
        voice_service.connect.return_value = gc
        mock_source = MagicMock()

        await service.play(1, 67890, mock_source)

        voice_service.connect.assert_called_once_with(1, 67890, None)
        gc.controller.set_tts_track.assert_called_once_with(mock_source)

    @pytest.mark.asyncio
    async def test_passes_ctx_to_connect(self, service, guilds, voice_service):
        gc = _make_guild_config(guild_id=1)
        voice_service.connect.return_value = gc
        mock_source = MagicMock()
        mock_ctx = MagicMock()

        await service.play(1, 67890, mock_source, ctx=mock_ctx)

        voice_service.connect.assert_called_once_with(1, 67890, mock_ctx)
