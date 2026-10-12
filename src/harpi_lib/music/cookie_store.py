"""Cookie file ownership: yt-dlp never writes the master cookie.

The master ``cookies.txt`` at the repo root is the source of truth. Each
process hands yt-dlp a working copy under ``.scratch/ytdl-debug/`` so a
yt-dlp session refresh can never mutate the master. When the working copy
does change, it is saved as a timestamped backup instead, so an edited
cookie is recoverable rather than lost.
"""

from __future__ import annotations

import atexit
import hashlib
import shutil
import time
from pathlib import Path

from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[3]
MASTER_COOKIE = REPO_ROOT / "cookies.txt"
WORK_DIR = REPO_ROOT / ".scratch" / "ytdl-debug"
WORK_COOKIE = WORK_DIR / "cookies.work.txt"
BACKUP_DIR = WORK_DIR / "cookie-backups"


def sha256(path: Path) -> str:
    """Return the hex sha256 of *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_cookie_file() -> Path | None:
    """Copy the master cookie to a working file and return its path.

    Returns None when no master cookie exists, so yt-dlp runs without
    cookies instead of erroring on a missing file.
    """
    if not MASTER_COOKIE.is_file():
        logger.warning(f"no master cookie at {MASTER_COOKIE}")
        return None
    try:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MASTER_COOKIE, WORK_COOKIE)
    except OSError as exc:
        logger.error(f"could not prepare cookie working copy: {exc}")
        return None
    logger.info(f"cookie master sha256={sha256(MASTER_COOKIE)}")
    return WORK_COOKIE


def save_cookie_version() -> None:
    """Save the working copy as a versioned backup when yt-dlp changed it."""
    if not (WORK_COOKIE.is_file() and MASTER_COOKIE.is_file()):
        return
    if sha256(WORK_COOKIE) == sha256(MASTER_COOKIE):
        return
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = BACKUP_DIR / f"cookies.{stamp}.txt"
        shutil.copy2(WORK_COOKIE, target)
        logger.info(
            "yt-dlp rewrote session cookies; saved version "
            f"{target.name} (master untouched)"
        )
    except OSError as exc:
        logger.error(f"could not save cookie version: {exc}")


atexit.register(save_cookie_version)
