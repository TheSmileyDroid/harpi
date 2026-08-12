from __future__ import annotations

import asyncio
import enum
import io
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

import discord
from loguru import logger

from src.harpi_lib.audio.controller import AudioController
from src.harpi_lib.audio.mixer import MixerSource
from src.harpi_lib.music.ytmusicdata import (
    FastStartFFmpegPCMAudio,
    ProbeEnvironmentError,
    YoutubeDLSource,
    YTMusicData,
)

MAX_SEEK_SECONDS = 4 * 3600
TRACK_LOAD_TIMEOUT = 60.0
DEFAULT_VOLUME = 0.7
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


LOOP_MODE_ALIASES: dict[str, LoopMode] = {
    **{a: LoopMode.OFF for a in ("off", "false", "0", "no", "n")},
    **{
        a: LoopMode.TRACK for a in ("track", "true", "1", "yes", "y", "musica")
    },
    **{a: LoopMode.QUEUE for a in ("queue", "fila")},
}


@dataclass(frozen=True)
class SessionStatus:
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
        self._mixer.add_observer("queue_end", self._on_queue_end)
        self._mixer.add_observer("track_end", self._on_track_end)

    def _on_queue_end(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._spawn_advance)
        else:
            logger.warning(
                f"No event loop bound to session for guild {self._guild_id}; "
                "cannot advance after track end"
            )

    def _spawn_advance(self) -> None:
        asyncio.ensure_future(self._advance())

    def _on_track_end(self, to_remove: list[discord.AudioSource]) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(
                self._drop_finished_layers, tuple(to_remove)
            )

    def _drop_finished_layers(
        self, to_remove: tuple[discord.AudioSource, ...]
    ) -> None:
        for source in to_remove:
            layer_id = getattr(source, "id", None)
            if layer_id is not None:
                self._layers.pop(layer_id, None)

    @property
    def guild_id(self) -> int:
        return self._guild_id

    def set_announcer(
        self, announcer: Callable[[str], Awaitable[Any]] | None
    ) -> None:
        self._announcer = announcer

    @property
    def status(self) -> SessionStatus:
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

    async def play_tts(self, audio: io.BufferedIOBase) -> None:
        """Speak synthesized *audio* over whatever the session is playing.

        The caller only synthesizes text to audio (for example with gTTS)
        and hands the resulting seekable byte stream over; this session
        owns audio-source construction, wrapping the stream in the FFmpeg
        pipe source and handing it to the mixer as a TTS track.  The TTS
        track plays alongside the queue and the background layers and is
        released when it finishes reading or when a newer TTS track
        replaces it.
        """
        source = FastStartFFmpegPCMAudio(audio, pipe=True)
        self._controller.set_tts_track(source)
        logger.info(f"Playing TTS audio in guild {self._guild_id}")

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

    async def _advance(self, force_next: bool = False) -> None:
        async with self._advance_lock:
            await self._advance_inner(force_next)

    async def _advance_inner(self, force_next: bool) -> None:
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
