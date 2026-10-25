"""Cookie file ownership: yt-dlp never writes the master cookie.

The master ``cookies.txt`` is read-only input. Each process hands yt-dlp a
working copy under the writable work directory so a yt-dlp session refresh
can never mutate the master. When the working copy does change, it is saved
as a timestamped backup instead, so an edited cookie is recoverable rather
than lost.
"""

from __future__ import annotations

import atexit
import hashlib
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from src.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[3]
MASTER_COOKIE = REPO_ROOT / "cookies.txt"
WORK_COOKIE_NAME = "cookies.work.txt"
BACKUP_DIR_NAME = "cookie-backups"
WORK_COOKIE_MODE = 0o600


@dataclass(frozen=True, slots=True)
class CookiePaths:
    master: Path
    work: Path
    backups: Path


def cookie_paths(work_dir: Path | str | None = None) -> CookiePaths:
    """Return the master, working copy, and backup paths.

    *work_dir* defaults to ``Settings.work_dir``, the one writable directory
    the runtime image mounts.
    """
    root = Path(Settings.from_env().work_dir if work_dir is None else work_dir)
    return CookiePaths(
        master=MASTER_COOKIE,
        work=root / WORK_COOKIE_NAME,
        backups=root / BACKUP_DIR_NAME,
    )


def sha256(path: Path) -> str:
    """Return the hex sha256 of *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_cookie_file(paths: CookiePaths | None = None) -> Path | None:
    """Copy the master cookie to a working file and return its path.

    Returns None when no master cookie exists, so yt-dlp runs without
    cookies instead of erroring on a missing file.
    """
    resolved = paths or cookie_paths()
    if not resolved.master.is_file():
        logger.warning(f"no master cookie at {resolved.master}")
        return None
    try:
        resolved.work.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(resolved.master, resolved.work)
        resolved.work.chmod(WORK_COOKIE_MODE)
    except OSError as exc:
        logger.error(f"could not prepare cookie working copy: {exc}")
        return None
    logger.info(f"cookie master sha256={sha256(resolved.master)}")
    return resolved.work


def save_cookie_version(paths: CookiePaths | None = None) -> None:
    """Save the working copy as a versioned backup when yt-dlp changed it."""
    resolved = paths or cookie_paths()
    if not (resolved.work.is_file() and resolved.master.is_file()):
        return
    if sha256(resolved.work) == sha256(resolved.master):
        return
    try:
        resolved.backups.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = resolved.backups / f"cookies.{stamp}.txt"
        shutil.copyfile(resolved.work, target)
        logger.info(
            "yt-dlp rewrote session cookies; saved version "
            f"{target.name} (master untouched)"
        )
    except OSError as exc:
        logger.error(f"could not save cookie version: {exc}")


atexit.register(save_cookie_version)
