"""Operator alerts to a private Discord channel.

Alerts are fire-and-forget: :func:`notify` only hands the alert to the
dispatcher loop, one worker sends, and an unset webhook makes every call a
no-op.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Literal

import aiohttp
from loguru import logger

AlertKind = Literal[
    "unauthorized",
    "forbidden",
    "rate_limited",
    "server_error",
    "stream_growth",
    "disk_pressure",
]

ALERT_TITLES: dict[AlertKind, str] = {
    "unauthorized": "401 unauthorized",
    "forbidden": "403 forbidden",
    "rate_limited": "429 rate limited",
    "server_error": "5xx server error",
    "stream_growth": "SSE stream growth",
    "disk_pressure": "disk pressure",
}

QUEUE_SIZE = 32
COALESCE_SECONDS = 60.0
SEND_TIMEOUT_SECONDS = 5.0
MAX_MESSAGE_CHARS = 2000
STREAM_GROWTH_THRESHOLD = 15

Sender = Callable[[str], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class Alert:
    kind: AlertKind
    detail: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.detail)

    @property
    def text(self) -> str:
        title = ALERT_TITLES[self.kind]
        if not self.detail:
            return f"[harpi] {title}"
        return f"[harpi] {title}: {self.detail}"


class WebhookSender:
    """Posts one alert to a Discord webhook, with a bounded wait."""

    def __init__(
        self, url: str, *, timeout_seconds: float = SEND_TIMEOUT_SECONDS
    ) -> None:
        self._url = url
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def __call__(self, text: str) -> None:
        async with (
            aiohttp.ClientSession(timeout=self._timeout) as http,
            http.post(
                self._url, json={"content": text[:MAX_MESSAGE_CHARS]}
            ) as response,
        ):
            response.raise_for_status()


class AlertDispatcher:
    """A bounded queue, one worker, and a coalescing window per alert."""

    def __init__(
        self,
        sender: Sender,
        *,
        queue_size: int = QUEUE_SIZE,
        coalesce_seconds: float = COALESCE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sender = sender
        self._coalesce_seconds = coalesce_seconds
        self._clock = clock
        self._queue: asyncio.Queue[Alert] = asyncio.Queue(maxsize=queue_size)
        self._recent: dict[tuple[str, str], float] = {}
        self._pending: set[tuple[str, str]] = set()
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._worker: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._loop is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._worker = self._loop.create_task(self._run(), name="harpi-alerts")

    def notify(self, kind: AlertKind, detail: str = "") -> None:
        self._ensure_started()
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        alert = Alert(kind=kind, detail=detail)
        with self._lock:
            if self._suppressed(alert):
                return
            self._pending.add(alert.key)
            self._recent[alert.key] = self._clock()
        loop.call_soon_threadsafe(self._enqueue, alert)

    async def flush(self) -> None:
        await asyncio.sleep(0)
        await self._queue.join()

    async def stop(self) -> None:
        worker = self._worker
        self._worker = None
        self._loop = None
        if worker is None:
            return
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker

    def _ensure_started(self) -> None:
        if self._loop is not None:
            return
        try:
            self.start()
        except RuntimeError:
            return

    def _suppressed(self, alert: Alert) -> bool:
        if alert.key in self._pending:
            return True
        last = self._recent.get(alert.key)
        return (
            last is not None and self._clock() - last < self._coalesce_seconds
        )

    def _enqueue(self, alert: Alert) -> None:
        try:
            self._queue.put_nowait(alert)
        except asyncio.QueueFull:
            with self._lock:
                self._pending.discard(alert.key)
                self._recent.pop(alert.key, None)
            logger.warning(f"Alert queue full; dropped {alert.kind}")

    async def _run(self) -> None:
        while True:
            alert = await self._queue.get()
            try:
                await self._sender(alert.text)
            except Exception as error:
                logger.error(f"Alert delivery failed: {type(error).__name__}")
            finally:
                with self._lock:
                    self._pending.discard(alert.key)
                self._queue.task_done()


_dispatcher: AlertDispatcher | None = None


def configure_alerts(
    webhook: str | None, *, sender: Sender | None = None
) -> AlertDispatcher | None:
    """Install the webhook sender, or remove alerts when it is unset."""
    global _dispatcher
    _dispatcher = None
    if not webhook:
        return None
    dispatcher = AlertDispatcher(sender or WebhookSender(webhook))
    try:
        dispatcher.start()
    except RuntimeError:
        return None
    _dispatcher = dispatcher
    return dispatcher


async def stop_alerts() -> None:
    global _dispatcher
    dispatcher = _dispatcher
    _dispatcher = None
    if dispatcher is not None:
        await dispatcher.stop()


def notify(kind: AlertKind, detail: str = "") -> None:
    dispatcher = _dispatcher
    if dispatcher is None:
        return
    try:
        dispatcher.notify(kind, detail)
    except Exception as error:
        logger.error(f"Alert enqueue failed: {type(error).__name__}")


def notify_stream_growth(live_streams: int) -> None:
    notify(
        "stream_growth",
        f"{live_streams} live streams at threshold {STREAM_GROWTH_THRESHOLD}",
    )
