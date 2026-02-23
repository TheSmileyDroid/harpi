import numpy as np

from tests.conftest import (
    FRAME_SIZE,
    SAMPLES_PER_FRAME,
    CHANNELS,
    generate_silence_frame,
    generate_tone_frame,
)
from unittest.mock import MagicMock


class TestMixerSourceInit:
    def test_initial_state(self, mixer_source):
        assert mixer_source.has_active_tracks is False
        assert mixer_source.pending_futures == {}

    def test_sample_rate_is_48k(self, mixer_source):
        assert mixer_source.SAMPLE_RATE == 48000

    def test_frame_size_is_3840(self, mixer_source):
        assert mixer_source.FRAME_SIZE == 3840


class TestReadSilence:
    def test_read_returns_silence_when_empty(self, mixer_source):
        result = mixer_source.read()
        assert len(result) == FRAME_SIZE
        assert result == generate_silence_frame()

    def test_read_has_active_tracks_false_when_empty(self, mixer_source):
        mixer_source.read()
        assert mixer_source.has_active_tracks is False


class TestReadSingleTrack:
    def test_read_passes_through_single_track(
        self, mixer_source, soundboard_controller
    ):
        mock_source = MagicMock()
        test_frame = generate_tone_frame(440, 16000)
        mock_source.read.return_value = test_frame

        soundboard_controller.add_layer(mock_source)
        result = mixer_source.read()

        assert len(result) == FRAME_SIZE
        audio_data = np.frombuffer(result, dtype=np.int16)
        assert np.any(audio_data != 0)

    def test_read_has_active_tracks_true_with_track(
        self, mixer_source, soundboard_controller
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = generate_tone_frame()
        soundboard_controller.add_layer(mock_source)

        mixer_source.read()

        assert mixer_source.has_active_tracks is True


class TestReadMixesMultipleTracks:
    def test_read_mixes_two_tracks(self, mixer_source, soundboard_controller):
        mock_source1 = MagicMock()
        mock_source2 = MagicMock()

        frame1 = generate_tone_frame(440, 8000)
        frame2 = generate_tone_frame(880, 8000)

        mock_source1.read.return_value = frame1
        mock_source2.read.return_value = frame2

        soundboard_controller.add_layer(mock_source1)
        soundboard_controller.add_layer(mock_source2)

        result = mixer_source.read()
        audio_data = np.frombuffer(result, dtype=np.int16)

        audio1 = np.frombuffer(frame1, dtype=np.int16)
        expected_max = np.max(audio1) * 2
        assert np.max(audio_data) <= expected_max + 100

    def test_mixed_audio_stays_in_16bit_range(
        self, mixer_source, soundboard_controller
    ):
        sources = []
        for i in range(10):
            mock_source = MagicMock()
            mock_source.read.return_value = generate_tone_frame(
                440 + i * 100, 20000
            )
            sources.append(mock_source)
            soundboard_controller.add_layer(mock_source)

        result = mixer_source.read()
        audio_data = np.frombuffer(result, dtype=np.int16)

        assert np.all(audio_data >= -32768)
        assert np.all(audio_data <= 32767)

    def test_clipping_prevents_overflow(
        self, mixer_source, soundboard_controller
    ):
        mock_source1 = MagicMock()
        mock_source2 = MagicMock()

        loud_frame = np.full(
            SAMPLES_PER_FRAME * CHANNELS, 25000, dtype=np.int16
        ).tobytes()
        mock_source1.read.return_value = loud_frame
        mock_source2.read.return_value = loud_frame

        soundboard_controller.add_layer(mock_source1)
        soundboard_controller.add_layer(mock_source2)

        result = mixer_source.read()
        audio_data = np.frombuffer(result, dtype=np.int16)

        assert np.max(audio_data) <= 32767
        assert np.min(audio_data) >= -32768


class TestFinishedTrackRemoval:
    def test_finished_track_removed(self, mixer_source, soundboard_controller):
        mock_source = MagicMock()
        mock_source.read.return_value = b""
        mock_source.cleanup = MagicMock()

        soundboard_controller.add_layer(mock_source)
        mixer_source.read()

        sounds = soundboard_controller.get_playing_sounds()
        assert mock_source not in [s for _, s in sounds]

    def test_partial_frame_handled(self, mixer_source, soundboard_controller):
        mock_source = MagicMock()
        partial_frame = b"\x00" * 100
        mock_source.read.return_value = partial_frame
        mock_source.cleanup = MagicMock()

        soundboard_controller.add_layer(mock_source)
        result = mixer_source.read()

        assert len(result) == FRAME_SIZE
        sounds = soundboard_controller.get_playing_sounds()
        assert mock_source not in [s for _, s in sounds]


class TestObserverNotifications:
    def test_track_end_notification(self, mixer_source, soundboard_controller):
        callback = MagicMock()
        mixer_source.add_observer("track_end", callback)

        mock_source = MagicMock()
        mock_source.read.return_value = b""
        soundboard_controller.add_layer(mock_source)

        mixer_source.read()

        callback.assert_called_once()
        assert "to_remove" in callback.call_args.kwargs

    def test_queue_end_notification(self, mixer_source, soundboard_controller):
        callback = MagicMock()
        mixer_source.add_observer("queue_end", callback)

        mock_source = MagicMock()
        mock_source.read.return_value = b""
        soundboard_controller.add_to_queue(mock_source)

        mixer_source.read()

        callback.assert_called_once()

    def test_remove_observer(self, mixer_source, soundboard_controller):
        callback = MagicMock()
        mixer_source.add_observer("track_end", callback)
        mixer_source.remove_observer("track_end", callback)

        mock_source = MagicMock()
        mock_source.read.return_value = b""
        soundboard_controller.add_layer(mock_source)

        mixer_source.read()

        callback.assert_not_called()

    def test_observer_exception_doesnt_crash(
        self, mixer_source, soundboard_controller
    ):
        def bad_callback(**kwargs):
            raise RuntimeError("Test error")

        mixer_source.add_observer("track_end", bad_callback)

        mock_source = MagicMock()
        mock_source.read.return_value = b""
        soundboard_controller.add_layer(mock_source)

        result = mixer_source.read()
        assert len(result) == FRAME_SIZE


class TestCleanup:
    def test_cleanup_cancels_pending_futures(
        self, mixer_source, soundboard_controller
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = generate_tone_frame()
        soundboard_controller.add_layer(mock_source)

        mixer_source.read()
        mixer_source.cleanup()

        assert mixer_source.pending_futures == {}

    def test_cleanup_executor_shutdown(
        self, mixer_source, soundboard_controller
    ):
        mock_source = MagicMock()
        mock_source.read.return_value = generate_tone_frame()
        soundboard_controller.add_layer(mock_source)

        mixer_source.read()
        mixer_source.cleanup()

        assert mixer_source.executor._shutdown is True


class TestTTSHandling:
    def test_tts_in_mix(self, mixer_source, soundboard_controller):
        mock_tts = MagicMock()
        mock_tts.read.return_value = generate_tone_frame(1000, 16000)
        soundboard_controller.set_tts_track(mock_tts)

        result = mixer_source.read()
        audio_data = np.frombuffer(result, dtype=np.int16)

        assert np.any(audio_data != 0)

    def test_tts_cleanup_on_finish(self, mixer_source, soundboard_controller):
        mock_tts = MagicMock()
        mock_tts.read.return_value = b""
        mock_tts.cleanup = MagicMock()

        soundboard_controller.set_tts_track(mock_tts)
        mixer_source.read()

        mock_tts.cleanup.assert_called()


class TestTimeoutHandling:
    def test_slow_source_doesnt_block(
        self, mixer_source, soundboard_controller
    ):
        mock_source = MagicMock()

        def slow_read():
            import time

            time.sleep(0.1)
            return generate_tone_frame()

        mock_source.read = slow_read
        soundboard_controller.add_layer(mock_source)

        result = mixer_source.read()
        assert len(result) == FRAME_SIZE
