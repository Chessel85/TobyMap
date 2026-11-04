"""The distance curve (P1-T13, SON-9)."""
import math

import pytest
import yaml

from mapcore.session import DEFAULTS_FILE
from mapcore.sound import CurveSettings, distance_gain_db, gain, muffle_cutoff_hz


def test_full_loudness_at_a_twentieth_of_the_range_or_closer():
    assert distance_gain_db(0.0) == 0 and distance_gain_db(0.05) == 0 and gain(0.03) == 1.0


def test_each_doubling_is_equally_quieter_down_to_the_edge():
    steps = [distance_gain_db(0.05 * 2 ** k) for k in range(0, 5)]
    drops = [b - a for a, b in zip(steps, steps[1:])]
    assert all(d == pytest.approx(drops[0]) for d in drops)
    assert distance_gain_db(1.0) == pytest.approx(-30.0)


def test_beyond_the_view_is_quiet_and_muffled():
    assert distance_gain_db(1.5) == -36.0 < distance_gain_db(1.0)
    assert muffle_cutoff_hz(1.5) < muffle_cutoff_hz(1.0) < muffle_cutoff_hz(0.5) < muffle_cutoff_hz(0.05)


def test_the_curve_is_a_setting_read_from_the_defaults():
    d = yaml.safe_load(DEFAULTS_FILE.read_text(encoding="utf-8"))
    s = CurveSettings.from_defaults(d)
    assert s == CurveSettings()
    louder = CurveSettings(edge_db=-20.0)
    assert distance_gain_db(1.0, louder) == pytest.approx(-20.0)
    assert math.isclose(gain(1.0, louder), 0.1)
