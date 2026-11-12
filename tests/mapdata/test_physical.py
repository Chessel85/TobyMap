"""P3-T1f: mountain ranges, physical regions and peaks (DAT-5, DP169)."""
import json

import numpy as np
import shapely

from mapdata.pipeline.build import STAGES
from mapdata.pipeline.settings import load_pack
from mapdata.stages import osm_places, physical


class FakeLand:
    """The land index's one method the stage uses, over a few land tiles."""

    def __init__(self, tiles):
        self.tiles = np.array(tiles, dtype=object)

    def within(self, mask):
        return self.tiles[shapely.intersects(mask, self.tiles)]


def test_a_range_is_cut_to_the_land_so_at_sea_you_are_in_no_range():
    land = FakeLand([shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1)])   # two land tiles; the sea is north of 1
    range_ = shapely.box(0.5, 0.5, 1.5, 1.5)
    (cut,) = physical.cut_to_land([range_], land, None, 0)
    assert cut.area == shapely.box(0.5, 0.5, 1.5, 1.0).area
    assert not cut.covers(shapely.Point(1.0, 1.2))
    (none,) = physical.cut_to_land([shapely.box(5, 5, 6, 6)], land, None, 0)
    assert none is None   # a range with no land is left out


def test_a_trial_box_cuts_the_ranges_too():
    land = FakeLand([shapely.box(0, 0, 4, 4)])
    (cut,) = physical.cut_to_land([shapely.box(1, 1, 3, 3)], land, [0, 0, 2, 4], 0)
    assert cut.bounds == (1.0, 1.0, 2.0, 3.0)


def test_the_wikidata_link_comes_from_gmbas_address():
    assert physical.wikidata_of("https://www.wikidata.org/wiki/Q1286") == "Q1286"
    assert physical.wikidata_of(None) == "" and physical.wikidata_of("none") == ""


def test_natural_earth_regions_keep_the_classes_named_with_their_type(tmp_path):
    path = tmp_path / "regions.geojson"
    feats = [{"type": "Feature", "properties": {"FEATURECLA": c, "NAME": n, "NAME_EN": n, "NE_ID": i,
                                                 "WIKIDATAID": f"Q{i}"},
              "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}
             for i, (c, n) in enumerate([("Desert", "Sahara"), ("Range/mtn", "Alps"), ("Island", "Corsica"),
                                         ("Pen/cape", "Iberian Peninsula")], 1)]
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    recs, geoms = physical.natural_earth_regions(path, None, {"Desert": "desert", "Pen/cape": "peninsula"})
    assert [(r["name"], r["type"], r["wikidata"]) for r in recs] == [("Sahara", "desert", "Q1"),
                                                                     ("Iberian Peninsula", "peninsula", "Q4")]
    assert len(geoms) == 2


def test_the_world_pack_keeps_gmbas_hierarchy_and_peaks_of_1000_metres():
    pack = load_pack("world")
    stage = next(s for s in pack.stages if s["stage"] == "physical")
    assert stage["ranges"]["min_level"] == 3 and stage["ranges"]["layer"] == "mountain-ranges"
    assert {"gmba-mountains", "naturalearth-physical-regions", "land-polygons"} <= set(stage["sources"])
    for layer in ("mountain-ranges", "physical-regions"):
        assert pack.layers[layer].made_by == "physical" and dict(pack.layers[layer].shown)["fill"] == "none"
        assert pack.layers["countries"].rank < pack.layers[layer].rank < pack.layers["regions"].rank
    peaks = next(s for s in pack.stages if s["stage"] == "osm-places" and s["layer"] == "peaks")
    assert all("[ele>=1000]" in q["query"] and q["elevation"] for q in peaks["queries"])   # DP169
    assert STAGES["physical"].module == "mapdata.stages.physical"


def test_a_peaks_height_is_read_from_its_ele_tag():
    assert osm_places.elevation_m("4808") == 4808.0
    assert osm_places.elevation_m("4808.73") == 4808.7
    assert osm_places.elevation_m("4808 m") == 4808.0
    assert osm_places.elevation_m("4,808") is None   # 4.8 or 4,808: not known
    assert osm_places.elevation_m("about 4000") is None
    assert osm_places.elevation_m("") is None
