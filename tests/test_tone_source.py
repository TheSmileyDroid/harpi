"""Tests for the test-tone audio sources."""

import numpy as np

from src.harpi_lib.audio.tone_source import (
    MultiFrequencyTestSource,
    TestToneSource,
)


def test_tone_source_defaults():
    tone = TestToneSource()
    assert tone.frequency == 440
    assert tone.name == "Test Tone"
    assert tone._frames_total == 50


def test_tone_source_read_returns_full_frames_until_duration_ends():
    tone = TestToneSource(duration_ms=40)
    assert tone._frames_total == 2
    first = tone.read()
    assert len(first) == TestToneSource.FRAME_SIZE
    assert tone.read() == first
    assert tone.read() == b""


def test_tone_source_read_is_silent_after_cleanup():
    tone = TestToneSource()
    tone.cleanup()
    assert tone.read() == b""


def test_tone_source_generates_stereo_sine_at_amplitude():
    tone = TestToneSource(frequency=600, amplitude=8000)
    samples = np.frombuffer(tone.read(), dtype=np.int16)
    assert len(samples) == TestToneSource.SAMPLES_PER_FRAME * 2
    left = samples[::2]
    right = samples[1::2]
    assert np.array_equal(left, right)
    assert abs(left).max() <= 8000
    assert abs(left).max() > 7000


def test_multi_frequency_source_cycles_through_frequencies():
    source = MultiFrequencyTestSource(
        frequencies=[300, 400], duration_per_freq_ms=40
    )
    assert source._frames_per_freq == 2

    first_freq_frames = [source.read(), source.read()]
    second_freq_frames = [source.read(), source.read()]

    assert first_freq_frames[0] != second_freq_frames[0]
    assert second_freq_frames[0] == second_freq_frames[1]
    assert source.read() == b""


def test_multi_frequency_source_reads_every_frequency_then_stops():
    source = MultiFrequencyTestSource(
        frequencies=[300, 400], duration_per_freq_ms=40
    )
    frames = [source.read() for _ in range(5)]
    assert frames[0] == frames[1]
    assert frames[2] == frames[3]
    assert frames[0] != frames[2]
    assert frames[4] == b""


def test_multi_frequency_source_uses_default_frequencies():
    source = MultiFrequencyTestSource()
    assert source._frequencies == [261, 329, 392, 523]
    assert source.name == "Multi-Frequency Test"


def test_multi_frequency_source_cleanup_stops_reading():
    source = MultiFrequencyTestSource()
    source.cleanup()
    assert source.read() == b""


def test_multi_frequency_source_generates_stereo_frames():
    source = MultiFrequencyTestSource(frequencies=[500])
    samples = np.frombuffer(source.read(), dtype=np.int16)
    left = samples[::2]
    right = samples[1::2]
    assert np.array_equal(left, right)
    assert abs(left).max() <= 12000
