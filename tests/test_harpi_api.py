import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from src.harpi_lib.api import GuildConfig, HarpiAPI, LoopMode
from src.harpi_lib.music.mixer import MixerSource


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.loop = asyncio.new_event_loop()
    bot.get_guild = MagicMock()
    return bot


@pytest.fixture
def mock_guild():
    guild = MagicMock()
    guild.id = 12345
    guild.voice_client = None
    guild.get_channel = MagicMock()
    return guild


@pytest.fixture
def mock_voice_channel():
    channel = MagicMock(spec=discord.VoiceChannel)
    channel.id = 67890
    channel.connect = AsyncMock()
    return channel


@pytest.fixture
def mock_voice_client():
    vc = MagicMock()
    vc.is_connected = MagicMock(return_value=True)
    vc.is_playing = MagicMock(return_value=False)
    vc.disconnect = AsyncMock()
    vc.play = MagicMock()
    return vc


@pytest.fixture
def api(mock_bot):
    return HarpiAPI(mock_bot)


class TestHarpiAPIInit:
    def test_creates_empty_guilds_dict(self, api):
        assert api.guilds == {}

    def test_stores_bot_reference(self, api, mock_bot):
        assert api.bot == mock_bot


class TestGuildHelper:
    def test_guild_returns_guild(self, api, mock_bot, mock_guild):
        mock_bot.get_guild.return_value = mock_guild
        result = api._guild(12345)
        assert result == mock_guild

    def test_guild_raises_on_not_found(self, api, mock_bot):
        mock_bot.get_guild.return_value = None
        with pytest.raises(ValueError, match="Servidor não encontrado"):
            api._guild(99999)


class TestVoiceChannelHelper:
    def test_voice_channel_returns_channel(
        self, api, mock_guild, mock_voice_channel
    ):
        mock_guild.get_channel.return_value = mock_voice_channel
        result = api._voice_channel(mock_guild, 67890)
        assert result == mock_voice_channel

    def test_voice_channel_raises_on_not_found(self, api, mock_guild):
        mock_guild.get_channel.return_value = None
        with pytest.raises(ValueError, match="Canal de voz não encontrado"):
            api._voice_channel(mock_guild, 99999)


class TestConnectToVoice:
    @pytest.mark.asyncio
    async def test_connect_creates_guild_config(
        self, api, mock_bot, mock_guild, mock_voice_channel, mock_voice_client
    ):
        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_voice_channel
        mock_voice_channel.connect.return_value = mock_voice_client

        with patch.object(MixerSource, "add_observer", MagicMock()):
            result = await api.connect_to_voice(12345, 67890)

        assert result.id == 12345
        assert result.voice_client == mock_voice_client
        assert result.channel == mock_voice_channel
        assert 12345 in api.guilds

    @pytest.mark.asyncio
    async def test_connect_disconnects_existing_voice(
        self, api, mock_bot, mock_guild, mock_voice_channel, mock_voice_client
    ):
        existing_vc = MagicMock()
        existing_vc.disconnect = AsyncMock()
        mock_guild.voice_client = existing_vc
        mock_bot.get_guild.return_value = mock_guild
        mock_guild.get_channel.return_value = mock_voice_channel
        mock_voice_channel.connect.return_value = mock_voice_client

        with patch.object(MixerSource, "add_observer", MagicMock()):
            await api.connect_to_voice(12345, 67890)

        existing_vc.disconnect.assert_called_once()


class TestStopMusic:
    @pytest.mark.asyncio
    async def test_stop_music_clears_queue(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345,
            mixer=mock_mixer,
            controller=mock_controller,
            queue=[MagicMock()],
        )
        api.guilds[12345] = guild_config

        await api.stop_music(12345)

        assert guild_config.queue == []
        mock_controller.clear_queue_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_music_raises_on_not_connected(self, api):
        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.stop_music(99999)


class TestSkipMusic:
    @pytest.mark.asyncio
    async def test_skip_calls_next_music(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345, mixer=mock_mixer, controller=mock_controller
        )
        api.guilds[12345] = guild_config

        with patch.object(
            api._music_queue, "next_music", AsyncMock()
        ) as mock_next:
            await api.skip_music(12345)
            mock_next.assert_called_once_with(guild_config, force_next=True)

    @pytest.mark.asyncio
    async def test_skip_raises_on_not_connected(self, api):
        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.skip_music(99999)


