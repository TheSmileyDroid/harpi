"""Unit tests for the token bucket rate limiter."""

import time

from src.api.rate_limit import TokenBucket


def test_token_bucket_allows_burst_then_denies():
    bucket = TokenBucket(capacity=3, refill_per_second=1.0)

    assert bucket.allow("a")
    assert bucket.allow("a")
    assert bucket.allow("a")
    assert not bucket.allow("a")


def test_token_bucket_keys_are_isolated():
    bucket = TokenBucket(capacity=1, refill_per_second=1.0)

    assert bucket.allow("a")
    assert not bucket.allow("a")
    assert bucket.allow("b")


def test_limiter_prunes_idle_keys():
    bucket = TokenBucket(capacity=10, refill_per_second=10.0, max_keys=2)
    bucket.allow("a")
    bucket.allow("b")
    bucket.allow("c")
    bucket._last_refill["a"] = time.monotonic() - 10.0
    bucket.allow("d")

    assert "a" not in bucket._tokens
    assert "b" in bucket._tokens
    assert "c" in bucket._tokens
    assert "d" in bucket._tokens
