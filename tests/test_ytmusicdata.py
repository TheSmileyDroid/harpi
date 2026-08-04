"""Unit tests for yt-dlp data reuse, stream selection, and queue skip recovery.

Test doubles are hand-written Fakes injected via ``pytest.MonkeyPatch``;
the silence probe is exercised against real ffmpeg on local media files.
"""

import asyncio
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, cast

import pytest

from src.harpi_lib.api import GuildConfig, LoopMode
from src.harpi_lib.audio.controller import AudioController
from src.harpi_lib.music import ytmusicdata
from src.harpi_lib.music.ytmusicdata import (
    ProbeEnvironmentError,
    ProbeSilenceError,
    ProbeTimeoutError,
    SILENCE_MAX_VOLUME_DB,
    YTMusicData,
    YoutubeDLSource,
    _parse_max_volume,
    probe_stream_audio,
)
from src.harpi_lib.services import music_queue as music_queue_module
from src.harpi_lib.services.music_queue import MusicQueueService


def _stream_formats() -> list[dict[str, Any]]:
    return [
        {
            "ext": "mhtml",
            "url": "https://sb.example.com/storyboard",
            "acodec": "none",
            "vcodec": "none",
        },
        {
            "ext": "mp4",
            "url": "https://stream.example.com/muxed.mp4",
            "acodec": "mp4a.40.2",
            "vcodec": "avc1.64001f",
            "abr": 128,
        },
        {
            "ext": "mp4",
            "url": "https://stream.example.com/video.mp4",
            "acodec": "none",
            "vcodec": "avc1",
            "tbr": 2000,
        },
        {
            "ext": "opus",
            "url": "https://stream.example.com/audio.opus",
            "acodec": "opus",
            "vcodec": "none",
            "abr": 50,
        },
        {
            "ext": "m4a",
            "url": "https://stream.example.com/audio-m4a-64.m4a",
            "acodec": "mp4a.40.2",
            "vcodec": "none",
            "abr": 64,
        },
        {
            "ext": "m4a",
            "url": "https://stream.example.com/audio-m4a-128.m4a",
            "acodec": "mp4a.40.2",
            "vcodec": "none",
            "abr": 128,
        },
    ]


def test_select_stream_url_prefers_highest_bitrate_m4a_audio_only():
    url = YoutubeDLSource._select_stream_url({"formats": _stream_formats()})

    assert url == "https://stream.example.com/audio-m4a-128.m4a"


def test_select_stream_url_falls_back_to_top_level_url():
    data = {"url": "https://stream.example.com/direct.mp4"}

    assert (
        YoutubeDLSource._select_stream_url(data)
        == "https://stream.example.com/direct.mp4"
    )


def test_select_stream_url_returns_none_for_unusable_data():
    assert YoutubeDLSource._select_stream_url(None) is None
    assert YoutubeDLSource._select_stream_url(cast(Any, "not a dict")) is None
    assert YoutubeDLSource._select_stream_url({}) is None
    assert YoutubeDLSource._select_stream_url({"formats": []}) is None
    assert YoutubeDLSource._select_stream_url({"url": "not-a-url"}) is None
    assert (
        YoutubeDLSource._select_stream_url({
            "formats": [{"ext": "m4a", "url": ""}]
        })
        is None
    )


def test_select_stream_url_prefers_higher_tbr_when_abr_missing():
    formats = [
        {
            "ext": "m4a",
            "url": "https://stream.example.com/audio-m4a-64.m4a",
            "acodec": "mp4a.40.2",
            "vcodec": "none",
            "tbr": 64,
        },
        {
            "ext": "m4a",
            "url": "https://stream.example.com/audio-m4a-128.m4a",
            "acodec": "mp4a.40.2",
            "vcodec": "none",
            "tbr": 128,
        },
    ]

    url = YoutubeDLSource._select_stream_url({"formats": formats})

    assert url == "https://stream.example.com/audio-m4a-128.m4a"


