from __future__ import annotations

from discord import Guild, VoiceChannel

from src.harpi_lib.audio.session import LayerInfo, SessionStatus
from src.harpi_lib.music.ytmusic import YTMusicData
from src.panel.schemas import (
    Channel,
    Guild as GuildModel,
    Layer,
    PlaybackStatus,
    Track,
)


def track_data(track: YTMusicData) -> Track:
    return Track(
        title=track.title,
        url=track.url,
        uploader=track.uploader,
        duration=track.duration,
        thumbnail=track.thumbnail,
    )


def layer_data(layer: LayerInfo) -> Layer:
    return Layer(
        id=layer.id,
        title=layer.title,
        url=layer.url,
        volume=layer.volume,
        thumbnail=layer.thumbnail,
    )


def status_data(status: SessionStatus) -> PlaybackStatus:
    return PlaybackStatus(
        guild_id=optional_snowflake(status.guild_id),
        connected=status.connected,
        is_playing=status.is_playing,
        is_paused=status.is_paused,
        current_music=(
            track_data(status.current_music) if status.current_music else None
        ),
        queue=[track_data(track) for track in status.queue],
        layers=[layer_data(layer) for layer in status.layers],
        loop_mode=status.loop_mode.name,
        volume=status.volume,
        progress=status.progress,
        channel_id=optional_snowflake(status.channel_id),
    )


def guild_data(guild: Guild) -> GuildModel:
    return GuildModel(id=snowflake(guild.id), name=guild.name)


def channel_data(channel: VoiceChannel) -> Channel:
    return Channel(id=snowflake(channel.id), name=channel.name)


def snowflake(value: int) -> str:
    return str(value)


def optional_snowflake(value: int | None) -> str | None:
    return None if value is None else str(value)
