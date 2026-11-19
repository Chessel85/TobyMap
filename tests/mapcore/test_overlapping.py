"""Overlapping (P3-T29e; INF-5, INF-6): what is partly inside the current feature, and what it is partly inside.

For an area, three subgroups: the areas of other layers that cover part of it, under a heading for each layer; the
lines crossing its border; the lines along its border. For a line, the areas it passes through, in order from its
start. For a place, nothing. Everything comes from the stored relationships, which the build made from the real
shapes; a bounding box never puts anything here. Not limited by the view, but only from layers that are on.

The test pack holds Hampshire, Southampton (osm:r127864), the River Itchen (osm:r7703089), which crosses
Hampshire's border once and Southampton's twice, Switzerland and the Rhine (osm:r123924), which runs along its
border, and the New Forest National Park (osm:r2678988), which overlaps Hampshire and Wiltshire.
"""
from dataclasses import replace

import pytest

from mapcore import panel as panel_table
from mapcore.geo import geodesy
from mapcore.session import MapSession

HAMPSHIRE = "osm:r172799"
SOUTHAMPTON = "osm:r127864"
ITCHEN = "osm:r7703089"
RHINE = "osm:r123924"
SWITZERLAND = "osm:r51701"
PARK = "osm:r2678988"
BROCKENHURST = "osm:n6076836207"

IN_SOUTHAMPTON = {"lat": 50.91, "lon": -1.40, "zoom_m": 25000, "step_m": 5000}
IN_HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
IN_THE_PARK = {"lat": 50.87, "lon": -1.6, "zoom_m": 25000, "step_m": 5000}
IN_SWITZERLAND = {"lat": 46.8, "lon": 8.2, "zoom_m": 100000, "step_m": 1000}


def _session(test_pack, place, current=None):
    s = MapSession(packs=[test_pack], saved_state=dict(place))
    s.start()
    if current:
        s.set_current_feature(current)
    return s


def _group(s, *opened):
    return next(g for g in s.panel(open={"overlapping", *opened}) if g["id"] == "overlapping")


def _heading(group, label_start):
    return next((i for i in group["items"] if panel_table.is_heading(i["id"]) and i["label"].startswith(label_start)),
                None)


def _names(group):
    return [i["name"] for i in panel_table.walk(group["items"]) if not panel_table.is_heading(i["id"])]


# For an area: the areas of other layers that cover part of it ---------------------------------------------

def test_an_area_lists_the_areas_of_other_layers_over_it_by_layer_with_both_shares(test_pack):
    s = _session(test_pack, IN_THE_PARK, PARK)
    g = _group(s)
    counties = _heading(g, "Counties ")
    assert counties is not None and counties["label"] == "Counties 2"
    assert [c["name"] for c in counties["children"]] == ["Hampshire", "Wiltshire"]
    hants = counties["children"][0]
    # You are in Hampshire here, so its nearest point is where you are.
    assert hants["label"] == ("Hampshire, you are inside, 93 percent of New Forest National Park and 14 percent of "
                              "Hampshire overlap")
    wilts = counties["children"][1]
    assert " kilometres " in wilts["label"] or " metres " in wilts["label"]
    s.store.close()


def test_an_overlapping_area_is_measured_to_its_nearest_point_not_its_centre(test_pack):
    """From the north of Hampshire, the park's nearest point is much nearer than the centre of its box."""
    s = _session(test_pack, IN_HAMPSHIRE, HAMPSHIRE)
    park = next(c for c in _heading(_group(s), "National parks ")["children"] if c["name"] == "New Forest National Park")
    rec = s.store.feature(PARK).record["bbox"]
    to_centre = geodesy.inverse(s.world.lat, s.world.lon, (rec[1] + rec[3]) / 2, (rec[0] + rec[2]) / 2)[0]
    assert park["distance_m"] < to_centre - 5000
    _area, lat, lon = s._spots[("overlapping", PARK)]
    assert geodesy.inverse(s.world.lat, s.world.lon, lat, lon)[0] == pytest.approx(park["distance_m"], abs=1.0)
    s.store.close()


# For an area: the lines crossing its border, and those along it --------------------------------------------

