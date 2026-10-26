from __future__ import annotations

import time
from datetime import timedelta

SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60
SESSION_LIFETIME = timedelta(seconds=SESSION_LIFETIME_SECONDS)

STRICT_COOKIE_NAME = "__Host-harpi"
LOCAL_COOKIE_NAME = "harpi"

ISSUED_AT_KEY = "issued_at"
LOGIN_EPOCH_KEY = "login_epoch"


def cookie_name(*, secure: bool) -> str:
    return STRICT_COOKIE_NAME if secure else LOCAL_COOKIE_NAME


def now() -> int:
    return int(time.time())


def within_lifetime(issued_at: object, *, at: int | None = None) -> bool:
    if not isinstance(issued_at, int) or isinstance(issued_at, bool):
        return False
    age = (now() if at is None else at) - issued_at
    return age <= SESSION_LIFETIME_SECONDS
