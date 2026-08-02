"""YouTube music data retrieval and audio source management.

Thread safety
-------------
* ``ytdl`` (module-level ``yt_dlp.YoutubeDL`` singleton) is called from
  the bot's event loop via ``run_in_executor``.  yt-dlp is not documented
  as thread-safe, but in practice only one extraction runs at a time
  because callers ``await`` the result.  This is an **accepted risk**.
* ``FFmpegPCMAudio.read()`` runs on one of the mixer's reader threads,
  while ``cleanup()`` and ``seek()`` may be called from the bot or
  Quart event loops.  A ``threading.Lock`` (``_proc_lock``) serialises
  access to ``self._process`` and a monotonically increasing
  ``_generation`` counter lets stale spawns detect that a newer seek
  or a cleanup superseded them, so a killed process is never
  resurrected.  Every ``seek()`` advances the generation, even when no
  process is currently running, so an in-flight reader spawn is always
  invalidated and the reader re-spawns at the new offset instead of
  committing audio from the old position.  Blocking pipe reads and
  subprocess spawns happen outside the lock so a stalled stream cannot
  block ``seek()`` or ``cleanup()`` indefinitely.
* ``YoutubeDLSource`` tracks its playback position in bytes under a
  dedicated lock (``_position_lock``) because ``read()`` runs on the
  voice-sending thread while ``position_seconds()`` and ``seek()`` are
  called from other threads.  ``seek()`` holds a dedicated ``_seek_lock``
  across the underlying seek and the counter reset so concurrent seeks
  cannot leave the byte counter disagreeing with the FFmpeg position.
"""

from __future__ import annotations

import asyncio
import io
import math
import re
import shlex
import subprocess  # noqa: S404
import threading
import time
import uuid
from typing import IO, Any, cast, override

import discord
import yt_dlp
from discord.opus import Encoder
from loguru import logger

from src.errors.nothingfound import NothingFoundError

ytdl_format_options = {
    "format": "m4a/bestaudio/best",
    "outtmpl": ".audios/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "extract_flat": True,
    "verbose": True,
    "no_warnings": False,
    "default_search": "auto_warning",
    "cookiefile": "cookies.txt",
}

ffmpeg_options = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}

BYTES_PER_SECOND = 48000 * 2 * 2

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class AudioSourceWrapper(discord.AudioSource):
    def __init__(self, source: discord.AudioSource) -> None:
        self._source: discord.AudioSource = source

    def read(self) -> bytes:
        return self._source.read()


class UniqueAudioSource(discord.PCMVolumeTransformer):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.id: str = str(uuid.uuid4())


class YoutubeDLSource(UniqueAudioSource):
    """Audio source that streams from YouTube via yt-dlp and FFmpeg."""

    def __init__(
        self, source: discord.AudioSource, data: dict[str, Any], **kwargs: Any
    ) -> None:
        super().__init__(original=source, **kwargs)

        self.data: dict[str, str | int] = data

        self.title: str = data.get("title", "Unknown Title")
        self.url: str = data.get("url", "Unknown URL")

        self._position_bytes: int = 0
        self._position_lock: threading.Lock = threading.Lock()
        self._seek_lock: threading.Lock = threading.Lock()

    @override
    def read(self) -> bytes:
        data = super().read()
        with self._position_lock:
            self._position_bytes += len(data)
        return data

    def position_seconds(self) -> float:
        with self._position_lock:
            return self._position_bytes / BYTES_PER_SECOND

    def seek(self, position: float) -> None:
        """Seek to an absolute position in seconds."""
        position = max(0.0, position)
        with self._seek_lock:
            original_seek = getattr(self.original, "seek", None)
            if callable(original_seek):
                original_seek(position)
            with self._position_lock:
                self._position_bytes = int(position * BYTES_PER_SECOND)

    @override
    def cleanup(self) -> None:
        """Forward cleanup to the underlying FFmpeg process."""
        original_cleanup = getattr(self.original, "cleanup", None)
        if callable(original_cleanup):
            original_cleanup()

    @classmethod
    async def from_music_data(
        cls,
        musicdata: YTMusicData,
        volume: float = 0.3,
    ) -> YoutubeDLSource:
        """Create a YoutubeDLSource instance from a YTMusicData."""
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(musicdata.get_url(), download=False),
        )

        if not isinstance(data, dict):
            raise ValueError("Invalid data from ytdl: expected dict")
        if "entries" in data:
            data = data["entries"][0]
        if not isinstance(data, dict):
            raise ValueError("Invalid data from ytdl: expected dict entry")

        url = data.get("url")
        if not isinstance(url, str):
            raise ValueError("Invalid URL from ytdl: expected string")
        # Use the URL directly for streaming instead of downloading the file
        return cls(
            FFmpegPCMAudio(
                source=url,
                options=ffmpeg_options["options"],
                before_options=ffmpeg_options["before_options"],
            ),
            data=dict(data),
            volume=volume,
        )


