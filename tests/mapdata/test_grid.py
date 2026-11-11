"""The grid square method of the base pack lite (P1-T4, AD-16, LOC-6), on small made-up shapes."""
import numpy as np
import shapely

from mapdata.stages import grid
from mapdata.stages.grid import Meta, Rules


def meta_for(*items):
    return [Meta(kind, id_, country, level, size) for kind, id_, country, level, size in items]


def wavy_coast(x0=0.0, y0=0.0):
    """Land in the west of the square at (x0, y0), with a coast of many small zigzags."""
    ys = np.linspace(y0, y0 + 1, 401)
    xs = x0 + 0.5 + 0.0003 * np.sin(np.arange(401) * 1.7)
    return shapely.Polygon([(x0, y0), *zip(xs, ys), (x0, y0 + 1)])


def test_a_square_is_covered_with_no_gaps_and_each_face_named():
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = wavy_coast()
    a = shapely.box(-1, -1, 0.3, 2)          # country A, reaching out to sea like a level 2 area
    b = shapely.box(0.3, -1, 2, 2)           # country B
    ocean = shapely.box(-10, -10, 10, 10)
    meta = meta_for(("country", "A", None, 2, 3.0), ("country", "B", None, 2, 5.0), ("ocean", "O", None, None, 400))
    pieces = [(0, shapely.intersection(a, shapely.box(*bounds))), (1, shapely.intersection(b, shapely.box(*bounds))),
              (2, shapely.box(*bounds))]
    r = grid.build_square(bounds, land, pieces, meta, Rules(), 100)
    assert set(r.labels) == {("land", "A", None), ("land", "B", None), ("water", "O", None)}
    whole = shapely.union_all(r.shapes)
    assert abs(whole.area - 1.0) < 1e-9
    assert shapely.coverage_is_valid(shapely.GeometryCollection(r.shapes))
    assert r.points_after < r.points_before


def test_land_in_no_country_and_water_in_no_ocean_wait_for_the_join_stage():
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = shapely.box(0, 0, 0.5, 1)
    meta = meta_for(("country", "A", None, 2, 1.0), ("ocean", "O", None, None, 1.0))
    pieces = [(0, shapely.box(0, 0, 0.4, 1)), (1, shapely.box(0.7, 0, 1, 1))]
    r = grid.build_square(bounds, land, pieces, meta, Rules(), 100)
    assert grid.WAITING_LAND in r.labels
    assert grid.WAITING_WATER in r.labels


def test_units_condominiums_and_regions():
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = shapely.box(0, 0, 1, 1)
    meta = meta_for(
        ("country", "F", None, 2, 10.0),
        ("unit", "U", "F", 3, 0.2),               # a country unit in the south of F
        ("country", "D", None, 2, 10.0),           # D and L both hold the strip x 0.9 to 1
        ("country", "L", None, 2, 0.5),
        ("division", "R4", "F", 4, 0.3),           # F's level 4 covers only part of it
        ("division", "R3", "F", 3, 0.8),           # level 3 fills the rest
    )
    pieces = [(0, shapely.box(0, 0, 0.9, 1)), (1, shapely.box(0, 0, 0.9, 0.2)),
              (2, shapely.box(0.9, 0, 1, 1)), (3, shapely.box(0.9, 0, 1, 1)),
              (4, shapely.box(0, 0.2, 0.5, 1)), (5, shapely.box(0, 0, 0.9, 1))]
    rules = Rules(condominiums={frozenset({"D", "L"}): "condominium:D-L"})
    r = grid.build_square(bounds, land, pieces, meta, rules, 100)
    assert ("land", "condominium:D-L", None) in r.labels
    assert ("land", "U", "R3") in r.labels          # the unit, with the level 3 region filling the gap
    assert ("land", "F", "R4") in r.labels
    assert ("land", "F", "R3") in r.labels
    assert [f[:3] for f in r.fills] == [("F", "R3", 3)]
    assert r.overlaps == []


def test_countries_overlapping_without_a_rule_are_reported_and_the_smaller_wins():
    bounds = (0.0, 0.0, 1.0, 1.0)
    meta = meta_for(("country", "A", None, 2, 4.0), ("country", "B", None, 2, 1.0))
    pieces = [(0, shapely.box(0, 0, 1, 1)), (1, shapely.box(0.5, 0, 1, 1))]
    r = grid.build_square(bounds, shapely.box(0, 0, 1, 1), pieces, meta, Rules(), 100)
    assert ("land", "B", None) in r.labels and ("land", "A", None) in r.labels
    assert [o[:2] for o in r.overlaps] == [("countries", ("A", "B"))]


