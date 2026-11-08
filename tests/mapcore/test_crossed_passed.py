"""Crossed and passed (P2-T5; ANN-2, ANN-7, SCP-6, SON-6, NFR-1, architecture 7.5).

After a move is described, the core searches along the move's path, in the background, for
the lines it crossed, the areas it passed over and the points it passed near. The list is in
the Information panel's Crossed and passed group, for the most recent move only, with a soft
earcon when something is added. Nothing in it is ever spoken.
"""
import json
import math
import time
from pathlib import Path

import pytest
import shapely.geometry

from mapcore.geo import geodesy
from mapcore.session import MapSession
from tests.world_pack import world_pack_path

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "osm" / "southampton-itchen.geojson"
STATION = (50.9074977, -1.4142289)
M_PER_DEG_LAT = 111_250.0


def sample(ident):
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    return next(f for f in data["features"] if f["properties"]["id"] == ident)


def m_per_deg_lon(lat):
    return geodesy.parallel_radius_m(lat) * math.pi / 180.0


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.95, "lon": -1.40, "zoom_m": 5000, "step_m": 5000})
    s.start()
    yield s
    s.store.close()


def place(s, lat, lon, step_m, zoom_m=5000):
    s.world.lat, s.world.lon = lat, lon
    s.world.step_index = s.world.step_list.index(step_m)
    s.world.zoom_index = s.world.zoom_list.index(zoom_m)


def crossed_group(s):
    return next(g for g in s.panel() if g["id"] == "crossed")


def labels(s):
    return [i["label"] for i in crossed_group(s)["items"]]


def step_east_and_search(s):
    r = s.run("move.east")
    assert r.background, "a move leaves the search to be done in the background"
    return r, s.crossed_now()