def search(arg: str) -> dict[str, Any]:
    """Search YouTube and return the music information."""
    _start_time = time.time()

    URL_REGEX = re.compile(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    )
    video: dict | None = None
    try:
        if not re.match(URL_REGEX, arg):
            video = cast(
                dict[str, str | int],
                cast(
                    object,
                    ytdl.extract_info(
                        f"ytsearch10:{arg}",
                        download=True,
                        process=False,
                    ),
                ),
            )
        else:
            video = cast(
                dict[str, str | int],
                cast(
                    object,
                    ytdl.extract_info(arg, download=True, process=False),
                ),
            )
    except Exception as e:
        logger.opt(exception=True).error(f"Error during search: {e}")
    if not video:
        raise NothingFoundError(arg)
    logger.info(
        f"Searched for {arg} in {time.time() - _start_time} seconds.",
    )
    return video


class YTMusicData:
    """Data container for a YouTube music track's metadata."""

    def __init__(self, video: dict[str, str | int]) -> None:
        self._title: str = cast(str, video.get("title", "Unknown"))
        self._url: str = cast(
            str,
            video.get(
                "url",
                cast(str, video.get("original_url", "Unknown")),
            ),
        )
        self._video: dict[str, str | int] = video
        self._source: YoutubeDLSource | None = None

    @classmethod
    async def from_url(cls, url: str) -> list[YTMusicData]:
        """Create a YTMusicData instance from a URL."""
        logger.info(f"Searching for {url}")
        result = search(url)
        if result.get("entries"):
            logger.info(
                f"Found {result.get('entries')} results.",
            )
            items = [
                cls(dict(cast(dict[str, str | int], video)))
                for video in cast(list, result.get("entries"))
            ]
            return [
                item
                for item in items
                if item.duration
                and item.duration > 0
                and "watch?v=" in item.url
            ]
        video = result
        return cast(
            list[YTMusicData], [cls(dict(cast(dict[str, str | int], video)))]
        )

    @property
    def title(self) -> str:
        return self._title

    def get_url(self) -> str:
        return self._url

    @property
    def url(self) -> str:
        return self._url

    @property
    def duration(self) -> int:
        return cast(int, self._video.get("duration", 0))

    @property
    def thumbnail(self) -> str:
        thumb = self._video.get("thumbnail") or self._video.get("thumb", "")
        if thumb:
            return cast(str, thumb)
        video_id = self._video.get("id", "")
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        return ""

    @property
    def uploader(self) -> str:
        return cast(
            str,
            self._video.get(
                "uploader",
                self._video.get("channel", self._video.get("creator", "")),
            ),
        )


