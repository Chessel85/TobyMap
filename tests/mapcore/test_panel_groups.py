"""The Information panel's seven groups, the current feature, and groups filled only when opened
(P3-T4a; INF-10, LOC-4, INF-2, NFR-1, DP80, DP156, DP160).

Bordering is filled here as the pattern for the other groups about the current feature: Contains
(P3-T4b), Overlapping and Crossing (P3-T4c) follow it.
"""
import pytest

from mapcore import panel as panel_table
from mapcore.commands import registry
from mapcore.session import MapSession, box_centre

SWITZERLAND = {"lat": 46.8, "lon": 8.2, "zoom_m": 100000, "step_m": 1000}
HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
LAZY = ["bordering", "contains", "overlapping", "search"]


@pytest.fixture
def swiss(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(SWITZERLAND))
    s.start()
    yield s
    s.store.close()


def group(groups, gid):
    return next(g for g in groups if g["id"] == gid)


# The group table ------------------------------------------------------------------------------

def test_the_seven_groups_in_the_pos_order():
    """INF-10, P3-T29a: Within, Nearby, Bordering, Contains, Overlapping, Passed over, Search, on Shift+1 to
    Shift+7. The Crossing group is gone."""
    assert registry.panel_groups() == ["within", "nearby", "bordering", "contains", "overlapping", "crossed",
                                       "search"]
    assert set(panel_table.GROUPS) == set(registry.panel_groups())


def test_each_groups_default_sort_and_zoom_limit():
    """UX 6.1: Within in its natural order, Nearby by distance, Bordering by bearing, the rest by name;
    Contains, Nearby, and Crossed and passed show only visible features (ANN-7, DP80)."""
    g = panel_table.GROUPS
    assert g["within"].default_sort == "natural" and g["nearby"].default_sort == "distance"
    assert g["bordering"].default_sort == "bearing"
    assert all(g[x].default_sort == "name" for x in ("contains", "overlapping", "search"))
    assert g["crossed"].default_sort == "natural"   # Passed over: along the move
    assert {x for x, v in g.items() if v.zoom_limited} == {"contains", "nearby", "crossed"}
    assert {x for x, v in g.items() if v.about_current} == {"contains", "bordering", "overlapping"}


# Filled only when opened (NFR-1) ----------------------------------------------------------------

def test_a_group_not_opened_is_not_filled_and_names_the_current_feature(swiss):
    groups = swiss.panel()
    for gid in LAZY:
        g = group(groups, gid)
        assert g["filled"] is False and g["items"] == []
    assert group(groups, "bordering")["label"] == "Bordering Switzerland"
    assert group(groups, "search")["label"] == "Search"
    assert all(group(groups, g)["filled"] for g in ("within", "nearby", "crossed"))


def test_an_open_group_is_filled_with_its_count(swiss):
    g = group(swiss.panel(open={"bordering"}), "bordering")
    assert g["filled"] and g["label"] == "Bordering Switzerland, 5 items, clockwise from north"


def test_the_open_groups_are_kept_until_the_shell_says_again(swiss):
    swiss.panel(open={"bordering"})
    assert group(swiss.panel(), "bordering")["filled"]
    assert not group(swiss.panel(open=set()), "bordering")["filled"]


def test_going_to_a_group_fills_it_though_the_shell_has_not_opened_it(swiss):
    r = swiss.press("Shift+3", "map")
    assert r.focus == {"region": "panel", "group": "bordering", "heading": True}   # on its heading (P3-T19c)
    assert group(swiss.panel(), "bordering")["filled"]


def test_a_step_never_fills_a_group_not_opened(swiss, monkeypatch):
    def refuse(*_a):
        raise AssertionError("Bordering was filled during a step")

    monkeypatch.setattr(swiss, "_group_bordering", refuse)
    swiss.run("move.north")
    swiss.release()
    swiss.panel()


def test_an_open_group_is_made_again_after_a_move_but_not_before(swiss, monkeypatch):
    calls = []
    real = swiss._group_bordering
    monkeypatch.setattr(swiss, "_group_bordering", lambda *a: calls.append(1) or real(*a))
    swiss.panel(open={"bordering"})
    swiss.panel()
    assert len(calls) == 1
    swiss.run("move.north")
    swiss.release()
    swiss.panel()
    assert len(calls) == 2


