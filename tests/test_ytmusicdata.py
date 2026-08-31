import asyncio
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, cast

import pytest

from src.harpi_lib.music import (
    stream_probe,
    ytmusic,
)
from src.harpi_lib.music.ffmpeg_source import FFmpegPCMAudio, _FFMPEG_HEADERS
from src.harpi_lib.music.stream_probe import (
    ProbeEnvironmentError,
    ProbeSilenceError,
    ProbeTimeoutError,
    SILENCE_MAX_VOLUME_DB,
    _parse_max_volume,
    probe_stream_audio,
)
from src.harpi_lib.music.ytdl_source import YoutubeDLSource
from src.harpi_lib.music.ytmusic import YTMusicData
from src.harpi_lib.music.nothing_found import NothingFoundError


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

    assert _parse_max_volume(stderr) == pytest.approx(-18.1)


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
    monkeypatch.setattr(stream_probe, "STREAM_PROBE_TOTAL_TIMEOUT", 0.3)

    with pytest.raises(ValueError, match="probe timed out"):
        probe_stream_audio(str(fifo))


def test_ffmpeg_headers_arg_carries_browser_like_headers():
    headers = _FFMPEG_HEADERS

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

    assert max_volume == pytest.approx(-3.0)
    assert captured[captured.index("-headers") + 1] == _FFMPEG_HEADERS


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

    FFmpegPCMAudio(
        source="https://stream.example.com/audio.m4a"
    )._spawn_process()

    assert captured[captured.index("-headers") + 1] == _FFMPEG_HEADERS


def test_ffmpegpcm_spawn_omits_headers_for_local_paths(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[str] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            captured.extend(args)
            self.stdout = None

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    FFmpegPCMAudio(source="/tmp/media/tone.wav")._spawn_process()

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
    monkeypatch.setattr(stream_probe, "STREAM_PROBE_RETRY_DELAY", 0.0)

    max_volume = probe_stream_audio("https://stream.example.com/audio.m4a")

    assert max_volume == pytest.approx(-3.0)
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
    monkeypatch.setattr(stream_probe, "STREAM_PROBE_RETRY_DELAY", 0.0)

    with pytest.raises(ValueError, match="stream not playable"):
        probe_stream_audio("https://stream.example.com/audio.m4a")

    assert len(attempts) == stream_probe.STREAM_PROBE_ATTEMPTS


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
    monkeypatch.setattr(stream_probe, "STREAM_PROBE_RETRY_DELAY", 0.0)

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

    redacted = stream_probe._redact_signed_tokens(text)

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
    redacted = stream_probe._redact_stream_url(
        "https://x.googlevideo.com/videoplayback?expire=123&sig=secret"
    )

    assert "sig" not in redacted
    assert "expire" not in redacted
    assert redacted.startswith("https://x.googlevideo.com")


def test_redact_stream_url_strips_userinfo_and_non_urls():
    redacted = stream_probe._redact_stream_url(
        "https://user:secret@x.googlevideo.com/videoplayback?expire=1"
    )

    assert "secret" not in redacted
    assert "user" not in redacted
    assert redacted == "https://x.googlevideo.com/..."
    assert (
        stream_probe._redact_stream_url("not a url")
        == "<non-url stream source>"
    )
    assert stream_probe._redact_stream_url("") == "<non-url stream source>"


def test_probe_stream_once_rejects_option_injection():
    with pytest.raises(ValueError, match="invalid stream url"):
        stream_probe._probe_stream_once("-i", timeout=5.0)


def test_probe_stream_once_raises_environment_error_without_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "Popen", raise_missing)

    with pytest.raises(ProbeEnvironmentError, match="ffmpeg not available"):
        stream_probe._probe_stream_once(
            "https://stream.example.com/audio.m4a", timeout=5.0
        )