class FFmpegPCMAudio(discord.AudioSource):
    def __init__(
        self,
        source: str | io.BufferedIOBase,
        *,
        executable: str = "ffmpeg",
        pipe: bool = False,
        stderr: IO[str] | None = None,
        before_options: str | None = None,
        options: str | None = None,
    ) -> None:
        self.source: str | io.BufferedIOBase = source
        self.executable: str = executable
        self.pipe: bool = pipe
        self.stderr: IO[str] | None = stderr
        self.before_options: str | None = before_options
        self.options: str | None = options

        self._proc_lock: threading.Lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._generation: int = 0
        self._seek_offset: float = 0.0
        self._shutdown: bool = False

    def _spawn_process(self) -> subprocess.Popen[bytes]:
        args: list[str] = [self.executable]

        if self._seek_offset > 0:
            args.extend(["-ss", f"{self._seek_offset:.2f}"])

        if self.before_options:
            args.extend(shlex.split(self.before_options))

        if isinstance(self.source, str) and self.source.startswith((
            "http:",
            "https:",
        )):
            if (
                not self.before_options
                or "-reconnect" not in self.before_options
            ):
                args.extend([
                    "-reconnect",
                    "1",
                    "-reconnect_streamed",
                    "1",
                    "-reconnect_delay_max",
                    "5",
                ])

        args.append("-i")
        args.append("-" if self.pipe else str(self.source))
        args.extend([
            "-f",
            "s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-loglevel",
            "warning",
        ])

        if self.options:
            args.extend(shlex.split(self.options))

        args.append("pipe:1")

        logger.debug(
            f"Starting FFmpeg (seek={self._seek_offset:.2f}s, pipe={self.pipe})"
        )

        input_stream: IO[bytes] | int | None = None
        if self.pipe:
            if isinstance(self.source, (str, bytes)):
                pass
            input_stream = cast(IO[bytes], cast(object, self.source))
        else:
            input_stream = subprocess.DEVNULL

        try:
            stderr_dest = self.stderr if self.stderr else subprocess.DEVNULL
            return subprocess.Popen(
                args,
                stdin=input_stream,
                stdout=subprocess.PIPE,
                stderr=stderr_dest,
            )
        except FileNotFoundError:
            raise discord.ClientException(
                f"Executable '{self.executable}' was not found."
            ) from None
        except subprocess.SubprocessError as exc:
            raise discord.ClientException(
                f"Failed to start Popen: {exc}"
            ) from exc

    @staticmethod
    def _terminate(proc: subprocess.Popen[bytes] | None) -> None:
        """Terminate the FFmpeg process, falling back to kill on timeout."""
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                _ = proc.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                proc.kill()
                _ = proc.communicate()
        except Exception:
            logger.debug(
                "FFmpegPCMAudio terminate error (suppressed)", exc_info=True
            )

    @override
    def read(self) -> bytes:
        while True:
            with self._proc_lock:
                proc = self._process
                generation = self._generation
                if proc is None:
                    if self._shutdown:
                        return b""
                    self._generation += 1
                    generation = self._generation

            if proc is None:
                new_proc = self._spawn_process()
                with self._proc_lock:
                    if self._shutdown:
                        self._terminate(new_proc)
                        return b""
                    if self._generation != generation:
                        self._terminate(new_proc)
                        continue
                    self._process = new_proc
                    proc = new_proc

            if proc.stdout is None:
                return b""

            try:
                ret = proc.stdout.read(Encoder.FRAME_SIZE)
            except (OSError, ValueError):
                ret = b""

            if len(ret) != Encoder.FRAME_SIZE:
                with self._proc_lock:
                    if self._process is proc:
                        self._process = None
                    else:
                        proc = None
                if proc is not None:
                    self._terminate(proc)
                    return b""
                continue
            return ret

    def seek(self, position: float) -> None:
        """Seek the stream to an absolute position in seconds."""
        if not math.isfinite(position):
            return
        position = max(0.0, position)
        with self._proc_lock:
            if self._shutdown:
                return
            self._seek_offset = position
            proc = self._process
            self._process = None
            self._generation += 1
            generation = self._generation
        self._terminate(proc)
        if proc is None:
            return
        new_proc = self._spawn_process()
        with self._proc_lock:
            if self._shutdown or self._generation != generation:
                self._terminate(new_proc)
                return
            self._process = new_proc

    @override
    def cleanup(self) -> None:
        with self._proc_lock:
            self._shutdown = True
            proc = self._process
            self._process = None
            self._generation += 1
        self._terminate(proc)


class FastStartFFmpegPCMAudio(discord.FFmpegPCMAudio):
    """Fast-start FFmpeg audio source for YouTube music streaming."""

    def __init__(
        self,
        source: io.BufferedIOBase,
        *,
        executable: str = "ffmpeg",
        pipe: bool = False,
        stderr: io.TextIOWrapper | None = None,
        before_options: str | None = None,
        options: str | None = None,
    ) -> None:
        if isinstance(before_options, str):
            before_options = (
                f"{before_options} -analyzeduration 1000000 -probesize 1000000"
            )
        else:
            before_options = "-analyzeduration 1000000 -probesize 1000000"

        super().__init__(
            source,
            executable=executable,
            pipe=pipe,
            stderr=cast("IO[bytes]", stderr),
            before_options=before_options,
            options=options,
        )
