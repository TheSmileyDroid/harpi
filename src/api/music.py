"""Music playback API endpoints."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field
from quart import Blueprint
from quart_schema import validate_request, validate_response

from src.api.deps import get_bot, run_on_bot_loop
from src.harpi_lib.audio.session import (
    LoopMode,
    PlaybackSession,
    SessionStatus,
)

bp = Blueprint("music", __name__)

DEFAULT_VOLUME = 0.5
SEEK_TIMEOUT_SECONDS = 10.0

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
    thumbnail: str = ""
    uploader: str = ""


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
    thumbnail: str = ""
    uploader: str = ""


class MusicStatusResponse(BaseModel):
    """Full music playback status for a guild."""

    current_music: MusicTrackResponse | None
    progress: int  # Current track position in milliseconds.
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


class SeekRequest(BaseModel):
    """Request to seek to a position in the current track."""

    guild_id: str
    position: float = Field(..., allow_inf_nan=False)
    absolute: bool = False


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
        "seek",
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
    position: float | None = Field(default=None, allow_inf_nan=False)


# === Helpers ===


def _parse_guild_id(raw: str) -> int | None:
    """Parse a guild_id string to int, returning None on failure."""
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def build_music_status(status: "SessionStatus") -> MusicStatusResponse:
    """Project a session status snapshot into the panel response."""
    current = status.current_music
    return MusicStatusResponse(
        current_music=MusicTrackResponse(
            title=current.title,
            duration=current.duration,
            url=current.url,
            thumbnail=current.thumbnail,
            uploader=current.uploader,
        )
        if current
        else None,
        progress=int(status.progress * 1000),
        queue=[
            QueueItemResponse(
                title=track.title,
                duration=track.duration,
                url=track.url,
                thumbnail=track.thumbnail,
                uploader=track.uploader,
            )
            for track in status.queue
        ],
        layers=[
            MusicLayerResponse(
                title=layer.title,
                id=layer.id,
                url=layer.url,
                volume=layer.volume,
            )
            for layer in status.layers
        ],
        is_playing=status.is_playing,
        is_paused=status.is_paused,
        loop_mode=status.loop_mode.name.lower(),
        volume=status.volume,
    )


async def get_music_data(guild_id: int) -> MusicStatusResponse | None:
    """Get music status data for a specific guild.

    Playback, queue, and background layer fields are all projected from the
    guild's session status snapshot, sampled on the bot's event loop via
    the ``run_on_bot_loop`` bridge.

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

    session = bot.sessions.get(guild_id)
    if session is None:
        return MusicStatusResponse.empty()

    status = await run_on_bot_loop(session.sample_status())
    return build_music_status(status)


def _get_session(guild_id: int) -> "PlaybackSession | None":
    """Resolve the guild's playback session, or None."""
    bot = get_bot()
    if not bot:
        return None
    return bot.sessions.get(guild_id)


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
        data = await get_music_data(int(guild_id))
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.stop())
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.skip())
        return MusicControlResponse(status="ok")
    except Exception as e:
        logger.opt(exception=True).error(f"Error skipping music: {e}")
        return MusicControlResponse(status="", error=str(e)), 500


@bp.route("/api/music/seek", methods=["POST"])
@validate_request(SeekRequest)
@validate_response(MusicControlResponse)
async def music_seek(
    data: SeekRequest,
) -> MusicControlResponse | tuple[MusicControlResponse, int]:
    """Seek to a position in the current track."""
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400
    try:
        session = _get_session(guild_id)
        if session is not None:
            await asyncio.wait_for(
                run_on_bot_loop(
                    session.seek(data.position, data.absolute),
                ),
                timeout=SEEK_TIMEOUT_SECONDS,
            )
        return MusicControlResponse(status="ok")
    except TimeoutError:
        logger.error(f"Seek timed out for guild {guild_id}")
        return MusicControlResponse(status="", error="Seek timed out"), 504
    except Exception as e:
        logger.opt(exception=True).error(f"Error seeking music: {e}")
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.pause())
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.resume())
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.set_loop(loop_mode))
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.set_volume(float(data.volume)))
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.remove_layer(data.layer_id))
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(session.clear_layers())
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
        session = _get_session(guild_id)
        if session is not None:
            await run_on_bot_loop(
                session.set_layer_volume(data.layer_id, float(data.volume))
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
        action: One of 'stop', 'skip', 'seek', 'pause', 'resume', 'loop',
                'remove_layer', 'clean_layers', 'set_volume', 'set_layer_volume'.
        mode: (Optional) Loop mode for 'loop' action.
        layer_id: (Optional) Layer ID for layer actions.
        volume: (Optional) Volume level.
        position: (Optional) Relative position in seconds for 'seek' action.
    """
    guild_id = _parse_guild_id(data.guild_id)
    if guild_id is None:
        return MusicControlResponse(status="", error="Invalid guild_id"), 400

    bot = get_bot()
    if not bot:
        return MusicControlResponse(status="", error="Bot not ready"), 503

    try:
        action = data.action

        if action == "stop":
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.stop())
        elif action == "skip":
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.skip())
        elif action == "seek":
            if data.position is None:
                return MusicControlResponse(
                    status="", error="position required"
                ), 400
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.seek(data.position))
        elif action == "pause":
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.pause())
        elif action == "resume":
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.resume())
        elif action == "loop":
            loop_mode = LOOP_MODE_ALIASES.get(data.mode or "")
            if loop_mode is None:
                return MusicControlResponse(
                    status="", error="Invalid loop mode"
                ), 400
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.set_loop(loop_mode))
        elif action == "remove_layer":
            if not data.layer_id:
                return MusicControlResponse(
                    status="", error="layer_id required"
                ), 400
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.remove_layer(data.layer_id))
        elif action == "clean_layers":
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.clear_layers())
        elif action == "set_volume":
            if data.volume is None:
                return MusicControlResponse(
                    status="", error="volume required"
                ), 400
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(session.set_volume(float(data.volume)))
        elif action == "set_layer_volume":
            if not data.layer_id or data.volume is None:
                return MusicControlResponse(
                    status="", error="layer_id and volume required"
                ), 400
            session = _get_session(guild_id)
            if session is not None:
                await run_on_bot_loop(
                    session.set_layer_volume(data.layer_id, float(data.volume))
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
        session = _get_session(guild_id)
        if session is None and not channel_id:
            return MusicAddResponse(
                status="", error="channel_id required when bot not connected"
            ), 400

        async def _apply_to_session(
            action: Callable[[PlaybackSession], Awaitable[Any]],
        ) -> None:
            manager = get_bot().sessions
            target = await manager.ensure(guild_id, channel_id or 0)
            await action(target)

        if music_type == "layer":
            await run_on_bot_loop(
                _apply_to_session(lambda s: s.add_layer(link))
            )
        else:
            await run_on_bot_loop(_apply_to_session(lambda s: s.play(link)))
        return MusicAddResponse(status="ok")

    except Exception as e:
        logger.opt(exception=True).error(f"Error adding music: {e}")
        return MusicAddResponse(status="", error=str(e)), 500
