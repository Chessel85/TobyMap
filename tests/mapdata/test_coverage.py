"""A regional pack's coverage (P4-T1a, design docs/plan/p4-t1-design.md sections 2 and 5.4): the .poly reader, the
covered pack tiles, the cutting of features to them, the manifest's coverage, and the pack settings files."""
from __future__ import annotations

import pytest
import shapely
import yaml

from mapcore.packs.tiles import tile_box
from mapdata.paths import CONFIG_DIR
from mapdata.pipeline.build import fingerprint
from mapdata.pipeline.settings import load_layers, load_pack
from mapdata.stages import coverage

POLY = """two boxes and a hole
first
   0.0   0.0
   2.0   0.0
   2.0   2.0
   0.0   2.0
   0.0   0.0
END
!hole
   0.5   0.5
   1.0   0.5
   1.0   1.0
   0.5   1.0
   0.5   0.5
END
second
   3.0   0.0
   4.0   0.0
   4.0   1.0
   3.0   1.0
END
END
"""


# The .poly file ------------------------------------------------------------------------------------------------

def test_poly_with_two_sections_and_a_hole():
    name, shape = coverage.read_poly(POLY)
    assert name == "two boxes and a hole"
    assert shape.geom_type == "MultiPolygon"
    assert shape.area == 4 - 0.25 + 1
    assert not shape.contains(shapely.Point(0.75, 0.75))   # in the hole
    assert shape.contains(shapely.Point(1.5, 1.5)) and shape.contains(shapely.Point(3.5, 0.5))


def test_poly_with_no_end_is_refused():
    from mapdata.pipeline.errors import BuildStopped

    with pytest.raises(BuildStopped, match="no END"):
        coverage.read_poly("name\n1\n 0 0\n 1 0\n 1 1\n")


def test_the_test_regions_outline_is_three_boxes():
    names, shape = coverage.read_outlines([CONFIG_DIR.parent.parent / "tests/samples/outlines/test-region.poly"])
    assert names == ["test-region"]
    assert len(shapely.get_parts(shape)) == 3


# Covered pack tiles --------------------------------------------------------------------------------------------

def test_covered_pack_tiles_of_a_made_up_outline_and_land():
    # Tile level 3: pack tiles 45 by 22.5 degrees. The outline covers four of them round 0, 0.
    outline = shapely.box(-40, -20, 40, 20)
    land = [shapely.box(1, 1, 2, 2),           # in the pack tile x 4, y 4
            shapely.box(-10, -10, 0, -5)]      # in x 3, y 3, its east edge on the line between x 3 and x 4
    assert coverage.covered_tiles(land, outline, 3) == {(4, 4), (3, 3)}


def test_land_outside_the_outline_covers_nothing():
    outline = shapely.box(-40, -20, 40, 20)
    assert coverage.covered_tiles([shapely.box(100, 50, 110, 60)], outline, 3) == set()


def test_four_covered_pack_tiles_are_written_as_one():
    four = {(4, 6), (5, 6), (4, 7), (5, 7)}
    assert coverage.merge_tiles(four, 5, 2) == [(4, 2, 3)]
    assert coverage.merge_tiles(four | {(9, 9)}, 5, 2) == [(4, 2, 3), (5, 9, 9)]
    three = four - {(5, 7)}
    assert coverage.merge_tiles(three, 5, 2) == [(5, 4, 6), (5, 4, 7), (5, 5, 6)]


def test_merging_stops_at_merge_from_level():
    whole = {(x, y) for x in range(8) for y in range(8)}   # every pack tile of a level 3 tile, at level 6
    assert coverage.merge_tiles(whole, 6, 3) == [(3, 0, 0)]
    assert len(coverage.merge_tiles(whole, 6, 4)) == 4
    assert len(coverage.merge_tiles(whole, 6, 6)) == 64


def test_reading_boxes_are_level_8_pack_tiles():
    boxes = coverage.reading_boxes([(14, 8132, 12839), (14, 8133, 12839), (6, 0, 0)])
    assert boxes[0] == list(tile_box(8, 0, 0))
    assert len(boxes) == 16 + 1   # the level 6 tile's sixteen, and the two level 14 tiles' one
    assert list(tile_box(8, 8132 >> 6, 12839 >> 6)) in boxes


# Cutting to the coverage ---------------------------------------------------------------------------------------

