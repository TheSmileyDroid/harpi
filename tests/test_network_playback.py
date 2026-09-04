"""Real-network smoke test: search → production source → real PCM."""

from __future__ import annotations

import asyncio

import pytest

from src.harpi_lib.music.ytdl_source import YoutubeDLSource
from src.harpi_lib.music.ytmusic import YTMusicData
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


async def test_smoke_search_source_pcm_flow() -> None:
    """Search, build the production source, and read real PCM."""
    require_network_env()

    results = await YTMusicData.from_url(CANONICAL_QUERY)
    assert results, (
        f"search returned no playable watch results for {CANONICAL_QUERY!r}"
    )
    first = results[0]

    source = await YoutubeDLSource.from_music_data(first)
    try:
        total, nonzero = read_pcm(source)
        assert_pcm_flows(
            total, nonzero, f"smoke for {first.title!r} ({first.url})"
        )
        print(
            f"[network smoke] read {total} PCM bytes "
            f"(~{total / BYTES_PER_SECOND:.2f}s) "
            f"from {redact_url(first.url)}"
        )
    finally:
        await asyncio.to_thread(source.cleanup)
