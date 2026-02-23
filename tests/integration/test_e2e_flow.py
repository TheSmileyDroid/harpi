import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.HarpiLib.api import LoopMode


class TestFullPlaybackFlow:
    @pytest.mark.asyncio
    async def test_connect_creates_guild_config(
        self, mock_bot, mock_guild, mock_voice_channel, mock_voice_client
    ):
        from src.HarpiLib.api import HarpiAPI

        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_voice_channel
        mock_voice_channel.connect.return_value = mock_voice_client

        api = HarpiAPI(mock_bot)

        result = await api.connect_to_voice(12345, 67890)

        assert result.id == 12345
        assert result.voice_client == mock_voice_client
        assert result.controller is not None
        assert result.mixer is not None
        assert 12345 in api.guilds

    @pytest.mark.asyncio
    async def test_queue_lifecycle(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        mock_source = MagicMock()
        mock_source.volume = 0.7

        mock_music1 = MagicMock()
        mock_music1.title = "Song 1"
        mock_music2 = MagicMock()
        mock_music2.title = "Song 2"

        guild_config.queue = [mock_music1, mock_music2]
        guild_config.current_music = None

        with patch("src.HarpiLib.api.YoutubeDLSource") as mock_ytdl:
            mock_ytdl.from_music_data = AsyncMock(return_value=mock_source)
            await api.next_music(guild_config)

        assert guild_config.current_music == mock_music1
        assert len(guild_config.queue) == 1
        assert guild_config.controller.get_queue_source() == mock_source

        with patch("src.HarpiLib.api.YoutubeDLSource") as mock_ytdl:
            mock_ytdl.from_music_data = AsyncMock(return_value=mock_source)
            await api.skip_music(12345)

        assert guild_config.current_music == mock_music2
        assert len(guild_config.queue) == 0

        await api.stop_music(12345)

        assert guild_config.queue == []
        assert guild_config.current_music is None
        assert guild_config.controller.get_queue_source() is None

    @pytest.mark.asyncio
    async def test_disconnect_clears_guild(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        await api.disconnect_voice(12345)

        assert 12345 not in api.guilds


class TestLoopModes:
    @pytest.mark.asyncio
    async def test_loop_track_mode(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        mock_source = MagicMock()
        mock_source.volume = 0.7

        mock_music = MagicMock()
        mock_music.title = "Looping Song"
        guild_config.current_music = mock_music
        guild_config.loop = LoopMode.TRACK

        with patch("src.HarpiLib.api.YoutubeDLSource") as mock_ytdl:
            mock_ytdl.from_music_data = AsyncMock(return_value=mock_source)
            await api.next_music(guild_config)

        assert guild_config.current_music == mock_music
        assert guild_config.controller.get_queue_source() == mock_source

    @pytest.mark.asyncio
    async def test_loop_queue_mode(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        mock_source = MagicMock()
        mock_source.volume = 0.7

        mock_music1 = MagicMock()
        mock_music1.title = "Song 1"
        mock_music2 = MagicMock()
        mock_music2.title = "Song 2"

        guild_config.queue = [mock_music1]
        guild_config.current_music = mock_music2
        guild_config.loop = LoopMode.QUEUE

        with patch("src.HarpiLib.api.YoutubeDLSource") as mock_ytdl:
            mock_ytdl.from_music_data = AsyncMock(return_value=mock_source)
            await api.next_music(guild_config)

        assert mock_music2 in guild_config.queue


class TestVolumeControl:
    @pytest.mark.asyncio
    async def test_volume_change_flow(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        await api.set_music_volume(12345, 0.8)

        assert guild_config.volume == 0.8

    @pytest.mark.asyncio
    async def test_volume_clamped_to_range(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        await api.set_music_volume(12345, 3.0)
        assert guild_config.volume == 2.0

        await api.set_music_volume(12345, -1.0)
        assert guild_config.volume == 0.0

    @pytest.mark.asyncio
    async def test_volume_affects_queue_source(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        mock_source = MagicMock()
        mock_source.volume = 0.7
        guild_config.controller.set_queue_source(mock_source)

        await api.set_music_volume(12345, 0.9)

        assert mock_source.volume == 0.9


class TestBackgroundAudio:
    @pytest.mark.asyncio
    async def test_background_audio_lifecycle(self, harpi_api_with_guild):
        api, guild_config = harpi_api_with_guild

        mock_source = MagicMock()
        mock_source.id = "test-id"
        mock_source.title = "Background Track"
        mock_source.volume = 0.7

        guild_config.background = {}

        layer_id = guild_config.controller.add_layer(mock_source)
        guild_config.background[layer_id] = mock_source

        sounds = guild_config.controller.get_playing_sounds()
        track_sounds = [s for t, s in sounds if t == "track"]
        assert len(track_sounds) == 1
        assert track_sounds[0] == mock_source

        await api.set_background_volume(12345, layer_id, 0.5)

        assert mock_source.volume == 0.5

        result = await api.remove_background_audio(12345, layer_id)

        assert result == mock_source
        assert layer_id not in guild_config.background
        sounds = guild_config.controller.get_playing_sounds()
        track_sounds = [s for t, s in sounds if t == "track"]
        assert len(track_sounds) == 0


class TestMultipleGuilds:
    @pytest.mark.asyncio
    async def test_multiple_guilds_isolated(self, mock_bot):
        from src.HarpiLib.api import GuildConfig, HarpiAPI

        api = HarpiAPI(mock_bot)

        controller1 = MagicMock()
        mixer1 = MagicMock()
        config1 = GuildConfig(id=111, mixer=mixer1, controller=controller1)
        api.guilds[111] = config1

        controller2 = MagicMock()
        mixer2 = MagicMock()
        config2 = GuildConfig(id=222, mixer=mixer2, controller=controller2)
        api.guilds[222] = config2

        await api.stop_music(111)

        assert 111 in api.guilds
        assert 222 in api.guilds
        assert config1.queue == []
        assert config2.queue is None

        await api.set_music_volume(111, 0.5)
        assert config1.volume == 0.5
        assert config2.volume == 0.7


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_operations_on_nonexistent_guild(self, mock_bot):
        from src.HarpiLib.api import HarpiAPI

        api = HarpiAPI(mock_bot)

        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.stop_music(99999)

        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.skip_music(99999)

        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.set_loop(99999, LoopMode.OFF)

        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.disconnect_voice(99999)