# Bordering, the pattern for the groups about the current feature (INF-2) -------------------------

def test_bordering_switzerland_lists_its_five_neighbours_by_bearing_with_their_borders(swiss):
    items = group(swiss.panel(open={"bordering"}), "bordering")["items"]
    assert sorted(i["name"] for i in items) == ["Austria", "France", "Germany", "Italy", "Liechtenstein"]
    bearings = [i["bearing_deg"] for i in items]
    assert bearings == sorted(bearings)   # clockwise from ahead, which is north here
    france = next(i for i in items if i["name"] == "France")
    # West: France's point is no longer pulled towards French Guiana, an area of its own (DP191).
    # With its distance, as every item now says (P3-T19c): "France, 210 kilometres west, shared border 573 kilometres".
    assert france["label"].startswith("France, ") and " kilometres west, shared border " in france["label"]
    assert all({"id", "label", "level", "name", "distance_m", "bearing_deg"} <= set(i) for i in items)
    assert all(i["level"] == 1 for i in items)


def test_bordering_is_not_limited_by_the_zoom(test_pack):
    """DP80: at 1 km, far less than the borders, all five are still listed."""
    s = MapSession(packs=[test_pack], saved_state=dict(SWITZERLAND, zoom_m=1000))
    s.start()
    assert len(group(s.panel(open={"bordering"}), "bordering")["items"]) == 5
    s.store.close()


def test_enter_and_space_work_on_a_bordering_item(swiss):
    items = group(swiss.panel(open={"bordering"}), "bordering")["items"]
    france = next(i for i in items if i["name"] == "France")
    assert swiss.run("panel.hear", item=france["id"], group="bordering").label.startswith("France, ")
    lat, lon = swiss._point_of(swiss.store.feature(france["id"]))   # its own point (P3-T19g)
    r = swiss.run("panel.go", item=france["id"], group="bordering")
    assert (swiss.world.lat, swiss.world.lon) == pytest.approx((lat, lon))
    assert r.focus == {"region": "panel", "group": "bordering", "item": None}


# The current feature (LOC-4) --------------------------------------------------------------------

def test_the_current_feature_is_the_smallest_area_here(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    assert s.current_feature.name == "Hampshire"
    assert group(s.panel(), "contains")["label"] == "Contains Hampshire"
    s.store.close()


def test_the_current_feature_is_the_first_area_where_am_i_says_not_the_first_by_layer_rank(test_pack):
    """P3-T28m, LOC-4: at 500 kilometres zoom in the New Forest, "where am I" says England first; the New Forest
    National Park's layer ranks above Regions, but it is said last, so it is not the current feature. As the
    British Isles at the United Kingdom in the world pack (the PO's note in explanation.md)."""
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.87, "lon": -1.6, "zoom_m": 500000, "step_m": 25000})
    s.start()
    said = s.run("where.am_i").announcements[0]["text"]
    assert said.startswith("England") and "New Forest National Park" in said
    assert s.current_feature.name == "England"
    assert group(s.panel(), "contains")["label"] == "Contains England"
    s.store.close()


def test_hierarchy_mode_can_make_another_feature_current_until_you_move(test_pack):
    """P3-T6 sets the current feature as it moves you to it; any move after makes the smallest area current."""
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    england = s.areas[1]
    s.set_current_feature(england.id)
    assert s.current_feature.id == england.id
    assert group(s.panel(open={"bordering"}), "bordering")["label"].startswith("Bordering England")
    s.run("move.north")
    s.release()
    assert s.current_feature.id == s.areas[0].id
    s.store.close()


def test_a_heading_inside_a_group_is_not_selected():
    """Contains' "Regions 13" and the like are headings: the map highlights nothing for them."""
    h = panel_table.heading("regions", "Regions, 2", [panel_table.item("a", "A", "A", 1.0, 10.0)])
    assert panel_table.is_heading(h["id"]) and h["children"][0]["level"] == 2
    assert [i["id"] for i in panel_table.walk([h])] == [h["id"], "a"]


def test_selecting_a_heading_clears_the_selection(swiss):
    swiss.run("panel.select", item="heading:regions", group="contains")
    assert swiss.selected is None


# Contains, Overlapping and Crossing (P3-T4b, P3-T4c; INF-1, INF-5, INF-6, DP70) -------------------
# The test pack has no Wales, so Contains is tried on England from Hampshire, which it holds, and on
# Hampshire, which holds the River Itchen.

