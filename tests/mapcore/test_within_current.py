"""Within's first item is the current feature when it is a line or a place (P3-T29h; INF-10, LOC-4, NAV-4).

The PO's answer R3, 19 November 2026: the Within list stays as it is, but if you are on a point or a line,
that is its top item. Stepping onto a place or a line does not make it the current feature, only going to it
(Enter on an item, a search, or hierarchy mode) does.
"""
import json
from pathlib import Path

import pytest

from mapcore.session import MapSession

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "osm" / "southampton-itchen.geojson"
STATION = (50.9074977, -1.4142289)


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.95, "lon": -1.40, "zoom_m": 5000, "step_m": 5000})
    s.start()
    yield s
    s.store.close()


def place(s, lat, lon, step_m=100, zoom_m=5000):
    s.world.lat, s.world.lon = lat, lon
    s.world.step_index = s.world.step_list.index(step_m)
    s.world.zoom_index = s.world.zoom_list.index(zoom_m)
    s.areas = s._here()


def within(s):
    return next(g for g in s.panel() if g["id"] == "within")


def labels(s):
    return [i["label"] for i in within(s)["items"]]


def nearby_item(s, text):
    return next(i for g in s.panel() if g["id"] == "nearby" for i in g["items"] if i["label"].startswith(text))


def go_to(s, text):
    s.run("panel.go", item=nearby_item(s, text)["id"], group="nearby")


def areas_only(s):
    """The labels of the areas, as Within has them with no line or place current."""
    return [i["label"] for i in within(s)["items"] if ", centre " in i["label"]]


def test_going_to_a_station_by_enter_puts_it_first_in_within(session):
    place(session, STATION[0] + 0.002, STATION[1])
    go_to(session, "Southampton Central")
    assert session.current_feature.name == "Southampton Central"
    got = labels(session)
    assert got[0] == "Southampton Central, here", got
    assert all(", centre " in l for l in got[1:]) and len(got) > 1
    assert within(session)["label"].startswith("Within, %d items" % len(got))


def test_going_to_a_station_by_search_puts_it_first_in_within(session):
    found = next(f for f in session.store.search("Southampton Central") if f.name == "Southampton Central")
    session.search_go(found.id)
    assert session.current_feature.name == "Southampton Central"
    assert labels(session)[0] == "Southampton Central, here"


def test_going_to_the_river_puts_it_first_then_the_areas_as_where_am_i_says(session):
    place(session, 50.95, -1.40)
    go_to(session, "River Itchen")
    assert session.current_feature.name == "River Itchen"
    got = labels(session)
    assert got[0] == "River Itchen, here", got
    assert [l.split(",")[0] for l in got[1:]] == [l.split(",")[0] for l in areas_only(session)]
    assert len(got) == len(areas_only(session)) + 1


def test_one_step_away_the_current_feature_is_the_area_and_the_item_goes(session):
    place(session, 50.95, -1.40)
    go_to(session, "River Itchen")
    assert labels(session)[0].startswith("River Itchen")
    session.run("move.north")
    session.release()
    assert session.current_feature.name != "River Itchen"
    assert not any(l.startswith("River Itchen") for l in labels(session))


def test_stepping_onto_a_place_does_not_make_it_the_current_feature(session):
    place(session, STATION[0], STATION[1])
    assert session.current_feature.name == session._first_said_here().name != "Southampton Central"
    assert not any(l.startswith("Southampton Central") for l in labels(session))


def test_with_an_area_current_within_is_the_areas_only(session):
    place(session, 50.95, -1.40)
    assert all(", centre " in l for l in labels(session))


def test_the_item_is_measured_to_the_lines_nearest_point_and_enter_goes_there(session):
    place(session, 50.95, -1.40)
    go_to(session, "River Itchen")
    session.run("move.east")
    session.release()
    assert session.current_feature.name != "River Itchen"
    session.set_current_feature(next(i["id"] for g in session.panel() if g["id"] == "nearby" for i in g["items"]
                                     if i["label"].startswith("River Itchen")))
    first = within(session)["items"][0]
    assert first["label"].startswith("River Itchen, ") and not first["label"].endswith("here")
    spot = session._spots[("within", first["id"])]
    assert spot[0].name == "River Itchen" and spot[1:] != (session.world.lat, session.world.lon)


def test_up_in_hierarchy_mode_from_a_line_goes_to_the_smallest_area_holding_all_of_it(session):
    place(session, 50.95, -1.40)
    go_to(session, "River Itchen")
    river = session.current_feature
    holding = session._parents(river)
    assert holding, "the River Itchen is held by an area in the test pack"
    session.run("mode.toggle")
    r = session.run("move.north")
    if r.dialog is None:
        assert session.current_feature.id == holding[0].id
    else:
        assert [l.split(",")[0] for l in r.dialog["lines"]] == [p.name for p in holding]
    assert all(p.id in session.store.relationships(river.id).get("in", ()) for p in holding)   # holds all of it
