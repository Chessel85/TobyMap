"""The River Itchen, Longbridge Lake and Southampton Central station in the test pack (P2-T10c; ANN-2).

They are the test pack's only line, lake and point, for the tests of Crossed and passed.
"""
import json
from pathlib import Path

import pytest
import shapely.geometry

from mapcore.geo import geodesy
from mapcore.session import MapSession

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "osm" / "southampton-itchen.geojson"
STATION = (50.9074977, -1.4142289)


def sample():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    return {f["properties"]["id"]: f for f in data["features"]}


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.95, "lon": -1.40, "zoom_m": 25000, "step_m": 1000})
    s.start()
    yield s
    s.store.close()


def test_the_sample_file_carries_the_odbl_notice_and_the_three_features():
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    assert "Open Database License" in data["licence"] and "OpenStreetMap" in data["licence"]
    assert {f["properties"]["layer"] for f in data["features"]} == {"rivers", "lakes", "stations"}
    assert {f["properties"]["name"] for f in data["features"]} == \
        {"River Itchen", "Longbridge Lake", "Southampton Central"}


def test_the_pack_holds_a_river_a_lake_and_a_station_in_their_layers(session):
    store = session.store
    river = store.feature("osm:r7703089")
    lake = store.feature("osm:r10303325")
    station = store.feature("osm:n638908005")
    assert (river.layer, lake.layer, station.layer) == ("rivers", "lakes", "stations")
    assert river.name == "River Itchen" and station.name == "Southampton Central"
    assert [(l["id"], l["geometry"]) for l in store.packs[0].layers if l["id"] in ("rivers", "lakes", "stations")] == \
        [("rivers", "line"), ("lakes", "area"), ("stations", "point")]


def test_standing_in_the_lake_names_it_but_never_the_river_or_the_station(session):
    point = shapely.geometry.shape(sample()["osm:r10303325"]["geometry"]).representative_point()
    names = [a.name for a in session.store.at(point.y, point.x)]
    assert "Longbridge Lake" in names, names
    assert not {"River Itchen", "Southampton Central"} & {a.name for a in session.store.at(*STATION)}


def test_a_step_across_the_river_crosses_it(session):
    river = sample()["osm:r7703089"]["geometry"]
    line = max(river["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    path = geodesy.step_parallel(lat, lon - 0.003, 600).path
    crossed = session.store.crossed_lines(path, layers={"rivers"})
    assert [c.area.name for c in crossed] == ["River Itchen"]


def test_a_step_across_the_river_plays_the_crossing_sound(session):
    river = sample()["osm:r7703089"]["geometry"]
    line = max(river["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    session.world.lat, session.world.lon = lat, lon - 0.0045    # 300 m west of the river
    session.world.step_index = session.world.step_list.index(500.0)
    assert "line_crossing" in session.run("move.east").earcons
    session.run("layers.set", layer="rivers", field="crossing_earcon", value=None)
    session.world.lat, session.world.lon = lat, lon - 0.0045
    assert "line_crossing" not in session.run("move.east").earcons
