from collections.abc import Awaitable, Callable
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel
from quart import Blueprint
from quart_schema import validate_request, validate_response

from src.api.deps import get_bot, run_on_bot_loop
from src.harpi_lib.audio.session import (
    DEFAULT_VOLUME,
    LoopMode,
    PlaybackSession,
    SessionStatus,
)

bp = Blueprint("music", __name__)

SEEK_TIMEOUT_SECONDS = 10.0


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
