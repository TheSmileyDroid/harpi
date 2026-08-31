"""Tests for the PCM mixing source."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from src.harpi_lib.audio.mixer import MixerSource


FRAME_SAMPLES = 960 * 2


class FakeController:
    def __init__(self) -> None:
        self.playing: list[tuple[str, Any]] = []
        self.removed: list[Any] = []
        self.finished: list[Any] = []
        self.tts_track: Any = "placeholder"

    def get_playing_sounds(self) -> list[tuple[str, Any]]:
        return self.playing

    def remove_finished_source(self, source: Any) -> None:
        self.removed.append(source)
        self.playing = [(t, s) for t, s in self.playing if s is not source]

    def _on_track_finished(self, source: Any) -> None:
        self.finished.append(source)

    def set_tts_track(self, track: Any) -> None:
        self.tts_track = track


class FakeSource:
    def __init__(self, data: bytes | Exception) -> None:
        self.data = data

    def read(self) -> bytes:
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


def pcm_frame(*values: int) -> bytes:
    samples = list(values) + [0] * (FRAME_SAMPLES - len(values))
    return np.array(samples, dtype=np.int16).tobytes()


@pytest.fixture
def controller():
    return FakeController()


@pytest.fixture
def mixer(controller):
    source = MixerSource(controller)  # type: ignore[arg-type]
    yield source
    source.cleanup()


def test_add_observer_and_notify(controller, mixer):
    seen: list[dict[str, object]] = []
    mixer.add_observer("track_end", lambda **kw: seen.append(kw))
    mixer._notify_observers("track_end", to_remove=["x"])
    assert seen == [{"to_remove": ["x"]}]


def test_notify_observers_swallows_callback_errors(controller, mixer):
    def boom(**kw: object) -> None:
        raise RuntimeError("observer failed")

    mixer.add_observer("queue_end", boom)
    mixer._notify_observers("queue_end")


def test_notify_observers_allows_observer_changes_during_callback(
    controller, mixer
):
    late: list[int] = []

    def add_late(**kw: object) -> None:
        mixer.add_observer("queue_end", lambda **kw: late.append(1))

    mixer.add_observer("track_end", add_late)
    mixer._notify_observers("track_end")
    mixer._notify_observers("queue_end")
    assert late == [1]


def test_read_mixes_and_sums_sources(controller, mixer):
    first = FakeSource(pcm_frame(1000))
    second = FakeSource(pcm_frame(500))
    controller.playing = [("track", first), ("track", second)]

    data = mixer.read()
    samples = np.frombuffer(data, dtype=np.int16)
    assert samples[0] == 1500
    assert len(samples) == FRAME_SAMPLES


def test_read_clips_overflowing_sum(controller, mixer):
    first = FakeSource(pcm_frame(32000))
    second = FakeSource(pcm_frame(32000))
    controller.playing = [("track", first), ("track", second)]

    samples = np.frombuffer(mixer.read(), dtype=np.int16)
    assert samples[0] == 32767


def test_read_returns_silence_after_shutdown(controller, mixer):
    mixer.cleanup()
    assert mixer.read() == b"\x00" * mixer.frame_size


def test_read_removes_source_that_errors(controller, mixer):
    source = FakeSource(RuntimeError("decode failed"))
    controller.playing = [("track", source)]
    ended: list[object] = []
    mixer.add_observer("track_end", lambda **kw: ended.extend(kw["to_remove"]))

    mixer.read()

    assert ended == [source]
    assert controller.removed == [source]
    assert controller.playing == []


def test_read_removes_source_with_empty_frame(controller, mixer):
    source = FakeSource(b"")
    controller.playing = [("track", source)]

    mixer.read()

    assert controller.removed == [source]


def test_read_pads_short_frame_then_removes_source(controller, mixer):
    source = FakeSource(np.array([7], dtype=np.int16).tobytes())
    controller.playing = [("track", source)]

    samples = np.frombuffer(mixer.read(), dtype=np.int16)
    assert samples[0] == 7
    assert samples[1] == 0
    assert controller.removed == [source]


def test_read_keeps_source_with_full_frame(controller, mixer):
    source = FakeSource(pcm_frame(1))
    controller.playing = [("track", source)]

    mixer.read()

    assert controller.removed == []
    assert controller.playing == [("track", source)]


def test_track_end_notifies_observers(controller, mixer):
    source = FakeSource(b"")
    controller.playing = [("track", source)]
    ended: list[object] = []
    mixer.add_observer("track_end", lambda **kw: ended.extend(kw["to_remove"]))

    mixer.read()

    assert ended == [source]


def test_queue_end_notifies_observers_and_controller(controller, mixer):
    source = FakeSource(b"")
    controller.playing = [("queue", source)]
    ended: list[bool] = []
    mixer.add_observer("queue_end", lambda **kw: ended.append(True))

    mixer.read()

    assert ended == [True]
    assert controller.finished == [source]
    assert controller.removed == [source]


def test_tts_source_end_clears_tts_track(controller, mixer):
    source = FakeSource(b"")
    controller.playing = [("tts", source)]

    mixer.read()

    assert controller.tts_track is None
    assert controller.removed == [source]


def test_button_source_end_needs_no_handling(controller, mixer):
    source = FakeSource(b"")
    controller.playing = [("button", source)]

    mixer.read()

    assert controller.finished == []
    assert controller.removed == [source]


def test_cleanup_shuts_down_executor_and_blocks_new_reads(controller):
    mixer = MixerSource(controller)  # type: ignore[arg-type]
    mixer.cleanup()
    with pytest.raises(RuntimeError, match="shutdown"):
        mixer.executor.submit(lambda: None)


def test_submit_read_futures_skips_when_shutdown(controller, mixer):
    mixer._shutdown = True
    mixer._submit_read_futures([("track", FakeSource(b""))])
    assert mixer.pending_futures == {}


def test_submit_read_futures_handles_shutdown_race(controller, mixer):
    mixer.cleanup()
    mixer._shutdown = False
    mixer._submit_read_futures([("track", FakeSource(b""))])
    assert mixer.pending_futures == {}


def test_prune_stale_futures_cancels_removed_sources(controller, mixer):
    stale = FakeSource(b"")
    active = FakeSource(pcm_frame(1))
    controller.playing = [("track", active)]
    mixer.pending_futures[stale] = mixer.executor.submit(lambda: b"")
    mixer.pending_futures[active] = mixer.executor.submit(lambda: b"")

    mixer._prune_stale_futures(controller.get_playing_sounds())

    assert stale not in mixer.pending_futures
    assert active in mixer.pending_futures


def test_await_futures_waits_for_pending_sources(controller, mixer):
    source = FakeSource(pcm_frame(1))
    controller.playing = [("track", source)]
    mixer._submit_read_futures(controller.get_playing_sounds())

    mixer._await_futures(controller.get_playing_sounds())

    assert all(f.done() for f in mixer.pending_futures.values())
