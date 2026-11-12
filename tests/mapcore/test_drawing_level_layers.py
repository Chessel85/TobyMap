"""P3-T1e: a drawing level holds only the layers that can be seen at the zooms it serves (VIS-1, NAV-13).

In the world pack, the 98,000 bays and straits that are places, visible only to 100 km, were in every drawing
level, and every map at a wide zoom decoded them all: 4 to 8 seconds a map. A level now lists the layers it
holds, and a layer the user has widened beyond them is read from the finest level that holds it (SCP-7)."""
from types import SimpleNamespace

from mapcore.render.scene import EXACT_BELOW_KM, drawing_source, finest_holding, holds, plan_for
from mapdata.stages.write import held_layers

LEVELS = [{"id": 0, "tile_level": 1, "view_km": 4000, "min_km2": 20000},
          {"id": 1, "tile_level": 3, "view_km": 1000, "min_km2": 1000},
          {"id": 2, "tile_level": 5, "view_km": 150, "min_km2": 40}]
TOPS = {"countries": None, "regions": 1000.0, "counties": 100.0, "sea-places": 100.0, "graticule": None,
        "close-only": 20.0}


def test_a_level_leaves_out_the_layers_whose_zoom_range_ends_below_the_zooms_it_serves():
    held = held_layers(LEVELS, TOPS)
    # Level 2 serves 25 to 150 km: everything visible beyond 25 km.
    assert held[2] == {"countries", "regions", "counties", "sea-places", "graticule"}
    # Level 1 serves 150 to 1,000 km: no counties or places, which end at 100 km.
    assert held[1] == {"countries", "regions", "graticule"}
    # Level 0 serves beyond 1,000 km: not the regions either, which end at 1,000 km.
    assert held[0] == {"countries", "graticule"}
    assert EXACT_BELOW_KM == 25.0


def test_the_zooms_each_level_serves_are_the_ones_the_application_uses():
    index = SimpleNamespace(pack=SimpleNamespace(drawing_levels={d["id"]: d for d in LEVELS}, tile_levels=[3, 7]))
    assert drawing_source(index, 25)[0] == "tile"
    assert drawing_source(index, 26)[1]["id"] == 2 and drawing_source(index, 150)[1]["id"] == 2
    assert drawing_source(index, 151)[1]["id"] == 1 and drawing_source(index, 1000)[1]["id"] == 1
    assert drawing_source(index, 1001)[1]["id"] == 0


def pack_index(levels):
    return SimpleNamespace(pack=SimpleNamespace(drawing_levels={d["id"]: d for d in levels}, tile_levels=[3, 7],
                                                layers=[{"id": k} for k in TOPS]))


def test_a_widened_layer_is_read_from_the_finest_level_that_holds_it():
    held = held_layers(LEVELS, TOPS)
    levels = [{**d, "layers": sorted(held[d["id"]])} for d in LEVELS]
    index = pack_index(levels)
    level0 = levels[0]
    assert holds(level0, "countries") and not holds(level0, "sea-places")
    assert finest_holding(index, "sea-places")["id"] == 2
    assert finest_holding(index, "close-only") is None   # only in the exact pack tiles
    # The layers shown at 2,500 km as at first: only level 0's tiles are read.
    assert plan_for(index, "draw", level0, ["countries", "graticule"]) == [("draw", 0, 1, None)]
    # The user has widened the places' zoom range: level 2's tiles are read for them only.
    plan = plan_for(index, "draw", level0, ["countries", "sea-places", "counties", "close-only"])
    assert plan[0] == ("draw", 0, 1, None)
    assert ("draw", 2, 5, frozenset({"sea-places", "counties"})) in plan
    assert ("tile", 3, 3, frozenset({"close-only"})) in plan and ("tile", 7, 7, frozenset({"close-only"})) in plan


def test_an_older_pack_without_the_list_reads_its_levels_as_before():
    index = pack_index(LEVELS)
    assert holds(LEVELS[0], "sea-places")
    assert plan_for(index, "draw", LEVELS[0], list(TOPS)) == [("draw", 0, 1, None)]
    assert plan_for(index, "tile", None, list(TOPS)) == [("tile", 3, 3, None), ("tile", 7, 7, None)]
