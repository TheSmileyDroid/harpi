"""Tests for the design review gate: the digest-staleness rules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.design_review_gate as gate


def _verdict(tmp_path: Path, digest: str, overall: str = "pass") -> Path:
    path = tmp_path / "verdict.json"
    path.write_text(
        json.dumps({"digest": digest, "overall": overall, "items": []})
    )
    return path


def test_passes_when_verdict_matches_digest(tmp_path: Path) -> None:
    path = _verdict(tmp_path, "abc123")
    assert gate.check(path, "abc123") is None


def test_fails_when_verdict_missing(tmp_path: Path) -> None:
    result = gate.check(tmp_path / "verdict.json", "abc123")
    assert result is not None and "design review required" in result


def test_fails_when_verdict_stale(tmp_path: Path) -> None:
    path = _verdict(tmp_path, "old-digest")
    result = gate.check(path, "abc123")
    assert result is not None and "stale" in result


def test_fails_when_review_found_failures(tmp_path: Path) -> None:
    path = _verdict(tmp_path, "abc123", overall="fail")
    result = gate.check(path, "abc123")
    assert result is not None and "fail" in result


def test_fails_on_malformed_verdict(tmp_path: Path) -> None:
    path = tmp_path / "verdict.json"
    path.write_text("{not json")
    result = gate.check(path, "abc123")
    assert result is not None and "unreadable" in result


def test_fails_on_incomplete_verdict(tmp_path: Path) -> None:
    path = tmp_path / "verdict.json"
    path.write_text(json.dumps({"digest": "abc123"}))
    result = gate.check(path, "abc123")
    assert result is not None


def test_digest_covers_single_file_bases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ui_digest must hash file bases directly: rglob on a file yields
    nothing, and a silent miss means skill/checklist changes never stale a
    verdict (the bug this test pins)."""
    import tools.design_review as dr

    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "x.html").write_text("<p>a</p>")
    skill = tmp_path / "SKILL.md"
    skill.write_text("v1")
    monkeypatch.setattr(dr, "REPO", tmp_path)
    monkeypatch.setattr(dr, "UI_DIRS", ("pages",))
    monkeypatch.setattr(dr, "UI_FILES", ("SKILL.md",))

    before = dr.ui_digest()
    skill.write_text("v2")
    assert dr.ui_digest() != before
