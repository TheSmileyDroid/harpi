"""Unattended soak: play tracks back-to-back through the production seam.

Reproduces the intermittent "starts then stops" playback failures
without Discord, so a fix can be proven repeatably. Each track is loaded
via the production seam and read until it ends or a per-track window
elapses; a track that stops well before its known duration, flows no
PCM, or fails to load is a failure. Exit code is 1 when anything fails.

Run it in the background while the live bot is exercised:

    HARPI_YTDL_DEBUG=1 .venv/bin/python -m tools.soak_playback --tracks 20 --window 60

Diagnostics for every event land in .scratch/ytdl-debug/ytdl-debug.log.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from src.harpi_lib.music.ytdl_source import YoutubeDLSource
from src.harpi_lib.music.ytmusic import YTMusicData
from tests.network_harness import BYTES_PER_SECOND, read_to_end

EARLY_STOP_GRACE_SECONDS = 5.0
DEFAULT_TRACKS = 20
DEFAULT_WINDOW_SECONDS = 60.0
QUERIES = (
    "Imagine Dragons - Warriors",
    "Daft Punk - Instant Crush",
    "Tame Impala - The Less I Know The Better",
)


@dataclass
class TrackResult:
    title: str
    played: float
    expected: float
    nonzero: int
    ended: bool
    error: str | None = None

    @property
    def early(self) -> bool:
        return (
            self.error is None
            and self.expected > 0
            and self.ended
            and self.played < self.expected - EARLY_STOP_GRACE_SECONDS
        )

    @property
    def ok(self) -> bool:
        return self.error is None and self.nonzero > 0 and not self.early


async def _collect(limit: int) -> list[YTMusicData]:
    tracks: list[YTMusicData] = []
    seen: set[str] = set()
    for query in QUERIES:
        for item in await YTMusicData.from_url(query):
            if item.url in seen or not item.duration:
                continue
            seen.add(item.url)
            tracks.append(item)
            if len(tracks) >= limit:
                return tracks
    return tracks


async def _play(item: YTMusicData, window_seconds: float) -> TrackResult:
    try:
        source = await YoutubeDLSource.from_music_data(item)
    except Exception as exc:
        return TrackResult(
            item.title, 0.0, float(item.duration or 0), 0, False, repr(exc)
        )
    try:
        total, nonzero, ended = await asyncio.to_thread(
            read_to_end, source, window_seconds
        )
        expected = float(source.data.get("duration") or 0)
    finally:
        await asyncio.to_thread(source.cleanup)
    return TrackResult(
        item.title, total / BYTES_PER_SECOND, expected, nonzero, ended
    )


async def _run(
    tracks: list[YTMusicData], window_seconds: float
) -> list[TrackResult]:
    results: list[TrackResult] = []
    for index, item in enumerate(tracks, start=1):
        result = await _play(item, window_seconds)
        results.append(result)
        status = "ok" if result.ok else "FAIL"
        print(
            f"[soak {index}/{len(tracks)}] {status} "
            f"played={result.played:.1f}s expected={result.expected:.1f}s "
            f"early={result.early} title={result.title!r} "
            f"error={result.error}"
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracks", type=int, default=DEFAULT_TRACKS)
    parser.add_argument("--window", type=float, default=DEFAULT_WINDOW_SECONDS)
    args = parser.parse_args(argv)

    tracks = asyncio.run(_collect(args.tracks))
    if not tracks:
        print("[soak] no tracks collected")
        return 1

    results = asyncio.run(_run(tracks, args.window))
    failures = [result for result in results if not result.ok]
    print(f"[soak] {len(results) - len(failures)}/{len(results)} ok")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
