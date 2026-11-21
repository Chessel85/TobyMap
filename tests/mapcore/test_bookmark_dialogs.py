"""The bookmark manager and the bookmark list dialog (P4-T8e; USR-3, ACC-7, DP219 point 7).

The manager is for the bookmark lists; the list dialog for one list's bookmarks. Each has a Close button, changes take
effect and are written at once, and deleting asks first."""
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
    b.add(0, "Alpha", 51.06, -1.11)
    b.add(0, "Corfe", 50.6, -2.05)
    b.new_list("Holidays")
    b.add(1, "Rome", 41.9, 12.5)
    b.new_list("Empty")
    yield s
    s.store.close()


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def names(s, li):
    return [m.name for m in s.bookmarks.lists[li].bookmarks]


def written(r) -> list[str]:
    """The lists in the file text the shell would write."""
    return [l["name"] for l in json.loads(r.bookmarks)["tobymap"]["lists"]]


# The keys and the menu -------------------------------------------------------------------------------

def test_the_manager_is_on_ctrl_shift_b_and_cmd_shift_b_and_in_the_map_menu():
    assert registry.default_key("bookmark.manager_open") == "Ctrl+Shift+B"
    assert registry.by_name("bookmark.manager_open").menu == "Map"
    for version in ("desktop", "browser"):
        assert keymaps.resolve(None, version, "mac")["bookmark.manager_open"] == "Shift+Cmd+B"
    assert registry.command_for_key("desktop", "Ctrl+Shift+B", "map").name == "bookmark.manager_open"
    assert registry.command_for_key("desktop", "Ctrl+Shift+B", "panel").name == "bookmark.manager_open"


def test_the_list_dialog_has_no_key_and_is_in_the_map_menu():
    c = registry.by_name("bookmark.list_open")
    assert c.menu == "Map" and not registry.default_key("bookmark.list_open")


# The bookmark manager --------------------------------------------------------------------------------

def test_the_manager_opens_on_the_list_used_last_and_says_each_list_with_its_count(s):
    s.bookmarks.use(1)
    d = s.run("bookmark.manager_open").dialog
    assert d["kind"] == "bookmark_manager" and d["title"] == "Bookmark manager"
    assert d["lists"]["current"] == 1
    assert [i["label"] for i in d["lists"]["items"]] == ["Castles, 3 bookmarks", "Holidays, 1 bookmark", "Empty, no bookmarks"]
    assert [i["on"] for i in d["lists"]["items"]] == [True, True, True]


def test_each_button_has_words_and_a_close_button_and_there_is_no_ok_to_wait_for(s):
    w = s.run("bookmark.manager_open").dialog["words"]
    assert [w[k] for k in ("new", "rename", "open_list", "up", "down", "delete", "zoom", "save_file", "open_file", "close")] == \
        ["New list", "Rename", "Open list", "Move up", "Move down", "Delete list", "Zoom range", "Save to a file",
         "Open a file", "Close"]


def test_move_up_and_down_are_unavailable_at_the_ends(s):
    items = s.run("bookmark.manager_open").dialog["lists"]["items"]
    assert [(i["up"], i["down"]) for i in items] == [(False, True), (True, True), (True, False)]


def test_a_zoom_range_is_in_the_line_and_a_list_with_none_has_no_words_for_it(s):
    s.run("bookmark.manager_zoom", index=0, low=1000, high=100000)
    items = s.run("bookmark.manager_open").dialog["lists"]["items"]
    assert items[0]["label"] == "Castles, 3 bookmarks, zoom from 1 kilometre to 100 kilometres"
    assert items[1]["label"] == "Holidays, 1 bookmark"


def test_a_new_list_goes_to_the_end_chosen_and_is_kept_at_once(s):
    r = s.run("bookmark.manager_new", text="  Forts ")
    assert [i["name"] for i in r.bookmark_manager["items"]] == ["Castles", "Holidays", "Empty", "Forts"]
    assert r.bookmark_manager["current"] == 3
    assert said(r) == ""   # the focus on the new line says it
    assert written(r) == ["Castles", "Holidays", "Empty", "Forts"]
    assert r.panel_stale   # the Bookmarks group is filled again


def test_a_new_list_with_no_name_or_a_name_in_use_is_refused_and_changes_nothing(s):
    r = s.run("bookmark.manager_new", text="  ")
    assert r.error == "Type a name for the list." and r.bookmarks is None
    r = s.run("bookmark.manager_new", text="holidays")
    assert r.error == "There is already a bookmark list called holidays. Type another name."
    assert len(s.bookmarks.lists) == 3


def test_rename_says_what_changed_and_keeps_the_bookmarks(s):
    r = s.run("bookmark.manager_rename", index=0, text="Forts")
    assert said(r) == "Renamed Castles to Forts." and s.bookmarks.lists[0].name == "Forts"
    assert names(s, 0) == ["Winchester", "Alpha", "Corfe"] and written(r)[0] == "Forts"
    assert s.run("bookmark.manager_rename", index=0, text="holidays").error is not None   # another list's name
    assert said(s.run("bookmark.manager_rename", index=0, text="forts")) == "Renamed Forts to forts."   # other capitals
    r = s.run("bookmark.manager_rename", index=0, text="forts")
    assert r.bookmarks is None and said(r) == ""   # no change, nothing said or written


