from __future__ import annotations

from typing import Any

from discord import Guild, VoiceChannel

from src.harpi_lib.audio.session import LayerInfo, SessionStatus
from src.harpi_lib.music.ytmusic import YTMusicData


def track_data(track: YTMusicData) -> dict[str, Any]:
    return {
        "title": track.title,
        "url": track.url,
        "uploader": track.uploader,
        "duration": track.duration,
        "thumbnail": track.thumbnail,
    }


def layer_data(layer: LayerInfo) -> dict[str, Any]:
    return {
        "id": layer.id,
        "title": layer.title,
        "url": layer.url,
        "volume": layer.volume,
        "thumbnail": layer.thumbnail,
    }


def status_data(status: SessionStatus) -> dict[str, Any]:
    return {
        "guild_id": status.guild_id,
        "connected": status.connected,
        "is_playing": status.is_playing,
        "is_paused": status.is_paused,
        "current_music": (
            track_data(status.current_music) if status.current_music else None
        ),
        "queue": [track_data(track) for track in status.queue],
        "layers": [layer_data(layer) for layer in status.layers],
        "loop_mode": status.loop_mode.name,
        "volume": status.volume,
        "progress": status.progress,
        "channel_id": status.channel_id,
    }


def guild_data(guild: Guild) -> dict[str, Any]:
    return {"id": guild.id, "name": guild.name}


def channel_data(channel: VoiceChannel) -> dict[str, Any]:
    return {"id": channel.id, "name": channel.name}
