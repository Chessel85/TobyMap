"""Saving and opening bookmark files, GeoJSON and GPX (P4-T9b, P4-T9c; USR-5, DP209, DP217, DP219).

The core makes a file's text from one list or all of them, and reads a file's text into new lists, always added after
the ones you have, under a free name, never merged or replaced. The shells only show the Save and Open boxes, and write
or read the text. Nothing here touches a file.
"""
import json
import xml.etree.ElementTree as ET

import pytest

from mapcore import bookmark_files as bf
from mapcore import bookmarks as bm
from mapcore.commands import registry
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
GPX = "{http://www.topografix.com/GPX/1/1}"


def some():
    """Castles, with three bookmarks, a note, a feature and a zoom range; Holidays with Rome; Empty, switched off."""
    b = bm.Bookmarks(lists=[bm.BookmarkList("Castles")])
    b.add(0, "Winchester", 51.0632, -1.3080, feature="Hampshire", note="The Great Hall & a round table <1290>")
    b.add(0, "Corfe", 50.6395, -2.0566)
    b.add(0, "Bodiam", 51.0023, 0.5436, feature="Bodiam Castle")
    b.set_zoom(0, 1000.0, 500000.0)
    b.add(b.new_list("Holidays"), "Rome", 41.9, 12.5, note="Visited 2019")
    b.set_on(b.new_list("Empty"), False)
    return b


def points(lst):
    return [(m.name, m.lat, m.lon, m.note) for m in lst.bookmarks]


# GeoJSON (P4-T9b) -----------------------------------------------------------------------------------

def test_one_list_saved_as_geojson_and_opened_again_is_identical():
    b = some()
    opened = bf.read(bf.geojson_text(b, 0))
    assert opened.kind == "geojson" and opened.left_out == 0
    assert opened.lists == [b.lists[0]]   # names, points, notes, features, order, on and zoom range


def test_all_lists_saved_as_geojson_and_opened_again_are_identical():
    b = some()
    assert bf.read(bf.geojson_text(b)).lists == b.lists


def test_all_lists_saved_is_the_same_as_the_bookmarks_file_so_it_opens_as_one():
    b = some()
    assert bf.geojson_text(b) == b.to_text()
    assert bm.Bookmarks.from_text(bf.geojson_text(b, 1)).lists == [b.lists[1]]


def test_the_saved_geojson_is_valid_for_qgis():
    """A FeatureCollection of Points, coordinates longitude then latitude, each named in properties.name."""
    data = json.loads(bf.geojson_text(some(), 0))
    assert data["type"] == "FeatureCollection"
    assert [f["type"] for f in data["features"]] == ["Feature"] * 3
    assert {f["geometry"]["type"] for f in data["features"]} == {"Point"}
    first = data["features"][0]
    assert first["geometry"]["coordinates"] == [-1.3080, 51.0632]
    assert first["properties"]["name"] == "Winchester" and first["properties"]["note"].startswith("The Great Hall")


def test_a_geojson_of_points_from_another_program_opens_into_one_list_named_from_the_file():
    data = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-0.1276, 51.5072]}, "properties": {"Name": "London"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [2.35, 48.85]}, "properties": {}}]}
    opened = bf.read(json.dumps(data), "Capitals.geojson")
    assert [l.name for l in opened.lists] == ["Capitals"]
    assert points(opened.lists[0]) == [("London", 51.5072, -0.1276, ""), ("Bookmark 2", 48.85, 2.35, "")]


