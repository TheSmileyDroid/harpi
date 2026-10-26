"""Pure builder for the yt-dlp options the music source runs with."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import Settings

PUBLIC_EXTRACTORS: tuple[str, ...] = (
    "youtube",
    "youtube:tab",
    "youtube:search",
)
PUBLIC_PLAYLIST_LIMIT = 1
PUBLIC_PLAYLIST_ITEMS = str(PUBLIC_PLAYLIST_LIMIT)


def build_ytdl_options(
    settings: Settings,
    *,
    cookiefile: str | None = None,
    js_runtimes: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the options shared by the search and extraction clients."""
    work_dir = Path(settings.work_dir)
    options: dict[str, Any] = {
        "format": "m4a/bestaudio/best",
        "outtmpl": str(
            work_dir / "audios" / "%(extractor)s-%(id)s-%(title)s.%(ext)s"
        ),
        "cachedir": str(work_dir / "yt-dlp-cache"),
        "restrictfilenames": True,
        "noplaylist": False,
        "extract_flat": True,
        "verbose": settings.ytdl_debug,
        "quiet": not settings.ytdl_debug,
        "no_warnings": not settings.ytdl_debug,
        "default_search": "auto_warning",
        "socket_timeout": 15,
        "retries": 1,
        "fragment_retries": 1,
        "extractor_retries": 1,
    }
    if cookiefile is not None:
        options["cookiefile"] = cookiefile
    if js_runtimes:
        options["js_runtimes"] = js_runtimes
    if settings.public_mode:
        options["allowed_extractors"] = list(PUBLIC_EXTRACTORS)
        options["playlist_items"] = PUBLIC_PLAYLIST_ITEMS
    return options
