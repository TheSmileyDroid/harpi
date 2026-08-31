"""Retry-budget tests for the ffmpeg stream probe."""

from __future__ import annotations

import pytest

from src.harpi_lib.music import stream_probe
from src.harpi_lib.music.stream_probe import (
    ProbeEnvironmentError,
    ProbeSilenceError,
    ProbeTimeoutError,
    _probe_with_retries,
)

FAR_FUTURE_DEADLINE = float("inf")
URL = "https://stream.example.com/audio.opus"


@pytest.fixture
def no_sleep(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(stream_probe.time, "sleep", slept.append)
    return slept


def test_returns_volume_after_transient_failures(monkeypatch, no_sleep):
    outcomes = iter([ValueError("boom"), ValueError("boom"), -12.0])

    def flaky(stream_url: str, timeout: float) -> float:
        result = next(outcomes)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(stream_probe, "_probe_stream_once", flaky)

    result = _probe_with_retries(URL, attempts=3, deadline=FAR_FUTURE_DEADLINE)
    assert result == pytest.approx(-12.0)
    assert no_sleep == [1.0, 1.0]


def test_retry_sleeps_at_most_the_remaining_budget(monkeypatch, no_sleep):
    monkeypatch.setattr(
        stream_probe,
        "_probe_stream_once",
        lambda stream_url, timeout: (_ for _ in ()).throw(ValueError("boom")),
    )
    monkeypatch.setattr(
        stream_probe, "_remaining_probe_budget", lambda deadline: 0.5
    )

    with pytest.raises(ValueError, match="boom"):
        _probe_with_retries(URL, attempts=3, deadline=FAR_FUTURE_DEADLINE)

    assert no_sleep == [0.5, 0.5]


def test_breaks_before_retry_when_budget_exhausted(monkeypatch, no_sleep):
    monkeypatch.setattr(
        stream_probe,
        "_probe_stream_once",
        lambda stream_url, timeout: (_ for _ in ()).throw(ValueError("boom")),
    )
    budgets = iter([15.0, 0.0])
    monkeypatch.setattr(
        stream_probe,
        "_remaining_probe_budget",
        lambda deadline: next(budgets),
    )

    with pytest.raises(ValueError, match="boom"):
        _probe_with_retries(URL, attempts=3, deadline=FAR_FUTURE_DEADLINE)

    assert no_sleep == []


def test_raises_probe_timeout_when_budget_gone_before_first_attempt(
    monkeypatch, no_sleep
):
    monkeypatch.setattr(
        stream_probe, "_remaining_probe_budget", lambda deadline: 0.0
    )

    with pytest.raises(ProbeTimeoutError):
        _probe_with_retries(URL, attempts=3, deadline=FAR_FUTURE_DEADLINE)

    assert no_sleep == []


def test_silence_is_never_retried(monkeypatch, no_sleep):
    def silent(stream_url: str, timeout: float) -> float:
        raise ProbeSilenceError("stream is silent")

    monkeypatch.setattr(stream_probe, "_probe_stream_once", silent)

    with pytest.raises(ProbeSilenceError):
        _probe_with_retries(URL, attempts=3, deadline=FAR_FUTURE_DEADLINE)

    assert no_sleep == []


def test_environment_failure_is_never_retried(monkeypatch, no_sleep):
    def broken(stream_url: str, timeout: float) -> float:
        raise ProbeEnvironmentError("ffmpeg missing")

    monkeypatch.setattr(stream_probe, "_probe_stream_once", broken)

    with pytest.raises(ProbeEnvironmentError):
        _probe_with_retries(URL, attempts=3, deadline=FAR_FUTURE_DEADLINE)

    assert no_sleep == []