@pytest.mark.parametrize("text", [
    '{"settings": {"units": "metric"}}',                               # a plain JSON file, such as a settings file
    json.dumps({"type": "FeatureCollection", "features": [            # a GeoJSON file of polygons
        {"type": "Feature", "properties": {"name": "A square"},
         "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}]}),
    json.dumps({"type": "FeatureCollection", "features": []}),         # an empty GeoJSON file, not one of TobyMap's
    '<?xml version="1.0"?><gpx><wpt lat="1" lon="2"><name>Broken',     # broken XML
    '<?xml version="1.0"?><html><body>Not GPX</body></html>',          # XML that is not GPX
    "Just some words.",
    "",                                                                # a file the shell could not read
])
def test_a_file_that_is_not_a_bookmark_file_is_refused(text):
    with pytest.raises(bm.BookmarkFileError) as refused:
        bf.read(text, "Something.json")
    assert refused.value.text.endswith("Nothing is changed.")


def test_the_content_decides_the_kind_not_the_name():
    b = some()
    assert bf.read(bf.gpx_text(b, 0), "castles.json").kind == "gpx"
    assert bf.read(bf.geojson_text(b, 0), "castles.gpx").kind == "geojson"


# GPX (P4-T9c) ---------------------------------------------------------------------------------------

def test_a_list_saved_as_gpx_and_opened_again_has_the_same_names_points_and_notes_in_order():
    b = some()
    opened = bf.read(bf.gpx_text(b, 0), "anything.gpx")
    assert opened.kind == "gpx" and [l.name for l in opened.lists] == ["Castles"]
    got, want = points(opened.lists[0]), points(b.lists[0])
    assert [(n, note) for n, _a, _o, note in got] == [(n, note) for n, _a, _o, note in want]
    for (_n, lat, lon, _note), (_m, lat0, lon0, _note0) in zip(got, want):
        assert abs(lat - lat0) < 1e-7 and abs(lon - lon0) < 1e-7
    assert [m.feature for m in opened.lists[0].bookmarks] == ["Hampshire", "", "Bodiam Castle"]


def test_the_saved_gpx_is_gpx_1_1_with_one_waypoint_for_each_bookmark():
    root = ET.fromstring(bf.gpx_text(some(), 0))
    assert root.tag == f"{GPX}gpx" and root.get("version") == "1.1" and root.get("creator") == "TobyMap"
    assert root.find(f"{GPX}metadata/{GPX}name").text == "Castles"
    wpts = root.findall(f"{GPX}wpt")
    assert [w.find(f"{GPX}name").text for w in wpts] == ["Winchester", "Corfe", "Bodiam"]
    assert (wpts[0].get("lat"), wpts[0].get("lon")) == ("51.0632", "-1.308")
    assert wpts[0].find(f"{GPX}desc").text.startswith("The Great Hall") and wpts[1].find(f"{GPX}desc") is None
    # GPX 1.1 puts a waypoint's children in a fixed order: name, then desc, then extensions last.
    assert [c.tag.split("}")[1] for c in wpts[0]] == ["name", "desc", "extensions"]


def test_all_lists_saved_as_gpx_open_again_as_the_same_lists_that_have_bookmarks():
    b = some()
    opened = bf.read(bf.gpx_text(b), "TobyMap bookmarks.gpx")
    assert [l.name for l in opened.lists] == ["Castles", "Holidays"]   # a list with no bookmarks has no waypoints
    assert [m.name for m in opened.lists[1].bookmarks] == ["Rome"]


def gpx(body: str, head: str = "") -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Someone" '
            f'xmlns="http://www.topografix.com/GPX/1/1">{head}{body}</gpx>')


def test_a_gpx_from_another_program_opens_into_one_list_named_from_its_metadata():
    text = gpx('<wpt lat="57.1" lon="-3.6"><name>Cairn Gorm</name><cmt>The summit cairn</cmt></wpt>'
               '<wpt lat="56.8" lon="-5.0"></wpt>', "<metadata><name>Munros</name></metadata>")
    opened = bf.read(text, "walks.gpx")
    assert [l.name for l in opened.lists] == ["Munros"]
    assert points(opened.lists[0]) == [("Cairn Gorm", 57.1, -3.6, "The summit cairn"), ("Waypoint 2", 56.8, -5.0, "")]


def test_a_gpx_with_no_name_is_named_from_the_file_or_else_opened_waypoints():
    text = gpx('<wpt lat="1" lon="2"><name>A</name></wpt>')
    assert bf.read(text, "Walks in Wales.gpx").lists[0].name == "Walks in Wales"
    assert bf.read(text).lists[0].name == "Opened waypoints"


def test_a_gpx_with_routes_and_tracks_says_how_many_were_left_out():
    text = gpx('<wpt lat="1" lon="2"><name>A</name></wpt>'
               '<rte><rtept lat="1" lon="2"/></rte><trk><trkseg><trkpt lat="1" lon="2"/></trkseg></trk>'
               '<trk><trkseg/></trk>')
    assert bf.read(text).left_out == 3


def test_a_gpx_with_only_tracks_is_refused():
    with pytest.raises(bm.BookmarkFileError) as refused:
        bf.read(gpx('<trk><trkseg><trkpt lat="1" lon="2"/></trkseg></trk>'))
    assert refused.value.reason == "no_waypoints"


def test_a_gpx_waypoint_off_the_globe_is_damaged():
    with pytest.raises(bm.BookmarkFileError) as refused:
        bf.read(gpx('<wpt lat="91" lon="2"><name>A</name></wpt>'))
    assert refused.value.reason == "damaged"


def test_a_gpx_1_0_file_opens_too():
    text = ('<gpx version="1.0" xmlns="http://www.topografix.com/GPX/1/0"><name>Old</name>'
            '<wpt lat="1.5" lon="2.5"><name>A</name><desc>Note</desc></wpt></gpx>')
    opened = bf.read(text)
    assert opened.lists[0].name == "Old" and points(opened.lists[0]) == [("A", 1.5, 2.5, "Note")]


# File names -----------------------------------------------------------------------------------------

def test_the_suggested_file_name_is_the_list_name_without_characters_windows_refuses():
    b = some()
    b.rename_list(1, 'Trips: "2026/27"?')
    assert bf.file_name(b, 0, "geojson") == "Castles.geojson"
    assert bf.file_name(b, 1, "gpx") == "Trips 2026 27.gpx"
    assert bf.file_name(b, None, "gpx") == "TobyMap bookmarks.gpx"


# Adding opened lists to yours -----------------------------------------------------------------------

def test_opened_lists_go_after_yours_with_a_free_name_and_nothing_is_merged():
    b = some()
    used = b.last_used
    opened = bf.read(bf.geojson_text(b))
    places = b.add_lists(opened.lists)
    assert places == [3, 4, 5]
    assert [l.name for l in b.lists] == ["Castles", "Holidays", "Empty", "Castles 2", "Holidays 2", "Empty 2"]
    assert points(b.lists[3]) == points(b.lists[0]) and b.last_used == used


# In the bookmark manager ----------------------------------------------------------------------------

@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    s.bookmarks.lists, s.bookmarks.last_used = some().lists, 0
    yield s
    s.store.close()


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def test_the_new_commands_are_in_the_registry():
    for name in ("bookmark.manager_save_chosen", "bookmark.manager_file_opened"):
        c = registry.by_name(name)
        assert c.pointer and c.region == "global"


def test_save_to_a_file_offers_the_chosen_list_or_all_lists_as_geojson_or_gpx(s):
    d = s.run("bookmark.manager_save_file", index=1).dialog
    assert d["kind"] == "choose" and d["title"] == "Save to a file" and d["go"] == "bookmark.manager_save_chosen"
    assert d["lines"] == ["Holidays, as GeoJSON, for QGIS and other map programs", "Holidays, as GPX waypoints",
                          "All lists, as GeoJSON, for QGIS and other map programs", "All lists, as GPX waypoints"]
    assert d["cancel"] == "Cancel"


def test_a_choice_asks_the_shell_to_save_the_text_under_a_suggested_name(s):
    s.run("bookmark.manager_save_file", index=1)
    r = s.run("bookmark.manager_save_chosen", index=0)
    f = r.save_file
    assert f["name"] == "Holidays.geojson" and f["title"] == "Save Holidays as GeoJSON"
    assert f["filter"] == "GeoJSON (*.geojson)" and f["mime"] == "application/geo+json"
    assert bf.read(f["text"]).lists == [s.bookmarks.lists[1]]
    assert f["saved"] == "Saved Holidays as GeoJSON."
    assert f["failed"] == "The file could not be saved."
    assert r.bookmarks is None   # saving changes nothing of yours

    s.run("bookmark.manager_save_file", index=0)
    f = s.run("bookmark.manager_save_chosen", index=3).save_file
    assert f["name"] == "TobyMap bookmarks.gpx" and f["filter"] == "GPX (*.gpx)" and f["mime"] == "application/gpx+xml"
    assert f["saved"] == "Saved all lists as GPX waypoints."
    assert [l.name for l in bf.read(f["text"]).lists] == ["Castles", "Holidays"]


def test_a_choice_without_a_save_to_a_file_first_does_nothing(s):
    r = s.run("bookmark.manager_save_chosen", index=0)
    assert r.save_file is None and r.earcons == ["blocked"]


def test_open_a_file_asks_the_shell_for_a_file(s):
    f = s.run("bookmark.manager_open_file").open_file
    assert f["title"] == "Open a bookmark file"
    assert f["filter"] == "Bookmark files (*.geojson *.json *.gpx)"
    assert f["accept"] == ".geojson,.json,.gpx"
    assert f["submit"] == "bookmark.manager_file_opened"


def test_a_list_opened_whose_name_is_used_is_kept_beside_it_as_castles_2(s):
    text = bf.geojson_text(s.bookmarks, 0)
    r = s.run("bookmark.manager_file_opened", text=text, file="Castles.geojson")
    assert said(r) == "Opened 3 bookmarks into Castles 2."
    assert [l.name for l in s.bookmarks.lists] == ["Castles", "Holidays", "Empty", "Castles 2"]
    assert r.bookmark_manager["current"] == 3 and r.bookmarks is not None   # written, and the focus on it
    assert points(s.bookmarks.lists[3]) == points(s.bookmarks.lists[0])


def test_opening_one_bookmark_and_an_empty_list_say_so(s):
    b = bm.Bookmarks(lists=[bm.BookmarkList("Rome")])
    b.add(0, "Colosseum", 41.89, 12.49)
    assert said(s.run("bookmark.manager_file_opened", text=bf.geojson_text(b, 0))) == "Opened 1 bookmark into Rome."
    b = bm.Bookmarks(lists=[bm.BookmarkList("Nothing yet")])
    assert said(s.run("bookmark.manager_file_opened", text=bf.geojson_text(b, 0))) == \
        "Opened the list Nothing yet, with no bookmarks."


def test_opening_all_lists_says_how_many_lists_and_bookmarks_and_their_names(s):
    r = s.run("bookmark.manager_file_opened", text=bf.geojson_text(s.bookmarks), file="all.geojson")
    assert said(r) == "Opened 3 lists with 4 bookmarks: Castles 2, Holidays 2, Empty 2."


def test_opening_a_gpx_with_tracks_says_how_many_were_left_out(s):
    text = gpx('<wpt lat="1" lon="2"><name>A</name></wpt><trk><trkseg/></trk><rte/>',
               "<metadata><name>Walk</name></metadata>")
    r = s.run("bookmark.manager_file_opened", text=text, file="walk.gpx")
    assert said(r) == "Opened 1 bookmark into Walk. 2 routes and tracks were left out, as TobyMap opens only waypoints."
    text = gpx('<wpt lat="1" lon="2"><name>A</name></wpt><trk/>', "<metadata><name>Walk</name></metadata>")
    assert said(s.run("bookmark.manager_file_opened", text=text)).endswith(
        "1 route or track was left out, as TobyMap opens only waypoints.")


@pytest.mark.parametrize("text, words", [
    ('{"settings": {}}', "This is not a bookmark file: it is not a GeoJSON feature collection. Nothing is changed."),
    ('<gpx><wpt lat="1"', "This is not a bookmark file: it is neither GeoJSON nor GPX. Nothing is changed."),
    (json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {},
                 "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}}]}),
     "This GeoJSON file is not a TobyMap bookmark file. Nothing is changed."),
])
def test_a_file_that_is_not_a_bookmark_file_says_so_and_nothing_changes(s, text, words):
    before = [(l.name, points(l)) for l in s.bookmarks.lists]
    r = s.run("bookmark.manager_file_opened", text=text, file="x.json")
    assert said(r) == words
    assert r.bookmarks is None and r.bookmark_manager is None
    assert [(l.name, points(l)) for l in s.bookmarks.lists] == before
