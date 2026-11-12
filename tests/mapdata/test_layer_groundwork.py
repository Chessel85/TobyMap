"""P3-T1e groundwork for the new layers of P3-T1e to P3-T1h: a layer made by a stage of its own does not
make the planet reading, the grid squares or the join run again; every id in a pack is different, whatever
layers share an OSM object; and a layer says how the map paints it (SCP-7, DMT-7, AD-13)."""
import shutil

import pytest

from mapcore.layers.catalogue import from_definition
from mapcore.render.scene import fill_of
from mapdata.paths import CONFIG_DIR
from mapdata.pipeline.build import fingerprint
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import load_pack
from mapdata.stages import write

PRINTS = {"planet": "p", "land-polygons": "l", "vliz-oceans": "v", "naturalearth-geographic-lines": "n",
          "naturalearth-marine-areas": "m"}
NEW_LAYER = ("  - {id: test-continents, name: Test continents, rank: 1, kind: land, made_by: continents, "
             "group: Physical, geometry: area, fill: none}\n")


def config_with(tmp_path, extra_layer: str):
    config = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    layers = config / "layers" / "base.yaml"
    layers.write_text(layers.read_text(encoding="utf-8") + extra_layer, encoding="utf-8")
    return config


def test_a_layer_made_by_a_stage_of_its_own_does_not_make_the_areas_again(tmp_path):
    """Adding the continents, mountain ranges or lakes must not reread the planet file or rebuild the world's
    grid squares, about 3 hours: only the layers the grid squares and join make are in their fingerprints."""
    with_layer = load_pack("world", config_with(tmp_path, NEW_LAYER))
    without = load_pack("world", CONFIG_DIR)
    assert with_layer.layers["test-continents"].made_by == "continents"
    for name in ("osm-areas", "squares", "join"):
        stage = next(s for s in without.stages if s["stage"] == name)
        assert fingerprint(with_layer, stage, "x", PRINTS) == fingerprint(without, stage, "x", PRINTS)
    write_stage = next(s for s in without.stages if s["stage"] == "write")
    assert fingerprint(with_layer, write_stage, "x", PRINTS) != fingerprint(without, write_stage, "x", PRINTS)


def test_an_area_layer_without_made_by_still_makes_the_areas_again(tmp_path):
    with_layer = load_pack("world", config_with(tmp_path, NEW_LAYER.replace("made_by: continents, ", "")))
    without = load_pack("world", CONFIG_DIR)
    stage = next(s for s in without.stages if s["stage"] == "squares")
    assert fingerprint(with_layer, stage, "x", PRINTS) != fingerprint(without, stage, "x", PRINTS)


def test_a_wrong_fill_stops_the_build_with_the_reason(tmp_path):
    with pytest.raises(BuildStopped, match="fill: blue; use land, water or none"):
        load_pack("test", config_with(tmp_path, NEW_LAYER.replace("fill: none", "fill: blue")))


def test_the_fill_is_written_into_the_pack_and_read_by_the_application(tmp_path):
    layer = load_pack("world", config_with(tmp_path, NEW_LAYER)).layers["test-continents"]
    d = layer.definition()
    assert d["fill"] == "none" and "made_by" not in d
    assert from_definition(d).fill == "none"
    assert from_definition({**d, "fill": "sparkly"}).fill is None   # from a newer pack: painted as before


def test_how_each_area_is_painted():
    ocean = ("o", 0, 1, "oceans")
    land = ("c", 1, 1, "countries")
    lake = ("l", 4, 1, "lakes")
    assert fill_of(ocean, None) == "water" and fill_of(land, None) == "land" and fill_of(lake, None) == "land"
    fills = {"lakes": "water", "countries": "land", "continents": "none"}
    assert fill_of(lake, fills) == "water"
    assert fill_of(("e", 4, 1, "continents"), fills) == "none"


def test_every_id_in_a_pack_is_different_whatever_layers_share_an_osm_object():
    """The world build of P3-T1d stopped at its last step: an island and a region were both osm:r1814783.
    The writing stage now gives the second an ending, and lists it, for any layers, now or later."""
    records = [
        {"id": "osm:r1", "layer": "regions", "name": "A"},
        {"id": "osm:r1", "layer": "islands", "name": "A"},
        {"id": "osm:r1", "layer": "lakes", "name": "A"},
        {"id": "osm:w2", "layer": "lakes", "name": "B"},
        {"id": "osm:w2", "layer": "lakes", "name": "B"},
        {"id": "osm:r1#as-islands", "layer": "rivers", "name": "C"},
    ]
    said = []
    assert write.keep_ids_unique(records, said.append) == 3
    ids = [r["id"] for r in records]
    assert len(set(ids)) == len(ids)
    assert ids[:5] == ["osm:r1", "osm:r1#as-islands#3", "osm:r1#as-lakes", "osm:w2", "osm:w2#2"]
    assert any("osm:r1 is used by the layer regions and again by the layer lakes" in s for s in said)


def test_ids_already_different_are_left_alone():
    records = [{"id": "osm:r1", "layer": "regions"}, {"id": "osm:r2", "layer": "islands"}]
    assert write.keep_ids_unique(records, print) == 0
    assert [r["id"] for r in records] == ["osm:r1", "osm:r2"]
