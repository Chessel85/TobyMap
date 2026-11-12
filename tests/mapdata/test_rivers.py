"""P3-T1g: whole rivers from OpenStreetMap's river ways, checked against Natural Earth (DAT-1, DP169)."""
import json

import pytest
import shapely

from mapdata.pipeline.build import STAGES
from mapdata.stages import osm_rivers


def test_a_rivers_ways_are_joined_from_source_to_mouth():
    """Ways drawn in the direction of flow, given in any order, are joined into one line from source to mouth."""
    ways = [shapely.LineString([(2, 0), (3, 0)]), shapely.LineString([(0, 0), (1, 0)]),
            shapely.LineString([(1, 0), (2, 0)])]
    g = osm_rivers.join_lines(ways)
    assert g.geom_type == "LineString"
    assert list(g.coords) == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_a_river_with_branches_is_one_feature_with_several_lines():
    """A delta: the river splits into two branches. Each line keeps the direction of flow."""
    ways = [shapely.LineString([(0, 0), (1, 0)]), shapely.LineString([(1, 0), (2, 1)]),
            shapely.LineString([(1, 0), (2, -1)])]
    g = osm_rivers.join_lines(ways)
    assert g.geom_type == "MultiLineString"
    for part in g.geoms:
        assert part.coords[0][0] < part.coords[-1][0]   # every line flows east, as drawn
    assert shapely.get_coordinates(g)[:, 0].max() == 2


def test_a_river_length_is_measured_along_the_earth():
    one_degree = shapely.LineString([(0, 0), (0, 1)])
    assert osm_rivers.length_km(one_degree) == pytest.approx(111.2, abs=0.2)
    at_60 = shapely.LineString([(0, 60), (1, 60)])
    assert osm_rivers.length_km(at_60) == pytest.approx(55.6, abs=0.2)


def test_ways_are_grouped_by_their_rivers_wikidata_link():
    """A relation's ways make its river; a way in no relation with the same link joins it; ways with another
    link make another river, named as most of its ways are; ways with no link are left out (DP169)."""
    ways = {1: ({"name": "Rhein", "wikidata": "Q584"}, None), 2: ({"name": "Rhein", "wikidata": "Q584"}, None),
            3: ({"name": "Rhin", "wikidata": "Q584"}, None),
            10: ({"name": "Aare", "wikidata": "Q1"}, None), 11: ({"name": "Aar", "wikidata": "Q1"}, None),
            12: ({"name": "Aare", "wikidata": "Q1"}, None),
            20: ({"name": "Brook"}, None)}
    relations = [("osm:r5", {"name": "Rhein", "name:en": "Rhine", "wikidata": "Q584"}, [1, 2])]
    got = osm_rivers.group_ways(relations, ways)
    assert [(t["id"], t["name"], wids) for t, wids in got] == [("osm:r5", "Rhein", [1, 2, 3]),
                                                               ("osm:w10", "Aare", [10, 11, 12])]


def test_a_river_takes_the_english_name_and_keeps_the_local_one():
    r = osm_rivers.river_record("osm:r5", {"name": "Rhein", "name:en": "Rhine", "wikidata": "Q584"}, "rivers")
    assert r == {"id": "osm:r5", "layer": "rivers", "name": "Rhine", "local_name": "Rhein", "type": "river",
                 "wikidata": "Q584"}
    assert osm_rivers.river_record("osm:r6", {"wikidata": "Q2"}, "rivers") is None


