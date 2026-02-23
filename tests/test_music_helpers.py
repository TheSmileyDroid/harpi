from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext import commands

from src.HarpiLib.music_helpers import (
    AlreadyPlaying,
    guild,
    voice_channel,
    voice_client,
    voice_state,
)


@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    return member


@pytest.fixture
def mock_voice_state_obj():
    vs = MagicMock(spec=discord.VoiceState)
    return vs


@pytest.fixture
def mock_voice_channel_obj():
    channel = MagicMock(spec=discord.VoiceChannel)
    channel.connect = AsyncMock()
    return channel


@pytest.fixture
def mock_guild_obj():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 12345
    return guild


@pytest.fixture
def mock_context(mock_member, mock_guild_obj):
    ctx = MagicMock()
    ctx.author = mock_member
    ctx.guild = mock_guild_obj
    ctx.bot = MagicMock()
    return ctx


class TestVoiceState:
    def test_voice_state_returns_state(
        self, mock_context, mock_member, mock_voice_state_obj
    ):
        mock_member.voice = mock_voice_state_obj
        result = voice_state(mock_context)
        assert result == mock_voice_state_obj

    def test_voice_state_raises_when_not_member(self, mock_context):
        mock_context.author = MagicMock(spec=discord.User)
        with pytest.raises(Exception):
            voice_state(mock_context)

    def test_voice_state_raises_when_no_voice(self, mock_context, mock_member):
        mock_member.voice = None
        with pytest.raises(Exception, match="canal de voz"):
            voice_state(mock_context)


class TestVoiceChannel:
    def test_voice_channel_returns_channel(
        self,
        mock_context,
        mock_member,
        mock_voice_state_obj,
        mock_voice_channel_obj,
    ):
        mock_member.voice = mock_voice_state_obj
        mock_voice_state_obj.channel = mock_voice_channel_obj

        result = voice_channel(mock_context)
        assert result == mock_voice_channel_obj

    def test_voice_channel_raises_when_no_channel(
        self, mock_context, mock_member, mock_voice_state_obj
    ):
        mock_member.voice = mock_voice_state_obj
        mock_voice_state_obj.channel = None

        with pytest.raises(Exception, match="canal de voz"):
            voice_channel(mock_context)


class TestGuild:
    def test_guild_returns_guild(self, mock_context, mock_guild_obj):
        result = guild(mock_context)
        assert result == mock_guild_obj

    def test_guild_raises_in_dm(self, mock_context):
        mock_context.guild = None
        with pytest.raises(commands.NoPrivateMessage):
            guild(mock_context)


class TestVoiceClient:
    @pytest.mark.asyncio
    async def test_voice_client_returns_existing(
        self,
        mock_context,
        mock_member,
        mock_voice_state_obj,
        mock_voice_channel_obj,
    ):
        mock_member.voice = mock_voice_state_obj
        mock_voice_state_obj.channel = mock_voice_channel_obj

        existing_vc = MagicMock()
        mock_context.bot.voice_clients = [existing_vc]

        with patch(
            "src.HarpiLib.music_helpers.discord.utils.get",
            return_value=existing_vc,
        ):
            with patch(
                "src.HarpiLib.music_helpers.guild",
                return_value=mock_context.guild,
            ):
                result = await voice_client(mock_context)
                assert result == existing_vc

    @pytest.mark.asyncio
    async def test_voice_client_connects_new(
        self,
        mock_context,
        mock_member,
        mock_voice_state_obj,
        mock_voice_channel_obj,
    ):
        mock_member.voice = mock_voice_state_obj
        mock_voice_state_obj.channel = mock_voice_channel_obj

        new_vc = MagicMock()
        mock_voice_channel_obj.connect = AsyncMock(return_value=new_vc)

        mock_context.bot.voice_clients = []

        with patch(
            "src.HarpiLib.music_helpers.discord.utils.get", return_value=None
        ):
            with patch(
                "src.HarpiLib.music_helpers.guild",
                return_value=mock_context.guild,
            ):
                with patch(
                    "src.HarpiLib.music_helpers.voice_channel",
                    return_value=mock_voice_channel_obj,
                ):
                    result = await voice_client(mock_context)
                    assert result == new_vc


class TestAlreadyPlaying:
    def test_is_command_error(self):
        assert issubclass(AlreadyPlaying, Exception)

    def test_can_be_raised(self):
        try:
            raise AlreadyPlaying("test message")
        except AlreadyPlaying as e:
            assert str(e) == "test message"
