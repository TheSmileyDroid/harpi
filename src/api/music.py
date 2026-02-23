from typing import Protocol, cast, runtime_checkable, Literal

from discord import VoiceClient
from loguru import logger
from pydantic import BaseModel
from quart import Blueprint
from quart_schema import validate_response, validate_request

from src.discord_bot import get_bot_instance
from src.HarpiLib.api import LoopMode


@runtime_checkable
class AudioSourceTrackedProtocol(Protocol):
    progress: float


bp = Blueprint("music", __name__)


class MusicTrackResponse(BaseModel):
    title: str
    duration: int
    url: str


class MusicLayerResponse(BaseModel):
    title: str
    id: str
    url: str
    volume: float


class QueueItemResponse(BaseModel):
    title: str
    duration: int
    url: str


class MusicStatusResponse(BaseModel):
    current_music: MusicTrackResponse | None
    progress: int
    queue: list[QueueItemResponse]
    layers: list[MusicLayerResponse]
    is_playing: bool
    is_paused: bool
    loop_mode: str
    volume: float


class MusicControlRequest(BaseModel):
    guild_id: str
    action: Literal[
        "stop",
        "skip",
        "pause",
        "resume",
        "loop",
        "remove_layer",
        "clean_layers",
        "set_volume",
        "set_layer_volume",
    ]
    mode: None | str
    layer_id: str | None = None
    volume: int | None = None


class MusicControlResponse(BaseModel):
    status: str
    error: str | None = None


class MusicAddRequest(BaseModel):
    guild_id: str
    channel_id: str | None = None
    link: str
    type: Literal["queue", "layer"] = "queue"


class MusicAddResponse(BaseModel):
    status: str
    error: str | None = None


def get_music_data(guild_id: int) -> MusicStatusResponse | None:
    """Get music status data for a specific guild.

    Args:
        guild_id: The guild ID to get music data for.

    Returns:
        MusicStatusResponse: Music data including current track, progress, queue, and playback state.
        None: If bot is not ready or guild not found.
    """
    bot = get_bot_instance()
    if not bot:
        return None

    guild = bot.get_guild(guild_id)
    if not guild:
        return None

    guild_config = bot.api.get_guild_config(guild_id)
    current_music = guild_config.current_music if guild_config else None
    queue = guild_config.queue if guild_config else None
    background = guild_config.background if guild_config else None
    loop_mode = guild_config.loop if guild_config else LoopMode.OFF
    progress = 0

    voice_client = (
        cast(VoiceClient, guild.voice_client) if guild.voice_client else None
    )
    if voice_client and (source := voice_client.source):
        source = cast(AudioSourceTrackedProtocol, cast(object, source))
        progress = 0

    return MusicStatusResponse(
        current_music=MusicTrackResponse(
            title=current_music.title,
            duration=current_music.duration,
            url=current_music.url,
        )
        if current_music
        else None,
        progress=round(progress),
        queue=[
            QueueItemResponse(title=m.title, duration=m.duration, url=m.url)
            for m in (queue if queue else [])
        ],
        layers=[
            MusicLayerResponse(
                title=layer.title,
                id=layer.id,
                url=layer.url,
                volume=layer.volume,
            )
            for layer in (background.values() if background else [])
        ],
        is_playing=voice_client.is_playing() if voice_client else False,
        is_paused=voice_client.is_paused() if voice_client else False,
        loop_mode=loop_mode.name.lower(),
        volume=guild_config.volume if guild_config else 0.5,
    )


@bp.route("/api/music/<guild_id>/status")
@validate_response(MusicStatusResponse)
async def music_status(guild_id: str):
    """Get music status for a guild.

    Query params:
        guild_id: The guild ID to get status for.

    Returns:
        JSON with music data or error.
    """
    if not guild_id:
        return MusicStatusResponse(
            current_music=None,
            progress=0,
            queue=[],
            layers=[],
            is_playing=False,
            is_paused=False,
            loop_mode="off",
            volume=0.5,
        ), 400

    try:
        data = get_music_data(int(guild_id))
        if data is None:
            return MusicStatusResponse(
                current_music=None,
                progress=0,
                queue=[],
                layers=[],
                is_playing=False,
                is_paused=False,
                loop_mode="off",
                volume=0.5,
            ), 404

    except ValueError:
        logger.error(f"Guild not found: {guild_id}")
        return MusicStatusResponse(
            current_music=None,
            progress=0,
            queue=[],
            layers=[],
            is_playing=False,
            is_paused=False,
            loop_mode="off",
            volume=0.5,
        ), 400

    return data


