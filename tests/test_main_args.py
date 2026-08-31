"""Tests for the CLI argument parsing of ``python -m src``.

``parse_args`` is pure: CLI flags must override the Settings defaults,
and the Settings values must survive when no flag is given.
"""

from __future__ import annotations

import sys

import pytest

from src.__main__ import parse_args
from src.config import Settings


def _settings() -> Settings:
    return Settings(
        discord_token=None,
        prefix="-",
        host="0.0.0.0",
        port=8000,
        reload=False,
        secret_key=None,
    )


def test_parse_args_defaults_to_the_settings_values(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["src"])

    args = parse_args(_settings())

    assert args.host == "0.0.0.0"
    assert args.port == 8000
    assert args.reload is False


@pytest.mark.parametrize(
    ("argv", "expected_host", "expected_port", "expected_reload"),
    [
        (["src", "--host", "127.0.0.1"], "127.0.0.1", 8000, False),
        (["src", "--port", "9000"], "0.0.0.0", 9000, False),
        (["src", "--reload"], "0.0.0.0", 8000, True),
    ],
)
def test_parse_args_flags_override_the_settings(
    monkeypatch,
    argv: list[str],
    expected_host: str,
    expected_port: int,
    expected_reload: bool,
):
    monkeypatch.setattr(sys, "argv", argv)

    args = parse_args(_settings())

    assert args.host == expected_host
    assert args.port == expected_port
    assert args.reload is expected_reload


def test_parse_args_honors_the_settings_reload_default(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["src"])
    settings = Settings(
        discord_token=None,
        prefix="-",
        host="0.0.0.0",
        port=8000,
        reload=True,
        secret_key=None,
    )

    assert parse_args(settings).reload is True
