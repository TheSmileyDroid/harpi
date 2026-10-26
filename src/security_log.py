"""One-line security records an operator can audit.

The record names the event, the Discord user, the client address and the
UTC instant. Request bodies never reach it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from loguru import logger

SecurityEvent = Literal[
    "login",
    "login_failure",
    "logout",
    "access_denied",
    "selection",
    "server_error",
]

SECURITY_BINDING = "security"
CALLBACK_PATH = "/api/auth/discord/callback"
LOGOUT_PATH = "/api/logout"
SELECTION_PATH = "/api/selection"
FAILED_LOGIN_MARKER = "?auth="
DENIED_STATUSES = frozenset({401, 403})
SERVER_ERROR_STATUS = 500
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
UNKNOWN = "-"


def event_for_request(
    method: str, path: str, status: int, location: str | None
) -> SecurityEvent | None:
    """The security event a finished request represents, if any."""
    if status >= SERVER_ERROR_STATUS:
        return "server_error"
    if status in DENIED_STATUSES:
        return "access_denied"
    if method == "GET" and path == CALLBACK_PATH:
        failed = location is not None and FAILED_LOGIN_MARKER in location
        return "login_failure" if failed else "login"
    if method == "POST" and path == LOGOUT_PATH:
        return "logout"
    if method == "POST" and path == SELECTION_PATH and status < 400:
        return "selection"
    return None


def record_line(
    event: SecurityEvent,
    *,
    user_id: str | None = None,
    ip: str | None = None,
    at: datetime | None = None,
) -> str:
    moment = datetime.now(UTC) if at is None else at.astimezone(UTC)
    return (
        f"security event={event} "
        f"user={user_id or UNKNOWN} "
        f"ip={ip or UNKNOWN} "
        f"at={moment.strftime(TIMESTAMP_FORMAT)}"
    )


def record_event(
    event: SecurityEvent,
    *,
    user_id: str | None = None,
    ip: str | None = None,
    at: datetime | None = None,
) -> None:
    logger.bind(**{SECURITY_BINDING: True}).info(
        record_line(event, user_id=user_id, ip=ip, at=at)
    )
