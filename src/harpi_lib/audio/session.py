"""PlaybackSession — one deep module holding a guild's playback state.

A session owns everything a single guild's audio needs: the voice client,
the :class:`AudioController`, the :class:`MixerSource`, the queue, the
current track, the loop mode, the volume, and the mixer's end-of-track
observer wiring.  The session is the seam the cogs, routes, and tests
cross.

Threading contract
------------------
The bot's event loop is the single writer for all session state.  Every
session verb must therefore run on the **bot's** loop; verbs that touch
discord.py's async voice APIs (``leave``) or spawn FFmpeg (``seek``) are
async, while ``start`` and ``cleanup`` are synchronous but still
bot-loop-bound.  The mixer itself is an exception by design:
``MixerSource.read()`` runs on discord.py's voice-sending thread, and its
``queue_end`` / ``track_end`` observers fire from that same thread.  Those
callbacks must never touch session state directly — they marshal work back
onto the bot's event loop (``asyncio.run_coroutine_threadsafe`` /
``call_soon_threadsafe``) before mutating anything.  Anything else that
needs a session (the web panel, the cogs) reaches it through the
:class:`SessionManager` and the ``run_on_bot_loop`` bridge, never by
calling into the controller or mixer directly.
"""

from __future__ import annotations

import asyncio
import enum
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

import discord
from loguru import logger

from src.harpi_lib.audio.controller import AudioController
from src.harpi_lib.audio.mixer import MixerSource
from src.harpi_lib.music.ytmusicdata import (
    ProbeEnvironmentError,
    YoutubeDLSource,
    YTMusicData,
)

# Fallback seek cap in seconds for tracks with unknown duration.
MAX_SEEK_SECONDS = 4 * 3600

# Max seconds allowed for loading a track's audio source before it is
# treated as failed and skipped.
TRACK_LOAD_TIMEOUT = 60.0

# Default music queue volume (0.0-2.0).
DEFAULT_VOLUME = 0.7

# Default background layer volume (0.0-2.0).
DEFAULT_LAYER_VOLUME = 0.7


@dataclass(frozen=True)
class LayerInfo:
    """Immutable description of a playing background layer."""

    id: str
    title: str
    url: str
    volume: float


class LoopMode(enum.Enum):
    """Enum for loop modes (off, track, queue)."""

    OFF = 0
    TRACK = 1
    QUEUE = 2


@dataclass(frozen=True)
class SessionStatus:
    """Immutable snapshot of a session's state, safe to pass across threads.

    The snapshot is produced on the bot's event loop (sampled from the
    voice client) and is immutable, so once built it can be handed to
    any reader — the panel JSON, the HTMX fragments, the server status,
    the chat ``list`` command.
    """

    guild_id: int
    connected: bool
    is_playing: bool
    is_paused: bool
    current_music: YTMusicData | None = None
    queue: tuple[YTMusicData, ...] = ()
    layers: tuple[LayerInfo, ...] = ()
    loop_mode: LoopMode = LoopMode.OFF
    volume: float = DEFAULT_VOLUME
    progress: float = 0.0
    channel_id: int | None = None


