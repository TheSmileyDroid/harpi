"""yt-dlp client, YouTube search, and the YTMusicData track container."""

from __future__ import annotations

import asyncio
import concurrent.futures
import re
import shutil
import time
from collections.abc import Callable
from typing import Any, cast

import yt_dlp
from loguru import logger

from src.harpi_lib.music.nothing_found import NothingFoundError

ytdl_format_options: dict[str, Any] = {
    "format": "m4a/bestaudio/best",
    "outtmpl": ".audios/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "extract_flat": True,
    "verbose": True,
    "no_warnings": False,
    "default_search": "auto_warning",
    "cookiefile": "cookies.txt",
    "socket_timeout": 15,
    "retries": 1,
    "fragment_retries": 1,
    "extractor_retries": 1,
}

# yt-dlp's own priority order for JS challenge runtimes; only deno is
# enabled by default, so without this option node/bun are ignored even
# when installed and YouTube degrades to clients whose streams fail.
JS_RUNTIME_PRIORITY = ("deno", "node", "quickjs", "bun")


def detect_js_runtimes(
    lookup: Callable[[str], str | None] = shutil.which,
) -> list[str]:
    """Find installed JS runtimes, in yt-dlp's priority order."""
    return [name for name in JS_RUNTIME_PRIORITY if lookup(name)]


def js_runtimes_option(runtimes: list[str]) -> dict[str, dict[str, Any]]:
    """Build yt-dlp's ``js_runtimes`` option ({runtime: config})."""
    return {name: {} for name in runtimes}


_detected_js_runtimes = detect_js_runtimes()
if _detected_js_runtimes:
    ytdl_format_options["js_runtimes"] = js_runtimes_option(
        _detected_js_runtimes
    )
    logger.info(
        f"yt-dlp JS challenge runtimes: {', '.join(_detected_js_runtimes)}"
    )
else:
    logger.warning(
        "No JavaScript runtime found (deno, node, quickjs, bun). "
        "YouTube extraction is degraded and most tracks will be "
        "rejected as unplayable. Install deno, see "
        "https://github.com/yt-dlp/yt-dlp/wiki/EJS"
    )

YT_SEARCH_TIMEOUT = 30.0
YT_EXTRACT_TIMEOUT = 25.0

ytdl = yt_dlp.YoutubeDL(cast(Any, ytdl_format_options))

# One YoutubeDL instance must not be called from two threads at once, so
# each single-worker executor owns its own instance.  Search gets its own
# pair so a long chain of track extractions (for example a run of
# unplayable tracks being skipped) can never starve a panel search past
# its request timeout.
search_ytdl = yt_dlp.YoutubeDL(cast(Any, ytdl_format_options))

_YTDL_SERIAL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="ytdl"
)
_YTDL_SEARCH_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="ytdl-search"
)


def search(arg: str) -> dict[str, Any]:
    """Search YouTube and return the music information."""
    start_time = time.time()

    URL_REGEX = re.compile(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    )
    video: dict[str, Any] | None = None
    try:
        if not URL_REGEX.match(arg):
            video = cast(
                dict[str, Any],
                cast(
                    object,
                    search_ytdl.extract_info(
                        f"ytsearch10:{arg}",
                        download=False,
                        process=False,
                    ),
                ),
            )
        else:
            video = cast(
                dict[str, Any],
                cast(
                    object,
                    search_ytdl.extract_info(
                        arg, download=False, process=False
                    ),
                ),
            )
    except Exception as e:
        logger.opt(exception=True).error(f"Error during search: {e}")
    if not video:
        raise NothingFoundError(arg)
    logger.info(
        f"Searched for {arg} in {time.time() - start_time} seconds.",
    )
    return video


class YTMusicData:
    """Data container for a YouTube music track's metadata."""

    def __init__(self, video: dict[str, Any]) -> None:
        self._title: str = cast(str, video.get("title", "Unknown"))
        self._url: str = cast(
            str,
            video.get(
                "url",
                cast(str, video.get("original_url", "Unknown")),
            ),
        )
        self._video: dict[str, Any] = video

    @classmethod
    async def from_url(cls, url: str) -> list[YTMusicData]:
        """Create a YTMusicData instance from a URL."""
        logger.info(f"Searching for {url}")
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(_YTDL_SEARCH_EXECUTOR, search, url),
            timeout=YT_SEARCH_TIMEOUT,
        )
        if result.get("entries"):
            logger.info(
                f"Found {result.get('entries')} results.",
            )
            items = [
                cls(dict(cast(dict[str, Any], video)))
                for video in cast(list, result.get("entries"))
            ]
            return [
                item
                for item in items
                if item.duration
                and item.duration > 0
                and "watch?v=" in item.url
            ]
        video = result
        return cast(list[YTMusicData], [cls(dict(video))])

    @property
    def video_data(self) -> dict[str, Any]:
        """Raw yt-dlp info dict stored at search time (flat for search/playlist entries)."""
        return self._video

    @property
    def title(self) -> str:
        return self._title

    def get_url(self) -> str:
        return self._url

    @property
    def url(self) -> str:
        return self._url

    @property
    def duration(self) -> int:
        return cast(int, self._video.get("duration", 0))

    @property
    def uploader(self) -> str:
        return cast(
            str,
            self._video.get(
                "uploader",
                self._video.get("channel", self._video.get("creator", "")),
            ),
        )
