"""The counties step's methods give the same counties (P1-T16, DP107).

The build speed trials keep the fastest method only if it chooses the same
counties as spike S2's method, with the same land.
"""
import pytest
import shapely

from mapdata.stages import counties
from mapdata.stages.boundaries import Area

# The land: a coast at y = 1. The country's outline reaches into the sea, to
# y = 1.2, as territorial waters do; its divisions stop at the coast.
LAND = shapely.box(-1, -1, 7, 1)


def clip(g):
    return shapely.intersection(g, LAND)


def _area(i, level, geom):
    return Area(id=f"osm:r{i}", name=f"area {i}", level=level, geom=geom)


def _country():
    country = shapely.box(0, 0, 6, 1.2)
    # Level 6 covers x 0 to 4, except a hole at x 1 to 1.5 (like Brussels).
    l6 = [_area(1, 6, shapely.box(0, 0, 1, 1)), _area(2, 6, shapely.box(1.5, 0, 4, 1)),
          _area(3, 6, shapely.box(1, 0.5, 1.5, 1))]
    l7 = [_area(10, 7, shapely.box(1, 0, 1.5, 0.5)),           # the hole: fills it
          _area(11, 7, shapely.box(0, 0, 0.5, 1)),             # inside level 6: not used
          _area(12, 7, shapely.box(3.3, 0, 4.4, 1))]           # mostly inside level 6: not used
    l8 = [_area(20, 8, shapely.box(4, 0, 5, 1)),               # fills part of the east
          _area(21, 8, shapely.box(2.2, 0.2, 2.4, 0.4))]       # inside level 6: not used
    regions = [(_area(90, 4, shapely.box(0, 0, 3, 1)), shapely.box(0, 0, 3, 1)),
               (_area(91, 4, shapely.box(3, 0, 6, 1)), shapely.box(3, 0, 6, 1))]
    return country, regions, {6: l6, 7: l7, 8: l8}


@pytest.mark.parametrize("method", counties.METHODS)
def test_each_method_fills_gaps_by_level_then_region(method):
    country, regions, cands = _country()
    res = counties.build(country, regions, cands, clip, [6, 7, 8], method=method)
    assert [c.area.id for c in res.counties] == ["osm:r1", "osm:r2", "osm:r3", "osm:r10", "osm:r20", "osm:r91"]
    assert res.levels_used == [6, 7, 8]
    assert res.regions_used == ["osm:r91"]
    filler = res.counties[-1]
    assert filler.region_fill and filler.geom.normalize().equals(shapely.box(5, 0, 6, 1).normalize())
    assert res.left_km2 == pytest.approx(0, abs=1e-6)


def test_the_nearby_methods_give_the_same_land_as_spike_s2s():
    country, regions, cands = _country()
    whole = counties.build(country, regions, cands, clip, [6, 7, 8], method="whole-gap")
    for method in counties.METHODS[1:]:
        other = counties.build(country, regions, cands, clip, [6, 7, 8], method=method)
        from mapdata.stages.county_trials import compare
        assert compare(whole, other) == []
        assert [f for f in other.filled] == [f for f in whole.filled]


def test_slivers_only_stop_the_lower_levels():
    # Level 6 leaves only the sea strip and a sliver of land under 1 km2,
    # so level 7 is not looked at.
    country = shapely.box(0, 0, 6, 1.2)
    l6 = [_area(1, 6, shapely.box(0, 0, 5.99999, 1))]
    l7 = [_area(2, 7, shapely.box(5.9, 0, 6, 1))]
    for method in counties.METHODS:
        res = counties.build(country, [], {6: l6, 7: l7}, clip, [6, 7, 8], method=method)
        assert res.levels_used == [6], method


def test_gap_squares_measure_land_without_cutting_the_gap():
    gap = shapely.box(0, 0, 2, 1.2)  # crosses many squares, and reaches into the sea
    squares = counties.GapSquares(gap)
    assert len(squares.squares) > 4
    assert shapely.union_all(squares.squares).normalize().equals(gap.normalize())
    whole = counties.area_km2(clip(gap))
    assert squares.land_km2(clip) == pytest.approx(whole, rel=1e-9)
    assert squares.land_km2(clip, stop_above=1.0) > 1.0
    land = shapely.box(1, 0, 3, 1)
    assert squares.inside_km2(land) == pytest.approx(counties.area_km2(shapely.box(1, 0, 2, 1)), rel=1e-9)


def test_an_unknown_method_is_named_in_the_error():
    country, regions, cands = _country()
    with pytest.raises(ValueError, match="fastest"):
        counties.build(country, regions, cands, clip, [6], method="fastest")


def test_join_uses_the_general_union_when_areas_overlap():
    edge_to_edge = [shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1)]
    assert counties.join(edge_to_edge).normalize().equals(shapely.box(0, 0, 2, 1).normalize())
    overlapping = [shapely.box(0, 0, 1, 1), shapely.box(0.5, 0, 2, 1)]
    out = counties.join(overlapping)
    assert out.is_valid and out.area == pytest.approx(2.0)

