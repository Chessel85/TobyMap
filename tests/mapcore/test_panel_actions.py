"""The Information panel's group counts, Within's distances, Enter to go to an item, and Go to and
Type a bearing from the panel and Details (P2-T17k; INF-10, DP155, NAV-8, NAV-12).

Desktop checklist 10.4: each group heading says how many items it holds. 11.5: Within says the
distance and direction to the area's centre, as Nearby does. 11.7 and DP155: Enter on an item goes
there, to a point, or to an area's centre. 10.5: Ctrl+G, and Ctrl+B, work from the panel and
Details, and the focus stays there: after a jump, on the first item of the same group.
"""
import pytest

from mapcore.describe import words
from mapcore.geo import geodesy
from mapcore.session import MapSession, box_centre

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 100000, "step_m": 25000}   # 8 Nearby items
STATION = (50.9074977, -1.4142289)


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


def group(s, gid):
    return next(g for g in s.panel() if g["id"] == gid)


# The count on each group heading (desktop 10.4) ---------------------------------------------

def test_each_group_heading_says_how_many_items_it_holds(session):
    within, nearby, crossed = session.panel()
    assert within["label"] == "Within, 3 items"
    assert nearby["label"] == "Nearby, 8 items" and len(nearby["items"]) == 8
    assert crossed["label"] == "Crossed and passed, no items"


def test_one_item_is_one_item(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.settings.set("nearby_count", 1)
    s.start()
    assert group(s, "nearby")["label"] == "Nearby, 1 item"
    s.store.close()


def test_go_to_a_group_keeps_its_plain_name(session):
    labels = [i["label"] for m in session.registry()["menus"] for i in m["items"]]
    assert "Go to Nearby" in labels


# Within's distance and direction (desktop 11.5) ----------------------------------------------

def test_within_says_the_distance_and_direction_to_the_area_centre(session):
    items = group(session, "within")["items"]
    england = next(a for a in session.areas if a.name == "England")
    lat, lon = box_centre(england.record["bbox"])
    distance, _, _ = geodesy.inverse(session.world.lat, session.world.lon, lat, lon)
    label = next(i["label"] for i in items if i["label"].startswith("England, "))
    assert label == f"England, centre {words.distance_text(distance, 'metric')} west"   # Kent is in its south-east
    assert [i["label"].split(",")[0] for i in items] == ["Kent", "England", "United Kingdom"]


# Enter goes to the item (desktop 11.7, DP155) -------------------------------------------------

def test_enter_on_a_within_item_goes_to_the_area_centre(session):
    england = next(a for a in session.areas if a.name == "England")
    session.run("panel.select", item=england.id, group="within")
    r = session.press("Enter", "panel")
    lat, lon = box_centre(england.record["bbox"])
    assert (session.world.lat, session.world.lon) == (round(lat, 6), round(lon, 6))
    assert spoken(r) == [session._place_text()] and r.redraw and r.panel_stale
    assert r.focus == {"region": "panel", "group": "within", "item": None}


def test_enter_on_a_point_goes_to_the_point(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": STATION[0], "lon": STATION[1] - 0.03,
                                                   "zoom_m": 5000, "step_m": 1000})
    s.start()
    station = next(i["id"] for i in group(s, "nearby")["items"] if i["label"].startswith("Southampton Central"))
    s.run("panel.select", item=station, group="nearby")
    r = s.press("Enter", "panel")
    assert abs(s.world.lat - STATION[0]) < 1e-5 and abs(s.world.lon - STATION[1]) < 1e-5
    assert r.focus == {"region": "panel", "group": "nearby", "item": None}
    assert s.press("Alt+,", "map").redraw   # a jump, so back comes back
    assert abs(s.world.lon - (STATION[1] - 0.03)) < 1e-5
    s.store.close()


def test_enter_on_a_group_heading_says_and_does_nothing(session):
    session.run("panel.select", item=None, group="nearby")
    before = (session.world.lat, session.world.lon)
    r = session.press("Enter", "panel")
    assert spoken(r) == [] and r.focus is None   # P2-T18a
    assert (session.world.lat, session.world.lon) == before


def test_enter_on_the_map_is_not_go_there(session):
    assert session.press("Enter", "map") is None


# Ctrl+G and Ctrl+B from the panel and Details (desktop 10.5) ----------------------------------

def test_ctrl_g_from_the_panel_comes_back_to_the_first_item_of_the_same_group(session):
    nearby = group(session, "nearby")["items"]
    session.run("panel.select", item=nearby[2]["id"], group="nearby")
    assert session.press("Ctrl+G", "panel").dialog["submit"] == "goto.set"
    r = session.run("goto.set", text="51.3, 0.5")
    assert spoken(r) == [session._place_text()]
    assert r.focus == {"region": "panel", "group": "nearby", "item": None}


def test_ctrl_g_from_a_group_heading_comes_back_to_that_group(session):
    session.run("panel.select", item=None, group="nearby")
    session.press("Ctrl+G", "panel")
    assert session.run("goto.set", text="51.3, 0.5").focus == {"region": "panel", "group": "nearby", "item": None}


def test_ctrl_g_from_details_comes_back_to_details(session):
    assert session.press("Ctrl+G", "details").dialog["submit"] == "goto.set"
    assert session.run("goto.set", text="51.3, 0.5").focus == {"region": "details"}


def test_ctrl_g_from_the_map_or_the_menu_leaves_the_focus_to_the_shell(session):
    session.press("Ctrl+G", "map")
    assert session.run("goto.set", text="51.3, 0.5").focus is None
    session.press("Ctrl+G", "details")
    session.run("goto.coordinates")   # from the menu bar: back to the map
    assert session.run("goto.set", text="51.2, 1.2").focus is None


def test_a_refused_answer_keeps_the_way_back(session):
    session.run("panel.select", item=None, group="within")
    session.press("Ctrl+G", "panel")
    assert session.run("goto.set", text="nonsense").error
    assert session.run("goto.set", text="51.3, 0.5").focus == {"region": "panel", "group": "within", "item": None}


def test_ctrl_b_from_the_panel_stays_on_the_same_item(session):
    nearby = group(session, "nearby")["items"]
    session.run("panel.select", item=nearby[1]["id"], group="nearby")
    assert session.press("Ctrl+B", "panel").dialog["submit"] == "bearing.set"
    r = session.run("bearing.set", text="90")
    assert r.focus == {"region": "panel", "group": "nearby", "item": nearby[1]["id"]}
    assert session.press("Ctrl+B", "details").dialog
    assert session.run("bearing.set", text="180").focus == {"region": "details"}
