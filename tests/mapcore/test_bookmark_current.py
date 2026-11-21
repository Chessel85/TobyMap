"""A bookmark as the current feature (P4-T8d; USR-1, DP219 point 6, DP211 point 7).

Enter on a bookmark in the Bookmarks group makes it the current feature. Then Delete deletes it after asking,
Ctrl+Enter renames it, and Ctrl+X, Ctrl+C and Ctrl+V cut, copy and paste it into another bookmark list. The keys
work on the map and in the Information panel only, never in a text box or Details (p4-t0f-keys.md)."""
import json

import pytest

from mapcore.commands import keys as keymaps
from mapcore.commands import registry
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    b = s.bookmarks
    b.lists[0].name = "Castles"
    b.add(0, "Winchester", 51.06, -1.31, feature="Hampshire")
    b.add(0, "Alpha", 51.06, -1.11, feature="Hampshire", note="The east gate")
    b.new_list("Holidays")
    b.add(1, "Rome", 41.9, 12.5)
    s.bookmarks_changed(s.start())
    yield s
    s.store.close()


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def group(s, gid="bookmarks"):
    return next(g for g in s.panel(open={gid}) if g["id"] == gid)


def names(s, li):
    return [m.name for m in s.bookmarks.lists[li].bookmarks]


def make_alpha_current(s):
    group(s)
    r = s.run("panel.go", item="bookmark:0:1", group="bookmarks")
    s.run("panel.select", item=None, group="bookmarks")   # the focus is on the group's heading after Enter
    return r


# The keys --------------------------------------------------------------------------------------------

def test_the_keys_on_the_map_and_in_the_panel():
    for name, key in {"bookmark.delete": "Delete", "bookmark.cut": "Ctrl+X", "bookmark.copy": "Ctrl+C",
                      "bookmark.paste": "Ctrl+V"}.items():
        assert registry.default_key(name) == key and registry.by_name(name).region == "map"
        panel = "panel." + name.replace(".", "_")
        assert registry.default_key(panel) == key and registry.by_name(panel).region == "panel"


def test_the_keys_never_reach_details_or_anywhere_else():
    """Details' text keeps Ctrl+C, and a text box keeps all four: none is a global key (p4-t0f-keys.md)."""
    for platform in ("desktop", "web"):
        for key in ("Delete", "Ctrl+X", "Ctrl+C", "Ctrl+V"):
            assert registry.command_for_key(platform, key, "details") is None
            assert key not in registry.keymap(platform)["global"]


def test_on_a_mac_cmd_and_cmd_backspace():
    for version in ("desktop", "browser"):
        mac = keymaps.resolve(None, version, "mac")
        assert mac["bookmark.copy"] == "Cmd+C" and mac["panel.bookmark_paste"] == "Cmd+V"
        assert mac["bookmark.cut"] == "Cmd+X"
        assert mac["bookmark.delete"] == "Cmd+Backspace" and mac["panel.bookmark_delete"] == "Cmd+Backspace"


# Enter makes it current ------------------------------------------------------------------------------

def test_enter_on_a_bookmark_makes_it_the_current_feature(s):
    r = make_alpha_current(s)
    assert said(r).startswith("Alpha. ")
    assert s.current_bookmark is s.bookmarks.lists[0].bookmarks[1]


def test_a_move_away_ends_it(s):
    make_alpha_current(s)
    s.run("move.north")
    assert s.current_bookmark is None
    assert s.current_feature is not None   # the usual rule again


def test_another_current_feature_ends_it(s):
    make_alpha_current(s)
    s.set_current_feature(s.current_feature.id)
    assert s.current_bookmark is None


def test_space_starts_with_the_bookmark(s):
    make_alpha_current(s)
    text = said(s.press("Space", "map"))
    assert text.startswith("Alpha, here. ")


