"""Islands inside a sea or a lake (P3-T32g; INF-4, DAT-4, SRB-4).

On the world pack of 20 November, Contains for the English Channel and hierarchy mode's Down listed only "Seas, bays
and straits 476": no Jersey, no Guernsey, no Isle of Wight. An island is a hole in the sea's outline, so it is never
wholly inside the sea's area, and the stored "in" never holds the sea. The build does store each island's coast on
each water ("coast", with its length) and its whole outline ("outline_km"), so the rule is made from those: an
island is in a water when at least SHORE_SHARE of its outline is shore on that water. For a lake the writing stage
stores the island's shore on it ("lake_shore"), as lakes are not "water" to the relationships stage.

So an island all round in the sea is in it; Great Britain, a seventh of whose coast is on the Channel, is not in
the Channel; an island joined to the mainland for most of its outline is not in the sea; an island in a bay is in
the bay and in the sea or ocean round the bay, as its coast is on both; an island in a lake on another island is
not in the sea round that island, as none of its coast is on the sea.

The test pack has no islands layer, so the relationships here are made by the test, as the world pack has them.
"""
from types import SimpleNamespace

import pytest

from mapcore.store import contents
from mapcore.store import store as store_mod

CHANNEL = "ne:marine:1159116535"
ATLANTIC = "vliz:goas:9"
BAY = "ne:marine:bay"
LAKE = "osm:lake"

JERSEY = {"coast": [[CHANNEL, 76.99], [ATLANTIC, 76.99]], "outline_km": 76.99, "in": ["osm:r367988"]}
WIGHT = {"coast": [[CHANNEL, 106.76], [ATLANTIC, 106.76]], "outline_km": 112.54, "in": ["osm:r58447"]}
BRITAIN = {"coast": [[ATLANTIC, 11243.52], [CHANNEL, 1542.1], ["ne:marine:north-sea", 3298.54]],
           "outline_km": 11501.72}
JOINED = {"coast": [[CHANNEL, 3.0], [ATLANTIC, 3.0]], "outline_km": 10.0}    # 7 km of it against the mainland
IN_BAY = {"coast": [[BAY, 5.0], [ATLANTIC, 5.0]], "outline_km": 5.0}
IN_LAKE = {"lake_shore": [[LAKE, 44.0]], "outline_km": 44.48}
LAKE_ON_ISLAND = {"lake_shore": [["osm:lake-on-sicily", 2.0]], "outline_km": 2.0}


def test_an_island_all_round_in_the_sea_is_in_it():
    assert contents.waters_round(JERSEY) == {CHANNEL, ATLANTIC}
    assert contents.waters_round(WIGHT) == {CHANNEL, ATLANTIC}   # 95 percent: a river mouth is not sea


def test_an_island_with_a_little_of_its_coast_on_a_sea_is_not_in_that_sea():
    assert contents.waters_round(BRITAIN) == {ATLANTIC}


def test_an_island_joined_to_the_mainland_for_most_of_its_outline_is_not_in_the_sea():
    assert contents.waters_round(JOINED) == set()


def test_an_island_in_a_bay_is_in_the_bay_and_the_water_round_it():
    assert contents.waters_round(IN_BAY) == {BAY, ATLANTIC}


def test_an_island_in_a_lake_is_in_the_lake_and_not_in_the_sea_round_the_land():
    assert contents.waters_round(IN_LAKE) == {LAKE}
    assert contents.waters_round(LAKE_ON_ISLAND) == {"osm:lake-on-sicily"}


def test_no_outline_no_rule():
    assert contents.waters_round({"coast": [[CHANNEL, 5.0]]}) == set()
    assert contents.waters_round({}) == set()


def test_only_islands_are_held_by_the_water_round_them():
    """A county or a country with a coast is never inside the sea (water_may_hold says so too)."""
    assert CHANNEL in contents.holders(JERSEY, "islands")
    assert CHANNEL not in contents.holders(JERSEY, "counties")
    assert CHANNEL not in contents.holders(JERSEY)
    assert contents.wholly_in(JERSEY, CHANNEL, "islands")
    assert not contents.wholly_in(BRITAIN, CHANNEL, "islands")
    assert contents.wholly_in(JERSEY, "osm:r367988", "islands")   # the stored "in", as before
    assert not contents.partly_in(JERSEY, CHANNEL, "islands")


