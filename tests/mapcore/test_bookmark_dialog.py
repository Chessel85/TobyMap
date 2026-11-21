"""The bookmark dialog (P4-T8b; USR-1, DP219): Ctrl+Enter on the map or on an item of the Information panel.

The core describes the dialog and carries out its answers; the shells only show it. Nothing here touches a file."""
import json

import pytest

from mapcore.commands import registry
from mapcore.describe import say
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
SWITZERLAND = {"lat": 46.8, "lon": 8.2, "zoom_m": 100000, "step_m": 1000}


@pytest.fixture
def here(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


@pytest.fixture
def swiss(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(SWITZERLAND))
    s.start()
    yield s
    s.store.close()


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def marks(s, li=0):
    return [(m.name, m.lat, m.lon, m.feature) for m in s.bookmarks.lists[li].bookmarks]


# The keys ---------------------------------------------------------------------------------------

def test_ctrl_enter_is_the_bookmark_dialog_on_the_map_and_on_an_item():
    assert registry.default_key("bookmark.open") == "Ctrl+Enter"
    assert registry.by_name("bookmark.open").region == "map"
    assert registry.default_key("panel.bookmark") == "Ctrl+Enter"
    assert registry.by_name("panel.bookmark").region == "panel"


# On the map -------------------------------------------------------------------------------------

def test_the_dialog_on_the_map_is_filled_from_the_current_feature_and_where_you_are(here):
    name = here.current_feature.name
    d = here.run("bookmark.open").dialog
    assert d["kind"] == "bookmark" and d["title"] == "Bookmark"
    assert d["name"] == name and d["feature"] == name
    assert d["coordinates"]
    assert d["lists"] == {"items": ["Bookmarks"], "current": 0}
    assert d["words"]["ok"] == "OK" and d["words"]["cancel"] == "Cancel" and d["words"]["new_list"] == "New list"


def test_ok_adds_the_bookmark_at_the_place_and_says_so_once(here):
    name = here.current_feature.name
    d = here.run("bookmark.open").dialog
    r = here.run(d["add"], text=d["name"], list=0)
    assert marks(here) == [(name, here.world.lat, here.world.lon, name)]
    assert said(r) == f"Bookmarked {name} in Bookmarks."
    assert json.loads(r.bookmarks)["features"][0]["properties"]["name"] == name   # the file's new text


def test_a_second_bookmark_is_numbered_and_cancel_makes_nothing(here):
    name = here.current_feature.name
    for _ in range(2):
        d = here.run("bookmark.open").dialog
        here.run(d["add"], text=d["name"], list=0)
    d = here.run("bookmark.open").dialog
    assert d["name"] == f"{name}_2"
    # Cancel runs nothing: the bookmarks are as they were.
    assert [m[0] for m in marks(here)] == [name, f"{name}_1"]


def test_the_name_may_be_changed_and_may_not_be_empty(here):
    d = here.run("bookmark.open").dialog
    r = here.run(d["add"], text="   ", list=0)
    assert r.error == say("bookmark.name_empty") and not marks(here)
    here.run(d["add"], text="  My   place ", list=0)
    assert marks(here)[0][0] == "My place"


def test_the_dialog_opens_on_the_list_used_last(here):
    d = here.run("bookmark.open").dialog
    here.run(d["new_list"], text="Castles")
    here.run(d["add"], text="One", list=1)
    assert here.bookmarks.last_used == 1
    assert here.run("bookmark.open").dialog["lists"] == {"items": ["Bookmarks", "Castles"], "current": 1}


# New list ---------------------------------------------------------------------------------------

def test_new_list_is_added_to_the_list_box_and_chosen(here):
    d = here.run("bookmark.open").dialog
    r = here.run(d["new_list"], text="Castles")
    assert r.bookmark_lists == {"items": ["Bookmarks", "Castles"], "current": 1}
    assert [l.name for l in here.bookmarks.lists] == ["Bookmarks"]   # made for real only by OK


def test_new_list_refuses_an_empty_or_used_name(here):
    d = here.run("bookmark.open").dialog
    assert here.run(d["new_list"], text="").error == say("bookmark.list_name_empty")
    assert here.run(d["new_list"], text="bookmarks").error == say("bookmark.list_name_taken", name="bookmarks")
    here.run(d["new_list"], text="Castles")
    assert here.run(d["new_list"], text="CASTLES").error


def test_ok_on_a_new_list_makes_the_list_and_bookmarks_into_it(here):
    d = here.run("bookmark.open").dialog
    here.run(d["new_list"], text="Castles")
    r = here.run(d["add"], text="Home", list=1)
    assert [l.name for l in here.bookmarks.lists] == ["Bookmarks", "Castles"]
    assert [m[0] for m in marks(here, 1)] == ["Home"] and here.bookmarks.last_used == 1
    assert said(r) == "Bookmarked Home in Castles."


def test_a_new_list_made_then_cancelled_is_not_kept(here):
    d = here.run("bookmark.open").dialog
    here.run(d["new_list"], text="Castles")
    again = here.run("bookmark.open").dialog
    assert again["lists"]["items"] == ["Bookmarks"]


# On an item -------------------------------------------------------------------------------------

def test_ctrl_enter_on_an_item_bookmarks_the_items_own_point_by_its_name(swiss):
    items = swiss.panel(open={"bordering"})
    bordering = next(g for g in items if g["id"] == "bordering")["items"]
    france = next(i for i in bordering if i["name"] == "France")
    lat, lon = swiss._point_of(swiss.store.feature(france["id"]))   # the point Enter goes to
    here = (swiss.world.lat, swiss.world.lon)
    d = swiss.run("panel.bookmark", item=france["id"], group="bordering").dialog
    assert d["name"] == "France" and d["feature"] == "France"
    r = swiss.run(d["add"], text=d["name"], list=0)
    assert marks(swiss) == [("France", pytest.approx(lat), pytest.approx(lon), "France")]
    assert (swiss.world.lat, swiss.world.lon) == here   # it never moves you
    assert said(r) == "Bookmarked France in Bookmarks."


def test_ctrl_enter_on_a_group_heading_does_nothing(swiss):
    r = swiss.run("panel.bookmark", item="group:bordering", group="bordering")
    assert r.dialog is None and not r.announcements
