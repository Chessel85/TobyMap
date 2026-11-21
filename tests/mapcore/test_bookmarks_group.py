"""The Bookmarks group of the Information panel (P4-T8c; USR-3, DP219, INF-10): Shift+8, a heading for each
bookmark list with its count, each bookmark with its distance and direction, Enter, Space, Shift+M and Ctrl+S."""
import pytest

from mapcore.commands import registry
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def group(s):
    return next(g for g in s.panel(open={"bookmarks"}) if g["id"] == "bookmarks")


def lists_of(g):
    return {i["label"]: [c["label"] for c in i["children"]] for i in g["items"]}


def stocked(s):
    """Castles (Zeta north, Alpha east, here) and Holidays (one), the way the dialog makes them."""
    b = s.bookmarks
    b.lists[0].name = "Castles"
    b.add(0, "Zeta", 51.16, -1.31)
    b.add(0, "Alpha", 51.06, -1.11)
    b.add(0, "Here", 51.06, -1.31)
    b.new_list("Holidays")
    b.add(1, "Rome", 41.9, 12.5)
    s.bookmarks_changed(s.start())


# The key and the group ----------------------------------------------------------------------------

def test_shift_8_goes_to_the_bookmarks_group(s):
    assert registry.panel_groups()[-1] == "bookmarks"
    assert registry.default_key("panel.bookmarks") == "Shift+8"
    r = s.press("Shift+8", "map")
    assert r.focus == {"region": "panel", "group": "bookmarks", "heading": True}


def test_the_group_is_filled_only_when_open(s):
    closed = next(g for g in s.panel(open=set()) if g["id"] == "bookmarks")
    assert closed["filled"] is False and closed["label"] == "Bookmarks"


# Headings and items -----------------------------------------------------------------------------

def test_each_list_is_a_heading_with_its_count_and_its_bookmarks(s):
    stocked(s)
    g = group(s)
    assert g["label"] == "Bookmarks, 2 items, in list order"
    assert [i["label"] for i in g["items"]] == ["Castles, 3 items", "Holidays, 1 item"]
    assert all(i["id"].startswith("heading:") for i in g["items"])
    castles = lists_of(g)["Castles, 3 items"]
    assert castles[0].startswith("Zeta, ") and "north" in castles[0]
    assert castles[1].startswith("Alpha, ") and "east" in castles[1]
    assert castles[2] == "Here, here"
    assert lists_of(g)["Holidays, 1 item"][0].startswith("Rome, ") and "kilometres" in lists_of(g)["Holidays, 1 item"][0]


def test_a_list_with_nothing_in_it_says_no_items(s):
    stocked(s)
    s.bookmarks.new_list("Empty")
    s.bookmarks_changed(s.start())
    assert "Empty, no items" in lists_of(group(s))


def test_a_list_switched_off_is_not_shown(s):
    stocked(s)
    s.bookmarks.set_on(1, False)
    s.bookmarks_changed(s.start())
    g = group(s)
    assert [i["label"] for i in g["items"]] == ["Castles, 3 items"]
    assert g["label"].startswith("Bookmarks, 1 item")


def test_the_empty_group_says_how_to_make_a_bookmark(s):
    g = group(s)
    assert g["label"] == "Bookmarks, no items" and g["items"] == []
    assert g["empty"] == "No bookmarks. Press Ctrl+Enter to make one."


def test_the_group_is_filled_again_when_bookmarks_change(s):
    assert group(s)["items"] == []
    s.run("bookmark.open")
    s.run("bookmark.add", text="Spot", list=0)
    assert [i["label"] for i in group(s)["items"]] == ["Bookmarks, 1 item"]
    assert lists_of(group(s))["Bookmarks, 1 item"] == ["Spot, here"]


# The keys on an item ----------------------------------------------------------------------------

def test_enter_goes_to_the_bookmark(s):
    stocked(s)
    item = next(c for c in group(s)["items"][1]["children"])
    r = s.run("panel.go", item=item["id"], group="bookmarks")
    assert said(r).startswith("Rome. ")
    assert round(s.world.lat, 1) == 41.9 and round(s.world.lon, 1) == 12.5
    assert r.focus == {"region": "panel", "group": "bookmarks", "heading": True}


def test_enter_on_a_list_heading_does_nothing(s):
    stocked(s)
    heading = group(s)["items"][0]
    r = s.run("panel.go", item=heading["id"], group="bookmarks")
    assert not r.announcements and s.world.lon == pytest.approx(-1.31)


def test_space_hears_its_direction(s):
    stocked(s)
    item = group(s)["items"][0]["children"][1]   # Alpha, east
    r = s.run("panel.hear", item=item["id"], group="bookmarks")
    assert r.sounds and r.voice and "Alpha" in r.voice["text"]


def test_shift_m_measures_to_it_without_moving(s):
    stocked(s)
    group(s)
    zeta = group(s)["items"][0]["children"][0]
    r = s.run("measure.to", item=zeta["id"], group="bookmarks")
    assert said(r).startswith("Zeta, ") and "north" in said(r)
    here = group(s)["items"][0]["children"][2]
    assert said(s.run("measure.to", item=here["id"], group="bookmarks")) == "Here, here"
    assert s.world.lon == pytest.approx(-1.31) and s.world.lat == pytest.approx(51.06)


# Ctrl+S ---------------------------------------------------------------------------------------

def sort_to(s, n):
    s.press("Shift+8", "map")
    for _ in range(n):
        s.run("panel.sort")


def names(s):
    return [[c["name"] for c in i["children"]] for i in group(s)["items"]]


def test_ctrl_s_cycles_list_order_name_distance_bearing(s):
    stocked(s)
    assert names(s)[0] == ["Zeta", "Alpha", "Here"] and group(s)["label"].endswith("in list order")
    sort_to(s, 1)
    assert names(s)[0] == ["Alpha", "Here", "Zeta"] and group(s)["label"].endswith("by name")
    sort_to(s, 1)
    assert names(s)[0] == ["Here", "Zeta", "Alpha"] and group(s)["label"].endswith("by distance")
    sort_to(s, 1)
    assert names(s)[0].index("Zeta") < names(s)[0].index("Alpha")   # north, then east
    assert group(s)["label"].endswith("clockwise from north")
    sort_to(s, 1)
    assert names(s)[0] == ["Zeta", "Alpha", "Here"] and group(s)["label"].endswith("in list order")
    assert [i["label"] for i in group(s)["items"]] == ["Castles, 3 items", "Holidays, 1 item"]   # the lists stay
