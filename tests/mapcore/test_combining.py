"""Several packs open together (P4-T3a; PLT-4, PCK-2, LOC-6, AD-14, architecture 6.8).

The test pack (a world pack) and the regional test pack, test-region, are opened together. Inside a covered pack
tile the regional pack answers for its layers, and the world pack's features of those layers are left out there;
elsewhere, and for every other layer, the world pack answers, and nothing is said about missing detail.
"""
from pathlib import Path

import numpy as np
import pytest
import yaml

from mapcore.packs import tiles
from mapcore.packs.pack import Pack
from mapcore.store import Store
from mapcore.store.packs_combined import Coverage, coverage_of, detail_order

WINCHESTER = (51.0590, -1.3074)       # the middle of the Winchester sample's covered pack tile, 14/8132/12839
LYMINGTON = (50.7458, -1.5381)        # in the Lymington sample's covered pack tiles
OUTSIDE = (51.2000, -1.4000)          # Hampshire, but in no covered pack tile
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def both(test_pack, test_region_pack):
    """The world pack first, as a folder listing might give them: the store puts the regional pack first."""
    store = Store([Pack(test_pack, check_app=False), Pack(test_region_pack, check_app=False)])
    yield store
    store.close()


@pytest.fixture(scope="module")
def world_only(test_pack):
    store = Store([Pack(test_pack, check_app=False)])
    yield store
    store.close()


def _regional(store) -> int:
    return next(p for p in range(len(store.packs)) if store.coverage(p) is not None)


# The coverage -------------------------------------------------------------------------------------------------

def test_a_coverage_covers_its_tiles_at_any_level():
    cov = Coverage({"kind": "region", "tile_level": 12, "layers": ["counties"], "draw_below_km": 250,
                    "tiles": ["8/127/203", "12/2034/3271"]})
    west, south, east, north = tiles.tile_box(8, 127, 203)
    assert cov.covers((south + north) / 2, (west + east) / 2)
    west, south, east, north = tiles.tile_box(12, 2034, 3271)
    assert cov.covers((south + north) / 2, (west + east) / 2)
    west, south, east, north = tiles.tile_box(12, 2035, 3271)
    assert not cov.covers((south + north) / 2, (west + east) / 2)
    assert not cov.covers(0.0, 0.0)


def test_the_part_of_a_coverage_in_a_box():
    cov = Coverage({"kind": "region", "tile_level": 4, "layers": ["counties"], "tiles": ["4/8/8"]})
    inside = tiles.tile_box(4, 8, 8)
    assert cov.part_in(inside) is True
    assert cov.part_in(tiles.tile_box(4, 0, 0)) is None
    wider = tiles.tile_box(3, 4, 4)   # the level 3 pack tile holding 4/8/8 and three others
    part = cov.part_in(wider)
    assert part is not True and part is not None
    assert part.area == pytest.approx((inside[2] - inside[0]) * (inside[3] - inside[1]))


def test_a_world_pack_has_no_coverage_and_regional_packs_come_first(test_pack, test_region_pack):
    world, region = Pack(test_pack, check_app=False), Pack(test_region_pack, check_app=False)
    try:
        assert coverage_of(world) is None
        assert coverage_of(region).tile_level == 14
        assert detail_order([world, region]) == [1, 0]
        assert detail_order([region, world]) == [0, 1]
    finally:
        world.close()
        region.close()


# Where am I -----------------------------------------------------------------------------------------------------

def test_a_point_in_the_regional_packs_tiles_is_answered_by_it(both):
    region = _regional(both)
    found = both.at(*WINCHESTER)
    ids = [a.id for a in found]
    assert "osm:r127238" in ids                 # the City of Winchester district, only in the regional pack
    assert ids.count("osm:r172799") == 1        # Hampshire, once
    assert ids.count("osm:r62149") == 1         # the United Kingdom, once
    for a in found:
        assert a.pack == region, (a.id, a.layer)


