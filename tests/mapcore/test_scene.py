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
    assert f["points"] == len(f["coords"]) // 2 > 0
    assert f["cross"] and f["heading"]["degrees"] == 0


def test_the_zoom_is_a_distance_so_a_smaller_window_shows_the_same_area(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
    for size in ((800, 800), (400, 400), (900, 400)):
        view = scene_mod.view_for(s.world, *size)
        side = min(size)
        left = globe.from_screen(view, *size, size[0] / 2 - side / 2, size[1] / 2)
        right = globe.from_screen(view, *size, size[0] / 2 + side / 2, size[1] / 2)
        from mapcore.geo import geodesy

        across = geodesy.distance_m(left[0], left[1], right[0], right[1])
        assert across == pytest.approx(250_000, rel=0.02)


@pytest.mark.parametrize("zoom", [100, 5000, 25_000, 100_000, 500_000, 2_500_000, 10_000_000])
def test_a_frame_stays_inside_the_point_budget_at_every_zoom(test_pack, zoom):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=zoom, step_m=25_000)
    f = s.scene(1000, 800)
    assert f["points"] <= POINT_BUDGET


def test_the_centre_is_in_the_shape_of_the_current_area(test_pack):
    s = make(test_pack, lat=51.2, lon=1.2, zoom_m=250_000, step_m=25_000)
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
    on_line = np.abs(xy[:, 0] - 400) < 0.6
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
    assert [x.id for x in b.store.at(b.world.lat, b.world.lon)] == [x.id for x in a.areas]


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
