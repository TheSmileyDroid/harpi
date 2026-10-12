"""Real-network full-track test: play a track through to its end.

The 1s-read smoke tests prove a stream starts. This proves a stream
survives past the first second, which is where the "plays 2 seconds and
stops" failures live: a mid-stream CDN 403, a dropped reconnect, or an
ffmpeg process that dies after the probe passed.
"""

from __future__ import annotations

import asyncio

import pytest

from src.harpi_lib.music.ytdl_source import YoutubeDLSource
from src.harpi_lib.music.ytmusic import YTMusicData
from tests.network_harness import (
    BYTES_PER_SECOND,
    CANONICAL_QUERY,
    TRACK_MAX_SECONDS,
    assert_pcm_flows,
    read_to_end,
    redact_url,
    require_network_env,
)

pytestmark = [
    pytest.mark.network,
    pytest.mark.usefixtures("version_banner"),
]

EARLY_STOP_GRACE_SECONDS = 5.0


async def _play_to_end(
    first: YTMusicData,
) -> tuple[float, float, int, int, bool]:
    source = await YoutubeDLSource.from_music_data(first)
    try:
        total, nonzero, ended = await asyncio.to_thread(
            read_to_end, source, TRACK_MAX_SECONDS
        )
        expected = float(source.data.get("duration") or 0)
    finally:
        await asyncio.to_thread(source.cleanup)
    return total / BYTES_PER_SECOND, expected, total, nonzero, ended


async def test_full_track_plays_to_the_end() -> None:
    """Play the canonical result until it ends; no early stop allowed."""
    require_network_env()

    results = await YTMusicData.from_url(CANONICAL_QUERY)
    assert results, (
        f"search returned no playable watch results for {CANONICAL_QUERY!r}"
    )
    first = results[0]

    played, expected, total, nonzero, ended = await _play_to_end(first)

    assert_pcm_flows(total, nonzero, "full-track")
    print(
        f"[network full-track] played {played:.1f}s of {expected:.1f}s "
        f"ended={ended} title={first.title!r} stream={redact_url(first.url)}"
    )
    if expected > 0 and ended:
        assert played >= expected - EARLY_STOP_GRACE_SECONDS, (
            f"track ended early after {played:.1f}s of {expected:.1f}s"
        )
