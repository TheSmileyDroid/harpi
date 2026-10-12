"""Cookie ownership: the master is never written; edits are versioned."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.harpi_lib.music import cookie_store


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    master = tmp_path / "cookies.txt"
    master.write_text("master\n")
    work_dir = tmp_path / "work"
    monkeypatch.setattr(cookie_store, "MASTER_COOKIE", master)
    monkeypatch.setattr(cookie_store, "WORK_DIR", work_dir)
    monkeypatch.setattr(
        cookie_store, "WORK_COOKIE", work_dir / "cookies.work.txt"
    )
    monkeypatch.setattr(
        cookie_store, "BACKUP_DIR", work_dir / "cookie-backups"
    )
    return master


def test_prepare_copies_master_and_leaves_it(store: Path):
    work = cookie_store.prepare_cookie_file()

    assert work == cookie_store.WORK_COOKIE
    assert work is not None
    assert work.read_text() == "master\n"
    assert store.read_text() == "master\n"


def test_prepare_returns_none_without_master(store: Path):
    store.unlink()

    assert cookie_store.prepare_cookie_file() is None


def test_save_keeps_a_version_when_work_differs(store: Path):
    cookie_store.prepare_cookie_file()
    cookie_store.WORK_COOKIE.write_text("edited\n")

    cookie_store.save_cookie_version()

    backups = list(cookie_store.BACKUP_DIR.glob("cookies.*.txt"))
    assert len(backups) == 1
    assert backups[0].read_text() == "edited\n"
    assert store.read_text() == "master\n"


def test_save_writes_nothing_when_unchanged(store: Path):
    cookie_store.prepare_cookie_file()

    cookie_store.save_cookie_version()

    assert not cookie_store.BACKUP_DIR.exists()


def test_save_is_noop_without_a_working_copy(store: Path):
    cookie_store.save_cookie_version()

    assert not cookie_store.BACKUP_DIR.exists()


def test_sha256_matches_hashlib(store: Path):
    assert (
        cookie_store.sha256(store) == hashlib.sha256(b"master\n").hexdigest()
    )
