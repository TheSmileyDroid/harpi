"""One-line security records an operator can audit.

The record names the event, the Discord user, the client address and the
UTC instant. Request bodies never reach it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from loguru import logger

from src.alerts import AlertKind

SecurityEvent = Literal[
    "login",
    "login_failure",
    "logout",
    "access_denied",
    "selection",
    "server_error",
]

ALERT_STATUS_KINDS: dict[int, AlertKind] = {
    401: "unauthorized",
    403: "forbidden",
    429: "rate_limited",
}

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
    return _event_for_success(method, path, status, location)


def _event_for_success(
    method: str, path: str, status: int, location: str | None
) -> SecurityEvent | None:
    if method == "GET":
        return _get_event(path, location)
    if method == "POST":
        return _post_event(path, status)
    return None


def _get_event(path: str, location: str | None) -> SecurityEvent | None:
    if path != CALLBACK_PATH:
        return None
    return "login_failure" if _login_failed(location) else "login"


def _post_event(path: str, status: int) -> SecurityEvent | None:
    if path == LOGOUT_PATH:
        return "logout"
    if path == SELECTION_PATH and status < 400:
        return "selection"
    return None


def _login_failed(location: str | None) -> bool:
    return location is not None and FAILED_LOGIN_MARKER in location


def alert_for_status(status: int) -> AlertKind | None:
    """The operator alert a response status deserves, if any."""
    if status >= SERVER_ERROR_STATUS:
        return "server_error"
    return ALERT_STATUS_KINDS.get(status)


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
