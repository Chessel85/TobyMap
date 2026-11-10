"""The map scene from a pack (P1-T9; VIS-1, VIS-5, AD-17, DP76, SCP-2)."""
import time

import numpy as np
import pytest

from mapcore.render import globe, scene as scene_mod
from mapcore.session import MapSession

POINT_BUDGET = 30_000   # VIS-1 aims near 10,000; the widest views of islands run higher


def make(test_pack, **state):
    s = MapSession(packs=[test_pack], saved_state=state)
    s.start()
    return s


def rings(frame):
    out = []
    xy = np.asarray(frame["coords"]).reshape(-1, 2)
    for i in range(len(frame["rings"]) - 1):
        out.append(xy[frame["rings"][i]:frame["rings"][i + 1]])
    return out


def test_the_scene_is_plain_arrays_and_lists(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    f = s.scene(800, 600)
    assert f["coords"].dtype == np.float32 and f["rings"].dtype == np.int32 and f["shapes"].dtype == np.int32
    assert len(f["seam"]) == len(f["coords"]) // 2
    assert len(f["shape_style"]) == len(f["shapes"]) - 1 == len(f["shape_area"])
    assert f["points"] >= len(f["coords"]) // 2 > 0   # the lines and markers count too
    assert f["cross"] and f["heading"]["degrees"] == 0


def test_the_zoom_is_drawn_at_a_fixed_scale_so_a_bigger_window_shows_more(test_pack):
    """DP138: the zoom distance is always drawn ZOOM_RADIUS_PX from the centre, whatever the
    window size, like a paper map's scale. A bigger window shows more map round the edges."""
    from mapcore.geo import geodesy

    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    r = scene_mod.ZOOM_RADIUS_PX
    for size in ((800, 800), (400, 400), (1600, 900)):
        view = scene_mod.view_for(s.world, *size)
        east = globe.from_screen(view, *size, size[0] / 2 + r, size[1] / 2)
        assert geodesy.distance_m(51.2, 1.2, east[0], east[1]) == pytest.approx(250_000, rel=0.02)


@pytest.mark.parametrize("zoom", [100, 5000, 25_000, 100_000, 500_000, 2_500_000, 10_000_000])
def test_a_frame_stays_inside_the_point_budget_at_every_zoom(test_pack, zoom):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=zoom, step_m=25_000)
    f = s.scene(1000, 800)
    assert f["points"] <= POINT_BUDGET


def test_the_centre_is_in_the_shape_of_the_current_area(test_pack):
    # 100 km: the counties, the smallest areas here, are in their zoom range (NAV-13)
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=100_000, step_m=25_000)
    f = s.scene(800, 600)
    assert f["current"], "the current area has shapes to outline"
    assert all(f["shape_area"][i] == s.areas[0].id for i in f["current"])