def test_a_feature_cut_by_the_coverage_is_partial_and_one_inside_is_not():
    shape = shapely.box(0, 0, 10, 10)
    records = [{"id": "inside", "layer": "a"}, {"id": "cut", "layer": "a"}, {"id": "outside", "layer": "a"},
               {"id": "line", "layer": "l"}, {"id": "points", "layer": "p"}, {"id": "nearly", "layer": "a"}]
    geoms = [shapely.box(1, 1, 2, 2), shapely.box(5, 5, 15, 15), shapely.box(20, 20, 30, 30),
             shapely.LineString([(5, 5), (15, 5)]), shapely.MultiPoint([(1, 1), (20, 20)]),
             shapely.box(1, 1, 10.0001, 9)]   # less than 0.1 percent outside: not partial
    out_r, out_g, counts = coverage.cut_to_coverage(records, geoms, shape)
    by_id = {r["id"]: (r, g) for r, g in zip(out_r, out_g)}
    assert set(by_id) == {"inside", "cut", "line", "points", "nearly"}
    assert "partial" not in by_id["inside"][0] and "partial" not in by_id["nearly"][0]
    assert by_id["cut"][0]["partial"] and by_id["cut"][1].area == 25
    assert by_id["line"][0]["partial"] and by_id["line"][1].length == 5
    assert by_id["points"][0]["partial"] and by_id["points"][1].geom_type == "MultiPoint"
    assert counts == {"kept": 5, "partial": 3, "dropped": 1}
    assert "partial" not in records[1]   # the records given are not changed


def test_a_line_of_no_length_is_dropped_not_a_fault():
    """A way whose points are all at one place cuts to an empty line; on the coverage's edge or outside it, this
    stopped the rehearsal's osm-waterways stage (P4-T1j)."""
    shape = shapely.box(0, 0, 10, 10)
    records = [{"id": "edge", "layer": "l"}, {"id": "outside", "layer": "l"}, {"id": "kept", "layer": "l"},
               {"id": "multi", "layer": "l"}]
    geoms = [shapely.LineString([(10, 5), (10, 5)]), shapely.LineString([(20, 5), (20, 5)]),
             shapely.MultiLineString([[(5, 5), (15, 5)], [(30, 5), (30, 5)]]),
             shapely.MultiLineString([[(10, 6), (10, 6)], [(30, 5), (30, 5)]])]
    out_r, out_g, counts = coverage.cut_to_coverage(records, geoms, shape)
    assert [r["id"] for r in out_r] == ["kept"] and out_g[0].length == 5
    assert counts == {"kept": 1, "partial": 1, "dropped": 3}


# The manifest's coverage ---------------------------------------------------------------------------------------

def _regional(**over):
    cov = {"kind": "region", "region": "r", "tile_level": 12, "tiles": ["6/31/50", "12/2034/3271"],
           "layers": ["countries"], "draw_below_km": 250}
    cov.update(over)
    return cov


def test_a_right_coverage_has_no_problems():
    assert coverage.check_manifest_coverage(_regional(), ["countries", "counties"]) == []
    assert coverage.check_manifest_coverage({"kind": "world"}, []) == []


def test_wrong_coverages_are_named():
    def problems(**over):
        return " ".join(coverage.check_manifest_coverage(_regional(**over), ["countries"]))

    assert "not sorted" in problems(tiles=["12/2034/3271", "6/31/50"])
    assert "not in the grid" in problems(tiles=["12/5000/3271"])
    assert "not in the grid" in problems(tiles=["13/0/0"])   # finer than the tile level
    assert "not a pack tile" in problems(tiles=["12/a/3"])
    assert "inside" in problems(tiles=["6/31/50", "12/1984/3200"])
    assert "twice" in problems(tiles=["6/31/50", "6/31/50"])
    assert "does not hold" in problems(layers=["countries", "streets"])
    assert "draw_below_km" in problems(draw_below_km=0)


def test_a_pack_with_no_coverage_stage_keeps_its_settings_coverage():
    assert coverage.manifest_coverage({"kind": "region"}, None, ["countries"]) == {"kind": "region"}


# The test region -----------------------------------------------------------------------------------------------

SAMPLE_TILES = (["14/8118/12817", "14/8118/12818", "14/8119/12817", "14/8119/12818", "14/8120/12817",
                 "14/8120/12818"]                                          # Brockenhurst
                + ["14/8121/12810", "14/8121/12811", "14/8122/12810", "14/8122/12811"]   # Lymington
                + ["14/8132/12839"])                                       # Winchester


