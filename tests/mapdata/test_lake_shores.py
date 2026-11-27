"""The writing stage stores each island's shore on the lakes round it (P3-T32g; INF-4, DAT-4).

An island in a lake is a hole in the lake's outline, so the relationships stage never puts it inside the lake;
and lakes are not water to that stage, so it measures no coast between them, as it does for the sea. The writing
stage measures it: the length of the island's outline within LAKE_SHORE_M of the lake, as the lake's and the
island's outlines are each simplified on their own by up to 100 metres. It is stored on the island ("lake_shore")
and on the lake ("shores"), and the core's rule (contents.waters_round) puts the island in the lake when at least
half its outline is shore on it.
"""
import math

import shapely

from mapcore.store import contents
from mapdata.stages import write

HOLE_A = shapely.box(0.40, 0.40, 0.50, 0.50)      # an island that is the lake's hole, exactly
HOLE_D = shapely.box(0.20, 0.20, 0.30, 0.30)      # a hole the island's own outline misses by about 55 metres
ISLAND_D = shapely.box(0.2005, 0.2005, 0.2995, 0.2995)
ISLAND_B = shapely.box(0.98, 0.50, 1.08, 0.55)    # on the lake's far shore, mostly on the land beyond it
ISLAND_C = shapely.box(3.0, 3.0, 3.1, 3.1)        # far from the lake
LAKE = shapely.box(0.0, 0.0, 1.0, 1.0).difference(shapely.union_all([HOLE_A, HOLE_D, ISLAND_B]))


def outline_km(g):
    c = shapely.get_coordinates(shapely.get_exterior_ring(g))
    return float(write.segments_km(c[:-1], c[1:]).sum())


def build():
    records = [{"id": "lake", "layer": "lakes"}, {"id": "a", "layer": "islands"}, {"id": "b", "layer": "islands"},
               {"id": "c", "layer": "islands"}, {"id": "d", "layer": "islands"}, {"id": "county", "layer": "counties"}]
    geoms = [LAKE, HOLE_A, ISLAND_B, ISLAND_C, ISLAND_D, shapely.box(0.9, 0.0, 2.0, 1.0)]
    rels = {r["id"]: {"outline_km": round(outline_km(g), 2)} for r, g in zip(records, geoms)}
    rels["lake"]["shores"] = [["county", 111.0]]
    n = write.lake_shores(records, geoms, rels)
    return n, rels


def test_islands_in_a_lake_have_their_shore_on_it():
    n, rels = build()
    assert n == 3
    for island in ("a", "d"):
        (lake, km), = rels[island]["lake_shore"]
        assert lake == "lake" and math.isclose(km, rels[island]["outline_km"], rel_tol=0.02), (island, km)
    assert "lake_shore" not in rels["c"] and "lake_shore" not in rels["county"]


def test_the_lake_has_them_on_its_shores_longest_first():
    _n, rels = build()
    shores = rels["lake"]["shores"]
    assert shores[0] == ["county", 111.0]
    assert [i for i, _km in shores] == ["county", "a", "d", "b"]
    assert [km for _i, km in shores] == sorted((km for _i, km in shores), reverse=True)


def test_the_core_puts_the_islands_all_round_in_the_lake_and_not_the_one_on_its_shore():
    _n, rels = build()
    assert contents.waters_round(rels["a"]) == {"lake"}
    assert contents.waters_round(rels["d"]) == {"lake"}
    assert contents.waters_round(rels["b"]) == set()   # under a third of its outline is on the lake


def whole_ring_km(island, water, eps_deg):
    """shore_km as it was before P4-T2b: every ring cut into steps and every step tested."""
    total = 0.0
    for ring in shapely.get_exterior_ring(shapely.get_parts(island)):
        c = shapely.get_coordinates(shapely.segmentize(ring, eps_deg))
        near = shapely.dwithin(water, shapely.points(c), eps_deg)
        both = near[:-1] & near[1:]
        if both.any():
            total += float(write.segments_km(c[:-1][both], c[1:][both]).sum())
    return total


def test_only_the_outline_near_the_water_is_measured_and_the_length_is_the_same():
    """P4-T2b: a large island's outline is cut into steps only near each lake, as Great Britain's whole outline was
    cut for each of England's lakes. The length is the same to the last digit, for lakes on the shore, inland and
    away from it, and for islands of several parts."""
    big = shapely.Point(0, 0).buffer(1.0, quad_segs=400)          # a large island, its outline of many segments
    parts = shapely.MultiPolygon([big, shapely.box(1.2, 0.0, 1.3, 0.1)])
    eps = write.LAKE_SHORE_M / 111_320.0
    lakes = [shapely.box(0.99, -0.01, 1.05, 0.01),                 # on the shore
             shapely.box(-0.2, -0.2, 0.2, 0.2),                    # inland, far from the outline
             shapely.box(1.15, 0.0, 1.21, 0.05),                   # between the two parts
             shapely.Point(0, 0.999).buffer(0.002)]                # a small lake just inside the outline
    for island in (big, parts):
        rings = write.outer_rings(island)
        for lake in lakes:
            expected = whole_ring_km(island, lake, eps)
            assert write.shore_km(island, lake, eps) == expected
            assert write.shore_km(island, lake, eps, rings) == expected
    assert whole_ring_km(big, lakes[0], eps) > 0 and whole_ring_km(big, lakes[1], eps) == 0


def test_no_lakes_or_no_islands_change_nothing():
    rels = {"lake": {}}
    assert write.lake_shores([{"id": "lake", "layer": "lakes"}], [LAKE], rels) == 0
    assert rels == {"lake": {}}


def test_the_counts_stored_take_in_the_islands_in_each_water():
    """count_held adds the islands in a water by their shore to its "held" and "counts", so the application need
    not read every island on its shores to say them (P3-T32g)."""
    from mapdata.stages import pack_write

    records = [{"id": "sea", "layer": "seas"}, {"id": "jersey", "layer": "islands"},
               {"id": "britain", "layer": "islands"}, {"id": "rock", "layer": "islands"},
               {"id": "county", "layer": "counties"}]
    rels = {"sea": {"counts": {"sea-places": 3, "islands": 1}},
            "jersey": {"coast": [["sea", 77.0]], "outline_km": 77.0, "in": ["county"]},
            "britain": {"coast": [["sea", 100.0]], "outline_km": 11500.0},
            "rock": {"in": ["sea"]},   # an island left inside the sea's area: counted as before, once
            "county": {"coast": [["sea", 50.0]], "outline_km": 60.0}}
    pack_write.count_held(records, rels)
    assert rels["sea"]["held"] == {"islands": 2}
    assert rels["sea"]["counts"] == {"islands": 2, "sea-places": 3}
