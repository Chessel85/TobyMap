"""P3-T33b: a layer that is off is in no list (SCP-6; the PO's answer to DP186, 20 November 2026: "If a layer is off,
then it shouldn't be in the Information Panel").

Off means the layer's check box in the layers list is clear, or the map view in use has it off: MapSession._layer_on.
A layer that is on but not painted (fill "none") is still on, and listed. Every Information panel group, search and
its dialog, browsing by category and its counts, hierarchy mode's lists and their "in all" numbers, Details' related
areas, the query builder and the world tree leave out the features of a layer that is off. The current feature
stays current when its own layer is switched off: the groups about it go on naming it.

Hampshire (osm:r172799) in the test pack is in England, borders Wiltshire and Southampton, holds Brockenhurst
station and Longbridge Lake, overlaps the New Forest National Park, and is crossed by the River Itchen.
"""
import pytest

from mapcore import panel as panel_table
from mapcore import session as session_mod
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
HAMPSHIRE_ID = "osm:r172799"


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    s.set_current_feature(HAMPSHIRE_ID)
    yield s
    s.store.close()


def off(s, *layers):
    for layer in layers:
        s.run("layers.set", layer=layer, field="on", value=False)


def group(s, gid):
    return next(g for g in s.panel(open={gid}) if g["id"] == gid)


def listed(s, gid):
    """The features listed in a group, as their layers."""
    return {s.store.layer_of(i["id"]) for i in panel_table.walk(group(s, gid)["items"])
            if not panel_table.is_heading(i["id"]) and s.store.layer_of(i["id"])}


# The current feature ----------------------------------------------------------------------------------------

def test_the_current_feature_stays_current_when_its_layer_is_off_and_its_neighbours_go(s):
    assert "counties" in listed(s, "bordering")
    off(s, "counties")
    assert s.current_feature.id == HAMPSHIRE_ID
    g = group(s, "bordering")
    assert g["label"].startswith("Bordering Hampshire")
    assert "counties" not in listed(s, "bordering")


def test_contains_and_overlapping_leave_out_layers_that_are_off(s):
    assert "stations" in listed(s, "contains")
    assert {"national_parks", "rivers"} <= listed(s, "overlapping")
    off(s, "stations", "national_parks", "rivers")
    assert "stations" not in listed(s, "contains")
    assert listed(s, "overlapping") == set()


# Search -----------------------------------------------------------------------------------------------------

def test_search_leaves_out_a_layer_that_is_off(s):
    assert any(f["layer"] == "counties" for f in s.search("Hampshire"))
    off(s, "counties")
    assert all(f["layer"] != "counties" for f in s.search("Hampshire"))


def test_the_search_group_drops_results_whose_layer_is_switched_off_afterwards(s):
    s.run("search.query", text="Brockenhurst")
    assert "stations" in listed(s, "search")
    off(s, "stations")
    assert "stations" not in listed(s, "search")


def test_the_search_dialog_offers_only_layers_that_are_on(s):
    off(s, "lakes")
    ids = [x["id"] for x in s.run("search.open").dialog["scopes"]]
    assert "layer:rivers" in ids and "layer:lakes" not in ids


# Browsing by category and the counts ----------------------------------------------------------------------

def test_browsing_counts_only_layers_that_are_on(s):
    lines = s.run("browse.open").dialog["lines"]
    assert any(line.startswith("Lakes ") for line in lines)
    off(s, "lakes")
    lines = s.run("browse.open").dialog["lines"]
    assert not any(line.startswith("Lakes ") for line in lines)
    assert any(line.startswith("Rivers ") for line in lines)


def test_downs_in_all_counts_only_layers_that_are_on(s, monkeypatch):
    """A kind's "in all" adds the layers counted under it (CONTAINS_KIND, as the bays drawn as places are under
    the seas), but only those that are on."""
    monkeypatch.setattr(session_mod, "CONTAINS_KIND", {"lakes": "stations"})
    monkeypatch.setattr(s.store, "contents_counts", lambda _i: ({}, {"stations": 1, "lakes": 4}))
    assert s._hierarchy_down().dialog["lines"] == ["Railway stations: 1 shown at this zoom, 5 in all"]
    off(s, "lakes")
    assert s._hierarchy_down().dialog["lines"] == ["Railway stations 1"]


# Details ----------------------------------------------------------------------------------------------------

def test_details_part_of_leaves_out_a_layer_that_is_off(s):
    s.selected = HAMPSHIRE_ID
    assert "Part of: England" in s.details()
    off(s, "regions")
    s.selected = HAMPSHIRE_ID
    assert "Part of:" not in s.details()


# The query builder ------------------------------------------------------------------------------------------

def test_the_query_builder_refuses_a_layer_that_is_off_and_offers_only_those_on(s):
    off(s, "rivers")
    form = s.run("query.open").dialog
    assert "rivers" not in [x["id"] for x in form["layers"]]
    r = s.run("query.run", layer="rivers", relation="crossing", of=HAMPSHIRE_ID)
    assert r.error


def test_the_query_builders_of_list_leaves_out_search_results_of_a_layer_that_is_off(s):
    s.run("search.query", text="Brockenhurst")
    found = [f for f in s.search_found.values() if f.layer == "stations"]
    assert found
    off(s, "stations")
    of = [x["id"] for x in s.run("query.open").dialog["of"]]
    assert not any(f.id in of for f in found)


# The world tree ---------------------------------------------------------------------------------------------

@pytest.fixture
def world(continents_pack):
    s = MapSession(packs=[continents_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


def names_in(s, identifier):
    return [i["label"].split(",")[0] for i in s.run("tree.children", id=identifier).branch["items"]]


def test_the_world_tree_passes_over_a_layer_that_is_off_and_lists_what_is_under_it(world):
    assert "United Kingdom" in names_in(world, "continent:europe")
    off(world, "countries")
    europe = names_in(world, "continent:europe")
    assert "United Kingdom" not in europe and "France" not in europe
    assert {"England", "Brittany"} <= set(europe) and europe == sorted(europe, key=str.casefold)
    root = [i["label"] for i in world.run("tree.open").dialog["root"]["items"]]
    assert "Europe, continent" in root
