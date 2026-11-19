"""Contains, limited to the view by real shapes (P3-T29c; INF-4, the PO's answer R2).

Contains lists the visible features wholly inside the current feature (the stored "in"), each whose nearest
point, measured on its real shape, is within the zoom distance of you. A bounding box is only a first filter.
Each item is said with the distance and direction to its nearest point, and an area you are in says "you are
inside". Bays and straits, areas and places, are one subgroup, "Seas, bays and straits". Hierarchy mode's Down
lists the same features.

The River Itchen runs from north-east to south-west, so its bounding box holds ground well away from it: at
50.89 north, 1.32 west, inside its box, it is about 4.5 kilometres away.
"""
from dataclasses import replace

import pytest

from mapcore.describe import words
from mapcore.session import MapSession

ITCHEN = "osm:r7703089"         # wholly in England, only partly in Hampshire (70 percent) and Southampton
HAMPSHIRE_ID = "osm:r172799"
BROCKENHURST = "osm:n6076836207"
ATLANTIC = "vliz:goas:north-atlantic-ocean"
BISCAY = "osm:r7156290"         # the Bay of Biscay, an area in the layer seas, inside the North Atlantic
OFF_ITCHEN = (50.89, -1.32)     # inside the Itchen's box, 4.5 kilometres from the river


def start(test_pack, lat, lon, zoom_m):
    s = MapSession(packs=[test_pack], saved_state={"lat": lat, "lon": lon, "zoom_m": zoom_m, "step_m": 1000})
    s.start()
    return s


def contains(s):
    """Contains' headings, each with its children."""
    g = next(g for g in s.panel(open={"contains"}) if g["id"] == "contains")
    return g["items"]


def children(s):
    return [c for h in contains(s) for c in h["children"]]


def england(s):
    return next(a for a in s.areas if a.name == "England")


def test_a_feature_only_partly_inside_is_not_listed(test_pack):
    """The River Itchen is 70 percent in Hampshire: not in Contains Hampshire (it goes to Overlapping, P3-T29e).
    The New Forest National Park, which overlaps Hampshire, is not listed either; Brockenhurst, wholly inside, is."""
    s = start(test_pack, 51.06, -1.31, 100000)
    assert s.current_feature.id == HAMPSHIRE_ID
    ids = [c["id"] for c in children(s)]
    assert ITCHEN not in ids and "osm:r2678988" not in ids
    assert BROCKENHURST in ids
    assert not any("partly" in c["label"] for c in children(s))
    s.store.close()


@pytest.mark.parametrize("zoom_m, listed", [(2500, False), (5000, True)])
def test_a_line_is_listed_only_when_its_shape_comes_within_the_zoom_distance(test_pack, zoom_m, listed):
    """Inside the Itchen's bounding box, 4.5 kilometres from the river: at 2.5 kilometres zoom its box reaches you
    but its shape does not, so it is not listed; at 5 kilometres it is, with its distance and direction to its
    nearest point, and Enter and Space use that point."""
    s = start(test_pack, *OFF_ITCHEN, zoom_m)
    s.set_current_feature(england(s).id)
    item = next((c for c in children(s) if c["id"] == ITCHEN), None)
    assert (item is not None) == listed
    if listed:
        near = s.store.measure(s.store.feature(ITCHEN), *OFF_ITCHEN)
        assert 4000 < near.distance_m < 5000
        assert item["label"] == "River Itchen, {} {}".format(
            words.distance_text(near.distance_m, s._units()),
            words.direction_text(near.bearing_deg, s.settings["bearing"], None))
        assert item["distance_m"] == pytest.approx(near.distance_m, rel=0.01)
        _area, lat, lon = s._spots[("contains", ITCHEN)][:3]
        assert (lat, lon) == pytest.approx((near.lat, near.lon), abs=1e-3)
    s.store.close()


def test_the_distance_is_to_the_nearest_point_not_the_features_own_point(test_pack):
    s = start(test_pack, *OFF_ITCHEN, 25000)
    s.set_current_feature(england(s).id)
    item = next(c for c in children(s) if c["id"] == ITCHEN)
    assert 4000 < item["distance_m"] < 5000
    s.store.close()


def test_an_area_you_are_in_says_you_are_inside(test_pack):
    s = start(test_pack, 51.06, -1.31, 100000)
    s.set_current_feature(england(s).id)
    hampshire = next(c for c in children(s) if c["id"] == HAMPSHIRE_ID)
    assert hampshire["label"] == "Hampshire, you are inside"
    assert hampshire["distance_m"] == 0.0
    s.store.close()


@pytest.fixture
def ocean(test_pack, monkeypatch):
    """The North Atlantic, from the Bay of Biscay at 500 kilometres, with Brockenhurst station made a bay that
    is only a place (layer sea-places) inside the ocean: the test pack has no such place."""
    s = start(test_pack, 47.0, -4.0, 500000)
    real_feature, real_rel = s.store.feature, s.store.relationships

    def feature(identifier):
        f = real_feature(identifier)
        if identifier == BROCKENHURST and f is not None:
            f = replace(f, record=dict(f.record, layer="sea-places"))
        return f

    def relationships(identifier):
        rel = dict(real_rel(identifier))
        if identifier == BROCKENHURST:
            rel["in"] = [ATLANTIC]
        return rel

    monkeypatch.setattr(s.store, "feature", feature)
    monkeypatch.setattr(s.store, "relationships", relationships)
    s.set_current_feature(ATLANTIC)
    yield s
    s.store.close()


def test_bays_and_straits_areas_and_places_are_one_subgroup(ocean):
    headings = contains(ocean)
    seas = [h for h in headings if h["name"] == "Seas, bays and straits"]
    assert len(seas) == 1, [h["label"] for h in headings]
    assert seas[0]["label"] == "Seas, bays and straits 2"
    assert {c["id"] for c in seas[0]["children"]} == {BISCAY, BROCKENHURST}
    assert not any(h["name"] == "Bays and straits, as places" for h in headings)


def test_down_counts_bays_and_straits_as_one_kind(ocean):
    ocean.run("mode.toggle")
    lines = ocean.run("move.south").dialog["lines"]
    assert "Seas, bays and straits 2" in lines
    assert not any(line.startswith("Bays and straits, as places") for line in lines)


@pytest.mark.parametrize("place, current", [((51.06, -1.31, 100000), None), ((51.06, -1.31, 100000), "England"),
                                            (OFF_ITCHEN + (5000,), "England")])
def test_down_lists_the_same_features_as_contains(test_pack, place, current):
    s = start(test_pack, *place)
    if current:
        s.set_current_feature(england(s).id)
    listed = {c["id"] for c in children(s)}
    s.run("mode.toggle")
    if current:
        s.set_current_feature(england(s).id)   # the toggle keeps you here; the current feature is set again
    kinds = s.run("move.south").dialog["lines"]
    down = set()
    for k in range(len(kinds)):
        s.run("hierarchy.choose", index=k)
        down |= {identifier for _kind, identifier in s._choices}
        s.run("move.south")
    assert listed and down == listed
    s.store.close()


def test_a_place_where_you_are_is_said_here(test_pack):
    """Not "0 metres": a line or a place whose nearest point is where you are is "here", as in Within and Nearby."""
    s = start(test_pack, 50.816746, -1.5734094, 25000)   # at Brockenhurst station, in Hampshire
    s.set_current_feature(HAMPSHIRE_ID)
    station = next(c for c in children(s) if c["id"] == BROCKENHURST)
    assert station["label"] == "Brockenhurst, here"
    s.store.close()
