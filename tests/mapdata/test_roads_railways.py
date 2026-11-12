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
