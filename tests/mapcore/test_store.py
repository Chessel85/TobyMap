"""The store: "where am I" and Nearby, on the test pack (P1-T5; LOC-2, LOC-6, INF-3, INF-7, NFR-1, NFR-4)."""
import time

import numpy as np
import pytest
import shapely

from mapcore.geo import geodesy
from mapcore.packs import coords, tiles
from mapcore.packs.pack import Pack
from mapcore.packs.source import MemorySource
from mapcore.store import Store

MILE = 1609.344
NIAGARA_CANADA = (43.08, -79.08)


@pytest.fixture(scope="module")
def store(test_pack):
    s = Store([test_pack])
    yield s
    s.close()


def names(areas):
    return [a.name for a in areas]


# Where am I ---------------------------------------------------------------------

def test_niagara_canadian_side_is_listed_smallest_first(store):
    areas = store.at(*NIAGARA_CANADA)
    assert names(areas) == ["Niagara Region", "Ontario", "Canada"]
    assert [a.layer for a in areas] == ["counties", "regions", "countries"]


def test_niagara_american_side(store):
    assert names(store.at(43.08, -79.0)) == ["Niagara County", "New York", "United States"]


def test_isle_of_wight_and_the_sea_off_it(store):
    assert names(store.at(50.7, -1.3)) == ["Isle of Wight", "England", "United Kingdom"]
    assert names(store.at(50.5, 1.0)) == ["North Atlantic Ocean"]


@pytest.mark.parametrize("lon", [179.99, 180.0, -179.99])
def test_fiji_on_either_side_of_the_180_degree_line(store, lon):
    areas = store.at(-16.5, lon)
    assert names(areas)[-1] == "Fiji"
    assert [a.layer for a in areas] == ["counties", "regions", "countries"]


def test_the_south_pole_and_near_it(store):
    for lat, lon in [(-90.0, 0.0), (-90.0, 123.0), (-89.9, 120.0), (-86.5, -170.0)]:
        assert names(store.at(lat, lon)) == ["Antarctica"], (lat, lon)


def test_the_store_agrees_with_a_slow_check_of_every_stored_part(store):
    """Where am I, for a grid of points in each sample's box, against Shapely on every entry of every pack tile."""
    pack = store.packs[0]
    parts = []  # (feature number, shape or the tile's box)
    for key in pack.keys():
        if key.startswith("tile/"):
            _t, level, x, y = key.split("/")
            for entry in pack.tile(int(level), int(x), int(y)):
                if entry.kind not in tiles.AREA_KINDS:
                    continue   # lines and points have no inside (P2-T10a)
                if entry.kind == tiles.COVERED:
                    parts.append((entry.feature, shapely.box(*tiles.tile_box(int(level), int(x), int(y)))))
                else:
                    parts.append((entry.feature, coords.to_shape(entry.data)))
    boxes = [(50.0, 51.2, -2.0, 1.6), (43.0, 43.2, -79.2, -78.9), (-17.5, -16.0, 179.0, 180.0),
             (-17.5, -16.0, -180.0, -179.0), (65.0, 66.5, -170.0, -168.0), (-90.0, -86.0, -20.0, 20.0)]
    checked = 0
    for south, north, west, east in boxes:
        for lat in np.linspace(south, north, 9):
            for lon in np.linspace(west, east, 9):
                want = {n for n, shape in parts if shapely.intersects_xy(shape, float(lon), float(lat))}
                got = {a.number for a in store.at(float(lat), float(lon))}
                assert got == want, (lat, lon)
                checked += 1
    assert checked == 6 * 81


def test_a_layer_can_be_asked_for_on_its_own(store):
    assert names(store.at(*NIAGARA_CANADA, layers={"countries"})) == ["Canada"]


def test_ties_in_rank_go_to_the_smaller_area(store):
    areas = store.at(*NIAGARA_CANADA)
    keys = [(-a.rank, a.area_km2) for a in areas]
    assert keys == sorted(keys)


def test_feature_by_identifier(store):
    area = store.feature("osm:r1428125")
    assert area.name == "Canada" and area.layer == "countries"
    assert store.feature("osm:none") is None


# Nearby ----------------------------------------------------------------------------

