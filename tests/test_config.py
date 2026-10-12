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


def test_js_runtime_dirs_come_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("HARPI_JS_RUNTIME_DIRS", "/opt/deno:/opt/bun")

    assert Settings.from_env().js_runtime_dirs == "/opt/deno:/opt/bun"


def test_ytdl_debug_flag_defaults_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HARPI_YTDL_DEBUG", raising=False)

    assert Settings.from_env().ytdl_debug is False


def test_ytdl_debug_flag_reads_the_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("HARPI_YTDL_DEBUG", "1")

    assert Settings.from_env().ytdl_debug is True
