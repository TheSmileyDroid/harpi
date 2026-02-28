"""Tests for MusicQueueService — covering uncovered paths."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.harpi_lib.api import GuildConfig, LoopMode
from src.harpi_lib.services.music_queue import MusicQueueService


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
    return MusicQueueService(mock_bot, guilds, voice_service)


def _make_guild_config(guild_id: int = 1, **kwargs) -> GuildConfig:
    return GuildConfig(
        id=guild_id,
        mixer=MagicMock(),
        controller=MagicMock(),
        **kwargs,
    )


class TestOnTrackEnd:
    def test_removes_finished_sources_from_controller(
        self, service, guilds, mock_bot
    ):
        mock_source = MagicMock()
        gc = _make_guild_config(
            guild_id=1, background={"layer-1": mock_source}
        )
        gc.controller.get_layer_id.return_value = "layer-1"
        guilds[1] = gc

        service.on_track_end(gc, [mock_source])

        gc.controller.remove_layer.assert_called_once_with("layer-1")
        # The background dict mutation is scheduled via call_soon_threadsafe;
        # run the bot event loop briefly so the scheduled callback executes.
        mock_bot.loop.run_until_complete(asyncio.sleep(0))
        assert "layer-1" not in gc.background

    def test_skips_source_with_no_layer_id(self, service, guilds):
        mock_source = MagicMock()
        gc = _make_guild_config(guild_id=1, background={})
        gc.controller.get_layer_id.return_value = None
        guilds[1] = gc

        # Should not raise
        service.on_track_end(gc, [mock_source])
        gc.controller.remove_layer.assert_not_called()


class TestNextMusicExceptionHandling:
    @pytest.mark.asyncio
    async def test_exception_clears_state(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        gc.current_music = MagicMock()
        guilds[1] = gc

        with patch.object(
            service,
            "_next_music_inner",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network error"),
        ):
            await service.next_music(gc)

        assert gc.current_music is None
        gc.controller.clear_queue_source.assert_called_once()


class TestNextMusicInnerLoopTrack:
    @pytest.mark.asyncio
    async def test_loop_track_replays_current(self, service, guilds):
        mock_music_data = MagicMock()
        mock_music_data.title = "Song"
        gc = _make_guild_config(
            guild_id=1,
            current_music=mock_music_data,
            loop=LoopMode.TRACK,
            volume=0.5,
        )
        guilds[1] = gc

        mock_source = MagicMock()
        with patch(
            "src.harpi_lib.services.music_queue.YoutubeDLSource.from_music_data",
            new_callable=AsyncMock,
            return_value=mock_source,
        ):
            await service._next_music_inner(gc, force_next=False)

        gc.controller.set_queue_source.assert_called_once_with(mock_source)
        assert mock_source.volume == 0.5

    @pytest.mark.asyncio
    async def test_loop_track_skipped_with_force_next(self, service, guilds):
        """force_next=True should bypass track looping."""
        mock_music_data = MagicMock()
        mock_music_data.title = "Song"
        gc = _make_guild_config(
            guild_id=1,
            current_music=mock_music_data,
            loop=LoopMode.TRACK,
            volume=0.5,
            queue=[],
        )
        guilds[1] = gc

        await service._next_music_inner(gc, force_next=True)
        # With empty queue and force_next, should clear
        assert gc.current_music is None
        gc.controller.clear_queue_source.assert_called_once()


class TestNextMusicInnerLoopQueue:
    @pytest.mark.asyncio
    async def test_loop_queue_appends_current_to_end(self, service, guilds):
        mock_current = MagicMock()
        mock_current.title = "Current"
        mock_next = MagicMock()
        mock_next.title = "Next"

        gc = _make_guild_config(
            guild_id=1,
            current_music=mock_current,
            loop=LoopMode.QUEUE,
            queue=[mock_next],
            volume=0.5,
        )
        guilds[1] = gc

        mock_source = MagicMock()
        with patch(
            "src.harpi_lib.services.music_queue.YoutubeDLSource.from_music_data",
            new_callable=AsyncMock,
            return_value=mock_source,
        ):
            await service._next_music_inner(gc, force_next=False)

        # Current track should be re-appended to queue
        assert mock_current in gc.queue
        assert gc.current_music is mock_next


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_clears_queue_and_current(self, service, guilds):
        gc = _make_guild_config(
            guild_id=1,
            queue=[MagicMock()],
            current_music=MagicMock(),
        )
        guilds[1] = gc

        await service.stop(1)
        assert gc.queue == []
        assert gc.current_music is None
        gc.controller.clear_queue_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.stop(999)


class TestSkip:
    @pytest.mark.asyncio
    async def test_skip_calls_next_music_with_force(self, service, guilds):
        gc = _make_guild_config(guild_id=1)
        guilds[1] = gc

        with patch.object(
            service, "next_music", new_callable=AsyncMock
        ) as mock_next:
            await service.skip(1)
            mock_next.assert_called_once_with(gc, force_next=True)

    @pytest.mark.asyncio
    async def test_skip_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.skip(999)


class TestSetLoop:
    @pytest.mark.asyncio
    async def test_sets_loop_mode(self, service, guilds):
        gc = _make_guild_config(guild_id=1, loop=LoopMode.OFF)
        guilds[1] = gc

        await service.set_loop(1, LoopMode.TRACK)
        assert gc.loop == LoopMode.TRACK

    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.set_loop(999, LoopMode.OFF)


class TestSetVolume:
    @pytest.mark.asyncio
    async def test_clamps_volume(self, service, guilds):
        gc = _make_guild_config(guild_id=1, volume=0.5)
        guilds[1] = gc

        await service.set_volume(1, 5.0)
        assert gc.volume == 2.0

        await service.set_volume(1, -1.0)
        assert gc.volume == 0.0

    @pytest.mark.asyncio
    async def test_propagates_to_queue_source(self, service, guilds):
        mock_source = MagicMock()
        mock_source.volume = 0.5
        gc = _make_guild_config(guild_id=1, volume=0.5)
        gc.controller.get_queue_source.return_value = mock_source
        guilds[1] = gc

        await service.set_volume(1, 0.8)
        assert mock_source.volume == 0.8

    @pytest.mark.asyncio
    async def test_handles_volume_set_error(self, service, guilds):
        """If setting volume on source raises, should not propagate."""
        mock_source = MagicMock()
        type(mock_source).volume = property(
            lambda s: 0.5,
            lambda s, v: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        gc = _make_guild_config(guild_id=1, volume=0.5)
        gc.controller.get_queue_source.return_value = mock_source
        guilds[1] = gc

        # Should not raise
        await service.set_volume(1, 0.8)
        assert gc.volume == 0.8

    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self, service):
        with pytest.raises(ValueError, match="não conectada"):
            await service.set_volume(999, 0.5)
