"""Shared parsing helpers for user-facing inputs."""

from __future__ import annotations

import math


def parse_finite_float(raw: str | None = "") -> float | None:
    """Parse *raw* into a finite float, or return ``None``.

    ``None``, empty strings, and non-numeric text return ``None``.
    NaN and infinity also return ``None`` because they are not finite.
    """
    try:
        value = float(raw or "")
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) else None
