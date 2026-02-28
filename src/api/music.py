"""Music playback API endpoints."""

from typing import cast, Literal

from discord import VoiceClient
from loguru import logger
from pydantic import BaseModel
from quart import Blueprint
from quart_schema import validate_response, validate_request

from src.api.deps import get_api, get_bot, run_on_bot_loop
from src.harpi_lib.api import LoopMode

bp = Blueprint("music", __name__)

DEFAULT_VOLUME = 0.5

LOOP_MODE_ALIASES: dict[str, LoopMode] = {}
for _alias in ("off", "false", "0", "no", "n"):
    LOOP_MODE_ALIASES[_alias] = LoopMode.OFF
for _alias in ("track", "true", "1", "yes", "y", "musica"):
    LOOP_MODE_ALIASES[_alias] = LoopMode.TRACK
for _alias in ("queue", "fila"):
    LOOP_MODE_ALIASES[_alias] = LoopMode.QUEUE


# === Response / Request Models ===


class MusicTrackResponse(BaseModel):
    """Current track information."""

    title: str
    duration: int
    url: str


class MusicLayerResponse(BaseModel):
    """Background audio layer information."""

    title: str
    id: str
    url: str
    volume: float


class QueueItemResponse(BaseModel):
    """Queue track information."""

    title: str
    duration: int
    url: str


class MusicStatusResponse(BaseModel):
    """Full music playback status for a guild."""

    current_music: MusicTrackResponse | None
    progress: int
    queue: list[QueueItemResponse]
    layers: list[MusicLayerResponse]
    is_playing: bool
    is_paused: bool
    loop_mode: str
    volume: float

    @staticmethod
    def empty() -> "MusicStatusResponse":
        """Return a default empty status response."""
        return MusicStatusResponse(
            current_music=None,
            progress=0,
            queue=[],
            layers=[],
            is_playing=False,
            is_paused=False,
            loop_mode=LoopMode.OFF.name.lower(),
            volume=DEFAULT_VOLUME,
        )


class MusicControlResponse(BaseModel):
    """Response for a music control action."""

    status: str
    error: str | None = None


class GuildRequest(BaseModel):
    """Base request containing only guild_id."""

    guild_id: str


class LoopRequest(BaseModel):
    """Request to change loop mode."""

    guild_id: str
    mode: str


class VolumeRequest(BaseModel):
    """Request to change volume."""

    guild_id: str
    volume: int


class LayerRemoveRequest(BaseModel):
    """Request to remove a background layer."""

    guild_id: str
    layer_id: str


class LayerVolumeRequest(BaseModel):
    """Request to set a layer's volume."""

    guild_id: str
    layer_id: str
    volume: int


class MusicAddRequest(BaseModel):
    """Request to add music to queue or as a layer."""

    guild_id: str
    channel_id: str | None = None
    link: str
    type: Literal["queue", "layer"] = "queue"


class MusicAddResponse(BaseModel):
    """Response after adding music."""

    status: str
    error: str | None = None


# === Deprecated models (kept for backward-compat endpoint) ===


class MusicControlRequest(BaseModel):
    """Legacy control request (deprecated)."""

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


# === Helpers ===


def _parse_guild_id(raw: str) -> int | None:
    """Parse a guild_id string to int, returning None on failure."""
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def get_music_data(guild_id: int) -> MusicStatusResponse | None:
    """Get music status data for a specific guild.

    Args:
        guild_id: The guild ID to get music data for.

    Returns:
        MusicStatusResponse with current track, progress, queue, and playback state.
        None if bot is not ready or guild not found.
    """
    bot = get_bot()
    if not bot:
        return None

    guild = bot.get_guild(guild_id)
    if not guild:
        return None

    guild_config = get_api().get_guild_config(guild_id)
    current_music = guild_config.current_music if guild_config else None
    queue = guild_config.queue if guild_config else None
    background = guild_config.background if guild_config else None
    loop_mode = guild_config.loop if guild_config else LoopMode.OFF

    voice_client = (
        cast(VoiceClient, guild.voice_client) if guild.voice_client else None
    )

    return MusicStatusResponse(
        current_music=MusicTrackResponse(
            title=current_music.title,
            duration=current_music.duration,
            url=current_music.url,
        )
        if current_music
        else None,
        progress=0,
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
        volume=guild_config.volume if guild_config else DEFAULT_VOLUME,
    )