def test_the_test_regions_manifest_coverage(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        cov = p.manifest["coverage"]
        held = {p.feature(n)["layer"] for n in range(p.manifest["features"]["count"])}
    assert cov["kind"] == "region" and cov["region"] == "test-region" and cov["tile_level"] == 14
    assert cov["tiles"] == SAMPLE_TILES
    assert set(cov["layers"]) == held and {"countries", "counties", "oceans"} <= held
    assert cov["draw_below_km"] == 250


def test_the_test_regions_cut_features_are_partial(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        records = {p.feature(n)["id"]: p.feature(n) for n in range(p.manifest["features"]["count"])}
    assert records["osm:r62149"]["partial"] is True        # the United Kingdom, cut to three small boxes
    assert records["vliz:goas:north-atlantic-ocean"]["partial"] is True
    assert "osm:r1403916" not in records                   # France is outside the coverage


def _gap_in(test_region_pack, box):
    from mapdata.pipeline import features

    work = test_region_pack.parents[2] / "working" / "test-region"
    folder = next(f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith("coverage-"))
    records, geoms = features.load(folder)
    cover = shapely.union_all([g for r, g in zip(records, geoms) if r["layer"] in ("countries", "oceans", "seas")])
    tiles = shapely.intersection(coverage.load(folder).shape, shapely.box(*box))
    assert tiles.area > 0
    return shapely.difference(tiles, cover)


def test_every_point_of_a_covered_pack_tile_is_in_land_or_sea(test_region_pack):
    """LOC-6 in the coverage: the land areas and the seas cover every covered pack tile, with no gap. Here for the
    inland boxes, Winchester and Brockenhurst."""
    for box in ([-1.31836, 51.05347, -1.29639, 51.06445], [-1.62598, 50.81177, -1.56006, 50.83374]):
        gap = _gap_in(test_region_pack, box)
        assert gap.area < 1e-12, f"gap of {gap.area} square degrees at {shapely.point_on_surface(gap)}"


@pytest.mark.xfail(strict=True, reason="The test pack's only sea is VLIZ's North Atlantic at ocean scale, which does "
                   "not reach up the Lymington River, while lymington-coast.geojson's land is cut to the exact coast, "
                   "so about 0.7 km2 of the estuary is in neither. A real regional pack's seas come from the land "
                   "polygons (squares and join), so it has no such gap. A cooked sea for the Lymington box makes this "
                   "pass; then remove the mark.")
def test_every_point_of_the_lymington_pack_tiles_is_in_land_or_sea(test_region_pack):
    gap = _gap_in(test_region_pack, [-1.56006, 50.73486, -1.51611, 50.75684])
    assert gap.area < 1e-12, f"gap of {gap.area} square degrees at {shapely.point_on_surface(gap)}"


# The pack settings files ---------------------------------------------------------------------------------------

def _without_region_lines(name: str) -> dict:
    data = yaml.safe_load((CONFIG_DIR / "packs" / f"{name}.yaml").read_text(encoding="utf-8"))
    for key in ("name", "title", "space_needed_mb"):
        data.pop(key)
    for st in data["stages"]:
        st.pop("box", None)
        if st["stage"] == "checks":
            st.pop("places", None)   # each pack's own check places (P4-T1j, P4-T2c)
        if st["stage"] == "coverage":
            st.pop("sources", None)
    return data


def test_great_britain_and_its_rehearsal_have_the_same_stages():
    assert _without_region_lines("great-britain") == _without_region_lines("hampshire-isle-of-wight")


def test_the_regional_packs_settings_load():
    for name in ("great-britain", "hampshire-isle-of-wight", "test-region"):
        pack = load_pack(name)
        assert pack.data["coverage"]["kind"] == "region"
        assert [s["stage"] for s in pack.stages].index("coverage") >= 2
        assert {"districts", "parishes", "streets", "stops", "villages"} <= set(pack.layers)


def test_regional_layers_never_rebuild_the_world_areas():
    """Every regional layer has made_by, so adding the regional layers to the world's layer groups leaves the
    fingerprints of osm-areas, squares and join as they are (architecture 6.11b). The world's write stage does take
    a new fingerprint from P4-T1a's change to write.py; that is expected."""
    regional = load_layers(["regional"])
    assert all(layer.made_by for layer in regional.values())
    world = load_pack("world")
    prints = {k: "x" for k in world.sources}
    before = [fingerprint(world, st, "", prints) for st in world.stages[:3]]
    world.layers.update(regional)
    world.data["layer_groups"] = [*world.data["layer_groups"], "regional"]
    assert [fingerprint(world, st, "", prints) for st in world.stages[:3]] == before
