"""Unit tests for music seek support across sources and services."""

from typing import cast

from dataclasses import dataclass
import io
import threading
import time
from unittest import mock

import discord
import pytest
from discord.opus import Encoder

from src.harpi_lib.api import GuildConfig
from src.harpi_lib.audio.controller import AudioController
from src.harpi_lib.music.ytmusicdata import (
    BYTES_PER_SECOND,
    FFmpegPCMAudio,
    YoutubeDLSource,
)
from src.harpi_lib.services.music_queue import MusicQueueService

CHUNK_SIZE = Encoder.FRAME_SIZE


class FakeProc:
    def __init__(self, chunks: list[bytes]) -> None:
        self.stdout = io.BytesIO(b"".join(chunks))
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self.killed = True

    def communicate(self) -> tuple[bytes, bytes]:
        return b"", b""


def _patch_popen(chunks: list[bytes]) -> mock._patch:
    return mock.patch(
        "src.harpi_lib.music.ytmusicdata.subprocess.Popen",
        side_effect=lambda *args, **kwargs: FakeProc(chunks),
    )


def test_initial_read_spawns_without_seek_offset():
    chunks = [b"\x00" * CHUNK_SIZE, b""]
    with _patch_popen(chunks) as popen:
        source = FFmpegPCMAudio(source="https://example.com/audio")
        result = source.read()

    assert result == b"\x00" * CHUNK_SIZE
    args = popen.call_args.args[0]
    assert "-ss" not in args


def test_seek_restarts_process_with_offset():
    chunks = [b"\x00" * CHUNK_SIZE, b""]
    with _patch_popen(chunks) as popen:
        source = FFmpegPCMAudio(source="https://example.com/audio")
        source.read()
        old_proc = source._process
        assert old_proc is not None

        source.seek(30.0)

    assert cast(FakeProc, old_proc).terminated
    assert source._process is not None
    assert source._process is not old_proc
    assert popen.call_count == 2
    args = popen.call_args.args[0]
    assert args.index("-ss") < args.index("-i")
    assert args[args.index("-ss") + 1] == "30.00"


def test_seek_with_no_process_sets_offset_only():
    with _patch_popen([b""]) as popen:
        source = FFmpegPCMAudio(source="https://example.com/audio")

        source.seek(45.5)

        assert source._process is None
        assert popen.call_count == 0

        source.read()

        assert popen.call_count == 1
        args = popen.call_args.args[0]
        assert args[args.index("-ss") + 1] == "45.50"


def test_read_clears_process_on_eof():
    chunks = [b"\x00" * CHUNK_SIZE, b""]
    with _patch_popen(chunks):
        source = FFmpegPCMAudio(source="https://example.com/audio")
        assert source.read() == b"\x00" * CHUNK_SIZE
        proc = source._process
        assert proc is not None

        assert source.read() == b""
        assert source._process is None
        assert cast(FakeProc, proc).terminated


class FakeRawSource(discord.AudioSource):
    def __init__(self, chunk_size: int, total_chunks: int) -> None:
        self.chunk_size = chunk_size
        self.remaining = total_chunks

    def read(self) -> bytes:
        if self.remaining <= 0:
            return b""
        self.remaining -= 1
        return b"\x00" * self.chunk_size


def test_position_tracking_increases_per_read():
    chunk = b"\x00" * 19200
    source = YoutubeDLSource(
        FakeRawSource(len(chunk), 4),
        data={"title": "t", "url": "u"},
        volume=1.0,
    )

    assert source.position_seconds() == 0.0
    for i in range(1, 5):
        source.read()
        assert source.position_seconds() == pytest.approx(
            i * 19200 / BYTES_PER_SECOND
        )


class FakeSeekableRawSource(discord.AudioSource):
    def __init__(self) -> None:
        self.seek_calls: list[float] = []

    def read(self) -> bytes:
        return b""

    def seek(self, position: float) -> None:
        self.seek_calls.append(position)


