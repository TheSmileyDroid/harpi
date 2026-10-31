from __future__ import annotations

import os
import threading
import time
from pathlib import Path

BACKUP_KEEP = 20
BACKUP_SUFFIX = ".md"

_WRITE_LOCK = threading.RLock()


def write_lock() -> threading.RLock:
    return _WRITE_LOCK


def atomic_write(path: Path, text: str) -> None:
    with _WRITE_LOCK:
        _replace(path, text.encode("utf-8"))


def _replace(path: Path, data: bytes) -> None:
    temp = path.with_name(f".harpi-tmp-{os.getpid()}")
    try:
        with temp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temp.chmod(_mode(path))
        temp.replace(path)
        fsync_directory(path.parent)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _mode(path: Path) -> int:
    try:
        return path.stat().st_mode & 0o777
    except OSError:
        return 0o644


def backup_text(directory: Path, text: str, rev: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{rev}-{time.time_ns()}{BACKUP_SUFFIX}"
    with target.open("wb") as handle:
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    prune_backups(directory)
    fsync_directory(directory)
    return target


def fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def prune_backups(directory: Path, keep: int = BACKUP_KEEP) -> None:
    entries = sorted(
        directory.glob(f"*{BACKUP_SUFFIX}"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )
    stale = entries if keep <= 0 else entries[:-keep]
    for path in stale:
        path.unlink(missing_ok=True)
