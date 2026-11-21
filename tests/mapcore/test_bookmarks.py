"""The bookmarks file (P4-T8a; USR-1, USR-3, USR-5, DP219, architecture 6.11).

All the bookmark lists in one GeoJSON file of TobyMap's own. The core holds them and makes the
file's text; the shells only read and write it. Nothing here touches a file.
"""
import json

import pytest

from mapcore import bookmarks as bm
from mapcore.describe import say
from mapcore.session import MapSession, Response


def some():
    """Two lists: Bookmarks with Rome and Paris, and Castles with Bodiam."""
    b = bm.Bookmarks()
    b.add(0, "Rome", 41.9, 12.5, feature="Rome", note="Visited 2019")
    b.add(0, "Paris", 48.85, 2.35, feature="Paris")
    castles = b.new_list("Castles")
    b.add(castles, "Bodiam", 51.0023, 0.5436, feature="Bodiam Castle")
    return b


def names(b, li):
    return [m.name for m in b.lists[li].bookmarks]


# At first ---------------------------------------------------------------------------------------

def test_at_first_there_is_one_list_called_bookmarks_and_it_is_used_last():
    b = bm.Bookmarks()
    assert [l.name for l in b.lists] == ["Bookmarks"]
    assert b.lists[0].on and b.lists[0].min_zoom_m == 0.0 and b.lists[0].max_zoom_m is None
    assert b.last_used == 0


# The name numbering rule (USR-1, DP211) ---------------------------------------------------------

def test_a_used_name_is_numbered_rome_rome_1_rome_2():
    b = bm.Bookmarks()
    assert b.unique_name("Rome") == "Rome"
    b.add(0, b.unique_name("Rome"), 41.9, 12.5)
    assert b.unique_name("Rome") == "Rome_1"
    b.add(0, b.unique_name("Rome"), 41.9, 12.5)
    assert b.unique_name("Rome") == "Rome_2"


def test_the_numbering_looks_in_every_list():
    """Within all lists: a bookmark's name is said with its list only in the Bookmarks group, so
    the same name in two lists would sound the same everywhere else, in Details and on the map."""
    b = some()
    assert b.unique_name("Bodiam") == "Bodiam_1"   # Bodiam is in Castles, not in Bookmarks


def test_the_first_free_number_is_used():
    b = bm.Bookmarks()
    for name in ("Rome", "Rome_2"):
        b.add(0, name, 0, 0)
    assert b.unique_name("Rome") == "Rome_1"


def test_two_bookmarks_may_have_the_same_name_and_place():
    b = bm.Bookmarks()
    b.add(0, "Rome", 41.9, 12.5)
    b.add(0, "Rome", 41.9, 12.5)
    assert names(b, 0) == ["Rome", "Rome"]


# Bookmarks: add, rename, note, delete, order ----------------------------------------------------

def test_add_goes_to_the_end_of_its_list_and_makes_it_the_list_used_last():
    b = some()
    assert names(b, 0) == ["Rome", "Paris"] and names(b, 1) == ["Bodiam"]
    assert b.last_used == 1
    b.add(0, "Oslo", 59.9, 10.75)
    assert names(b, 0)[-1] == "Oslo" and b.last_used == 0


def test_a_point_off_the_globe_or_an_empty_name_is_refused():
    b = bm.Bookmarks()
    with pytest.raises(ValueError):
        b.add(0, "North of north", 91, 0)
    with pytest.raises(ValueError):
        b.add(0, "  ", 0, 0)
    assert not b.lists[0].bookmarks


def test_a_longitude_beyond_180_is_brought_round():
    b = bm.Bookmarks()
    b.add(0, "Fiji", -17.8, 181.0)
    assert b.lists[0].bookmarks[0].lon == pytest.approx(-179.0)


