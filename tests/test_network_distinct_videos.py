"""Real-network distinct-videos stability run: the first half of the
agreed stability bar.

Searches the canonical query via the production search path, takes the
first 10 distinct results (deduped by video id), and drives each one
through the production seam ``YoutubeDLSource.from_music_data`` (extract
→ format pick → stream → silence probe), then reads real PCM bytes and
asserts non-trivial, non-all-zero byte flow.

Failure reporting: every video's outcome is accumulated and reported
together at the end; a failure names the video by title + id (never a
signed URL), carries the verbatim yt-dlp/ffmpeg error inside the
diagnosis block, plus the library-version banner.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

import pytest

from src.harpi_lib.music.ytdl_source import YoutubeDLSource
from src.harpi_lib.music.ytmusic import YTMusicData
from tests.network_diagnosis import build_diagnosis
from tests.network_harness import (
    BYTES_PER_SECOND,
    CANONICAL_QUERY,
    assert_pcm_flows,
    read_pcm,
    require_network_env,
)

pytestmark = [
    pytest.mark.network,
    pytest.mark.usefixtures("version_banner"),
]

DISTINCT_VIDEO_COUNT = 10


def video_id(musicdata: YTMusicData) -> str:
    """Extract the 11-char video id from the watch URL of *musicdata*."""
    query = parse_qs(urlsplit(musicdata.get_url()).query)
    ids = query.get("v")
    return ids[0] if ids else "<no-id>"


def _first_distinct(
    results: list[YTMusicData], count: int
) -> list[YTMusicData]:
    """First *count* results with unique video ids, in search order."""
    distinct: list[YTMusicData] = []
    seen: set[str] = set()
    for item in results:
        vid = video_id(item)
        if vid in seen:
            continue
        seen.add(vid)
        distinct.append(item)
        if len(distinct) == count:
            break
    return distinct


@dataclass
class VideoOutcome:
    title: str
    vid: str
    passed: bool
    detail: str


async def _play_video(musicdata: YTMusicData) -> str:
    """Drive one video through the production seam; return a summary."""
    source = await YoutubeDLSource.from_music_data(musicdata)
    try:
        total, nonzero = read_pcm(source)
        assert_pcm_flows(total, nonzero, f"video {video_id(musicdata)}")
        return f"read {total} PCM bytes (~{total / BYTES_PER_SECOND:.2f}s)"
    finally:
        await asyncio.to_thread(source.cleanup)


@pytest.mark.network
async def test_ten_distinct_videos_stability_run() -> None:
    """10 distinct search results each extract, stream, and pass the
    silence probe through the production seam."""
    require_network_env()

    results = await YTMusicData.from_url(CANONICAL_QUERY)
    assert results, (
        f"search returned no playable watch results for {CANONICAL_QUERY!r}"
    )

    distinct = _first_distinct(results, DISTINCT_VIDEO_COUNT)
    assert len(distinct) == DISTINCT_VIDEO_COUNT, (
        f"search yielded only {len(distinct)} distinct videos, "
        f"needed {DISTINCT_VIDEO_COUNT}"
    )

    outcomes: list[VideoOutcome] = []
    for item in distinct:
        vid = video_id(item)
        print(f"[network run] video {vid}: {item.title!r} ...")
        try:
            detail = await _play_video(item)
        except Exception as exc:
            diagnosis = build_diagnosis(exc, video=f"[{vid}] {item.title!r}")
            outcomes.append(VideoOutcome(item.title, vid, False, diagnosis))
            print(f"[network run] video {vid}: FAIL\n{diagnosis}")
        else:
            outcomes.append(VideoOutcome(item.title, vid, True, detail))
            print(f"[network run] video {vid}: pass ({detail})")

    failures = [o for o in outcomes if not o.passed]
    if failures:
        lines = [
            f"{i}. [{o.vid}] {o.title!r}: FAIL\n{o.detail}"
            for i, o in enumerate(outcomes, 1)
        ]
        raise AssertionError(
            f"{len(failures)}/{len(outcomes)} distinct videos failed "
            f"the stability run\n" + "\n".join(lines)
        )

    for o in outcomes:
        print(f"[network run] {o.vid} {o.title!r}: pass ({o.detail})")
