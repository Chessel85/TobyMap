"""Hierarchy mode in the core (P3-T6a; NAV-4, NAV-11, LOC-4, DP70, DP77).

M switches between stepping and hierarchy mode (the PO's key list, in place of 1 and 2). In hierarchy
mode Up goes to the area that holds the current feature, Down lists what it holds, and Left and Right go
round its neighbours. The test pack has no continents, so "up" from Hampshire ends at the United Kingdom.
Brockenhurst station is inside both Hampshire and the New Forest National Park, neither inside the other,
which gives the ambiguous up.
"""
import pytest

from mapcore.geo import geodesy
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}
FRANCE = {"lat": 47.0, "lon": 2.5, "zoom_m": 100000, "step_m": 1000}


def session(test_pack, place, **extra):
    s = MapSession(packs=[test_pack], saved_state=dict(place, **extra))
    s.start()
    s.run("mode.toggle")
    return s


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


@pytest.fixture
def hants(test_pack):
    s = session(test_pack, HAMPSHIRE)
    yield s
    s.store.close()


# Switching mode (NAV-11) --------------------------------------------------------------------------

def test_m_enters_and_leaves_hierarchy_mode_without_moving(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    before = (s.world.lat, s.world.lon, s.world.zoom_m)
    r = s.press("M", "map")
    assert said(r) == "Hierarchy mode. Hampshire." and s.world.movement_mode == "hierarchy"
    assert s.toggles()["mode.toggle"] is True
    assert "Hierarchy mode." in said(s.run("where.heading"))
    assert said(s.press("M", "map")) == "Stepping mode."
    assert (s.world.lat, s.world.lon, s.world.zoom_m) == before
    s.store.close()


def test_the_arrows_step_again_in_stepping_mode(hants):
    hants.run("mode.toggle")
    lat = hants.world.lat
    hants.run("move.north")
    hants.release()
    assert hants.world.lat > lat


def test_a_held_arrow_does_not_repeat_in_hierarchy_mode(hants):
    before = (hants.world.lat, hants.world.lon)
    assert hants.run("move.north", held=True, repeat=True).announcements == []
    assert (hants.world.lat, hants.world.lon) == before and hants.holding is None


# Up (NAV-4) ---------------------------------------------------------------------------------------

def test_up_from_hampshire_goes_to_england_then_the_united_kingdom_with_no_menu(hants):
    r = hants.run("move.north")
    assert r.dialog is None and said(r).startswith("England. Zoom ")
    assert hants.current_feature.name == "England"
    england = hants.store.feature(hants.current_feature.id)
    lon, lat = england.record["point"]
    assert (hants.world.lat, hants.world.lon) == pytest.approx((lat, lon), abs=1e-6)
    hants.run("move.north")
    assert hants.current_feature.name == "United Kingdom"
    r = hants.run("move.north")   # nothing holds it in the test pack
    assert r.earcons == ["blocked"] and said(r) == "Nothing holds United Kingdom."
    assert hants.current_feature.name == "United Kingdom"


def test_up_uses_only_layers_that_are_on(hants):
    hants.run("layers.set", layer="regions", field="on", value=False)
    hants.run("move.north")
    assert hants.current_feature.name == "United Kingdom"


def test_moving_zooms_to_fit_and_details_and_the_map_follow(hants):
    hants.run("move.north")
    zoom = hants.world.zoom_m
    assert 100_000 <= zoom <= 1_000_000   # England, from 1 km
    assert hants.details().startswith("England\n")
    hants.panel()
    assert hants.scene(800, 600) is not None


def test_alt_comma_comes_back_with_the_zoom_and_the_feature(hants):
    hants.run("move.north")
    hants.run("move.north")
    assert hants.current_feature.name == "United Kingdom"
    hants.run("history.back")
    assert hants.current_feature.name == "England"
    hants.run("history.back")
    assert hants.world.zoom_m == 1000 and hants.current_feature.name == "Hampshire"
    hants.run("history.forward")
    assert hants.current_feature.name == "England"


# Down (NAV-4, INF-4, DP70) --------------------------------------------------------------------------

def down_kinds(s):
    r = s.run("move.south")
    assert r.dialog is not None and r.dialog["kind"] == "choose" and r.dialog["go"] == "hierarchy.choose"
    return r.dialog["lines"]


def test_down_lists_the_kinds_inside_with_counts_then_their_features(test_pack):
    s = session(test_pack, HAMPSHIRE, zoom_m=100000)
    kinds = down_kinds(s)
    assert "Railway stations 1" in kinds and "Rivers 1" in kinds
    assert "National parks 1" in kinds   # partly inside counts, with no label (DP70)
    r = s.run("hierarchy.choose", index=kinds.index("Railway stations 1"))
    assert r.dialog["title"] == "Railway stations in Hampshire" and r.dialog["lines"][0].startswith("Brockenhurst, ")
    r = s.run("hierarchy.choose", index=0)
    assert said(r) == "Brockenhurst. Zoom 100 kilometres." and s.current_feature.name == "Brockenhurst"
    assert s.world.zoom_m == 100000   # a place keeps the zoom
    s.store.close()


def test_down_from_england_lists_its_counties(test_pack):
    """Up fits England at a zoom beyond the Counties layer's zoom range (100 km in the test pack); Down
    still lists the counties, as the PO chose (DP188)."""
    s = session(test_pack, HAMPSHIRE, zoom_m=1000)
    s.run("move.north")
    assert s.world.zoom_m > 100000
    kinds = down_kinds(s)
    counties = next(k for k in kinds if k.startswith("Counties "))
    r = s.run("hierarchy.choose", index=kinds.index(counties))
    assert any(line.startswith("Hampshire, ") for line in r.dialog["lines"])
    s.store.close()


def test_down_from_a_county_with_no_national_park_does_not_list_national_parks(test_pack):
    s = session(test_pack, {"lat": 51.25, "lon": -0.45, "zoom_m": 100000, "step_m": 1000})   # Surrey
    assert s.current_feature.name == "Surrey"
    r = s.run("move.south")
    lines = r.dialog["lines"] if r.dialog else []
    assert not any(line.startswith("National parks") for line in lines)
    s.store.close()


def test_the_park_does_not_list_england_as_inside_it(test_pack):
    s = session(test_pack, HAMPSHIRE, zoom_m=1_000_000)
    park = next(i for i, *_ in s.store.relationships(s.current_feature.id)["overlaps"])
    s.set_current_feature(park)
    r = s.run("move.south")
    lines = r.dialog["lines"] if r.dialog else []
    assert not any(line.startswith(("Regions", "Countries")) for line in lines)
    s.store.close()


# The ambiguous up (NAV-4) -----------------------------------------------------------------------------

def to_brockenhurst(test_pack):
    s = session(test_pack, HAMPSHIRE, zoom_m=100000)
    kinds = down_kinds(s)
    s.run("hierarchy.choose", index=kinds.index("Railway stations 1"))
    s.run("hierarchy.choose", index=0)
    return s


def test_up_from_a_place_in_hampshire_and_the_new_forest_offers_both(test_pack):
    s = to_brockenhurst(test_pack)
    before = (s.world.lat, s.world.lon)
    r = s.run("move.north")
    assert "ambiguous_up" in r.earcons
    assert r.dialog["kind"] == "choose" and r.dialog["cancel"] == "Cancel"
    # Smallest first, each with its type.
    assert r.dialog["lines"] == ["New Forest National Park, national park", "Hampshire, county of England"]
    assert (s.world.lat, s.world.lon) == before   # Cancel runs nothing, so you stay
    r = s.run("hierarchy.choose", index=0)
    assert s.current_feature.name == "New Forest National Park" and said(r).startswith("New Forest National Park.")
    s.store.close()


def test_a_parent_in_a_layer_switched_off_is_not_offered(test_pack):
    s = to_brockenhurst(test_pack)
    s.run("layers.set", layer="national_parks", field="on", value=False)
    r = s.run("move.north")
    assert r.dialog is None and s.current_feature.name == "Hampshire"
    s.store.close()


# Left and Right: the neighbours, clockwise from ahead (NAV-4, INF-2) ------------------------------------

def neighbours(s, key="move.east"):
    """Go round the neighbours once, and give each one's name and bearing from where you started."""
    start = (s.world.lat, s.world.lon)
    out, first = [], None
    while True:
        r = s.run(key)
        name = s.current_feature.name
        if name == first:
            return out
        first = first or name
        _, bearing, _ = geodesy.inverse(*start, s.world.lat, s.world.lon)
        out.append((name, bearing, said(r)))


@pytest.mark.parametrize("orientation, heading", [("north-fixed", 0.0), ("cardinal", 90.0), ("free", 200.0)])
def test_the_neighbours_of_france_clockwise_from_ahead(test_pack, orientation, heading):
    s = session(test_pack, FRANCE, orientation=orientation, heading=heading)
    assert s.current_feature.name == "France"
    found = neighbours(s)
    names = [n for n, *_ in found]
    assert {"Spain", "Belgium", "Germany"} <= set(names)
    ahead = 0.0 if orientation == "north-fixed" else heading
    turns = [(b - ahead) % 360.0 for _, b, _ in found]
    assert turns == sorted(turns)
    s.store.close()


def test_a_neighbour_is_said_with_its_direction_border_and_zoom(test_pack):
    s = session(test_pack, FRANCE)
    spain = next(text for name, _, text in neighbours(s) if name == "Spain")
    assert spain.startswith("Spain, south") and ", shared border " in spain and ". Zoom " in spain


def test_left_goes_round_the_other_way(test_pack):
    s = session(test_pack, FRANCE)
    right = [n for n, *_ in neighbours(s)]
    s.store.close()
    s = session(test_pack, FRANCE)
    assert [n for n, *_ in neighbours(s, "move.west")] == right[::-1]
    s.store.close()


def test_switzerland_has_its_five_neighbours(test_pack):
    s = session(test_pack, {"lat": 46.8, "lon": 8.2, "zoom_m": 100000, "step_m": 1000})
    assert sorted(n for n, *_ in neighbours(s)) == ["Austria", "France", "Germany", "Italy", "Liechtenstein"]
    s.store.close()