def test_rename_note_and_delete():
    b = some()
    b.rename(0, 1, "Paris in spring")
    b.set_note(0, 1, "The Louvre")
    assert b.lists[0].bookmarks[1].name == "Paris in spring" and b.lists[0].bookmarks[1].note == "The Louvre"
    gone = b.delete(0, 0)
    assert gone.name == "Rome" and names(b, 0) == ["Paris in spring"]


def test_move_up_and_down_and_not_past_the_ends():
    b = some()
    b.add(0, "Oslo", 59.9, 10.75)
    assert b.move(0, 2, -1) == 1 and names(b, 0) == ["Rome", "Oslo", "Paris"]
    assert b.move(0, 0, -1) == 0 and names(b, 0) == ["Rome", "Oslo", "Paris"]
    assert b.move(0, 0, +1) == 1 and names(b, 0) == ["Oslo", "Rome", "Paris"]
    assert b.move(0, 2, +1) == 2 and names(b, 0) == ["Oslo", "Rome", "Paris"]


def test_copy_to_another_list_keeps_the_original():
    b = some()
    at = b.copy_to(0, 0, 1)
    assert names(b, 0) == ["Rome", "Paris"] and names(b, 1) == ["Bodiam", "Rome"] and at == 1
    copy = b.lists[1].bookmarks[1]
    assert (copy.lat, copy.lon, copy.feature, copy.note) == (41.9, 12.5, "Rome", "Visited 2019")
    b.rename(1, 1, "Roma")
    assert b.lists[0].bookmarks[0].name == "Rome"   # a copy, not the same bookmark


def test_move_to_another_list_takes_it_out_of_the_first():
    b = some()
    at = b.move_to(0, 1, 1)
    assert names(b, 0) == ["Rome"] and names(b, 1) == ["Bodiam", "Paris"] and at == 1


# Lists ------------------------------------------------------------------------------------------

def test_new_list_goes_last_and_a_used_name_is_refused():
    b = some()
    assert b.new_list("Cafes in London") == 2
    with pytest.raises(ValueError):
        b.new_list("castles")   # names are compared as a screen reader hears them, without case
    with pytest.raises(ValueError):
        b.new_list("   ")
    assert [l.name for l in b.lists] == ["Bookmarks", "Castles", "Cafes in London"]


def test_a_free_list_name_for_a_file_opened_is_numbered_with_a_space():
    """USR-5, DP217: the list opened is called "My favourite castles 2"."""
    b = some()
    assert b.free_list_name("Castles") == "Castles 2"
    b.new_list("Castles 2")
    assert b.free_list_name("Castles") == "Castles 3"
    assert b.free_list_name("Walks") == "Walks"


def test_rename_list_keeps_it_the_list_used_last_and_refuses_a_used_name():
    b = some()
    b.rename_list(1, "My favourite castles")
    assert b.lists[1].name == "My favourite castles" and b.last_used == 1
    b.rename_list(1, "My Favourite Castles")   # its own name, in other capitals, is allowed
    with pytest.raises(ValueError):
        b.rename_list(1, "Bookmarks")


def test_move_lists_up_and_down_and_the_list_used_last_follows():
    b = some()
    b.new_list("Walks")
    assert b.last_used == 1   # Castles; a new list is not used until a bookmark goes in
    assert b.move_list(1, -1) == 0
    assert [l.name for l in b.lists] == ["Castles", "Bookmarks", "Walks"] and b.last_used == 0
    assert b.move_list(2, +1) == 2


def test_delete_list_takes_its_bookmarks_and_the_last_list_left_is_never_gone():
    b = some()
    gone = b.delete_list(1)
    assert gone.name == "Castles" and [l.name for l in b.lists] == ["Bookmarks"] and b.last_used == 0
    b.delete_list(0)
    assert [l.name for l in b.lists] == ["Bookmarks"] and not b.lists[0].bookmarks


