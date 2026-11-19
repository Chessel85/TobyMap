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
    # Büsingen, Germany's exclave on the Rhine, is crossed too (P3-T24g): the countries are in order.
    assert [i for i in pack.relationships(RHINE)["crosses"] if not i.startswith("exclave:")] == [SWITZERLAND, GERMANY, FRANCE]
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


def test_each_count_is_the_number_ctrl_shift_f_lists(test_pack):
    """P3-T19j, checklist 12.3: Switzerland said "Lakes 13" and listed 17, as the count left out lakes partly
    inside, such as Lake Geneva. Each count is now made by the same test as the list."""
    from mapcore.store import Store

    store = Store([test_pack])
    try:
        for holder in (SWITZERLAND, ENGLAND, HAMPSHIRE):
            for layer, count in store.relationships(holder)["counts"].items():
                assert len(store.browse(layer, holder)) == count, (holder, layer)
    finally:
        store.close()


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


def test_an_island_and_an_area_of_one_name_on_nearly_the_same_land_are_the_same_but_not_with_another_name():
    """P3-T23, DP198: the Isle of Wight the island and the county, cut to the coast a little differently, are the
    same land, so said once; the island of Ireland is not the country, which is about five sixths of it."""
    island, county = shapely.box(0, 0, 1, 1), shapely.box(0, 0, 0.95, 1)
    for name_b, same in (("Wight", True), ("Other", False)):
        records = [{"id": "a", "layer": "islands", "name": "Wight"}, {"id": "b", "layer": "counties", "name": name_b}]
        kinds = [rel.AREA, rel.AREA]
        sums = rel.measure(records, [island, county], kinds, dict(rel.SETTINGS))
        out = rel.relationships(records, [island, county], kinds, sums, {"islands": 5, "counties": 6}, set(),
                                dict(rel.SETTINGS))
        assert (out[0].get("same") == [1]) is same, name_b
    ireland, country = shapely.box(0, 0, 1, 1), shapely.box(0, 0, 0.83, 1)
    records = [{"id": "a", "layer": "islands", "name": "Ireland"}, {"id": "b", "layer": "countries", "name": "Ireland"}]
    sums = rel.measure(records, [ireland, country], [rel.AREA, rel.AREA], dict(rel.SETTINGS))
    out = rel.relationships(records, [ireland, country], [rel.AREA, rel.AREA], sums, {"islands": 5, "countries": 2},
                            set(), dict(rel.SETTINGS))
    assert "same" not in out[0] and out[1]["in"] == [0]


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
    branch = shapely.LineString([(8, 0.3), (9, 2)])          # given first, but near the end of the main part
    z = rel.with_distance(shapely.MultiLineString([branch, main]))
    first = rel.first_distance(list(shapely.get_parts(z)))
    assert first[0] > 800 and first[1] == pytest.approx(0)


def test_a_river_in_parts_is_measured_along_its_chain_of_parts():
    """P3-T19j: the Rhine's countries came out of order, as every part was measured along its longest part only,
    so the river above a lake all fell at its start. Now each part goes on from the part it starts near."""
    above = shapely.LineString([(0, 0), (2, 0)])          # about 222 km, from the source
    below = shapely.LineString([(2.3, 0), (8, 0)])        # below a lake 33 km long, the longest part
    branch = shapely.LineString([(7, 0), (7.5, -0.5)])    # a delta branch, leaving near the end
    z = rel.with_distance(shapely.MultiLineString([below, branch, above]))
    first = rel.first_distance(list(shapely.get_parts(z)))
    assert first[2] == pytest.approx(0)                   # the source
    assert first[0] == pytest.approx(222.6 + 33.4, rel=0.01)
    assert first[1] == pytest.approx(222.6 + 33.4 + 4.7 * 111.3, rel=0.01)   # where it leaves, 4.7 degrees on


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


def test_a_pair_the_geometry_library_refuses_is_made_valid_and_done_again():
    """On the world pack, GEOS refused one pair cut along a box's edge ("Ring edge missing", P3-T3): the pair is
    done again with both shapes made valid, the other pairs as they were, and the build does not stop."""
    bowtie = shapely.Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])   # invalid: it crosses itself
    square = shapely.box(0, 0, 1, 1)
    calls = []

    def fussy(a, b, **kw):
        calls.append(kw)
        if not all(shapely.is_valid(g) for g in [*shapely.get_parts(a), *shapely.get_parts(b)]):
            raise shapely.errors.GEOSException("TopologyException: Ring edge missing")
        return shapely.intersection(a, b, **kw)

    rel.REPAIRED[0] = 0
    got = rel.robust(fussy, [square, bowtie], [square, square])
    assert got[0].equals(square)
    assert shapely.area(got[1]) == pytest.approx(0.5)
    assert rel.REPAIRED[0] == 1


