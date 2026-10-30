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


def test_discord_client_id_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "891732797054681119")

    assert Settings.from_env().discord_client_id == "891732797054681119"


def test_discord_redirect_uri_defaults_to_localhost(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DISCORD_REDIRECT_URI", raising=False)

    assert (
        Settings.from_env().discord_redirect_uri
        == "http://localhost:8000/api/auth/discord/callback"
    )


def test_discord_redirect_uri_honors_the_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(
        "DISCORD_REDIRECT_URI",
        "https://panel.example/api/auth/discord/callback",
    )

    assert (
        Settings.from_env().discord_redirect_uri
        == "https://panel.example/api/auth/discord/callback"
    )


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


def test_guild_allowlist_reads_snowflakes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "PANEL_GUILD_ALLOWLIST",
        "734174030701264906, 896066642948259960",
    )

    assert Settings.from_env().guild_allowlist == frozenset({
        734174030701264906,
        896066642948259960,
    })


@pytest.mark.parametrize("value", ["", "   ", "not-a-snowflake", "1,abc"])
def test_guild_allowlist_fails_closed(
    monkeypatch: pytest.MonkeyPatch, value: str
):
    monkeypatch.setenv("PANEL_GUILD_ALLOWLIST", value)

    assert Settings.from_env().guild_allowlist == frozenset()


def test_public_mode_defaults_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PANEL_PUBLIC_MODE", raising=False)

    assert Settings.from_env().public_mode is False


def test_public_mode_reads_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PANEL_PUBLIC_MODE", "1")

    assert Settings.from_env().public_mode is True


def test_trusted_hosts_default_to_the_public_host(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("PANEL_TRUSTED_HOSTS", raising=False)

    assert Settings.from_env().trusted_hosts == (
        "harpi.smileydroid.com.br",
        "localhost",
        "127.0.0.1",
    )


def test_trusted_hosts_read_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PANEL_TRUSTED_HOSTS", "panel.example, localhost")

    assert Settings.from_env().trusted_hosts == ("panel.example", "localhost")


def test_work_directory_defaults_under_data(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HARPI_WORK_DIR", raising=False)

    assert Settings.from_env().work_dir == "data/work"


def test_vault_path_defaults_to_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HARPI_VAULT_PATH", raising=False)

    assert Settings.from_env().vault_path is None


def test_vault_path_reads_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARPI_VAULT_PATH", "/vault")

    assert Settings.from_env().vault_path == "/vault"


def test_blank_vault_path_is_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARPI_VAULT_PATH", "")

    assert Settings.from_env().vault_path is None


def test_retention_days_read_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PANEL_RETENTION_DAYS", "7")

    assert Settings.from_env().retention_days == 7
