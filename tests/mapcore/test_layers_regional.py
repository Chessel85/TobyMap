"""The shown fields of a regional pack's layers (P4-T1i; VIS-1, VIS-2, SCP-6, SCP-7, LOC-2)."""
from pathlib import Path

import pytest
import yaml

from mapcore import views
from mapcore.describe import earcon_list
from mapcore.render import themes
from mapcore.world.state import DEFAULT_ZOOMS

ROOT = Path(__file__).resolve().parents[2]
LAYERS = yaml.safe_load((ROOT / "mapdata/config/layers/regional.yaml").read_text(encoding="utf-8"))["layers"]
IDS = [layer["id"] for layer in LAYERS]
TEMPLATES = yaml.safe_load((ROOT / "mapcore/describe/templates.yaml").read_text(encoding="utf-8"))
EVENTS = {e["event"] for e in earcon_list()}
PACKS = ["great-britain", "england", "hampshire-isle-of-wight", "test-region"]


@pytest.mark.parametrize("layer", LAYERS, ids=IDS)
def test_each_layer_has_its_shown_fields(layer):
    assert layer["switched_on"] is True
    if layer["id"] != "national_parks":   # the national parks have no zoom limit
        assert layer["max_zoom_m"] in DEFAULT_ZOOMS
    assert layer["id"] in TEMPLATES["details"]["layers"]


@pytest.mark.parametrize("layer", LAYERS, ids=IDS)
def test_each_layer_sound_is_an_earcon_event(layer):
    for field in ("sound", "crossing_earcon"):
        if field in layer:
            assert layer[field] in EVENTS


def test_the_new_sound_events_are_listed():
    assert {"layer_path", "layer_park", "layer_poi"} <= EVENTS


@pytest.mark.parametrize("layer", LAYERS, ids=IDS)
def test_each_layer_has_a_place_in_the_drawing_order_and_the_said_order(layer):
    if layer["geometry"] != "point":   # places are drawn last, as markers, and said by rank
        assert layer["id"] in views.drawing_order()
    if layer["geometry"] == "area":
        for view in views.built_in():
            assert layer["id"] in view["said"]
            assert layer["id"] in view["layers"]


def test_the_drawing_order_puts_the_new_layers_as_designed():
    area = ["counties", "districts", "parishes", "land-use", "parks", "school-grounds", "national_parks",
            "physical-regions", "islands", "mountain-ranges", "lakes", "rivers", "streams", "outlines", "paths",
            "streets", "main-roads", "roads", "railways"]
    assert [i for i in views.drawing_order() if i in area] == area


def test_the_political_layers_run_down_to_the_parishes():
    assert views.political_layers() == ["countries", "regions", "counties", "districts", "parishes"]


def test_the_said_order_starts_from_the_designed_one():
    said = views.find("political")["said"]
    assert said[:10] == ["lakes", "school-grounds", "parks", "land-use", "seas", "oceans", "territorial-waters",
                         "parishes", "districts", "national_parks"]


@pytest.mark.parametrize("name", themes.names())
def test_every_kind_has_a_colour_in_every_theme_that_keeps_the_contrast(name):
    t = themes.theme(name)
    for kind in ("land-use", "parks", "school-grounds"):
        assert t["physical"][kind].startswith("#")
    if t["high_contrast"]:
        assert themes.contrast_problems(t) == []


def test_the_national_parks_definition_is_the_same_in_the_test_pack_and_a_regional_pack():
    samples = {x["id"]: x for x in yaml.safe_load(
        (ROOT / "mapdata/config/layers/samples.yaml").read_text(encoding="utf-8"))["layers"]}
    regional = {x["id"]: x for x in LAYERS}["national_parks"]
    # made_by is a build field only the regional pack's stage needs.
    assert {k: v for k, v in regional.items() if k != "made_by"} == samples["national_parks"]


@pytest.mark.parametrize("pack", PACKS)
def test_each_regional_pack_sets_its_drawing_levels(pack):
    data = yaml.safe_load((ROOT / f"mapdata/config/packs/{pack}.yaml").read_text(encoding="utf-8"))
    write = next(s for s in data["stages"] if s["stage"] == "write")
    levels = write["drawing_levels"]
    assert [lv["view_km"] for lv in levels] == [50, 150]
    assert [lv["tile_level"] for lv in levels] == [9, 7]