def test_the_usa_is_under_a_mile_from_the_canadian_side_of_niagara_falls(store):
    near = {n.area.name: n for n in store.nearby(*NIAGARA_CANADA, radius_m=50_000)}
    usa = near["United States"]
    assert usa.distance_m < MILE
    assert not usa.inside
    assert 45 < usa.bearing_deg < 135  # to the east
    assert near["Canada"].inside and near["Canada"].distance_m == 0.0
    assert (near["Canada"].lat, near["Canada"].lon) == NIAGARA_CANADA


def test_nearby_is_nearest_first_and_limited(store):
    near = store.nearby(*NIAGARA_CANADA, radius_m=300_000, limit=5)
    assert len(near) == 5
    d = [n.distance_m for n in near]
    assert d == sorted(d)


def test_nearby_stays_within_the_radius(store):
    near = store.nearby(*NIAGARA_CANADA, radius_m=10_000, limit=50)
    assert near and all(n.distance_m <= 10_000 for n in near)


def test_nearby_can_leave_some_areas_out(store):
    near = store.nearby(*NIAGARA_CANADA, radius_m=50_000, exclude={"osm:r148838"}, layers={"countries"})
    assert [n.area.name for n in near] == ["Canada"]


def _brute_nearest(store, identifier, lat, lon):
    """The nearest vertex of an area, over all its stored parts, by exact geodesic distance."""
    area = store.feature(identifier)
    pack = store.packs[0]
    best = None
    for level in pack.tile_levels:
        for key in pack.keys():
            if not key.startswith(f"tile/{level}/"):
                continue
            _t, _l, x, y = key.split("/")
            for entry in pack.tile(level, int(x), int(y)):
                if entry.feature != area.number or entry.kind != tiles.COMPACT:
                    continue
                pts = coords.to_shape(entry.data)
                for lo, la in shapely.get_coordinates(pts):
                    d = geodesy.distance_m(lat, lon, la, lo)
                    best = d if best is None or d < best else best
    return best


def test_nearest_point_agrees_with_the_nearest_vertex(store):
    # South of the Isle of Wight, in the sea, and from a shore point in Niagara Falls.
    for identifier, lat, lon in [("osm:r154350", 50.45, -1.3), ("osm:r148838", 43.06, -79.12)]:
        near = {n.area.id: n for n in store.nearby(lat, lon, radius_m=100_000, limit=50)}
        want = _brute_nearest(store, identifier, lat, lon)
        got = near[identifier].distance_m
        # A vertex is never nearer than the edge it is on; the samples have a vertex every 10 to 100 m.
        assert got <= want + 1.0
        assert got >= want - 150.0


def test_nearest_point_is_on_the_ellipsoid_distance(store):
    near = next(n for n in store.nearby(50.45, -1.3, radius_m=100_000, limit=5) if not n.inside)
    d, b, _ = geodesy.inverse(50.45, -1.3, near.lat, near.lon)
    assert near.distance_m == pytest.approx(d, abs=0.01)
    assert near.bearing_deg == pytest.approx(b, abs=0.01)


def test_nearby_across_the_180_degree_line(store):
    # In the sea 0.2 degrees from the line, Fiji's islands on both sides are reached.
    near = store.nearby(-15.0, 180.0, radius_m=300_000, limit=10, layers={"countries"})
    assert [n.area.name for n in near] == ["Fiji"]
    assert 60_000 < near[0].distance_m < 100_000
    assert near[0].lon < -179.0  # the nearest point is across the line, on the far side
    east = store.nearby(-15.0, -179.9, radius_m=300_000, layers={"countries"})
    west = store.nearby(-15.0, 179.9, radius_m=300_000, layers={"countries"})
    assert east and west


def test_a_country_past_the_far_meridian_is_not_brought_close(store):
    # Russia runs from 19 degrees east past the 180 degree line. Seen from the middle
    # of the Atlantic, its far end is beyond the meridian opposite, which once made a
    # false edge across the flat view and put Russia 1,600 km away, due north at sea.
    near = [n for n in store.nearby(45.0, -30.0, 6_000_000, limit=500) if n.area.name == "Russia"]
    assert near and 3_500_000 < near[0].distance_m < 3_800_000
    assert near[0].lon > 19.0   # Kaliningrad, its nearest part


def test_nearby_at_the_south_pole(store):
    near = store.nearby(-90.0, 0.0, radius_m=50_000)
    assert [n.area.name for n in near] == ["Antarctica"] and near[0].inside


