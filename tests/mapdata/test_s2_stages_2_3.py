"""Spike S2 stages 2 and 3 on small made-up shapes: no data folder, no network (P0-T5, AD-17, DP101)."""
import math

import numpy as np
import pytest
import shapely

from mapdata.stages import antimeridian, counties
from mapdata.stages.boundaries import Area
from mapdata.stages.geodesy import R_AUTHALIC_KM, area_km2
from mapdata.stages.s2_stage import part_boxes

# A country like Fiji: islands either side of the 180 degree line, one of
# them split by it.
WEST = shapely.box(179.0, -17.0, 180.0, -16.0)      # the part of the split island west of the line
EAST = shapely.box(-180.0, -17.0, -179.5, -16.0)    # its part east of the line
FAR_WEST = shapely.box(177.0, -18.5, 178.5, -17.5)
FIJI = shapely.MultiPolygon([FAR_WEST, WEST, EAST])


def test_wrap_box_crosses_the_line():
    box = antimeridian.wrap_box(FIJI)
    assert box.crosses
    assert box.west == pytest.approx(177.0)
    assert box.east == pytest.approx(-179.5)
    assert box.width == pytest.approx(3.5)


def test_wrap_box_of_a_shape_not_crossing_the_line():
    box = antimeridian.wrap_box(shapely.box(10, 50, 12, 52))
    assert not box.crosses
    assert (box.west, box.east, box.width) == pytest.approx((10, 12, 2))


def test_centre_is_on_the_right_side_of_the_world():
    c = antimeridian.centre(FIJI)
    # Halfway between 177 and 180.5 is 178.75, near Fiji, not 0 degrees in the Atlantic.
    assert c.lon == pytest.approx(178.75)
    assert c.lat == pytest.approx(-17.25)


def test_centre_in_the_sea_is_snapped_to_the_nearest_land():
    atolls = shapely.MultiPolygon([shapely.box(170, 0, 170.1, 0.1), shapely.box(-160, 0, -159.9, 0.1)])
    c = antimeridian.centre(atolls)
    assert not c.in_shape
    assert c.snap_km > 1000
    assert shapely.intersects(atolls.buffer(1e-9), shapely.Point(c.snapped_lon, c.snapped_lat))


def test_shape_round_the_pole_has_the_pole_as_its_centre():
    antarctica = shapely.MultiPolygon([shapely.box(-180, -90, 0, -70), shapely.box(0, -90, 180, -65)])
    box = antimeridian.wrap_box(antarctica)
    assert box.round_the_world
    c = antimeridian.centre(antarctica, box)
    assert c.lat < -89.9 and c.in_shape


def test_shifted_shape_is_one_compact_group():
    moved = antimeridian.shifted(FIJI)
    w, _s, e, _n = moved.bounds
    assert (w, e) == pytest.approx((177.0, 180.5))
    # The split island joins up again across the line.
    assert len(shapely.get_parts(moved)) == 2


def test_edges_along_the_line_match_on_both_sides():
    edges = antimeridian.line_edges(FIJI)
    assert edges.east_km == pytest.approx(111.2, rel=0.01)
    assert edges.west_km == pytest.approx(111.2, rel=0.01)
    assert edges.unmatched_km == pytest.approx(0, abs=1e-6)


def test_edges_on_one_side_only_are_found():
    broken = shapely.MultiPolygon([WEST, shapely.box(-180.0, -16.5, -179.5, -16.0)])
    assert antimeridian.line_edges(broken).unmatched_km == pytest.approx(55.6, rel=0.01)


def test_area_on_the_ellipsoid():
    # A cap round the South Pole, south of 60 degrees, against the exact
    # ellipsoid figure from the authalic latitude.
    cap = shapely.box(-180, -90, 180, -60)
    from mapdata.stages.geodesy import authalic_lat
    beta = math.radians(float(authalic_lat(np.array(-60.0))))
    exact = 2 * math.pi * R_AUTHALIC_KM ** 2 * (1 - math.sin(-beta))
    assert area_km2(cap) == pytest.approx(exact, rel=0.002)
    # Split at the line, the two halves add up to the same.
    halves = area_km2(shapely.box(-180, -90, 0, -60)) + area_km2(shapely.box(0, -90, 180, -60))
    assert halves == pytest.approx(exact, rel=0.002)