def test_a_point_outside_is_answered_by_the_world_pack(both, world_only):
    found = both.at(*OUTSIDE)
    assert [a.id for a in found] == [a.id for a in world_only.at(*OUTSIDE)]
    assert {a.pack for a in found} == {both._world}


def test_the_world_pack_keeps_its_own_layers_inside_the_coverage(both):
    world = both._world
    assert both._hidden(world, "counties", *WINCHESTER)
    assert not both._hidden(world, "towns", *WINCHESTER)         # the regional pack has no towns
    assert not both._hidden(world, "counties", *OUTSIDE)
    assert not both._hidden(_regional(both), "counties", *WINCHESTER)


def test_nothing_is_said_about_missing_detail_outside(test_pack, test_region_pack):
    """Where am I at a point no regional pack covers is the same as with the world pack alone (PLT-4)."""
    from mapcore.session import MapSession

    said = []
    for packs in ([test_pack], [test_pack, test_region_pack]):
        store = Store([Pack(p, check_app=False) for p in packs])
        s = MapSession(store=store, saved_state={"lat": OUTSIDE[0], "lon": OUTSIDE[1], "zoom_m": 5000,
                                                  "step_m": 100})
        try:
            s.start()
            said.append(s._place_text())
        finally:
            store.close()
    assert said[0] == said[1]
    assert "Hampshire" in said[1]


def test_where_am_i_inside_names_the_parish_and_district(test_pack, test_region_pack):
    from mapcore.session import MapSession

    store = Store([Pack(test_pack, check_app=False), Pack(test_region_pack, check_app=False)])
    s = MapSession(store=store, saved_state={"lat": WINCHESTER[0], "lon": WINCHESTER[1], "zoom_m": 1000,
                                              "step_m": 10})
    try:
        s.start()
        text = s._place_text()
        assert "Winchester" in text and text.count("Hampshire") == 1, text
    finally:
        store.close()


# Nearby and places --------------------------------------------------------------------------------------------

def test_nearby_gives_each_feature_once(both):
    near = both.nearby(*LYMINGTON, radius_m=5000, limit=40)
    ids = [n.area.id for n in near]
    assert len(ids) == len(set(ids)), ids
    assert "osm:r172799" in ids
    region = _regional(both)
    for n in near:
        if n.area.layer == "counties" and both.coverage(region).covers(n.lat, n.lon):
            assert n.area.pack == region


def test_places_of_a_world_only_layer_come_from_the_world_pack(both, world_only):
    got = [n.area.id for n in both.points_near(*WINCHESTER, 300_000, "towns")]
    assert got == [n.area.id for n in world_only.points_near(*WINCHESTER, 300_000, "towns")]
    assert got   # the test pack's towns


def test_a_path_crossing_the_coverage_gives_each_feature_once(both):
    lat, lon = WINCHESTER
    path = [(lat, lon - 0.05), (lat, lon + 0.05)]   # from outside the covered pack tile, across it, and out
    passed = both.along_path(path, 50.0)
    keys = [(p.area.id, p.kind) for p in passed]
    assert len(keys) == len(set(keys)), keys


# The drawing ----------------------------------------------------------------------------------------------------

def test_a_wide_view_is_drawn_by_the_world_pack_alone(both):
    box = [(-2.0, 50.5, -1.0, 51.5)]
    assert both.drawn_packs(300.0, box) == [both._world]
    assert both.drawn_packs(5.0, box) == [_regional(both), both._world]
    assert both.drawn_packs(5.0, [(10.0, 10.0, 11.0, 11.0)]) == [both._world]


