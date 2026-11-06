"""The visible rule (P2-T4a; NAV-13, SCP-7, ANN-7, DP80, architecture 7.4).

A feature is visible when its layer is on, the zoom is within the layer's zoom
range, an area is at least the layer's minimum size, and at least part of it is
within the view, the circle round you whose radius is the zoom.
"""
import math
import random
import time

import numpy as np
import pytest

from mapcore.geo import geodesy
from mapcore.layers.catalogue import from_definition
from mapcore.layers.visible import VisibleRule, box_reach
from mapcore.session import MapSession
from mapcore.world.state import nearest_index
from tests.world_pack import world_pack_path

KENT = (51.2, 1.2)
LUXEMBOURG = (49.75, 6.1)


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": KENT[0], "lon": KENT[1], "zoom_m": 25000, "step_m": 25000})
    s.start()
    yield s
    s.store.close()


def names(session, lat, lon, zoom_m) -> set:
    return {session.store.feature(i).name for i in session.visible.features(lat, lon, zoom_m)}


# The tests from the plan -------------------------------------------------------

def test_france_is_out_of_view_from_kent_at_10_km_and_in_view_at_100_km(session):
    assert "France" not in names(session, *KENT, 10_000)
    assert "Kent" in names(session, *KENT, 10_000)
    assert "France" in names(session, *KENT, 100_000)


def test_luxembourg_is_too_small_at_5000_km_but_where_am_i_still_names_it(session):
    assert "Luxembourg" not in names(session, *LUXEMBOURG, 5_000_000)
    assert "France" in names(session, *LUXEMBOURG, 5_000_000)
    assert "Luxembourg" in names(session, *LUXEMBOURG, 500_000)
    assert "Luxembourg" in [a.name for a in session.store.at(*LUXEMBOURG)]   # ANN-7: never limited


@pytest.mark.parametrize("lon", [179.6, -179.6])
def test_fiji_across_the_180_degree_line_is_in_view_from_both_sides(session, lon):
    lat = -17.0
    fiji = session.store.feature("osm:r571747")
    near = [n for n in session.store.nearby(lat, lon, 2_000_000, limit=200) if n.area.id == fiji.id][0]
    assert near.distance_m > 20_000
    assert fiji.id in session.visible.features(lat, lon, near.distance_m * 1.2)
    assert fiji.id not in session.visible.features(lat, lon, near.distance_m * 0.8)


def test_at_the_poles(session):
    south = names(session, -90.0, 0.0, 1_000_000)
    assert "Antarctica" in south
    assert "Antarctica" in names(session, -89.0, 120.0, 25_000)
    assert "Fiji" not in south


# The view agrees with Nearby's distances ----------------------------------------

@pytest.mark.parametrize("lat, lon, zoom_km", [(51.2, 1.2, 60), (50.0, -3.0, 200), (-17.0, 178.0, 400),
                                                (65.0, -170.0, 300), (45.0, -30.0, 3000)])
def test_in_view_matches_the_distance_nearby_measures(session, lat, lon, zoom_km):
    zoom_m = zoom_km * 1000.0
    rule = session.visible
    seen = rule.features(lat, lon, zoom_m)
    for near in session.store.nearby(lat, lon, zoom_m * 2, limit=500):
        area = near.area
        if not rule.passes(area.record, zoom_m):
            continue
        # A drawing shape may be up to its tolerance away from the exact one, so a
        # band round the edge of the view is left out of the comparison.
        if near.distance_m < zoom_m * 0.9:
            assert area.id in seen, (area.name, near.distance_m)
        elif near.distance_m > zoom_m * 1.1:
            assert area.id not in seen, (area.name, near.distance_m)


# The first three tests ----------------------------------------------------------

def test_a_layer_that_is_off_or_outside_its_zoom_range_is_not_visible(session):
    assert "Kent" in names(session, *KENT, 50_000)
    session.layers.change("counties", "on", False)
    assert "Kent" not in names(session, *KENT, 50_000)
    assert "counties" not in session.visible.shown_layers(50_000)
    session.layers.change("counties", "on", True)
    session.layers.change("counties", "max_zoom_m", 40_000)
    assert "Kent" not in names(session, *KENT, 50_000)
    assert "Kent" in names(session, *KENT, 40_000)
    session.layers.change("counties", "min_zoom_m", 20_000)
    assert "Kent" not in names(session, *KENT, 10_000)


