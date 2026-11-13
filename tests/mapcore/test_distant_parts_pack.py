"""DP191 in the test pack: French Guiana and Hawaii are areas of their own in the Countries layer.

Natural Earth's France, which the test pack's France takes over, holds French Guiana, and its United States
holds Hawaii. The PO decided that France and French Guiana count as separate countries (DP190, DP191): "where
am I" in Cayenne says French Guiana, not France, and France's neighbours are European. Details still says
whose it is.
"""
from types import SimpleNamespace

import pytest

from mapcore.describe import describer
from mapcore.session import MapSession

CAYENNE = {"lat": 4.93, "lon": -52.33, "zoom_m": 100000, "step_m": 1000}
HONOLULU = {"lat": 21.31, "lon": -157.86, "zoom_m": 100000, "step_m": 1000}
FRANCE = {"lat": 47.0, "lon": 2.5, "zoom_m": 100000, "step_m": 1000}


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


@pytest.fixture
def at(test_pack):
    made = []

    def make(place, **extra):
        s = MapSession(packs=[test_pack], saved_state=dict(place, **extra))
        s.start()
        made.append(s)
        return s
    yield make
    for s in made:
        s.store.close()


def country_here(s):
    return next(a for a in s.store.at(s.world.lat, s.world.lon) if a.layer == "countries")


def test_french_guiana_is_an_area_of_its_own_not_in_france(at):
    s = at(CAYENNE)
    here = s.store.at(s.world.lat, s.world.lon)
    assert [a.name for a in here if a.layer == "countries"] == ["French Guiana"]
    assert "France" not in [a.name for a in here]
    guiana = country_here(s)
    assert guiana.id == "part:osm:r2502058" and not guiana.record.get("parents")


def test_where_am_i_in_cayenne_says_french_guiana_once_and_not_france(at):
    s = at(CAYENNE)
    text = said(s.run("where.am_i"))
    assert text.split(", ").count("French Guiana") == 1
    assert "France" not in text


def test_frances_neighbours_are_european(at):
    s = at(FRANCE)
    france = country_here(s)
    assert france.name == "France"
    rel = s.store.relationships(france.id)
    names = {s.store.feature(i).name for i, *_ in rel.get("next", [])}
    assert {"Spain", "Belgium", "Germany"} <= names
    assert not names & {"Brazil", "Suriname", "French Guiana"}
    assert france.record["bbox"][0] > -10.0   # no longer reaching to South America (DP190)


def test_details_say_whose_a_distant_part_is(at):
    s = at(CAYENNE)
    assert s._type_text(country_here(s)) == "region of France"
    s = at(HONOLULU)
    hawaii = country_here(s)
    assert hawaii.name == "Hawaii"
    assert s._type_text(hawaii) == "region of the United States"


def test_details_of_the_region_in_a_distant_part_say_its_country(at):
    s = at(CAYENNE)
    region = next(a for a in s.store.at(s.world.lat, s.world.lon) if a.layer == "regions")
    assert region.name == "French Guiana"
    assert s._type_text(region) == "region of France"


def fake(record, name="French Guiana"):
    return SimpleNamespace(layer="countries", name=name, record=record)


def test_a_country_unit_says_its_type_and_sovereign(at):
    """A country unit (DP86) such as French Guiana in the world pack: "overseas region of France", as
    architecture 6.12 says. Gibraltar, a country, and metropolitan France are said as before."""
    s = at(FRANCE)
    assert s._type_text(fake({"type": "overseas region", "sovereign": "France", "tier": "country"})) == \
        "overseas region of France"
    assert s._type_text(fake({"type": "country", "sovereign": "United Kingdom", "tier": "country"},
                             "Gibraltar")) == "country"
    assert s._type_text(fake({"type": "metropolitan France", "sovereign": "France", "tier": "country"},
                             "France")) == "country"


def test_a_distant_part_with_no_region_is_part_of_its_country(at):
    s = at(FRANCE)
    rec = {"type": "distant part", "sovereign": "United States", "sovereign_id": "osm:r148838", "tier": "country"}
    assert s._type_text(fake(rec, "Wake Island")) == "part of the United States"


def area(name, km2, id_=None):
    return SimpleNamespace(name=name, area_km2=km2, id=id_ or name, record={})


def test_the_same_land_with_one_name_is_said_once():
    areas = [area("Hawaii", 16_635.0, "region"), area("Hawaii", 16_640.0, "part"), area("Oceania", 8.5e6)]
    assert describer.area_names(areas) == ["Hawaii", "Oceania"]


def test_a_part_named_from_its_region_or_a_unit_holding_its_region_is_said_once():
    part = area("French Guiana", 90_000.0, "part:osm:r2502058")
    part.record = {"named_from": "osm:r2502058"}
    region = area("French Guiana", 83_000.0, "osm:r2502058")
    assert describer.area_names([region, part]) == ["French Guiana"]
    unit = area("French Guiana", 90_000.0, "osm:r1260551")
    region.record = {"parent": "osm:r1260551"}
    assert describer.area_names([region, unit]) == ["French Guiana"]


def test_two_areas_of_one_name_and_different_sizes_are_both_said():
    """Luxembourg the canton and Luxembourg the country are different land."""
    areas = [area("Luxembourg", 238.0, "canton"), area("Luxembourg", 2_586.0, "country")]
    assert describer.area_names(areas) == ["Luxembourg", "Luxembourg"]