def _get_voice_client(guild_id: int) -> VoiceClient | None:
    """Resolve the VoiceClient for a guild, or None."""
    bot = get_bot()
    if not bot:
        return None
    guild = bot.get_guild(guild_id)
    if guild and guild.voice_client:
        return cast(VoiceClient, guild.voice_client)
    return None


# === Endpoints ===


@bp.route("/api/music/<guild_id>/status")
@validate_response(MusicStatusResponse)
async def music_status(
    guild_id: str,
) -> MusicStatusResponse | tuple[MusicStatusResponse, int]:
    """Get music status for a guild.

    Query params:
        guild_id: The guild ID to get status for.
    """
    if not guild_id:
        return MusicStatusResponse.empty(), 400

    try:
        data = get_music_data(int(guild_id))
        if data is None:
            return MusicStatusResponse.empty(), 404

    except ValueError:
        logger.error(f"Guild not found: {guild_id}")
        return MusicStatusResponse.empty(), 400

    return data


# --- Individual control endpoints ---


@bp.route("/api/music/stop", methods=["POST"])
@validate_request(GuildRequest)
@validate_response(MusicControlResponse)
async def music_stop(
    data: GuildRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Stop music playback for a guild."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        await get_api().stop_music(guild_id)
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error stopping music: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/skip", methods=["POST"])
@validate_request(GuildRequest)
@validate_response(MusicControlResponse)
async def music_skip(
    data: GuildRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Skip to the next track in the queue."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        await get_api().skip_music(guild_id)
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error skipping music: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/pause", methods=["POST"])
@validate_request(GuildRequest)
@validate_response(MusicControlResponse)
async def music_pause(
    data: GuildRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Pause music playback."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        vc = _get_voice_client(guild_id)
        if vc:
            vc.pause()
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error pausing music: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/resume", methods=["POST"])
@validate_request(GuildRequest)
@validate_response(MusicControlResponse)
async def music_resume(
    data: GuildRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Resume music playback."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        vc = _get_voice_client(guild_id)
        if vc:
            vc.resume()
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error resuming music: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/loop", methods=["POST"])
@validate_request(LoopRequest)
@validate_response(MusicControlResponse)
async def music_loop(
    data: LoopRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Set the loop mode (off, track, queue)."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    loop_mode = LOOP_MODE_ALIASES.get(data.mode)
    if loop_mode is None:
        return MusicControlResponse(status="", error="Invalid loop mode"), 400
    try:
        await get_api().set_loop(guild_id, loop_mode)
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error setting loop: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/volume", methods=["POST"])
@validate_request(VolumeRequest)
@validate_response(MusicControlResponse)
async def music_volume(
    data: VolumeRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Set the main playback volume."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        await get_api().set_music_volume(guild_id, float(data.volume))
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error setting volume: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/layer/remove", methods=["POST"])
@validate_request(LayerRemoveRequest)
@validate_response(MusicControlResponse)
async def music_layer_remove(
    data: LayerRemoveRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Remove a background audio layer."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        await get_api().remove_background_audio(guild_id, data.layer_id)
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error removing layer: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/layer/clean", methods=["POST"])
@validate_request(GuildRequest)
@validate_response(MusicControlResponse)
async def music_layer_clean(
    data: GuildRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Remove all background audio layers."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        await get_api().clean_background_audios(guild_id)
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error cleaning layers: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/layer/volume", methods=["POST"])
@validate_request(LayerVolumeRequest)
@validate_response(MusicControlResponse)
async def music_layer_volume(
    data: LayerVolumeRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Set volume for a specific background audio layer."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        await get_api().set_background_volume(
            guild_id, data.layer_id, float(data.volume)
        )
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error setting layer volume: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


# --- Deprecated combined endpoint (kept for backward compatibility) ---


@bp.route("/api/music/control", methods=["POST"])
@validate_request(MusicControlRequest)
@validate_response(MusicControlResponse)
async def music_control(
    data: MusicControlRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Control music playback for a guild.

    .. deprecated::
        Use the individual endpoints instead (e.g. POST /api/music/stop).

    Body:
        guild_id: The guild ID.
        action: One of 'stop', 'skip', 'pause', 'resume', 'loop',
                'remove_layer', 'clean_layers', 'set_volume', 'set_layer_volume'.
        mode: (Optional) Loop mode for 'loop' action.
        layer_id: (Optional) Layer ID for layer actions.
        volume: (Optional) Volume level.
    """
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400

    bot = get_bot()
    if not bot:
        return MusicControlResponse(status="", error="Bot not ready"), 503

    try:
        api = get_api()
        action = data.action

        if action == "stop":
            await api.stop_music(guild_id)
        elif action == "skip":
            await api.skip_music(guild_id)
        elif action == "pause":
            vc = _get_voice_client(guild_id)
            if vc:
                vc.pause()
        elif action == "resume":
            vc = _get_voice_client(guild_id)
            if vc:
                vc.resume()
        elif action == "loop":
            loop_mode = LOOP_MODE_ALIASES.get(data.mode or "")
            if loop_mode is None:
                return MusicControlResponse(
                    status="", error="Invalid loop mode"
                ), 400
            await api.set_loop(guild_id, loop_mode)
        elif action == "remove_layer":
            if not data.layer_id:
                return MusicControlResponse(
                    status="", error="layer_id required"
                ), 400
            await api.remove_background_audio(guild_id, data.layer_id)
        elif action == "clean_layers":
            await api.clean_background_audios(guild_id)
        elif action == "set_volume":
            if data.volume is None:
                return MusicControlResponse(
                    status="", error="volume required"
                ), 400
            await api.set_music_volume(guild_id, float(data.volume))
        elif action == "set_layer_volume":
            if not data.layer_id or data.volume is None:
                return MusicControlResponse(
                    status="", error="layer_id and volume required"
                ), 400
            await api.set_background_volume(
                guild_id, data.layer_id, float(data.volume)
            )
        else:
            return MusicControlResponse(status="", error="Invalid action"), 400

        return MusicControlResponse(status="ok")

    except Exception as e:
        logger.opt(exception=True).error(f"Error in music control: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


# --- Add music endpoint ---


@bp.route("/api/music/add", methods=["POST"])
@validate_request(MusicAddRequest)
@validate_response(MusicAddResponse)
async def music_add(
    data: MusicAddRequest,
) -> MusicAddResponse | tuple[MusicAddResponse, int]:
    """Add music to queue via link.

    Body:
        guild_id: The guild ID.
        channel_id: The voice channel ID to connect to.
        link: The music URL (YouTube, etc).
        type: (Optional) 'queue' (default) or 'layer'.
    """
    guild_id_str = data.guild_id
    link = data.link
    music_type = data.type

    if not guild_id_str or not link:
        return MusicAddResponse(
            status="", error="guild_id and link required"
        ), 400

    guild_id = _parse_guild_id(guild_id_str)
    if guild_id is None:
        return MusicAddResponse(status="", error="Invalid guild_id"), 400

    try:
        channel_id = int(data.channel_id) if data.channel_id else None
    except (ValueError, TypeError):
        return MusicAddResponse(status="", error="Invalid channel_id"), 400

    bot = get_bot()
    if not bot:
        return MusicAddResponse(status="", error="Bot not ready"), 503

    try:
        api = get_api()
        guild_config = api.get_guild_config(guild_id)
        if not guild_config and not channel_id:
            return MusicAddResponse(
                status="", error="channel_id required when bot not connected"
            ), 400

        if music_type == "layer":
            await run_on_bot_loop(
                api.add_background_audio(guild_id, channel_id or 0, link)
            )
        else:
            await run_on_bot_loop(
                api.add_music_to_queue(guild_id, channel_id or 0, link)
            )
        return MusicAddResponse(status="ok")

    except Exception as e:
        logger.opt(exception=True).error(f"Error adding music: {e}")
        return MusicAddResponse(status="", error=str(e)), 500
