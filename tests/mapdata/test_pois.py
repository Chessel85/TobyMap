"""The osm-pois stage: points of interest in four layers, and the villages (P4-T1f, design
docs/plan/p4-t1-design.md 3.10; DAT-2, DAT-3).

Made-up tags test the category table; the regional test pack (the raw samples) tests the stage: a bus stop on the
Broadway is in stops, an unnamed bench is "Bench", a shop mapped as an area is a place inside it, and the villages are
in villages with the areas they are in. The CSV for the product owner is made again identical from the table.
"""
import csv
import io
import json
from pathlib import Path

import pytest
import shapely

from mapdata.pipeline import features
from mapdata.stages import osm_pois, osm_source

REPO = Path(__file__).resolve().parents[2]
SAMPLES = REPO / "tests" / "samples" / "osm-raw"


@pytest.fixture(scope="module")
def record():
    return osm_pois.load_record()


def _key(found):
    return None if found is None else found["key"]


# The category table -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tags, kind, key, layer", [
    ({"highway": "bus_stop", "name": "Broadway (Stop E)"}, "node", "bus_stop", "stops"),
    ({"public_transport": "platform", "bus": "yes"}, "node", "bus_stop", "stops"),
    ({"railway": "station"}, "area", "railway_station", "stops"),
    ({"highway": "crossing"}, "node", "crossing", "stops"),
    ({"shop": "supermarket"}, "area", "supermarket", "shops-food"),
    ({"shop": "books"}, "node", "shop", "shops-food"),
    ({"amenity": "pub"}, "area", "pub", "shops-food"),
    ({"amenity": "place_of_worship", "religion": "christian"}, "area", "church", "services"),
    ({"amenity": "place_of_worship"}, "node", "place_of_worship", "services"),
    ({"amenity": "school"}, "node", "school", "services"),
    ({"amenity": "parking"}, "area", "car_park", "services"),
    ({"amenity": "bench"}, "node", "bench", "street-furniture"),
    ({"amenity": "waste_basket"}, "node", "bin", "street-furniture"),
    ({"amenity": "post_box"}, "node", "post_box", "street-furniture"),
])
def test_each_tag_has_its_category_and_layer(record, tags, kind, key, layer):
    found = osm_pois.classify(tags, kind, record["categories"])
    assert found["key"] == key and found["layer"] == layer


@pytest.mark.parametrize("tags, kind", [
    ({"amenity": "school"}, "area"),    # a school ground, the osm-land stage's
    ({"shop": "no"}, "node"),
    ({"public_transport": "platform"}, "node"),   # a platform with no bus=yes
    ({"highway": "residential"}, "node"),
])
def test_what_is_not_a_point_of_interest_is_left_out(record, tags, kind):
    assert osm_pois.classify(tags, kind, record["categories"]) is None


def test_a_node_with_two_matching_categories_takes_the_first(record):
    # A bus stop with a bench: stops come before street furniture in the table.
    assert _key(osm_pois.classify({"highway": "bus_stop", "amenity": "bench"}, "node", record["categories"])) \
        == "bus_stop"
    # A bakery that is also a cafe: the bakery is first in the table.
    assert _key(osm_pois.classify({"shop": "bakery", "amenity": "cafe"}, "node", record["categories"])) == "bakery"
    made_up = [{"key": "b", "layer": "services", "tags": [{"amenity": "x"}]},
               {"key": "a", "layer": "stops", "tags": [{"amenity": "x"}]}]
    assert _key(osm_pois.classify({"amenity": "x"}, "node", made_up)) == "b"


def test_every_category_has_its_words_and_a_known_layer(record):
    words = osm_pois.category_words()
    keys = [c["key"] for c in record["categories"]]
    assert len(keys) == len(set(keys))
    assert all(k in words and words[k] for k in keys)
    assert {c["layer"] for c in record["categories"]} == set(osm_pois.LAYERS)


def test_the_query_is_one_the_samples_understand(record):
    osm_source.parse_query(osm_pois.query_for(record["categories"]))


def test_an_unnamed_place_is_named_by_its_words_with_a_capital():
    recs = [{"id": "osm:n2", "layer": "street-furniture", "type": "bench", "name": ""},
            {"id": "osm:n1", "layer": "stops", "type": "bus stop", "name": "Broadway (Stop E)"}]
    out, _geoms, skipped = osm_pois.make_records(recs, [shapely.Point(0, 0)] * 2, set(), "planet")
    assert [(r["id"], r["name"], r["type"]) for r in out] == [("osm:n1", "Broadway (Stop E)", "bus stop"),
                                                             ("osm:n2", "Bench", "bench")]
    assert skipped == 0


def test_a_place_already_in_the_pack_is_not_added_again():
    recs = [{"id": "osm:w5", "layer": "services", "type": "car park", "name": ""}]
    out, _geoms, skipped = osm_pois.make_records(recs, [shapely.Point(0, 0)], {"osm:w5"}, "planet")
    assert out == [] and skipped == 1


