"""Regression tests for AudioController track-finish handling.

These lock in the end-of-track behaviour that the mixer's
``queue_end`` / ``track_end`` path depends on, so a behaviour-preserving
refactor of the controller cannot silently change it.
"""

import discord
from typing import Any, cast

from src.harpi_lib.audio.controller import AudioController


class FakeSource(discord.AudioSource):
    """Audio source that records whether it was cleaned up."""

    def __init__(self, id: str = "layer") -> None:
        self.id = id
        self.cleaned_up = False

    def read(self) -> bytes:
        return b""

    def cleanup(self) -> None:
        self.cleaned_up = True


def test_on_track_finished_cleans_and_clears_current_source():
    controller = AudioController()
    source = FakeSource()
    controller.set_queue_source(source)

    controller._on_track_finished(source)

    assert source.cleaned_up is True
    assert controller.get_queue_source() is None


def test_on_track_finished_ignores_unknown_source():
    controller = AudioController()
    current = FakeSource()
    finished = FakeSource()
    controller.set_queue_source(current)

    controller._on_track_finished(finished)

    assert finished.cleaned_up is False
    assert controller.get_queue_source() is current


def test_remove_finished_source_clears_current_queue_source():
    controller = AudioController()
    source = FakeSource()
    controller.set_queue_source(source)

    controller.remove_finished_source(source)

    assert source.cleaned_up is True
    assert controller.get_queue_source() is None


def test_remove_finished_source_removes_layer():
    controller = AudioController()
    source = FakeSource()
    controller.add_layer(cast(Any, source))

    controller.remove_finished_source(source)

    assert source.cleaned_up is True
    assert controller.get_layer_id(source) is None
    assert controller.get_playing_sounds() == []


def test_remove_finished_source_clears_tts_track():
    controller = AudioController()
    source = FakeSource()
    controller.set_tts_track(source)

    controller.remove_finished_source(source)

    assert source.cleaned_up is True
    assert controller.get_playing_sounds() == []


def test_remove_finished_source_ignores_unknown_source():
    controller = AudioController()
    current = FakeSource()
    removed = FakeSource()
    controller.set_queue_source(current)

    controller.remove_finished_source(removed)

    assert removed.cleaned_up is False
    assert controller.get_queue_source() is current


def test_cleanup_all_cleans_layers_queue_source_and_tts():
    controller = AudioController()
    layer = FakeSource()
    queue_source = FakeSource()
    tts = FakeSource()
    controller.add_layer(cast(Any, layer))
    controller.set_queue_source(queue_source)
    controller.set_tts_track(tts)

    controller.cleanup_all()

    assert layer.cleaned_up is True
    assert queue_source.cleaned_up is True
    assert tts.cleaned_up is True
    assert controller.get_playing_sounds() == []


def test_get_playing_sounds_lists_each_active_source_once():
    controller = AudioController()
    layer = FakeSource()
    queue_source = FakeSource()
    tts = FakeSource()
    controller.add_layer(cast(Any, layer))
    controller.set_queue_source(queue_source)
    controller.set_tts_track(tts)

    sounds = controller.get_playing_sounds()

    assert {kind for kind, _ in sounds} == {"track", "queue", "tts"}
    assert [source for _, source in sounds] == [layer, queue_source, tts]
