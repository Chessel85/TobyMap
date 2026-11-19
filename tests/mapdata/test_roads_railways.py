"""P3-T1i: motorways, trunk roads and main railway lines, joined into one feature per road and country (DAT-1)."""
import shapely

from mapdata.pipeline.build import STAGES
from mapdata.stages import osm_lines

ROADS = {"layer": "roads", "key": "ref", "unnamed": "Unnamed road"}
RAILWAYS = {"layer": "railways", "key": "name", "unnamed": "Unnamed railway line", "number_name": "Railway line"}


def line(*pts):
    return shapely.LineString(pts)


def test_the_stage_is_known():
    assert "osm-lines" in STAGES


def test_only_the_first_number_is_used():
    assert osm_lines.first_ref("A 3;IP 1") == "A 3"
    assert osm_lines.way_key({"ref": "M3", "name": "London Road"}, "ref") == ("ref", "M3")
    assert osm_lines.way_key({"name": "London Road"}, "ref") == ("name", "London Road")
    assert osm_lines.way_key({"ref": "ECM5", "name": "East Coast Main Line"}, "name") == \
        ("name", "East Coast Main Line")
    assert osm_lines.way_key({"ref": "5919"}, "name") == ("ref", "5919")
    assert osm_lines.way_key({}, "ref") is None


def test_a_roads_ways_are_one_feature_per_country():
    """The A1 in France and the A1 in Italy are two roads; three ways of the M3 are one."""
    ways = {1: ({"ref": "M3"}, "motorway", line((0, 0), (1, 0))),
            2: ({"ref": "M3"}, "motorway", line((1, 0), (2, 0))),
            3: ({"ref": "M3"}, "motorway", line((2, 0), (3, 0))),
            10: ({"ref": "A1"}, "motorway", line((10, 0), (11, 0))),
            11: ({"ref": "A1"}, "motorway", line((20, 0), (21, 0)))}
    country = {1: "gb", 2: "gb", 3: "gb", 10: "fr", 11: "it"}
    recs, geoms = osm_lines.group_layer(ROADS, ways, country, say=lambda _t: None)
    assert [(r["id"], r["name"], r["country"]) for r in recs] == [("osm:w1", "M3", "gb"), ("osm:w10", "A1", "fr"),
                                                                  ("osm:w11", "A1", "it")]
    assert geoms[0].geom_type == "LineString" and len(geoms[0].coords) == 4


def test_an_unnamed_link_joins_the_road_it_meets():
    """A chain of two unnamed ways at the end of the M3 joins it; an unnamed way meeting nothing is Unnamed road."""
    ways = {1: ({"ref": "M3"}, "motorway", line((0, 0), (1, 0))),
            2: ({}, "motorway", line((1, 0), (2, 0))),
            3: ({}, "motorway", line((2, 0), (3, 0))),
            9: ({}, "trunk road", line((50, 50), (51, 50)))}
    recs, _g = osm_lines.group_layer(ROADS, ways, {}, say=lambda _t: None)
    assert [(r["id"], r["name"]) for r in recs] == [("osm:w1", "M3"), ("osm:w9", "Unnamed road")]


def test_a_roads_name_is_added_when_most_ways_carry_it():
    ways = [{"ref": "A-8", "name": "Autovia del Cantabrico"}, {"ref": "A-8", "name": "Autovia del Cantabrico"},
            {"ref": "A-8"}]
    r = osm_lines.line_record("osm:w1", ROADS, ("ref", "A-8"), ways, ["motorway"] * 3)
    assert r["name"] == "A-8, Autovia del Cantabrico" and r["ref"] == "A-8" and r["type"] == "motorway"
    ways = [{"ref": "A6", "name": "Buxton Road"}, {"ref": "A6"}, {"ref": "A6"}]
    r = osm_lines.line_record("osm:w1", ROADS, ("ref", "A6"), ways, ["trunk road", "trunk road", "motorway"])
    assert r["name"] == "A6" and r["type"] == "trunk road"


