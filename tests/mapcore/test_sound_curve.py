"""The distance curve (P1-T13, SON-9). Linear, with a minimum volume (PO's answer to DP137)."""
import pytest
import yaml

from mapcore.session import DEFAULTS_FILE
from mapcore.sound import CurveSettings, distance_gain_db, gain, muffle_cutoff_hz


def test_full_loudness_at_a_twentieth_of_the_range_or_closer():
    assert distance_gain_db(0.0) == 0 and distance_gain_db(0.05) == 0 and gain(0.03) == 1.0


def test_the_loudness_falls_in_a_straight_line_to_the_minimum_at_the_edge():
    s = CurveSettings()
    assert s.model == "linear"
    assert gain(1.0) == pytest.approx(s.min_gain)
    assert gain((0.05 + 1.0) / 2) == pytest.approx((1.0 + s.min_gain) / 2)
    steps = [gain(0.05 + 0.19 * k) for k in range(6)]
    drops = [a - b for a, b in zip(steps, steps[1:])]
    assert all(d == pytest.approx(drops[0]) for d in drops)


def test_no_sound_drops_below_the_minimum_volume():
    s = CurveSettings()
    for fraction in (0.5, 1.0, 1.5, 3.0, 100.0):
        assert gain(fraction) >= s.min_gain - 1e-12
    assert gain(1.5) == pytest.approx(s.min_gain)          # beyond the view: the minimum, and muffled
    log = CurveSettings(model="log", edge_db=-60.0)
    assert gain(1.0, log) == pytest.approx(log.min_gain)    # the floor holds in the other model too


def test_beyond_the_view_is_muffled():
    assert muffle_cutoff_hz(1.5) < muffle_cutoff_hz(1.0) < muffle_cutoff_hz(0.5) < muffle_cutoff_hz(0.05)


def test_the_other_model_halves_equally_for_each_doubling():
    log = CurveSettings(model="log", min_gain=0.01)       # a low minimum, so it does not cut in
    steps = [distance_gain_db(0.05 * 2 ** k, log) for k in range(0, 4)]
    drops = [b - a for a, b in zip(steps, steps[1:])]
    assert all(d == pytest.approx(drops[0]) for d in drops)


def test_the_curve_is_a_setting_read_from_the_defaults():
    d = yaml.safe_load(DEFAULTS_FILE.read_text(encoding="utf-8"))
    assert CurveSettings.from_defaults(d) == CurveSettings()
    quieter = CurveSettings(min_gain=0.1)
    assert gain(1.0, quieter) == pytest.approx(0.1)