def test_a_1_km_step_across_the_river_lists_it_crossed_with_the_earcon_and_nothing_spoken(session):
    line = max(sample("osm:r7703089")["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    move, done = step_east_and_search(session)
    assert any(l.startswith("River Itchen, crossed") for l in labels(session)), labels(session)
    assert done.earcons == ["crossed_added"]
    assert not done.announcements
    assert not any("Itchen" in a["text"] for a in move.announcements)


def test_a_path_300_metres_from_the_station_lists_it_and_800_metres_does_not(session):
    lat, lon = STATION
    start_lon = lon - 2500 / m_per_deg_lon(lat)
    place(session, lat + 300 / M_PER_DEG_LAT, start_lon, 5000)
    step_east_and_search(session)
    station = [l for l in labels(session) if l.startswith("Southampton Central")]
    assert station and station[0].startswith("Southampton Central, passed, closest 300 metres"), labels(session)

    place(session, lat + 800 / M_PER_DEG_LAT, start_lon, 5000)
    step_east_and_search(session)
    assert not [l for l in labels(session) if l.startswith("Southampton Central")], labels(session)


def test_the_passed_nearby_distance_can_be_a_fixed_distance(session):
    lat, lon = STATION
    session.run("settings.set", field="passed_nearby", value="fixed")
    session.run("settings.set", field="passed_fixed_m", value=1000)
    place(session, lat + 800 / M_PER_DEG_LAT, lon - 2500 / m_per_deg_lon(lat), 5000)
    step_east_and_search(session)
    assert [l for l in labels(session) if l.startswith("Southampton Central, passed")], labels(session)


def test_a_5_km_step_over_the_small_lake_lists_it_passed_over(session):
    lake = shapely.geometry.shape(sample("osm:r10303325")["geometry"])
    c = lake.centroid
    place(session, c.y, c.x - 2500 / m_per_deg_lon(c.y), 5000)
    step_east_and_search(session)
    assert any(l.startswith("Longbridge Lake, passed over") for l in labels(session)), labels(session)


def test_an_area_you_end_in_is_not_passed_over(session):
    lake = shapely.geometry.shape(sample("osm:r10303325")["geometry"])
    c = lake.centroid
    place(session, c.y, c.x - 1000 / m_per_deg_lon(c.y), 1000)
    step_east_and_search(session)
    assert any(a.name == "Longbridge Lake" for a in session.areas)
    assert not any(l.startswith("Longbridge Lake") for l in labels(session)), labels(session)


def test_the_list_is_replaced_after_each_move_and_emptied_by_a_jump(session):
    line = max(sample("osm:r7703089")["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    step_east_and_search(session)
    assert labels(session)
    _, done = step_east_and_search(session)    # 700 m to 1,700 m east: nothing more
    assert labels(session) == [] and done.earcons == []
    assert crossed_group(session)["empty"] == "Nothing crossed or passed on the last move."
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    step_east_and_search(session)
    session.run("goto.set", text="50.95, -1.40")
    assert labels(session) == []


def test_a_layer_that_is_off_or_out_of_its_zoom_range_is_left_out(session):
    line = max(sample("osm:r7703089")["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    session.run("layers.set", layer="rivers", field="on", value=False)
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    step_east_and_search(session)
    assert not any("Itchen" in l for l in labels(session))
    session.run("layers.set", layer="rivers", field="on", value=True)
    session.run("layers.set", layer="rivers", field="max_zoom_m", value=1000)
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    step_east_and_search(session)
    assert not any("Itchen" in l for l in labels(session))


def test_the_earcon_can_be_switched_off(session):
    line = max(sample("osm:r7703089")["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    session.run("settings.set", field="earcon_on_crossed_added", value=False)
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    _, done = step_east_and_search(session)
    assert labels(session) and done.earcons == []


def test_a_newer_move_throws_away_an_unfinished_search(session):
    line = max(sample("osm:r7703089")["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    session.run("move.east")
    job = session.crossed_job()
    session.run("move.east")                      # before the first search has finished
    assert session.crossed_search(job) is None
    assert session.crossed_finish(job, []).panel_stale is False


def test_a_held_run_lists_what_the_whole_run_crossed(session):
    line = max(sample("osm:r7703089")["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    place(session, lat, lon - 2200 / m_per_deg_lon(lat), 1000)
    session.run("move.east")                      # the press: 1,200 m west of the river after it
    session.crossed_job()
    for _ in range(3):
        session.run("move.east", held=True, repeat=True)   # the river is crossed on the second
    r = session.release()
    assert r.background
    session.crossed_now()
    assert any(l.startswith("River Itchen, crossed") for l in labels(session)), labels(session)


def test_shift_and_a_number_goes_to_that_group_for_as_many_groups_as_there_are(session):
    """The PO's answer, 8 November 2026: Shift+1 for the first group, Shift+2 for the second, and
    so on, made from the list of groups, so a new group has its key without more code."""
    groups = [g["id"] for g in session.panel()]
    assert groups == ["within", "nearby", "crossed"]
    for number, group in enumerate(groups, start=1):
        for region in ("map", "panel"):
            assert session.press(f"Shift+{number}", region).focus == {"region": "panel", "group": group}
    assert session.press(f"Shift+{len(groups) + 1}", "map") is None   # no fourth group yet, so no key
    items = {i["name"]: (i["label"], i["key"]) for m in session.registry()["menus"] for i in m["items"]}
    assert items["panel.within"] == ("Go to Within", "Shift+1")
    assert items["panel.crossed"] == ("Go to Crossed and passed", "Shift+3")


def test_the_announcement_does_not_wait_for_the_search(session):
    """NFR-1: the move's own time is the same whatever the search would cost, because it is not done there."""
    line = max(sample("osm:r7703089")["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    calls = []
    real = session.store.along_path
    session.store.along_path = lambda *a, **k: calls.append(1) or real(*a, **k)
    place(session, lat, lon - 300 / m_per_deg_lon(lat), 1000)
    session.run("move.east")
    assert calls == []


def test_it_works_over_the_north_pole_and_across_the_180_degree_line(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 89.9, "lon": 179.9, "zoom_m": 1000000, "step_m": 25000})
    s.start()
    s.run("orientation.cycle")                    # cardinal facing, north
    r = s.run("move.north")
    assert r.background
    assert s.crossed_now() is not None            # the search runs without an error over the pole
    s.world.lat, s.world.lon = 0.0, 179.99
    s.run("move.east")
    assert s.crossed_now() is not None
    s.store.close()


@pytest.mark.skipif(world_pack_path() is None, reason="the world pack is not built on this computer")
def test_a_100_km_step_across_luxembourg_lists_it_passed_over_on_the_world_pack():
    s = MapSession(packs=[world_pack_path()], saved_state={"lat": 49.75, "lon": 5.4, "zoom_m": 250000,
                                                           "step_m": 100000})
    s.start()
    started = time.perf_counter()
    s.run("move.east")
    s.crossed_now()
    assert any(l.startswith("Luxembourg, passed over") for l in labels(s)), (labels(s), time.perf_counter() - started)
    s.store.close()


def test_details_of_a_listed_river_or_station_give_its_type_and_no_area(session):
    session.run("panel.select", item="osm:n638908005")
    lines = session.details().splitlines()
    assert lines[:2] == ["Southampton Central", "Type: railway station"]
    assert not any(l.startswith("Area:") for l in lines)
