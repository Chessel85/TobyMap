"""Relationships worked out by the pipeline (P3-T3; AD-8, NAV-4, INF-2, INF-5, INF-6, DAT-4, LOC-3).

On the test pack: containment with parents of parents, neighbours with their shared border
lengths, nearly touching areas, overlaps with the share of each, the order of the areas a line
passes through, the lines crossing an area or along its border, the water hierarchy, and counts.
"""
import pytest
import shapely

from mapcore.packs.pack import Pack
from mapdata.stages import relationships as rel

SWITZERLAND, HAMPSHIRE, WILTSHIRE, ENGLAND, UK = "osm:r51701", "osm:r172799", "osm:r57533", "osm:r58447", "osm:r62149"
NEW_FOREST, RHINE, ITCHEN, BISCAY, ATLANTIC = ("osm:r2678988", "osm:r123924", "osm:r7703089", "osm:r7156290",
                                               "vliz:goas:north-atlantic-ocean")
FRANCE, GERMANY, ITALY, AUSTRIA, LIECHTENSTEIN = "osm:r1403916", "osm:r51477", "osm:r365331", "osm:r16239", "osm:r1155955"
SOUTHAMPTON, STATION, ISLE_OF_WIGHT = "osm:r127864", "osm:n638908005", "osm:r154350"


@pytest.fixture(scope="module")
def pack(test_pack):
    with Pack(test_pack, check_app=False) as p:
        yield p


def test_switzerland_has_exactly_its_five_neighbours_with_their_border_lengths(pack):
    """INF-2. Wikipedia's lengths: Italy 744 km, France 573, Germany 362, Austria 164, Liechtenstein 41. The
    sample is simplified to about 200 metres, which shortens a winding border, so France and Germany come
    out 3 to 4 percent short here; the 2 percent is checked on the trial pack's 100 metre data."""
    nxt = dict((i, km) for i, km in pack.relationships(SWITZERLAND)["next"])
    assert set(nxt) == {FRANCE, GERMANY, ITALY, AUSTRIA, LIECHTENSTEIN}
    wikipedia = {ITALY: 744, FRANCE: 573, GERMANY: 362, AUSTRIA: 164, LIECHTENSTEIN: 41}
    for country, km in wikipedia.items():
        assert nxt[country] == pytest.approx(km, rel=0.05)
    assert list(nxt) == [ITALY, FRANCE, GERMANY, AUSTRIA, LIECHTENSTEIN]   # the longest border first


def test_hampshires_parents_are_england_and_the_united_kingdom_with_no_ambiguity(pack):
    r = pack.relationships(HAMPSHIRE)
    assert r["in"] == [ENGLAND, UK]
    assert pack.relationships(ENGLAND)["in"] == [UK]
    assert pack.relationships(STATION)["in"] == [SOUTHAMPTON, ENGLAND, UK]   # parents of parents, smallest first


def test_the_new_forest_overlaps_hampshire_and_wiltshire_with_a_share_for_each(pack):
    """INF-5, and NAV-4's ambiguous up: a point in the New Forest is in Hampshire and in the park, and neither
    holds the other."""
    over = {i: (mine, theirs) for i, mine, theirs in pack.relationships(NEW_FOREST)["overlaps"]}
    assert over[HAMPSHIRE][0] == pytest.approx(0.92, abs=0.02) and over[HAMPSHIRE][1] == pytest.approx(0.14, abs=0.02)
    assert over[WILTSHIRE][0] == pytest.approx(0.05, abs=0.02) and 0 < over[WILTSHIRE][1] < 0.02
    hants = {i: (mine, theirs) for i, mine, theirs in pack.relationships(HAMPSHIRE)["overlaps"]}
    assert hants[NEW_FOREST] == (over[HAMPSHIRE][1], over[HAMPSHIRE][0])
    assert NEW_FOREST not in pack.relationships(HAMPSHIRE).get("in", [])
    assert HAMPSHIRE not in pack.relationships(NEW_FOREST).get("in", [])


def test_a_line_lists_the_areas_it_passes_through_in_order_from_its_start(pack):
    """INF-6. The Rhine sample runs from Schaffhausen down to Basel, the way OSM draws a river, as it flows."""
    assert pack.relationships(RHINE)["crosses"] == [SWITZERLAND, GERMANY, FRANCE]
    assert pack.relationships(ITCHEN)["crosses"] == [UK, ENGLAND, HAMPSHIRE, SOUTHAMPTON]


