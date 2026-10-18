from __future__ import annotations

from discord import Guild, VoiceChannel

from src.harpi_lib.audio.session import LayerInfo, SessionStatus
from src.harpi_lib.music.ytmusic import YTMusicData
from src.panel.schemas import (
    Channel,
    ConnectionEvent,
    Guild as GuildModel,
    Layer,
    PlaybackStatus,
    Presence,
    Track,
    Viewer,
)
from src.storage.registry import ConnectionRecord, ViewerRecord


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


def viewer_data(viewer: ViewerRecord) -> Viewer:
    return Viewer(
        user_id=viewer.user_id,
        username=viewer.username,
        display_name=viewer.display_name,
        channel_id=optional_snowflake(viewer.channel_id),
        channel_name=viewer.channel_name,
        seen_at=viewer.seen_at,
    )


def connection_data(record: ConnectionRecord) -> ConnectionEvent:
    return ConnectionEvent(
        action=record.action,
        channel_id=optional_snowflake(record.channel_id),
        channel_name=record.channel_name,
        actor_id=optional_snowflake(record.actor_id),
        actor_name=record.actor_name,
        at=record.at,
    )


def presence_data(
    guild_id: int,
    viewers: list[ViewerRecord],
    last_connection: ConnectionRecord | None,
) -> Presence:
    return Presence(
        guild_id=snowflake(guild_id),
        viewers=[viewer_data(viewer) for viewer in viewers],
        last_connection=(
            connection_data(last_connection)
            if last_connection is not None
            else None
        ),
    )


def snowflake(value: int) -> str:
    return str(value)


def optional_snowflake(value: int | str | None) -> str | None:
    return None if value is None else str(value)