def test_the_size_rule_is_for_areas_only():
    area = from_definition({"id": "fields", "name": "Fields"})
    line = from_definition({"id": "rivers", "name": "Rivers", "geometry": "line"})
    big = from_definition({"id": "lakes", "name": "Lakes", "min_size": 0.1})
    record = {"width_km": 1.0}
    assert VisibleRule.big_enough(area, record, 50_000)          # 1 km against 2% of 50 km
    assert not VisibleRule.big_enough(area, record, 51_000)
    assert VisibleRule.big_enough(line, record, 10_000_000)      # a line has no size rule
    assert not VisibleRule.big_enough(big, record, 11_000)       # its own minimum size
    assert VisibleRule.big_enough(area, {}, 10_000_000)          # a record with no width is never left out


# The reach of a box -----------------------------------------------------------------

def _angle(lat1, lon1, lat2, lon2):
    p1, p2, dl = np.radians(lat1), np.radians(lat2), np.radians(np.asarray(lon2) - lon1)
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dl)
    return np.arccos(np.clip(c, -1, 1))


def test_the_nearest_and_farthest_reach_of_a_box_match_a_dense_sample():
    rng = random.Random(7)
    boxes, points = [], []
    for _ in range(300):
        south = rng.uniform(-90, 85)
        north = min(90.0, south + rng.uniform(0.1, 60))
        west = rng.uniform(-180, 180)
        east = geodesy.wrap_lon(west + rng.uniform(0.1, 200))
        boxes.append((west, south, east, north))
        points.append((rng.uniform(-90, 90), rng.uniform(-180, 180)))
    boxes.append((-180.0, -90.0, 180.0, -60.0))    # round the whole world, as Antarctica's
    points.append((-75.0, 33.0))
    boxes.append((177.0, -21.0, -178.0, -12.0))     # across the 180 degree line, as Fiji's
    points.append((-17.0, 179.9))
    for (west, south, east, north), (lat, lon) in zip(boxes, points):
        near, far = box_reach(np.array([[west, south, east, north]]), lat, lon)
        span = (east - west) % 360.0 or 360.0
        lons = west + np.linspace(0.0, span, 721)
        lats = np.linspace(south, north, 241)
        g_lat, g_lon = np.meshgrid(lats, lons)
        d = _angle(lat, lon, g_lat.ravel(), g_lon.ravel())
        assert near[0] <= d.min() + 1e-9
        assert near[0] >= d.min() - math.radians(0.35)
        assert far[0] >= d.max() - 1e-9
        assert far[0] <= d.max() + math.radians(0.35)


# Speed ----------------------------------------------------------------------------------

def test_the_rule_takes_under_5_ms_a_frame_on_the_world_pack():
    pack = world_pack_path()
    if pack is None:
        pytest.skip("the world pack is not built on this computer")
    s = MapSession(packs=[pack], saved_state={"lat": 50.0, "lon": 5.0, "zoom_m": 250_000, "step_m": 50_000})
    s.start()
    start = time.perf_counter()
    s.store._indexes[0].boxes          # once a session, shared with Nearby
    table_ms = (time.perf_counter() - start) * 1000
    times = []
    for lat, lon, zoom_km in [(50.0, 5.0, 250), (50.2, 5.4, 250), (-17.0, 179.9, 500), (-80.0, 0.0, 1000),
                              (40.0, -100.0, 5000), (51.0, 0.0, 10), (51.05, 0.1, 10), (0.0, 0.0, 2500)]:
        s.world.lat, s.world.lon = lat, lon
        s.world.zoom_index = nearest_index(s.world.zoom_list, zoom_km * 1000.0)
        s.scene(1000, 700)                       # the drawing reads the tiles, as it does before the rule is asked
        start = time.perf_counter()
        s.visible.features(lat, lon, s.world.zoom_m)
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    print(f"the visible rule on the world pack: median {times[len(times) // 2]:.2f} ms, slowest {times[-1]:.2f} ms, "
          f"after reading the feature table once in {table_ms:.0f} ms")
    assert times[len(times) // 2] < 5.0
