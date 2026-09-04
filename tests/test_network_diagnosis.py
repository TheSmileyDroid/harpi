"""Offline unit tests for the network-test diagnosis block builder."""

from __future__ import annotations

import yt_dlp.utils

from src.harpi_lib.music.stream_probe import (
    ProbeEnvironmentError,
    ProbeSilenceError,
    ProbeTimeoutError,
)
from tests.network_diagnosis import (
    EXTRACTION,
    SILENCE,
    STREAM,
    build_diagnosis,
    classify_layer,
)

SIGNED_URL = (
    "https://rr5---sn-1.googlevideo.com/videoplayback"
    "?expire=1790000000&lsig=SECRET_LSIG&signature=TOP_SECRET&n=abc123"
)


def test_silence_failure_names_silence_layer() -> None:
    exc = ProbeSilenceError("stream is silent (max_volume=-91.2 dB)")
    block = build_diagnosis(exc, video="Imagine Dragons - Warriors")
    assert classify_layer(exc) == SILENCE
    assert f"Failed layer : {SILENCE}" in block


def test_timeout_failure_names_stream_layer() -> None:
    exc = ProbeTimeoutError("stream probe timed out")
    block = build_diagnosis(exc, video="Warriors", play=2)
    assert classify_layer(exc) == STREAM
    assert f"Failed layer : {STREAM}" in block
    assert "Play number  : 2" in block
    assert "Video        : Warriors" in block


def test_extraction_failure_names_extraction_layer() -> None:
    exc = yt_dlp.utils.DownloadError(
        "ERROR: [youtube] dQw4w9WgXcQ: Video unavailable"
    )
    assert classify_layer(exc) == EXTRACTION
    block = build_diagnosis(exc)
    assert f"Failed layer : {EXTRACTION}" in block
    assert "Video unavailable" in block


def test_unknown_pattern_reports_no_upstream_match() -> None:
    exc = yt_dlp.utils.DownloadError("ERROR: something never seen before")
    block = build_diagnosis(exc)
    assert "No upstream match found" in block
    assert "github.com/yt-dlp" not in block
    # Verbatim error still present.
    assert "something never seen before" in block


def test_known_pattern_includes_issue_url() -> None:
    exc = ProbeTimeoutError(
        "probe failed: HTTP Error 403: Forbidden from googlevideo"
    )
    block = build_diagnosis(exc)
    assert "https://github.com/yt-dlp/yt-dlp/issues/17456" in block
    assert "Known upstream breakage" in block


def test_block_contains_library_versions() -> None:
    block = build_diagnosis(ProbeSilenceError("silent"))
    assert "Library versions:" in block
    assert "yt-dlp    :" in block
    assert "yt-dlp-ejs:" in block
    assert "ffmpeg    :" in block


def test_block_never_leaks_signed_url_parameters() -> None:
    exc = yt_dlp.utils.DownloadError(
        f"ERROR: unable to download video data: {SIGNED_URL}"
    )
    block = build_diagnosis(exc)
    assert "SECRET_LSIG" not in block
    assert "TOP_SECRET" not in block
    # The URL itself is still (safely) referenced for triage.
    assert "googlevideo.com" in block


def test_unknown_exception_defaults_to_stream_with_uncertainty_note() -> None:
    class WeirdFailure(Exception):
        pass

    exc = WeirdFailure(" inexplicable")
    assert classify_layer(exc) == STREAM
    block = build_diagnosis(exc)
    assert "classification uncertain" in block


def test_environment_error_is_stream_not_silence() -> None:
    exc = ProbeEnvironmentError("ffmpeg not available for stream probing")
    assert classify_layer(exc) == STREAM
