"""YouTube music data retrieval and audio source management.

Thread safety
-------------
* ``ytdl`` (module-level ``yt_dlp.YoutubeDL`` singleton) is called from
  the bot's event loop via ``run_in_executor``.  yt-dlp is not documented
  as thread-safe, but in practice only one extraction runs at a time
  because callers ``await`` the result.  This is an **accepted risk**.
* ``FFmpegPCMAudio.read()`` is called from discord.py's voice-sending
  thread.  ``cleanup()`` may be called from the bot or Quart event loops.
  A ``threading.Lock`` (``_proc_lock``) serialises process spawn and
  teardown to prevent races on ``self._process``.
"""

from __future__ import annotations

import asyncio
import io
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

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source: discord.AudioSource) -> None:
        self._source: discord.AudioSource = source
        self.count_20ms: int = 0

    def read(self) -> bytes:
        data = self._source.read()
        if data:
            self.count_20ms += 1
        return data

    @property
    def progress(self) -> float:
        return self.count_20ms * 0.02  # count_20ms * 20ms


class UniqueAudioSource(discord.PCMVolumeTransformer):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.id: str = str(uuid.uuid4())


class YoutubeDLSource(UniqueAudioSource):
    """Audio source that streams from YouTube via yt-dlp and FFmpeg."""

    def __init__(
        self, source: discord.AudioSource, data: dict[str, Any], **kwargs: Any
    ) -> None:
        """Create a YoutubeDLSource instance."""
        super().__init__(original=source, **kwargs)

        self.data: dict[str, str | int] = data

        self.title: str = data.get("title", "Unknown Title")
        self.url: str = data.get("url", "Unknown URL")

    @classmethod
    async def from_music_data(
        cls,
        musicdata: YTMusicData,
        volume: float = 0.3,
    ) -> YoutubeDLSource:
        """Create a YoutubeDLSource instance from a YTMusicData.

        Args:
            musicdata (YTMusicData): Music data to use.
            volume (float, optional): Volume to be set. Defaults to 0.3.

        Raises:
            BadLink: If the link is invalid.

        Returns:
            YoutubeDLSource: The created YoutubeDLSource instance.

        """
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
    """Search YouTube and return the music information.

    Args:
        arg (str): A string representing the search query.

    Raises:
        NothingFoundError: If no music is found.

    Returns:
        dict[str, Any]: A dictionary containing the information of the music.

    """
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
                        f"ytsearch:{arg}",
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
        """Create a YTMusicData instance.

        Args:
            video (dict[str, Any]):
                A dictionary containing the information of the music.

        """
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
        """Create a YTMusicData instance from a URL.

        Args:
            url (str): A string representing the URL.

        Returns:
            list[YTMusicData]: A list of YTMusicData instances.

        """
        logger.info(f"Searching for {url}")
        result = search(url)
        if result.get("entries"):
            logger.info(
                f"Found {result.get('entries')} results.",
            )
            return [
                cls(dict(cast(dict[str, str | int], video)))
                for video in cast(list, result.get("entries"))
            ]
        video = result
        return cast(
            list[YTMusicData], [cls(dict(cast(dict[str, str | int], video)))]
        )

    def get_title(self) -> str:
        """Return the title of the music.

        Returns:
            str: The title of the music.

        """
        return self._title

    def get_metadata(self, key: str) -> Any:
        return self._video.get(key, None)

    @property
    def title(self) -> str:
        """Return the title of the music.

        Returns:
            str: The title of the music.

        """
        return self._title

    def get_url(self) -> str:
        """Return the URL of the music.

        Returns:
            str: The URL of the music.

        """
        return self._url

    @property
    def url(self) -> str:
        """Return the URL of the music.

        Returns:
            str: The URL of the music.

        """
        return self._url

    def get_artist(self) -> str:
        """Return the artist of the music.

        Returns:
            str: The artist of the music.

        """
        return cast(str, self._video.get("artist", "Unknown"))

    @property
    def artist(self) -> str:
        """Return the artist of the music.

        Returns:
            str: The artist of the music.

        """
        return cast(str, self._video.get("artist", "Unknown"))

    def get_thumbnail(self) -> str:
        """Return the thumbnail URL of the music.

        Returns:
            str: The URL of the thumbnail.

        """
        return cast(str, self._video.get("thumbnail", "Unknown"))

    @property
    def thumbnail(self) -> str:
        """Return the thumbnail URL of the music.

        Returns:
            str: The URL of the thumbnail.

        """
        return cast(str, self._video.get("thumbnail", "Unknown"))

    @property
    def duration(self) -> int:
        """Return the duration of the music.

        Returns:
            int: The duration of the music.

        """
        return cast(int, self._video.get("duration", 0))