BAY_OF_BISCAY, LONGBRIDGE_LAKE = "osm:r7156290", "osm:r10303325"


def test_a_country_has_its_coast_on_each_sea_and_the_sea_its_shores(pack):
    """P3-T24e, DP200: land and sea share an edge, as the countries are cut to the coast, so the coast is exact."""
    coast = dict(pack.relationships(FRANCE)["coast"])
    assert BAY_OF_BISCAY in coast and coast[BAY_OF_BISCAY] > 100
    assert dict(pack.relationships(BAY_OF_BISCAY)["shores"])[FRANCE] == coast[BAY_OF_BISCAY]
    assert "coast" not in pack.relationships(SWITZERLAND)   # landlocked


def test_a_lake_has_its_shore_in_each_area_round_it(pack):
    """P3-T24e, DP200: a lake lies on the land, so its shore is its outline inside each area."""
    shores = dict(pack.relationships(LONGBRIDGE_LAKE)["shores"])
    assert set(shores) >= {HAMPSHIRE, ENGLAND, UK}
    assert shores[HAMPSHIRE] == pytest.approx(pack.relationships(LONGBRIDGE_LAKE)["outline_km"], rel=0.01)


def test_a_landlocked_countrys_whole_outline_is_its_borders(pack):
    """P3-T24f, DP201: the whole border, land and coast, is stored for the share of each neighbour."""
    rel = pack.relationships(SWITZERLAND)
    assert rel["outline_km"] == pytest.approx(sum(km for _i, km in rel["next"]), rel=0.03)
    france = pack.relationships(FRANCE)
    land, coast = sum(km for _i, km in france["next"]), sum(km for _i, km in france["coast"])
    assert land + coast <= france["outline_km"] * 1.01


def _land_and_sea(shapes: dict, settings: dict):
    """The relationships of made-up areas, by name, with the sea in the oceans layer and the land layers named."""
    names = list(shapes)
    records = [{"id": n, "layer": shapes[n][0], "name": n} for n in names]
    geoms = [shapes[n][1] for n in names]
    kinds = [rel.AREA] * len(names)
    settings = {**rel.SETTINGS, **settings, "sea": ["oceans"], "water": ["oceans"],
                "land": ["countries", "national_parks", "mountain-ranges"]}
    ranks = {"countries": 2, "oceans": 2, "mountain-ranges": 3, "national_parks": 6, "lakes": 7}
    sums = rel.measure(records, geoms, kinds, settings, say=lambda s: None)
    out = rel.relationships(records, geoms, kinds, sums, ranks, {"oceans"}, settings)
    return {names[i]: {k: ([names[j] for j in v] if k in ("in", "same") else
                           {names[x[0]]: x[1] for x in v} if k in ("overlaps", "partly") else v)
                       for k, v in r.items()} for i, r in out.items()}


@pytest.mark.parametrize("fine", [False, True], ids=["whole boxes", "small boxes"])
def test_a_land_areas_share_inside_another_is_measured_on_its_land(fine):
    """P3-T28n, NAV-4: Exmoor, 1.2 percent of whose outline is in the sea, is wholly inside England, so Up from it
    goes there. A park truly across a land border stays partly inside each country, and a lake, which is water,
    is measured on its whole shape as before. Small boxes make some areas cover a box whole."""
    shapes = {
        "England": ("countries", shapely.box(0, 0, 10, 10)),
        "Wales": ("countries", shapely.box(-10, 0, 0, 10)),
        "Sea": ("oceans", shapely.box(10, -5, 20, 15).union(shapely.box(-10, -5, 20, 0)).union(
            shapely.box(-10, 10, 20, 15))),
        "Exmoor": ("national_parks", shapely.box(8, 4, 10.02, 6)),            # about 1 percent in the sea
        "Border park": ("national_parks", shapely.box(-1, 4, 1, 6)),          # half in each country
        "Hills": ("mountain-ranges", shapely.box(9, 3, 12, 7)),               # two thirds in the sea
        "Lagoon": ("lakes", shapely.box(9.98, 1, 10.02, 2)),                  # water: half in the sea
    }
    out = _land_and_sea(shapes, {"leaf_points": 0, "min_leaf_deg": 0.5} if fine else {})
    assert "England" in out["Exmoor"]["in"]
    assert "England" not in out["Exmoor"].get("overlaps", {})
    assert out["Exmoor"]["overlaps"]["Sea"] == pytest.approx(0.0099, abs=0.0005)   # against the sea, as before
    assert out["Border park"]["overlaps"]["England"] == pytest.approx(0.5, abs=0.01)
    assert out["Border park"]["overlaps"]["Wales"] == pytest.approx(0.5, abs=0.01)
    assert "in" not in out["Border park"]
    # Both in the sea: only the land they share counts, half of Exmoor's land and half of the hills' land.
    assert out["Exmoor"]["overlaps"]["Hills"] == pytest.approx(0.5, abs=0.003)
    assert out["Hills"]["overlaps"]["Exmoor"] == pytest.approx(0.5, abs=0.003)
    assert "England" in out["Hills"]["in"]
    assert "England" not in out["Lagoon"].get("in", []) and out["Lagoon"]["overlaps"]["England"] == pytest.approx(0.5, abs=0.01)


