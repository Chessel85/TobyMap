"""The osm-water stage: every other lake, pond, reservoir and basin (P4-T1c, design docs/plan/p4-t1-design.md 3.6;
DAT-1, DAT-3, DP87).

osm-layer reads the named lakes with the world's ids; osm-water reads every other water area of OpenStreetMap, of
any size, into the layer lakes, named by OSM or, where it has no name, by its type's words in the templates
("Pond", "Unnamed lake"). An id already in the stage before is skipped, so a lake is never read twice. A river's
area (water=river) is left out: it belongs to the river's line.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import shapely

from mapdata.pipeline import features
from mapdata.stages import osm_source, osm_water

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "osm-raw"
UNNAMED_POND = "osm:w945871680"        # Brockenhurst: natural=water, water=pond, no name
MIRROR_POND = "osm:w124914274"         # Brockenhurst: named
UNNAMED_WATER = "osm:w125903597"       # Brockenhurst: natural=water, no water tag, no name
RIVER_AREA = "osm:r13309528"           # Brockenhurst: water=river
WASTEWATER = "osm:w945871702"          # Brockenhurst: water=wastewater


# The rules ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tags, kind", [
    ({"natural": "water", "water": "pond"}, "pond"),
    ({"natural": "water", "water": "lake"}, "lake"),
    ({"natural": "water"}, "lake"),
    ({"natural": "water", "water": "reservoir"}, "reservoir"),
    ({"landuse": "reservoir"}, "reservoir"),
    ({"landuse": "basin"}, "basin"),
    ({"natural": "water", "water": "basin"}, "basin"),
    ({"natural": "water", "water": "wastewater"}, "basin"),
    ({"natural": "water", "water": "lagoon"}, "lagoon"),
    ({"natural": "water", "water": "oxbow"}, "lake"),
    ({"water": "pond"}, "pond"),
])
def test_the_type_comes_from_the_water_tag(tags, kind):
    assert osm_water.type_of(tags) == kind


def test_a_river_area_is_left_out():
    assert osm_water.left_out({"natural": "water", "water": "river"}, ("river",))
    assert not osm_water.left_out({"natural": "water", "water": "pond"}, ("river",))


def test_the_words_for_unnamed_water_come_from_the_templates():
    words = osm_water.unnamed_words()
    assert words["pond"] == "Pond" and words["lake"] == "Unnamed lake"
    assert set(words) >= {"lake", "pond", "reservoir", "basin", "lagoon"}
    assert osm_water.fingerprint_extra({"stage": "osm-water"}) == {"unnamed_words": words}


def test_the_query_is_one_the_samples_understand():
    osm_source.parse_query(osm_water.QUERY)


# The stage, on the regional test pack ---------------------------------------------------------------------------

def _stage_folder(test_region_pack, kind):
    work = Path(test_region_pack).parents[2] / "working" / "test-region"
    return next(f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith(f"{kind}-"))


@pytest.fixture(scope="module")
def lakes(test_region_pack):
    records, geoms = features.load(_stage_folder(test_region_pack, "osm-water"))
    return {r["id"]: (r, g) for r, g in zip(records, geoms) if r["layer"] == "lakes"}


def test_an_unnamed_pond_in_brockenhurst_is_in_lakes_as_pond(lakes):
    r, g = lakes[UNNAMED_POND]
    assert r["name"] == "Pond" and r["type"] == "pond" and r["layer"] == "lakes"
    assert g.geom_type in ("Polygon", "MultiPolygon") and not g.is_empty


def test_named_and_unnamed_water_of_any_size(lakes):
    assert lakes[MIRROR_POND][0]["name"] == "Mirror Pond"
    assert lakes[UNNAMED_WATER][0]["name"] == "Unnamed lake"
    assert lakes[WASTEWATER][0]["type"] == "basin"
    assert RIVER_AREA not in lakes


def test_the_stage_writes_its_counts_for_the_quality_report(test_region_pack):
    report = json.loads((_stage_folder(test_region_pack, "osm-water") / osm_water.REPORT).read_text(encoding="utf-8"))
    assert report["counts"]["added"] >= 10 and report["counts"]["left_out_river"] >= 1
    assert report["counts"]["by_type"]["pond"] >= 5


def test_the_ponds_are_in_the_pack(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        records = {p.feature(n)["id"]: p.feature(n) for n in range(p.manifest["features"]["count"])}
    assert records[UNNAMED_POND]["name"] == "Pond" and records[UNNAMED_POND]["layer"] == "lakes"


# A lake already read ----------------------------------------------------------------------------------------------

def test_a_lake_already_read_keeps_its_world_id_and_is_not_read_twice(test_region_pack, tmp_path):
    """As osm-layer reads the named lakes with the world's ids before osm-water: Mirror Pond, already in the stage
    before, stays as it was and is not added again."""
    before = _stage_folder(test_region_pack, "small-islands")
    records, geoms = features.load(before)
    osm_layer_lake = {"id": MIRROR_POND, "layer": "lakes", "name": "Mirror Pond", "type": "lake",
                      "wikidata": "Q-made-up"}
    previous = tmp_path / "before"
    previous.mkdir()
    features.save(previous, records + [osm_layer_lake], geoms + [shapely.box(-1.58, 50.82, -1.579, 50.821)])
    folder = tmp_path / "osm-water"
    folder.mkdir()
    lines = []
    ctx = SimpleNamespace(settings={"stage": "osm-water", "source": "sample-osm-raw", "tolerance_m": 5},
                          previous=previous, folder=folder, folders=None,
                          earlier={"coverage": _stage_folder(test_region_pack, "coverage")}, claim=lambda p: p,
                          source=lambda key: (None, SAMPLES),
                          progress=SimpleNamespace(line=lines.append, log=lines.append))
    osm_water.run(ctx)
    out, _g = features.load(folder)
    mirror = [r for r in out if r["id"] == MIRROR_POND]
    assert mirror == [osm_layer_lake]
    assert len({r["id"] for r in out}) == len(out)
    assert any(r["id"] == UNNAMED_POND for r in out)
    report = json.loads((folder / osm_water.REPORT).read_text(encoding="utf-8"))
    assert report["counts"]["already_read"] == 1