@pytest.fixture
def hants(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


def test_contains_groups_what_is_visible_by_layer_under_headings(hants):
    g = group(hants.panel(open={"contains"}), "contains")
    # Brockenhurst station, wholly inside. The River Itchen and the New Forest National Park are only partly
    # inside, so not listed (P3-T29c); Longbridge Lake is too small to see at this zoom.
    assert g["label"] == "Contains Hampshire, 1 item, by name"
    assert [h["label"] for h in g["items"]] == ["Railway stations 1"]
    heading = g["items"][0]
    assert heading["label"] == "Railway stations 1" and panel_table.is_heading(heading["id"]) and heading["level"] == 1
    child = heading["children"][0]
    assert child["level"] == 2 and child["label"].startswith("Brockenhurst, ")


def test_contains_follows_the_zoom(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE, zoom_m=1000))
    s.start()
    assert group(s.panel(open={"contains"}), "contains")["items"] == []   # ANN-7: not visible, not listed
    s.store.close()


def test_contains_for_england_from_hampshire_has_hampshire(hants):
    hants.set_current_feature(hants.areas[1].id)
    names = [c["name"] for h in group(hants.panel(open={"contains"}), "contains")["items"] for c in h["children"]]
    assert "Hampshire" in names


def test_enter_works_on_an_item_under_a_heading(hants):
    child = group(hants.panel(open={"contains"}), "contains")["items"][0]["children"][0]
    assert hants.run("panel.hear", item=child["id"], group="contains").label.startswith("Brockenhurst")
    assert hants.run("panel.go", item=child["id"], group="contains").focus["group"] == "contains"


def test_overlapping_an_area_says_both_shares(hants):
    headings = group(hants.panel(open={"overlapping"}), "overlapping")["items"]
    assert [h["name"] for h in headings] == ["National parks"]   # under a heading for each kind (P3-T24e)
    items = headings[0]["children"]
    assert [i["name"] for i in items] == ["New Forest National Park"]
    assert "14 percent of Hampshire and 92 percent of New Forest National Park overlap" in items[0]["label"]


@pytest.mark.skip(reason="The Crossing group went in P3-T29a; its content comes back in Overlapping in P3-T29e")
def test_crossing_an_area_lists_lines_across_then_along_by_name(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(SWITZERLAND))
    s.start()
    labels = [i["label"] for i in group(s.panel(open={"crossing"}), "crossing")["items"]]
    assert labels[0].endswith("crosses it") and labels[-1].endswith("along its border")
    s.store.close()


def test_a_group_with_nothing_says_so(swiss):
    g = group(swiss.panel(open={"overlapping"}), "overlapping")
    assert g["items"] == [] and g["empty"] == "Nothing overlaps Switzerland."


HEADING_OF_BORDERING = {"region": "panel", "group": "bordering", "heading": True}


# Sorting (P3-T4d) -------------------------------------------------------------------------------

def test_ctrl_s_cycles_the_orders_of_the_group_the_focus_is_in(swiss):
    swiss.run("panel.bordering")
    swiss.panel(open={"bordering"})
    assert swiss.run("panel.sort").focus == HEADING_OF_BORDERING   # bearing -> name
    assert group(swiss.panel(), "bordering")["label"].endswith("by name")
    names = [i["name"] for i in group(swiss.panel(), "bordering")["items"]]
    assert names == sorted(names)
    swiss.run("panel.sort")
    assert group(swiss.panel(), "bordering")["label"].endswith("by distance")
    d = [i["distance_m"] for i in group(swiss.panel(), "bordering")["items"]]
    assert d == sorted(d)
    swiss.run("panel.sort_back")
    assert group(swiss.panel(), "bordering")["label"].endswith("by name")


def test_a_group_whose_first_order_is_natural_has_it_in_its_cycle(hants):
    hants.run("panel.within")
    hants.run("panel.sort_back")
    assert group(hants.panel(), "within")["label"].endswith("clockwise from north")
    hants.run("panel.sort")
    assert group(hants.panel(), "within")["label"].endswith("smallest first")


def test_headings_say_their_order_after_the_count_and_an_empty_one_says_none(swiss, hants):
    assert group(hants.panel(), "within")["label"] == "Within, 3 items, smallest first"
    assert group(hants.panel(), "nearby")["label"].endswith(", by distance")
    empty = group(swiss.panel(open={"overlapping"}), "overlapping")
    assert empty["label"] == "Overlapping Switzerland, no items"   # no order with no items