def test_details_tells_the_bookmark(s):
    make_alpha_current(s)
    lines = s.details().split("\n")
    assert lines[0] == "Alpha"
    assert "Type: bookmark" in lines
    assert "Bookmark list: Castles" in lines
    assert any(line.startswith("Location: ") for line in lines)
    assert "Feature: Hampshire" in lines
    assert "Note: The east gate" in lines


def test_the_groups_about_a_feature_say_it_is_a_bookmark(s):
    make_alpha_current(s)
    for gid in ("bordering", "contains", "overlapping"):
        g = group(s, gid)
        assert g["items"] == []
        assert g["empty"] == "The current feature is the bookmark Alpha, which is only a point."
        assert "Alpha" not in g["label"]


def test_shift_m_with_no_item_measures_to_the_bookmark(s):
    make_alpha_current(s)
    assert said(s.run("measure.to")) == "Alpha, here"


def test_no_current_bookmark_says_how_to_make_one(s):
    for key in ("Delete", "Ctrl+X", "Ctrl+C"):
        r = s.press(key, "map")
        assert r.dialog is None and "blocked" in r.earcons
        assert said(r) == "No bookmark is the current feature. Enter on a bookmark in the Bookmarks group makes it current."


# Delete ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("region", ["map", "panel"])
def test_delete_asks_and_cancel_keeps_it(s, region):
    make_alpha_current(s)
    r = s.press("Delete", region)
    d = r.dialog
    assert d["kind"] == "confirm"
    assert d["text"] == "Delete the bookmark Alpha from Castles?"
    assert d["ok"] == "Delete" and d["cancel"] == "Cancel"
    assert not r.announcements and r.bookmarks is None
    # Cancel runs nothing: the bookmark stays, and is still current.
    assert names(s, 0) == ["Winchester", "Alpha"]
    assert s.current_bookmark is not None


def test_delete_after_asking(s):
    make_alpha_current(s)
    d = s.press("Delete", "panel").dialog
    r = s.run(d["submit"])
    assert said(r) == "Deleted Alpha."
    assert names(s, 0) == ["Winchester"]
    assert r.bookmarks is not None and "Alpha" not in r.bookmarks   # the file is written
    assert s.current_bookmark is None and s.current_feature is not None
    assert [c["name"] for c in group(s)["items"][0]["children"]] == ["Winchester"]   # the group filled again


def test_delete_when_it_is_already_gone_does_nothing(s):
    make_alpha_current(s)
    d = s.press("Delete", "map").dialog
    s.bookmarks.delete(0, 1)
    r = s.run(d["submit"])
    assert r.bookmarks is None and names(s, 0) == ["Winchester"]


# Rename ---------------------------------------------------------------------------------------------

def test_ctrl_enter_renames_the_current_bookmark(s):
    make_alpha_current(s)
    d = s.press("Ctrl+Enter", "map").dialog
    assert d["kind"] == "bookmark" and d["title"] == "Rename bookmark"
    assert d["name"] == "Alpha" and d["feature"] == "Hampshire"
    assert d["lists"] == {"items": ["Castles", "Holidays"], "current": 0}
    r = s.run(d["add"], text="Beta", list=0)
    assert said(r) == "Renamed Alpha to Beta."
    assert names(s, 0) == ["Winchester", "Beta"] and r.bookmarks is not None
    assert s.current_bookmark.name == "Beta"


def test_ctrl_enter_in_the_panel_on_its_heading_renames_it(s):
    make_alpha_current(s)
    d = s.press("Ctrl+Enter", "panel").dialog
    assert d["title"] == "Rename bookmark" and d["name"] == "Alpha"


def test_rename_to_another_list_moves_it(s):
    make_alpha_current(s)
    d = s.press("Ctrl+Enter", "map").dialog
    r = s.run(d["add"], text="Alpha", list=1)
    assert said(r) == "Moved Alpha to Holidays."
    assert names(s, 0) == ["Winchester"] and names(s, 1) == ["Rome", "Alpha"]
    assert s.current_bookmark.name == "Alpha"