def test_natural_earth_rivers_are_matched_by_link_name_or_place(tmp_path):
    ne = tmp_path / "rivers.geojson"
    feats = [
        {"type": "Feature", "properties": {"featurecla": "River", "name": "Rhine", "wikidataid": "Q584"},
         "geometry": {"type": "LineString", "coordinates": [[8, 47.5], [8, 52]]}},
        {"type": "Feature", "properties": {"featurecla": "River", "name": "Loire", "wikidataid": "Q1471"},
         "geometry": {"type": "LineString", "coordinates": [[2, 45], [-2, 47.2]]}},
        {"type": "Feature", "properties": {"featurecla": "River", "name": "Ebro", "wikidataid": ""},
         "geometry": {"type": "LineString", "coordinates": [[-4, 43], [0.8, 40.7]]}},
        {"type": "Feature", "properties": {"featurecla": "River", "name": "Seine", "wikidataid": "Q1471x"},
         "geometry": {"type": "LineString", "coordinates": [[4.7, 47.5], [0.1, 49.5]]}},
        {"type": "Feature", "properties": {"featurecla": "River", "name": "Short", "wikidataid": "Q9"},
         "geometry": {"type": "LineString", "coordinates": [[0, 50], [0, 50.5]]}},
        {"type": "Feature", "properties": {"featurecla": "Lake Centerline", "name": "Lake", "wikidataid": ""},
         "geometry": {"type": "LineString", "coordinates": [[0, 40], [5, 40]]}},
    ]
    ne.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    rivers = osm_rivers.natural_earth_rivers(ne, None, 300)
    assert [r["name"] for r in rivers] == ["Rhine", "Ebro", "Seine", "Loire"]
    records = [{"name": "Rhein", "wikidata": "Q584"}, {"name": "Ebro"},
               {"name": "La Seine", "wikidata": "Q1"}]
    seine_line = shapely.LineString([(4.7, 47.5), (0.1, 49.5)])
    geoms = [shapely.LineString([(8, 47.5), (8, 52)]), shapely.LineString([(-4, 43), (0.8, 40.7)]), seine_line]
    gone = osm_rivers.unmatched(rivers, records, geoms, within_km=5)
    assert [r["name"] for r in gone] == ["Loire"]


def test_the_stage_is_known_and_reads_in_its_own_process():
    assert STAGES["osm-rivers"].module == "mapdata.stages.osm_rivers"
    assert callable(osm_rivers.main)


def test_a_section_of_a_river_is_not_a_river_of_its_own():
    """OSM has a relation for the Upper Rhine, a section of the Rhine, with its own Wikidata link. It is left out,
    as its ways are the Rhine's. A tributary sharing one way at its mouth is kept."""
    rivers = [({"id": "osm:r1", "name": "Rhine"}, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]),
              ({"id": "osm:r2", "name": "Upper Rhine"}, [3, 4, 5, 6, 7]),
              ({"id": "osm:r3", "name": "Aare"}, [11, 20, 21, 22])]
    kept, left = osm_rivers.leave_out_sections(rivers)
    assert [t["name"] for t, _w in kept] == ["Rhine", "Aare"]
    assert left == ["Upper Rhine (osm:r2), a section of Rhine (osm:r1)"]


def test_a_relation_with_no_link_of_its_own_is_a_river_too():
    """A waterway relation with no Wikidata link takes the link most of its ways carry; with none, it is a river of
    its own, marked, which the reading keeps only if it is long (min_km_unlinked), such as Brazil's Rio Verde."""
    ways = {1: ({"name": "Kotto", "wikidata": "Q7"}, None), 2: ({"name": "Kotto", "wikidata": "Q7"}, None),
            3: ({"name": "Kotto"}, None), 10: ({"name": "Rio Verde"}, None), 11: ({"name": "Rio Verde"}, None)}
    relations = [("osm:r5", {"name": "Kotto"}, [1, 2, 3]), ("osm:r6", {"name": "Rio Verde"}, [10, 11])]
    got = osm_rivers.group_ways(relations, ways)
    assert [(t["id"], t.get("wikidata"), t.get("unlinked", False), w) for t, w in got] == [
        ("osm:r5", "Q7", False, [1, 2, 3]), ("osm:r6", None, True, [10, 11])]


def test_names_match_without_accents_or_words_such_as_river():
    assert osm_rivers.same_name("Aldan", {"name": "Aldan River", "local_name": "Алдан"})
    assert osm_rivers.same_name("Mahäna Nadï", {"name": "Mahana Nadi"})
    assert osm_rivers.same_name("Velhas", {"name": "Rio das Velhas"})
    assert not osm_rivers.same_name("Verde", {"name": "Rio Verdejo"})
    assert not osm_rivers.same_name("River", {"name": "River"})   # nothing left to compare


def test_lines_cut_by_a_reading_box_are_kept_whatever_shape_the_cut_gives():
    cut = shapely.GeometryCollection([shapely.MultiLineString([[(0, 0), (1, 0)], [(1, 0), (2, 0)]]),
                                      shapely.Point(5, 5)])
    g = osm_rivers.join_lines([cut])
    assert g.geom_type == "LineString" and list(g.coords) == [(0, 0), (1, 0), (2, 0)]