def test_area_of_a_degree_square_at_the_equator():
    # 1 degree by 1 degree at the equator on WGS 84 is about 12,308 km2.
    assert area_km2(shapely.box(0, 0, 1, 1)) == pytest.approx(12308, rel=0.001)


def test_part_boxes_join_parts_near_each_other():
    shape = shapely.MultiPolygon([shapely.box(0, 0, 1, 1), shapely.box(1.5, 0, 2, 1), shapely.box(50, 50, 51, 51)])
    boxes = part_boxes(shape, pad=0.0)
    assert len(boxes) == 2
    assert sorted(boxes)[0] == pytest.approx([0, 0, 2, 1])


# The counties rule (DP101) ------------------------------------------------

def _area(i, level, geom):
    return Area(id=f"osm:r{i}", name=f"area {i}", level=level, geom=geom)


def test_counties_gap_is_filled_from_the_next_level_then_the_region():
    country = shapely.box(0, 0, 3, 1)
    # Level 6 covers the west third only; level 7 has the middle third and a
    # small area inside level 6's land, which must not be used; nothing
    # covers the east third, so its region is used.
    l6 = [_area(1, 6, shapely.box(0, 0, 1, 1))]
    l7 = [_area(2, 7, shapely.box(1, 0, 2, 1)), _area(3, 7, shapely.box(0.2, 0.2, 0.4, 0.4))]
    regions = [(_area(9, 4, shapely.box(0, 0, 3, 1)), shapely.box(0, 0, 3, 1))]
    res = counties.build(country, regions, {6: l6, 7: l7, 8: []}, lambda g: g, [6, 7, 8])
    ids = [c.area.id for c in res.counties]
    assert ids == ["osm:r1", "osm:r2", "osm:r9"]
    assert res.levels_used == [6, 7]
    assert res.regions_used == ["osm:r9"]
    filler = res.counties[-1]
    assert filler.region_fill and filler.geom.equals(shapely.box(2, 0, 3, 1))
    assert res.left_km2 == pytest.approx(0, abs=1e-6)


def test_counties_from_level_7_when_there_is_no_level_6():
    country = shapely.box(0, 0, 2, 1)
    l7 = [_area(1, 7, shapely.box(0, 0, 1, 1)), _area(2, 7, shapely.box(1, 0, 2, 1))]
    res = counties.build(country, [], {6: [], 7: l7}, lambda g: g, [6, 7, 8])
    assert res.levels_used == [7]
    assert len(res.counties) == 2 and not res.regions_used


def test_counties_record_is_kept_and_corrections_are_never_overwritten(tmp_path):
    path = tmp_path / "county_levels.yaml"
    res = counties.Result(counties=[], levels_used=[7], regions_used=[])
    counties.update_record(path, "osm:r1", "Norway", res, {}, "a test")
    levels, from_record = counties.levels_for(counties.load_record(path), "osm:r1")
    assert levels == [7] and from_record
    assert counties.levels_for({}, "osm:r2") == (counties.DEFAULT_LEVELS, False)
    record = counties.load_record(path)
    record["osm:r1"]["levels"] = [9]
    record["osm:r1"]["how"] = "corrected: the wiki says level 9"
    import yaml
    path.write_text(yaml.safe_dump({"countries": record}), encoding="utf-8")
    counties.update_record(path, "osm:r1", "Norway", res, {}, "a test")
    assert counties.load_record(path)["osm:r1"]["levels"] == [9]


# Outlines with an open end (Russia in the planet file of November 2025) ------