def test_rename_and_move_to_a_new_list(s):
    make_alpha_current(s)
    d = s.press("Ctrl+Enter", "map").dialog
    lists = s.run(d["new_list"], text="Gates").bookmark_lists
    assert lists == {"items": ["Castles", "Holidays", "Gates"], "current": 2}
    r = s.run(d["add"], text="East gate", list=2)
    assert said(r) == "Renamed Alpha to East gate and moved it to Gates."
    assert names(s, 2) == ["East gate"]


def test_rename_with_no_name_is_refused(s):
    make_alpha_current(s)
    d = s.press("Ctrl+Enter", "map").dialog
    assert s.run(d["add"], text="  ", list=0).error == "Type a name for the bookmark."
    assert names(s, 0) == ["Winchester", "Alpha"]


def test_ctrl_enter_with_no_current_bookmark_still_makes_one(s):
    d = s.press("Ctrl+Enter", "map").dialog
    assert d["title"] == "Bookmark" and d["add"] == "bookmark.add"


# Cut, copy and paste ---------------------------------------------------------------------------------

def focus_on(s, item):
    group(s)
    s.run("panel.select", item=item, group="bookmarks")


def test_copy_and_paste_into_another_list(s):
    make_alpha_current(s)
    assert said(s.press("Ctrl+C", "map")) == "Copied Alpha."
    focus_on(s, "heading:bookmarks:1")
    r = s.press("Ctrl+V", "panel")
    assert said(r) == "Pasted Alpha_1 into Holidays."
    assert names(s, 0) == ["Winchester", "Alpha"] and names(s, 1) == ["Rome", "Alpha_1"]
    assert r.bookmarks is not None and "Alpha_1" in r.bookmarks
    copied = s.bookmarks.lists[1].bookmarks[1]
    assert (copied.lat, copied.lon, copied.note) == (51.06, -1.11, "The east gate")
    # A copy can be pasted again.
    assert said(s.press("Ctrl+V", "panel")) == "Pasted Alpha_2 into Holidays."


def test_cut_and_paste_on_a_bookmark_moves_it(s):
    make_alpha_current(s)
    assert said(s.press("Ctrl+X", "panel")) == "Alpha will move when pasted."
    assert names(s, 0) == ["Winchester", "Alpha"]   # nothing moves until pasted
    focus_on(s, "bookmark:1:0")   # on Rome, in Holidays
    r = s.press("Ctrl+V", "panel")
    assert said(r) == "Pasted Alpha into Holidays."
    assert names(s, 0) == ["Winchester"] and names(s, 1) == ["Rome", "Alpha"]
    assert json.loads(r.bookmarks)["features"][-1]["properties"] == {
        "name": "Alpha", "list": "Holidays", "feature": "Hampshire", "note": "The east gate"}
    assert s.current_bookmark.name == "Alpha"   # still the same bookmark, now in Holidays
    assert said(s.press("Ctrl+V", "panel")) == "Nothing to paste. Copy or cut a bookmark first."


def test_cut_into_its_own_list_leaves_it(s):
    make_alpha_current(s)
    s.press("Ctrl+X", "map")
    focus_on(s, "heading:bookmarks:0")
    r = s.press("Ctrl+V", "panel")
    assert said(r) == "Alpha is already in Castles."
    assert names(s, 0) == ["Winchester", "Alpha"] and r.bookmarks is None


def test_paste_on_the_map_or_elsewhere_says_where(s):
    make_alpha_current(s)
    s.press("Ctrl+C", "map")
    where = "To paste, go to a bookmark list in the Bookmarks group, Shift+8."
    assert said(s.press("Ctrl+V", "map")) == where
    s.run("panel.select", item=None, group="bookmarks")   # on the group's own heading: no list
    assert said(s.press("Ctrl+V", "panel")) == where
    within = group(s, "within")
    s.run("panel.select", item=within["items"][0]["id"], group="within")
    assert said(s.press("Ctrl+V", "panel")) == where


def test_paste_with_nothing_copied(s):
    assert said(s.press("Ctrl+V", "map")) == "Nothing to paste. Copy or cut a bookmark first."