def test_a_line_partly_inside_says_how_many_times_it_crosses_and_its_nearest_crossing(test_pack):
    s = _session(test_pack, IN_HAMPSHIRE, HAMPSHIRE)
    g = _group(s)
    lines = _heading(g, "Lines crossing its border ")
    assert lines["label"] == "Lines crossing its border 1"
    itchen = lines["children"][0]
    assert itchen["label"].startswith("River Itchen, crosses once, nearest ") and itchen["level"] == 2
    assert itchen["expandable"]
    # The headings: areas by layer first, then the lines crossing its border.
    assert [i["label"] for i in g["items"]] == ["National parks 1", "Lines crossing its border 1"]
    s.store.close()


def test_a_crossing_line_opens_to_each_crossing_and_enter_goes_to_it(test_pack):
    s = _session(test_pack, IN_SOUTHAMPTON, SOUTHAMPTON)
    itchen = _heading(_group(s, ITCHEN), "Lines crossing its border ")["children"][0]
    assert itchen["label"].startswith("River Itchen, crosses twice, nearest ")
    points = itchen["children"]
    assert [p["label"].split(",")[0] for p in points] == ["Crossing 1 of River Itchen", "Crossing 2 of River Itchen"]
    assert all(p["level"] == 3 for p in points)
    assert points[0]["distance_m"] <= points[1]["distance_m"]   # nearest first
    _area, lat, lon, _point = s._spots[("overlapping", points[1]["id"])]
    s.run("panel.go", item=points[1]["id"], group="overlapping")
    assert (s.world.lat, s.world.lon) == pytest.approx((lat, lon))
    s.store.close()


def test_a_line_along_the_border_is_in_its_own_subgroup_not_crossing_it_hundreds_of_times(test_pack):
    s = _session(test_pack, IN_SWITZERLAND, SWITZERLAND)
    g = _group(s)
    along = _heading(g, "Lines along its border ")
    assert along["label"] == "Lines along its border 1"
    assert along["children"][0]["name"] == "Rhine" and along["children"][0]["label"].endswith(", along its border")
    assert _heading(g, "Lines crossing its border ") is None
    assert not any("crosses " in i["label"] and " times" in i["label"] for i in panel_table.walk(g["items"]))
    s.store.close()


def test_the_lines_partly_inside_are_read_from_the_area_alone(test_pack, monkeypatch):
    """Item 4b: the build keeps the lines partly inside each area ("partly_by"), so no line's own relationships
    are read, which made a first open for England take about two seconds on the world pack. A line wholly
    inside, which the build leaves out of the list, is in Contains, not here."""
    s = _session(test_pack, IN_HAMPSHIRE, HAMPSHIRE)
    real = s.store.relationships
    assert ITCHEN in real(HAMPSHIRE)["partly_by"]
    read = []

    def relationships(identifier):
        read.append(identifier)
        return real(identifier)

    monkeypatch.setattr(s.store, "relationships", relationships)
    assert "River Itchen" in _names(_group(s))
    assert ITCHEN not in read

    def without_itchen(identifier):
        rel = dict(real(identifier))
        if identifier == HAMPSHIRE:
            rel["partly_by"] = [i for i in rel["partly_by"] if i != ITCHEN]
        return rel

    monkeypatch.setattr(s.store, "relationships", without_itchen)
    s.run("move.north")   # a new place, so the group is made again
    s.release()
    s.set_current_feature(HAMPSHIRE)
    assert "River Itchen" not in _names(_group(s))
    s.store.close()


def test_a_line_wholly_inside_is_not_listed_as_crossing_from_a_pack_without_the_list(test_pack, monkeypatch):
    """A pack written before item 4b has no "partly_by": each crossing line's own relationships are read, and a
    line whose stored "in" holds the area is in Contains, not here, though the build stored a crossing."""
    s = _session(test_pack, IN_HAMPSHIRE, HAMPSHIRE)
    real = s.store.relationships

    def old_pack(identifier):
        rel = dict(real(identifier))
        rel.pop("partly_by", None)
        return rel

    monkeypatch.setattr(s.store, "relationships", old_pack)
    assert "River Itchen" in _names(_group(s))

    def relationships(identifier):
        rel = old_pack(identifier)
        if identifier == ITCHEN:
            rel["in"] = [HAMPSHIRE, *rel.get("in", ())]
        return rel

    monkeypatch.setattr(s.store, "relationships", relationships)
    s.run("move.north")   # a new place, so the group is made again
    s.release()
    s.set_current_feature(HAMPSHIRE)
    assert "River Itchen" not in _names(_group(s))
    s.store.close()


