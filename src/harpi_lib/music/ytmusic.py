"""yt-dlp client, YouTube search, and the YTMusicData track container."""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import re
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import yt_dlp
from loguru import logger

from src.config import Settings
from src.harpi_lib.music import cookie_store
from src.harpi_lib.music.nothing_found import NothingFoundError

_WORK_DIR = Path(Settings.from_env().work_dir)

ytdl_format_options: dict[str, Any] = {
    "format": "m4a/bestaudio/best",
    "outtmpl": str(
        _WORK_DIR / "audios" / "%(extractor)s-%(id)s-%(title)s.%(ext)s"
    ),
    "cachedir": str(_WORK_DIR / "yt-dlp-cache"),
    "restrictfilenames": True,
    "noplaylist": False,
    "extract_flat": True,
    "verbose": True,
    "no_warnings": False,
    "default_search": "auto_warning",
    "socket_timeout": 15,
    "retries": 1,
    "fragment_retries": 1,
    "extractor_retries": 1,
}

_work_cookie = cookie_store.prepare_cookie_file()
if _work_cookie is not None:
    ytdl_format_options["cookiefile"] = str(_work_cookie)

JS_RUNTIME_PRIORITY = ("deno", "node", "quickjs", "bun")

JS_RUNTIME_BINARIES = {
    "deno": "deno",
    "node": "node",
    "quickjs": "qjs",
    "bun": "bun",
}

DEFAULT_JS_RUNTIME_DIRS = (
    "~/.deno/bin",
    "~/.bun/bin",
    "~/.local/bin",
    "/usr/local/bin",
)


def js_runtime_search_dirs(configured: str = "") -> list[Path]:
    """Return directories to search for runtimes, configured ones first.

    *configured* is a path-separator list (from ``HARPI_JS_RUNTIME_DIRS``)
    prepended to the defaults; it exists because services such as systemd
    start Harpi with a PATH that omits per-user install directories.
    """
    directives = [entry for entry in configured.split(os.pathsep) if entry]
    directives.extend(DEFAULT_JS_RUNTIME_DIRS)
    resolved: list[Path] = []
    seen: set[str] = set()
    for directive in directives:
        path = Path(directive).expanduser()
        if str(path) not in seen:
            seen.add(str(path))
            resolved.append(path)
    return resolved


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def find_js_runtime(
    name: str,
    dirs: list[Path],
    lookup: Callable[[str], str | None] = shutil.which,
) -> str | None:
    """Resolve *name* to an executable path, PATH first then *dirs*."""
    binary = JS_RUNTIME_BINARIES[name]
    found = lookup(binary)
    if found:
        return found
    for directory in dirs:
        candidate = directory / binary
        if _is_executable_file(candidate):
            return str(candidate)
    return None


def detect_js_runtimes(
    lookup: Callable[[str], str | None] = shutil.which,
    dirs: list[Path] | None = None,
) -> dict[str, str]:
    """Resolve installed runtimes to executable paths, in priority order."""
    search_dirs = (
        js_runtime_search_dirs(Settings.from_env().js_runtime_dirs)
        if dirs is None
        else dirs
    )
    resolved: dict[str, str] = {}
    for name in JS_RUNTIME_PRIORITY:
        path = find_js_runtime(name, search_dirs, lookup)
        if path:
            resolved[name] = path
    return resolved


def js_runtimes_option(runtimes: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Build yt-dlp's ``js_runtimes`` option with an explicit path each."""
    return {name: {"path": path} for name, path in runtimes.items()}


_detected_js_runtimes = detect_js_runtimes()
if _detected_js_runtimes:
    ytdl_format_options["js_runtimes"] = js_runtimes_option(
        _detected_js_runtimes
    )
    logger.info(
        "yt-dlp JS challenge runtimes: "
        + ", ".join(
            f"{name} ({path})" for name, path in _detected_js_runtimes.items()
        )
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


# Panel thumbnails want a mid-resolution image: big enough to look
# sharp, small enough to load fast. yt-dlp entries usually carry a
# whole ladder of widths, and 400px sits in the ~320-480px sweet spot.
THUMBNAIL_TARGET_WIDTH = 400


def _thumbnail_candidates(video: dict[str, Any]) -> list[tuple[Any, str]]:
    """Extract (width, url) pairs from the yt-dlp thumbnails list."""
    thumbs = video.get("thumbnails")
    if not isinstance(thumbs, list):
        return []
    return [
        (thumb.get("width"), thumb["url"])
        for thumb in thumbs
        if isinstance(thumb, dict)
        and isinstance(thumb.get("url"), str)
        and thumb["url"]
    ]


def pick_thumbnail(video: dict[str, Any]) -> str:
    """Pick a reasonable mid-resolution thumbnail URL from a yt-dlp dict.

    Prefers a candidate 320-480px wide (closest to 400px); otherwise the
    closest sized candidate, then the middle entry when no widths are
    known, then the top-level ``thumbnail`` key, then an empty string.
    """
    candidates = _thumbnail_candidates(video)
    if not candidates:
        top_level = video.get("thumbnail")
        return top_level if isinstance(top_level, str) else ""
    sized = [
        candidate
        for candidate in candidates
        if isinstance(candidate[0], int | float)
    ]
    if sized:
        return min(sized, key=lambda c: abs(c[0] - THUMBNAIL_TARGET_WIDTH))[1]
    return candidates[len(candidates) // 2][1]


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
        return [cls(dict(video))]

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
    def thumbnail(self) -> str:
        """Mid-resolution thumbnail URL, or an empty string when none."""
        return pick_thumbnail(self._video)

    @property
    def uploader(self) -> str:
        return cast(
            str,
            self._video.get(
                "uploader",
                self._video.get("channel", self._video.get("creator", "")),
            ),
        )
