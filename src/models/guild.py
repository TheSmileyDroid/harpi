"""Models for the guilds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import discord.ext
import discord.ext.commands
from pydantic import BaseModel, ConfigDict

from src.cogs.music import LoopMode, MusicCog
from src.HarpiLib.nested import get_nested_attr

if TYPE_CHECKING:
    import discord
    from discord import VoiceClient
    from discord.ext.commands import Bot

    from src.HarpiLib.musicdata.ytmusicdata import YTMusicData


class IMusic(BaseModel):
    """Music data model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str
    url: str
    thumbnail: str | None
    duration: float
    artists: list[str] | None
    album: str | None
    categories: list[str]
    release_year: int | None

    @classmethod
    def from_musicdata(cls, music_data: YTMusicData) -> IMusic:
        return cls(
            title=music_data.title,
            url=music_data.url,
            thumbnail=music_data.thumbnail,
            duration=music_data.duration or 0,
            artists=music_data.get_metadata("artists"),
            album=music_data.get_metadata("album"),
            categories=music_data.get_metadata("categories") or [],
            release_year=music_data.get_metadata("release_year") or 0,
        )


class ITextChannel(BaseModel):
    """Text channel model."""

    id: str
    name: str

    @classmethod
    def from_discord_channel(
        cls,
        channel: discord.TextChannel,
    ) -> ITextChannel:
        return cls(
            id=str(channel.id),
            name=channel.name,
        )


class IVoiceChannel(BaseModel):
    """Voice channel model."""

    id: str
    name: str
    members: list[str]

    @classmethod
    def from_discord_channel(
        cls,
        channel: discord.VoiceChannel,
    ) -> IVoiceChannel:
        return cls(
            id=str(channel.id),
            name=channel.name,
            members=[str(member.id) for member in channel.members],
        )


class IGuild(BaseModel):
    """Guild model."""

    model_config = ConfigDict(coerce_numbers_to_str=True)

    id: str
    name: str
    description: str | None
    approximate_member_count: int
    icon: str | None
    voice_channels: list[IVoiceChannel] | None
    text_channels: list[ITextChannel] | None

    @classmethod
    def from_discord_guild(cls, guild: discord.Guild) -> IGuild:
        return cls(
            id=str(guild.id),
            name=guild.name,
            description=guild.description,
            approximate_member_count=guild.approximate_member_count or 0,
            icon=getattr(guild.icon, "url", None),
            voice_channels=[
                IVoiceChannel.from_discord_channel(channel)
                for channel in guild.voice_channels
            ],
            text_channels=[
                ITextChannel.from_discord_channel(channel)
                for channel in guild.text_channels
            ],
        )


class IMusicState(BaseModel):
    """Model for sending all the Music state of a guild."""

    queue: list[IMusic]
    loop_mode: LoopMode
    progress: float
    current_voice_channel: IVoiceChannel | None
    paused: bool = False
    playing: bool = False

    @classmethod
    def from_music_cog(
        cls,
        music_cog: MusicCog,
        bot: Bot,
        guild_id: int,
    ) -> IMusicState:
        active_track = music_cog.current_music.get(guild_id, None)

        music_queue = music_cog.music_queue.get(guild_id, []).copy()
        result_queue = []
        if active_track:
            music_queue.insert(0, active_track)
        for music in music_queue:
            result_queue.append(  # noqa: PERF401
                IMusic.from_musicdata(
                    music,
                ),
            )
        progress = 0
        voice_client: VoiceClient | None = get_nested_attr(
            bot.get_guild(guild_id),
            "voice_client",
            None,
        )
        if (
            voice_client
            and voice_client.source
            and hasattr(voice_client.source, "progress")
        ):
            source = cast(AudioSourceTrackedProtocol, voice_client.source)
            progress = source.progress
        current_voice_channel = get_nested_attr(
            bot.get_guild(guild_id),
            "voice_client.channel",
            None,
        )

        return cls(
            queue=result_queue,
            loop_mode=music_cog.loop_map.get(guild_id, LoopMode.OFF),
            progress=progress,
            current_voice_channel=IVoiceChannel.from_discord_channel(
                current_voice_channel,
            )
            if current_voice_channel
            else None,
            paused=voice_client.is_paused() if voice_client else False,
            playing=voice_client.is_playing() if voice_client else False,
        )


@runtime_checkable
class AudioSourceTrackedProtocol(Protocol):
    progress: float