def test_move_up_and_down_follow_the_list_and_say_nothing(s):
    s.bookmarks.use(0)
    r = s.run("bookmark.manager_move", index=0, by=1)
    assert [i["name"] for i in r.bookmark_manager["items"]] == ["Holidays", "Castles", "Empty"]
    assert r.bookmark_manager["current"] == 1 and said(r) == "" and written(r) == ["Holidays", "Castles", "Empty"]
    assert s.bookmarks.lists[s.bookmarks.last_used].name == "Castles"   # the list used last is the same list
    r = s.run("bookmark.manager_move", index=0, by=-1)   # the first cannot go up: nothing changes
    assert r.bookmarks is None and r.bookmark_manager is None


def test_on_and_off_is_the_check_box_and_says_nothing(s):
    r = s.run("bookmark.manager_on", index=1, on=False)
    assert not s.bookmarks.lists[1].on and said(r) == "" and r.bookmark_manager["items"][1]["on"] is False
    assert json.loads(r.bookmarks)["tobymap"]["lists"][1]["on"] is False
    s.run("bookmark.manager_on", index=1, on=True)
    assert s.bookmarks.lists[1].on


def test_the_zoom_range_is_set_and_said_and_a_minimum_over_the_maximum_is_refused(s):
    r = s.run("bookmark.manager_zoom", index=1, low=0, high=50000)
    assert said(r) == "Zoom range of Holidays: up to 50 kilometres." and s.bookmarks.lists[1].max_zoom_m == 50000
    assert written(r) and r.bookmark_manager["items"][1]["max_zoom_m"] == 50000
    r = s.run("bookmark.manager_zoom", index=1, low=5000, high=1000)
    assert r.error == s.run("layers.check", low=5000, high=1000).error   # the layers' words
    assert s.bookmarks.lists[1].max_zoom_m == 50000 and r.bookmarks is None
    r = s.run("bookmark.manager_zoom", index=1, low=0, high=None)
    assert said(r) == "Zoom range of Holidays: every zoom."


def test_the_zoom_dialog_offers_the_zooms_the_layers_dialog_does(s):
    d = s.run("bookmark.manager_open").dialog
    assert d["zooms"] == s.run("layers.open").dialog["zooms"]
    assert d["every_zoom"] == "No limit" and d["words"]["min_zoom"] and d["words"]["max_zoom"]


def test_delete_list_asks_with_the_count_and_cancel_runs_nothing(s):
    r = s.run("bookmark.manager_delete", index=0)
    q = r.dialog
    assert q["kind"] == "confirm" and q["text"] == "Delete the list Castles and its 3 bookmarks?"
    assert (q["ok"], q["cancel"]) == ("Delete", "Cancel") and q["submit"] == "bookmark.manager_delete_confirm"
    assert len(s.bookmarks.lists) == 3 and r.bookmarks is None
    assert s.run("bookmark.manager_delete", index=1).dialog["text"] == "Delete the list Holidays and its 1 bookmark?"
    assert s.run("bookmark.manager_delete", index=2).dialog["text"] == "Delete the list Empty?"


def test_delete_list_goes_after_yes_and_says_so_and_is_written_at_once(s):
    s.run("bookmark.manager_delete", index=1)
    r = s.run("bookmark.manager_delete_confirm")
    assert said(r) == "Deleted Holidays." and written(r) == ["Castles", "Empty"]
    assert r.bookmark_manager["current"] == 1 and [i["name"] for i in r.bookmark_manager["items"]] == ["Castles", "Empty"]
    assert s.run("bookmark.manager_delete_confirm").earcons == ["blocked"]   # asked once, answered once


def test_deleting_the_only_list_says_a_new_empty_bookmarks_list_follows(s):
    for _ in range(2):
        s.run("bookmark.manager_delete", index=0)
        s.run("bookmark.manager_delete_confirm")
    q = s.run("bookmark.manager_delete", index=0).dialog["text"]
    assert q == "Delete the list Empty? It is the only list, so you will then have a new empty list, Bookmarks."
    r = s.run("bookmark.manager_delete_confirm")
    assert written(r) == ["Bookmarks"] and r.bookmark_manager["items"][0]["label"] == "Bookmarks, no bookmarks"


def test_save_and_open_file_ask_the_shell_and_change_nothing_themselves(s):
    """What they offer and say is in test_bookmark_files.py (P4-T9b, P4-T9c)."""
    r = s.run("bookmark.manager_save_file", index=0)
    assert r.dialog["kind"] == "choose" and r.bookmarks is None
    r = s.run("bookmark.manager_open_file")
    assert r.open_file["submit"] == "bookmark.manager_file_opened" and r.bookmarks is None and not said(r)


