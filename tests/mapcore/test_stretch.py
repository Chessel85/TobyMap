"""Time stretching for the spatial voice (P2-T16g, SON-3): faster without the pitch going up."""
from __future__ import annotations

import numpy as np
import pytest

from mapcore.sound import stretch
from mapcore.sound.stretch import PIPER_MOST, piper_speed, speed_up, split_rate, wsola

RATE = 22050


def tone(freq: float = 220.0, seconds: float = 1.0, rate: int = RATE) -> np.ndarray:
    t = np.arange(int(seconds * rate)) / rate
    return (0.8 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def peak_hz(samples: np.ndarray, rate: int = RATE) -> float:
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples)), n=8 * len(samples)))
    return float(np.argmax(spectrum) * rate / (8 * len(samples)))


@pytest.mark.parametrize("factor", [1.25, 2.0, 3.0, 5.0])
def test_length_is_divided_by_the_stretch(factor):
    src = tone(seconds=2.0)
    out = wsola(src, RATE, factor)
    frame = int(stretch.FRAME_S * RATE)
    assert abs(len(out) - len(src) / factor) <= frame


@pytest.mark.parametrize("freq", [110.0, 220.0, 330.0])
@pytest.mark.parametrize("factor", [2.0, 5.0])
def test_the_pitch_is_unchanged(freq, factor):
    out = wsola(tone(freq, 2.0), RATE, factor)
    assert peak_hz(out) == pytest.approx(freq, abs=2.0)


@pytest.mark.parametrize("factor", [2.0, 3.5, 5.0])
def test_no_clicks_at_the_joins(factor):
    src = tone(220.0, 2.0)
    own = float(np.abs(np.diff(src)).max())   # the tone's own largest step between samples
    out = wsola(src, RATE, factor)
    assert float(np.abs(np.diff(out)).max()) <= own * 1.25
    # and the loudness stays even, with no dips where slices fade into each other
    body = out[len(out) // 10: -len(out) // 10]
    windows = body[: len(body) // 220 * 220].reshape(-1, 220)
    rms = np.sqrt((windows ** 2).mean(axis=1))
    assert rms.min() > 0.85 * rms.max()


def test_the_pitch_can_be_lowered_without_slowing_down():
    src = tone(220.0, 2.0)
    out = stretch.lower_pitch(src, RATE, 0.84)
    assert len(out) == pytest.approx(len(src), rel=0.03)
    assert peak_hz(out) == pytest.approx(220.0 * 0.84, abs=2.0)


@pytest.mark.parametrize("speed", [1.0, 2.0, 5.0])
def test_the_voice_behind_is_lower_at_the_same_speed(speed):
    """The PO chose sample 9 on 8 November 2026: lower behind, without slowing down."""
    src = tone(220.0, 2.0)
    out = stretch.shape_voice(src, RATE, speed, 0.84)
    assert len(out) == pytest.approx(len(src) / speed, rel=0.03)
    assert peak_hz(out) == pytest.approx(220.0 * 0.84, abs=2.0)
    ahead = stretch.shape_voice(src, RATE, speed, 1.0)
    assert np.array_equal(ahead, speed_up(src, RATE, speed))


def test_a_stretch_of_one_or_less_changes_nothing():
    src = tone()
    assert np.array_equal(wsola(src, RATE, 1.0), src)
    assert np.array_equal(speed_up(src, RATE, 1.0), src)
    assert np.array_equal(speed_up(src, RATE, 0.8), src)


def test_short_sounds_and_silence_are_safe():
    assert len(speed_up(np.zeros(0, np.float32), RATE, 3.0)) == 0
    assert len(speed_up(np.zeros(100, np.float32), RATE, 3.0)) <= 100
    out = speed_up(np.zeros(RATE, np.float32), RATE, 3.0)
    assert out.dtype == np.float32 and not np.any(out)


def words_and_gaps() -> np.ndarray:
    """Three 'words' of tone with 300 ms gaps of silence between them."""
    word, gap = tone(200.0, 0.4), np.zeros(int(0.3 * RATE), np.float32)
    return np.concatenate([word, gap, word, gap, word])


def test_gaps_between_words_are_shortened_first():
    src = words_and_gaps()
    shorter = stretch.shorten_gaps(src, RATE, 2.0)
    loud = lambda s: int((np.abs(s) > 0.05).sum())   # noqa: E731
    assert len(shorter) < len(src) - int(0.4 * RATE)       # most of the 600 ms of gaps went
    assert loud(shorter) == pytest.approx(loud(src), rel=0.01)   # and none of the words
    assert len(stretch.shorten_gaps(tone(), RATE, 3.0)) == RATE   # no gap, nothing cut


def test_speed_up_reaches_the_speed_asked_for():
    src = words_and_gaps()
    for factor in (1.5, 2.5, 4.0):
        out = speed_up(src, RATE, factor)
        assert len(out) == pytest.approx(len(src) / factor, rel=0.05)
        assert out.dtype == np.float32


def test_the_speed_is_split_between_piper_and_the_stretch():
    # Up to 100 percent Piper alone, as before.
    assert split_rate(1.0) == (1.0, 1.0)
    assert split_rate(0.5) == (0.5, 1.0)
    # Above it, Piper speaks as fast as it cleanly can, and the stretch makes up the rest,
    # allowing for Piper being slower than asked (piper_speed).
    p, s = split_rate(5.0)
    assert p == PIPER_MOST == 2.0
    assert piper_speed(p) * s == pytest.approx(5.0)
    p, s = split_rate(1.5)
    assert p == 1.5 and piper_speed(p) * s == pytest.approx(1.5)
    # Measured with Alba on 8 November 2026: 2.0 gave 1.54 to 1.67 times as fast.
    assert 1.5 < piper_speed(2.0) < 1.7
    assert piper_speed(1.0) == 1.0
