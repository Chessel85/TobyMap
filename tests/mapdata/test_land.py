"""The osm-land stage: land use, parks, school grounds and national parks (P4-T1e, design
docs/plan/p4-t1-design.md 3.8; DAT-2, DAT-3).

Made-up areas test the classes and the joining; the regional test pack (the raw samples) tests the stage: Abbey
Gardens is in parks, Winchester College is in school-grounds, the New Forest National Park is in national_parks cut to
the land, and the log lists each class that differs from Shortbread's layer or zoom.
"""
import json
from pathlib import Path

import pytest
import shapely

from mapdata.pipeline import features
from mapdata.stages import osm_land, osm_source

E = 1 / 111_320 / 0.63   # a metre eastwards at latitude 51, in degrees
D = 1 / 111_320          # a metre northwards, in degrees


@pytest.fixture(scope="module")
def record():
    return osm_land.load_record()


def _square(x, y, size=100):
    return shapely.box(x, y, x + size * E, y + size * D)


def _area(oid, layer, kind, shape, name=""):
    return {"id": oid, "layer": layer, "type": kind, "name": name}, shape


def _join(pairs, parishes=()):
    recs, geoms, _sizes = osm_land.join_areas([r for r, _g in pairs], [g for _r, g in pairs], list(parishes))
    return {r["id"]: (r, g) for r, g in zip(recs, geoms)}


# Which areas are read, and into which layer -----------------------------------------------------------------------

@pytest.mark.parametrize("tags, layer, kind", [
    ({"leisure": "park", "name": "Abbey Gardens"}, "parks", "park"),
    ({"amenity": "school"}, "school-grounds", "school"),
    ({"amenity": "university"}, "school-grounds", "university"),
    ({"natural": "wood"}, "land-use", "woodland"),
    ({"landuse": "farmland"}, "land-use", "farmland"),
    ({"landuse": "village_green"}, "parks", "village green"),
    ({"boundary": "national_park"}, "national_parks", "national park"),
    ({"boundary": "protected_area", "protect_class": "5", "designation": "national_park"},
     "national_parks", "national park"),
    ({"boundary": "protected_area", "protect_class": "5"}, "national_parks", "protected landscape"),
    ({"leisure": "garden", "name": "Rose Garden"}, "parks", "garden"),
    ({"leisure": "garden", "access": "permissive"}, "parks", "garden"),
])
def test_each_tag_has_its_layer_and_type(record, tags, layer, kind):
    assert osm_land.classify(tags, record) == (layer, kind)


@pytest.mark.parametrize("tags", [
    {"leisure": "garden"},
    {"leisure": "garden", "access": "private"},
    {"boundary": "protected_area", "protect_class": "2"},
    {"highway": "residential"},
])
def test_a_private_garden_and_other_things_are_left_out(record, tags):
    assert osm_land.classify(tags, record) is None


def test_the_query_is_one_the_samples_understand(record):
    osm_source.parse_query(osm_land.query_for(record["classes"]))


def test_the_record_gives_each_class_a_layer_and_shortbread_comparison(record):
    assert {c["layer"] for c in record["classes"]} == set(osm_land.LAYERS)
    assert all("shortbread_layer" in c and c["type"] for c in record["classes"])


def test_differences_name_each_tag_whose_layer_or_zoom_differs(record):
    lines = osm_land.differences(record)
    text = "\n".join(lines)
    assert any(line.startswith("leisure=sports_centre:") and "Shortbread's layer sites" in line for line in lines)
    assert any(line.startswith("boundary=protected_area:") and "does not hold" in line for line in lines)
    assert any(line.startswith("natural=wood:") and "zoom 7" in line for line in lines)
    assert "amenity=school" not in text   # the same layer and zoom as Shortbread's


@pytest.mark.parametrize("tag, layer, zoom", [
    ("landuse=residential", "land", 10), ("landuse=farmland", "land", 10), ("landuse=cemetery", "land", 13),
    ("leisure=park", "land", 11), ("leisure=playground", "land", 11), ("leisure=stadium", "pois", 14),
    ("landuse=construction", "sites", 14), ("natural=heath", "land", 11), ("leisure=common", "none", None),
    ("leisure=nature_reserve", "none", None), ("boundary=national_park", "none", None),
    ("amenity=kindergarten", "none", None), ("natural=wetland", "none", None),
])
def test_shortbread_layers_and_zooms_are_its_schemas(record, tag, layer, zoom):
    """The Shortbread reference values as its schema 1.0 documents them (shortbread-tiles.org/schema/1.0, read on
    26 November 2026, P4-T1j); P4-T1e had entered them from memory."""
    (c,) = [c for c in record["classes"] if f"{c['key']}={c['value']}" == tag]
    assert c["shortbread_layer"] == layer and c.get("shortbread_zoom") == zoom


# Joining ------------------------------------------------------------------------------------------------------------

PARISH_A = ("p:a", shapely.box(-0.01, 50.99, 0.02, 51.02))
PARISH_B = ("p:b", shapely.box(0.02, 50.99, 0.05, 51.02))


