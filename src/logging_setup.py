"""Loguru sinks shared by ``python -m src`` and the ASGI app."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.config import Settings
from src.redaction import redact, redact_record
from src.security_log import SECURITY_BINDING

if TYPE_CHECKING:
    from loguru import FilterFunction, Record

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} - {message}\n"
)
LOG_ROTATION = "10 MB"
LOG_RETENTION = 5
SECURITY_LOG_NAME = "security.log"
EXCEPTION_FIELD = "redacted_exception"


def log_level(settings: Settings) -> str:
    """DEBUG only when diagnostics are asked for, otherwise the setting."""
    return "DEBUG" if settings.ytdl_debug else settings.log_level


def redacted_format(record: Record) -> str:
    """Format template that carries a scrubbed traceback, not the raw one."""
    exception = record["exception"]
    if exception is None or exception.type is None:
        return LOG_FORMAT
    record["extra"][EXCEPTION_FIELD] = redact(
        "".join(
            traceback.format_exception(
                exception.type, exception.value, exception.traceback
            )
        )
    )
    return f"{LOG_FORMAT}{{extra[{EXCEPTION_FIELD}]}}"


def is_security_record(record: Record) -> bool:
    return record["extra"].get(SECURITY_BINDING) is True


def security_log_path(log_path: Path) -> Path:
    return log_path.with_name(SECURITY_LOG_NAME)


def configure_logging(
    settings: Settings,
    *,
    rotation: str | int = LOG_ROTATION,
    retention: int = LOG_RETENTION,
) -> None:
    level = log_level(settings)
    logger.remove()
    logger.configure(patcher=redact_record)
    logger.add(
        sys.stdout,
        level=level,
        format=redacted_format,
        backtrace=False,
        diagnose=False,
    )
    log_path = Path(settings.log_path)
    _add_file_sink(log_path, level, rotation, retention)
    _add_file_sink(
        security_log_path(log_path),
        level,
        rotation,
        retention,
        record_filter=is_security_record,
    )


def _add_file_sink(
    path: Path,
    level: str,
    rotation: str | int,
    retention: int,
    *,
    record_filter: FilterFunction | None = None,
) -> None:
    logger.add(
        path,
        level=level,
        format=redacted_format,
        filter=record_filter,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        delay=True,
        backtrace=False,
        diagnose=False,
    )
