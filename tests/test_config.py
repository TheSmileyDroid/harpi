"""Tests for the Settings environment reads."""

from __future__ import annotations

import pytest

from src.config import Settings


def test_host_defaults_to_localhost(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HOST", raising=False)

    assert Settings.from_env().host == "127.0.0.1"


def test_host_honors_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOST", "0.0.0.0")

    assert Settings.from_env().host == "0.0.0.0"


def test_panel_token_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("PANEL_TOKEN", "panel-secret")

    assert Settings.from_env().panel_token == "panel-secret"
