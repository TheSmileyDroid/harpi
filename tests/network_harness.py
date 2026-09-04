"""Harness for the real-network playback tests.

Provides environment skips (no network, no cookies.txt, no ffmpeg), a
version banner printed at network-run start, and the URL redaction
helper that is the ONLY way stream URLs may appear in test output.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
from importlib.metadata import version
from typing import Any
from urllib.parse import urlsplit

from src.harpi_lib.music.stream_probe import _redact_signed_tokens
import pathlib

import pytest

CANONICAL_QUERY = "Imagine Dragons - Warriors"
COOKIES_PATH = "cookies.txt"
NETWORK_CONNECT_TIMEOUT = 5.0
# Stereo s16le 48kHz PCM: 48000 samples * 2 channels * 2 bytes.
BYTES_PER_SECOND = 48000 * 2 * 2
# How much audio to read before judging silence: matches the window the
# production silence probe uses, so a video with a silent intro is not
# judged by its first second.
PCM_WINDOW_SECONDS = 15


def require_network_env() -> None:
    """Skip the calling test unless the network environment is usable."""
    if not outbound_network_available():
        pytest.skip("no outbound network available")
    if not cookies_present():
        pytest.skip(f"missing {COOKIES_PATH} in repo root")
    if not ffmpeg_present():
        pytest.skip("ffmpeg binary not installed")


def read_pcm(
    source: Any,
    window_seconds: float = PCM_WINDOW_SECONDS,
) -> tuple[int, int]:
    """Read real PCM bytes from *source*; return (total, nonzero).

    Reads at least one second of audio (or to stream end), and keeps
    reading — up to *window_seconds* — until a non-zero byte has been
    seen, so a silent intro is not judged by its first second.
    """
    limit = int(window_seconds * BYTES_PER_SECOND)
    minimum = BYTES_PER_SECOND
    total = 0
    nonzero = 0
    while total < limit and (nonzero == 0 or total < minimum):
        chunk = source.read()
        if not chunk:
            break
        total += len(chunk)
        nonzero += sum(1 for b in chunk if b)
    return total, nonzero


def assert_pcm_flows(total: int, nonzero: int, label: str) -> None:
    """Assert non-trivial, non-silent byte flow for *label*."""
    assert total > 0, f"{label}: no PCM bytes read from the source"
    assert nonzero > 0, f"{label}: PCM stream is all-zero bytes"


def redact_url(url: str) -> str:
    """Render *url* safe for test output and failure messages.

    Strips the query string entirely and blanks any token-like
    parameter that survives; this is the only sanctioned way a URL is
    rendered in network-test output.
    """
    if not isinstance(url, str):
        return "<non-url>"
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "<invalid url>"
    if not (parsed.scheme and parsed.netloc):
        return "<non-url>"
    host = parsed.netloc.rsplit("@", 1)[-1]
    return _redact_signed_tokens(f"{parsed.scheme}://{host}{parsed.path}")


def cookies_present() -> bool:
    return pathlib.Path(COOKIES_PATH).is_file()


def ffmpeg_present() -> bool:
    return shutil.which("ffmpeg") is not None


def outbound_network_available() -> bool:
    try:
        with socket.create_connection(
            ("1.1.1.1", 443), timeout=NETWORK_CONNECT_TIMEOUT
        ):
            return True
    except OSError:
        return False


def yt_dlp_version() -> str:
    from yt_dlp.version import __version__ as v

    return v


def yt_dlp_ejs_version() -> str:
    try:
        return version("yt-dlp-ejs")
    except Exception:
        return "<not installed>"


def ffmpeg_version() -> str:
    try:
        out = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "<ffmpeg not runnable>"
    return out.stdout.splitlines()[0] if out.stdout else "<no version>"


def print_version_banner() -> None:
    print(
        "[network tests] yt-dlp "
        f"{yt_dlp_version()} | yt-dlp-ejs "
        f"{yt_dlp_ejs_version()} | {ffmpeg_version()}"
    )
