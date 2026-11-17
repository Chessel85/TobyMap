"""The territories list (P3-T24c, P3-T24d, DP199) and enclaves and exclaves (P3-T24g, DP207), in the build."""
import pytest
import shapely

from mapdata.stages import enclaves, territories


def _entry(**kw):
    e = {"place": "Jersey", "wikidata": "Q785", "sovereign": "the British Crown", "status": "Crown Dependency",
         "say_sovereign": False}
    e.update(kw)
    return e


# The territories list -------------------------------------------------------------------------------------------

def test_the_territories_list_as_it_is_passes_its_own_check():
    entries = territories.load()
    assert len(entries) >= 50
    assert territories.check(entries) == []
    assert {e["status"] for e in entries} <= set(territories.STATUSES)
    grey = [e for e in entries if e.get("grey")]
    assert grey and all(e.get("note") for e in grey)


@pytest.mark.parametrize("change, words", [
    ({"status": "colony"}, "the status 'colony' is not one of"),
    ({"say_sovereign": None}, "has no say_sovereign"),
    ({"say_sovereign": "maybe"}, "say_sovereign must be yes or no"),
    ({"wikidata": None}, "needs wikidata or id"),
    ({"colour": "red"}, "a field TobyMap does not know: colour"),
])
def test_a_mistake_stops_the_build_naming_the_entry(change, words):
    with pytest.raises(territories.TerritoryError) as e:
        territories.check([_entry(), _entry(place="Guernsey", **change)])
    assert "entry 2, Guernsey" in str(e.value) and words in str(e.value)


def test_in_a_build_of_the_whole_world_every_entry_must_be_found():
    records = [{"id": "osm:r1", "layer": "countries", "name": "Jersey", "wikidata": "Q785"}]
    assert territories.check([_entry()], records, whole_world=True) == []
    missing = [_entry(place="Guam", wikidata="Q16635")]
    assert territories.check(missing, records) == ["Guam"]   # a trial lists it
    with pytest.raises(territories.TerritoryError, match="Guam: Q16635 is not found"):
        territories.check(missing, records, whole_world=True)


def test_each_named_area_gets_its_status_and_sovereign_found_by_wikidata_or_name():
    records = [{"id": "osm:r1", "layer": "countries", "name": "Spain", "wikidata": "Q29"},
               {"id": "part:osm:r2", "layer": "countries", "name": "Canary Islands", "wikidata": "Q5813",
                "type": "distant part"},
               {"id": "osm:r3", "layer": "countries", "name": "United Kingdom", "wikidata": "Q145"},
               {"id": "osm:r4", "layer": "countries", "name": "Falkland Islands", "wikidata": "Q9648"}]
    entries = [_entry(place="Canary Islands", wikidata="Q5813", sovereign="Spain", sovereign_wikidata="Q29",
                      status="integral part", say_sovereign=True),
               _entry(place="Falkland Islands", wikidata="Q9648", sovereign="United Kingdom",
                      status="overseas territory", claimed_by="Argentina")]
    assert territories.apply(entries, records, line=lambda _t: None) == 2
    canary, falklands = records[1], records[3]
    assert canary["status"] == "integral part" and canary["say_sovereign"] is True and canary["sovereign_id"] == "osm:r1"
    assert falklands["say_sovereign"] is False and falklands["sovereign_id"] == "osm:r3"   # by name
    assert falklands["claimed_by"] == "Argentina"


def test_a_territory_mapped_inside_its_country_becomes_an_area_of_its_own():
    """Puerto Rico: OpenStreetMap maps it as a region of the United States."""
    records = [{"id": "osm:r1", "layer": "countries", "name": "United States", "colour": 1},
               {"id": "osm:r2", "layer": "regions", "name": "Puerto Rico", "wikidata": "Q1183", "parent": "osm:r1"}]
    shapes = {0: shapely.box(0, 0, 10, 10), 1: shapely.box(8, 0, 10, 2)}
    entry = _entry(place="Puerto Rico", wikidata="Q1183", sovereign="United States", status="overseas territory",
                   separate=True)
    new, changed, reparent = territories.separate([entry], records, lambda idx: {i: shapes[i] for i in idx},
                                                  line=lambda _t: None)
    (rec, land), = new
    assert rec["id"] == "part:osm:r2" and rec["layer"] == "countries" and rec["name"] == "Puerto Rico"
    assert land.area == pytest.approx(4.0) and changed[0].area == pytest.approx(96.0)
    assert reparent == {1: "part:osm:r2"}