def test_nearby_near_the_south_pole_finds_the_nearest_edge_of_the_sample(store):
    # The sample covers Antarctica south of 86 degrees south; from 85.5 south it is about 55 km away.
    near = store.nearby(-85.5, 0.0, radius_m=200_000, layers={"countries"})
    assert near and near[0].area.name == "Antarctica"


def test_nothing_near_in_the_middle_of_the_sea(store):
    assert store.nearby(0.0, -30.0, radius_m=50_000, layers={"countries"}) == []


def test_the_20_nearest_areas_come_back_within_a_second(store):
    started = time.perf_counter()
    near = store.nearby(*NIAGARA_CANADA, radius_m=4_000_000, limit=20)
    assert len(near) == 20
    assert time.perf_counter() - started < 1.0


# The tile cache ------------------------------------------------------------------------

def test_a_lookup_with_the_cache_filled_takes_a_few_milliseconds(test_pack):
    s = Store([test_pack])
    started = time.perf_counter()
    s.at(*NIAGARA_CANADA)
    cold = time.perf_counter() - started
    times = []
    for _ in range(20):
        started = time.perf_counter()
        s.at(*NIAGARA_CANADA)
        times.append(time.perf_counter() - started)
    warm = sorted(times)[len(times) // 2]
    print(f"\nwhere am I at Niagara Falls: nothing cached {cold * 1000:.1f} ms, cached {warm * 1000:.2f} ms (median)")
    assert warm < 0.005
    assert cold < 0.15  # NFR-1
    assert s.cache.hits > 0
    s.close()


def test_the_cache_keeps_to_its_size_limit_and_answers_stay_right(test_pack):
    s = Store([test_pack], cache_bytes=20_000)
    points = [NIAGARA_CANADA, (43.08, -79.0), (50.7, -1.3), (-16.5, 179.99), (-90.0, 0.0), (50.5, 1.0)]
    expected = [names(Store([test_pack]).at(*p)) for p in points]
    for _ in range(3):
        for p, want in zip(points, expected):
            assert names(s.at(*p)) == want
    big = Store([test_pack])
    for p in points:
        big.at(*p)
    assert len(s.cache) < len(big.cache)  # the small cache let tiles go
    assert s.cache.size < big.cache.size
    s.close()


def test_warm_reads_the_tiles_round_a_point(test_pack):
    s = Store([test_pack])
    assert s.warm(*NIAGARA_CANADA) > 0
    misses = s.cache.misses
    s.at(*NIAGARA_CANADA)
    assert s.cache.misses == misses
    s.close()


def test_prefetch_runs_in_the_background(test_pack):
    s = Store([test_pack])
    thread = s.prefetch(*NIAGARA_CANADA)
    assert thread is not None
    thread.join(10)
    assert len(s.cache) > 0 and names(s.at(*NIAGARA_CANADA))[-1] == "Canada"
    s.close()


# A damaged record (NFR-4) -----------------------------------------------------------------

def test_a_damaged_tile_is_reported_and_the_store_carries_on(test_pack):
    data = bytearray(test_pack.read_bytes())
    clean = Pack(MemorySource(bytes(data), "test.pack"))
    level = max(L for L in clean.tile_levels
                if tiles.tile_key(L, *tiles.tile_of(NIAGARA_CANADA[1], NIAGARA_CANADA[0], L)) in clean.directory)
    key = tiles.tile_key(level, *tiles.tile_of(NIAGARA_CANADA[1], NIAGARA_CANADA[0], level))
    offset, length, _check = clean.directory[key]
    data[offset + length // 2] ^= 0xFF
    s = Store([Pack(MemorySource(bytes(data), "test.pack"))])
    areas = s.at(*NIAGARA_CANADA)
    assert s.problems and key in s.problems[0]
    assert "Canada" in names(areas) or "Ontario" in names(areas) or areas == []  # carries on, with what is left
    assert names(s.at(50.7, -1.3))[0] == "Isle of Wight"
    assert s.nearby(*NIAGARA_CANADA, radius_m=20_000) is not None
    assert len(s.problems) == 1  # the same record is not reported again and again


def test_the_self_check_finds_no_problems():
    from mapcore.store import selfcheck

    assert selfcheck.run() == []
