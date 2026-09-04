"""Real-network repeat-play test: 3 consecutive plays of one video.

Each play goes through the production seam
``YoutubeDLSource.from_music_data`` from scratch, so URL freshness and
the reused-vs-fresh stream fallback are exercised across plays —
catching stream URL expiry between plays and the CDN's spurious 403 on
fresh URLs (the real retry budget against the real edge).
"""

from __future__ import annotations

import asyncio

import pytest

from src.harpi_lib.music.ytdl_source import YoutubeDLSource
from src.harpi_lib.music.ytmusic import YTMusicData
from tests.network_diagnosis import build_diagnosis
from tests.network_harness import (
    BYTES_PER_SECOND,
    CANONICAL_QUERY,
    assert_pcm_flows,
    read_pcm,
    redact_url,
    require_network_env,
)

pytestmark = [
    pytest.mark.network,
    pytest.mark.usefixtures("version_banner"),
]

PLAYS = 3


async def _play_once(first: YTMusicData, play: int) -> str:
    """One play through the production seam; return a summary line."""
    source = await YoutubeDLSource.from_music_data(first)
    try:
        total, nonzero = read_pcm(source)
        assert_pcm_flows(total, nonzero, f"play {play}/{PLAYS}")
        print(
            f"[network repeat] play {play}/{PLAYS}: read {total} PCM bytes "
            f"(~{total / BYTES_PER_SECOND:.2f}s) title={source.title!r} "
            f"stream={redact_url(first.url)}"
        )
        return f"read {total} PCM bytes (~{total / BYTES_PER_SECOND:.2f}s)"
    finally:
        await asyncio.to_thread(source.cleanup)


async def test_repeat_play_three_consecutive_plays() -> None:
    """Play the first canonical result 3 times through the production seam."""
    require_network_env()

    results = await YTMusicData.from_url(CANONICAL_QUERY)
    assert results, (
        f"search returned no playable watch results for {CANONICAL_QUERY!r}"
    )
    first = results[0]

    outcomes: list[str] = []
    for play in range(1, PLAYS + 1):
        try:
            outcomes.append(await _play_once(first, play))
        except Exception as exc:
            raise AssertionError(
                f"play {play}/{PLAYS} of {first.title!r} failed: {exc!r}\n"
                f"{build_diagnosis(exc, play=play)}"
            ) from exc

    assert len(outcomes) == PLAYS
