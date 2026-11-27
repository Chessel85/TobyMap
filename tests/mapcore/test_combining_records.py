"""Features and relationships merged across packs (P4-T3b; PLT-4, PCK-2, AD-14, architecture 6.7 and 6.8).

The test pack (a world pack) and the regional test pack, test-region, are opened together. The match stage gave the
regional features the world pack's identifiers, so a feature both hold is one feature: its record is the whole
feature's, the world's where the regional pack holds only part of it (Hampshire, cut to the covered pack tiles), and
the regional pack's where it holds all of it; Within, Contains and Bordering give one Hampshire; and a parish only
the regional pack holds sits under the world pack's Hampshire.
"""
import pytest

from mapcore.packs.pack import Pack
from mapcore.store import Store
from mapcore.store.packs_combined import _ordered_merge, merge_records, merge_relationships

WINCHESTER = (51.0590, -1.3074)
HAMPSHIRE = "osm:r172799"
ENGLAND = "osm:r58447"
UK = "osm:r62149"
NEW_FOREST_PARK = "osm:r2678988"
LYMINGTON_PARISH = "osm:r3949115"     # Lymington and Pennington, only in the regional pack
NEW_FOREST_DISTRICT = "osm:r129306"   # only in the regional pack
ITCHEN = "osm:r7703089"               # matched by Wikidata, with its own id kept as an alias
ITCHEN_ALIAS = "osm:w44911161"


@pytest.fixture(scope="module")
def packs(test_pack, test_region_pack):
    world, region = Pack(test_pack, check_app=False), Pack(test_region_pack, check_app=False)
    yield world, region
    world.close()
    region.close()


@pytest.fixture(scope="module")
def both(test_pack, test_region_pack):
    store = Store([Pack(test_pack, check_app=False), Pack(test_region_pack, check_app=False)])
    yield store
    store.close()


def _regional(store) -> int:
    return next(p for p in range(len(store.packs)) if store.coverage(p) is not None)


# The rules, on their own ------------------------------------------------------------------------------------------

def test_a_merged_record_keeps_the_first_and_adds_what_only_others_have():
    first = {"id": "a", "area_km2": 10.0, "partial": True, "aliases": ["x"]}
    got = merge_records(first, [{"id": "a", "area_km2": 2.0, "facts": {"f": 1}, "partial": True, "aliases": ["y"]}])
    assert got["area_km2"] == 10.0 and got["facts"] == {"f": 1} and got["aliases"] == ["x", "y"]
    assert merge_records({"id": "a"}, [{"id": "a", "partial": True}]).get("partial") is None


def test_the_authority_answers_alone_for_its_layers():
    layer = {"county": "counties", "town": "towns", "parish": "parishes", "country": "countries"}.get
    first = {"in": ["country"], "counts": {"parishes": 5}, "held": {"parishes": 5}}
    world = {"in": ["country"], "overlaps": [["county", 0.5, 0.5]], "counts": {"towns": 2, "counties": 1},
             "held": {"towns": 2}, "next": [["town", 3.0]], "outline_km": 99.0}
    got = merge_relationships(first, [(world, False)], frozenset({"counties", "parishes", "countries"}), layer)
    assert got["counts"] == {"parishes": 5, "towns": 2}     # the world's counties are the regional pack's to say
    assert got["held"] == {"parishes": 5, "towns": 2}
    assert "overlaps" not in got                            # a county: the regional pack's layer
    assert got["next"] == [["town", 3.0]] and got["outline_km"] == 99.0


def test_a_part_says_nothing_about_where_the_whole_lies():
    layer = {"district": "districts", "county": "counties"}.get
    first = {"in": ["county"], "outline_km": 100.0}
    part = {"in": ["district"], "counts": {"parishes": 3, "counties": 1}, "outline_km": 4.0, "crosses": ["district"]}
    got = merge_relationships(first, [(part, True)], frozenset({"counties"}), layer)
    assert got["in"] == ["county"] and got["outline_km"] == 100.0
    assert got["counts"] == {"parishes": 3}                 # only the layers the first pack does not have
    assert got["crosses"] == ["district"]


def test_a_lines_areas_stay_in_order_from_its_start():
    assert _ordered_merge(["uk", "england", "hampshire", "east"], ["uk", "england", "hampshire", "district",
                                                                    "parish", "east"]) == \
        ["uk", "england", "hampshire", "district", "parish", "east"]
    assert _ordered_merge(["a", "b"], ["x", "a", "y"]) == ["x", "a", "y", "b"]


# One Hampshire ------------------------------------------------------------------------------------------------------

def test_a_partial_regional_record_yields_to_the_worlds(both, packs):
    world, region = packs
    assert region.feature_by_id(HAMPSHIRE).get("partial")
    got = both.feature(HAMPSHIRE)
    whole = world.feature_by_id(HAMPSHIRE)
    assert got.pack == both._world
    assert got.area_km2 == whole["area_km2"] and got.record["bbox"] == whole["bbox"]
    assert not got.record.get("partial")