def test_an_area_lists_the_lines_crossing_it_and_along_its_border(pack):
    assert RHINE in pack.relationships(SWITZERLAND)["crossed_by"]
    assert RHINE in pack.relationships(SWITZERLAND)["along"]       # the Rhine is the border with Germany
    assert ITCHEN in pack.relationships(HAMPSHIRE)["crossed_by"]


def test_areas_that_nearly_touch_are_listed_with_the_distance(pack):
    near = dict(pack.relationships(HAMPSHIRE)["near"])
    assert near[ISLE_OF_WIGHT] == pytest.approx(1.3, abs=0.3)      # Hurst Spit to the island, across the Solent


def test_the_bay_of_biscay_is_in_the_north_atlantic(pack):
    """DAT-4: the water hierarchy."""
    r = pack.relationships(BISCAY)
    assert r["water_in"] == ATLANTIC and ATLANTIC in r["in"]


def test_an_area_counts_what_is_inside_it_by_layer(pack):
    counts = pack.relationships(ENGLAND)["counts"]
    assert counts["counties"] >= 21 and counts["rivers"] == 1 and counts["stations"] == 2   # Southampton Central, Brockenhurst


def test_a_pack_without_relationships_gives_none(pack):
    assert pack.relationships("osm:no-such-feature") == {}


# The parts on their own ------------------------------------------------------------------------------

def test_the_same_land_is_same_as_not_parent_and_child():
    """DP71: identical boundaries, within same_share, are stored as the same land."""
    a = shapely.box(0, 0, 1, 1)
    records = [{"id": "a", "layer": "x"}, {"id": "b", "layer": "y"}]
    kinds = [rel.AREA, rel.AREA]
    sums = rel.measure(records, [a, a], kinds, dict(rel.SETTINGS))
    out = rel.relationships(records, [a, a], kinds, sums, {"x": 1, "y": 2}, set(), dict(rel.SETTINGS))
    assert out[0]["same"] == [1] and out[1]["same"] == [0] and "in" not in out[0]


def test_a_shared_border_is_measured_and_cut_box_edges_are_not():
    """Two squares side by side across the cut at 0 degrees: one degree of shared border, about 111 km."""
    a, b = shapely.box(-1, 10, 0, 11), shapely.box(0, 10, 1, 11)
    records = [{"id": "a", "layer": "x"}, {"id": "b", "layer": "x"}]
    settings = {**rel.SETTINGS, "leaf_points": 0, "min_leaf_deg": 0.5}
    sums = rel.measure(records, [a, b], [rel.AREA, rel.AREA], settings)
    out = rel.relationships(records, [a, b], [rel.AREA, rel.AREA], sums, {"x": 1}, set(), settings)
    assert out[0]["next"][0][0] == 1 and out[0]["next"][0][1] == pytest.approx(111.2, rel=0.01)


def test_a_line_in_parts_is_ordered_along_its_longest_part():
    main = shapely.LineString([(0, 0), (10, 0)])
    branch = shapely.LineString([(8, 1), (9, 2)])            # given first, but near the end of the main part
    z = rel.with_distance(shapely.MultiLineString([branch, main]))
    first = rel.first_distance(list(shapely.get_parts(z)))
    assert first[0] > 800 and first[1] == pytest.approx(0)


def test_a_covering_area_is_noted_and_not_cut_further():
    big = shapely.box(-10, -10, 10, 10)
    assert rel.cut((0, rel.AREA, big), (0, 0, 5, 5)) == (0, rel.AREA, rel.COVER)
    assert rel.cut((1, rel.POINT, shapely.MultiPoint([(5, 5), (1, 1)])), (0, 0, 5, 5))[2].equals(
        shapely.MultiPoint([(1, 1)]))   # a point on the east or north edge belongs to the next box


def test_a_border_along_a_parallel_on_a_cutting_line_is_measured():
    """Montana and Wyoming meet along 45 degrees north, which is the edge of the top boxes: about 111 km for
    each degree of longitude times the cosine of 45 degrees."""
    montana, wyoming = shapely.box(-111, 45, -104, 49), shapely.box(-111, 41, -104, 45)
    records = [{"id": "mt", "layer": "x"}, {"id": "wy", "layer": "x"}]
    sums = rel.measure(records, [montana, wyoming], [rel.AREA, rel.AREA], dict(rel.SETTINGS), say=lambda s: None)
    out = rel.relationships(records, [montana, wyoming], [rel.AREA, rel.AREA], sums, {"x": 1}, set(),
                            dict(rel.SETTINGS))
    assert out[0]["next"] == [[1, pytest.approx(7 * 111.195 * 0.7071, rel=0.001)]]
