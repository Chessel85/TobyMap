"""Line and point features in packs, the store and the map (P2-T10a; DAT-13, SCP-7, AD-11).

A small pack is written with the pipeline's own writer: an area, a few lines
like the graticule's, a line cut at the 180 degree line, and a point. The
store must leave lines and points out of "where am I", find the lines a path
crosses in order, including across the 180 degree line and over a pole, and
the map scene must draw the lines.
"""
import numpy as np
import pytest
import shapely

from mapcore.geo import geodesy
from mapcore.packs import coords, tiles
from mapcore.packs.pack import Pack
from mapcore.store import Store
from mapdata.stages import pack_write
from mapdata.stages.write import drawing_shapes

LAYERS = [{"id": "countries", "name": "Countries", "geometry": "area"},
          {"id": "graticule", "name": "Lines of latitude and longitude", "geometry": "line", "switched_on": False},
          {"id": "stations", "name": "Railway stations", "geometry": "point"}]
LEVELS = [{"id": 0, "tolerance_m": 2000, "min_km2": 1, "tile_level": 3, "view_km": 1000}]


def meridian(lon, south=-89.5, north=89.5):
    return shapely.LineString([(lon, lat) for lat in np.arange(south, north + 0.01, 0.5)])


def parallel(lat):
    return shapely.LineString([(lon, lat) for lon in np.arange(-180.0, 180.01, 1.0)])


FEATURES = [
    ({"id": "test:land", "layer": "countries", "type": "country", "name": "Squareland"},
     shapely.box(0.0, 40.0, 20.0, 60.0)),
    ({"id": "grat:lon10e", "layer": "graticule", "type": "meridian", "name": "10 degrees east"}, meridian(10.0)),
    ({"id": "grat:lon179.5e", "layer": "graticule", "type": "meridian", "name": "179.5 degrees east"},
     meridian(179.5, -60, 60)),
    ({"id": "grat:lon179.5w", "layer": "graticule", "type": "meridian", "name": "179.5 degrees west"},
     meridian(-179.5, -60, 60)),
    ({"id": "grat:lat50n", "layer": "graticule", "type": "parallel", "name": "50 degrees north"}, parallel(50.0)),
    ({"id": "grat:lat89.5n", "layer": "graticule", "type": "parallel", "name": "89.5 degrees north"}, parallel(89.5)),
    # A line across the 180 degree line, stored as its two sides.
    ({"id": "test:dateline", "layer": "graticule", "type": "line", "name": "A bent line"},
     shapely.MultiLineString([[(179.0, -10.0), (180.0, 0.0)], [(-180.0, 0.0), (-179.0, 10.0)]])),
    ({"id": "test:station", "layer": "stations", "type": "station", "name": "Middle station"},
     shapely.MultiPoint([(10.25, 50.25)])),
]


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("lines") / "lines.pack"
    records = [dict(r) for r, _g in FEATURES]
    geoms = [g for _r, g in FEATURES]
    for r in records:
        r["area_km2"] = 0.0 if r["layer"] != "countries" else 1.0
    manifest = {"name": "lines", "sources": [{"name": "made up", "licence": "CC0", "date": "2026-11-05"}],
                "drawing_levels": LEVELS}
    pack_write.write(path, manifest, records, geoms, 1, say=lambda _line: None, layers=LAYERS,
                     drawing_geoms=drawing_shapes(records, geoms, LEVELS, lambda _line: None))
    return path


@pytest.fixture
def store(pack_path):
    s = Store([pack_path])
    yield s
    s.close()


def east_path(lat, lon, km):
    return geodesy.step_parallel(lat, lon, km * 1000).path


def test_lines_and_points_are_stored_in_their_own_tile_entries(pack_path):
    pack = Pack(pack_path)
    kinds = {}
    for key in pack.keys():
        parts = key.split("/")
        if parts[0] == "tile":
            for entry in pack.tile(*map(int, parts[1:])):
                kinds.setdefault(pack.feature(entry.feature)["id"], set()).add(entry.kind)
    assert pack.format == 4
    assert kinds["test:land"] <= {tiles.COVERED, tiles.COMPACT}
    assert kinds["grat:lon10e"] == {tiles.LINES} and kinds["test:station"] == {tiles.POINTS}
    assert [d["geometry"] for d in pack.layers] == ["area", "line", "point"]
    pack.close()


def test_the_pipeline_lookup_finds_only_areas_where_lines_and_points_are(pack_path):
    # The world build's checks stopped here on 6 Nov 2026 when they read a line as an area (P2-T10d).
    from mapdata.stages import lookup
    with lookup.open_pack(pack_path) as pack:
        assert [f["id"] for f in lookup.at(pack, 10.25, 50.25)] == ["test:land"]
        assert lookup.at(pack, 179.5, 0.0) == []


def test_the_build_summary_counts_lines_and_places_not_areas(pack_path, tmp_path):
    from types import SimpleNamespace
    from mapdata.pipeline.build import summary
    from mapdata.pipeline.progress import Progress
    shown = []
    summary(SimpleNamespace(name="lines"), pack_path, [], [], Progress(say=shown.append), tmp_path / "log.txt")
    assert "Countries: 1 area." in shown
    assert "Lines of latitude and longitude: 6 lines." in shown
    assert "Railway stations: 1 place." in shown


