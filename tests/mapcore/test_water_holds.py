"""Water holds only water features and islands (P3-T29d; INF-4, DAT-4).

A sea or ocean holds seas, bays and straits and islands; a lake holds its islands. Rivers, roads, railways and
towns are never inside water, even where the sea's rough outline overlaps the coast. The test pack has no sea
whose stored relationships put such a feature inside it, so the session tests add those relationships to the
stored ones of a lake in Hampshire (Longbridge Lake), as the build would store them for an outline that overlaps.
"""
from dataclasses import replace

import pytest

from mapcore.session import MapSession
from mapcore.store import contents

LAKE = "osm:r10303325"   # Longbridge Lake, in the test pack
NOT_IN_WATER = ("rivers", "roads", "railways", "towns")


@pytest.mark.parametrize("holder", ["oceans", "seas"])
def test_a_sea_holds_bays_straits_and_islands_never_land_features(holder):
    for layer in ("seas", "oceans", "sea-places", "islands"):
        assert contents.water_may_hold(holder, layer), layer
    for layer in NOT_IN_WATER:
        assert not contents.water_may_hold(holder, layer), layer


def test_a_lake_holds_its_islands_and_bays_not_a_river():
    assert contents.water_may_hold("lakes", "islands")
    assert contents.water_may_hold("lakes", "sea-places")   # a bay on a lake, kept by P3-T28c
    for layer in NOT_IN_WATER:
        assert not contents.water_may_hold("lakes", layer), layer


def test_a_county_still_holds_a_river_and_the_rest():
    for holder in ("counties", "regions", "countries", "continents"):
        for layer in (*NOT_IN_WATER, "islands", "lakes", "seas"):
            assert contents.water_may_hold(holder, layer)


@pytest.fixture
def hants(test_pack, monkeypatch):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.957, "lon": -1.488, "zoom_m": 100000, "step_m": 1000})
    s.start()
    real = s.store.relationships

    def relationships(identifier):
        rel = dict(real(identifier))
        rec = s.store.feature(identifier)
        if identifier != LAKE and rec is not None and rec.layer in NOT_IN_WATER:
            rel["in"] = [LAKE, *rel.get("in", ())]   # an outline that overlaps the coast
        return rel

    real_feature = s.store.feature

    def feature(identifier):
        f = real_feature(identifier)
        if identifier == LAKE and f is not None:   # no bounding box: no feature is ruled out by its box alone
            f = replace(f, record={k: v for k, v in f.record.items() if k != "bbox"})
        return f

    monkeypatch.setattr(s.store, "relationships", relationships)
    monkeypatch.setattr(s.store, "feature", feature)
    yield s
    s.store.close()


def test_browse_and_contains_leave_land_features_out_of_water(hants):
    current = hants.store.feature(LAKE)
    for layer in NOT_IN_WATER:
        assert hants.store.browse(layer, LAKE) == [], layer
    assert not set(hants._contained(current)) & set(NOT_IN_WATER)


def test_the_same_relationships_do_list_them_when_the_rule_is_off(hants, monkeypatch):
    """The control: without the rule the added relationships do put land features in the lake, so the test above
    is not passing for want of data."""
    monkeypatch.setattr(contents, "water_may_hold", lambda holder, layer: True)
    listed = [layer for layer in NOT_IN_WATER if hants.store.browse(layer, LAKE)]
    assert listed, "the lake's bounding box meets no river, road, railway or town in the test pack"
    assert set(listed) <= set(hants._contained(hants.store.feature(LAKE)))
