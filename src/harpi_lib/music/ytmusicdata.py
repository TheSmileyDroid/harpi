"""YouTube music data retrieval and audio source management."""

from __future__ import annotations

import asyncio
import concurrent.futures
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
from urllib.parse import urlsplit
from yt_dlp.utils.networking import std_headers

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
    "socket_timeout": 15,
    "retries": 1,
    "fragment_retries": 1,
    "extractor_retries": 1,
}

YT_SEARCH_TIMEOUT = 30.0
YT_EXTRACT_TIMEOUT = 25.0

SILENCE_PROBE_SECONDS = 15.0  # ffmpeg volumedetect window (seconds)
SILENCE_MAX_VOLUME_DB = -60.0  # max_volume below this is treated as silence
STREAM_PROBE_ATTEMPTS = 3  # probe attempts for remote streams before giving up
STREAM_PROBE_RETRY_DELAY = 1.0  # seconds between probe attempts
STREAM_PROBE_TOTAL_TIMEOUT = (
    15.0  # overall budget for one probe sequence (seconds)
)


class ProbeError(ValueError):
    """A stream could not be probed or is not fit for playback."""


class ProbeSilenceError(ProbeError):
    """The probed stream carries audio but is pure silence."""


class ProbeEnvironmentError(ProbeError):
    """The probe could not run in this deployment (e.g. ffmpeg is missing)."""


class ProbeTimeoutError(ProbeError):
    """The probe exceeded its overall budget."""


# Reconnect flags for flaky remote streams, shared by probe and playback.
_RECONNECT_OPTIONS = (
    "-reconnect",
    "1",
    "-reconnect_streamed",
    "1",
    "-reconnect_delay_max",
    "5",
)

ffmpeg_options = {
    "options": "-vn",
    "before_options": " ".join(_RECONNECT_OPTIONS),
}

# Browser-like HTTP headers, the same set yt-dlp attaches to every request.
# YouTube's CDN answers the googlevideo stream URLs with 403 when ffmpeg
# fetches them without these headers, so probing and playback send them.
_FFMPEG_HEADERS = (
    "\r\n".join(f"{k}: {v}" for k, v in std_headers.items()) + "\r\n"
)

