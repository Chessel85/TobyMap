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