@bp.route("/api/music/control", methods=["POST"])
@validate_request(MusicControlRequest)
@validate_response(MusicControlResponse)
async def music_control(data: MusicControlRequest):
    """Control music playback for a guild.

    Body:
        guild_id: The guild ID.
        action: One of 'stop', 'skip', 'pause', 'resume', 'loop'.
        mode: (Optional) Loop mode for 'loop' action.

    Returns:
        JSON with status or error.
    """
    guild_id = data.guild_id
    action = data.action

    if not guild_id:
        return MusicControlResponse(status="", error="guild_id required"), 400

    try:
        guild_id = int(guild_id)
    except (ValueError, TypeError):
        return MusicControlResponse(status="", error="Invalid guild_id"), 400

    bot = get_bot_instance()
    if not bot:
        return MusicControlResponse(status="", error="Bot not ready"), 503

    try:
        if action == "stop":
            await bot.api.stop_music(guild_id)
        elif action == "skip":
            await bot.api.skip_music(guild_id)
        elif action == "pause":
            guild = bot.get_guild(guild_id)
            if guild and guild.voice_client:
                voice_client = cast(VoiceClient, guild.voice_client)
                voice_client.pause()
        elif action == "resume":
            guild = bot.get_guild(guild_id)
            if guild and guild.voice_client:
                voice_client = cast(VoiceClient, guild.voice_client)
                voice_client.resume()
        elif action == "loop":
            mode = data.mode
            if mode in {"off", "false", "0", "no", "n"}:
                await bot.api.set_loop(guild_id, LoopMode.OFF)
            elif mode in {"track", "true", "1", "yes", "y", "musica"}:
                await bot.api.set_loop(guild_id, LoopMode.TRACK)
            elif mode in {"queue", "fila"}:
                await bot.api.set_loop(guild_id, LoopMode.QUEUE)
            else:
                return MusicControlResponse(
                    status="", error="Invalid loop mode"
                ), 400
        elif action == "remove_layer":
            layer_id = data.layer_id
            if not layer_id:
                return MusicControlResponse(
                    status="", error="layer_id required"
                ), 400
            await bot.api.remove_background_audio(guild_id, layer_id)
        elif action == "clean_layers":
            await bot.api.clean_background_audios(guild_id)
        elif action == "set_volume":
            volume = data.volume
            if volume is None:
                return MusicControlResponse(
                    status="", error="volume required"
                ), 400
            await bot.api.set_music_volume(guild_id, float(volume))
        elif action == "set_layer_volume":
            layer_id = data.layer_id
            volume = data.volume
            if not layer_id or volume is None:
                return MusicControlResponse(
                    status="", error="layer_id and volume required"
                ), 400
            await bot.api.set_background_volume(
                guild_id, layer_id, float(volume)
            )
        else:
            return MusicControlResponse(status="", error="Invalid action"), 400
        return MusicControlResponse(status="ok")

    except Exception as e:
        logger.error(f"Error in music control: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/add", methods=["POST"])
@validate_request(MusicAddRequest)
@validate_response(MusicAddResponse)
async def music_add(data: MusicAddRequest):
    """Add music to queue via link.

    Body:
        guild_id: The guild ID.
        channel_id: The voice channel ID to connect to.
        link: The music URL (YouTube, etc).
        type: (Optional) 'queue' (default) or 'layer'.

    Returns:
        JSON with status or error.
    """
    guild_id = data.guild_id
    channel_id = data.channel_id
    link = data.link
    music_type = data.type

    if not guild_id or not link:
        return MusicAddResponse(
            status="", error="guild_id and link required"
        ), 400

    try:
        guild_id = int(guild_id)
        channel_id = int(channel_id) if channel_id else None
    except (ValueError, TypeError):
        return MusicAddResponse(
            status="", error="Invalid guild_id or channel_id"
        ), 400

    bot = get_bot_instance()
    if not bot:
        return MusicAddResponse(status="", error="Bot not ready"), 503

    try:
        guild_config = bot.api.get_guild_config(guild_id)
        if not guild_config and not channel_id:
            return MusicAddResponse(
                status="", error="channel_id required when bot not connected"
            ), 400

        if music_type == "layer":
            await bot.api.add_background_audio(guild_id, channel_id or 0, link)
        else:
            await bot.api.add_music_to_queue(guild_id, channel_id or 0, link)
        return MusicAddResponse(status="ok")

    except Exception as e:
        logger.error(f"Error adding music: {e}")
        return MusicAddResponse(status="", error=str(e)), 500