def test_neighbouring_squares_meet_exactly():
    # A country and the sea across two grid squares, built one square at a time.
    land = shapely.union_all([wavy_coast(0, 0), wavy_coast(1, 0)])
    land = shapely.Polygon([(0, 0.2), (2, 0.25), (2, 0.8), (0, 0.75)]).intersection(land.buffer(0.2))
    country = shapely.box(-1, -1, 3, 0.5)
    other = shapely.box(-1, 0.5, 3, 2)
    meta = meta_for(("country", "A", None, 2, 8.0), ("country", "B", None, 2, 6.0), ("ocean", "O", None, None, 9.0))
    cut = {i: grid.cut_to_squares(g, 1.0) for i, g in enumerate([country, other, shapely.box(-5, -5, 5, 5)])}
    shapes = []
    for w in (0.0, 1.0):
        b = (w, 0.0, w + 1, 1.0)
        pieces = [(i, cut[i][(w, 0.0)]) for i in cut if (w, 0.0) in cut[i]]
        r = grid.build_square(b, shapely.intersection(land, shapely.box(*b), grid_size=grid.GRID), pieces, meta,
                              Rules(), 2000)
        shapes += r.shapes
    assert shapely.coverage_is_valid(shapely.GeometryCollection(shapes))
    assert abs(shapely.union_all(shapes).area - 2.0) < 1e-9


def test_cut_to_squares_by_halving():
    g = shapely.box(-0.5, -0.5, 2.5, 1.5)
    parts = grid.cut_to_squares(g, 1.0)
    assert sorted(parts) == [(x, y) for x in (-1.0, 0.0, 1.0, 2.0) for y in (-1.0, 0.0, 1.0)]
    assert abs(sum(p.area for p in parts.values()) - g.area) < 1e-9
    assert sorted(grid.cut_to_squares(g, 1.0, within=(0, 0, 1, 1))) == [(0.0, 0.0)]


def test_the_polar_cap():
    assert grid.polar_cap((10, -86, 11, -85), -85.05).bounds == (10, -86, 11, -85.05)
    assert grid.polar_cap((10, -80, 11, -79), -85.05) is None


def test_union_parts_joins_neighbours_that_share_an_edge():
    # The world build met grid squares whose shared edge was noded differently on each side (P1-T4).
    import shapely

    from mapdata.stages.join import union_parts

    a = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    b = shapely.Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0.5)])  # a vertex on the shared edge, a has none
    u = union_parts([a, b])
    assert abs(u.area - 2.0) < 1e-9


def test_counties_level_6_then_gaps_filled_by_7_then_8_then_the_region():
    # DP101, P3-T1a: level 6 where it is, level 7 in its gap, level 8 in what is left, and the region itself
    # where nothing covers the land.
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = shapely.box(0, 0, 1, 1)
    meta = meta_for(("country", "A", None, 2, 9.0), ("division", "R", "A", 4, 4.0),
                    ("division", "six", "A", 6, 1.0), ("division", "seven", "A", 7, 1.0),
                    ("division", "eight", "A", 8, 1.0))
    sq = shapely.box(*bounds)
    pieces = [(0, sq), (1, sq), (2, shapely.box(0, 0, 0.4, 1)), (3, shapely.box(0, 0, 0.6, 1)),
              (4, shapely.box(0.6, 0, 0.8, 1))]
    r = grid.build_square(bounds, land, pieces, meta, Rules(county_levels={}), 100)
    got = {lab[3]: shapely.union_all([g for l, g in zip(r.labels, r.shapes) if l == lab]).area for lab in r.labels}
    assert set(got) == {"six", "seven", "eight", "R#county"}
    assert abs(got["six"] - 0.4) < 1e-9 and abs(got["seven"] - 0.2) < 1e-9
    assert abs(got["eight"] - 0.2) < 1e-9 and abs(got["R#county"] - 0.2) < 1e-9
    levels = {c[1]: c[2] for c in r.counties}
    assert set(levels) == {6, 7, 8, grid.REGION_AS_COUNTY}