def test_on_or_off_and_the_zoom_range_of_each_list():
    b = some()
    b.set_on(1, False)
    b.set_zoom(1, 100.0, 25000.0)
    assert not b.lists[1].on and (b.lists[1].min_zoom_m, b.lists[1].max_zoom_m) == (100.0, 25000.0)
    assert b.lists[0].on and b.lists[0].max_zoom_m is None
    with pytest.raises(ValueError):
        b.set_zoom(1, 5000.0, 100.0)
    assert (b.lists[1].min_zoom_m, b.lists[1].max_zoom_m) == (100.0, 25000.0)


def test_use_sets_the_list_used_last():
    b = some()
    b.use(0)
    assert b.last_used == 0


# The file: GeoJSON (USR-5) ----------------------------------------------------------------------

def test_the_file_is_a_feature_collection_of_points_qgis_can_open():
    data = json.loads(some().to_text())
    assert data["type"] == "FeatureCollection"
    first = data["features"][0]
    assert first == {"type": "Feature", "geometry": {"type": "Point", "coordinates": [12.5, 41.9]},
                     "properties": {"name": "Rome", "list": "Bookmarks", "feature": "Rome", "note": "Visited 2019"}}
    assert [f["properties"]["name"] for f in data["features"]] == ["Rome", "Paris", "Bodiam"]
    assert data["tobymap"] == {
        "format": "TobyMap bookmarks", "version": 1, "last_used": "Castles",
        "lists": [{"name": "Bookmarks", "on": True, "min_zoom_m": 0.0, "max_zoom_m": None},
                  {"name": "Castles", "on": True, "min_zoom_m": 0.0, "max_zoom_m": None}]}


def test_the_round_trip_is_identical():
    b = some()
    b.set_on(1, False)
    b.set_zoom(1, 250.0, 50000.0)
    b.add(0, "Café du Monde, New Orleans", 29.9575, -90.0619, note="Beignets")
    text = b.to_text()
    again = bm.Bookmarks.from_text(text)
    assert again.to_text() == text
    assert again == b


def test_an_empty_list_keeps_its_place_in_the_order():
    b = some()
    b.new_list("Empty")
    b.move_list(2, -1)
    again = bm.Bookmarks.from_text(b.to_text())
    assert [l.name for l in again.lists] == ["Bookmarks", "Empty", "Castles"]


@pytest.mark.parametrize("text,reason", [
    ("this is not JSON", "not_json"),
    ('{"settings": {"values": {}}}', "not_geojson"),
    ('{"type": "FeatureCollection", "features": []}', "not_bookmarks"),
    ('[1, 2, 3]', "not_geojson"),
    ('{"type": "FeatureCollection", "features": [], "tobymap": {"format": "TobyMap bookmarks", "version": 99, '
     '"last_used": "Bookmarks", "lists": [{"name": "Bookmarks", "on": true, "min_zoom_m": 0, "max_zoom_m": null}]}}',
     "newer"),
])
def test_a_file_that_is_not_a_bookmark_file_is_refused_with_its_reason(text, reason):
    with pytest.raises(bm.BookmarkFileError) as error:
        bm.Bookmarks.from_text(text)
    assert error.value.reason == reason
    assert error.value.text == say(f"bookmarks.file.{reason}")


def test_a_plain_json_file_is_refused_and_nothing_changes():
    b = some()
    before = b.to_text()
    with pytest.raises(bm.BookmarkFileError):
        b.replace_from_text('{"settings": {"values": {"units": "imperial"}}, "state": {}}')
    assert b.to_text() == before