# The CSV for the product owner --------------------------------------------------------------------------------------

def test_the_csv_is_made_again_identical_from_the_table():
    import importlib.util

    spec = importlib.util.spec_from_file_location("make_poi_categories_csv",
                                                  REPO / "tools" / "make_poi_categories_csv.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    path = REPO / "docs" / "plan" / "p4-t1f-poi-categories.csv"
    made = tool.make_csv(tool.read_counts(path))
    assert made == path.read_bytes().decode("utf-8")
    rows = list(csv.reader(io.StringIO(made)))
    assert rows[0] == ["category", "words", "layer", "tags", "count in the rehearsal",
                       "count in the United Kingdom"]
    assert [r[0] for r in rows[1:]] == [c["key"] for c in osm_pois.load_record()["categories"]]
    bus = next(r for r in rows if r[0] == "bus_stop")
    assert bus[1] == "bus stop" and bus[2] == "stops" and "highway=bus_stop" in bus[3]


# The stage, on the regional test pack -------------------------------------------------------------------------------

def _stage_folders(test_region_pack, kind):
    work = Path(test_region_pack).parents[2] / "working" / "test-region"
    return [f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith(f"{kind}-")]


@pytest.fixture(scope="module")
def stage(test_region_pack):
    folder = _stage_folders(test_region_pack, "osm-pois")[0]
    records, geoms = features.load(folder)
    mine = {r["id"]: (r, g) for r, g in zip(records, geoms) if r["layer"] in osm_pois.LAYERS}
    return mine, folder


def _raw(name):
    data = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
    return {f"osm:{f['properties']['osm']}": f for f in data["features"]}


def test_a_bus_stop_on_the_broadway_is_in_stops(stage):
    mine, _folder = stage
    r, g = mine["osm:n13680919369"]
    assert (r["layer"], r["name"], r["type"]) == ("stops", "Broadway St Johns (Stand 8)", "bus stop")
    assert (round(g.x, 7), round(g.y, 7)) == (-1.3095295, 51.0614626)


def test_an_unnamed_bench_is_bench(stage):
    mine, _folder = stage
    benches = [r for r, _g in mine.values() if r["type"] == "bench"]
    assert benches and all(r["layer"] == "street-furniture" for r in benches)
    raw = _raw("winchester.geojson")
    unnamed = [r for r in benches if not raw.get(r["id"], {}).get("properties", {}).get("tags", {}).get("name")
               and r["id"] in raw]
    assert unnamed and all(r["name"] == "Bench" for r in unnamed)


def test_a_shop_mapped_as_an_area_becomes_a_place_inside_it(stage):
    mine, _folder = stage
    raw = {}
    for name in ("winchester.geojson", "brockenhurst.geojson", "lymington.geojson"):
        raw.update(_raw(name))
    areas = [oid for oid, f in raw.items() if f["properties"]["kind"] == "area"
             and f["properties"]["tags"].get("shop") == "supermarket" and oid in mine]
    assert areas
    for oid in areas:
        r, g = mine[oid]
        assert g.geom_type == "Point" and r["layer"] == "shops-food" and r["type"] == "supermarket"
        area = shapely.from_geojson(json.dumps(raw[oid]["geometry"]))
        assert shapely.contains(area, g) or shapely.distance(area, g) < 1e-7


def test_the_stage_writes_its_counts(stage):
    _mine, folder = stage
    report = json.loads((folder / osm_pois.REPORT).read_text(encoding="utf-8"))
    layers = report["counts"]["layers"]
    assert set(layers) == set(osm_pois.LAYERS)
    assert all(layers[k]["places"] > 0 for k in osm_pois.LAYERS)
    assert report["counts"]["by_category"]["bus_stop"] > 0


def test_the_villages_are_in_villages_with_the_areas_they_are_in(test_region_pack):
    folder = _stage_folders(test_region_pack, "osm-pois")[-1]
    records, geoms = features.load(folder)
    villages = {r["id"]: (r, g) for r, g in zip(records, geoms) if r["layer"] == "villages"}
    r, g = villages["osm:n271485"]
    assert (r["name"], r["type"]) == ("Brockenhurst", "village")
    within = [w["layer"] for w in r["within"]]
    assert within[:3] == ["countries", "regions", "counties"]
    assert "districts" in within and "parishes" in within
    assert any(rr["type"] == "suburb" for rr, _g in villages.values())


def test_the_points_of_interest_and_villages_are_in_the_pack(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        records = {p.feature(n)["id"]: p.feature(n) for n in range(p.manifest["features"]["count"])}
    assert records["osm:n13680919369"]["layer"] == "stops"
    assert records["osm:n13680919369"]["type"] == "bus stop"
    assert records["osm:n271485"]["layer"] == "villages"
