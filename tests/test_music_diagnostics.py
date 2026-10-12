"""Diagnostics capture and early-stop detection for the YouTube chain."""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Any

import discord
import pytest

from src.harpi_lib.music import debug_capture, ytdl_source
from src.harpi_lib.music.debug_capture import StderrTail, redact_source
from src.harpi_lib.music.ffmpeg_source import FFmpegPCMAudio
from src.harpi_lib.music.ytdl_source import YoutubeDLSource


@pytest.fixture
def debug_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(debug_capture, "CAPTURE_ENABLED", True)
    monkeypatch.setattr(debug_capture, "DEBUG_DIR", tmp_path)
    monkeypatch.setattr(
        debug_capture, "DEBUG_FILE", tmp_path / "ytdl-debug.log"
    )
    monkeypatch.setattr(
        debug_capture, "ROTATED_FILE", tmp_path / "ytdl-debug.log.1"
    )
    return tmp_path


def test_record_appends_one_line(debug_dir: Path):
    debug_capture.record("track-stop", title="x", played="1.0")

    text = (debug_dir / "ytdl-debug.log").read_text()

    assert "track-stop" in text
    assert "title='x'" in text
    assert "played='1.0'" in text
    assert text.count("\n") == 1


def test_record_rotates_before_overwriting(
    debug_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(debug_capture, "MAX_BYTES", 10)
    log = debug_dir / "ytdl-debug.log"
    log.write_text("x" * 20)

    debug_capture.record("event")

    assert (debug_dir / "ytdl-debug.log.1").exists()
    assert "event" in log.read_text()


def test_stderr_tail_keeps_only_the_last_lines():
    tail = StderrTail(max_lines=2)
    tail.add("a\n")
    tail.add("b\n")
    tail.add("c\n")

    assert tail.tail() == "b\nc"


def test_redact_source_hides_query_and_marks_non_urls():
    assert (
        redact_source("https://x.googlevideo.com/videoplayback?lsig=secret")
        == "https://x.googlevideo.com/videoplayback"
    )
    assert redact_source("/tmp/tone.wav") == "<non-url>"
    assert redact_source(io.BytesIO()) == "<pipe>"


def test_ffmpegpcm_drains_stderr_stream_deterministically():
    source = FFmpegPCMAudio(source="https://stream.example.com/audio.m4a")

    source._drain_stderr(io.BytesIO(b"line1\nline2\n"))

    assert source.stderr_tail() == "line1\nline2"


def test_ffmpegpcm_pipes_stderr_by_default(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, Any] = {}

    class FakePopen:
        def __init__(self, args: list[str], **kwargs: Any) -> None:
            captured.update(kwargs)
            self.stdout = io.BytesIO(b"")
            self.stderr = io.BytesIO(b"")

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    monkeypatch.setattr(
        "src.harpi_lib.music.ffmpeg_source.subprocess.Popen", FakePopen
    )

    FFmpegPCMAudio(
        source="https://stream.example.com/audio.m4a"
    )._spawn_process()

    assert captured["stderr"] is subprocess.PIPE


class FakeOriginal(discord.AudioSource):
    def __init__(self, stderr_text: str) -> None:
        self._stderr_text = stderr_text

    def read(self) -> bytes:
        return b""

    def stderr_tail(self) -> str:
        return self._stderr_text

    def cleanup(self) -> None:
        return None


def _build_source(duration: int, stderr_text: str) -> YoutubeDLSource:
    return YoutubeDLSource(
        FakeOriginal(stderr_text),
        data={"title": "t", "duration": duration, "url": "u"},
        volume=0.5,
    )


def test_read_reports_early_stop_with_stderr(
    debug_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    recorded: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        debug_capture,
        "record",
        lambda event, **fields: recorded.append((event, fields)),
    )

    source = _build_source(
        duration=200, stderr_text="HTTP error 403 Forbidden"
    )

    assert source.read() == b""

    events = [event for event, _ in recorded]
    stop = next(fields for event, fields in recorded if event == "track-stop")
    assert events == ["track-stop", "ffmpeg-stderr"]
    assert stop["early"] is True


def test_read_reports_stop_once(
    debug_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    events: list[str] = []
    monkeypatch.setattr(
        debug_capture, "record", lambda event, **fields: events.append(event)
    )

    source = _build_source(duration=200, stderr_text="")
    source.read()
    source.read()

    assert events.count("track-stop") == 1
    assert "ffmpeg-stderr" not in events


def test_read_full_track_is_not_early(
    debug_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    recorded: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        debug_capture,
        "record",
        lambda event, **fields: recorded.append((event, fields)),
    )

    source = _build_source(duration=100, stderr_text="")
    source._position_bytes = 100 * ytdl_source.BYTES_PER_SECOND

    source.read()

    stop = next(fields for event, fields in recorded if event == "track-stop")
    assert stop["early"] is False
