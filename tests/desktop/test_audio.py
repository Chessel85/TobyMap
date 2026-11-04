"""Spatial rendering for the listening test: shapes and levels, never the sound device (P1-T13, AD-10, SON-9)."""
import io
import wave

import numpy as np
import pytest

from desktop.audio import spatial


@pytest.fixture(scope="module")
def noise():
    return spatial.noise_bursts(count=1)


def level(x):
    return float(np.sqrt((x ** 2).mean()))


def test_stereo_pans_left_and_right(noise):
    right = spatial.stereo(noise, 90, 0.04)
    left = spatial.stereo(noise, 270, 0.04)
    assert level(right[:, 1]) > 3 * level(right[:, 0])
    assert level(left[:, 0]) > 3 * level(left[:, 1])
    centre = spatial.stereo(noise, 0, 0.04)
    assert level(centre[:, 0]) == pytest.approx(level(centre[:, 1]), rel=1e-4)


def test_a_sound_behind_is_lower_and_longer(noise):
    assert len(spatial.stereo(noise, 180, 0.04)) > len(spatial.stereo(noise, 0, 0.04))
    assert not spatial.is_behind(90) and spatial.is_behind(135) and spatial.is_behind(225)


def test_distance_follows_the_curve(noise):
    near = level(spatial.stereo(noise, 0, 0.04))
    edge = level(spatial.stereo(noise, 0, 1.0))
    beyond = level(spatial.stereo(noise, 0, 1.5))
    assert near > edge > beyond


@pytest.mark.skipif(not spatial.hrtf_available(), reason="the KEMAR download is not on this computer")
def test_hrtf_puts_a_sound_on_the_right_louder_in_the_right_ear(noise):
    out = spatial.render("hrtf_pitch", noise[:8000], 90, 0.04)
    assert level(out[:, 1]) > level(out[:, 0])


def test_a_moving_sound_is_whole_and_ends_where_it_should(noise):
    burst = noise[:int(0.17 * spatial.RATE)]   # the burst, without the silence after it
    out = spatial.render_moving("stereo", burst, 90, 270, 0.04, pieces=6)
    assert out.shape[0] > 0 and out.shape[1] == 2
    n = len(out) // 6
    assert level(out[:n, 1]) > level(out[:n, 0])           # starts on the right
    assert level(out[-n:, 0]) > level(out[-n:, 1])         # ends on the left


def test_wav_bytes_are_a_valid_stereo_file(noise):
    with wave.open(io.BytesIO(spatial.to_wav_bytes(spatial.stereo(noise, 0, 0.1)))) as w:
        assert w.getnchannels() == 2 and w.getframerate() == spatial.RATE