def test_seek_delegates_to_original_and_resets_position():
    original = FakeSeekableRawSource()
    source = YoutubeDLSource(
        original, data={"title": "t", "url": "u"}, volume=1.0
    )

    source.seek(12.5)

    assert original.seek_calls == [12.5]
    assert source.position_seconds() == 12.5


class FakeSeekSource(discord.AudioSource):
    def __init__(self, position: float = 0.0) -> None:
        self.position = position
        self.seek_calls: list[float] = []

    def read(self) -> bytes:
        return b""

    def position_seconds(self) -> float:
        return self.position

    def seek(self, position: float) -> None:
        self.seek_calls.append(position)
        self.position = position


@dataclass
class FakeMusicData:
    duration: int


def _make_guild_config(source, current_music=None) -> GuildConfig:
    controller = AudioController()
    controller.set_queue_source(source)
    return GuildConfig(
        id=1,
        mixer=mock.Mock(),
        controller=controller,
        current_music=current_music,
    )


def _make_service(source, current_music=None) -> MusicQueueService:
    guild_config = _make_guild_config(source, current_music)
    return MusicQueueService(mock.Mock(), {1: guild_config})


async def test_absolute_seek_uses_position_directly():
    source = FakeSeekSource(position=10.0)
    service = _make_service(source)

    await service.seek(1, 30.0, absolute=True)

    assert source.seek_calls == [30.0]


async def test_relative_seek_adds_to_current_position():
    source = FakeSeekSource(position=10.0)
    service = _make_service(source)

    await service.seek(1, -4.0)

    assert source.seek_calls == [6.0]


async def test_negative_result_clamps_to_zero():
    source = FakeSeekSource(position=5.0)
    service = _make_service(source)

    await service.seek(1, -20.0)

    assert source.seek_calls == [0.0]


async def test_target_clamps_to_track_duration():
    source = FakeSeekSource(position=10.0)
    service = _make_service(source, current_music=FakeMusicData(duration=60))

    await service.seek(1, 90.0, absolute=True)

    assert source.seek_calls == [60.0]


async def test_seek_raises_when_guild_not_connected():
    service = MusicQueueService(mock.Mock(), {})

    with pytest.raises(ValueError):
        await service.seek(99, 10.0)


class FakeUnseekableSource(discord.AudioSource):
    def read(self) -> bytes:
        return b""


async def test_seek_returns_silently_without_supported_source():
    controller = AudioController()
    controller.set_queue_source(FakeUnseekableSource())
    guild_config = GuildConfig(id=1, mixer=mock.Mock(), controller=controller)
    service = MusicQueueService(mock.Mock(), {1: guild_config})

    await service.seek(1, 10.0)


def test_get_queue_position_returns_zero_without_source():
    controller = AudioController()

    assert controller.get_queue_position() == 0.0


def test_get_queue_position_returns_source_position():
    controller = AudioController()
    controller.set_queue_source(FakeSeekSource(position=42.5))

    assert controller.get_queue_position() == 42.5


def test_get_queue_position_handles_source_errors():
    class BrokenSource(discord.AudioSource):
        def read(self) -> bytes:
            return b""

        def position_seconds(self) -> float:
            raise RuntimeError("boom")

    controller = AudioController()
    controller.set_queue_source(BrokenSource())

    assert controller.get_queue_position() == 0.0


def test_read_after_seek_uses_new_process():
    first_chunks = [b"\x00" * CHUNK_SIZE, b""]
    second_chunks = [b"\x01" * CHUNK_SIZE, b""]
    with _patch_popen(first_chunks):
        source = FFmpegPCMAudio(source="https://example.com/audio")
        assert source.read() == b"\x00" * CHUNK_SIZE
    with _patch_popen(second_chunks) as popen:
        source.seek(5.0)
        assert source.read() == b"\x01" * CHUNK_SIZE
        args = popen.call_args.args[0]
        assert args.index("-ss") < args.index("-i")
        assert args[args.index("-ss") + 1] == "5.00"


def test_seek_after_cleanup_is_noop():
    with _patch_popen([b"\x00" * CHUNK_SIZE, b""]) as popen:
        source = FFmpegPCMAudio(source="https://example.com/audio")
        source.read()
        source.cleanup()
        source.seek(5.0)
    assert popen.call_count == 1