def test_parse_max_volume_parses_volumedetect_output():
    stderr = (
        "[Parsed_volumedetect_0 @ 0x55] n_samples: 65536\n"
        "[Parsed_volumedetect_0 @ 0x55] mean_volume: -32.4 dB\n"
        "[Parsed_volumedetect_0 @ 0x55] max_volume: -18.1 dB\n"
        "[Parsed_volumedetect_0 @ 0x55] histogram_0db: 1\n"
        "[Parsed_volumedetect_0 @ 0x55] histogram_1db: 2\n"
    )

    assert _parse_max_volume(stderr) == -18.1


def test_parse_max_volume_returns_none_for_garbage():
    assert _parse_max_volume("") is None
    assert _parse_max_volume("no volume lines here") is None
    assert _parse_max_volume("max_volume: missing dB value") is None


def test_parse_max_volume_handles_inf_silence():
    assert _parse_max_volume("max_volume: -inf dB") == float("-inf")


def test_validate_duration_rejects_zero_and_negative():
    with pytest.raises(ValueError, match="no playable duration"):
        YoutubeDLSource._validate_duration({"duration": 0})
    with pytest.raises(ValueError, match="no playable duration"):
        YoutubeDLSource._validate_duration({"duration": -5})
    with pytest.raises(ValueError, match="no playable duration"):
        YoutubeDLSource._validate_duration({"duration": "0"})


def test_validate_duration_allows_positive_or_missing():
    YoutubeDLSource._validate_duration({"duration": 210})
    YoutubeDLSource._validate_duration({"duration": 0.5})
    YoutubeDLSource._validate_duration({})
    YoutubeDLSource._validate_duration({"duration": None})
    YoutubeDLSource._validate_duration({"duration": "abc"})


def test_is_usable_audio_format_requires_audio_codec():
    assert not YoutubeDLSource._is_usable_audio_format({
        "acodec": "none",
        "vcodec": "avc1",
        "ext": "mp4",
        "url": "...",
    })
    assert not YoutubeDLSource._is_usable_audio_format({
        "acodec": "none",
        "vcodec": "none",
        "ext": "mhtml",
        "url": "...",
    })
    assert not YoutubeDLSource._is_usable_audio_format({})
    assert not YoutubeDLSource._is_usable_audio_format({"acodec": 123})
    assert YoutubeDLSource._is_usable_audio_format({
        "acodec": "mp4a.40.2",
        "vcodec": "avc1.64001f",
        "ext": "mp4",
        "url": "...",
    })
    assert YoutubeDLSource._is_usable_audio_format({
        "acodec": "opus",
        "vcodec": "none",
        "ext": "opus",
        "url": "...",
    })


def test_ytmusicdata_video_data_returns_stored_dict():
    video = {"title": "t", "formats": []}
    musicdata = YTMusicData(video)

    assert musicdata.video_data is video


