"""The orthographic globe: projection, horizon clipping and the shape list (VIS-5, AD-6, architecture 7.10)."""
import math
import time

import numpy as np
import pytest

from mapcore.render import globe
from mapcore.store.world_sample import WorldSample


@pytest.fixture(scope="module")
def world():
    return WorldSample.load()


@pytest.fixture(scope="module")
def geometry(world):
    return globe.GlobeGeometry.from_world(world)


def test_centre_projects_to_the_middle():
    view = globe.View(lat=52, lon=-1, scale=1)
    x, y, depth = globe.project_points(view, np.array([52.0]), np.array([-1.0]))
    assert x[0] == pytest.approx(0, abs=1e-12)
    assert y[0] == pytest.approx(0, abs=1e-12)
    assert depth[0] == pytest.approx(1)


def test_north_is_up_and_east_is_right():
    view = globe.View(lat=0, lon=0, scale=1)
    x, y, _ = globe.project_points(view, np.array([10.0, 0.0]), np.array([0.0, 10.0]))
    assert y[0] > 0 and x[0] == pytest.approx(0, abs=1e-12)   # north is up (positive y)
    assert x[1] > 0 and y[1] == pytest.approx(0, abs=1e-12)   # east is right


def test_point_90_degrees_away_is_on_the_limb_and_antipode_is_behind():
    view = globe.View(lat=0, lon=0, scale=1)
    x, y, depth = globe.project_points(view, np.array([0.0, 0.0]), np.array([90.0, 180.0]))
    assert math.hypot(x[0], y[0]) == pytest.approx(1)
    assert depth[0] == pytest.approx(0, abs=1e-12)
    assert depth[1] == pytest.approx(-1)


def test_inverse_round_trip():
    view = globe.View(lat=40, lon=20, scale=2)
    for lat, lon in [(40, 20), (55, 30), (20, 5)]:
        sx, sy = globe.to_screen(view, 800, 600, lat, lon)
        back = globe.from_screen(view, 800, 600, sx, sy)
        assert back is not None
        assert back[0] == pytest.approx(lat, abs=1e-9)
        assert back[1] == pytest.approx(lon, abs=1e-9)


def test_click_off_the_globe_is_none():
    view = globe.View(lat=0, lon=0, scale=1)
    assert globe.from_screen(view, 800, 600, 2, 2) is None


def test_scene_is_plain_data(geometry, world):
    view = globe.View(lat=52, lon=-1, scale=1)
    scene = globe.build_scene(geometry, view, 800, 600, current="ne:GBR", highlight="ne:FRA")
    assert scene["width"] == 800 and scene["height"] == 600
    g = scene["globe"]
    assert g["cx"] == 400 and g["cy"] == 300 and g["r"] == pytest.approx(270)
    coords, rings, shapes = scene["coords"], scene["rings"], scene["shapes"]
    assert coords.dtype == np.float32 and rings.dtype == np.int32 and shapes.dtype == np.int32
    assert rings[0] == 0 and rings[-1] * 2 == len(coords)
    assert shapes[0] == 0 and shapes[-1] == len(rings) - 1
    assert len(scene["shape_style"]) == len(shapes) - 1
    assert len(scene["shape_country"]) == len(shapes) - 1
    # Every drawn point is on or inside the globe's disc.
    xy = coords.reshape(-1, 2).astype(np.float64)
    dist = np.hypot(xy[:, 0] - 400, xy[:, 1] - 300)
    assert dist.max() <= 270 * 1.0001
    # The United Kingdom is drawn and outlined, France highlighted, Australia (far side) not drawn.
    drawn = set(scene["shape_country"])
    assert "ne:GBR" in drawn and "ne:FRA" in drawn and "ne:AUS" not in drawn
    assert scene["current"] == [i for i, c in enumerate(scene["shape_country"]) if c == "ne:GBR"]
    assert scene["highlight"] == [i for i, c in enumerate(scene["shape_country"]) if c == "ne:FRA"]
    assert scene["cross"]["x"] == 400 and scene["cross"]["y"] == 300
    styles = scene["styles"]
    assert all(set(s) >= {"fill", "stroke"} for s in styles)


def test_antimeridian_edges_are_marked_as_seams(geometry, world):
    # AD-17: Fiji, Russia and Antarctica are split at the 180 degree line in
    # Natural Earth; those edges are filled across but never outlined.
    scene = globe.build_scene(geometry, globe.View(lat=-60, lon=180, scale=1), 800, 600)
    assert scene["seam"].dtype == np.uint8 and len(scene["seam"]) * 2 == len(scene["coords"])
    shapes_with_seams = {scene["shape_country"][si]
                         for si in range(len(scene["shapes"]) - 1)
                         for ri in range(scene["shapes"][si], scene["shapes"][si + 1])
                         if scene["seam"][scene["rings"][ri]:scene["rings"][ri + 1]].any()}
    assert "ne:ATA" in shapes_with_seams
    assert "ne:AUS" not in shapes_with_seams


def test_offsets_use_the_native_index_type(geometry):
    # Pyodide's NumPy is 32-bit; int64 offsets fail there in reduceat and
    # repeat (found in spike S5). np.intp works on both.
    assert geometry.ring_offsets.dtype == np.intp
    assert geometry.shape_ring_offsets.dtype == np.intp
    assert geometry.ring_shape.dtype == np.intp


def test_zoomed_in_drops_shapes_off_screen(geometry):
    whole = globe.build_scene(geometry, globe.View(lat=52, lon=-1, scale=1), 800, 600)
    close = globe.build_scene(geometry, globe.View(lat=52, lon=-1, scale=16), 800, 600)
    assert len(close["shapes"]) < len(whole["shapes"])


def test_projection_is_fast(geometry):
    view = globe.View(lat=52, lon=-1, scale=1)
    globe.build_scene(geometry, view, 1200, 900)
    start = time.perf_counter()
    for i in range(20):
        globe.build_scene(geometry, globe.View(lat=52, lon=-1 + i, scale=1), 1200, 900)
    per_frame_ms = (time.perf_counter() - start) * 1000 / 20
    assert per_frame_ms < 50, per_frame_ms
