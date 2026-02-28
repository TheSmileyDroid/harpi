"""Tests for audio test tone sources."""

from src.harpi_lib.audio.test_tone_source import (
    MultiFrequencyTestSource,
    TestToneSource,
)


class TestTestToneSource:
    FRAME_SIZE = TestToneSource.FRAME_SIZE

    def test_default_init(self):
        src = TestToneSource()
        assert src.frequency == 440
        assert src.name == "Test Tone"
        assert src.is_finished is False

    def test_custom_init(self):
        src = TestToneSource(frequency=880, duration_ms=2000, name="Custom")
        assert src.frequency == 880
        assert src.name == "Custom"

    def test_read_returns_correct_frame_size(self):
        src = TestToneSource(duration_ms=1000)
        frame = src.read()
        assert len(frame) == self.FRAME_SIZE

    def test_read_returns_non_silent(self):
        src = TestToneSource(frequency=440, duration_ms=100, amplitude=16000)
        frame = src.read()
        assert frame != b"\x00" * self.FRAME_SIZE

    def test_read_returns_empty_after_duration(self):
        src = TestToneSource(duration_ms=20)
        # At 48kHz with 960 samples/frame → each frame = 20ms
        # So 20ms duration → 1 frame
        frame1 = src.read()
        assert len(frame1) == self.FRAME_SIZE
        frame2 = src.read()
        assert frame2 == b""

    def test_is_finished_after_exhausted(self):
        src = TestToneSource(duration_ms=20)
        assert src.is_finished is False
        src.read()  # consume the one frame
        assert src.is_finished is True

    def test_cleanup_stops_playback(self):
        src = TestToneSource(duration_ms=5000)
        assert src.read() != b""
        src.cleanup()
        assert src.read() == b""

    def test_read_after_cleanup_returns_empty(self):
        src = TestToneSource(duration_ms=5000)
        src.cleanup()
        assert src.read() == b""


class TestMultiFrequencyTestSource:
    FRAME_SIZE = MultiFrequencyTestSource.FRAME_SIZE

    def test_default_init(self):
        src = MultiFrequencyTestSource()
        assert src.name == "Multi-Frequency Test"
        assert src.current_frequency == 261  # First default freq

    def test_custom_frequencies(self):
        src = MultiFrequencyTestSource(frequencies=[100, 200])
        assert src.current_frequency == 100

    def test_read_returns_correct_frame_size(self):
        src = MultiFrequencyTestSource(duration_per_freq_ms=100)
        frame = src.read()
        assert len(frame) == self.FRAME_SIZE

    def test_cycles_through_frequencies(self):
        # 20ms per freq → 1 frame per freq
        src = MultiFrequencyTestSource(
            frequencies=[100, 200], duration_per_freq_ms=20
        )
        assert src.current_frequency == 100
        src.read()  # consume frame for freq 100
        assert src.current_frequency == 200
        src.read()  # consume frame for freq 200
        assert src.current_frequency is None  # exhausted

    def test_returns_empty_after_all_frequencies(self):
        src = MultiFrequencyTestSource(
            frequencies=[100], duration_per_freq_ms=20
        )
        frame1 = src.read()
        assert len(frame1) == self.FRAME_SIZE
        frame2 = src.read()
        assert frame2 == b""

    def test_cleanup_stops_playback(self):
        src = MultiFrequencyTestSource(duration_per_freq_ms=5000)
        assert src.read() != b""
        src.cleanup()
        assert src.read() == b""

    def test_current_frequency_none_after_exhausted(self):
        src = MultiFrequencyTestSource(
            frequencies=[440], duration_per_freq_ms=20
        )
        src.read()  # exhaust the single frequency
        assert src.current_frequency is None
