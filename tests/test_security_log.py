"""The security log names audited events with user, address and UTC time."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from loguru import logger

from app import app as quart_app
from src import security_log
from src.security_log import event_for_request, record_event, record_line

AT = datetime(2026, 10, 26, 12, 0, 0, tzinfo=UTC)
CALLBACK = "/api/auth/discord/callback"


@pytest.mark.parametrize(
    ("method", "path", "status", "location", "expected"),
    [
        ("GET", CALLBACK, 302, "/", "login"),
        ("GET", CALLBACK, 302, "/?auth=denied", "login_failure"),
        ("GET", CALLBACK, 302, "/?auth=failed", "login_failure"),
        ("GET", CALLBACK, 302, "/?auth=cancelled", "login_failure"),
        ("GET", CALLBACK, 302, None, "login"),
        ("POST", "/api/logout", 200, None, "logout"),
        ("POST", "/api/selection", 200, None, "selection"),
        ("GET", "/api/status", 401, None, "access_denied"),
        ("POST", "/api/queue", 403, None, "access_denied"),
        ("GET", "/api/status", 500, None, "server_error"),
        ("GET", "/api/status", 200, None, None),
        ("POST", "/api/selection", 404, None, None),
        ("GET", "/", 200, None, None),
    ],
)
def test_event_for_request_classifies_the_audited_request(
    method: str,
    path: str,
    status: int,
    location: str | None,
    expected: str | None,
):
    assert event_for_request(method, path, status, location) == expected


def test_the_classifier_names_routes_the_app_serves():
    rules = {rule.rule for rule in quart_app.url_map.iter_rules()}

    assert security_log.CALLBACK_PATH in rules
    assert security_log.LOGOUT_PATH in rules
    assert security_log.SELECTION_PATH in rules


def test_record_line_carries_the_actor_the_address_and_utc_time():
    line = record_line("login", user_id="555", ip="203.0.113.9", at=AT)

    assert line == (
        "security event=login user=555 ip=203.0.113.9 at=2026-10-26T12:00:00Z"
    )


def test_record_line_marks_an_unknown_actor_and_address():
    line = record_line("access_denied", at=AT)

    assert line == (
        "security event=access_denied user=- ip=- at=2026-10-26T12:00:00Z"
    )


def test_record_event_writes_exactly_one_line():
    lines: list[str] = []
    handler = logger.add(lines.append, format="{message}", level="INFO")
    try:
        record_event("logout", user_id="555", ip="203.0.113.9", at=AT)
    finally:
        logger.remove(handler)

    assert [str(line).rstrip("\n") for line in lines] == [
        record_line("logout", user_id="555", ip="203.0.113.9", at=AT)
    ]


async def test_an_unauthenticated_api_call_is_an_access_denial():
    lines: list[str] = []
    handler = logger.add(lines.append, level="INFO")
    try:
        response = await quart_app.test_client().get("/api/status")
    finally:
        logger.remove(handler)

    assert response.status_code == 401
    assert "security event=access_denied" in "".join(lines)
