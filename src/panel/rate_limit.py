from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

MINUTE_SECONDS = 60.0
SEARCHES_PER_MINUTE = 20
QUEUE_ACTIONS_PER_MINUTE = 10
STREAM_CONNECTIONS_PER_USER = 5
STREAM_CONNECTIONS_PER_GUILD = 20
STREAM_RETRY_AFTER_SECONDS = 30


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    retry_after_seconds: int = 0


class TokenBucket:
    """One key's budget, refilled at a fixed rate from an injected clock."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = MINUTE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._capacity = float(limit)
        self._refill_per_second = limit / window_seconds
        self._clock = clock
        self._tokens = float(limit)
        self._updated_at = clock()

    def take(self) -> Decision:
        now = self._clock()
        elapsed = max(0.0, now - self._updated_at)
        self._tokens = min(
            self._capacity, self._tokens + elapsed * self._refill_per_second
        )
        self._updated_at = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return Decision(allowed=True)
        seconds_to_next = (1.0 - self._tokens) / self._refill_per_second
        return Decision(
            allowed=False,
            retry_after_seconds=max(1, math.ceil(seconds_to_next)),
        )


class UserTokenBuckets:
    """A TokenBucket per user id, all refilled at the same rate."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = MINUTE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._buckets: dict[str, TokenBucket] = {}

    def take(self, user_id: str) -> Decision:
        bucket = self._buckets.get(user_id)
        if bucket is None:
            bucket = TokenBucket(
                self._limit, self._window_seconds, self._clock
            )
            self._buckets[user_id] = bucket
        return bucket.take()


class StreamSlot:
    """One live stream's claim on the user and guild connection budgets."""

    def __init__(
        self, slots: StreamSlots, user_id: str, guild_id: int | None
    ) -> None:
        self._slots = slots
        self._user_id = user_id
        self._guild_id = guild_id
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._slots._release(self._user_id, self._guild_id)


class StreamSlots:
    """Live SSE connections counted per user and per guild."""

    def __init__(
        self,
        per_user: int = STREAM_CONNECTIONS_PER_USER,
        per_guild: int = STREAM_CONNECTIONS_PER_GUILD,
    ) -> None:
        self._per_user = per_user
        self._per_guild = per_guild
        self._users: dict[str, int] = {}
        self._guilds: dict[int, int] = {}

    def acquire(self, user_id: str, guild_id: int | None) -> StreamSlot | None:
        if self._users.get(user_id, 0) >= self._per_user:
            return None
        if (
            guild_id is not None
            and self._guilds.get(guild_id, 0) >= self._per_guild
        ):
            return None
        self._users[user_id] = self._users.get(user_id, 0) + 1
        if guild_id is not None:
            self._guilds[guild_id] = self._guilds.get(guild_id, 0) + 1
        return StreamSlot(self, user_id, guild_id)

    def _release(self, user_id: str, guild_id: int | None) -> None:
        self._users[user_id] -= 1
        if self._users[user_id] <= 0:
            del self._users[user_id]
        if guild_id is None:
            return
        self._guilds[guild_id] -= 1
        if self._guilds[guild_id] <= 0:
            del self._guilds[guild_id]