def test_an_island_that_also_overlaps_the_sea_is_wholly_in_it():
    rel = {**JERSEY, "overlaps": [[CHANNEL, 0.01, 0.0]]}
    assert not contents.partly_in(rel, CHANNEL, "islands")
    assert contents.partly_in(rel, CHANNEL, "counties")


def test_contents_stored_for_the_land_are_unchanged():
    """The writing stage's contents of the land areas: a sea is never one of the holders, so nothing changes."""
    records = [{"id": "osm:jersey", "layer": "islands"}, {"id": "osm:r367988", "layer": "countries"},
               {"id": CHANNEL, "layer": "seas"}]
    rels = {"osm:jersey": JERSEY}
    held = contents.contents(records, lambda i: rels.get(i, {}), {"osm:jersey": 1, "osm:r367988": 2, CHANNEL: 3})
    assert held == {"osm:r367988": {"islands": ([1], [])}}


# The store: browse, and the counts Ctrl+Shift+F and Down say ------------------------------------------------------

ISLANDS = {"osm:jersey": JERSEY, "osm:wight": WIGHT, "osm:britain": BRITAIN, "osm:joined": JOINED}


@pytest.fixture
def store(test_pack, monkeypatch):
    s = store_mod.Store(test_pack)
    rels = {**ISLANDS,
            CHANNEL: {"shores": [["osm:britain", 1542.1], ["osm:wight", 106.76], ["osm:jersey", 76.99],
                                 ["osm:joined", 3.0], ["osm:r58447", 900.0]],
                      "counts": {"sea-places": 476, "roads": 18}, "held": {"sea-places": 476}}}
    names = {"osm:jersey": "Jersey", "osm:wight": "Isle of Wight", "osm:britain": "Great Britain",
             "osm:joined": "Joined Island", "osm:r58447": "England", CHANNEL: "English Channel"}
    layers = {**{i: "islands" for i in ISLANDS}, "osm:r58447": "countries", CHANNEL: "seas"}

    def feature(i):
        if i not in layers:
            return None
        rec = {"id": i, "layer": layers[i], "names": {"en": names[i]}, "point": [0.0, 50.0],
               "bbox": [-6.0, 48.0, 2.0, 52.0]}
        return SimpleNamespace(id=i, name=names[i], layer=layers[i], pack=0, number=0, record=rec)

    monkeypatch.setattr(s, "relationships", lambda i: rels.get(i, {}))
    monkeypatch.setattr(s, "feature", feature)
    monkeypatch.setattr(s, "layer_of", lambda i: layers.get(i))
    monkeypatch.setattr(s, "_relationships_many", lambda ids: {i: rels.get(i, {}) for i in ids})
    monkeypatch.delitem(s._indexes[0].pack.manifest, "islands_in_water", raising=False)   # a pack written before
    s.scanned = 0
    real_scan = s._indexes[0].pack.scan

    def scan(layers_):
        s.scanned += 1
        return real_scan(layers_)

    monkeypatch.setattr(s._indexes[0].pack, "scan", scan)
    yield s
    s.close()


def test_a_sea_lists_the_islands_in_it(store):
    assert store.water_islands(CHANNEL) == ["osm:wight", "osm:jersey"]   # in the order of its shores
    found = store.browse("islands", CHANNEL)
    assert [f.name for f in found] == ["Isle of Wight", "Jersey"]
    assert all(f.description == f.name for f in found)   # wholly inside, not "partly in"


def test_a_sea_with_no_island_inside_its_area_is_not_scanned(store):
    """The islands come from the sea's shores; with no island counted inside its area, no layer is read through,
    which took 6 seconds for the Channel on the world pack."""
    store.browse("islands", CHANNEL)
    assert store.scanned == 0


