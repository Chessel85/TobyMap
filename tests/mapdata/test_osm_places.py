"""The osm-places stage's records (P3-T1b, DP168): seas, bays and straits that OSM has only as a point."""
import shapely

from mapdata.pipeline.settings import load_pack
from mapdata.stages import osm_places


def test_a_place_takes_the_english_name_and_keeps_the_local_one():
    r = osm_places.place_record("osm:n1", {"name": "Golfe du Morbihan", "name:en": "Gulf of Morbihan",
                                           "wikidata": "Q1"}, "sea-places", "bay")
    assert r == {"id": "osm:n1", "layer": "sea-places", "name": "Gulf of Morbihan", "type": "bay",
                 "local_name": "Golfe du Morbihan", "wikidata": "Q1"}
    r = osm_places.place_record("osm:n2", {"name": "The Solent", "name:en": "", "wikidata": ""}, "sea-places", "strait")
    assert r == {"id": "osm:n2", "layer": "sea-places", "name": "The Solent", "type": "strait"}
    assert osm_places.place_record("osm:n3", {"name": "", "name:en": "", "wikidata": ""}, "sea-places", "bay") is None


def test_a_place_already_a_sea_is_left_out():
    records = [{"name": "North Sea"}, {"name": "Golfe de Gascogne", "local_name": "Bay of Biscay"},
               {"name": "The Solent"}]
    geoms = [shapely.Point(3, 55), shapely.Point(-4, 45), shapely.Point(-1.3, 50.8)]
    kept, kept_g, left = osm_places.leave_out_repeats(records, geoms, {"North Sea", "Bay of Biscay"})
    assert [r["name"] for r in kept] == ["The Solent"] and len(kept_g) == 1
    assert left == ["North Sea", "Golfe de Gascogne"]


def test_the_world_pack_reads_the_sea_places_into_a_layer_of_places():
    pack = load_pack("world")
    stage = next(s for s in pack.stages if s["stage"] == "osm-places")
    assert stage["layer"] == "sea-places" and stage["same_as"] == "seas"
    assert pack.layers["sea-places"].geometry == "point"
    assert {q["type"] for q in stage["queries"]} == {"sea", "bay", "strait"}