BYTES_PER_SECOND = 48000 * 2 * 2

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# Serializes yt-dlp extractions: the library is not thread-safe, and a
# timed-out extraction is abandoned mid-flight rather than awaited, so a
# single worker guarantees callers never interleave on the shared instance.
_YTDL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="ytdl"
)


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
        """Create a YoutubeDLSource instance from a YTMusicData.

        Reuses the formats already extracted at search time when possible
        (avoiding a redundant, easily-throttled second extraction) and
        bounds the fallback extraction with a timeout.  The selected
        stream is then duration-validated and probed for playability and
        silence before playback, so an unreachable, audio-less, or silent
        track is rejected up front.
        """
        info, stream_url = await cls._pick_stream(musicdata)
        data = dict(info)
        data["url"] = musicdata.get_url()
        return cls(
            FFmpegPCMAudio(
                source=stream_url,
                options=ffmpeg_options["options"],
                before_options=ffmpeg_options["before_options"],
            ),
            data=data,
            volume=volume,
        )

    @staticmethod
    def _validate_duration(info: dict[str, Any]) -> None:
        """Reject tracks whose duration is known to be zero or negative."""
        duration = info.get("duration")
        if duration is None:
            return
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            return
        if duration <= 0:
            raise ValueError("track has no playable duration")

    @classmethod
    async def _pick_stream(
        cls, musicdata: YTMusicData
    ) -> tuple[dict[str, Any], str]:
        """Pick and validate a playable stream for *musicdata*.

        Reuses the formats already extracted at search time, then retries
        with a fresh extraction if that stream cannot be probed.  Reusing
        avoids a redundant, easily-throttled second extraction in the
        common case; the fresh extraction yields a brand-new URL when the
        reused one was rejected by the CDN edge.  The fresh extraction
        happens at most once per call.
        """
        reused = (
            musicdata.video_data
            if isinstance(musicdata.video_data, dict)
            else None
        )

        async def _try(
            info: dict[str, Any],
            stream_url: str,
        ) -> tuple[dict[str, Any], str] | None:
            if not stream_url.startswith(("http://", "https://")):
                raise ValueError(
                    f"No playable stream found for URL: {musicdata.get_url()}"
                )
            cls._validate_duration(info)
            try:
                await asyncio.to_thread(probe_stream_audio, stream_url)
            except ValueError as exc:
                if not cls._probe_failure_is_transient(exc):
                    raise
                return None
            return info, stream_url

        reused_url = (
            cls._stream_url_from(reused) if reused is not None else None
        )
        if reused_url is not None:
            picked = await _try(reused, reused_url)
            if picked is not None:
                return picked

        fresh = await cls._extract_fresh(musicdata.get_url())
        fresh_url = cls._select_stream_url(fresh)
        if not isinstance(fresh_url, str) or not fresh_url.startswith((
            "http://",
            "https://",
        )):
            raise ValueError(
                f"No playable stream found for URL: {musicdata.get_url()}"
            )
        picked = await _try(fresh, fresh_url)
        if picked is not None:
            return picked
        raise ValueError(
            f"No playable stream found for URL: {musicdata.get_url()}"
        )

    @staticmethod
    def _stream_url_from(info: dict[str, Any] | None) -> str | None:
        """Select a reused stream URL, or None to force a fresh extraction.

        Flat search entries carry no usable ``formats`` list, so a top-level
        URL is never trusted here; only real extracted formats are reused.
        """
        if not isinstance(info, dict):
            return None
        formats = info.get("formats")
        if not isinstance(formats, list) or not formats:
            return None
        return YoutubeDLSource._select_stream_url(info)

    @classmethod
    async def _extract_fresh(cls, url: str) -> dict[str, Any]:
        """Extract yt-dlp info with a timeout on the single ytdl worker."""
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(_YTDL_EXECUTOR, cls._extract_info, url),
            timeout=YT_EXTRACT_TIMEOUT,
        )

    @staticmethod
    def _probe_failure_is_transient(exc: Exception) -> bool:
        """True when a failed probe may succeed on a fresh stream URL.

        Silence and a missing ffmpeg are properties of the track or the
        deployment, not of the connection, so they are never transient;
        everything else (rejected stream, unreadable stream, timeout) can
        be.
        """
        return not isinstance(exc, (ProbeSilenceError, ProbeEnvironmentError))

    @staticmethod
    def _extract_info(url: str) -> dict[str, Any]:
        """Extract yt-dlp info for *url* and unwrap playlist/search entries to the first video."""
        data = ytdl.extract_info(url, download=False)
        if not isinstance(data, dict):
            raise ValueError("Invalid data from ytdl: expected dict")
        if "entries" in data:
            entries = data["entries"]
            if not entries or not isinstance(entries[0], dict):
                raise ValueError("Invalid data from ytdl: expected dict entry")
            data = entries[0]
        if not isinstance(data, dict):
            raise ValueError("Invalid data from ytdl: expected dict entry")
        return data

    @classmethod
    def _select_stream_url(cls, data: dict[str, Any] | None) -> str | None:
        """Pick the best playable stream URL without any network access.

        Prefers audio-only formats, then ``m4a``, then the highest bitrate.
        Returns None when nothing usable is found.
        """
        if not isinstance(data, dict):
            return None
        formats = data.get("formats")
        if isinstance(formats, list) and formats:
            candidates: list[dict[str, Any]] = []
            for f in formats:
                if not isinstance(f, dict):
                    continue
                url = f.get("url")
                if not isinstance(url, str) or not url.startswith((
                    "http://",
                    "https://",
                )):
                    continue
                if not cls._is_usable_audio_format(f):
                    continue
                candidates.append(f)
            if not candidates:
                return None

            def _bitrate(f: dict[str, Any]) -> float:
                for key in ("abr", "tbr"):
                    value = f.get(key)
                    if value is None:
                        continue
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue
                return 0.0

            def _score(f: dict[str, Any]) -> tuple[int, int, float]:
                return (
                    not cls._is_audio_only_format(f),
                    f.get("ext") != "m4a",
                    -_bitrate(f),
                )

            best = min(candidates, key=_score)
            url = best.get("url")
            if isinstance(url, str):
                return url
            return None
        url = data.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
        return None

    @staticmethod
    def _is_usable_audio_format(f: dict[str, Any]) -> bool:
        """True if *f* carries an audio stream (muxed or audio-only)."""
        acodec = f.get("acodec")
        return isinstance(acodec, str) and bool(acodec) and acodec != "none"

    @staticmethod
    def _is_audio_only_format(f: dict[str, Any]) -> bool:
        """True if *f* carries audio but no video."""
        acodec = f.get("acodec")
        vcodec = f.get("vcodec")
        return (
            isinstance(acodec, str)
            and bool(acodec)
            and acodec != "none"
            and (not vcodec or vcodec == "none")
        )


