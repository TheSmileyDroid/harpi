"""Secret scrubbing for every line that reaches a log sink.

The pure function is :func:`redact`. The loguru patcher is
:func:`redact_record`; it runs once per record, before any sink formats it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loguru import Record

REDACTED = "[REDACTED]"

_SENSITIVE_PARAM_NAMES = (
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "api_key",
    "apikey",
    "key",
    "secret",
    "password",
    "passwd",
    "signature",
    "sig",
    "auth",
    "authorization",
    "cookie",
    "session",
    "code",
)

_SENSITIVE_PARAMS = re.compile(
    r"(?i)(?<![\w-])(?P<name>"
    + "|".join(_SENSITIVE_PARAM_NAMES)
    + r")=(?P<value>[^&\s\"'<>]+)"
)

_SENSITIVE_HEADERS = re.compile(
    r"(?i)(?<![\w-])(?P<name>"
    r"set-cookie|cookie|proxy-authorization|authorization|x-api-key"
    r")(?P<separator>\s*[:=]\s*)(?P<value>[^\r\n]+)"
)

_SENSITIVE_ASSIGNMENTS = re.compile(
    r"(?i)(?<![\w-])(?P<name>"
    r"access_token|refresh_token|id_token|token|api_key|apikey|"
    r"secret|password|passwd"
    r")(?P<separator>\s*:\s*)(?P<value>[^\r\n]+)"
)

_URL_CREDENTIALS = re.compile(
    r"(?i)(?P<scheme>[a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@"
)

_WEBHOOK_URL = re.compile(
    r"(?i)(?P<prefix>https?://(?:discord|discordapp)\.com"
    r"/api/webhooks/\d+)/[A-Za-z0-9._-]+"
)

_AUTH_SCHEME = re.compile(
    r"(?i)(?P<scheme>bearer)\s+(?P<value>[A-Za-z0-9._~+/=-]{8,})"
)


def redact(text: str) -> str:
    """Replace secret values in *text*, keeping the surrounding structure."""
    scrubbed = _SENSITIVE_HEADERS.sub(
        lambda match: f"{match['name']}{match['separator']}{REDACTED}",
        text,
    )
    scrubbed = _SENSITIVE_ASSIGNMENTS.sub(
        lambda match: f"{match['name']}{match['separator']}{REDACTED}",
        scrubbed,
    )
    scrubbed = _URL_CREDENTIALS.sub(
        lambda match: f"{match['scheme']}{REDACTED}@", scrubbed
    )
    scrubbed = _WEBHOOK_URL.sub(
        lambda match: f"{match['prefix']}/{REDACTED}", scrubbed
    )
    scrubbed = _AUTH_SCHEME.sub(
        lambda match: f"{match['scheme']} {REDACTED}", scrubbed
    )
    return _SENSITIVE_PARAMS.sub(
        lambda match: f"{match['name']}={REDACTED}", scrubbed
    )


def redact_record(record: Record) -> None:
    """Loguru patcher: scrub the message and every string extra value."""
    record["message"] = redact(str(record["message"]))
    for key, value in list(record["extra"].items()):
        if isinstance(value, str):
            record["extra"][key] = redact(value)