class PlaybackSession:
    """All playback state and behaviour for a single guild.

    The controller and the mixer are internal seams: nothing outside the
    session touches them.  State is read through :attr:`status` and
    changed through the session's verbs (``play``, ``stop``, ``skip``,
    ``seek``, ``set_loop``, ``set_volume``, ``pause``, ``resume``,
    ``toggle_pause``, ``remove``, ``move``, ``clear_queue``, ``leave``,
    ``add_layer``, ``remove_layer``, ``clear_layers``,
    ``set_layer_volume``).
    """

    def __init__(
        self,
        guild_id: int,
        voice_client: discord.VoiceClient,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        volume: float = DEFAULT_VOLUME,
    ) -> None:
        self._guild_id = guild_id
        self._voice_client = voice_client
        self._loop = (
            loop if loop is not None else getattr(voice_client, "loop", None)
        )

        self._controller = AudioController()
        self._mixer = MixerSource(self._controller)
        self._wire_mixer_observers()

        self._queue: list[YTMusicData] = []
        self._layers: dict[str, YoutubeDLSource] = {}
        self._current_music: YTMusicData | None = None
        self._loop_mode = LoopMode.OFF
        self._volume = volume
        self._announcer: Callable[[str], Awaitable[Any]] | None = None
        self._advance_lock = asyncio.Lock()

    def _wire_mixer_observers(self) -> None:
        """Hook the mixer's end-of-track events to the session's own handlers."""
        self._mixer.add_observer("queue_end", self._on_queue_end)
        self._mixer.add_observer("track_end", self._on_track_end)

    # --- End-of-track handlers (fired from the voice-sending thread) ---

    def _on_queue_end(self) -> None:
        """The current queue track finished reading.

        Called from the voice-sending thread.  The controller already
        cleared and cleaned the finished source; marshal the advance back
        onto the bot's event loop as the threading contract requires.
        """
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._spawn_advance)
        else:
            logger.warning(
                f"No event loop bound to session for guild {self._guild_id}; "
                "cannot advance after track end"
            )

    def _spawn_advance(self) -> None:
        """Run on the bot's event loop; schedule the next advance."""
        asyncio.ensure_future(self._advance())

    def _on_track_end(self, to_remove: list[discord.AudioSource]) -> None:
        """A background layer finished reading.

        The controller already removed and cleaned the finished sources.
        Drop the finished layers from the session's registry, marshalling
        back onto the bot's event loop as the threading contract requires.
        """
        if self._loop is not None:
            self._loop.call_soon_threadsafe(
                self._drop_finished_layers, tuple(to_remove)
            )

    def _drop_finished_layers(
        self, to_remove: tuple[discord.AudioSource, ...]
    ) -> None:
        """Run on the bot's event loop; drop finished layers from the registry."""
        for source in to_remove:
            layer_id = getattr(source, "id", None)
            if layer_id is not None:
                self._layers.pop(layer_id, None)

    # --- Public API ---

    @property
    def guild_id(self) -> int:
        return self._guild_id

    def set_announcer(
        self, announcer: Callable[[str], Awaitable[Any]] | None
    ) -> None:
        """Bind an async sink for user-facing announcements.

        The cogs bind ``ctx.send``; the panel can pass ``None`` or its own
        sink.  Announcements never raise back into the caller.
        """
        self._announcer = announcer

    @property
    def status(self) -> SessionStatus:
        """Snapshot of this session's state; read from the bot's event loop.

        Sampling the voice client from any other thread races against the
        bot loop, the session's single writer.  Panel readers cross the
        loop via the ``run_on_bot_loop`` bridge; the immutable snapshot
        is safe to hand around once built.
        """
        voice_client = self._voice_client
        return SessionStatus(
            guild_id=self._guild_id,
            connected=voice_client.is_connected(),
            is_playing=voice_client.is_playing(),
            is_paused=voice_client.is_paused(),
            current_music=self._current_music,
            queue=tuple(self._queue),
            layers=tuple(
                LayerInfo(
                    id=source.id,
                    title=source.title,
                    url=source.url,
                    volume=float(source.volume),
                )
                for source in self._layers.values()
            ),
            loop_mode=self._loop_mode,
            volume=self._volume,
            progress=self._controller.get_queue_position(),
            channel_id=getattr(voice_client.channel, "id", None),
        )

    async def sample_status(self) -> SessionStatus:
        """Return the current :class:`SessionStatus` snapshot.

        Awaited from another event loop via ``run_on_bot_loop`` so the
        snapshot is taken on the bot loop, the session's single writer.
        """
        return self.status

    def start(self) -> None:
        """Begin streaming the mixer to the voice client."""
        self._voice_client.play(self._mixer)

    def cleanup(self) -> None:
        """Release the controller's sources and shut down the mixer.

        Does not touch the voice client; callers that want to leave the
        channel use :meth:`leave`.
        """
        self._controller.cleanup_all()
        self._mixer.cleanup()

    async def leave(self) -> None:
        """Disconnect the voice client if it is still connected."""
        voice_client = self._voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()

    # --- Playback verbs ---

    async def play(self, link: str) -> int:
        """Resolve *link* and add every track found to the queue.

        If the session is idle this also starts playing the first track.
        Returns the number of tracks added.  Raises :class:`ValueError`
        when nothing is found.
        """
        music_data_list = await YTMusicData.from_url(link)
        if not music_data_list:
            raise ValueError("Nenhuma música encontrada para este link")
        self._queue.extend(music_data_list)
        logger.info(
            f"Added {len(music_data_list)} track(s) to queue in guild {self._guild_id}"
        )
        if self._current_music is None:
            await self._advance()
        return len(music_data_list)

    async def stop(self) -> None:
        """Stop current playback and clear the queue."""
        self._queue.clear()
        self._current_music = None
        self._controller.clear_queue_source()
        logger.info(
            f"Stopped music and cleared queue in guild {self._guild_id}"
        )

    async def skip(self) -> None:
        """Skip the current track and play the next."""
        logger.info(f"Skipping track in guild {self._guild_id}")
        await self._advance(force_next=True)

    async def seek(self, position: float, absolute: bool = False) -> bool:
        """Seek the current track to *position* seconds (relative by default).

        Returns ``True`` when the position changed; ``False`` when there is
        no seekable track to move.  Raises :class:`ValueError` for an
        invalid position.
        """
        source = self._controller.get_queue_source()
        if (
            source is None
            or not hasattr(source, "seek")
            or not hasattr(source, "position_seconds")
        ):
            return False
        if not math.isfinite(position):
            raise ValueError("Posição inválida")
        position_seconds = cast(Callable[[], float], source.position_seconds)
        seek = cast(Callable[[float], None], source.seek)
        duration = self._current_music.duration if self._current_music else 0

        def _seek_in_thread() -> float:
            # Relative offsets are resolved inside the worker so two rapid
            # seeks cannot both read the same pre-seek position and lose a
            # jump.  FFmpeg spawn and teardown block, so this runs off the
            # bot event loop to avoid freezing it.
            target = position if absolute else position_seconds() + position
            if not math.isfinite(target):
                raise ValueError("Posição inválida")
            target = max(0.0, target)
            if duration:
                target = min(target, float(duration))
            else:
                target = min(target, MAX_SEEK_SECONDS)
            seek(target)
            return target

        target = await asyncio.to_thread(_seek_in_thread)
        logger.info(f"Seeking to {target:.1f}s in guild {self._guild_id}")
        return True

    async def set_loop(self, loop: LoopMode) -> None:
        """Set the loop mode (off, track, or queue)."""
        self._loop_mode = loop

    async def set_volume(self, volume: float) -> None:
        """Set the playback volume (clamped to the 0.0-2.0 range)."""
        self._volume = max(0.0, min(2.0, volume))
        queue_source = self._controller.get_queue_source()
        if queue_source and hasattr(queue_source, "volume"):
            try:
                queue_source.volume = self._volume  # type: ignore
            except Exception as e:
                logger.opt(exception=True).error(
                    f"Error while setting volume for music in guild "
                    f"{self._guild_id}: {e}"
                )

    async def pause(self) -> None:
        """Pause the voice client if it is currently playing."""
        voice_client = self._voice_client
        if voice_client.is_playing() and not voice_client.is_paused():
            voice_client.pause()

    async def resume(self) -> None:
        """Resume the voice client if it is currently paused."""
        voice_client = self._voice_client
        if voice_client.is_paused():
            voice_client.resume()

    async def toggle_pause(self) -> None:
        """Toggle between paused and resumed playback."""
        if self._voice_client.is_paused():
            await self.resume()
        elif self._voice_client.is_playing():
            await self.pause()

    async def remove(self, track_url: str) -> bool:
        """Remove the first track with *track_url* from the queue.

        Removing the currently-playing track skips to the next one.
        Returns ``True`` when a track was removed or skipped.
        """
        for index, track in enumerate(self._queue):
            if track.url == track_url:
                self._queue.pop(index)
                logger.info(
                    f"Removed '{track.title}' from the queue in guild "
                    f"{self._guild_id}"
                )
                return True
        if (
            self._current_music is not None
            and self._current_music.url == track_url
        ):
            await self.skip()
            return True
        return False

    async def move(self, track_url: str, position: int) -> bool:
        """Move the first waiting track with *track_url* to *position*.

        *position* is a zero-based index into the waiting queue (``0``
        plays next).  Moving the currently-playing track is a no-op.
        Returns ``True`` when the track moved.
        """
        if (
            self._current_music is not None
            and self._current_music.url == track_url
        ):
            return False
        for index, track in enumerate(self._queue):
            if track.url == track_url:
                self._queue.pop(index)
                target = max(0, min(position, len(self._queue)))
                self._queue.insert(target, track)
                logger.info(
                    f"Moved '{track.title}' to position {target} in guild "
                    f"{self._guild_id}"
                )
                return True
        return False

    async def clear_queue(self) -> None:
        """Drop every waiting track, leaving the current track playing."""
        cleared = len(self._queue)
        self._queue.clear()
        logger.info(
            f"Cleared {cleared} queued track(s) in guild {self._guild_id}"
        )

    # --- Background layer verbs ---

    async def add_layer(self, link: str) -> str:
        """Resolve *link* and add the first track found as a background layer.

        Layers play alongside the queue and are independent of the current
        track: stopping or clearing the queue leaves them running.  Returns
        the new layer's id.  Raises :class:`ValueError` when nothing is
        found.
        """
        music_data_list = await YTMusicData.from_url(link)
        if not music_data_list:
            raise ValueError("Nenhuma música encontrada para este link")
        source = await asyncio.wait_for(
            YoutubeDLSource.from_music_data(
                music_data_list[0], volume=DEFAULT_LAYER_VOLUME
            ),
            timeout=TRACK_LOAD_TIMEOUT,
        )
        layer_id = self._controller.add_layer(source)
        self._layers[layer_id] = source
        logger.info(
            f"Added background layer '{source.title}' in guild {self._guild_id}"
        )
        return layer_id

    async def remove_layer(self, layer_id: str) -> bool:
        """Remove the background layer *layer_id*, releasing its source.

        Returns ``True`` when a layer was removed.
        """
        source = self._layers.pop(layer_id, None)
        if source is None:
            return False
        self._controller.remove_layer(layer_id)
        logger.info(
            f"Removed background layer '{source.title}' in guild {self._guild_id}"
        )
        return True

    async def clear_layers(self) -> None:
        """Remove every background layer, releasing their sources."""
        layer_ids = list(self._layers)
        for layer_id in layer_ids:
            self._controller.remove_layer(layer_id)
        self._layers.clear()
        logger.info(f"Cleared background layers in guild {self._guild_id}")

    async def set_layer_volume(self, layer_id: str, volume: float) -> bool:
        """Set the volume of the background layer *layer_id* (clamped 0-2).

        Returns ``True`` when the layer exists.
        """
        source = self._layers.get(layer_id)
        if source is None:
            return False
        source.volume = max(0.0, min(2.0, volume))
        return True

    # --- Internals ---

    async def _advance(self, force_next: bool = False) -> None:
        """Move the queue forward; serialized so verbs and observers agree."""
        async with self._advance_lock:
            await self._advance_inner(force_next)

    async def _advance_inner(self, force_next: bool) -> None:
        """Prepare and play the next queued track.

        A track that fails to load with a transient error is skipped (and
        the reason announced) instead of stalling or silently killing the
        queue.  A :class:`ProbeEnvironmentError` means the environment is
        broken; the session stops cleanly and announces loudly rather than
        retrying forever.
        """
        if self._current_music:
            if self._loop_mode is LoopMode.TRACK and not force_next:
                if await self._play_or_fail(
                    self._current_music, reloading=True
                ):
                    return
                self._current_music = None
            elif self._loop_mode is LoopMode.QUEUE:
                self._queue.append(self._current_music)

        while self._queue:
            music_data = self._queue.pop(0)
            self._current_music = music_data
            logger.info(
                f"Playing next track '{music_data.title}' in guild {self._guild_id}"
            )
            if await self._play_or_fail(music_data, reloading=False):
                return

        self._current_music = None
        self._controller.clear_queue_source()

    async def _play_or_fail(
        self, music_data: YTMusicData, *, reloading: bool
    ) -> bool:
        """Try to load and play *music_data*.

        Returns ``True`` when a track is now playing or playback stopped
        (environment failure); ``False`` when the track was skipped and the
        queue should keep advancing.
        """
        try:
            await self._load_and_play(music_data)
            return True
        except ProbeEnvironmentError as e:
            logger.error(
                f"Environment failure playing '{music_data.title}' in guild "
                f"{self._guild_id}: {e}"
            )
            self._current_music = None
            self._controller.clear_queue_source()
            await self._announce(
                f"'{music_data.title}' não pôde ser reproduzida por um erro "
                f"de ambiente ({e}). Parando a reprodução."
            )
            return True
        except Exception as e:
            logger.warning(
                f"Skipping unplayable track '{music_data.title}' in guild "
                f"{self._guild_id}: {e}"
            )
            prefix = "recarregada" if reloading else "carregada"
            await self._announce(
                f"'{music_data.title}' não pôde ser {prefix} e foi pulada: {e}"
            )
            return False

    async def _load_and_play(self, music_data: YTMusicData) -> None:
        """Load a source for *music_data* (bounded by a timeout) and set it as current."""
        source = await asyncio.wait_for(
            YoutubeDLSource.from_music_data(music_data, volume=self._volume),
            timeout=TRACK_LOAD_TIMEOUT,
        )
        self._controller.set_queue_source(source)

    async def _announce(self, message: str) -> None:
        """Deliver an announcement, never letting the sink raise."""
        if self._announcer is None:
            return
        try:
            await self._announcer(message)
        except Exception:
            logger.opt(exception=True).error(
                f"Announcer failed for guild {self._guild_id}"
            )