def test_a_railway_is_named_by_its_name_or_its_number():
    ways = [{"name": "East Coast Main Line", "ref": "ECM5", "wikidata": "Q1"}, {"name": "East Coast Main Line"},
            {"name": "East Coast Main Line", "wikidata": "Q1"}]
    r = osm_lines.line_record("osm:w1", RAILWAYS, ("name", "East Coast Main Line"), ways, ["railway"] * 3)
    assert r == {"id": "osm:w1", "layer": "railways", "type": "railway", "name": "East Coast Main Line",
                 "wikidata": "Q1"}
    r = osm_lines.line_record("osm:w2", RAILWAYS, ("ref", "5919"), [{"ref": "5919"}], ["high-speed railway"])
    assert r["name"] == "Railway line 5919" and r["type"] == "high-speed railway"
    r = osm_lines.line_record("osm:w3", RAILWAYS, ("name", "Brennerbahn"),
                              [{"name": "Brennerbahn", "name:en": "Brenner Railway"}], ["railway"])
    assert r["name"] == "Brenner Railway" and r["local_name"] == "Brennerbahn"


def test_a_way_takes_the_country_it_is_in_or_the_nearest():
    countries = [("fr", shapely.box(0, 0, 10, 10)), ("de", shapely.box(10, 0, 20, 10))]
    pts = [shapely.Point(5, 5), shapely.Point(15, 5), shapely.Point(21, 5), shapely.Point(-1, 5)]
    assert osm_lines.countries_of(pts, countries) == ["fr", "de", "de", "fr"]
    assert osm_lines.countries_of(pts, []) == ["", "", "", ""]


def test_a_roundabout_keeps_its_ring_when_simplified():
    """Simplified plainly to 100 metres, a 50 metre roundabout shrinks to a point, and 641 roads in Western Europe
    were lost so. It keeps its ring."""
    ring = line((0, 0), (0.0005, 0), (0.0005, 0.0005), (0, 0.0005), (0, 0))
    g = osm_lines.simplify_line(ring, 100 / 111_320)
    assert not g.is_empty and g.length > 0 and g.is_closed
    long_road = line((0, 0), (0.5, 0.0001), (1, 0))
    assert len(osm_lines.simplify_line(long_road, 100 / 111_320).coords) == 2


def test_a_roads_parts_far_apart_are_two_roads():
    """P3-T28d: England's M3 and Belfast's M3, both in the United Kingdom, are two roads; each keeps its own ways."""
    ways = {1: ({"ref": "M3"}, "motorway", line((-1.0, 51.0), (-1.1, 51.1))),
            2: ({"ref": "M3"}, "motorway", line((-1.1, 51.1), (-1.2, 51.2))),
            7: ({"ref": "M3", "name": "Belfast Road"}, "motorway", line((-5.9, 54.6), (-5.92, 54.62)))}
    recs, geoms = osm_lines.group_layer(ROADS, ways, {1: "gb", 2: "gb", 7: "gb"}, say=lambda _t: None)
    assert [(r["id"], r["name"], r["country"]) for r in recs] == [("osm:w1", "M3", "gb"),
                                                                  ("osm:w7", "M3, Belfast Road", "gb")]
    assert len(geoms[0].coords) == 3


def test_a_small_gap_or_a_second_carriageway_keeps_one_road():
    """Two carriageways side by side, and a road whose ways stop short of each other by under the gap, are one."""
    ways = {1: ({"ref": "M3"}, "motorway", line((0, 0), (0.1, 0))),
            2: ({"ref": "M3"}, "motorway", line((0.1, 0.0003), (0, 0.0003))),
            3: ({"ref": "M3"}, "motorway", line((0.1 + (osm_lines.GAP_KM - 0.5) / 111.32, 0), (0.3, 0)))}
    recs, _g = osm_lines.group_layer(ROADS, ways, {}, say=lambda _t: None)
    assert [r["id"] for r in recs] == ["osm:w1"]


def test_the_gap_is_measured_in_km_on_the_ground():
    """At 60 degrees north a degree of longitude is about 55.7 km: two ways 0.1 degree apart east to west, 5.6 km,
    are near; two 0.1 degree apart north to south, 11.1 km, are not, with a gap of 8 km and no share."""
    east = [line((0, 60), (1, 60)), line((1.1, 60), (2, 60))]
    north = [line((0, 60), (0, 61)), line((0, 61.1), (0, 62))]
    assert osm_lines.road_parts(east, 8, share=0) == [[0, 1]]
    assert osm_lines.road_parts(north, 8, share=0) == [[0], [1]]
    far = [line((5, 5), (6, 5)), line((0, 0), (1, 0)), line((6, 5), (7, 5))]
    assert osm_lines.road_parts(far, 1, share=0) == [[0, 2], [1]]
    assert osm_lines.road_parts([line((0, 0), (1, 0))]) == [[0]]