def test_read_after_cleanup_returns_empty():
    with _patch_popen([b"\x00" * CHUNK_SIZE, b""]) as popen:
        source = FFmpegPCMAudio(source="https://example.com/audio")
        source.read()
        source.cleanup()
        assert source.read() == b""
    assert popen.call_count == 1


def test_youtube_source_cleanup_forwards_to_original():
    class CleanupTrackingSource(discord.AudioSource):
        def __init__(self) -> None:
            self.cleaned_up = False

        def read(self) -> bytes:
            return b""

        def cleanup(self) -> None:
            self.cleaned_up = True

    original = CleanupTrackingSource()
    source = YoutubeDLSource(
        original, data={"title": "t", "url": "u"}, volume=1.0
    )

    source.cleanup()

    assert original.cleaned_up


async def test_seek_rejects_non_finite_target():
    source = FakeSeekSource(position=10.0)
    service = _make_service(source)

    with pytest.raises(ValueError):
        await service.seek(1, float("inf"), absolute=True)


async def test_seek_clamps_when_duration_unknown():
    source = FakeSeekSource(position=0.0)
    service = _make_service(source)

    await service.seek(1, 1_000_000_000.0, absolute=True)

    assert source.seek_calls == [4 * 3600]


def test_seek_request_rejects_non_finite():
    from pydantic import ValidationError

    from src.api.music import SeekRequest

    with pytest.raises(ValidationError):
        SeekRequest(guild_id="1", position=float("inf"))
    with pytest.raises(ValidationError):
        SeekRequest(guild_id="1", position=float("nan"))


def test_music_control_request_rejects_non_finite_position():
    from pydantic import ValidationError

    from src.api.music import MusicControlRequest

    with pytest.raises(ValidationError):
        MusicControlRequest(
            guild_id="1", action="seek", mode=None, position=float("inf")
        )


def test_seek_invalidates_in_flight_spawn():
    """A seek during an in-flight reader spawn must win via generation."""
    release_spawn = threading.Event()
    unblock_spawn = threading.Event()
    spawned: list[tuple[float, FakeProc]] = []

    def controlled_spawn(self: FFmpegPCMAudio) -> FakeProc:
        offset = self._seek_offset
        release_spawn.set()
        unblock_spawn.wait(timeout=5)
        proc = FakeProc([b"\x00" * CHUNK_SIZE, b""])
        spawned.append((offset, proc))
        return proc

    source = FFmpegPCMAudio(source="https://example.com/audio")
    with mock.patch.object(FFmpegPCMAudio, "_spawn_process", controlled_spawn):
        reader = threading.Thread(target=source.read, daemon=True)
        reader.start()
        assert release_spawn.wait(timeout=5)
        source.seek(50.0)
        unblock_spawn.set()
        reader.join(timeout=5)

    assert not reader.is_alive()
    assert [offset for offset, _ in spawned] == [0.0, 50.0]
    assert spawned[0][1].terminated
    assert source._process is spawned[1][1]


def test_seek_serializes_concurrent_calls():
    """Concurrent seeks must land atomically on the underlying source."""
    entered = threading.Event()
    release = threading.Event()

    class BlockingSeekSource(discord.AudioSource):
        def __init__(self) -> None:
            self.seek_calls: list[float] = []

        def read(self) -> bytes:
            return b""

        def seek(self, position: float) -> None:
            self.seek_calls.append(position)
            if position == 10.0:
                entered.set()
                release.wait(timeout=5)

    original = BlockingSeekSource()
    source = YoutubeDLSource(
        original, data={"title": "t", "url": "u"}, volume=1.0
    )

    first = threading.Thread(target=source.seek, args=(10.0,), daemon=True)
    first.start()
    assert entered.wait(timeout=5)

    second = threading.Thread(target=source.seek, args=(20.0,), daemon=True)
    second.start()
    time.sleep(0.05)
    assert original.seek_calls == [10.0]

    release.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert original.seek_calls == [10.0, 20.0]
    assert source.position_seconds() == 20.0