def test_counties_use_the_levels_in_the_record_and_none_when_not_asked():
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = shapely.box(0, 0, 1, 1)
    meta = meta_for(("country", "A", None, 2, 9.0), ("division", "six", "A", 6, 1.0),
                    ("division", "seven", "A", 7, 1.0))
    sq = shapely.box(*bounds)
    pieces = [(0, sq), (1, shapely.box(0, 0, 0.5, 1)), (2, sq)]
    r = grid.build_square(bounds, land, pieces, meta, Rules(county_levels={"A": (7,)}), 100)
    assert {lab[3] for lab in r.labels} == {"seven"}
    r = grid.build_square(bounds, land, pieces, meta, Rules(), 100)
    assert {len(lab) for lab in r.labels} == {3}


def test_a_region_used_as_county_over_a_sliver_goes_to_the_county_beside_it():
    # DP101: a gap in the counties under 1 km2 is a sliver, not a missing county (P3-T1a).
    from mapdata.stages import join

    lines = []
    ctx = type("C", (), {"progress": type("P", (), {"line": staticmethod(lines.append)})()})()
    county = ("land", "A", "R", "six")
    sliver = ("land", "A", "R", "R#county")
    big = ("land", "A", "Q", "Q#county")
    shapes = {county: [shapely.box(0, 0, 1, 1)], sliver: [shapely.box(1, 0, 1.0001, 0.001)],
              big: [shapely.box(5, 5, 6, 6)]}
    join.sliver_counties(ctx, shapes, {})
    assert sliver not in shapes and len(shapes[county]) == 2
    assert big in shapes   # a region used as county over more than 1 km2 is kept
    assert "1 of their parts are given to the county beside them" in lines[0]
    islet = ("land", "A", "R", "R#county")
    shapes = {county: [shapely.box(0, 0, 1, 1)], islet: [shapely.box(1.01, 0, 1.0101, 0.001)]}
    join.sliver_counties(ctx, shapes, {})
    assert islet not in shapes and len(shapes[county]) == 2   # an islet goes to the nearest county


def test_divisions_at_a_level_no_county_uses_are_left_out_before_the_squares():
    from mapdata.stages import squares

    lines = []
    ctx = type("C", (), {"progress": type("P", (), {"line": staticmethod(lines.append)})()})()
    records = [{"kind": "country", "id": "US"}, {"kind": "division", "country": "US", "level": 4},
               {"kind": "division", "country": "US", "level": 6}, {"kind": "division", "country": "US", "level": 8},
               {"kind": "division", "country": "FR", "level": 8}]
    assert squares.unused_levels(records, {"US": (6,), "FR": (6, 7, 8)}, ctx) == {3}


def test_seas_name_the_water_below_the_ocean_and_the_smaller_sea_wins():
    # P3-T1b, DP168: Natural Earth's marine areas name the water under the VLIZ ocean. A water face is in
    # its ocean and its sea; where two seas overlap, the smaller wins; a face in an area that names no sea,
    # such as Natural Earth's own ocean, has none.
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = shapely.box(0, 0, 0.2, 1)
    meta = meta_for(("ocean", "O", None, None, 400.0), ("sea", "S", None, None, 4.0),
                    ("sea", "B", None, None, 0.1), ("nosea", "N", None, None, 300.0))
    pieces = [(0, shapely.box(*bounds)), (1, shapely.box(0.1, 0, 0.7, 1)), (2, shapely.box(0.1, 0, 0.4, 0.5)),
              (3, shapely.box(0.7, 0, 1, 1))]
    r = grid.build_square(bounds, land, pieces, meta, Rules(seas=True), 100)
    area = {lab: g.area for lab, g in zip(r.labels, r.shapes)}
    assert abs(area[("water", "O", None, "B")] - 0.1) < 1e-9
    assert abs(area[("water", "O", None, "S")] - 0.4) < 1e-9
    assert abs(area[("water", "O", None, None)] - 0.3) < 1e-9
    assert grid.WAITING_LAND in r.labels