# Lines that go back over themselves, and the lines partly inside an area ---------------------------------------

def _lines_and_areas(lines: dict, areas: dict, settings: dict | None = None):
    """The relationships of made-up lines and areas, by name."""
    names = list(areas) + list(lines)
    records = [{"id": n, "layer": "roads" if n in lines else "counties", "name": n} for n in names]
    geoms = [areas[n] if n in areas else lines[n] for n in names]
    kinds = [rel.LINE if n in lines else rel.AREA for n in names]
    settings = {**rel.SETTINGS, **(settings or {})}
    sums = rel.measure(records, geoms, kinds, settings, say=lambda s: None)
    out = rel.relationships(records, geoms, kinds, sums, {"counties": 6, "roads": 9}, set(), settings)

    def name(v):
        return names[v] if isinstance(v, int) else [names[v[0]], *v[1:]]
    return {names[i]: {k: ([name(x) for x in v] if isinstance(v, list) else v) for k, v in r.items()}
            for i, r in out.items()}


@pytest.mark.parametrize("fine", [False, True], ids=["whole boxes", "small boxes"])
def test_a_roundabout_simplified_to_there_and_back_is_wholly_inside_not_half(fine):
    """Item 4b: a small roundabout, a closed way, simplified to two points and back (A, B, A), was stored as
    exactly 50 percent inside the county it is in, as cutting it with the county's outline kept the stretch
    once while its own length counted it twice. Now it is wholly inside. With small boxes, the big area covers
    a box whole, which is measured without cutting, and the small one is cut."""
    roundabout = shapely.LineString([(0.30, 0.30), (0.31, 0.30), (0.30, 0.30)])
    back = shapely.LineString([(0.6, 0.6), (0.9, 0.6), (0.7, 0.6), (0.7, 0.7)])   # goes back over part of itself
    out = _lines_and_areas({"Roundabout": roundabout, "Spur": back},
                           {"Shire": shapely.box(0.1, 0.1, 0.95, 0.95), "Country": shapely.box(-5, -5, 5, 5)},
                           {"leaf_points": 0, "min_leaf_deg": 0.25} if fine else None)
    for line in ("Roundabout", "Spur"):
        assert set(out[line]["in"]) == {"Shire", "Country"}, line
        assert "partly" not in out[line], line


def test_a_line_crossing_into_the_next_area_keeps_its_share():
    out = _lines_and_areas({"Road": shapely.LineString([(0.5, 0.5), (1.5, 0.5)])},
                           {"West": shapely.box(0, 0, 1, 1), "East": shapely.box(1, 0, 2, 1)})
    assert dict((a, s) for a, s in out["Road"]["partly"]) == {"West": 0.5, "East": 0.5}


def test_an_area_stores_the_lines_partly_inside_it_and_not_those_wholly_inside():
    """Item 4b: so Overlapping's "Lines crossing its border" reads them at once, not every line's relationships."""
    out = _lines_and_areas({"Through": shapely.LineString([(-0.5, 0.5), (0.5, 0.5)]),
                            "Inside": shapely.LineString([(0.2, 0.2), (0.4, 0.4)])},
                           {"Shire": shapely.box(0.1, 0.1, 1, 1)})   # off the 0 degree edge of the boxes
    shire = out["Shire"]
    assert set(shire["crossed_by"]) == {"Through", "Inside"}
    assert shire["partly_by"] == ["Through"]
    assert [c[0] for c in shire["crossed_at"]] == ["Through"]


def test_an_area_crossed_only_by_lines_wholly_inside_stores_an_empty_list():
    """So the application knows the pack has the list and need not look at each line."""
    out = _lines_and_areas({"Inside": shapely.LineString([(0.2, 0.2), (0.4, 0.4)])}, {"Shire": shapely.box(0, 0, 1, 1)})
    assert out["Shire"]["partly_by"] == []


def test_the_lines_partly_inside_are_kept_by_id(pack):
    hants = pack.relationships(HAMPSHIRE)
    assert ITCHEN in hants["partly_by"] and set(hants["partly_by"]) <= set(hants["crossed_by"])
    assert RHINE in pack.relationships(SWITZERLAND)["partly_by"]


def test_the_lines_partly_inside_are_written_by_id():
    by = rel.by_id({0: {"crossed_by": [1, 2], "partly_by": [2]}}, ["a", "b", "c"])
    assert by == {"a": {"crossed_by": ["b", "c"], "partly_by": ["c"]}}
