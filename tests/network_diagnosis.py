"""Structured diagnosis blocks for failed real-network playback tests.

Lives in the test layer on purpose: when a network test fails, this
module renders the failure as a report — failed layer, verbatim error,
library versions, and (for known upstream breakage patterns) a link to
the matching yt-dlp GitHub issue. It never mitigates, never touches
production, and never lets a signed stream URL into the output.
"""

from __future__ import annotations

import re

from src.harpi_lib.music.stream_probe import (
    _redact_signed_tokens,
    ProbeEnvironmentError,
    ProbeError,
    ProbeSilenceError,
    ProbeTimeoutError,
)
from tests.network_harness import (
    ffmpeg_version,
    redact_url,
    yt_dlp_ejs_version,
    yt_dlp_version,
)

EXTRACTION = "extraction"
STREAM = "stream"
SILENCE = "silence"

# Known upstream breakage patterns: regex on error text mapped to a real
# yt-dlp GitHub issue. URLs are wiki/issue pages, never signed stream
# URLs, so they are safe as-is; error text goes through redaction.
KNOWN_UPSTREAM_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"Sign in to confirm", re.IGNORECASE),
        "https://github.com/yt-dlp/yt-dlp/issues/15800",
        "YouTube bot check rejecting extraction",
    ),
    (
        re.compile(
            r"nsig extraction failed|n challenge solving failed",
            re.IGNORECASE,
        ),
        "https://github.com/yt-dlp/yt-dlp/issues/14458",
        "nsig challenge failure throttling/breaking streams",
    ),
    (
        re.compile(r"HTTP Error 403|403 Forbidden", re.IGNORECASE),
        "https://github.com/yt-dlp/yt-dlp/issues/17456",
        "googlevideo 403 rejecting the stream URL",
    ),
)

_URL_IN_TEXT = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def _redact_error_text(text: str) -> str:
    """Render every URL inside *text* safe for test output."""
    return _URL_IN_TEXT.sub(lambda m: redact_url(m.group(0)), text)


def _yt_dlp_error_classes() -> tuple[type[BaseException], ...]:
    import yt_dlp.utils

    return (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError)


def _is_yt_dlp_error(exc: BaseException) -> bool:
    try:
        return isinstance(exc, _yt_dlp_error_classes())
    except Exception:  # pragma: no cover - yt_dlp always importable here
        return "yt_dlp" in type(exc).__module__


def classify_layer(exc: BaseException) -> str:
    """Map *exc* onto the playback layer that failed.

    ProbeSilenceError -> silence; other probe errors (ProbeTimeoutError,
    ProbeEnvironmentError, plain "stream not playable" ValueError) ->
    stream; yt-dlp errors -> extraction. Anything else is reported as
    stream by default, flagged uncertain by :func:`build_diagnosis`.
    """
    if isinstance(exc, ProbeSilenceError):
        return SILENCE
    if isinstance(exc, ProbeError):
        # ProbeTimeoutError, ProbeEnvironmentError, and any other probe
        # failure that is not silence are stream-layer failures.
        return STREAM
    if _is_yt_dlp_error(exc):
        return EXTRACTION
    if isinstance(exc, ValueError):
        # ProbeError subclasses ValueError; a bare ValueError that is not
        # a yt-dlp error is most plausibly the probe's "stream not
        # playable", so stream is the honest default.
        return STREAM
    return STREAM


def match_upstream_issue(error_text: str) -> str | None:
    """Return the GitHub-issue reference for a known upstream pattern."""
    for pattern, url, _what in KNOWN_UPSTREAM_PATTERNS:
        if pattern.search(error_text):
            return url
    return None


def build_diagnosis(
    exc: BaseException,
    *,
    video: str | None = None,
    play: int | None = None,
) -> str:
    """Render the structured diagnosis block for a failed network test.

    Includes the failed layer, the verbatim (redacted) error, library
    versions, and — when the error matches a known upstream breakage
    pattern — the matching yt-dlp GitHub issue. Never includes cookies
    or signed URL parameters: every URL is passed through
    :func:`tests.network_harness.redact_url`.
    """
    error_text = str(exc) or repr(exc)
    layer = classify_layer(exc)
    lines = [
        "=" * 72,
        "NETWORK TEST FAILURE DIAGNOSIS",
        "=" * 72,
        f"Failed layer : {layer}",
    ]
    if layer in (STREAM, SILENCE) and not isinstance(
        exc, (ProbeSilenceError, ProbeTimeoutError, ProbeEnvironmentError)
    ):
        lines.append(
            f"               (classified as {layer} by default; "
            "classification uncertain for this exception type)"
        )
    if video is not None:
        lines.append(f"Video        : {video}")
    if play is not None:
        lines.append(f"Play number  : {play}")
    lines.extend([
        "",
        "Verbatim error:",
        f"  {_redact_error_text(_redact_signed_tokens(error_text))}",
        "",
        "Library versions:",
        f"  yt-dlp    : {yt_dlp_version()}",
        f"  yt-dlp-ejs: {yt_dlp_ejs_version()}",
        f"  ffmpeg    : {ffmpeg_version()}",
        "",
    ])
    issue = match_upstream_issue(error_text)
    if issue is not None:
        lines.append(f"Known upstream breakage: {issue}")
    else:
        lines.append(
            "No upstream match found: this error text does not match a "
            "known yt-dlp breakage pattern. Check yt-dlp's issue tracker "
            "manually before assuming our code is at fault."
        )
    lines.append("=" * 72)
    return "\n".join(lines)
