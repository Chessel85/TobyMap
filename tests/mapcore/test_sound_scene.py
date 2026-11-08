"""The sound scene (P2-T6a; SON-1, SON-2, SON-9, AD-10, DP80, DP100, DP137).

The core works out each sound's direction relative to ahead, loudness, pitch and muffling.
No sound device is opened.
"""
import math

import pytest

from mapcore.geo import geodesy
from mapcore.session import MapSession
from mapcore.sound import CurveSettings, gain
from mapcore.sound.scene import BEHIND_PITCH, VOICE_BEHIND_PITCH, place


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 0.0, "lon": 0.0, "zoom_m": 100000, "step_m": 1000})
    s.start()
    yield s
    s.store.close()


def east_of(s, metres):
    """A point due east of the location, metres away."""
    return 0.0, metres / geodesy.parallel_radius_m(0.0) * 180 / math.pi


def test_a_sound_at_90_degrees_is_to_the_right_in_north_fixed(session):
    p = session.place_sound("ding", *east_of(session, 10_000))
    assert p["relative_deg"] == pytest.approx(90, abs=0.01) and p["pan"] == pytest.approx(1.0)
    assert not p["behind"] and p["pitch"] == 1.0


@pytest.mark.parametrize("orientation", ["cardinal", "free"])
def test_facing_90_degrees_it_is_straight_ahead_in_either_facing_orientation(session, orientation):
    session.world.set_orientation(orientation)
    session.world.face(90.0)
    p = session.place_sound("ding", *east_of(session, 10_000))
    assert p["relative_deg"] == pytest.approx(0, abs=0.01) and p["pan"] == pytest.approx(0, abs=1e-4)


def test_a_sound_at_half_the_hearing_range_is_equally_loud_at_every_zoom(session):
    gains = set()
    for zoom in (1000, 25000, 1000000):
        session.world.zoom_index = session.world.zoom_list.index(zoom)
        p = session.place_sound("ding", *east_of(session, zoom / 2))
        gains.add(round(p["gain"], 3))
    assert len(gains) == 1


def test_no_sound_is_quieter_than_the_minimum_and_beyond_the_view_it_is_at_the_minimum_and_muffled(session):
    session.run("settings.set", field="min_volume", value=30)
    within = session.place_sound("ding", *east_of(session, 99_000))
    beyond = session.place_sound("ding", *east_of(session, 300_000))
    assert within["gain"] >= 0.3 and not within["beyond"]
    assert beyond["beyond"] and beyond["gain"] == pytest.approx(0.3)
    assert beyond["cutoff_hz"] < within["cutoff_hz"]
    assert beyond["sound"] == "ding"
    session.run("settings.set", field="sound_curve", value="log")
    assert session.place_sound("ding", *east_of(session, 99_000))["gain"] >= 0.3


def test_beyond_the_view_can_be_the_fixed_tone(session):
    session.run("settings.set", field="beyond_view", value="tone")
    beyond = session.place_sound("ding", *east_of(session, 300_000))
    assert beyond["sound"] == "beyond_view" and beyond["file"]["default"] == "beyond-view.wav"
    assert session.place_sound("ding", *east_of(session, 5_000))["sound"] == "ding"


@pytest.mark.parametrize("mode", ["stereo", "hrtf"])
def test_a_sound_behind_has_the_lower_pitch_and_slight_muffling_in_both_modes(session, mode):
    session.run("settings.set", field="sound_mode", value=mode)
    ahead = session.place_sound("ding", 0.05, 0.0)
    behind = session.place_sound("ding", -0.05, 0.0)
    assert behind["behind"] and behind["pitch"] == BEHIND_PITCH and behind["mode"] == mode
    assert ahead["pitch"] == 1.0 and behind["cutoff_hz"] < ahead["cutoff_hz"]
    assert behind["gain"] == pytest.approx(ahead["gain"])


def test_three_semitones_lower():
    assert BEHIND_PITCH == pytest.approx(2 ** (-3 / 12), abs=0.005)


def test_the_voice_behind_is_one_and_a_half_semitones_lower():
    """The PO's choice on 8 November 2026 (P2-T16g); other sounds stay three semitones lower."""
    assert VOICE_BEHIND_PITCH == pytest.approx(2 ** (-1.5 / 12), abs=0.001)
    assert place("voice", 180.0, 10.0, 0.0, 100.0).pitch == VOICE_BEHIND_PITCH
    assert place("ding", 180.0, 10.0, 0.0, 100.0).pitch == BEHIND_PITCH


def test_the_curve_is_the_linear_one_by_default_from_full_to_the_minimum():
    c = CurveSettings()
    p = place("ding", 0, 0, 0, 1000, c)
    assert p.gain == 1.0
    assert place("ding", 0, 1000, 0, 1000, c).gain == pytest.approx(c.min_gain)
    assert place("ding", 0, 525, 0, 1000, c).gain == pytest.approx(gain(0.525, c))


def test_mute_drops_placed_sounds(session):
    from mapcore.session import Response

    session.settings.set("mute", True)
    r = Response(sounds=[session.place_sound("ding", 0.05, 0.0)])
    assert session._record("x", r).sounds == []


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        place("ding", 0, 0, 0, 1000, mode="surround")