def test_within_lists_hampshire_once_with_its_whole_area(both, packs):
    world, _region = packs
    found = both.at(*WINCHESTER)
    hampshire = [a for a in found if a.id == HAMPSHIRE]
    assert len(hampshire) == 1
    assert hampshire[0].area_km2 == world.feature_by_id(HAMPSHIRE)["area_km2"]
    assert [a.id for a in found].count(UK) == 1
    region = _regional(both)
    assert next(a for a in found if a.id == "osm:r127238").pack == region   # the district, only regional


def test_bordering_is_the_whole_countys(both, packs):
    world, _region = packs
    rel = both.relationships(HAMPSHIRE)
    assert rel["next"] == world.relationships(HAMPSHIRE)["next"]
    assert rel["outline_km"] == world.relationships(HAMPSHIRE)["outline_km"]
    assert rel["coast"] == world.relationships(HAMPSHIRE)["coast"]
    assert rel["in"] == [ENGLAND, UK]


def test_contains_of_hampshire_has_both_packs_features(both):
    counts, held = both.contents_counts(HAMPSHIRE)
    assert counts["parishes"] == 5 and counts["districts"] == 2      # only the regional pack has them
    assert counts["stations"] == 1                                   # only the world pack has them
    assert counts["lakes"] == 1                                      # the whole county's, the world's
    assert "countries" not in counts                                 # the cut part is no country's holder
    assert held["stations"] == 1
    assert [f.id for f in both.browse("parishes", HAMPSHIRE)] and \
        len(both.browse("parishes", HAMPSHIRE)) == 5
    assert len(both.browse("stations", HAMPSHIRE)) == 1


# A parish under the world pack's county -----------------------------------------------------------------------------

def test_a_parish_sits_under_the_world_packs_county(both):
    rel = both.relationships(LYMINGTON_PARISH)
    assert rel["in"][:4] == [NEW_FOREST_DISTRICT, HAMPSHIRE, ENGLAND, UK]
    assert both.feature(rel["in"][1]).pack == both._world


def test_a_regional_feature_is_carried_on_above_the_top_of_its_own(test_pack, test_region_pack):
    """Within for a feature only the regional pack holds: its own parents, then the world's holders of the top one.
    The test pack puts nothing above the United Kingdom, so a world holder of it is added here."""
    world = Pack(test_pack, check_app=False)
    stored = world.relationships

    def relationships(identifier):
        rel = stored(identifier)
        return {**rel, "in": ["test:continent"]} if identifier == UK else rel

    world.relationships = relationships
    store = Store([world, Pack(test_region_pack, check_app=False)])
    try:
        assert store.relationships(LYMINGTON_PARISH)["in"][-2:] == [UK, "test:continent"]
        assert store.relationships(HAMPSHIRE)["in"] == [ENGLAND, UK]   # the world's, which knows the whole county
    finally:
        store.close()


def test_hierarchy_up_from_the_parish_reaches_the_world_packs_county(test_pack, test_region_pack):
    from mapcore.session import MapSession

    store = Store([Pack(test_pack, check_app=False), Pack(test_region_pack, check_app=False)])
    s = MapSession(store=store, saved_state={"lat": WINCHESTER[0], "lon": WINCHESTER[1], "zoom_m": 1000,
                                              "step_m": 10})
    try:
        s.start()
        district = store.feature(NEW_FOREST_DISTRICT)
        parents = s._parents(district)
        assert [p.id for p in parents] == [HAMPSHIRE]
        assert parents[0].pack == store._world
    finally:
        store.close()


# A whole regional record wins -----------------------------------------------------------------------------------------

def test_a_whole_regional_record_wins(both, packs):
    world, region = packs
    got = both.feature(NEW_FOREST_PARK)
    assert got.pack == _regional(both)
    assert got.area_km2 == region.feature_by_id(NEW_FOREST_PARK)["area_km2"]
    assert got.record["wikidata"] == region.feature_by_id(NEW_FOREST_PARK)["wikidata"]
    rel = both.relationships(NEW_FOREST_PARK)
    assert HAMPSHIRE in rel["in"] and ENGLAND in rel["in"]
    overlapped = [i for i, *_ in rel.get("overlaps", ())]
    assert ENGLAND not in overlapped and HAMPSHIRE not in overlapped   # the regional pack says it is inside them
    assert rel["counts"].get("stations") == 1                           # the world's, a layer only it has
    assert rel["counts"].get("parishes") == region.relationships(NEW_FOREST_PARK)["counts"]["parishes"]


def test_a_partial_lines_areas_keep_their_order(both, packs):
    world, region = packs
    rel = both.relationships(ITCHEN)
    whole = world.relationships(ITCHEN)["crosses"]
    assert [i for i in rel["crosses"] if i in whole] == whole
    assert "osm:r127238" in rel["crosses"]                              # the Winchester district, regional
    assert rel["in"] == world.relationships(ITCHEN)["in"]              # the part's "in" is not the whole's


# Aliases ------------------------------------------------------------------------------------------------------------

def test_an_alias_finds_the_feature(both):
    assert both.feature(ITCHEN_ALIAS).id == ITCHEN
    assert both.relationships(ITCHEN_ALIAS) == both.relationships(ITCHEN)
    assert both.feature("osm:no-such-feature") is None
    assert both.relationships("osm:no-such-feature") == {}