def test_water_between_a_seas_rough_coast_and_the_real_coast_goes_to_the_sea_beside_it():
    # Natural Earth's coasts are rough, so between a sea's edge and the real coast there is water in no
    # marine area. It takes the sea it shares the longest edge with, in the grid square.
    bounds = (0.0, 0.0, 1.0, 1.0)
    land = shapely.box(0, 0, 0.2, 1)
    meta = meta_for(("ocean", "O", None, None, 400.0), ("sea", "S", None, None, 4.0),
                    ("nosea", "N", None, None, 300.0))
    # The sea's coast is at 0.3, the real coast at 0.2. The sea covers the south 0.8 of the coast,
    # Natural Earth's ocean the north 0.2.
    pieces = [(0, shapely.box(*bounds)), (1, shapely.box(0.3, 0, 1, 0.8)), (2, shapely.box(0.3, 0.8, 1, 1))]
    r = grid.build_square(bounds, land, pieces, meta, Rules(seas=True), 100)
    area = {lab: g.area for lab, g in zip(r.labels, r.shapes)}
    assert set(area) == {("land", None, None), ("water", "O", None, "S"), ("water", "O", None, None)}
    assert abs(area[("water", "O", None, "S")] - (0.7 * 0.8 + 0.1)) < 1e-9   # the whole strip, 0.1


def test_without_seas_water_keeps_three_names():
    bounds = (0.0, 0.0, 1.0, 1.0)
    meta = meta_for(("ocean", "O", None, None, 400.0), ("sea", "S", None, None, 4.0))
    pieces = [(0, shapely.box(*bounds)), (1, shapely.box(0.5, 0, 1, 1))]
    r = grid.build_square(bounds, None, pieces, meta, Rules(), 100)
    assert r.labels == [("water", "O", None)]


def test_marine_areas_from_natural_earth():
    # Which of Natural Earth's classes name a sea, which name none, and which are left out.
    from mapdata.stages import seas

    feats = [
        {"properties": {"name": "Bay of Biscay", "name_en": "Bay of Biscay", "featurecla": "bay", "ne_id": 1,
                        "wikidataid": "Q129987"}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}},
        {"properties": {"name": "Golfe du Lion", "name_en": "Gulf of Lion", "featurecla": "gulf", "ne_id": 2},
         "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 0]]]}},
        {"properties": {"name": "North Atlantic Ocean", "name_en": "Atlantic Ocean", "featurecla": "ocean", "ne_id": 3},
         "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [3, 0], [3, 3], [0, 0]]]}},
        {"properties": {"name": None, "name_en": None, "featurecla": "generic", "ne_id": 4},
         "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [3, 0], [3, 3], [0, 0]]]}},
        {"properties": {"name": "Great Barrier Reef", "name_en": "Great Barrier Reef", "featurecla": "reef", "ne_id": 5},
         "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [3, 0], [3, 3], [0, 0]]]}},
    ]
    records, geoms = seas.marine_areas(feats)
    assert [(r["id"], r["kind"], r.get("name"), r.get("type")) for r in records] == [
        ("ne:marine:1", "sea", "Bay of Biscay", "bay"),
        ("ne:marine:2", "sea", "Gulf of Lion", "gulf"),
        ("ne:marine:3", "nosea", None, None),
        ("ne:marine:4", "nosea", None, None),
    ]
    assert records[0]["wikidata"] == "Q129987" and records[1]["local_name"] == "Golfe du Lion"
    assert len(geoms) == 4


def test_the_join_gives_a_sea_to_water_whose_sea_waits():
    # Water in an ocean whose sea is still waiting, as no sea was beside it in its grid square, takes the
    # sea of the water it shares the longest edge with; water in no ocean takes its neighbour's ocean and
    # keeps its own sea.
    from mapdata.stages import join

    sea = ("water", "O", None, "S")
    ocean_only = ("water", "O", None, None)
    waits = ("water", "O", None, grid.SEA_WAITING)
    no_ocean = ("water", None, None, "S")
    shapes = {sea: [shapely.box(1, 0, 2, 1)], ocean_only: [shapely.box(1, 1, 2, 5)],
              waits: [shapely.box(0, 0, 1, 1.2)], no_ocean: [shapely.box(2, 0, 2.01, 1)]}
    lines = []
    ctx = type("C", (), {"progress": type("P", (), {"line": staticmethod(lines.append),
                                                     "log": staticmethod(lines.append)})()})()
    join.settle_seas(ctx, shapes)
    assert waits not in shapes and len(shapes[sea]) == 2
    assert no_ocean in shapes   # water in no ocean is settled by the ocean step, before this
