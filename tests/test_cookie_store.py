"""Cookie ownership: the master is never written; edits are versioned."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from src.harpi_lib.music import cookie_store


@pytest.fixture
def paths(tmp_path: Path) -> cookie_store.CookiePaths:
    master = tmp_path / "cookies.txt"
    master.write_text("master\n")
    return replace(cookie_store.cookie_paths(tmp_path / "work"), master=master)


def test_work_directory_comes_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("HARPI_WORK_DIR", str(tmp_path / "runtime"))

    assert cookie_store.cookie_paths().work.parent == tmp_path / "runtime"


def test_work_directory_defaults_under_data(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HARPI_WORK_DIR", raising=False)

    assert cookie_store.cookie_paths().work.parent == Path("data/work")


def test_prepare_copies_master_and_leaves_it(paths: cookie_store.CookiePaths):
    work = cookie_store.prepare_cookie_file(paths)

    assert work == paths.work
    assert work is not None
    assert work.read_text() == "master\n"
    assert paths.master.read_text() == "master\n"


def test_prepare_writes_under_the_work_directory(
    paths: cookie_store.CookiePaths,
):
    work = cookie_store.prepare_cookie_file(paths)

    assert work is not None
    assert work.parent == paths.work.parent
    assert work.parent.is_dir()


def test_prepare_copies_a_read_only_master_into_a_writable_copy(
    paths: cookie_store.CookiePaths,
):
    paths.master.chmod(0o444)

    work = cookie_store.prepare_cookie_file(paths)

    assert work is not None
    assert work.read_text() == "master\n"
    assert work.stat().st_mode & 0o200


def test_prepare_returns_none_without_master(paths: cookie_store.CookiePaths):
    paths.master.unlink()

    assert cookie_store.prepare_cookie_file(paths) is None


def test_master_is_never_written(paths: cookie_store.CookiePaths):
    cookie_store.prepare_cookie_file(paths)
    paths.work.write_text("edited\n")

    cookie_store.save_cookie_version(paths)

    assert paths.master.read_text() == "master\n"
    assert (
        cookie_store.sha256(paths.master)
        == hashlib.sha256(b"master\n").hexdigest()
    )


def test_save_keeps_a_version_when_work_differs(
    paths: cookie_store.CookiePaths,
):
    cookie_store.prepare_cookie_file(paths)
    paths.work.write_text("edited\n")

    cookie_store.save_cookie_version(paths)

    backups = list(paths.backups.glob("cookies.*.txt"))
    assert len(backups) == 1
    assert backups[0].read_text() == "edited\n"
    assert paths.master.read_text() == "master\n"


def test_save_writes_nothing_when_unchanged(paths: cookie_store.CookiePaths):
    cookie_store.prepare_cookie_file(paths)

    cookie_store.save_cookie_version(paths)

    assert not paths.backups.exists()


def test_save_is_noop_without_a_working_copy(paths: cookie_store.CookiePaths):
    cookie_store.save_cookie_version(paths)

    assert not paths.backups.exists()


def test_sha256_matches_hashlib(paths: cookie_store.CookiePaths):
    assert (
        cookie_store.sha256(paths.master)
        == hashlib.sha256(b"master\n").hexdigest()
    )