@pytest.fixture
def media_dir(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Generate real local media fixtures with ffmpeg into tmp_path."""
    tone = tmp_path / "tone.wav"
    silent = tmp_path / "silent.wav"
    garbage = tmp_path / "garbage.bin"

    def _run(args: list[str]) -> None:
        subprocess.run(
            args,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    _run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        str(tone),
    ])
    _run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",
        "-t",
        "2",
        str(silent),
    ])
    garbage.write_bytes(b"not media")
    return tone, silent, garbage


def test_probe_stream_audio_real_tone(media_dir: tuple[Path, Path, Path]):
    tone, _, _ = media_dir

    max_volume = probe_stream_audio(str(tone))

    assert SILENCE_MAX_VOLUME_DB < max_volume < 0.0


def test_probe_stream_audio_real_silent(media_dir: tuple[Path, Path, Path]):
    _, silent, _ = media_dir

    with pytest.raises(ValueError, match="stream is silent"):
        probe_stream_audio(str(silent))


def test_probe_stream_audio_real_garbage(media_dir: tuple[Path, Path, Path]):
    _, _, garbage = media_dir

    with pytest.raises(ValueError, match="stream not playable"):
        probe_stream_audio(str(garbage))


def test_probe_stream_audio_missing_path(tmp_path: Path):
    with pytest.raises(ValueError, match="stream not playable"):
        probe_stream_audio(str(tmp_path / "missing.wav"))


def test_probe_stream_audio_rejects_option_injection():
    with pytest.raises(ValueError, match="invalid stream url"):
        probe_stream_audio("-i")


def test_probe_stream_audio_times_out_on_blocking_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    monkeypatch.setattr(ytmusicdata, "STREAM_PROBE_TOTAL_TIMEOUT", 0.3)

    with pytest.raises(ValueError, match="probe timed out"):
        probe_stream_audio(str(fifo))


def test_ffmpeg_headers_arg_carries_browser_like_headers():
    headers = ytmusicdata._FFMPEG_HEADERS

    assert "User-Agent:" in headers
    assert "Accept:" in headers
    assert "Accept-Language:" in headers
    assert headers.endswith("\r\n")


def test_probe_stream_audio_sends_headers_for_stream_urls(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured.extend(args)
            self.returncode = 0

        def communicate(self, timeout=None):
            return None, "[Parsed_volumedetect_0] max_volume: -3.0 dB\n"

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    max_volume = probe_stream_audio("https://stream.example.com/audio.m4a")

    assert max_volume == -3.0
    assert (
        captured[captured.index("-headers") + 1] == ytmusicdata._FFMPEG_HEADERS
    )


def test_probe_stream_audio_omits_headers_for_local_paths(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured.extend(args)
            self.returncode = 0

        def communicate(self, timeout=None):
            return None, "[Parsed_volumedetect_0] max_volume: -3.0 dB\n"

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    probe_stream_audio("/tmp/media/tone.wav")

    assert "-headers" not in captured


def test_ffmpegpcm_spawn_sends_headers_for_stream_urls(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured.extend(args)
            self.stdout = None

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    ytmusicdata.FFmpegPCMAudio(
        source="https://stream.example.com/audio.m4a"
    )._spawn_process()

    assert (
        captured[captured.index("-headers") + 1] == ytmusicdata._FFMPEG_HEADERS
    )


def test_ffmpegpcm_spawn_omits_headers_for_local_paths(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured.extend(args)
            self.stdout = None

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    ytmusicdata.FFmpegPCMAudio(source="/tmp/media/tone.wav")._spawn_process()

    assert "-headers" not in captured


def test_probe_stream_audio_retries_transient_failures(
    monkeypatch: pytest.MonkeyPatch,
):
    attempts: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            attempts.append("call")
            self.returncode = 1 if len(attempts) < 3 else 0

        def communicate(self, timeout=None):
            if self.returncode == 0:
                return None, "[Parsed_volumedetect_0] max_volume: -3.0 dB\n"
            return None, "HTTP error 403 Forbidden\n"

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr(ytmusicdata, "STREAM_PROBE_RETRY_DELAY", 0.0)

    max_volume = probe_stream_audio("https://stream.example.com/audio.m4a")

    assert max_volume == -3.0
    assert len(attempts) == 3


def test_probe_stream_audio_retries_then_gives_up(
    monkeypatch: pytest.MonkeyPatch,
):
    attempts: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            attempts.append("call")
            self.returncode = 1

        def communicate(self, timeout=None):
            return None, "HTTP error 403 Forbidden\n"

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr(ytmusicdata, "STREAM_PROBE_RETRY_DELAY", 0.0)

    with pytest.raises(ValueError, match="stream not playable"):
        probe_stream_audio("https://stream.example.com/audio.m4a")

    assert len(attempts) == ytmusicdata.STREAM_PROBE_ATTEMPTS


def test_probe_stream_audio_does_not_retry_silence(
    monkeypatch: pytest.MonkeyPatch,
):
    attempts: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            attempts.append("call")
            self.returncode = 0

        def communicate(self, timeout=None):
            return None, "[Parsed_volumedetect_0] max_volume: -91.0 dB\n"

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr(ytmusicdata, "STREAM_PROBE_RETRY_DELAY", 0.0)

    with pytest.raises(ValueError, match="stream is silent"):
        probe_stream_audio("https://stream.example.com/audio.m4a")

    assert len(attempts) == 1


def test_probe_stream_audio_does_not_retry_local_paths(
    monkeypatch: pytest.MonkeyPatch,
):
    attempts: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            attempts.append("call")
            self.returncode = 1

        def communicate(self, timeout=None):
            return None, "cannot open file\n"

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    with pytest.raises(ValueError, match="stream not playable"):
        probe_stream_audio("/tmp/media/missing.wav")

    assert len(attempts) == 1


def test_redact_signed_tokens_strips_signed_values():
    text = (
        "https://x.googlevideo.com/vid?lsig=aaabbb&token=xyz&sig=cccddd"
        "&expire=123456&pot=ppp&n=nnn&nh=hhh&gcr=ggg&signature=sss&s=vvv"
    )

    redacted = ytmusicdata._redact_signed_tokens(text)

    for secret in (
        "aaabbb",
        "xyz",
        "cccddd",
        "123456",
        "ppp",
        "nnn",
        "hhh",
        "ggg",
        "sss",
        "vvv",
    ):
        assert secret not in redacted
    assert "REDACTED" in redacted


def test_redact_stream_url_strips_query_string():
    redacted = ytmusicdata._redact_stream_url(
        "https://x.googlevideo.com/videoplayback?expire=123&sig=secret"
    )

    assert "sig" not in redacted
    assert "expire" not in redacted
    assert redacted.startswith("https://x.googlevideo.com")


def test_redact_stream_url_strips_userinfo_and_non_urls():
    redacted = ytmusicdata._redact_stream_url(
        "https://user:secret@x.googlevideo.com/videoplayback?expire=1"
    )

    assert "secret" not in redacted
    assert "user" not in redacted
    assert redacted == "https://x.googlevideo.com/..."
    assert (
        ytmusicdata._redact_stream_url("not a url")
        == "<non-url stream source>"
    )
    assert ytmusicdata._redact_stream_url("") == "<non-url stream source>"


def test_probe_stream_once_rejects_option_injection():
    with pytest.raises(ValueError, match="invalid stream url"):
        ytmusicdata._probe_stream_once("-i", timeout=5.0)


def test_probe_stream_once_raises_environment_error_without_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "Popen", raise_missing)

    with pytest.raises(ProbeEnvironmentError, match="ffmpeg not available"):
        ytmusicdata._probe_stream_once(
            "https://stream.example.com/audio.m4a", timeout=5.0
        )


def test_probe_stream_once_raises_environment_error_on_permission_denied(
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_permission(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(subprocess, "Popen", raise_permission)

    with pytest.raises(ProbeEnvironmentError, match="ffmpeg not available"):
        ytmusicdata._probe_stream_once(
            "https://stream.example.com/audio.m4a", timeout=5.0
        )


def test_probe_stream_audio_does_not_retry_environment_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[str] = []

    def fake_probe(url: str, timeout: float) -> float:
        calls.append(url)
        raise ProbeEnvironmentError("ffmpeg not available")

    monkeypatch.setattr(ytmusicdata, "_probe_stream_once", fake_probe)
    monkeypatch.setattr(ytmusicdata, "STREAM_PROBE_RETRY_DELAY", 0.0)

    with pytest.raises(ProbeEnvironmentError):
        probe_stream_audio("https://stream.example.com/audio.m4a")

    assert len(calls) == 1


def test_probe_stream_audio_does_not_retry_silence_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[str] = []

    def fake_probe(url: str, timeout: float) -> float:
        calls.append(url)
        raise ProbeSilenceError("stream is silent")

    monkeypatch.setattr(ytmusicdata, "_probe_stream_once", fake_probe)
    monkeypatch.setattr(ytmusicdata, "STREAM_PROBE_RETRY_DELAY", 0.0)

    with pytest.raises(ProbeSilenceError):
        probe_stream_audio("https://stream.example.com/audio.m4a")

    assert len(calls) == 1


def test_probe_stream_audio_passes_bounded_budget_to_each_attempt(
    monkeypatch: pytest.MonkeyPatch,
):
    attempts: list[str] = []
    timeouts: list[float] = []

    def fake_probe(url: str, timeout: float) -> float:
        attempts.append(url)
        timeouts.append(timeout)
        if len(attempts) < 2:
            raise ValueError("stream not playable")
        return -3.0

    monkeypatch.setattr(ytmusicdata, "_probe_stream_once", fake_probe)
    monkeypatch.setattr(ytmusicdata, "STREAM_PROBE_RETRY_DELAY", 0.0)

    max_volume = probe_stream_audio("https://stream.example.com/audio.m4a")

    assert max_volume == -3.0
    assert len(attempts) == 2
    assert all(
        0.0 < timeout <= ytmusicdata.STREAM_PROBE_TOTAL_TIMEOUT
        for timeout in timeouts
    )


def test_probe_failure_is_transient_classifies_errors():
    assert not YoutubeDLSource._probe_failure_is_transient(
        ProbeSilenceError("stream is silent")
    )
    assert not YoutubeDLSource._probe_failure_is_transient(
        ProbeEnvironmentError("ffmpeg missing")
    )
    assert YoutubeDLSource._probe_failure_is_transient(
        ValueError("stream not playable")
    )
    assert YoutubeDLSource._probe_failure_is_transient(
        ProbeTimeoutError("stream probe timed out")
    )


def test_ffmpegpcm_spawn_rejects_option_injection():
    source = ytmusicdata.FFmpegPCMAudio(source="-i")

    with pytest.raises(ValueError, match="invalid stream source"):
        source._spawn_process()


def test_ffmpegpcm_spawn_headers_with_existing_reconnect_options(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured.extend(args)
            self.stdout = None

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    ytmusicdata.FFmpegPCMAudio(
        source="https://stream.example.com/audio.m4a",
        before_options="-reconnect 1 -reconnect_streamed 1",
    )._spawn_process()

    assert captured.count("-reconnect") == 1
    assert (
        captured[captured.index("-headers") + 1] == ytmusicdata._FFMPEG_HEADERS
    )


class FakeProbe:
    def __init__(
        self,
        error: Exception | None = None,
        fail_urls: list[str] | None = None,
    ) -> None:
        self.urls: list[str] = []
        self.error = error
        self.fail_urls = set(fail_urls or [])

    def __call__(self, stream_url: str) -> float:
        self.urls.append(stream_url)
        if stream_url in self.fail_urls:
            raise ValueError("stream not playable")
        if self.error is not None:
            raise self.error
        return -3.0


class FakeExtractor:
    def __init__(self, result: dict[str, Any] | None = None) -> None:
        self.result = result
        self.calls: list[tuple[str, bool]] = []

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        self.calls.append((url, download))
        if self.result is None:
            raise AssertionError("extract_info must not be called")
        return self.result


class BlockingExtractor(FakeExtractor):
    def __init__(self) -> None:
        super().__init__()
        self.release = threading.Event()

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        self.calls.append((url, download))
        self.release.wait(timeout=5)
        return {"title": "slow"}


def _m4a_format(url: str) -> dict[str, Any]:
    return {
        "ext": "m4a",
        "url": url,
        "acodec": "mp4a.40.2",
        "vcodec": "none",
        "abr": 128,
    }


async def test_from_music_data_reuses_stored_formats(
    monkeypatch: pytest.MonkeyPatch,
):
    video = {
        "title": "reuse",
        "url": "https://www.youtube.com/watch?v=abc",
        "duration": 210,
        "formats": [_m4a_format("https://stream.example.com/reused.m4a")],
    }
    musicdata = YTMusicData(video)
    probe = FakeProbe()
    extractor = FakeExtractor(result=None)
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    source = await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert source.url == "https://www.youtube.com/watch?v=abc"
    assert probe.urls == ["https://stream.example.com/reused.m4a"]
    assert extractor.calls == []


async def test_from_music_data_falls_back_to_extract_info(
    monkeypatch: pytest.MonkeyPatch,
):
    musicdata = YTMusicData({
        "title": "flat",
        "original_url": "https://www.youtube.com/watch?v=flat",
    })
    extracted = {
        "title": "flat",
        "duration": 180,
        "formats": [
            {
                "ext": "opus",
                "url": "https://stream.example.com/fallback.opus",
                "acodec": "opus",
                "vcodec": "none",
                "abr": 70,
            }
        ],
    }
    probe = FakeProbe()
    extractor = FakeExtractor(result=extracted)
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    source = await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert source.url == "https://www.youtube.com/watch?v=flat"
    assert extractor.calls == [("https://www.youtube.com/watch?v=flat", False)]
    assert probe.urls == ["https://stream.example.com/fallback.opus"]


async def test_from_music_data_flat_search_entry_uses_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    musicdata = YTMusicData({
        "_type": "url",
        "title": "flat",
        "url": "https://www.youtube.com/watch?v=flat",
        "duration": 635,
    })
    extracted = {
        "title": "flat",
        "duration": 180,
        "formats": [
            {
                "ext": "opus",
                "url": "https://stream.example.com/fallback.opus",
                "acodec": "opus",
                "vcodec": "none",
                "abr": 70,
            }
        ],
    }
    probe = FakeProbe()
    extractor = FakeExtractor(result=extracted)
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    source = await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert extractor.calls == [("https://www.youtube.com/watch?v=flat", False)]
    assert source.url == "https://www.youtube.com/watch?v=flat"
    assert probe.urls == ["https://stream.example.com/fallback.opus"]


async def test_from_music_data_times_out_on_slow_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(ytmusicdata, "YT_EXTRACT_TIMEOUT", 0.05)
    musicdata = YTMusicData({"title": "slow"})
    probe = FakeProbe()
    extractor = BlockingExtractor()
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    with pytest.raises(asyncio.TimeoutError):
        await YoutubeDLSource.from_music_data(musicdata)

    extractor.release.set()


async def test_from_music_data_propagates_silent_probe(
    monkeypatch: pytest.MonkeyPatch,
):
    video = {
        "title": "silent",
        "url": "https://www.youtube.com/watch?v=silent",
        "duration": 210,
        "formats": [_m4a_format("https://stream.example.com/reused.m4a")],
    }
    musicdata = YTMusicData(video)
    probe = FakeProbe(error=ProbeSilenceError("stream is silent"))
    extractor = FakeExtractor(result=None)
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    with pytest.raises(ValueError, match="stream is silent"):
        await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert probe.urls == ["https://stream.example.com/reused.m4a"]
    assert extractor.calls == []


async def test_from_music_data_refetches_when_reused_stream_unplayable(
    monkeypatch: pytest.MonkeyPatch,
):
    video = {
        "title": "retry",
        "url": "https://www.youtube.com/watch?v=retry",
        "duration": 210,
        "formats": [_m4a_format("https://stream.example.com/reused.m4a")],
    }
    musicdata = YTMusicData(video)
    extracted = {
        "title": "retry",
        "duration": 210,
        "formats": [_m4a_format("https://stream.example.com/fresh.m4a")],
    }
    probe = FakeProbe(fail_urls=["https://stream.example.com/reused.m4a"])
    extractor = FakeExtractor(result=extracted)
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    source = await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert source.url == "https://www.youtube.com/watch?v=retry"
    assert extractor.calls == [
        ("https://www.youtube.com/watch?v=retry", False)
    ]
    assert probe.urls == [
        "https://stream.example.com/reused.m4a",
        "https://stream.example.com/fresh.m4a",
    ]


async def test_from_music_data_plays_fresh_top_level_url_without_formats(
    monkeypatch: pytest.MonkeyPatch,
):
    musicdata = YTMusicData({
        "_type": "url",
        "title": "direct",
        "url": "https://www.youtube.com/watch?v=direct",
        "duration": 635,
    })
    extracted = {
        "title": "direct",
        "url": "https://direct.example.com/audio.mp3",
        "duration": 120,
    }
    probe = FakeProbe()
    extractor = FakeExtractor(result=extracted)
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    source = await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert source.url == "https://www.youtube.com/watch?v=direct"
    assert extractor.calls == [
        ("https://www.youtube.com/watch?v=direct", False)
    ]
    assert probe.urls == ["https://direct.example.com/audio.mp3"]


async def test_from_music_data_flat_entry_probes_fresh_stream_once(
    monkeypatch: pytest.MonkeyPatch,
):
    musicdata = YTMusicData({
        "_type": "url",
        "title": "flat",
        "url": "https://www.youtube.com/watch?v=flat",
        "duration": 635,
    })
    extracted = {
        "title": "flat",
        "duration": 180,
        "formats": [_m4a_format("https://stream.example.com/fresh.m4a")],
    }
    probe = FakeProbe(fail_urls=["https://stream.example.com/fresh.m4a"])
    extractor = FakeExtractor(result=extracted)
    monkeypatch.setattr(ytmusicdata, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusicdata, "ytdl", extractor)

    with pytest.raises(ValueError, match="No playable stream found"):
        await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert extractor.calls == [("https://www.youtube.com/watch?v=flat", False)]
    assert probe.urls == ["https://stream.example.com/fresh.m4a"]


class FakeSource:
    def __init__(self) -> None:
        self.volume = 1.0


class FakeSourceFactory:
    """Fake YoutubeDLSource substitute for MusicQueueService tests."""

    @classmethod
    async def from_music_data(
        cls, music_data: Any, volume: float = 0.3
    ) -> FakeSource:
        if music_data.title == "bad":
            raise RuntimeError("throttled")
        return FakeSource()


class FakeMixer:
    pass


class FakeBot:
    pass


class FakeMusicData(YTMusicData):
    """Minimal YTMusicData stand-in for queue tests."""

    def __init__(self, title: str) -> None:
        super().__init__({"title": title})


def _make_guild_config(
    *titles: str, current: str | None = None
) -> tuple[Any, AudioController]:
    controller = AudioController()
    guild_config = GuildConfig(
        id=1,
        mixer=cast(Any, FakeMixer()),
        controller=controller,
        queue=[FakeMusicData(t) for t in titles],
    )
    if current is not None:
        guild_config.current_music = FakeMusicData(current)
    return guild_config, controller


async def test_next_music_inner_skips_failing_track_and_plays_next(
    monkeypatch: pytest.MonkeyPatch,
):
    guild_config, controller = _make_guild_config("bad", "good")
    monkeypatch.setattr(
        music_queue_module, "YoutubeDLSource", FakeSourceFactory
    )
    service = MusicQueueService(cast(Any, FakeBot()), {1: guild_config})

    await service._next_music_inner(guild_config)

    assert guild_config.current_music is not None
    assert guild_config.current_music.title == "good"
    assert isinstance(controller.get_queue_source(), FakeSource)
    assert guild_config.queue == []


async def test_next_music_inner_all_failing_tracks_clear_queue(
    monkeypatch: pytest.MonkeyPatch,
):
    guild_config, controller = _make_guild_config("bad", "bad")
    monkeypatch.setattr(
        music_queue_module, "YoutubeDLSource", FakeSourceFactory
    )
    service = MusicQueueService(cast(Any, FakeBot()), {1: guild_config})

    await service._next_music_inner(guild_config)

    assert guild_config.current_music is None
    assert controller.get_queue_source() is None
    assert guild_config.queue == []


async def test_next_music_inner_track_loop_reload_failure_skips_to_next(
    monkeypatch: pytest.MonkeyPatch,
):
    guild_config, controller = _make_guild_config("good", current="bad")
    guild_config.loop = LoopMode.TRACK
    monkeypatch.setattr(
        music_queue_module, "YoutubeDLSource", FakeSourceFactory
    )
    service = MusicQueueService(cast(Any, FakeBot()), {1: guild_config})

    await service._next_music_inner(guild_config)

    assert guild_config.current_music is not None
    assert guild_config.current_music.title == "good"
    assert isinstance(controller.get_queue_source(), FakeSource)
    assert guild_config.queue == []