def search(arg: str) -> dict[str, Any]:
    """Search YouTube and return the music information."""
    _start_time = time.time()

    URL_REGEX = re.compile(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    )
    video: dict[str, Any] | None = None
    try:
        if not re.match(URL_REGEX, arg):
            video = cast(
                dict[str, Any],
                cast(
                    object,
                    ytdl.extract_info(
                        f"ytsearch10:{arg}",
                        download=False,
                        process=False,
                    ),
                ),
            )
        else:
            video = cast(
                dict[str, Any],
                cast(
                    object,
                    ytdl.extract_info(arg, download=False, process=False),
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


def _parse_max_volume(stderr: str) -> float | None:
    """Return the volumedetect ``max_volume`` (dB) from ffmpeg stderr."""
    match = re.search(r"max_volume:\s*(-?(?:inf|[\d.]+))\s*dB", stderr)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


_SIGNED_PARAM = re.compile(
    r"(?P<pre>[?&])(?:lsig|signature|sig|token|expire|pot|nh|gcr|s|n)="
    r"[^&\s]+",
    re.IGNORECASE,
)


def _redact_signed_tokens(text: str) -> str:
    """Blank signed URL-parameter values so logs do not leak stream tokens."""
    return _SIGNED_PARAM.sub(r"\g<pre>REDACTED", text)


def _redact_stream_url(stream_url: str) -> str:
    """Return *stream_url* reduced to a bare host for log safety."""
    try:
        parsed = urlsplit(stream_url)
    except ValueError:
        return "<invalid stream url>"
    if not (parsed.scheme and parsed.netloc):
        return "<non-url stream source>"
    host = parsed.netloc
    if "@" in host:
        host = host.rsplit("@", 1)[-1]
    return f"{parsed.scheme}://{host}/..."


def _probe_stream_once(stream_url: str, timeout: float) -> float:
    """Run a single ffmpeg volumedetect probe and return the max volume (dB).

    Raises a :class:`ProbeError` subclass when the stream cannot be probed
    (no audio stream, ffmpeg failure, or timeout) or is pure silence.
    """
    if not isinstance(stream_url, str) or stream_url.startswith("-"):
        raise ValueError("invalid stream url")
    args = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-t",
        str(SILENCE_PROBE_SECONDS),
    ]
    if stream_url.startswith(("http://", "https://")):
        args.extend(_RECONNECT_OPTIONS)
        args.extend(["-headers", _FFMPEG_HEADERS])
    args.extend([
        "-i",
        stream_url,
        "-map",
        "0:a:0",
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ])
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError:
        raise ProbeEnvironmentError(
            "ffmpeg not available for stream probing"
        ) from None
    try:
        _, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass
        proc.communicate()
        raise ProbeTimeoutError("stream probe timed out") from None
    if proc.returncode != 0:
        tail = (stderr or "").strip()[-300:]
        logger.debug(
            f"Probe failed for stream {_redact_stream_url(stream_url)}: "
            f"{_redact_signed_tokens(tail)}"
        )
        raise ValueError("stream not playable")
    max_volume = _parse_max_volume(stderr or "")
    if max_volume is None:
        raise ValueError("could not determine stream volume")
    if max_volume < SILENCE_MAX_VOLUME_DB:
        raise ProbeSilenceError(
            f"stream is silent (max_volume={max_volume:.1f} dB)"
        )
    return max_volume


def probe_stream_audio(stream_url: str) -> float:
    """Probe *stream_url* and return its max volume (dB), retrying remote streams.

    YouTube's CDN sometimes answers the first request for a fresh stream URL
    with a spurious 403 before the edge has validated it, so remote streams
    are retried within a single overall budget before being declared
    unplayable.  The budget is enforced here, inside this thread, so a slow
    or hanging stream can never orphan a subprocess.  Silence and a missing
    ffmpeg are properties of the track or the deployment, not of the
    connection, so they are never retried.
    """
    if not isinstance(stream_url, str) or stream_url.startswith("-"):
        raise ValueError("invalid stream url")
    remote = stream_url.startswith(("http://", "https://"))
    attempts = STREAM_PROBE_ATTEMPTS if remote else 1
    deadline = time.monotonic() + STREAM_PROBE_TOTAL_TIMEOUT
    last_error: ValueError | None = None
    for attempt in range(attempts):
        if attempt:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(STREAM_PROBE_RETRY_DELAY, remaining))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            return _probe_stream_once(stream_url, timeout=remaining)
        except (ProbeSilenceError, ProbeEnvironmentError):
            raise
        except ValueError as exc:
            last_error = exc
            if attempt < attempts - 1:
                logger.debug(
                    f"Probe attempt {attempt + 1}/{attempts} failed for "
                    f"{_redact_stream_url(stream_url)}; retrying"
                )
    if last_error is None:
        raise ProbeTimeoutError("stream probe timed out")
    raise last_error


class YTMusicData:
    """Data container for a YouTube music track's metadata."""

    def __init__(self, video: dict[str, Any]) -> None:
        self._title: str = cast(str, video.get("title", "Unknown"))
        self._url: str = cast(
            str,
            video.get(
                "url",
                cast(str, video.get("original_url", "Unknown")),
            ),
        )
        self._video: dict[str, Any] = video

    @classmethod
    async def from_url(cls, url: str) -> list[YTMusicData]:
        """Create a YTMusicData instance from a URL."""
        logger.info(f"Searching for {url}")
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(_YTDL_EXECUTOR, search, url),
            timeout=YT_SEARCH_TIMEOUT,
        )
        if result.get("entries"):
            logger.info(
                f"Found {result.get('entries')} results.",
            )
            items = [
                cls(dict(cast(dict[str, Any], video)))
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
        return cast(list[YTMusicData], [cls(dict(video))])

    @property
    def video_data(self) -> dict[str, Any]:
        """Raw yt-dlp info dict stored at search time (flat for search/playlist entries)."""
        return self._video

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

        if isinstance(self.source, str) and self.source.startswith("-"):
            raise ValueError("invalid stream source")

        if isinstance(self.source, str) and self.source.startswith((
            "http://",
            "https://",
        )):
            if not self.before_options or "-reconnect" not in shlex.split(
                self.before_options
            ):
                args.extend(_RECONNECT_OPTIONS)
            args.extend(["-headers", _FFMPEG_HEADERS])

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