def test_the_world_packs_shapes_lose_the_coverage(both):
    """A 5 kilometre view round Winchester draws both packs. Inside the covered pack tile Hampshire is drawn
    once, by the regional pack: the world pack's Hampshire has the coverage cut out. Round it, the world pack
    draws Hampshire."""
    import shapely

    from mapcore.render.scene import SceneBuilder

    builder = SceneBuilder(both)
    lat, lon = WINCHESTER
    geoms, feats, _boxes, *_ = builder._collect(lat, lon, 5.0 / 6371.0, 5.0)
    hampshire = [g for g, f in zip(geoms, feats) if f[0] == "osm:r172799"]
    cell = shapely.box(*tiles.tile_box(14, 8132, 12839))
    inside = sum(g.intersection(cell).area for g in hampshire)
    assert inside == pytest.approx(cell.area, rel=0.01)   # once, not twice
    round_it = shapely.box(lon - 0.03, lat - 0.02, lon + 0.03, lat + 0.02).difference(cell)   # in view, uncovered
    outside = sum(g.intersection(round_it).area for g in hampshire)
    assert outside == pytest.approx(round_it.area, rel=0.01)   # the world pack's Hampshire round the tile


def test_a_cut_shape_is_made_once_a_tile():
    import shapely

    from mapcore.render.scene import _cut_covered
    from mapcore.store.cache import TileData

    cov = Coverage({"kind": "region", "tile_level": 4, "layers": ["counties"], "tiles": ["4/8/8"]})
    box = tiles.tile_box(3, 4, 4)
    data = TileData([])
    shapes = np.empty(2, object)
    shapes[:] = [shapely.box(*box), shapely.box(*box)]
    found = [("a", 3, 1, "counties"), ("b", 3, 1, "towns")]
    cut, kept = _cut_covered(data, shapes, found, box, [cov])
    assert [f[0] for f in kept] == ["a", "b"]
    assert cut[0].area == pytest.approx(shapes[0].area * 3 / 4)
    assert cut[1] is shapes[1]
    again, _ = _cut_covered(data, shapes, found, box, [cov])
    assert again[0] is cut[0]
    # Where the coverage fills the tile, the shapes of its layers are left out.
    inner = tiles.tile_box(4, 8, 8)
    shapes[:] = [shapely.box(*inner), shapely.box(*inner)]
    _cut, kept = _cut_covered(TileData([]), shapes, found, inner, [cov])
    assert [f[0] for f in kept] == ["b"]


def test_an_edge_along_the_coverage_is_a_seam():
    from mapcore.render.scene import _grid_seams

    west, south, east, north = tiles.tile_box(14, 8132, 12839)
    lon = np.array([west, west, -1.3, -1.3001])
    lat = np.array([south, north, 51.0601, 51.0602])
    nxt = np.array([1, 2, 3, 3])
    is_last = np.array([False, False, False, True])
    got = _grid_seams(lon, lat, nxt, is_last, 3e-7, (14, [(west, south, east, north)]))
    assert got.tolist() == [True, False, False, False]


def test_the_visible_rule_hides_world_features_inside_the_coverage(both):
    from mapcore.layers.catalogue import LayerCatalogue
    from mapcore.layers.visible import VisibleRule

    rule = VisibleRule(both, LayerCatalogue(both.packs[::-1], dict))
    lat, lon = WINCHESTER
    seen = rule.features(lat, lon, 500.0)
    assert "osm:r172799" in seen and "osm:r127238" in seen
    drawn = rule.drawn(lat, lon, 500.0, 500.0 / 6371000.0)
    assert drawn == [_regional(both), both._world]


# The pack files ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["test-region", "hampshire-isle-of-wight", "england", "great-britain"])
def test_a_regional_pack_is_refused_by_older_applications(name):
    """An application older than P4-T3a would read a regional pack as a world pack (design 2.4)."""
    settings = yaml.safe_load((REPO / "mapdata" / "config" / "packs" / f"{name}.yaml").read_text(encoding="utf-8"))
    version = (REPO / "version.txt").read_text(encoding="utf-8").strip()
    assert settings["app_versions"]["from"] == version == "0.1.1"
