"""One-line diagnostics for the YouTube source chain.

Every stage of the chain calls :func:`record`, which writes at DEBUG. Turning on
``HARPI_YTDL_DEBUG`` raises the level ``logging_setup`` installs, so the events
land in the same rotated log as everything else.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any
from urllib.parse import urlsplit

from loguru import logger

STDERR_TAIL_LINES = 40


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
    """Write one diagnostic line at DEBUG level."""
    rendered = " ".join(f"{key}={value!r}" for key, value in fields.items())
    logger.debug(f"{event} {rendered}".rstrip())
