"""Both entry points install the same rotated, redacted file sink."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from loguru import logger

from src.config import Settings
from src.logging_setup import configure_logging, log_level
from src.security_log import record_event


@pytest.fixture(autouse=True)
def restore_logging():
    yield
    configure_logging(Settings.from_env())


def _settings(log_dir: Path, **changes) -> Settings:
    return replace(
        Settings.from_env(),
        log_path=str(log_dir / "harpi.log"),
        **changes,
    )


def test_production_logs_at_info(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARPI_LOG_LEVEL", "INFO")
    monkeypatch.delenv("HARPI_YTDL_DEBUG", raising=False)

    assert log_level(Settings.from_env()) == "INFO"


def test_the_debug_flag_raises_the_level(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARPI_YTDL_DEBUG", "1")

    assert log_level(Settings.from_env()) == "DEBUG"


def test_the_file_sink_writes_under_the_configured_path(tmp_path):
    configure_logging(_settings(tmp_path / "logs"))

    logger.info("panel storage ready")
    logger.complete()

    assert (tmp_path / "logs" / "harpi.log").exists()


def test_the_file_sink_rotates_by_size_and_keeps_a_bounded_count(tmp_path):
    configure_logging(_settings(tmp_path), rotation=400, retention=2)

    for _ in range(30):
        logger.info("x" * 100)
    logger.complete()

    files = list(tmp_path.glob("harpi*.log"))
    assert 1 < len(files) <= 3


def test_security_records_get_their_own_file(tmp_path):
    configure_logging(_settings(tmp_path))

    record_event("login", user_id="555", ip="203.0.113.9")
    logger.info("a normal line")
    logger.complete()

    security = (tmp_path / "security.log").read_text()
    assert "security event=login user=555 ip=203.0.113.9" in security
    assert "a normal line" not in security