def test_outline_with_a_small_open_end_is_closed_and_reported():
    from mapdata.stages.boundaries import close_outline

    # A square outline in two ways, with a gap of 0.1 degrees at one corner.
    outer = [shapely.LineString([(0, 0), (10, 0), (10, 10)]), shapely.LineString([(10, 10), (0, 10), (0, 0.1)])]
    repairs = []
    shape = close_outline(outer, [], "test land", repairs)
    assert shape.area == pytest.approx(100, rel=0.001)
    assert len(repairs) == 1 and "closed with a straight line" in repairs[0]


def test_closed_outline_is_left_alone():
    from mapdata.stages.boundaries import close_outline

    outer = [shapely.LineString([(0, 0), (10, 0), (10, 10)]), shapely.LineString([(10, 10), (0, 10), (0, 0)])]
    repairs = []
    assert close_outline(outer, [], "test land", repairs) is None
    assert repairs == []


def test_outline_with_a_large_open_end_is_reported_not_closed():
    from mapdata.stages.boundaries import close_outline

    outer = [shapely.LineString([(0, 0), (10, 0), (10, 10), (0, 10), (0, 5)])]
    repairs = []
    assert close_outline(outer, [], "test land", repairs) is None
    assert "too far apart" in repairs[0]


def test_raw_gaps_match_gaps_on_the_cut_shapes():
    from mapdata.stages import clip

    land = clip.Land(np.array([shapely.box(0, 0, 2, 1)], dtype=object))
    # The country and its two regions reach out to sea (y up to 2); the
    # regions leave a strip of land, x 0.9 to 1.0, in no region.
    country = shapely.box(-1, -1, 3, 2)
    west, east = shapely.box(-1, -1, 0.9, 2), shapely.box(1, -1, 3, 2)
    raw = clip.raw_gaps(country, [west, east], ["West", "East"], land)
    cut = clip.gaps(land.clip(country), [land.clip(west), land.clip(east)], ["West", "East"])
    assert len(raw) == len(cut) == 1
    assert raw[0].area_km2 == pytest.approx(cut[0].area_km2)


def test_cutting_with_workers_matches_one_process(tmp_path):
    from mapdata.stages import clip
    from mapdata.stages.s2_stage import clip_all

    lines = []
    land = clip.Land(np.array([shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1), shapely.box(3, 0, 3.2, 0.2)],
                              dtype=object))
    items = [("osm:r1", shapely.box(-0.5, -0.5, 1.5, 1.5)), ("osm:r2", shapely.box(1.5, -0.5, 3.5, 0.5)),
             ("osm:r3", shapely.box(10, 10, 11, 11))]
    one = clip_all(land, items, tmp_path / "a", lines.append, workers=1)
    two = clip_all(land, items, tmp_path / "b", lines.append, workers=2)
    for key in ("osm:r1", "osm:r2", "osm:r3"):
        assert one[key].equals(two[key]) or (one[key].is_empty and two[key].is_empty)
    assert one["osm:r1"].area == pytest.approx(1.5)
    # A second run reads the cache.
    again = clip_all(land, items, tmp_path / "b", lines.append, workers=2)
    assert again["osm:r2"].equals(two["osm:r2"])


def test_window_pieces_keep_neighbours_fitting_exactly():
    from mapdata.stages.s2_stage import border_window, window_pieces

    west, east = shapely.box(0, 0, 2.5, 3), shapely.box(2.5, 0, 5, 3)
    win = border_window([west, east], 0.2)
    pieces = window_pieces([west, east], win)
    assert len(pieces) == 6  # three one-degree squares on each side of the border
    assert shapely.coverage_is_valid(np.array(pieces, dtype=object))
    assert sum(p.area for p in pieces) == pytest.approx(0.4 * 3)


def test_layer_check_in_a_worker_returns_its_report():
    from mapdata import parallel
    from mapdata.stages.s2_stage import _coverage_job

    layer = [shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1)]
    with parallel.pool(2) as executor:
        lines, result = executor.submit(_coverage_job, "Test layer", layer, 0.01).result()
    assert result["valid_after"] and "simplified" not in result
    assert lines and lines[0].startswith("Test layer: 2 areas.")


