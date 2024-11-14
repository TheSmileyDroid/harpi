"""Models for the guilds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from src.cogs.music import LoopMode  # noqa: TCH001

if TYPE_CHECKING:
    import discord

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


class IGuild(BaseModel):
    """Guild model."""

    model_config = ConfigDict(coerce_numbers_to_str=True)

    id: str
    name: str
    description: str | None
    approximate_member_count: int
    icon: str | None

    @classmethod
    def from_discord_guild(cls, guild: discord.Guild) -> IGuild:
        return cls(
            id=str(guild.id),
            name=guild.name,
            description=guild.description,
            approximate_member_count=guild.approximate_member_count or 0,
            icon=getattr(guild.icon, "url", None),
        )


class IMusicState(BaseModel):
    """Model for sending all the Music state of a guild."""

    queue: list[IMusic]
    loop_mode: LoopMode
    progress: float


@runtime_checkable
class AudioSourceTrackedProtocol(Protocol):
    progress: float