def test_the_counts_take_the_islands_in(store):
    counts, held = store.contents_counts(CHANNEL)
    assert counts == {"islands": 2, "roads": 18, "sea-places": 476}
    assert held == {"islands": 2, "sea-places": 476}


def test_a_pack_that_stores_them_is_not_read_again(store, monkeypatch):
    """A pack written from P3-T32g on has the islands in each water's stored counts, as its manifest says."""
    monkeypatch.setitem(store._indexes[0].pack.manifest, "islands_in_water", True)
    assert store.contents_counts(CHANNEL) == ({"roads": 18, "sea-places": 476}, {"sea-places": 476})


def test_the_test_pack_says_it_stores_them(test_pack):
    s = store_mod.Store(test_pack)
    assert s.packs[0].manifest.get("islands_in_water") is True
    s.close()


def test_land_counts_are_as_stored(store):
    counts, held = store.contents_counts("osm:r58447")
    assert counts == {} and held is None


# The session: Contains, Down and Ctrl+Shift+F --------------------------------------------------------------------

TEST_ATLANTIC = "vliz:goas:north-atlantic-ocean"
BROCKENHURST = "osm:n6076836207"   # a station in the test pack, standing in for an island


@pytest.fixture
def ocean(test_pack, monkeypatch):
    """The North Atlantic, from the Bay of Biscay at 500 kilometres, with Brockenhurst station standing in for an
    island all round in the ocean, whose coast is on it: the test pack has no islands layer, so its stations layer
    is the islands layer here."""
    from dataclasses import replace

    from mapcore.session import MapSession

    monkeypatch.setattr(contents, "ISLE_LAYERS", ("stations",))
    monkeypatch.setitem(contents.WATER_HELD, "oceans", (*contents.WATER_HELD["oceans"], "stations"))
    s = MapSession(packs=[test_pack], saved_state={"lat": 47.0, "lon": -4.0, "zoom_m": 500000, "step_m": 1000})
    s.start()
    real_feature, real_rel = s.store.feature, s.store.relationships

    def relationships(identifier):
        rel = dict(real_rel(identifier))
        if identifier == BROCKENHURST:
            rel.update({"in": [i for i in rel.get("in", ()) if i != TEST_ATLANTIC], "coast": [[TEST_ATLANTIC, 4.0]],
                        "outline_km": 4.0})
        if identifier == TEST_ATLANTIC:   # its stored counts, as the build made them, leave the island out
            rel["shores"] = [*rel.get("shores", ()), [BROCKENHURST, 4.0]]
            for key in ("counts", "held"):
                rel[key] = {k: v for k, v in rel.get(key, {}).items() if k != "stations"}
        return rel

    def feature(identifier):
        f = real_feature(identifier)
        if identifier == TEST_ATLANTIC and f is not None:   # no box: Brockenhurst is not ruled out by it alone
            f = replace(f, record={k: v for k, v in f.record.items() if k != "bbox"})
        return f

    monkeypatch.setattr(s.store, "relationships", relationships)
    monkeypatch.setattr(s.store, "feature", feature)
    monkeypatch.setattr(s.store, "_relationships_many", lambda ids: {i: relationships(i) for i in ids})
    monkeypatch.delitem(s.store.packs[0].manifest, "islands_in_water", raising=False)   # a pack written before
    s.set_current_feature(TEST_ATLANTIC)
    yield s
    s.store.close()


def test_contains_and_down_list_an_island_in_the_sea(ocean):
    assert [n.area.id for n in ocean._contained(ocean.current_feature).get("stations", [])] == [BROCKENHURST]
    ocean.run("mode.toggle")
    lines = ocean.run("move.south").dialog["lines"]
    assert any(line.startswith("Railway stations") for line in lines), lines


def test_browse_lists_an_island_in_the_sea(ocean):
    lines = ocean.run("browse.open").dialog["lines"]
    assert any(line.startswith("Railway stations") for line in lines), lines
    assert [f.id for f in ocean.store.browse("stations", TEST_ATLANTIC)] == [BROCKENHURST]
