import threading
from unittest.mock import MagicMock

import numpy as np
import pytest

from tests.integration.conftest import (
    FRAME_SIZE,
    generate_silence_frame,
    generate_tone_frame,
)


class TestAudioPipelineBasics:
    def test_empty_controller_returns_silence(self, audio_pipeline):
        controller, mixer = audio_pipeline

        result = mixer.read()

        assert len(result) == FRAME_SIZE
        audio_data = np.frombuffer(result, dtype=np.int16)
        assert np.all(audio_data == 0)
        assert mixer.has_active_tracks is False

    def test_single_track_passes_through(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        tone_frames = [generate_tone_frame(440, 16000) for _ in range(5)]
        source = fake_audio_source_factory(frames=tone_frames)

        controller.add_layer(source)
        result = mixer.read()

        assert len(result) == FRAME_SIZE
        audio_data = np.frombuffer(result, dtype=np.int16)
        assert np.any(audio_data != 0)
        assert mixer.has_active_tracks is True

    def test_multiple_tracks_are_mixed(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        tone_440 = [generate_tone_frame(440, 8000) for _ in range(5)]
        tone_880 = [generate_tone_frame(880, 8000) for _ in range(5)]

        source1 = fake_audio_source_factory(frames=tone_440)
        source2 = fake_audio_source_factory(frames=tone_880)

        controller.add_layer(source1)
        controller.add_layer(source2)

        result = mixer.read()
        audio_data = np.frombuffer(result, dtype=np.int16)

        audio_440 = np.frombuffer(tone_440[0], dtype=np.int16)
        expected_max = np.max(np.abs(audio_440)) * 2

        assert np.max(np.abs(audio_data)) <= expected_max + 100
        assert np.all(audio_data >= -32768)
        assert np.all(audio_data <= 32767)


class TestTrackLifecycle:
    def test_finished_track_removed_from_controller(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        source = fake_audio_source_factory(frame_count=2)
        controller.add_layer(source)

        mixer.read()
        mixer.read()
        mixer.read()

        sounds = controller.get_playing_sounds()
        assert source not in [s for _, s in sounds]

    def test_partial_frame_handled(self, audio_pipeline):
        controller, mixer = audio_pipeline

        partial_frame = b"\x00" * 100
        source = MagicMock()
        source.read.return_value = partial_frame
        source.cleanup = MagicMock()

        controller.add_layer(source)
        result = mixer.read()

        assert len(result) == FRAME_SIZE
        sounds = controller.get_playing_sounds()
        assert source not in [s for _, s in sounds]


class TestQueueHandling:
    def test_queue_track_is_mixed(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        queue_source = fake_audio_source_factory(frame_count=3)

        controller.add_to_queue(queue_source)

        result = mixer.read()

        assert len(result) == FRAME_SIZE
        assert mixer.has_active_tracks is True

    def test_queue_advances_on_end(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        finished_source = fake_audio_source_factory(frame_count=1)
        next_source = fake_audio_source_factory(frame_count=5)

        controller.add_to_queue(finished_source)
        controller.add_to_queue(next_source)

        mixer.read()
        mixer.read()

        sounds = controller.get_playing_sounds()
        queue_sounds = [s for t, s in sounds if t == "queue"]
        assert len(queue_sounds) == 1
        assert queue_sounds[0] == next_source

    def test_queue_empty_notification(self, audio_pipeline):
        controller, mixer = audio_pipeline
        callback_called = []

        def on_queue_empty():
            callback_called.append(True)

        controller.on_queue_empty(on_queue_empty)

        source = MagicMock()
        source.read.return_value = b""
        controller.add_to_queue(source)

        mixer.read()

        assert len(callback_called) == 1


class TestTTSHandling:
    def test_tts_plays_and_clears(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        tts_source = fake_audio_source_factory(frame_count=3)
        controller.set_tts_track(tts_source)

        mixer.read()

        sounds = controller.get_playing_sounds()
        tts_sounds = [s for t, s in sounds if t == "tts"]
        assert len(tts_sounds) == 1

        for _ in range(5):
            mixer.read()

        sounds = controller.get_playing_sounds()
        tts_sounds = [s for t, s in sounds if t == "tts"]
        assert len(tts_sounds) == 0


class TestButtonSounds:
    def test_button_sound_plays_and_removes(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        button_source = fake_audio_source_factory(frame_count=2)
        controller.add_button_sound(button_source)

        mixer.read()

        sounds = controller.get_playing_sounds()
        button_sounds = [s for t, s in sounds if t == "button"]
        assert len(button_sounds) == 1

        for _ in range(3):
            mixer.read()

        sounds = controller.get_playing_sounds()
        button_sounds = [s for t, s in sounds if t == "button"]
        assert len(button_sounds) == 0


class TestObserverPattern:
    def test_observer_receives_track_end_event(self, audio_pipeline):
        controller, mixer = audio_pipeline
        events = []

        def on_track_end(**kwargs):
            events.append(("track_end", kwargs))

        mixer.add_observer("track_end", on_track_end)

        source = MagicMock()
        source.read.return_value = b""
        controller.add_layer(source)

        mixer.read()

        assert len(events) == 1
        assert events[0][0] == "track_end"
        assert "to_remove" in events[0][1]

    def test_observer_receives_queue_end_event(self, audio_pipeline):
        controller, mixer = audio_pipeline
        events = []

        def on_queue_end(**kwargs):
            events.append("queue_end")

        mixer.add_observer("queue_end", on_queue_end)

        source = MagicMock()
        source.read.return_value = b""
        controller.add_to_queue(source)

        mixer.read()

        assert "queue_end" in events


class TestThreadSafety:
    def test_concurrent_reads_thread_safety(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline
        errors = []

        def reader_thread():
            try:
                for _ in range(50):
                    mixer.read()
            except Exception as e:
                errors.append(e)

        def adder_thread():
            try:
                for i in range(20):
                    source = fake_audio_source_factory(frame_count=3)
                    controller.add_layer(source)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader_thread),
            threading.Thread(target=adder_thread),
            threading.Thread(target=reader_thread),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestMixerCleanup:
    def test_mixer_cleanup_clears_pending(
        self, audio_pipeline, fake_audio_source_factory
    ):
        controller, mixer = audio_pipeline

        source = fake_audio_source_factory(frame_count=10)
        controller.add_layer(source)

        mixer.read()

        mixer.cleanup()

        assert mixer.pending_futures == {}