def test_full_pack_tiles_are_split_and_lookups_still_find_every_area(tmp_path, monkeypatch):
    from mapcore.packs.archive import Pack
    from mapdata.stages import pack_write

    monkeypatch.setattr(pack_write, "TILE_POINTS", 50)
    # 16 small squares side by side, each with 20 points: far too many for one pack tile at 50 points.
    geoms = [shapely.box(i, 0, i + 0.9, 0.9).segmentize(0.2) for i in range(16)]
    records = [{"id": f"osm:r{i}", "name": f"Area {i}", "area_km2": float(i)} for i in range(16)]
    stats = pack_write.write(tmp_path / "t.pack", {"name": "t"}, records, geoms, "compact", say=lambda s: None)
    assert max(stats["levels"]) > pack_write.START_LEVEL
    pack = Pack(tmp_path / "t.pack")
    try:
        for i in range(16):
            assert [f["name"] for f in pack.at(i + 0.45, 0.45)] == [f"Area {i}"]
        assert pack.at(i + 0.95, 0.45) == []
    finally:
        pack.close()


def test_far_parts_allow_for_the_180_degree_line():
    from mapdata.stages.s2_stage import far_parts

    # A mainland just west of the line and a large part just east of it: neighbours, not far apart.
    shape = shapely.MultiPolygon([shapely.box(170, 60, 180, 70), shapely.box(-180, 60, -175, 70)])
    lines = []
    assert far_parts("Test", shape, [], lines.append) == []


def test_polar_cap_is_added_when_the_land_stops_short_of_the_pole():
    from mapdata.stages.s2_stage import with_polar_cap

    tiles = np.array([shapely.box(0, -86, 1, -85), shapely.box(10, 50, 11, 51)], dtype=object)
    out, south = with_polar_cap(tiles)
    assert south == pytest.approx(-86) and len(out) == 3
    assert shapely.intersects(out[-1], shapely.Point(0, -89.99))
    assert with_polar_cap(tiles[1:])[1] is None


def test_both_packs_written_at_once_match_the_packs_written_one_by_one(tmp_path):
    from mapcore.packs.archive import Pack
    from mapdata.stages import pack_write

    geoms = [shapely.box(i, 0, i + 0.9, 0.9).segmentize(0.05) for i in range(6)] + [shapely.box(-10, -10, 20, 20)]
    records = [{"id": f"osm:r{i}", "name": f"Area {i}", "area_km2": float(i)} for i in range(len(geoms))]
    quiet = lambda s: None
    one = {e: pack_write.write(tmp_path / f"one-{e}.pack", {"name": "t"}, records, geoms, e, say=quiet)
           for e in ("wkb", "compact")}
    both = pack_write.write_both({e: tmp_path / f"both-{e}.pack" for e in ("wkb", "compact")}, {"name": "t"},
                                 records, geoms, workers=2, say=quiet)
    for e in ("wkb", "compact"):
        assert both[e]["tiles"] == one[e]["tiles"] and both[e]["pieces"] == one[e]["pieces"]
        a, b = Pack(tmp_path / f"one-{e}.pack"), Pack(tmp_path / f"both-{e}.pack")
        try:
            for lon, lat in [(0.5, 0.5), (3.45, 0.45), (5.95, 0.5), (15, 15), (30, 30)]:
                assert [f["id"] for f in a.at(lon, lat)] == [f["id"] for f in b.at(lon, lat)]
        finally:
            a.close()
            b.close()


def test_pictures_are_drawn_in_workers(tmp_path):
    from mapdata.stages.s2_stage import draw_all

    lines = []
    views = {"one": ((0, 0, 2, 2), [shapely.box(0.5, 0.5, 1.5, 1.5)]), "two": ((5, 5, 6, 6), [shapely.box(0, 0, 9, 9)])}
    pics, globes = draw_all(tmp_path, views, None, [], 2, lines.append)
    assert sorted(pics) == ["one.png", "two.png"]
    assert (tmp_path / "one.png").stat().st_size > 0 and globes == []
