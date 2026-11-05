import json
from pathlib import Path

import yaml

from mapcore.geo import geodesy
from mapcore.world import WorldState

DEFAULTS = yaml.safe_load((Path(__file__).parents[2] / "mapcore" / "defaults.yaml").read_text("utf-8"))


def make(**kw):
    w = WorldState.from_defaults(DEFAULTS)
    for k, v in kw.items():
        setattr(w, k, v)
    return w


def test_lists_from_defaults():
    w = make()
    assert w.zoom_list[0] == 100 and w.zoom_list[-1] == 10_000_000
    assert w.step_list[0] == 10 and w.step_list[-1] == 1_000_000
    assert (w.zoom_m, w.step_m) == (5000, 100)


def test_imperial_has_its_own_round_lists():
    """DP130, DP136: switching to imperial moves to the nearest round size, and back again."""
    from mapcore.describe import words

    w = make()
    w.use_units("imperial")
    assert [words.distance_text(z, "imperial") for z in w.zoom_list] == [
        "100 yards", "250 yards", "0.5 miles", "1 mile", "2.5 miles", "5 miles", "10 miles", "25 miles", "50 miles",
        "100 miles", "250 miles", "500 miles", "1,000 miles", "2,500 miles", "6,000 miles"]
    assert [words.distance_text(s, "imperial") for s in w.step_list] == [
        "10 yards", "25 yards", "50 yards", "100 yards", "250 yards", "0.5 miles", "1 mile", "5 miles",
        "25 miles", "100 miles", "250 miles", "600 miles"]
    assert words.distance_text(w.zoom_m, "imperial") == "2.5 miles"      # nearest to 5 kilometres
    assert words.distance_text(w.step_m, "imperial") == "100 yards"      # nearest to 100 metres
    w.use_units("metric")
    assert (w.zoom_m, w.step_m) == (5000, 100)                           # nearest to 2.5 miles and 100 yards
    w.use_units("nautical")                                              # nautical keeps the metric lists
    assert w.zoom_list[0] == 100


def test_north_south_east_west():
    w = make(lat=10.0, lon=20.0, step_index=6)  # 1 km
    r = w.step("north")
    assert r.moved and r.lat > 10 and r.lon == 20 and r.heading == 0
    r = w.step("east")
    assert r.heading == 90 and r.lon > 20
    w.step("south")
    w.step("west")
    assert abs(w.lat - 10) < 1e-3 and abs(w.lon - 20) < 1e-3


def test_wraps_across_180():
    w = make(lat=0.0, lon=179.999, step_index=6)
    assert w.step("east").moved and -180 <= w.lon < -179.9
    w.step("west")
    assert w.lon > 179.9


def test_blocked_at_poles():
    w = make(lat=89.9995, lon=0.0, step_index=6)
    assert not w.step("north").moved and w.lat == 89.9995
    w = make(lat=-90.0, lon=0.0)
    assert not w.step("east").moved
    assert not w.step("south").moved


def test_zoom_ends():
    w = make(zoom_index=0)
    assert not w.change_zoom(-1)
    assert w.change_zoom(1) and w.zoom_m == 250
    w = make(zoom_index=len(DEFAULTS["zoom_list_m"]) - 1)
    assert not w.change_zoom(1)


def test_unlinked_keeps_other():
    w = make()
    w.change_zoom(1)
    assert w.step_m == 100
    w.change_step(1)
    assert w.zoom_m == 10000


def test_link_both_ways():
    w = make(zoom_index=4)  # 2.5 km
    w.set_link(True)
    w.change_zoom(-1)  # zoom 1 km
    assert w.zoom_m == 1000 and w.step_m == 250
    w.change_step(1)  # step 500 -> four steps is 2 km -> nearest zoom 2.5 km
    assert w.step_m == 500 and w.zoom_m == 2500


def test_ten_joined_moves_end_in_the_last_place():
    w = make(lat=0.0, lon=0.0, step_index=6)
    results = w.step_many(["north"] * 10)
    assert len(results) == 10 and all(r.moved for r in results)
    assert (w.lat, w.lon) == (results[-1].lat, results[-1].lon)
    assert abs(geodesy.distance_m(0, 0, w.lat, w.lon) - 10_000) < 50


def test_save_and_restore():
    w = make(lat=12.5, lon=-179.5, zoom_index=3, step_index=8)
    d = json.loads(json.dumps(w.to_dict()))
    w2 = make()
    w2.restore(d)
    assert (w2.lat, w2.lon, w2.zoom_m, w2.step_m) == (12.5, -179.5, w.zoom_m, w.step_m)