# For a line: the areas it passes through ------------------------------------------------------------------

def test_a_line_lists_the_areas_it_passes_through_in_order_from_its_start_with_shares(test_pack):
    """England and the United Kingdom hold all of the River Itchen, so Up reaches them, and they are not listed."""
    s = _session(test_pack, IN_SOUTHAMPTON, ITCHEN)
    g = _group(s)
    assert g["label"] == "Overlapping River Itchen, 2 items, from its start"
    assert [i["name"] for i in g["items"]] == ["Hampshire", "Southampton"]
    hants, soton = g["items"]
    assert hants["label"].endswith(", 70 percent of River Itchen is inside it")
    assert soton["label"] == "Southampton, you are inside, 30 percent of River Itchen is inside it"
    s.store.close()


def test_a_lines_areas_can_be_sorted_and_come_back_to_their_order_from_its_start(test_pack):
    s = _session(test_pack, IN_SOUTHAMPTON, RHINE)
    assert [i["name"] for i in _group(s)["items"]] == ["Switzerland", "Germany", "France",
                                                        "Büsingen am Hochrhein"]
    s.run("panel.overlapping")
    s.run("panel.sort")
    g = _group(s)
    assert g["label"].endswith(", by name")
    assert [i["name"] for i in g["items"]] == ["Büsingen am Hochrhein", "France", "Germany", "Switzerland"]
    s.run("panel.sort_back")
    assert _group(s)["label"].endswith(", from its start")
    s.store.close()


# For a place: nothing ----------------------------------------------------------------------------------------

def test_a_place_has_nothing_overlapping(test_pack):
    s = _session(test_pack, IN_THE_PARK, BROCKENHURST)
    g = _group(s)
    assert g["items"] == [] and g["empty"] == "Nothing overlaps Brockenhurst."
    s.store.close()


# Layers that are off, and bounding boxes -------------------------------------------------------------------

def test_a_layer_that_is_off_is_left_out(test_pack):
    s = _session(test_pack, IN_HAMPSHIRE, HAMPSHIRE)
    s.run("layers.set", layer="rivers", field="on", value=False)
    g = _group(s)
    assert _heading(g, "Lines crossing its border ") is None and _heading(g, "National parks ") is not None
    s.run("layers.set", layer="national_parks", field="on", value=False)
    assert _group(s)["items"] == []
    s.set_current_feature(ITCHEN)
    s.run("layers.set", layer="counties", field="on", value=False)
    assert _group(s)["items"] == []
    s.store.close()


def test_a_diagonal_line_whose_box_covers_the_area_is_not_listed_unless_the_relationships_say_so(test_pack,
                                                                                                 monkeypatch):
    """The River Itchen given a bounding box that covers all of Southampton, as a diagonal line's would, but with
    the stored relationships of a line that never reaches it: it is in neither's Overlapping."""
    s = _session(test_pack, IN_SOUTHAMPTON, SOUTHAMPTON)
    assert "River Itchen" in _names(_group(s))   # the control: with the real relationships it is listed
    real_rel, real_feature = s.store.relationships, s.store.feature

    def relationships(identifier):
        rel = dict(real_rel(identifier))
        if identifier == SOUTHAMPTON:
            rel["crossed_by"] = [i for i in rel.get("crossed_by", ()) if i != ITCHEN]
            rel["crossed_at"] = [c for c in rel.get("crossed_at", ()) if c[0] != ITCHEN]
            rel["partly_by"] = [i for i in rel.get("partly_by", ()) if i != ITCHEN]
        if identifier == ITCHEN:
            rel["crosses"] = [i for i in rel.get("crosses", ()) if i != SOUTHAMPTON]
            rel["partly"] = [p for p in rel.get("partly", ()) if p[0] != SOUTHAMPTON]
        return rel

    def feature(identifier):
        f = real_feature(identifier)
        if identifier == ITCHEN and f is not None:
            f = replace(f, record=dict(f.record, bbox=[-1.6, 50.8, -1.2, 51.1]))
        return f

    monkeypatch.setattr(s.store, "relationships", relationships)
    monkeypatch.setattr(s.store, "feature", feature)
    s.run("move.north")   # a new place, so the group is made again
    s.release()
    s.set_current_feature(SOUTHAMPTON)
    assert "River Itchen" not in _names(_group(s))
    s.set_current_feature(ITCHEN)
    assert "Southampton" not in _names(_group(s))
    s.store.close()