class FFmpegPCMAudio(discord.AudioSource):
    """Audio streaming source via FFmpeg with strict typing.

    Thread safety
    -------------
    ``read()`` is called from the mixer's thread pool, while ``cleanup()``
    can be called from any thread (mixer pool on EOF, or bot/Quart loops
    on disconnect).  A ``threading.Lock`` protects the ``_process``
    lifecycle to prevent double-terminate / double-kill races.

    Improvements applied:
    1. Lazy Loading: The process only starts on the first read (saves resources).
    2. Deadlock Fix: Stderr is redirected to DEVNULL if not provided.
    3. Type Hints: Full typing for static validation (Mypy/Pyright).
    4. Auto-Reconnection: Reconnection flags applied only for HTTP(S) URLs.
    """

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
        """Initialize FFmpegPCMAudio.

        Args:
            source: URL (str) or file object (buffer) to read from.
            executable: Name or path of the ffmpeg executable.
            pipe: If True, source will be passed via stdin.
            stderr: File/Pipe for error logging.
            before_options: FFmpeg arguments before the input (-i).
            options: FFmpeg arguments after the input.
        """
        self.source: str | io.BufferedIOBase = source
        self.executable: str = executable
        self.pipe: bool = pipe
        self.stderr: IO[str] | None = stderr
        self.before_options: str | None = before_options
        self.options: str | None = options

        self._proc_lock: threading.Lock = threading.Lock()
        # The process is typed as Popen that returns bytes on stdout
        self._process: subprocess.Popen[bytes] | None = None

    def _spawn_process(self) -> None:
        """Spawn the FFmpeg subprocess (lazy loading)."""
        args: list[str] = [self.executable]

        # 1. Before Options
        if self.before_options:
            args.extend(shlex.split(self.before_options))

        # 2. Reconnection Flags (HTTP/HTTPS URLs only)
        # Avoids errors on local files where these flags do not exist.
        if isinstance(self.source, str) and self.source.startswith(
            ("http:", "https:")
        ):
            # Check if the user has not already passed these flags manually
            if (
                not self.before_options
                or "-reconnect" not in self.before_options
            ):
                args.extend(
                    [
                        "-reconnect",
                        "1",
                        "-reconnect_streamed",
                        "1",
                        "-reconnect_delay_max",
                        "5",
                    ]
                )

        # 3. Input (-i)
        args.append("-i")
        args.append("-" if self.pipe else str(self.source))

        # 4. Codec Options (Discord default: PCM 16-bit Little Endian, 48kHz, Stereo)
        args.extend(
            [
                "-f",
                "s16le",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-loglevel",
                "warning",
            ]
        )

        # 5. After Options
        if self.options:
            args.extend(shlex.split(self.options))

        # 6. Output Pipe
        args.append("pipe:1")

        logger.debug(f"Starting FFmpeg with command: {shlex.join(args)}")

        # Stdin Configuration
        # If pipe=True, we use self.source as stdin. Otherwise, we use DEVNULL.
        # We need to ensure that stdin is a valid file or None/DEVNULL.
        input_stream: IO[bytes] | int | None = None
        if self.pipe:
            if isinstance(self.source, (str, bytes)):
                # If source is a string but pipe=True, this is usually a usage error,
                # unless the string is raw data (which str should not be).
                # We assume here that source is a valid Buffer if pipe=True.
                pass
            input_stream = cast(IO[bytes], cast(object, self.source))
        else:
            input_stream = subprocess.DEVNULL

        try:
            # FIX DEADLOCK: Use DEVNULL if stderr is not set by the user.
            # Never leave stderr=subprocess.PIPE without reading the data, as it blocks the process.
            stderr_dest = self.stderr if self.stderr else subprocess.DEVNULL

            self._process = subprocess.Popen(
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

    @override
    def read(self) -> bytes:
        """Read 20ms of PCM audio.

        Thread-safe: acquires ``_proc_lock`` for process spawning and
        delegates to ``cleanup()`` (which also acquires the lock) on EOF.
        The actual ``stdout.read()`` is performed without the lock held
        so that long reads don't block cleanup from another thread.
        """
        # Lazy initialization under lock
        with self._proc_lock:
            if self._process is None:
                self._spawn_process()
            proc = self._process

        # Safety check after spawn
        if proc is None or proc.stdout is None:
            return b""

        ret: bytes = b""
        try:
            # Read the exact frame size (usually 3840 bytes for stereo/48k)
            ret = proc.stdout.read(Encoder.FRAME_SIZE)

            # If the read size is less than the frame, we reached end of stream or error.
            if len(ret) != Encoder.FRAME_SIZE:
                self.cleanup()
                return b""
        except (OSError, ValueError) as e:
            logger.error(f"Error reading from FFmpeg: {e}")
            self.cleanup()
            return b""

        return ret

    @override
    def cleanup(self) -> None:
        """Terminate the process cleanly.

        Thread-safe: acquires ``_proc_lock`` to prevent double-terminate
        if ``read()`` (mixer thread) and disconnect (bot thread) race.
        """
        with self._proc_lock:
            proc = self._process
            if proc is None:
                return
            self._process = None

        try:
            # Try to terminate gracefully (SIGTERM)
            proc.terminate()
            try:
                # Wait briefly to avoid zombie processes
                _ = proc.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                # If it doesn't close, force kill (SIGKILL)
                proc.kill()
                _ = proc.communicate()
        except Exception:
            # Log but don't crash — cleanup must be best-effort
            logger.debug(
                "FFmpegPCMAudio cleanup error (suppressed)", exc_info=True
            )


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
        """Create a FFmpegPCMAudio instance."""
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