def test_two_touching_unnamed_woods_in_one_parish_are_one_woodland():
    out = _join([_area("osm:w10", "land-use", "woodland", _square(0, 51)),
                 _area("osm:w9", "land-use", "woodland", _square(100 * E, 51))], [PARISH_A, PARISH_B])
    assert list(out) == ["osm:w9"]
    r, g = out["osm:w9"]
    assert g.area == pytest.approx(2 * _square(0, 51).area, rel=1e-4) and g.geom_type == "Polygon"
    made = osm_land.make_records([r], [g], set(), None, "x")[0][0]
    assert made["name"] == "Woodland"


def test_woods_that_do_not_touch_or_are_named_or_differ_in_type_stay_separate():
    out = _join([_area("osm:w1", "land-use", "woodland", _square(0, 51)),
                 _area("osm:w2", "land-use", "woodland", _square(300 * E, 51)),
                 _area("osm:w3", "land-use", "woodland", _square(100 * E, 51), name="Big Wood"),
                 _area("osm:w4", "land-use", "heath", _square(0, 51 + 100 * D))], [PARISH_A])
    assert sorted(out) == ["osm:w1", "osm:w2", "osm:w3", "osm:w4"]


def test_touching_woods_in_two_parishes_are_two():
    x = 0.02 - 100 * E   # the second square starts on the boundary of the parishes
    out = _join([_area("osm:w1", "land-use", "woodland", _square(x, 51)),
                 _area("osm:w2", "land-use", "woodland", _square(x + 100 * E, 51))], [PARISH_A, PARISH_B])
    assert sorted(out) == ["osm:w1", "osm:w2"]


def test_a_chain_of_touching_areas_is_one_and_the_smallest_id_is_kept():
    out = _join([_area(f"osm:w{n}", "land-use", "farmland", _square(i * 100 * E, 51))
                 for i, n in enumerate([30, 20, 10, 40])], [PARISH_A])
    assert list(out) == ["osm:w10"]


def test_national_parks_are_never_joined():
    out = _join([_area("osm:r1", "national_parks", "national park", _square(0, 51)),
                 _area("osm:r2", "national_parks", "national park", _square(100 * E, 51))], [PARISH_A])
    assert len(out) == 2


# The stage, on the regional test pack -------------------------------------------------------------------------------

def _stage_folder(test_region_pack, kind):
    work = Path(test_region_pack).parents[2] / "working" / "test-region"
    return next(f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith(f"{kind}-"))


@pytest.fixture(scope="module")
def stage(test_region_pack):
    folder = _stage_folder(test_region_pack, "osm-land")
    records, geoms = features.load(folder)
    mine = {r["id"]: (r, g) for r, g in zip(records, geoms) if r["layer"] in osm_land.LAYERS}
    return mine, folder


def _named(mine, name, layer):
    return [(r, g) for r, g in mine.values() if r["name"] == name and r["layer"] == layer]


def test_abbey_gardens_is_in_parks(stage):
    mine, _folder = stage
    r, g = mine["osm:w76027863"]
    assert r["name"] == "Abbey Gardens" and r["layer"] == "parks" and r["type"] == "park"
    assert g.area > 0


def test_winchester_college_is_in_school_grounds(stage):
    mine, _folder = stage
    found = _named(mine, "Winchester College", "school-grounds")
    assert found and found[0][0]["type"] == "school"


def test_the_new_forest_national_park_is_in_national_parks_cut_to_the_land(stage, test_region_pack):
    mine, folder = stage
    found = _named(mine, "New Forest National Park", "national_parks")
    assert len(found) == 1
    r, g = found[0]
    assert r["type"] == "national park" and r["id"] == "osm:r2678988"
    countries = [gg for rr, gg in zip(*features.load_layers(folder, {"countries"})) if rr["layer"] == "countries"]
    land = shapely.union_all(countries)
    assert shapely.area(shapely.difference(g, land.buffer(1e-6))) == pytest.approx(0, abs=1e-9)


def test_a_private_garden_is_not_in_the_pack(stage):
    mine, _folder = stage
    data = json.loads((Path(__file__).resolve().parents[1] / "samples" / "osm-raw" / "winchester.geojson")
                      .read_text(encoding="utf-8"))
    private = [f"osm:{f['properties']['osm']}" for f in data["features"]
               if f["properties"]["tags"].get("leisure") == "garden" and not f["properties"]["tags"].get("name")
               and f["properties"]["tags"].get("access") not in ("yes", "permissive")]
    assert private and not set(private) & set(mine)


def test_the_stage_joins_unnamed_areas_and_writes_the_differences(stage):
    _mine, folder = stage
    report = json.loads((folder / osm_land.REPORT).read_text(encoding="utf-8"))
    land_use = report["counts"]["layers"]["land-use"]
    assert land_use["read"] > land_use["features"] > 0
    assert any(line.startswith("leisure=sports_centre:") for line in report["shortbread_differences"])
    assert report["counts"]["joined_areas"] > 0


def test_the_areas_are_in_the_pack(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        records = {p.feature(n)["id"]: p.feature(n) for n in range(p.manifest["features"]["count"])}
    assert records["osm:w76027863"]["layer"] == "parks"
