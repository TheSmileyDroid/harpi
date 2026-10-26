"""Secrets are scrubbed before any log sink formats a line."""

from __future__ import annotations

import pytest
from loguru import logger

from src.logging_setup import redacted_format
from src.redaction import REDACTED, redact, redact_record


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ),
        (
            "https://example.com/watch?token=abc123&v=xyz",
            "https://example.com/watch?token=[REDACTED]&v=xyz",
        ),
        (
            "https://user:hunter2@example.com/path",
            "https://[REDACTED]@example.com/path",
        ),
        (
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig",
            "Authorization: [REDACTED]",
        ),
        ("authorization=Bearer abcdefghijklmnop", "authorization=[REDACTED]"),
        ("Cookie: sessionid=abc; theme=dark", "Cookie: [REDACTED]"),
        ("Set-Cookie: __Host-harpi=abc123; Path=/", "Set-Cookie: [REDACTED]"),
        (
            "https://discord.com/api/webhooks/123/abcdefghijklmnop",
            "https://discord.com/api/webhooks/123/[REDACTED]",
        ),
        (
            "https://discordapp.com/api/webhooks/42/xyz-TOKEN_here",
            "https://discordapp.com/api/webhooks/42/[REDACTED]",
        ),
        ("api_key=supersecret value=kept", "api_key=[REDACTED] value=kept"),
        ("token: abc123def", "token: [REDACTED]"),
        ("X-Api-Key: abc123def456", "X-Api-Key: [REDACTED]"),
        ("Bearer eyJhbGciOiJIUzI1NiJ9", "Bearer [REDACTED]"),
        (
            "access_token=xyz&refresh_token=abc",
            "access_token=[REDACTED]&refresh_token=[REDACTED]",
        ),
        ("?code=oauthcode&state=nonce", "?code=[REDACTED]&state=nonce"),
        ("monkey=business", "monkey=business"),
        (
            "Discord bot initialization started",
            "Discord bot initialization started",
        ),
        ("a plain line with no secret", "a plain line with no secret"),
    ],
)
def test_redact_replaces_the_value_and_keeps_the_shape(
    text: str, expected: str
):
    assert redact(text) == expected


def test_redact_is_idempotent():
    once = redact("https://example.com/?token=abc&Cookie: a=b")

    assert redact(once) == once


def test_a_logged_message_reaches_the_sink_redacted():
    lines: list[str] = []
    handler = logger.add(lines.append, format=redacted_format, level="INFO")
    logger.configure(patcher=redact_record)
    try:
        logger.info("searching {url}", url="https://x.test/?token=abc123")
    finally:
        logger.remove(handler)

    rendered = "".join(lines)
    assert "abc123" not in rendered
    assert REDACTED in rendered


def test_a_logged_traceback_reaches_the_sink_redacted():
    lines: list[str] = []
    handler = logger.add(lines.append, format=redacted_format, level="ERROR")
    logger.configure(patcher=redact_record)
    try:
        try:
            raise RuntimeError("Cookie: sessionid=abc123")
        except RuntimeError:
            logger.exception("the search failed")
    finally:
        logger.remove(handler)

    rendered = "".join(lines)
    assert "abc123" not in rendered
    assert REDACTED in rendered