def test_a_point_on_a_pack_tile_edge_is_stored_once(pack_path):
    pack = Pack(pack_path)
    station = pack.feature_number("test:station")
    stored = [(key, e) for key in pack.keys() if key.startswith("tile/")
              for e in pack.tile(*map(int, key.split("/")[1:])) if e.feature == station]
    assert len(stored) == 1
    assert coords.to_point_shapes([stored[0][1].data])[0].equals(shapely.MultiPoint([(10.25, 50.25)]))
    pack.close()


def test_where_am_i_never_names_a_line_or_a_point(store):
    assert [a.id for a in store.at(50.25, 10.25)] == ["test:land"]
    assert [a.id for a in store.at(50.0, 10.0)] == ["test:land"]


def test_a_path_east_crosses_the_meridian_where_it_is(store):
    found = store.crossed_lines(east_path(50.5, 9.0, 150))
    assert [c.area.id for c in found] == ["grat:lon10e"]
    assert found[0].lon == pytest.approx(10.0) and found[0].lat == pytest.approx(50.5)
    assert found[0].along_m == pytest.approx(70_900, rel=0.02)


def test_crossings_come_in_the_order_the_path_meets_them(store):
    path = geodesy.step_meridian(49.0, 9.0, 300_000).path   # north across 50 degrees, and not the meridian
    assert [c.area.id for c in store.crossed_lines(path)] == ["grat:lat50n"]
    move = geodesy.step_geodesic(49.0, 9.0, 45.0, 300_000)
    assert [c.area.id for c in store.crossed_lines(move.path)] == ["grat:lon10e", "grat:lat50n"]


def test_a_path_across_the_180_degree_line_crosses_both_sides_in_order(store):
    found = store.crossed_lines(east_path(30.0, 179.0, 200))
    assert [c.area.id for c in found] == ["grat:lon179.5e", "grat:lon179.5w"]
    assert found[0].along_m < found[1].along_m
    west = store.crossed_lines(geodesy.step_parallel(30.0, -179.0, -200_000).path)
    assert [c.area.id for c in west] == ["grat:lon179.5w", "grat:lon179.5e"]


def test_a_line_cut_at_the_180_degree_line_is_still_crossed(store):
    path = geodesy.step_meridian(-2.0, 179.95, 600_000).path   # north just east of the line's lower half
    assert "test:dateline" in [c.area.id for c in store.crossed_lines(path)]


def test_a_path_over_the_pole_crosses_a_circle_round_it_first_on_the_near_side(store):
    move = geodesy.step_geodesic(89.0, 10.0, 0.0, 300_000)
    assert move.lon == pytest.approx(-170.0, abs=0.01)   # it went over the pole
    found = [c for c in store.crossed_lines(move.path) if c.area.id == "grat:lat89.5n"]
    assert len(found) == 1
    assert found[0].lat == pytest.approx(89.5, abs=0.01) and found[0].lon == pytest.approx(10.0, abs=0.01)


def test_crossings_keep_to_the_layers_asked_for(store):
    path = east_path(50.5, 9.0, 150)
    assert store.crossed_lines(path, layers={"countries"}) == []
    assert [c.area.id for c in store.crossed_lines(path, layers={"graticule"})] == ["grat:lon10e"]


def test_nearby_finds_a_line_and_a_point_by_their_nearest_point(store):
    near = {n.area.id: n for n in store.nearby(50.1, 10.1, 30_000, limit=10)}
    assert near["grat:lon10e"].distance_m == pytest.approx(geodesy.inverse(50.1, 10.1, 50.1, 10.0)[0], rel=0.01)
    assert near["test:station"].distance_m == pytest.approx(geodesy.inverse(50.1, 10.1, 50.25, 10.25)[0], rel=0.01)
    assert not near["grat:lon10e"].inside and not near["test:station"].inside


def test_the_map_draws_lines_and_points(pack_path):
    from mapcore.render.scene import SceneBuilder
    from mapcore.world import WorldState

    store = Store([pack_path])
    world = WorldState(lat=50.0, lon=10.0)
    world.zoom_index = world.zoom_list.index(250000)
    frame = SceneBuilder(store).build(world, 800, 600)
    drawn = set(frame["line_area"])
    assert {"grat:lon10e", "grat:lat50n"} <= drawn
    assert len(frame["line_runs"]) - 1 == len(frame["line_style"]) == len(frame["line_area"])
    assert "test:station" in frame["marker_area"] and len(frame["marker_coords"]) == 2
    off = SceneBuilder(store).build(world, 800, 600, layers={"countries"})
    assert off["line_area"] == [] and off["marker_area"] == []
    far = WorldState(lat=50.0, lon=10.0)
    far.zoom_index = far.zoom_list.index(2500000)   # a drawing level
    assert "grat:lon10e" in SceneBuilder(store).build(far, 800, 600)["line_area"]
    store.close()
