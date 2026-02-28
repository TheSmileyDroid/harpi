"""Tests for BackgroundAudioService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.harpi_lib.api import GuildConfig
from src.harpi_lib.services.background_audio import BackgroundAudioService


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
    return BackgroundAudioService(mock_bot, guilds, voice_service)


def _make_guild_config(guild_id: int = 1, **kwargs) -> GuildConfig:
    return GuildConfig(
        id=guild_id,
        mixer=MagicMock(),
        controller=MagicMock(),
        **kwargs,
    )


class TestRemove:
    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.remove(999, "layer-1")

    @pytest.mark.asyncio
    async def test_raises_when_layer_not_found(self, service, guilds):
        gc = _make_guild_config(guild_id=1, background={})
        guilds[1] = gc
        with pytest.raises(ValueError, match="não encontrado"):
            await service.remove(1, "no-such-layer")

    @pytest.mark.asyncio
    async def test_raises_when_no_background_dict(self, service, guilds):
        gc = _make_guild_config(guild_id=1, background=None)
        guilds[1] = gc
        with pytest.raises(ValueError, match="não encontrado"):
            await service.remove(1, "any")

    @pytest.mark.asyncio
    async def test_removes_and_returns_source(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(
            guild_id=1, background={"layer-1": mock_source}
        )
        guilds[1] = gc

        result = await service.remove(1, "layer-1")
        assert result is mock_source
        assert "layer-1" not in gc.background
        gc.controller.remove_layer.assert_called_once_with("layer-1")


class TestSetVolume:
    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.set_volume(999, "layer-1", 0.5)

    @pytest.mark.asyncio
    async def test_raises_when_layer_not_found(self, service, guilds):
        gc = _make_guild_config(guild_id=1, background={})
        guilds[1] = gc
        with pytest.raises(ValueError, match="não encontrado"):
            await service.set_volume(1, "no-layer", 0.5)

    @pytest.mark.asyncio
    async def test_sets_volume_with_clamping(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(
            guild_id=1, background={"layer-1": mock_source}
        )
        guilds[1] = gc

        await service.set_volume(1, "layer-1", 5.0)
        assert mock_source.volume == 2.0  # clamped to max

        await service.set_volume(1, "layer-1", -1.0)
        assert mock_source.volume == 0.0  # clamped to min

        await service.set_volume(1, "layer-1", 0.7)
        assert mock_source.volume == 0.7


class TestGetStatus:
    def test_returns_empty_when_not_connected(self, service):
        assert service.get_status(999) == []

    def test_returns_empty_when_no_background(self, service, guilds):
        gc = _make_guild_config(guild_id=1, background=None)
        guilds[1] = gc
        assert service.get_status(1) == []

    def test_returns_status_for_sources(self, service, guilds):
        mock_source = MagicMock()
        mock_source.volume = 0.7
        mock_source.data = {"duration": 120}
        mock_source.progress = 0.5
        mock_source.title = "Test Song"
        mock_source.url = "https://example.com"

        gc = _make_guild_config(
            guild_id=1, background={"layer-1": mock_source}
        )
        guilds[1] = gc

        status = service.get_status(1)
        assert len(status) == 1
        assert status[0]["layer_id"] == "layer-1"
        assert status[0]["playing"] is True
        assert status[0]["volume"] == 70.0  # 0.7 * 100
        assert status[0]["duration"] == 120.0
        assert status[0]["title"] == "Test Song"

    def test_handles_source_without_data_attr(self, service, guilds):
        mock_source = MagicMock(spec=[])  # no attributes at all
        mock_source.volume = 0.5

        gc = _make_guild_config(
            guild_id=1, background={"layer-1": mock_source}
        )
        guilds[1] = gc

        status = service.get_status(1)
        assert len(status) == 1
        assert status[0]["duration"] == 0.0


class TestCleanAll:
    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.clean_all(999)

    @pytest.mark.asyncio
    async def test_cleans_controller_and_background(self, service, guilds):
        gc = _make_guild_config(
            guild_id=1,
            background={"l1": MagicMock(), "l2": MagicMock()},
        )
        guilds[1] = gc

        await service.clean_all(1)
        gc.controller.cleanup_all.assert_called_once()
        assert gc.background == {}

    @pytest.mark.asyncio
    async def test_handles_no_background_dict(self, service, guilds):
        gc = _make_guild_config(guild_id=1, background=None)
        guilds[1] = gc

        await service.clean_all(1)
        gc.controller.cleanup_all.assert_called_once()