def test_ctrl_s_puts_the_focus_on_the_heading_and_says_nothing_from_an_item(swiss):
    swiss.run("panel.bordering")
    swiss.panel(open={"bordering"})
    swiss.run("panel.select", item=group(swiss.panel(), "bordering")["items"][0]["id"], group="bordering")
    r = swiss.run("panel.sort")
    assert r.focus == HEADING_OF_BORDERING and r.panel_stale and not r.announcements   # the focus move says it
    r = swiss.run("panel.sort_back")
    assert r.focus == HEADING_OF_BORDERING and not r.announcements


def test_ctrl_s_on_the_heading_itself_says_the_new_heading_once(swiss):
    swiss.run("panel.bordering")
    swiss.panel(open={"bordering"})
    swiss.run("panel.select", group="bordering")   # the focus is on the heading
    r = swiss.run("panel.sort")
    assert r.focus == HEADING_OF_BORDERING
    assert [a["text"] for a in r.announcements] == ["Bordering Switzerland, 5 items, by name"]


def test_the_chosen_order_does_not_change_the_cached_items(swiss):
    swiss.run("panel.bordering")
    first = [i["id"] for i in group(swiss.panel(open={"bordering"}), "bordering")["items"]]
    swiss.run("panel.sort")
    swiss.run("panel.sort_back")
    assert [i["id"] for i in group(swiss.panel(), "bordering")["items"]] == first


def test_ctrl_enter_says_bookmarks_come_later(swiss):
    assert swiss.run("panel.bookmark").announcements[0]["text"] == "Bookmarks come in Phase 4."
    assert registry.by_name("panel.bookmark").key == "Ctrl+Enter"


# The map's highlight for an item of each new group (P3-T4f, VIS-1) ------------------------------
# The highlight colours keep 7 to 1 in the high contrast themes: tests/mapcore/test_themes_and_names.py
# checks the highlight outline on its fill for every theme.

def _highlighted(session, gid, item_id):
    """Whether the frame marks the item: a shape, a line run or a marker is in the highlight style."""
    from mapcore.render import scene as scene_mod
    session.run("panel.select", item=item_id, group=gid)
    f = session.scene(800, 600)
    lines = any(a == item_id and st == scene_mod.HIGHLIGHT_LINE_STYLE
                for a, st in zip(f["line_area"], f["line_style"].tolist()))
    return bool(f["highlight"]) or lines, f


def test_the_map_highlights_an_item_of_each_new_group(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    s.set_current_feature(s.areas[1].id)                                  # England holds the river and the county
    listed = [c for h in group(s.panel(open={"contains"}), "contains")["items"] for c in h["children"]]
    contains = next(c for c in listed if c["name"] == "River Itchen")     # a line
    county = next(c for c in listed if c["name"] == "Hampshire")          # an area
    for gid, item in (("contains", contains), ("contains", county)):
        marked, _ = _highlighted(s, gid, item["id"])
        assert marked, f"{item['name']} in {gid} is in view but not highlighted"
    s.store.close()


def test_a_bordering_item_is_highlighted_and_one_out_of_view_does_not_fail(test_pack):
    """France at 1,000 km is in view; at 1 km it is not. Its large outer ring may still be kept for
    its bounding box, so only that the frame builds and every highlight index is valid is checked."""
    for zoom in (1_000_000, 1000):
        s = MapSession(packs=[test_pack], saved_state=dict(SWITZERLAND, zoom_m=zoom))
        s.start()
        france = next(i for i in group(s.panel(open={"bordering"}), "bordering")["items"] if i["name"] == "France")
        marked, frame = _highlighted(s, "bordering", france["id"])
        assert all(0 <= i < len(frame["shape_area"]) for i in frame["highlight"])
        if zoom == 1_000_000:
            assert marked
        s.store.close()


def test_an_overlapping_item_of_an_unfilled_layer_is_highlighted(hants):
    # The P3-T4f finding, fixed by P3-T23: a layer that is not filled is still outlined, so its shapes are drawn.
    item = group(hants.panel(open={"overlapping"}), "overlapping")["items"][0]["children"][0]
    assert _highlighted(hants, "overlapping", item["id"])[0]
