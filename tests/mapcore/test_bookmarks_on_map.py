"""Bookmarks on the map (P4-T8f; USR-3, SCP-6, VIS-2, VIS-3, DP219 point 5): the Bookmarks layer, a mark of a
fixed size on screen with its name beside it, each bookmark list on or off with its own zoom range, and the
layer switched off hiding them from the map, the Bookmarks group and every announcement."""
import pytest

from mapcore.render import themes
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
W, H = 800, 600


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


def stocked(s):
    """Castles (Winchester, a little east of where you are) and Holidays (Rome, far off the map)."""
    b = s.bookmarks
    b.lists[0].name = "Castles"
    b.add(0, "Wolvesey", 51.06, -1.21)
    b.new_list("Holidays")
    b.add(1, "Rome", 41.9, 12.5)
    s.bookmarks_changed(s.start())


def marks(s, **settings):
    for field, value in settings.items():
        s.run("settings.set", field=field, value=value)
    return s.scene(W, H)["bookmarks"]


def zoom_to(s, metres):
    from mapcore.world.state import nearest_index

    s.world.zoom_index = nearest_index(s.world.zoom_list, metres)
    assert s.world.zoom_m == metres


def group(s):
    return next(g for g in s.panel(open={"bookmarks"}) if g["id"] == "bookmarks")


def switch_layer(s, on: bool):
    s.run("layers.set", layer="bookmarks", field="on", value=on)


# The layer --------------------------------------------------------------------------------------

def test_the_layers_dialog_lists_the_bookmarks_layer_on_in_its_own_group(s):
    groups = s.layer_list()["groups"]
    last = groups[-1]
    assert last["name"] == "Bookmarks"
    assert [(l["id"], l["name"], l["on"], l["geometry"]) for l in last["layers"]] == [
        ("bookmarks", "Bookmarks", True, "point")]
    r = s.run("layers.open")
    assert r.dialog["text"].endswith("Bookmarks\nBookmarks, on")


def test_the_bookmarks_layer_is_not_a_layer_to_search_in(s):
    r = s.run("query.open")
    assert "bookmarks" not in [l["id"] for l in r.dialog["layers"]]


# The mark ---------------------------------------------------------------------------------------

def test_a_bookmark_is_drawn_at_its_point_with_its_name_beside_it(s):
    stocked(s)
    got = marks(s)
    assert [m["text"] for m in got] == ["Wolvesey"]   # Rome is far off the map
    m = got[0]
    assert m["x"] > W / 2 + 10 and abs(m["y"] - H / 2) < 10   # east of the centre, on the same latitude
    assert m["half"] == pytest.approx(6.0)                     # about 12 pixels across at 100%
    assert m["text_x"] > m["x"] + m["half"] and m["text_y"] == pytest.approx(m["y"])


def test_the_mark_is_the_same_size_at_every_zoom_and_follows_label_size(s):
    stocked(s)
    wide = marks(s)[0]["half"]
    zoom_to(s, 25000)
    s.world.lat, s.world.lon = 51.06, -1.25
    assert marks(s)[0]["half"] == wide
    big = marks(s, label_size=150)[0]
    assert big["half"] == pytest.approx(wide * 1.5) and big["text_size"] > 12


def test_the_scene_carries_the_marks_style_from_the_theme(s):
    stocked(s)
    frame = s.scene(W, H)
    t = themes.theme("standard")
    assert frame["bookmark_style"]["fill"] == t["bookmark"] and frame["bookmark_style"]["stroke"] == t["bookmark_outline"]


def test_names_are_left_out_when_names_on_the_map_are_off(s):
    stocked(s)
    assert marks(s, map_names=False)[0]["text"] == ""


def test_a_selected_bookmark_is_drawn_highlighted(s):
    stocked(s)
    item = group(s)["items"][0]["children"][0]
    s.selected = item["id"]
    assert marks(s)[0]["selected"] is True


# On or off, and zoom ranges -----------------------------------------------------------------------

def test_a_bookmark_list_switched_off_is_gone_from_the_map_and_the_group(s):
    stocked(s)
    s.bookmarks.set_on(0, False)
    s.bookmarks_changed(s.start())
    assert marks(s) == []
    assert [i["label"] for i in group(s)["items"]] == ["Holidays, 1 item"]


def test_the_layer_switched_off_hides_every_bookmark_from_the_map_and_the_group(s):
    stocked(s)
    switch_layer(s, False)
    assert marks(s) == []
    g = group(s)
    assert g["items"] == []
    assert g["empty"] == "The Bookmarks layer is switched off. Switch it on in Layers, in the Map menu."
    switch_layer(s, True)
    assert [m["text"] for m in marks(s)] == ["Wolvesey"]
    assert len(group(s)["items"]) == 2


def test_a_list_outside_its_zoom_range_is_gone_from_the_map_and_the_group(s):
    stocked(s)
    s.bookmarks.set_zoom(0, 0.0, 50000)   # Castles only closer than 50 km; the map is at 100 km
    s.bookmarks_changed(s.start())
    assert marks(s) == []
    assert [i["label"] for i in group(s)["items"]] == ["Holidays, 1 item"]
    zoom_to(s, 25000)
    assert [m["text"] for m in marks(s)] == ["Wolvesey"]
    assert [i["label"] for i in group(s)["items"]] == ["Castles, 1 item", "Holidays, 1 item"]


def test_with_every_list_outside_its_range_the_group_says_so(s):
    stocked(s)
    for li in (0, 1):
        s.bookmarks.set_zoom(li, 0.0, 50000)
    s.bookmarks_changed(s.start())
    g = group(s)
    assert g["items"] == [] and g["empty"] == "No bookmarks at this zoom level."


def test_the_layers_own_zoom_range_applies_too(s):
    stocked(s)
    s.run("layers.set", layer="bookmarks", field="max_zoom_m", value=50000)
    assert marks(s) == []
    assert group(s)["empty"] == "No bookmarks at this zoom level."


def test_a_change_in_the_bookmark_manager_redraws_the_map(s):
    stocked(s)
    r = s.run("bookmark.manager_on", index=0, on=False)
    assert r.redraw


# Announcements ----------------------------------------------------------------------------------

def test_with_the_layer_off_a_bookmark_is_no_longer_the_current_feature(s):
    stocked(s)
    rome = group(s)["items"][1]["children"][0]
    s.run("panel.go", item=rome["id"], group="bookmarks")
    assert s.current_bookmark is not None
    switch_layer(s, False)
    assert s.current_bookmark is None


def test_with_the_layer_off_a_selected_bookmark_is_no_longer_selected(s):
    stocked(s)
    s.selected = group(s)["items"][0]["children"][0]["id"]
    switch_layer(s, False)
    assert s.selected is None


# Themes ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", themes.names())
def test_the_mark_stands_out_on_land_and_sea_in_every_theme(name):
    """3 to 1 against every fill in every theme (WCAG non-text contrast), 7 to 1 in the high contrast ones (VIS-2),
    and its outline against the mark itself."""
    t = themes.theme(name)
    fills = [c for c in t["land"]] + [t["ocean"], t["light_water"], t["plain_land"], *t["physical"].values()]
    least = 7.0 if t["high_contrast"] else 3.0
    assert min(themes.contrast(t["bookmark"], f) for f in fills) >= least
    assert themes.contrast(t["bookmark_outline"], t["bookmark"]) >= least
    assert t["bookmark"] != t["marker"] and t["bookmark"] != t["current_outline"]