def damaged_versions():
    good = json.loads(some().to_text())
    out = []
    for change in (
        lambda d: d["features"][0]["geometry"].update(coordinates=[12.5]),           # no latitude
        lambda d: d["features"][0]["geometry"].update(type="LineString"),             # not a point
        lambda d: d["features"][0]["geometry"].update(coordinates=[12.5, 95.0]),     # off the globe
        lambda d: d["features"][1]["properties"].update(list="No such list"),
        lambda d: d["features"][1]["properties"].update(name=7),
        lambda d: d["features"][1].pop("properties"),
        lambda d: d["tobymap"].update(lists=[]),
        lambda d: d["tobymap"]["lists"].append(dict(d["tobymap"]["lists"][0])),      # a list twice
        lambda d: d["tobymap"]["lists"][1].update(min_zoom_m=500.0, max_zoom_m=100.0),
        lambda d: d["tobymap"]["lists"][1].update(on="yes"),
    ):
        d = json.loads(json.dumps(good))
        change(d)
        out.append(json.dumps(d))
    return out


@pytest.mark.parametrize("text", damaged_versions())
def test_a_damaged_bookmark_file_is_refused(text):
    with pytest.raises(bm.BookmarkFileError) as error:
        bm.Bookmarks.from_text(text)
    assert error.value.reason == "damaged"


def test_a_missing_note_or_feature_is_read_as_none_given():
    data = json.loads(some().to_text())
    del data["features"][0]["properties"]["note"]
    data["features"][0]["properties"]["feature"] = None
    b = bm.Bookmarks.from_text(json.dumps(data))
    assert (b.lists[0].bookmarks[0].note, b.lists[0].bookmarks[0].feature) == ("", "")


def test_a_last_used_list_that_is_gone_becomes_the_first():
    data = json.loads(some().to_text())
    data["tobymap"]["last_used"] = "Gone"
    assert bm.Bookmarks.from_text(json.dumps(data)).last_used == 0


# The session: loaded at start, the file's text handed back when bookmarks change --------------

def test_the_session_starts_with_the_bookmarks_the_shell_gives(test_pack):
    s = MapSession(packs=[test_pack], bookmarks=some().to_text())
    assert names(s.bookmarks, 1) == ["Bodiam"]
    r = s.start()
    assert r.bookmarks is None and not r.bookmarks_damaged


def test_no_file_starts_one_bookmarks_list_and_nothing_is_written(test_pack):
    for given in (None, "", "  \n"):
        s = MapSession(packs=[test_pack], bookmarks=given)
        assert [l.name for l in s.bookmarks.lists] == ["Bookmarks"]
        r = s.start()
        assert r.bookmarks is None and not r.bookmarks_damaged


def test_a_damaged_file_is_set_aside_said_and_a_new_list_started(test_pack):
    s = MapSession(packs=[test_pack], bookmarks='{"type": "FeatureCollection", "features": [')
    assert [l.name for l in s.bookmarks.lists] == ["Bookmarks"] and not s.bookmarks.lists[0].bookmarks
    r = s.start()
    assert r.bookmarks_damaged   # the shell renames the file aside
    assert r.bookmarks is None    # and writes nothing until a bookmark is made
    message = say("bookmarks.damaged")
    assert message in [a["text"] for a in r.announcements]
    assert s.start_label().endswith(message)   # heard at start, with the place (P2-T17d)


def test_a_change_hands_the_shell_the_new_text(test_pack):
    s = MapSession(packs=[test_pack])
    s.bookmarks.add(0, "Here", 51.2, 1.2)
    r = s.bookmarks_changed(Response())
    assert r.bookmarks == s.bookmarks.to_text()
    assert bm.Bookmarks.from_text(r.bookmarks) == s.bookmarks
    assert "bookmarks" in r.to_dict() and "bookmarks_damaged" in r.to_dict()


def test_reset_all_settings_leaves_the_bookmarks(test_pack):
    """DP209: Reset all settings does not touch the bookmarks, and writes nothing to their file."""
    s = MapSession(packs=[test_pack], bookmarks=some().to_text())
    before = s.bookmarks.to_text()
    r = s.run("settings.reset_confirm")
    assert r.action == "reset"
    assert s.bookmarks.to_text() == before
    assert r.bookmarks is None and not r.bookmarks_damaged