def test_probe_stream_once_raises_environment_error_on_permission_denied(
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_permission(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(subprocess, "Popen", raise_permission)

    with pytest.raises(ProbeEnvironmentError, match="ffmpeg not available"):
        stream_probe._probe_stream_once(
            "https://stream.example.com/audio.m4a", timeout=5.0
        )


def test_probe_stream_audio_does_not_retry_environment_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[str] = []

    def fake_probe(url: str, timeout: float) -> float:
        calls.append(url)
        raise ProbeEnvironmentError("ffmpeg not available")

    monkeypatch.setattr(stream_probe, "_probe_stream_once", fake_probe)
    monkeypatch.setattr(stream_probe, "STREAM_PROBE_RETRY_DELAY", 0.0)

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

    monkeypatch.setattr(stream_probe, "_probe_stream_once", fake_probe)
    monkeypatch.setattr(stream_probe, "STREAM_PROBE_RETRY_DELAY", 0.0)

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

    monkeypatch.setattr(stream_probe, "_probe_stream_once", fake_probe)
    monkeypatch.setattr(stream_probe, "STREAM_PROBE_RETRY_DELAY", 0.0)

    max_volume = probe_stream_audio("https://stream.example.com/audio.m4a")

    assert max_volume == pytest.approx(-3.0)
    assert len(attempts) == 2
    assert all(
        0.0 < timeout <= stream_probe.STREAM_PROBE_TOTAL_TIMEOUT
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
    source = FFmpegPCMAudio(source="-i")

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

    FFmpegPCMAudio(
        source="https://stream.example.com/audio.m4a",
        before_options="-reconnect 1 -reconnect_streamed 1",
    )._spawn_process()

    assert captured.count("-reconnect") == 1
    assert captured[captured.index("-headers") + 1] == _FFMPEG_HEADERS


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
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

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
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

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
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

    source = await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert extractor.calls == [("https://www.youtube.com/watch?v=flat", False)]
    assert source.url == "https://www.youtube.com/watch?v=flat"
    assert probe.urls == ["https://stream.example.com/fallback.opus"]


async def test_from_music_data_times_out_on_slow_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(ytmusic, "YT_EXTRACT_TIMEOUT", 0.05)
    musicdata = YTMusicData({"title": "slow"})
    probe = FakeProbe()
    extractor = BlockingExtractor()
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

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
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

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
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

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
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

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
    monkeypatch.setattr(stream_probe, "probe_stream_audio", probe)
    monkeypatch.setattr(ytmusic, "ytdl", extractor)

    with pytest.raises(ValueError, match="No playable stream found"):
        await YoutubeDLSource.from_music_data(musicdata, volume=0.5)

    assert extractor.calls == [("https://www.youtube.com/watch?v=flat", False)]
    assert probe.urls == ["https://stream.example.com/fresh.m4a"]


def _fake_ytdl(monkeypatch: pytest.MonkeyPatch, result: Any, calls: list):
    class FakeYtdl:
        def extract_info(self, arg, download=False, process=False):
            assert not process, "search must extract flat entries"
            calls.append(arg)
            if isinstance(result, Exception):
                raise result
            return result

    monkeypatch.setattr(ytmusic, "search_ytdl", FakeYtdl())


def test_search_delegates_to_ytsearch_for_plain_query(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list = []
    _fake_ytdl(monkeypatch, {"entries": [{"title": "x"}]}, calls)

    result = ytmusic.search("some song")

    assert calls == ["ytsearch10:some song"]
    assert result == {"entries": [{"title": "x"}]}


def test_search_extracts_flat_entries_without_downloading(
    monkeypatch: pytest.MonkeyPatch,
):
    """A download=True mutant would write files to disk in production."""
    kwargs_seen: list[dict] = []

    class RecordingYtdl:
        def extract_info(self, arg, **kwargs):
            kwargs_seen.append(kwargs)
            return {"entries": [{"title": "x"}]}

    monkeypatch.setattr(ytmusic, "search_ytdl", RecordingYtdl())

    ytmusic.search("some song")
    ytmusic.search("https://www.youtube.com/watch?v=abc")

    assert kwargs_seen == [
        {"download": False, "process": False},
        {"download": False, "process": False},
    ]


def test_search_recognizes_urls_with_uppercase_characters(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list = []
    _fake_ytdl(monkeypatch, {"title": "direct"}, calls)

    ytmusic.search("https://www.YouTube.COM/watch?v=ABC")

    assert calls == ["https://www.YouTube.COM/watch?v=ABC"]


def test_search_extracts_url_directly(monkeypatch: pytest.MonkeyPatch):
    calls: list = []
    _fake_ytdl(monkeypatch, {"title": "direct"}, calls)

    result = ytmusic.search("https://www.youtube.com/watch?v=abc")

    assert calls == ["https://www.youtube.com/watch?v=abc"]
    assert result == {"title": "direct"}


def test_search_wraps_ytdl_failure_in_nothing_found(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list = []
    _fake_ytdl(monkeypatch, RuntimeError("network down"), calls)

    with pytest.raises(NothingFoundError):
        ytmusic.search("some song")


def test_search_wraps_empty_result_in_nothing_found(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list = []
    _fake_ytdl(monkeypatch, None, calls)

    with pytest.raises(NothingFoundError):
        ytmusic.search("some song")


async def test_from_url_wraps_each_entry(monkeypatch: pytest.MonkeyPatch):
    entries = [
        {
            "title": "kept",
            "url": "https://www.youtube.com/watch?v=1",
            "duration": 100,
        },
        {
            "title": "no duration",
            "url": "https://www.youtube.com/watch?v=2",
        },
        {
            "title": "zero duration",
            "url": "https://www.youtube.com/watch?v=3",
            "duration": 0,
        },
        {
            "title": "no watch url",
            "url": "https://youtu.be/4",
            "duration": 50,
        },
    ]
    monkeypatch.setattr(ytmusic, "search", lambda arg: {"entries": entries})

    tracks = await YTMusicData.from_url("some song")

    assert [t.title for t in tracks] == ["kept"]
    assert tracks[0].duration == 100


async def test_from_url_without_entries_returns_single_track(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        ytmusic,
        "search",
        lambda arg: {
            "title": "solo",
            "url": "https://www.youtube.com/watch?v=solo",
            "duration": 30,
        },
    )

    tracks = await YTMusicData.from_url("https://www.youtube.com/watch?v=solo")

    assert len(tracks) == 1
    assert tracks[0].title == "solo"
    assert tracks[0].url == "https://www.youtube.com/watch?v=solo"


async def test_search_is_not_starved_by_track_extractions(
    monkeypatch: pytest.MonkeyPatch,
):
    """A skip chain occupies the extraction executor for ~4s per track;
    panel searches must not queue behind it."""
    release_extraction = threading.Event()
    ytmusic._YTDL_SERIAL_EXECUTOR.submit(release_extraction.wait)
    monkeypatch.setattr(
        ytmusic,
        "search",
        lambda arg: {
            "title": "fresh search",
            "url": "https://www.youtube.com/watch?v=fresh",
            "duration": 9,
        },
    )
    try:
        tracks = await asyncio.wait_for(
            YTMusicData.from_url("some song"), timeout=5
        )
    finally:
        release_extraction.set()

    assert [t.title for t in tracks] == ["fresh search"]


def test_detect_js_runtimes_follows_ytdlp_priority_order():
    installed = {"deno", "bun"}

    found = ytmusic.detect_js_runtimes(
        lambda name: f"/usr/bin/{name}" if name in installed else None
    )

    assert found == ["deno", "bun"]


def test_detect_js_runtimes_finds_nothing_when_none_installed():
    assert ytmusic.detect_js_runtimes(lambda name: None) == []


def test_js_runtimes_option_uses_ytdlp_dict_shape():
    assert ytmusic.js_runtimes_option(["node", "bun"]) == {
        "node": {},
        "bun": {},
    }