# Enclaves and exclaves -------------------------------------------------------------------------------------------

def _countries():
    """Spain with Llivia inside France, and an island of Spain's in the sea, which is neither."""
    spain = shapely.MultiPolygon([shapely.box(0, 0, 1, 1), shapely.box(1.5, 1.4, 1.52, 1.42),
                                  shapely.box(-0.5, -0.5, -0.45, -0.45)])
    france = shapely.difference(shapely.box(0, 1, 3, 3), shapely.box(1.5, 1.4, 1.52, 1.42))
    records = [{"id": "es", "layer": "countries", "name": "Spain"}, {"id": "fr", "layer": "countries", "name": "France"},
               {"id": "t", "layer": "towns", "name": "Llivia", "population": 1500}]
    return records, [spain, france, shapely.Point(1.51, 1.41)]


def test_a_part_inside_another_country_is_an_enclave_and_an_exclave_and_an_island_is_neither():
    records, geoms = _countries()
    found = enclaves.find(records, geoms)
    (f,) = found
    assert f["sovereign"] == 0 and set(f["beside"]) == {1} and f["enclave"] and not f["coast"]
    new = enclaves.apply(records, geoms, found, log=lambda _t: None)
    (rec, _shape), = new
    assert rec["layer"] == "exclaves" and rec["name"] == "Llivia" and rec["type"] == "enclave"
    assert rec["exclave"]["beside"] == ["fr"] and rec["exclave"]["sovereign"] == "Spain"
    assert records[0]["exclaves"] == [rec["id"]] and records[1]["enclaves"] == [rec["id"]]


def test_a_part_the_sea_cuts_off_is_not_an_exclave_unless_it_is_a_small_part_of_a_larger_coast():
    # A large part beside a small neighbour, across the sea from its main part: not an exclave.
    home = shapely.box(0, 0, 1, 1)
    island = shapely.box(5, 0, 6, 1)
    records = [{"id": "a", "layer": "countries", "name": "A"}, {"id": "b", "layer": "countries", "name": "B"}]
    geoms = [shapely.MultiPolygon([home, island]), shapely.box(6, 0, 6.5, 1)]
    assert enclaves.find(records, geoms) == []
    # A town-sized part on a much larger country's coast, as Ceuta is: an exclave, on the coast.
    town = shapely.box(5, 0.4, 5.02, 0.42)
    geoms = [shapely.MultiPolygon([home, town]), shapely.difference(shapely.box(5.02, -2, 9, 3), town)]
    (f,) = enclaves.find(records, geoms)
    assert f["coast"] and not f["enclave"]


def test_a_whole_country_inside_another_is_an_enclave():
    records = [{"id": "it", "layer": "countries", "name": "Italy"}, {"id": "sm", "layer": "countries", "name": "San Marino"}]
    san_marino = shapely.box(1, 1, 1.1, 1.1)
    geoms = [shapely.difference(shapely.box(0, 0, 3, 3), san_marino), san_marino]
    found = enclaves.find(records, geoms)
    assert any(f.get("whole") and f["sovereign"] == 1 for f in found)
    enclaves.apply(records, geoms, found, log=lambda _t: None)
    assert records[1]["enclave_in"] == ["it"] and records[0]["enclaves"] == ["sm"]


def test_an_exclave_is_named_by_hand_where_its_largest_place_is_a_village():
    records, geoms = _countries()
    records[2]["layer"] = "villages"   # not a town
    found = enclaves.find(records, geoms)
    new = enclaves.apply(records, geoms, found, {"names": [{"point": [1.51, 1.41], "name": "Llívia"}]},
                         log=lambda _t: None)
    assert new[0][0]["name"] == "Llívia"
    new = enclaves.apply(*_countries()[:2], enclaves.find(*_countries()[:2]),
                         {"names": [{"box": [1.4, 1.3, 1.6, 1.5], "name": "X", "of": "France"}]}, log=lambda _t: None)
    assert new[0][0]["name"] == "Llivia"   # the box is for France's, not Spain's