class TestSetLoop:
    @pytest.mark.asyncio
    async def test_set_loop_off(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345,
            mixer=mock_mixer,
            controller=mock_controller,
            loop=LoopMode.TRACK,
        )
        api.guilds[12345] = guild_config

        await api.set_loop(12345, LoopMode.OFF)
        assert guild_config.loop == LoopMode.OFF

    @pytest.mark.asyncio
    async def test_set_loop_track(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345,
            mixer=mock_mixer,
            controller=mock_controller,
            loop=LoopMode.OFF,
        )
        api.guilds[12345] = guild_config

        await api.set_loop(12345, LoopMode.TRACK)
        assert guild_config.loop == LoopMode.TRACK

    @pytest.mark.asyncio
    async def test_set_loop_raises_on_not_connected(self, api):
        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.set_loop(99999, LoopMode.OFF)


class TestDisconnectVoice:
    @pytest.mark.asyncio
    async def test_disconnect_removes_guild_config(
        self, api, mock_voice_client
    ):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345,
            mixer=mock_mixer,
            controller=mock_controller,
            voice_client=mock_voice_client,
        )
        api.guilds[12345] = guild_config

        await api.disconnect_voice(12345)

        assert 12345 not in api.guilds

    @pytest.mark.asyncio
    async def test_disconnect_calls_voice_disconnect(
        self, api, mock_voice_client
    ):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345,
            mixer=mock_mixer,
            controller=mock_controller,
            voice_client=mock_voice_client,
        )
        api.guilds[12345] = guild_config

        await api.disconnect_voice(12345)

        mock_voice_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_raises_on_not_connected(self, api):
        with pytest.raises(ValueError, match="Guilda não conectada"):
            await api.disconnect_voice(99999)


class TestGetGuildConfig:
    def test_returns_config_when_exists(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345, mixer=mock_mixer, controller=mock_controller
        )
        api.guilds[12345] = guild_config

        result = api.get_guild_config(12345)
        assert result == guild_config

    def test_returns_none_when_not_exists(self, api):
        result = api.get_guild_config(99999)
        assert result is None


class TestSetMusicVolume:
    @pytest.mark.asyncio
    async def test_set_volume_updates_config(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345, mixer=mock_mixer, controller=mock_controller, volume=0.5
        )
        api.guilds[12345] = guild_config

        await api.set_music_volume(12345, 0.8)
        assert guild_config.volume == 0.8

    @pytest.mark.asyncio
    async def test_set_volume_clamps_max(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345, mixer=mock_mixer, controller=mock_controller, volume=0.5
        )
        api.guilds[12345] = guild_config

        await api.set_music_volume(12345, 3.0)
        assert guild_config.volume == 2.0

    @pytest.mark.asyncio
    async def test_set_volume_clamps_min(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345, mixer=mock_mixer, controller=mock_controller, volume=0.5
        )
        api.guilds[12345] = guild_config

        await api.set_music_volume(12345, -0.5)
        assert guild_config.volume == 0.0


class TestNextMusic:
    @pytest.mark.asyncio
    async def test_next_music_sets_none_on_empty_queue(self, api):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        guild_config = GuildConfig(
            id=12345, mixer=mock_mixer, controller=mock_controller, queue=[]
        )
        api.guilds[12345] = guild_config

        await api.next_music(guild_config)

        assert guild_config.current_music is None
        mock_controller.clear_queue_source.assert_called_once()


class TestLoopMode:
    def test_loop_mode_values(self):
        assert LoopMode.OFF.value == 0
        assert LoopMode.TRACK.value == 1
        assert LoopMode.QUEUE.value == 2


class TestGuildConfig:
    def test_guild_config_defaults(self):
        mock_mixer = MagicMock()
        mock_controller = MagicMock()
        config = GuildConfig(
            id=123, mixer=mock_mixer, controller=mock_controller
        )

        assert config.ctx is None
        assert config.voice_client is None
        assert config.queue is None
        assert config.background is None
        assert config.current_music is None
        assert config.loop == LoopMode.OFF
        assert config.channel is None
        assert config.volume == 0.7
