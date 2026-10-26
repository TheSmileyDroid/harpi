"""Unit tests for the panel's token buckets and stream slots."""

from __future__ import annotations

from src.panel import rate_limit


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_a_bucket_allows_its_limit_and_then_refuses():
    clock = FakeClock()
    bucket = rate_limit.TokenBucket(3, clock=clock)

    assert [bucket.take().allowed for _ in range(3)] == [True, True, True]

    refused = bucket.take()

    assert refused.allowed is False
    assert refused.retry_after_seconds == 20


def test_a_bucket_refills_at_the_window_rate():
    clock = FakeClock()
    bucket = rate_limit.TokenBucket(1, clock=clock)
    assert bucket.take().allowed is True
    assert bucket.take().allowed is False

    clock.advance(60)

    assert bucket.take().allowed is True


def test_a_bucket_never_exceeds_its_capacity():
    clock = FakeClock()
    bucket = rate_limit.TokenBucket(2, clock=clock)
    clock.advance(600)

    assert [bucket.take().allowed for _ in range(3)] == [True, True, False]


def test_retry_after_rounds_up_to_the_next_whole_second():
    clock = FakeClock()
    bucket = rate_limit.TokenBucket(1, clock=clock)
    bucket.take()
    clock.advance(59.5)

    refused = bucket.take()

    assert refused.allowed is False
    assert refused.retry_after_seconds == 1


def test_each_user_gets_their_own_bucket():
    clock = FakeClock()
    buckets = rate_limit.UserTokenBuckets(1, clock=clock)
    assert buckets.take("a").allowed is True
    assert buckets.take("a").allowed is False
    assert buckets.take("b").allowed is True


def test_stream_slots_cap_connections_per_user():
    slots = rate_limit.StreamSlots(per_user=2, per_guild=20)

    held = [slots.acquire("a", None) for _ in range(2)]

    assert all(slot is not None for slot in held)
    assert slots.acquire("a", None) is None
    assert slots.acquire("b", None) is not None


def test_stream_slots_cap_connections_per_guild():
    slots = rate_limit.StreamSlots(per_user=5, per_guild=1)

    assert slots.acquire("a", 7) is not None
    assert slots.acquire("b", 7) is None
    assert slots.acquire("b", 8) is not None


def test_releasing_a_slot_frees_it_once():
    slots = rate_limit.StreamSlots(per_user=1, per_guild=1)
    slot = slots.acquire("a", 7)
    assert slot is not None

    slot.release()
    slot.release()

    assert slots.acquire("a", 7) is not None
