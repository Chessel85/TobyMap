"""The faster methods of 2 November (spike S2, P0-T5): each must give the same result as the method it replaces."""
import math
import zipfile
from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import pytest
import shapely
import yaml

from mapcore.packs import tiles as grid
from mapdata.stages import clip, drawing, land, pack_write, s2_compare, s2_stage
from mapdata.stages.geodesy import area_km2, areas_km2


def wiggly(cx, cy, r, n=3000, holes=True):
    """A shape with many points, a hole and islands, like a detailed coast."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rad = r * (1 + 0.15 * np.sin(17 * t) + 0.05 * np.sin(131 * t))
    outer = np.stack([cx + rad * np.cos(t), cy + rad * np.sin(t)], axis=1)
    hole = [] if not holes else [shapely.Point(cx + r * 0.3, cy).buffer(r * 0.1).exterior.coords]
    main = shapely.Polygon(outer, hole)
    islands = [shapely.Point(cx + r * 1.4 + k * 0.05, cy + r * 0.2).buffer(0.015, 6) for k in range(5)]
    return shapely.MultiPolygon([main, *islands])


# 1. Cutting into pack tiles --------------------------------------------------

def _old_cut(geom, level, x, y, out, index):
    """The cut as it was on 1 November, with the general intersection."""
    box = shapely.box(*grid.tile_box(level, x, y))
    if shapely.contains_properly(geom, box):
        out[(level, x, y)].append((index, pack_write.COVERED, None))
        return
    piece = pack_write._areas(shapely.intersection(geom, box))
    if piece is None:
        return
    if shapely.equals(piece, box):
        out[(level, x, y)].append((index, pack_write.COVERED, None))
        return
    if shapely.get_num_coordinates(piece) > pack_write.MAX_POINTS and level < pack_write.MAX_LEVEL:
        for dx in (0, 1):
            for dy in (0, 1):
                _old_cut(piece, level + 1, 2 * x + dx, 2 * y + dy, out, index)
        return
    out[(level, x, y)].append((index, pack_write.SHAPE, piece))


def _cut_all(cut, geom):
    tiles = defaultdict(list)
    w, s, e, n = geom.bounds
    x0, y0 = grid.tile_of(w, s, pack_write.START_LEVEL)
    x1, y1 = grid.tile_of(e, n, pack_write.START_LEVEL)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            cut(geom, pack_write.START_LEVEL, x, y, tiles, 0)
    return tiles


@pytest.mark.parametrize("geom", [wiggly(-3.0, 54.0, 4.0, 20000), wiggly(10.0, 45.0, 0.5, 5000, holes=False)])
def test_rectangle_cut_gives_the_same_pack_tiles_as_the_general_cut(geom):
    old, new = _cut_all(_old_cut, geom), _cut_all(pack_write._cut, geom)
    assert set(old) == set(new)
    for key in old:
        (_i, k1, g1), = old[key]
        (_j, k2, g2), = new[key]
        assert k1 == k2
        if g1 is not None:
            assert g2.is_valid
            assert shapely.symmetric_difference(g1, g2).area < 1e-12


def test_rectangle_cut_falls_back_to_the_general_cut_when_its_result_is_invalid(monkeypatch):
    bowtie = shapely.Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    monkeypatch.setattr(pack_write.shapely, "clip_by_rect", lambda g, *b: bowtie)
    square = shapely.box(0, 0, 2, 2)
    got = pack_write.cut_to_rect(square, (0, 0, 1, 1))
    assert got.is_valid and shapely.equals(got, shapely.box(0, 0, 1, 1))


# 3. Joining the land tiles -----------------------------------------------------

def test_cut_to_the_land_joins_tiles_as_a_full_union_would():
    land_shape = wiggly(0.0, 50.0, 2.0, 4000)
    # Land tiles a degree square, overlapping by a thin band, as the OSM ones do.
    tiles = []
    for x in np.arange(-3, 3, 1.0):
        for y in np.arange(47, 53, 1.0):
            t = shapely.intersection(land_shape, shapely.box(x - 0.0005, y - 0.0005, x + 1.0005, y + 1.0005))
            tiles.extend(p for p in shapely.get_parts(t) if p.geom_type == "Polygon")
    tiles = np.array(tiles, dtype=object)
    area = shapely.Point(0.5, 50.0).buffer(2.2)
    got = clip.clip_to(area, tiles)
    full = shapely.intersection(shapely.union_all(tiles), area)
    assert got.is_valid
    assert shapely.symmetric_difference(got, full).area < 1e-12
    assert len(shapely.get_parts(got)) == len(shapely.get_parts(clip.polygonal(full)))


# 4. Measuring many parts at once -------------------------------------------------

def test_areas_in_one_go_match_areas_one_at_a_time():
    shapes = [shapely.box(0, 0, 1, 1), shapely.box(179, -17, 180, -16), shapely.Polygon(),
              wiggly(15.0, 69.0, 1.0, 2000), shapely.box(-180, -90, 180, -86), shapely.Point(1, 1).buffer(1e-4)]
    got = areas_km2(np.array(shapes, dtype=object))
    want = [area_km2(g) for g in shapes]
    assert got == pytest.approx(want, rel=1e-9, abs=1e-12)


def test_areas_of_no_shapes_is_empty():
    assert len(areas_km2(np.zeros(0, object))) == 0


# 5. The land index -------------------------------------------------------------

def _download(tmp_path, tiles):
    """A small land polygons download, laid out as the real one is."""
    import pyogrio.raw

    shp_dir = tmp_path / "shp" / "land-polygons-split-4326"
    shp_dir.mkdir(parents=True)
    pyogrio.raw.write(str(shp_dir / "land_polygons.shp"), geometry=shapely.to_wkb(tiles), field_data=[],
                      fields=[], geometry_type="Polygon", crs="EPSG:4326", driver="ESRI Shapefile")
    downloads = tmp_path / "downloads"
    zip_path = land.source_path(downloads)
    zip_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "w") as z:
        for f in shp_dir.iterdir():
            z.write(f, f"land-polygons-split-4326/{f.name}")
    return downloads


def test_land_index_reads_the_same_land_tiles_as_the_download(tmp_path):
    import pyogrio.raw

    rng = np.random.default_rng(5)
    tiles = np.array([shapely.Point(x, y).buffer(0.3, 4) for x, y in rng.uniform(-20, 20, (400, 2))], dtype=object)
    downloads = _download(tmp_path, tiles)
    working = tmp_path / "tobymap" / "working" / "s2-test"
    boxes = [[-5.0, -5.0, 0.0, 0.0], [2.0, 2.0, 2.5, 9.0], [-19.0, 10.0, -12.0, 19.5]]
    got = land.load_boxes(downloads, working, "test", boxes, say=lambda *_: None)
    mask = shapely.union_all([shapely.box(*b) for b in boxes])
    _m, _f, wkb, _x = pyogrio.raw.read(land.vsi_path(land.source_path(downloads)), mask=mask, return_fids=True,
                                       read_geometry=True)
    want = shapely.from_wkb(wkb)
    assert len(got) == len(want) > 0
    assert all(shapely.equals_exact(a, b, 0) for a, b in zip(got, want))
    # The index is made once, beside the build's working folder, and used again.
    assert len(list((tmp_path / "tobymap" / "working").glob("land-index-*"))) == 1
    one = land.load(downloads, working, {"west": [-19.0, 10.0, -12.0, 19.5]}, say=lambda *_: None)
    _m, _f, wkb, _x = pyogrio.raw.read(land.vsi_path(land.source_path(downloads)), bbox=(-19.0, 10.0, -12.0, 19.5),
                                       return_fids=True, read_geometry=True)
    assert [shapely.to_wkb(g) for g in one] == [shapely.to_wkb(g) for g in shapely.from_wkb(wkb)]


# 2. Drawing whole outlines -------------------------------------------------------

def _elements(path):
    return [(int(path.elementAt(i).type.value), path.elementAt(i).x, path.elementAt(i).y)
            for i in range(path.elementCount())]


def test_whole_outline_path_matches_one_built_point_by_point():
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QPainterPath, QPolygonF

    g = shapely.MultiPolygon([shapely.Polygon([(0, 0), (4, 0), (4, 4), (0, 4)], [[(1, 1), (2, 1), (2, 2), (1, 2)]]),
                              shapely.box(6, 6, 7, 8)])
    expected = QPainterPath()
    expected.setFillRule(Qt.FillRule.OddEvenFill)
    for poly in g.geoms:
        for ring in [poly.exterior, *poly.interiors]:
            expected.addPolygon(QPolygonF([QPointF(x, y) for x, y in ring.coords]))
            expected.closeSubpath()
    xy, move = drawing.polygon_arrays(g)
    got = drawing.qpath(xy, move)
    assert _elements(got) == _elements(expected)
    assert got.fillRule() == Qt.FillRule.OddEvenFill


def test_large_outlines_load_whole():
    import gc

    for _ in range(3):
        xy = np.random.default_rng(1).uniform(0, 900, (300_000, 2))
        move = np.zeros(len(xy), bool)
        move[::1000] = True
        path = drawing.qpath(xy, move)
        gc.collect()
        assert path.elementCount() == len(xy)
        assert (path.elementAt(123_456).x, path.elementAt(123_456).y) == tuple(xy[123_456])


def test_simplifying_each_part_keeps_every_part_and_each_valid():
    g = wiggly(0.0, 0.0, 1.0, 4000)
    got = drawing.simplify_parts(g, 0.01)
    assert len(shapely.get_parts(got)) == len(shapely.get_parts(g))
    assert all(p.is_valid for p in shapely.get_parts(got))
    assert shapely.get_num_coordinates(got) < shapely.get_num_coordinates(g) / 4
    assert abs(got.area - g.area) < 0.02 * g.area
    assert drawing.simplify_parts(shapely.Polygon(), 0.01).is_empty


def test_outline_lifts_the_pen_at_artificial_edges():
    # Two rings: a square whose edge from point 1 to point 2 is a seam, and a triangle.
    coords = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [5, 5], [6, 5], [5, 6]], float)
    rings = np.array([0, 4, 7])
    seam = np.array([0, 1, 0, 0, 0, 0, 0], bool)
    xy, move = drawing.outline_arrays(coords, rings, seam)
    assert xy.tolist() == [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0], [5, 5], [6, 5], [5, 6], [5, 5]]
    # The point after the seam edge is a move, so the seam is not drawn.
    assert move.tolist() == [True, False, True, False, False, True, False, False, False]


def test_globe_seam_found_for_every_ring_at_once():
    from mapcore.render import globe

    ring_a = SimpleNamespace(lon=np.array([179.0, 180.0, 180.0, 179.0]), lat=np.array([-17.0, -17.0, -16.0, -16.0]))
    ring_b = SimpleNamespace(lon=np.array([0.0, 10.0, 10.0, 0.0]), lat=np.array([-89.995, -89.995, -80.0, -80.0]))
    ring_c = SimpleNamespace(lon=np.array([-180.0, -179.0, -179.0, -180.0]), lat=np.array([-17.0, -17.0, -16.0, -16.0]))
    world = SimpleNamespace(countries=[SimpleNamespace(id="a", colour=1, polygons=[[ring_a], [ring_c]]),
                                       SimpleNamespace(id="b", colour=2, polygons=[[ring_b]])])
    g = globe.GlobeGeometry.from_world(world)
    # Fiji's east edge along the line (point 1 to 2), its west one closing the ring (3 to 0),
    # and the polar edge (0 to 1 of ring b).
    assert g.seam.tolist() == [False, True, False, False,
                               False, False, False, True,
                               True, False, False, False]


# 6. Stage 1 by the shared program -----------------------------------------------

def test_stage_1_again_uses_stage_1s_countries_and_reading_boxes():
    from mapdata.paths import CONFIG_DIR

    old = yaml.safe_load((CONFIG_DIR / "s2_stage1.yaml").read_text(encoding="utf-8"))
    new = s2_stage.load_config(1)
    assert new["name"] != old["name"]  # its own folders, so the 1 November results are kept
    assert [c["id"] for c in new["countries"]] == [c["id"] for c in old["countries"]]
    assert [c["name"] for c in new["countries"]] == [c["name"] for c in old["countries"]]
    assert {c["id"] for c in new["countries"] if c.get("divisions")} == \
        {c["id"] for c in old["countries"] if c.get("divisions")}
    assert sorted(map(tuple, new["boxes"].values())) == sorted(map(tuple, old["regions"].values()))
    france = next(c for c in new["countries"] if c["id"] == "osm:r2202162")
    assert sorted(map(tuple, france["land_within"])) == sorted(map(tuple, old["regions"].values()))
    assert new["units"] is True


def test_cut_cache_path_depends_on_the_shape():
    a, b = shapely.box(0, 0, 1, 1), shapely.box(0, 0, 1, 2)
    from pathlib import Path
    w = Path("w")
    assert s2_stage.cut_cache_path(w, "osm:r1", a) == s2_stage.cut_cache_path(w, "osm:r1", shapely.box(0, 0, 1, 1))
    assert s2_stage.cut_cache_path(w, "osm:r1", a) != s2_stage.cut_cache_path(w, "osm:r1", b)
    assert s2_stage.cut_cache_path(w, "osm:r1", a).name.startswith("osm_r1-")


# The comparison ---------------------------------------------------------------

def test_comparison_accepts_counties_added_by_dp101_and_nothing_else():
    old = [{"id": "c1", "layer": "counties", "name": "Kent"}, {"id": "r1", "layer": "regions", "name": "England"}]
    added = {"id": "c9", "layer": "counties", "name": "Camden"}
    assert s2_compare.compare_found(old, list(old), {"c1", "r1"}) == ("same", [])
    assert s2_compare.compare_found(old[1:], [added, old[1]], {"c1", "r1"}) == ("added", ["Camden"])
    # A county that was in the old pack but is now found elsewhere is a difference.
    assert s2_compare.compare_found(old[1:], [old[0], old[1]], {"c1", "r1"})[0] == "different"
    assert s2_compare.compare_found(old, old[1:], {"c1", "r1"})[0] == "different"


def test_comparison_matches_slivers_by_place_and_area():
    old = [{"centre": [1.0, 50.0], "area_km2": 0.010}, {"centre": [2.0, 51.0], "area_km2": 0.5}]
    new = [{"centre": [2.00001, 51.0], "area_km2": 0.501}, {"centre": [1.0, 50.0], "area_km2": 0.0100001},
           {"centre": [3.0, 52.0], "area_km2": 0.2}]
    matched, old_only, new_only = s2_compare.match_slivers(old, new)
    assert matched == 2 and old_only == [] and new_only == [new[2]]


def test_comparison_of_islands_reports_each_count():
    old = {"parts": 10, "named_parts": 4, "unnamed_parts": 5, "at_least_1_hectare": 3,
           "unnamed_at_least_1_hectare": 1, "at_least_1_km2": 2, "at_least_20_km2": 1}
    lines, same = s2_compare.compare_islands(old, dict(old))
    assert same and all(line.startswith("Same") for line in lines)
    lines, same = s2_compare.compare_islands(old, {**old, "unnamed_parts": 6})
    assert not same and sum(line.startswith("DIFFERENT") for line in lines) == 1


def test_grid_points_cover_every_box():
    points = s2_compare.grid_points()
    assert {p[0] for p in points} == set(s2_compare.GRID_BOXES) | set(s2_compare.SMALL_BOXES)
    assert all(not math.isnan(p[1]) for p in points)
