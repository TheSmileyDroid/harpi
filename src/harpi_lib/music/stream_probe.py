"""ffmpeg volumedetect probing for remote and local audio streams."""

from __future__ import annotations

import contextlib
import re
import subprocess
import time
from urllib.parse import urlsplit

from loguru import logger

from src.harpi_lib.music.ffmpeg_source import (
    _FFMPEG_HEADERS,
    _RECONNECT_OPTIONS,
)

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


def _ensure_probeable_url(stream_url: str) -> None:
    if not isinstance(stream_url, str) or stream_url.startswith("-"):
        raise ValueError("invalid stream url")


def _remaining_probe_budget(deadline: float) -> float:
    return deadline - time.monotonic()


def _log_probe_retry(attempt: int, attempts: int, stream_url: str) -> None:
    if attempt < attempts - 1:
        logger.debug(
            f"Probe attempt {attempt + 1}/{attempts} failed for "
            f"{_redact_stream_url(stream_url)}; retrying"
        )


def _ffmpeg_probe_args(stream_url: str) -> list[str]:
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
    return args


def _spawn_volume_probe(args: list[str]) -> subprocess.Popen[str]:
    try:
        return subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError:
        raise ProbeEnvironmentError(
            "ffmpeg not available for stream probing"
        ) from None


def _collect_probe_stderr(proc: subprocess.Popen[str], timeout: float) -> str:
    try:
        _, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            proc.kill()
        proc.communicate()
        raise ProbeTimeoutError("stream probe timed out") from None
    return stderr or ""


def _volume_probe_verdict(
    proc: subprocess.Popen[str], stderr: str, stream_url: str
) -> float:
    if proc.returncode != 0:
        tail = stderr.strip()[-300:]
        logger.debug(
            f"Probe failed for stream {_redact_stream_url(stream_url)}: "
            f"{_redact_signed_tokens(tail)}"
        )
        raise ValueError("stream not playable")
    max_volume = _parse_max_volume(stderr)
    if max_volume is None:
        raise ValueError("could not determine stream volume")
    if max_volume < SILENCE_MAX_VOLUME_DB:
        raise ProbeSilenceError(
            f"stream is silent (max_volume={max_volume:.1f} dB)"
        )
    return max_volume


def _probe_stream_once(stream_url: str, timeout: float) -> float:
    """Run a single ffmpeg volumedetect probe and return the max volume (dB).

    Raises a :class:`ProbeError` subclass when the stream cannot be probed
    (no audio stream, ffmpeg failure, or timeout) or is pure silence.
    """
    _ensure_probeable_url(stream_url)
    proc = _spawn_volume_probe(_ffmpeg_probe_args(stream_url))
    stderr = _collect_probe_stderr(proc, timeout)
    return _volume_probe_verdict(proc, stderr, stream_url)


def _probe_with_retries(
    stream_url: str, attempts: int, deadline: float
) -> float:
    """Probe up to *attempts* times within *deadline*, returning the volume.

    Silence and a missing ffmpeg are properties of the track or the
    deployment, not of the connection, so they are never retried.
    """
    last_error: ValueError | None = None
    for attempt in range(attempts):
        if attempt:
            remaining = _remaining_probe_budget(deadline)
            if remaining <= 0:
                break
            time.sleep(min(STREAM_PROBE_RETRY_DELAY, remaining))
        remaining = _remaining_probe_budget(deadline)
        if remaining <= 0:
            break
        try:
            return _probe_stream_once(stream_url, timeout=remaining)
        except (ProbeSilenceError, ProbeEnvironmentError):
            raise
        except ValueError as exc:
            last_error = exc
            _log_probe_retry(attempt, attempts, stream_url)
    if last_error is None:
        raise ProbeTimeoutError("stream probe timed out")
    raise last_error


def probe_stream_audio(stream_url: str) -> float:
    """Probe *stream_url* and return its max volume (dB), retrying remote streams.

    YouTube's CDN sometimes answers the first request for a fresh stream URL
    with a spurious 403 before the edge has validated it, so remote streams
    are retried within a single overall budget before being declared
    unplayable.  The budget is enforced here, inside this thread, so a slow
    or hanging stream can never orphan a subprocess.
    """
    _ensure_probeable_url(stream_url)
    remote = stream_url.startswith(("http://", "https://"))
    attempts = STREAM_PROBE_ATTEMPTS if remote else 1
    deadline = time.monotonic() + STREAM_PROBE_TOTAL_TIMEOUT
    return _probe_with_retries(stream_url, attempts, deadline)
