"""Spike S1: placing sounds in space, checked without any audio device (P0-T4, SON-1, SON-9)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "spikes" / "s1"))
import spatial  # noqa: E402

needs_kemar = pytest.mark.skipif(not spatial.KEMAR_ZIP.is_file(),
                                 reason="MIT KEMAR data not downloaded (python tools/spikes/s1/demo.py --fetch)")


def energy(x):
    return float(np.sum(x.astype(np.float64) ** 2))


def test_distance_gain_follows_son9():
    assert spatial.distance_gain_db(0.01) == 0
    assert spatial.distance_gain_db(0.05) == 0
    assert spatial.distance_gain_db(1.0) == spatial.QUIET_DB
    assert spatial.distance_gain_db(3.0) == spatial.QUIET_DB
    # Each doubling is equally quieter.
    d1 = spatial.distance_gain_db(0.1) - spatial.distance_gain_db(0.2)
    d2 = spatial.distance_gain_db(0.2) - spatial.distance_gain_db(0.4)
    assert d1 == pytest.approx(d2)
    # Halfway to the edge sounds the same at every zoom: it depends only on the fraction.
    assert spatial.distance_gain_db(0.5) == pytest.approx(spatial.QUIET_DB * math.log2(10) / math.log2(20))


def test_muffling_grows_with_distance_and_is_strongest_beyond_the_view():
    cut = [spatial.muffle_cutoff_hz(f) for f in (0.02, 0.1, 0.5, 1.0, 2.0)]
    assert cut == sorted(cut, reverse=True)
    assert cut[0] == spatial.BRIGHT_HZ and cut[-1] == spatial.BEYOND_HZ


def test_far_sounds_are_quieter_and_duller():
    mono = spatial.noise_bursts()
    near = spatial.render("stereo", mono, 0, 0.05)
    far = spatial.render("stereo", mono, 0, 0.9)
    assert energy(far) < energy(near) / 100


@pytest.mark.parametrize("bearing, louder", [(90, "right"), (270, "left"), (45, "right"), (300, "left")])
def test_stereo_pans_to_the_side(bearing, louder):
    out = spatial.render("stereo", spatial.noise_bursts(), bearing)
    left, right = energy(out[:, 0]), energy(out[:, 1])
    assert (right > left) if louder == "right" else (left > right)


def test_stereo_pitches_sounds_behind_lower():
    mono = spatial.chime()
    ahead = spatial.render("stereo", mono, 10)
    behind = spatial.render("stereo", mono, 170)
    assert len(behind) > len(ahead)  # played slower, so lower


@needs_kemar
@pytest.mark.parametrize("bearing, louder", [(90, "right"), (270, "left"), (60, "right"), (200, "left")])
def test_hrtf_reaches_the_nearer_ear_more(bearing, louder):
    out = spatial.render("hrtf", spatial.noise_bursts(), bearing)
    left, right = energy(out[:, 0]), energy(out[:, 1])
    assert (right > 2 * left) if louder == "right" else (left > 2 * right)


@needs_kemar
def test_hrtf_ahead_is_balanced_and_left_mirrors_right():
    k = spatial.kemar()
    ahead = k.response(0)
    assert energy(ahead[:, 0]) == pytest.approx(energy(ahead[:, 1]), rel=0.35)
    assert np.allclose(k.response(90), k.response(270)[:, ::-1])
    assert np.allclose(k.response(3), k.response(5))  # nearest 5 degrees


@needs_kemar
def test_render_shape():
    out = spatial.render("hrtf", spatial.chime(), 135, 0.3)
    assert out.dtype == np.float32 and out.ndim == 2 and out.shape[1] == 2
    assert np.abs(out).max() < 1.0


@needs_kemar
def test_hrtf_pitch_lowers_only_sounds_behind():
    tone = spatial.chime()
    ahead = spatial.render("hrtf_pitch", tone, 45)
    behind = spatial.render("hrtf_pitch", tone, 135)
    assert len(ahead) == len(spatial.render("hrtf", tone, 45))
    assert len(behind) > len(ahead)  # played slower, so lower and longer


import openal  # noqa: E402

needs_openal = pytest.mark.skipif(not openal.available(), reason="OpenAL Soft is not in tools/spikes/s1/vendor")


@needs_openal
@pytest.mark.parametrize("bearing, louder", [(90, 1), (270, 0), (45, 1), (315, 0)])
def test_openal_renders_in_memory_with_hrtf(bearing, louder):
    # Loopback rendering: no sound device is opened.
    al = openal.shared(spatial.RATE)
    assert al.hrtf_enabled
    out = spatial.render("openal", spatial.chime(), bearing)
    assert out.shape[1] == 2 and np.abs(out).max() < 1
    assert energy(out[:, louder]) > 1.5 * energy(out[:, 1 - louder])


@needs_openal
def test_openal_ahead_and_behind_are_balanced_but_differ():
    tone = spatial.chime()
    ahead, behind = spatial.render("openal", tone, 0), spatial.render("openal", tone, 180)
    for x in (ahead, behind):
        assert abs(energy(x[:, 0]) - energy(x[:, 1])) < 0.01 * energy(x)
    assert not np.allclose(ahead, behind)


import synth  # noqa: E402

needs_synthizer = pytest.mark.skipif(not synth.available(), reason="Synthizer is not built (tools/spikes/s1/build_synthizer.ps1)")


@needs_synthizer
def test_synthizer_gets_a_mono_sound_with_distance_applied_and_no_device_opened():
    tone = spatial.chime()
    near = spatial.render("synthizer", tone, 90, 0.05)
    far = spatial.render("synthizer", tone, 90, 1.0)
    assert isinstance(near, synth.Live) and near.bearing == 90 and near.rate == spatial.RATE
    assert near.shape == (len(tone), 2)
    assert energy(far.mono) < energy(near.mono) / 100  # 30 dB quieter, and muffled
    assert near.setup == "atmap"
    assert spatial.render("synthizer_angular", tone, 90, 0.05).setup == "angular"
    assert synth._player is None  # nothing played, so Synthizer was never started