def test_the_manager_listing_is_asked_for_again_after_the_list_dialog(s):
    s.run("bookmark.list_delete", list=0, index=0)
    s.run("bookmark.list_delete_confirm")
    r = s.run("bookmark.manager_listing", index=1)
    assert r.bookmark_manager["current"] == 1
    assert r.bookmark_manager["items"][0]["label"] == "Castles, 2 bookmarks"


# The bookmark list dialog ----------------------------------------------------------------------------

def test_the_list_dialog_opens_from_the_manager_for_the_chosen_list(s):
    d = s.run("bookmark.list_open", index=1).dialog
    assert d["kind"] == "bookmark_list" and d["title"] == "Bookmarks in Holidays" and d["list"] == 1
    assert [i["label"] for i in d["lists"]["items"]] == ["Rome"]
    assert [t["name"] for t in d["lists"]["targets"]] == ["Castles", "Empty"]
    assert [d["words"][k] for k in ("up", "down", "copy", "move", "delete", "close")] == \
        ["Move up", "Move down", "Copy to list", "Move to list", "Delete", "Close"]


def test_the_list_dialog_from_the_map_menu_is_the_list_used_last(s):
    s.bookmarks.use(1)
    assert s.run("bookmark.list_open").dialog["list"] == 1


def test_an_empty_list_says_so_and_the_only_list_has_no_other_list_to_go_to(s):
    d = s.run("bookmark.list_open", index=2).dialog
    assert d["lists"]["items"] == [] and d["lists"]["empty"] == "This list has no bookmarks."
    for index in (2, 1):
        s.run("bookmark.manager_delete", index=index)
        s.run("bookmark.manager_delete_confirm")
    assert s.run("bookmark.list_open", index=0).dialog["lists"]["targets"] == []


def test_move_up_and_down_in_the_list_say_nothing_and_are_unavailable_at_the_ends(s):
    items = s.run("bookmark.list_open", index=0).dialog["lists"]["items"]
    assert [(i["up"], i["down"]) for i in items] == [(False, True), (True, True), (True, False)]
    r = s.run("bookmark.list_move", list=0, index=0, by=1)
    assert names(s, 0) == ["Alpha", "Winchester", "Corfe"] and r.bookmark_list["current"] == 1 and said(r) == ""
    assert written(r) and r.panel_stale
    assert s.run("bookmark.list_move", list=0, index=2, by=1).bookmarks is None   # the last cannot go down


def test_copy_to_another_list_keeps_the_original_and_numbers_a_used_name(s):
    r = s.run("bookmark.list_copy", list=0, index=1, target=1)
    assert names(s, 0) == ["Winchester", "Alpha", "Corfe"] and names(s, 1) == ["Rome", "Alpha_1"]
    r = s.run("bookmark.list_copy", list=1, index=0, target=2)
    assert said(r) == "Copied Rome to Empty as Rome_1." and names(s, 2) == ["Rome_1"]
    assert r.bookmark_list["current"] == 0 and written(r)


def test_move_to_another_list_takes_it_out_and_the_focus_goes_to_the_next(s):
    r = s.run("bookmark.list_move_to", list=0, index=1, target=2)
    assert names(s, 0) == ["Winchester", "Corfe"] and names(s, 2) == ["Alpha"]
    assert said(r) == "Moved Alpha to Empty." and r.bookmark_list["current"] == 1
    assert [i["label"] for i in r.bookmark_list["items"]] == ["Winchester", "Corfe"]


def test_copy_or_move_to_the_same_or_no_list_does_nothing(s):
    assert s.run("bookmark.list_copy", list=0, index=0, target=0).earcons == ["blocked"]
    assert s.run("bookmark.list_move_to", list=0, index=0, target=9).earcons == ["blocked"]
    assert s.run("bookmark.list_copy", list=0, index=7, target=1).earcons == ["blocked"]
    assert names(s, 0) == ["Winchester", "Alpha", "Corfe"]


def test_delete_a_bookmark_asks_then_says_deleted_and_the_focus_goes_to_the_next(s):
    q = s.run("bookmark.list_delete", list=0, index=1).dialog
    assert q["text"] == "Delete the bookmark Alpha from Castles?" and q["cancel"] == "Cancel"
    assert q["submit"] == "bookmark.list_delete_confirm" and names(s, 0) == ["Winchester", "Alpha", "Corfe"]
    r = s.run("bookmark.list_delete_confirm")
    assert said(r) == "Deleted Alpha." and names(s, 0) == ["Winchester", "Corfe"]
    assert r.bookmark_list["current"] == 1 and written(r)


def test_deleting_the_last_bookmark_leaves_an_empty_list_dialog(s):
    s.run("bookmark.list_delete", list=1, index=0)
    r = s.run("bookmark.list_delete_confirm")
    assert r.bookmark_list["items"] == [] and r.bookmark_list["empty"] == "This list has no bookmarks."


def test_a_current_bookmark_that_is_deleted_here_is_no_longer_current(s):
    s.panel(open={"bookmarks"})
    s.run("panel.go", item="bookmark:0:1", group="bookmarks")
    assert s.current_bookmark is not None
    s.run("bookmark.list_delete", list=0, index=1)
    s.run("bookmark.list_delete_confirm")
    assert s.current_bookmark is None