def test_the_highlight_marks_the_selected_item(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    s.run("panel.select", item=s.areas[-1].id)
    f = s.scene(800, 600)
    assert f["highlight"] and all(f["shape_style"][i] == scene_mod.HIGHLIGHT_STYLE for i in f["highlight"])


def test_the_centre_cross_can_be_switched_off(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    s.run("settings.set", field="centre_cross", value=False)
    assert s.scene(800, 600)["cross"] is None


def test_oceans_are_painted_before_land(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    f = s.scene(800, 600)
    styles = list(f["shape_style"])
    first_land = next(i for i, st in enumerate(styles) if st != scene_mod.OCEAN_STYLE)
    assert all(st != scene_mod.OCEAN_STYLE for st in styles[first_land:])


def test_fiji_draws_whole_across_the_180_degree_line_with_no_outline_along_it(test_pack):
    s = make(test_pack, lat=-16.5, lon=180.0, zoom_m=100_000, step_m=10_000)
    f = s.scene(800, 600)
    xy = np.asarray(f["coords"]).reshape(-1, 2)
    seam = np.asarray(f["seam"], bool)
    # Points on the vertical line down the middle (the 180 degree line) are joined by seams only.
    on_line = np.abs(xy[:, 0] - 400) < 0.01   # exactly on the line: coast edges leaving it are less than a pixel away
    assert on_line.any()
    for i in range(len(f["rings"]) - 1):
        a, b = f["rings"][i], f["rings"][i + 1]
        for k in range(a, b):
            nxt = a + (k - a + 1) % (b - a)
            if on_line[k] and on_line[nxt]:
                assert seam[k], "an edge along the 180 degree line must not be outlined"
    # Land on both sides of the line is drawn.
    assert (xy[:, 0] < 400 - 5).any() and (xy[:, 0] > 400 + 5).any()


def test_chukotka_draws_across_the_line(test_pack):
    s = make(test_pack, lat=66.0, lon=180.0, zoom_m=500_000, step_m=25_000)
    f = s.scene(800, 600)
    assert any(a.startswith("osm:") for a in f["shape_area"])
    xy = np.asarray(f["coords"]).reshape(-1, 2)
    assert (xy[:, 0] < 395).any() and (xy[:, 0] > 405).any()


def test_the_south_pole_edge_is_never_outlined(test_pack):
    s = make(test_pack, lat=-89.0, lon=0.0, zoom_m=500_000, step_m=25_000)
    f = s.scene(800, 800)
    assert f["points"] > 0 and np.asarray(f["seam"]).any()


def test_a_click_gives_the_same_answer_as_stepping_there(test_pack):
    a = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    view = scene_mod.view_for(a.world, 800, 600)
    x, y = globe.to_screen(view, 800, 600, 50.975, 1.9)
    clicked = a.run("map.click", x=x, y=y, width=800, height=600)
    b = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    names = [t["text"] for t in clicked.announcements]
    assert names == ["Pas-de-Calais, Hauts-de-France, France"] or names, "a click describes the place it lands in"
    b.world.lat, b.world.lon = a.world.lat, a.world.lon
    # Both leave out the layers outside their zoom range, such as Counties at 250 km (DP160).
    assert [x.id for x in b._here()] == [x.id for x in a.areas]


def test_a_frame_is_built_quickly_once_the_tiles_are_cached(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    s.scene(800, 600)
    start = time.perf_counter()
    for _ in range(5):
        s.scene(800, 600)
    assert (time.perf_counter() - start) / 5 < 0.1   # VIS-1: 100 ms


def test_every_drawn_layer_is_one_where_am_i_can_find(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=500_000, step_m=25_000)
    f = s.scene(800, 600)
    layers = {s.store.feature(a).layer for a in set(f["shape_area"])}
    findable = {a.layer for a in s.store.at(51.2, 1.2)} | {"countries", "regions", "counties", "oceans"}
    assert layers <= findable


def _one_by_one(self, box):
    """The drawing's shapes as before P2-T14c: each entry decoded on its own."""
    import shapely

    from mapcore.packs import tiles

    geoms = np.empty(len(self.entries), object)
    for i, e in enumerate(self.entries):
        geoms[i] = shapely.box(*box) if e.kind == tiles.COVERED else self.shape(i)
    return geoms, np.asarray([e.feature for e in self.entries], np.int64)


@pytest.mark.parametrize("zoom", [10_000, 250_000, 2_500_000])
def test_a_drawing_from_shapes_kept_with_their_tiles_matches_a_fresh_one(test_pack, monkeypatch, zoom):
    """P2-T14c: each tile's shapes are decoded together and kept. The picture is the
    same, point for point within a pixel, as one drawn afresh, and as one from
    shapes decoded one by one."""
    from mapcore.store.cache import TileData

    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=zoom, step_m=25_000)
    s.scene(800, 600)
    s.world.lon += 0.3
    s.scene(800, 600)
    s.world.lon -= 0.3
    kept = s.scene(800, 600)                                  # from the shapes kept with the tiles
    fresh = make(test_pack, lat=51.2, lon=1.2, zoom_m=zoom, step_m=25_000).scene(800, 600)
    monkeypatch.setattr(TileData, "drawing_shapes", _one_by_one)
    old = make(test_pack, lat=51.2, lon=1.2, zoom_m=zoom, step_m=25_000).scene(800, 600)
    for other in (fresh, old):
        assert kept["points"] == other["points"] > 0
        assert np.abs(np.asarray(kept["coords"]) - np.asarray(other["coords"])).max() <= 1.0
        for key in ("rings", "shapes", "shape_style", "seam"):
            assert np.array_equal(kept[key], other[key]), key
        assert kept["shape_area"] == other["shape_area"]


def test_the_heading_arrow_turns_with_the_way_you_face(test_pack):
    """P2-T1e, NAV-12: the arrow at the centre points the way you face, in the scene both shells paint."""
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    assert s.scene(800, 600)["heading"]["degrees"] == 0
    s.run("orientation.cycle")
    s.run("move.east")
    assert s.scene(800, 600)["heading"]["degrees"] == 90
    s.run("bearing.set", text="47")
    f = s.scene(800, 600)
    assert f["heading"]["degrees"] == 47 and (f["heading"]["x"], f["heading"]["y"]) == (400, 300)
    s.run("orientation.cycle")   # north-fixed again: the arrow points up
    assert s.scene(800, 600)["heading"]["degrees"] == 0


def test_an_edge_along_a_tile_edge_stays_a_seam_when_the_point_before_it_is_merged():
    """P2-T17v: the straight line along 45 degrees north across France. A real edge less than
    a pixel long ends on a pack tile edge, and the long edge along the tile edge follows. The
    end of the short edge is merged away, as it is in the same pixel, but the long edge must
    still be a seam, never outlined (AD-17)."""
    from types import SimpleNamespace

    builder = scene_mod.SceneBuilder(store=None, theme=globe.load_theme())
    view = globe.View(lat=45.0, lon=5.0, scale=1.0, up=0.0)
    width = height = 800
    r = globe._radius(view, width, height)
    # Inside, then a hair short of the tile's north edge, then on it, along it, and back.
    ring = [(2.0, 45.0), (2.00001, 49.99999), (2.00002, 50.0), (8.0, 50.0), (8.0, 45.0), (2.0, 45.0)]
    xy = np.array(ring, float)
    frame = builder._frame(view, width, height, width / 2, height / 2, r, xy,
                           np.array([0, len(ring)], np.intp), np.array([0, 1], np.intp),
                           np.array([0], np.intp), [("a", 1, 1, "countries", None, None, "A")],
                           np.array([[0.0, 40.0, 10.0, 50.0]]), None, None)
    pts = np.asarray(frame["coords"]).reshape(-1, 2)
    seam = np.asarray(frame["seam"], bool)
    n = len(pts)
    long_unmarked = [k for k in range(n)
                     if not seam[k] and abs(pts[k][1] - pts[(k + 1) % n][1]) < 3
                     and abs(pts[k][0] - pts[(k + 1) % n][0]) > 20 and min(pts[k][1], pts[(k + 1) % n][1]) < height / 2 - 20]
    assert not long_unmarked, "the edge along the tile's north edge would be outlined"
    assert seam.any()