KM = 111.32   # km in a degree at the equator, where the made-up roads below are


def test_a_motorways_unbuilt_stretch_keeps_one_road():
    """P3-T28d: two 100 km stretches of a motorway with 60 km unbuilt between them, as the A 4 in Germany has, are one
    road: the gap is more than GAP_KM but not more than GAP_SHARE times the shorter stretch's length."""
    parts = [line((0, 0), (100 / KM, 0)), line((160 / KM, 0), (260 / KM, 0))]
    assert osm_lines.GAP_KM < 60 <= osm_lines.GAP_SHARE * 100
    assert osm_lines.road_parts(parts) == [[0, 1]]


def test_a_short_stretch_far_from_the_rest_is_a_road_of_its_own():
    """A 5 km stretch 40 km from a 100 km road of the same number, as France's D roads of the same number in two
    departments are, is a road of its own: 40 km is more than GAP_SHARE times 5 km."""
    parts = [line((0, 0), (100 / KM, 0)), line((140 / KM, 0), (145 / KM, 0))]
    assert osm_lines.road_parts(parts) == [[0], [1]]


def test_long_roads_further_apart_than_the_most_are_two():
    """Two 100 km roads of the same number more than GAP_MOST_KM apart, such as the A6 in England and the A6 in
    Northern Ireland, are two, however long they are."""
    gap = osm_lines.GAP_MOST_KM + 10
    parts = [line((0, 0), (100 / KM, 0)), line(((100 + gap) / KM, 0), ((200 + gap) / KM, 0))]
    assert osm_lines.road_parts(parts) == [[0], [1]]
    assert osm_lines.road_parts(parts, most_km=gap + 10) == [[0, 1]]


def test_the_parts_join_through_each_other():
    """A road in three stretches, each within GAP_KM of the next, is one, though its ends are far apart; the ways of
    one stretch, side by side or end to end, stay together."""
    parts = [line((0, 0), (50 / KM, 0)), line((55 / KM, 0), (100 / KM, 0)), line((50 / KM, 0.0003), (0, 0.0003)),
             line((105 / KM, 0), (150 / KM, 0))]
    assert osm_lines.road_parts(parts) == [[0, 1, 2, 3]]


def test_each_part_keeps_the_name_and_takes_its_smallest_way_id():
    """The two M3s are both named M3, each with the id of its own smallest way, so the ids stay the same from build
    to build while the ways do; and unnamed ways far apart in a country stay one Unnamed road, as before."""
    ways = {5: ({"ref": "M3"}, "motorway", line((-5.9, 54.6), (-5.92, 54.62))),
            9: ({"ref": "M3"}, "motorway", line((-1.0, 51.0), (-1.1, 51.1))),
            3: ({"ref": "M3"}, "motorway", line((-1.1, 51.1), (-1.2, 51.2))),
            20: ({}, "trunk road", line((-3.0, 50.0), (-3.01, 50.0))),
            21: ({}, "trunk road", line((-1.0, 55.0), (-1.01, 55.0)))}
    recs, _g = osm_lines.group_layer(ROADS, ways, {w: "gb" for w in ways}, say=lambda _t: None)
    assert [(r["id"], r["name"]) for r in recs] == [("osm:w3", "M3"), ("osm:w5", "M3"), ("osm:w20", "Unnamed road")]


def test_a_railway_far_apart_is_split_too():
    ways = {1: ({"name": "Main Line"}, "railway", line((0, 0), (1, 0))),
            2: ({"name": "Main Line"}, "railway", line((10, 0), (10.05, 0)))}
    recs, _g = osm_lines.group_layer(RAILWAYS, ways, {}, say=lambda _t: None)
    assert [(r["id"], r["name"]) for r in recs] == [("osm:w1", "Main Line"), ("osm:w2", "Main Line")]
