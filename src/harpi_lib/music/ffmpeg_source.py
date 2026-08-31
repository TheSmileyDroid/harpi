"""ffmpeg-backed audio sources for Discord playback."""

from __future__ import annotations

import io
import math
import shlex
import subprocess
import threading
from typing import IO, cast, override

import discord
from discord.opus import Encoder
from loguru import logger
from yt_dlp.utils.networking import std_headers

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

    def _input_stage_args(self) -> list[str]:
        args: list[str] = []

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
            args.extend(self._http_input_args())

        return args

    def _http_input_args(self) -> list[str]:
        """Return the reconnect/header args required for HTTP sources."""
        args: list[str] = []
        if not self.before_options or "-reconnect" not in shlex.split(
            self.before_options
        ):
            args.extend(_RECONNECT_OPTIONS)
        args.extend(["-headers", _FFMPEG_HEADERS])
        return args

    def _pipe_input(self) -> IO[bytes]:
        return cast(IO[bytes], cast(object, self.source))

    def _start_process(self, args: list[str]) -> subprocess.Popen[bytes]:
        input_stream: IO[bytes] | int | None = (
            self._pipe_input() if self.pipe else subprocess.DEVNULL
        )
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

    def _spawn_process(self) -> subprocess.Popen[bytes]:
        args: list[str] = [self.executable, *self._input_stage_args()]
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
        return self._start_process(args)

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
    def read(self) -> bytes:  # type: ignore[override]
        while True:
            proc, superseded = self._ensure_process()
            if superseded:
                continue
            if proc is None or proc.stdout is None:
                return b""
            frame = self._read_frame(proc)
            if len(frame) == Encoder.FRAME_SIZE:
                return frame
            if self._discard_partial_frame(proc):
                return b""

    def _ensure_process(
        self,
    ) -> tuple[subprocess.Popen[bytes] | None, bool]:
        """Return the live ffmpeg process and whether the spawn was superseded.

        A None process with superseded=False means the source is shut
        down, so the caller stops; superseded=True means a concurrent seek
        invalidated the freshly spawned process and the caller retries.
        """
        with self._proc_lock:
            proc = self._process
            if proc is not None:
                return proc, False
            if self._shutdown:
                return None, False
            self._generation += 1
            generation = self._generation

        new_proc = self._spawn_process()
        with self._proc_lock:
            if self._shutdown:
                self._terminate(new_proc)
                return None, False
            if self._generation != generation:
                self._terminate(new_proc)
                return None, True
            self._process = new_proc
            return new_proc, False

    @staticmethod
    def _read_frame(proc: subprocess.Popen[bytes]) -> bytes:
        try:
            assert proc.stdout is not None
            return proc.stdout.read(Encoder.FRAME_SIZE)
        except (OSError, ValueError):
            return b""

    def _discard_partial_frame(self, proc: subprocess.Popen[bytes]) -> bool:
        """Retire *proc* after a short read; True stops the read loop."""
        with self._proc_lock:
            is_current = self._process is proc
            if is_current:
                self._process = None
        if is_current:
            self._terminate(proc)
        return is_current

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
    def cleanup(self) -> None:  # type: ignore[override]
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
