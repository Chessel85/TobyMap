"""Search across packs (P4-T3c; SRB-1, SRB-2, PLT-4, PCK-2, AD-14).

The test pack (a world pack) and the regional test pack, test-region, are opened together. One search reads both
packs' search records, and a feature both packs hold, by the identifier the match stage gave it, is listed once:
with the name, description and point of the pack holding the whole feature, the best match either pack's row
gives, and the most importance either gives.
"""
from dataclasses import replace

import pytest

from mapcore.packs.pack import Pack
from mapcore.store import Store

HAMPSHIRE = "osm:r172799"             # the regional pack holds only part of it
ITCHEN = "osm:r7703089"               # matched by Wikidata; the regional pack holds part of it
NEW_FOREST_PARK = "osm:r2678988"      # the regional pack holds all of it
LYMINGTON_PARISH = "osm:r3949115"     # Lymington and Pennington, only in the regional pack
SOUTHAMPTON_CENTRAL = "osm:n638908005"   # a station: the regional pack has no stations
WORDS = ("hampshire", "itchen", "new forest", "lymington", "southampton", "england", "winchester", "forest")


@pytest.fixture(scope="module")
def packs(test_pack, test_region_pack):
    world, region = Pack(test_pack, check_app=False), Pack(test_region_pack, check_app=False)
    yield world, region
    world.close()
    region.close()


@pytest.fixture(scope="module")
def both(packs):
    return Store(list(packs))


@pytest.fixture(scope="module")
def alone(packs):
    world, region = packs
    return Store([world]), Store([region])


def _one(results, identifier):
    got = [f for f in results if f.id == identifier]
    assert len(got) == 1, [(f.id, f.name) for f in results]
    return got[0]


def test_a_feature_both_packs_hold_is_listed_once(both):
    for text in WORDS:
        ids = [f.id for f in both.search(text, limit=200)]
        assert len(ids) == len(set(ids)), text


def test_no_feature_either_pack_finds_is_lost(both, alone):
    for text in WORDS:
        expected = {f.id for store in alone for f in store.search(text, limit=500)}
        assert {f.id for f in both.search(text, limit=500)} == expected, text


def test_a_part_gives_way_to_the_whole_features_row(both, alone):
    world, region = alone
    assert region.feature(HAMPSHIRE).record.get("partial")
    got = _one(both.search("hampshire"), HAMPSHIRE)
    whole = _one(world.search("hampshire"), HAMPSHIRE)
    assert both.coverage(got.pack) is None   # the world pack's
    assert got.description == whole.description == "Hampshire, England, United Kingdom"
    assert (got.lat, got.lon, got.importance) == (whole.lat, whole.lon, whole.importance)
    assert both.search("hampshire")[0].id == HAMPSHIRE
    river = _one(both.search("itchen"), ITCHEN)
    assert both.coverage(river.pack) is None and river.importance == _one(world.search("itchen"), ITCHEN).importance


def test_a_feature_the_regional_pack_holds_whole_has_its_row_and_the_most_importance(both, alone):
    world, region = alone
    assert not region.feature(NEW_FOREST_PARK).record.get("partial")
    got = _one(both.search("new forest"), NEW_FOREST_PARK)
    own = _one(region.search("new forest"), NEW_FOREST_PARK)
    other = _one(world.search("new forest"), NEW_FOREST_PARK)
    assert both.coverage(got.pack) is not None
    assert got.description == own.description == "New Forest National Park, England, United Kingdom"
    # the test region is built without Wikidata, so the world pack weighs the park more
    assert got.importance == max(own.importance, other.importance) == other.importance


def test_features_only_one_pack_holds_are_found(both):
    parish = _one(both.search("lymington"), LYMINGTON_PARISH)
    assert both.coverage(parish.pack) is not None
    station = _one(both.search("southampton central"), SOUTHAMPTON_CENTRAL)
    assert both.coverage(station.pack) is None


def test_the_best_match_of_any_pack_counts(both):
    """A name only one pack has finds the feature as well as it would alone (the rule on its own)."""
    rows = {}
    for f in both.search("hampshire", limit=200):
        if f.id == HAMPSHIRE:
            rows = f
    regional = next(p for p in range(len(both.packs)) if both.coverage(p) is not None)
    world = next(p for p in range(len(both.packs)) if both.coverage(p) is None)
    weak = replace(rows, pack=world, level=1, similarity=0.6, via="")
    strong = replace(rows, pack=regional, level=4, similarity=1.0, via="Hants", importance=140,
                     description="Hampshire")
    order, got = both._one_result({regional: ((), strong, 0), world: ((), weak, 0)})
    assert (got.pack, got.description) == (world, weak.description)
    assert (got.level, got.similarity, got.via, got.importance) == (4, 1.0, "Hants", weak.importance)
    assert order[:3] == (-4, -1.0, -weak.importance)


def test_narrowed_to_a_county_a_regional_parish_is_inside_the_worlds_county(both):
    found = both.search("lymington", inside=HAMPSHIRE, limit=50)
    assert LYMINGTON_PARISH in {f.id for f in found}
    assert len({f.id for f in found}) == len(found)


def test_the_order_the_packs_are_given_makes_no_difference(packs, both):
    world, region = packs
    other = Store([region, world])
    for text in WORDS:
        assert [(f.id, f.description, f.importance) for f in other.search(text, limit=50)] == \
            [(f.id, f.description, f.importance) for f in both.search(text, limit=50)], text


def test_nearness_ranks_a_merged_feature_by_its_whole_features_point(both):
    here = (51.0590, -1.3074)   # Winchester
    near = both.search("hampshire", here=here)
    assert near[0].id == HAMPSHIRE and both.coverage(near[0].pack) is None


def test_a_feature_both_packs_hold_is_ranked_by_its_whole_features_row_however_few_are_read(both):
    """_ranked reads the records of a feature several packs found only when it may come next; its place is the
    whole feature's row's, not the best place a part's row would give."""
    hampshire = _one(both.search("hampshire"), HAMPSHIRE)
    regional = next(p for p in range(len(both.packs)) if both.coverage(p) is not None)
    world = next(p for p in range(len(both.packs)) if both.coverage(p) is None)
    whole = replace(hampshire, pack=world, level=4, similarity=1.0, importance=400)
    part = replace(hampshire, pack=regional, level=4, similarity=1.0, importance=100)
    other = replace(hampshire, pack=world, id="osm:test-between", name="Hampshire", importance=450)
    best = {
        HAMPSHIRE: {regional: ((), part, 100), world: ((), whole, 0)},   # the part's row is nearer: 500 at best
        other.id: {world: (both._one_result({world: ((), other, 0)})[0], other, 0)},   # 450
    }
    got = list(both._ranked(best))
    assert [f.id for f in got] == [other.id, HAMPSHIRE]
    assert got[1].pack == world and got[1].importance == 400
