"""Rolling diagnostic capture for the YouTube source chain.

Every stage of the chain writes one line per event here, and any
ffmpeg stderr tail is attached when a stream ends early or fails. The
file lives under ``.scratch/ytdl-debug/`` (gitignored) and rotates by
size so a long soak cannot fill the disk.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from loguru import logger

from src.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[3]
DEBUG_DIR = REPO_ROOT / ".scratch" / "ytdl-debug"
DEBUG_FILE = DEBUG_DIR / "ytdl-debug.log"
ROTATED_FILE = DEBUG_DIR / "ytdl-debug.log.1"
MAX_BYTES = 2_000_000
STDERR_TAIL_LINES = 40
CAPTURE_ENABLED = Settings.from_env().ytdl_debug

_write_lock = threading.Lock()


class StderrTail:
    """Bounded, thread-safe ring buffer of a process's stderr lines."""

    def __init__(self, max_lines: int = STDERR_TAIL_LINES) -> None:
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._lock = threading.Lock()

    def add(self, line: str) -> None:
        with self._lock:
            self._lines.append(line.rstrip("\n"))

    def tail(self) -> str:
        with self._lock:
            return "\n".join(self._lines)


def _rotate_if_needed() -> None:
    try:
        if DEBUG_FILE.exists() and DEBUG_FILE.stat().st_size > MAX_BYTES:
            DEBUG_FILE.replace(ROTATED_FILE)
    except OSError as exc:
        logger.debug(f"ytdl debug rotation failed: {exc}")


def redact_source(source: object) -> str:
    """Render an audio source safe for logs: bare host, or a pipe marker."""
    if not isinstance(source, str):
        return "<pipe>" if hasattr(source, "read") else "<non-url>"
    if not source.startswith(("http://", "https://")):
        return "<non-url>"
    parsed = urlsplit(source)
    host = parsed.netloc.rsplit("@", 1)[-1]
    return f"{parsed.scheme}://{host}{parsed.path}"


def record(event: str, **fields: Any) -> None:
    """Append one diagnostic line to the rolling file and the log."""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    rendered = " ".join(f"{key}={value!r}" for key, value in fields.items())
    line = f"{stamp} {event} {rendered}".rstrip()
    logger.debug(line)
    if not CAPTURE_ENABLED:
        return
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            _rotate_if_needed()
            with DEBUG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except OSError as exc:
        logger.debug(f"ytdl debug write failed: {exc}")
