"""Islands (P3-T1d, DP169): the land named with its island in the grid squares, and the join's naming of land
that no island area covers. On small made-up shapes, so no file is read."""
from __future__ import annotations

import shapely

from mapdata.stages import grid, join
from mapdata.stages.osm_areas import island_record


def meta(kind, fid, area, country=None, level=None):
    return grid.Meta(kind, fid, country, level, float(area.area))


def test_land_is_named_with_the_smallest_island_area_it_is_in():
    country = shapely.box(0, 0, 1, 1)
    big = shapely.box(0.1, 0.1, 0.9, 0.9)
    lake_island = shapely.box(0.4, 0.4, 0.5, 0.5)
    m = [meta("country", "c", country), meta("island", "big", big), meta("island", "small", lake_island)]
    rules = grid.Rules(islands=True)
    assert grid.label_land([0, 1, 2], m, rules, [], [], 1.0) == ("land", "c", None, None, "small")
    assert grid.label_land([0, 1], m, rules, [], [], 1.0) == ("land", "c", None, None, "big")
    assert grid.label_land([0], m, rules, [], [], 1.0) == ("land", "c", None, None, None)


def test_without_islands_the_labels_are_as_before():
    country = shapely.box(0, 0, 1, 1)
    m = [meta("country", "c", country)]
    assert grid.label_land([0], m, grid.Rules(), [], [], 1.0) == ("land", "c", None)


def test_with_island_puts_the_island_fifth():
    assert grid.with_island(("land", "c", "r"), "i") == ("land", "c", "r", None, "i")
    assert grid.with_island(("land", "c", "r", "k"), "i") == ("land", "c", "r", "k", "i")
    assert grid.with_island(("land", "c", "r", "k", "old"), "i") == ("land", "c", "r", "k", "i")
    assert grid.with_island(("land", "c", "r"), None) == ("land", "c", "r")
    assert grid.island_in(("land", "c", "r", None, "i")) == "i"
    assert grid.island_in(("water", "o", None, "s")) is None


def test_a_square_names_the_island_and_keeps_it_on_land_in_no_country():
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = shapely.union(shapely.box(0.1, 0.1, 0.3, 0.3), shapely.box(0.6, 0.6, 0.8, 0.8))
    country = shapely.box(0, 0, 0.5, 0.5)
    isl_a = shapely.box(0.05, 0.05, 0.35, 0.35)
    isl_b = shapely.box(0.55, 0.55, 0.85, 0.85)
    ocean = shapely.box(0, 0, 1, 1)
    m = [meta("country", "c", country), meta("island", "a", isl_a), meta("island", "b", isl_b),
         meta("ocean", "o", ocean)]
    r = grid.build_square(bounds, land, [(0, country), (1, isl_a), (2, isl_b), (3, ocean)], m,
                          grid.Rules(islands=True), 1.0)
    assert ("land", "c", None, None, "a") in r.labels
    assert ("land", None, None, None, "b") in r.labels   # waiting land in no country keeps its island


def _deg_km2(km2):
    """The side in degrees, at the equator, of a square of this many km2."""
    return (km2 ** 0.5) / (grid.METRES_PER_DEGREE / 1000)


def test_a_landmass_with_no_island_area_of_1_km2_or_more_is_an_unnamed_island():
    d = _deg_km2(4)
    shapes = {("land", "c", None, None, None): [shapely.box(10, 0, 10 + d, d)]}
    records, _ = join.name_islands(shapes, {}, say=lambda _t: None)
    (iid, rec), = records.items()
    assert rec["name"] == join.UNNAMED_ISLAND
    assert ("land", "c", None, None, iid) in shapes


def test_a_landmass_under_1_km2_with_no_name_has_no_island():
    d = _deg_km2(0.5)
    shapes = {("land", "c", None, None, None): [shapely.box(10, 0, 10 + d, d)]}
    records, _ = join.name_islands(shapes, {}, say=lambda _t: None)
    assert records == {}
    assert list(shapes) == [("land", "c", None, None, None)]


def test_an_island_point_names_the_landmass_whatever_its_size():
    d = _deg_km2(0.5)
    by_id = {"osm:n1": {**island_record("osm:n1", {"name": "Skär"}, "islet"), "kind": "island point",
                        "point": [10 + d / 2, d / 2]}}
    shapes = {("land", "c", None, None, None): [shapely.box(10, 0, 10 + d, d)]}
    records, _ = join.name_islands(shapes, by_id, say=lambda _t: None)
    assert records["osm:n1"]["name"] == "Skär"
    assert ("land", "c", None, None, "osm:n1") in shapes


def test_land_left_by_a_short_island_outline_takes_that_island():
    d = _deg_km2(100)
    shapes = {("land", "c", None, None, "osm:w1"): [shapely.box(0, 0, d * 0.9, d)],
              ("land", "c", None, None, None): [shapely.box(d * 0.9, 0, d, d)]}
    join.name_islands(shapes, {}, say=lambda _t: None)
    assert set(shapes) == {("land", "c", None, None, "osm:w1")}


def test_an_island_across_a_border_is_one_island_in_both_countries():
    d = _deg_km2(4)
    shapes = {("land", "se", None, None, None): [shapely.box(0, 0, d / 2, d)],
              ("land", "fi", None, None, None): [shapely.box(d / 2, 0, d, d)]}
    records, _ = join.name_islands(shapes, {}, say=lambda _t: None)
    (iid,) = records
    assert set(shapes) == {("land", "se", None, None, iid), ("land", "fi", None, None, iid)}


def test_a_continent_is_no_island_but_keeps_its_named_islands():
    d = _deg_km2(join.CONTINENT_KM2 * 1.2) / 2
    big = [shapely.box(0, 0, d, d), shapely.box(d, 0, 2 * d, d), shapely.box(0, d, d, 2 * d),
           shapely.box(d, d, 2 * d, 2 * d)]
    shapes = {("land", "c", None, None, None): big,
              ("land", "c", None, None, "osm:w9"): [shapely.box(2 * d, 0, 2 * d + 0.01, 0.01)]}
    records, _ = join.name_islands(shapes, {}, say=lambda _t: None)
    assert records == {}
    assert ("land", "c", None, None, None) in shapes and ("land", "c", None, None, "osm:w9") in shapes


def test_touching_islands_are_neighbours_for_the_colours():
    d = _deg_km2(4)
    shapes = {("land", "c", None, None, "a"): [shapely.box(0, 0, d, d)],
              ("land", "c", None, None, "b"): [shapely.box(d, 0, 2 * d, d)]}
    _records, pairs = join.name_islands(shapes, {}, say=lambda _t: None)
    assert pairs == {("a", "b")}


def test_an_island_with_the_id_of_a_region_gets_an_ending_so_every_id_is_different():
    from mapdata.stages import grid, join
    records = [
        {"id": "osm:r1", "layer": "regions"},
        {"id": "osm:r1", "layer": "islands"},
        {"id": "osm:r2", "layer": "islands"},
        {"id": "osm:r3", "layer": "counties"},
        {"id": "osm:r3", "layer": "islands"},
    ]
    join.keep_ids_unique(records)
    ids = [r["id"] for r in records]
    assert ids == ["osm:r1", "osm:r1" + grid.ISLAND_ALSO_AREA_SUFFIX, "osm:r2", "osm:r3",
                   "osm:r3" + grid.ISLAND_ALSO_AREA_SUFFIX]
    assert len(set(ids)) == len(ids)
