from __future__ import annotations

import time
from collections import defaultdict


class TokenBucket:
    """Token bucket rate limiter keyed by client address.

    Buckets are keyed by the immediate TCP peer, so behind a reverse
    proxy every client collapses into the proxy's bucket and one
    misbehaving client can exhaust the shared allowance.  Trusting
    ``X-Forwarded-For`` was deliberately avoided because that header is
    client-spoofable unless the proxy strips it; this limiter is a load
    cap, not an authentication boundary.
    """

    def __init__(
        self,
        capacity: float,
        refill_per_second: float,
        max_keys: int = 10_000,
    ) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._max_keys = max_keys
        self._tokens: dict[str, float] = defaultdict(lambda: self.capacity)
        self._last_refill: dict[str, float] = {}

    def allow(self, key: str) -> bool:
        """Consume one token for *key*, returning False when exhausted."""
        now = time.monotonic()
        self._prune(now)
        last = self._last_refill.get(key, now)
        self._tokens[key] = min(
            self.capacity,
            self._tokens[key] + (now - last) * self.refill_per_second,
        )
        self._last_refill[key] = now
        if self._tokens[key] >= 1.0:
            self._tokens[key] -= 1.0
            return True
        return False

    def _prune(self, now: float) -> None:
        """Drop keys idle long enough to refill from empty."""
        if len(self._tokens) <= self._max_keys:
            return
        idle = self.capacity / self.refill_per_second
        for key in list(self._tokens):
            if now - self._last_refill.get(key, now) > idle:
                del self._tokens[key]
                del self._last_refill[key]


MUSIC_ACTION_LIMITER = TokenBucket(capacity=10, refill_per_second=2.0)
