"""One sampler per guild, shared by every open panel stream."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any

from pydantic import BaseModel

from src.panel import state
from src.panel.schemas import Directory, Position, StatusSnapshot

POLL_SECONDS = 0.5
POSITION_JUMP_SECONDS = 1.0
QUEUE_LIMIT = 32

log = logging.getLogger(__name__)

Frame = tuple[str, BaseModel]


def without_progress(snapshot: StatusSnapshot) -> dict[str, Any]:
    data = snapshot.model_dump()
    playback = data.get("playback")
    if playback is not None:
        playback.pop("progress", None)
    return data


def progress_of(snapshot: StatusSnapshot) -> tuple[float, bool]:
    playback = snapshot.playback
    if playback is None:
        return 0.0, False
    return playback.progress, playback.is_playing and not playback.is_paused


class GuildSampler:
    def __init__(self, guild_id: int | None) -> None:
        self.guild_id = guild_id
        self._sample: StatusSnapshot | None = None
        self._state_key: dict[str, Any] | None = None
        self._directory: Directory | None = None
        self._position = Position(progress=0.0)
        self._position_at: float | None = None
        self._playing = False
        self._subscribers: set[asyncio.Queue[Frame]] = set()
        self._wake = asyncio.Event()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._failing = False

    @property
    def healthy(self) -> bool:
        return self._sample is not None and not self._failing

    def current(self) -> StatusSnapshot | None:
        return self._sample

    def position(self) -> Position:
        return self._position

    def directory(self) -> Directory | None:
        return self._directory

    async def subscribe(self) -> asyncio.Queue[Frame]:
        queue: asyncio.Queue[Frame] = asyncio.Queue(maxsize=QUEUE_LIMIT)
        await self.sample()
        self._subscribers.add(queue)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Frame]) -> None:
        self._subscribers.discard(queue)
        if self._subscribers or self._task is None:
            return
        self._task.cancel()
        self._task = None

    def poke(self) -> None:
        self._wake.set()

    async def sample(self) -> None:
        async with self._lock:
            try:
                snapshot = await state.status_snapshot(self.guild_id)
                directory = state.directory_snapshot(self.guild_id)
            except Exception:
                if not self._failing:
                    log.exception(
                        "Panel sampler for guild %s failed", self.guild_id
                    )
                self._failing = True
                return
            self._failing = False
            now = time.monotonic()
            self._store_sample(snapshot, now)
            if directory != self._directory:
                self._directory = directory
                self._publish("directory", directory)

    def _store_sample(self, snapshot: StatusSnapshot, now: float) -> None:
        key = without_progress(snapshot)
        progress, playing = progress_of(snapshot)
        changed = key != self._state_key
        jumped = self._jumped(progress, now)
        self._sample = snapshot
        self._position = Position(progress=progress)
        self._position_at = now
        self._playing = playing
        if changed:
            self._state_key = key
            self._publish("status", snapshot)
        elif jumped:
            self._publish("position", self._position)

    def _jumped(self, progress: float, now: float) -> bool:
        if self._position_at is None:
            return False
        expected = self._position.progress
        if self._playing:
            expected += now - self._position_at
        return abs(progress - expected) >= POSITION_JUMP_SECONDS

    def _publish(self, name: str, payload: BaseModel) -> None:
        for queue in tuple(self._subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait((name, payload))

    async def _run(self) -> None:
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._wake.wait(), POLL_SECONDS)
            self._wake.clear()
            await self.sample()


_samplers: dict[int | None, GuildSampler] = {}


def get_sampler(guild_id: int | None) -> GuildSampler:
    sampler = _samplers.get(guild_id)
    if sampler is None:
        sampler = GuildSampler(guild_id)
        _samplers[guild_id] = sampler
    return sampler


def poke_sampler(guild_id: int | None) -> None:
    sampler = _samplers.get(guild_id)
    if sampler is not None:
        sampler.poke()
