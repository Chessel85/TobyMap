"""Space names a town you are near (P3-T28p, Q6, DP206, LOC-5): "Near Newport. Isle of Wight, England, United Kingdom".

A town's reach, the distance within which it counts as near, grows with its population, or with its type where
the pack has no population for it. Of the towns near, the one nearest for its reach is said.
"""
from types import SimpleNamespace

import pytest

from mapcore.describe import describer, say
from mapcore.session import MapSession

NEWPORT = (50.7003707, -1.2952039)   # Newport on the Isle of Wight, a town with no population in the test pack
PARIS = (48.8534951, 2.3483915)      # Paris, a city of 2.1 million
SAO_PAULO = (-23.5506507, -46.6333824)   # São Paulo the city, inside São Paulo the state


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


def _town(name, kind="town", population=None, facts=None):
    record = {"id": "t:" + name, "layer": "towns", "type": kind}
    if population is not None:
        record["population"] = population
    if facts is not None:
        record["facts"] = {"population": {"value": facts, "source": "Wikidata"}}
    return SimpleNamespace(name=name, id=record["id"], record=record)


def _near(town, metres):
    return SimpleNamespace(area=town, distance_m=metres)


def test_the_approved_wording_of_near():
    assert say("place.near", name="Winchester", place="Hampshire, England, United Kingdom") \
        == "Near Winchester. Hampshire, England, United Kingdom"


def test_a_towns_reach_grows_with_its_population_between_2_and_30_kilometres():
    reach = describer.town_reach_m
    assert reach(_town("Small", population=3_000).record) == 2_000          # at least 2 km
    assert reach(_town("Winchester", "city", facts=35_200).record) == pytest.approx(4_690, abs=10)
    assert reach(_town("Southampton", "city", facts=271_173).record) == pytest.approx(13_018, abs=10)
    assert reach(_town("London", "city", facts=8_799_728).record) == 30_000   # at most 30 km
    # Wikidata's population is used before OpenStreetMap's.
    assert reach(_town("Both", population=1_000_000, facts=40_000).record) == 5_000


def test_without_a_population_the_type_gives_the_reach_and_other_types_are_not_near():
    assert describer.town_reach_m(_town("Newport").record) == 3_000
    assert describer.town_reach_m(_town("A city", "city").record) == 8_000
    for kind in ("village", "hamlet", "suburb", "neighbourhood"):
        assert describer.town_reach_m(_town("Somewhere", kind, population=50_000).record) is None


def test_the_town_nearest_for_its_reach_is_said():
    southampton = _town("Southampton", "city", facts=271_173)   # reach 13 km
    eastleigh = _town("Eastleigh", population=78_716)             # reach 7 km
    # In Eastleigh's centre, 8 km from Southampton's: Eastleigh, though Southampton is larger.
    assert describer.near_town([_near(southampton, 8_000), _near(eastleigh, 500)], []) is eastleigh
    # Halfway, Southampton is nearer for its reach.
    assert describer.near_town([_near(southampton, 4_000), _near(eastleigh, 4_000)], []) is southampton
    # Beyond every reach: none.
    assert describer.near_town([_near(southampton, 14_000), _near(eastleigh, 7_100)], []) is None
    assert describer.near_town([], []) is None


def test_a_town_with_the_name_of_an_area_said_is_not_said_again():
    paris = _town("Paris", "city", population=2_133_111)
    assert describer.near_town([_near(paris, 1_000)], ["Paris", "Île-de-France", "France"]) is None
    assert describer.near_town([_near(paris, 1_000)], ["Île-de-France", "France"]) is paris


@pytest.fixture
def at(test_pack):
    sessions = []

    def make(lat, lon, zoom_m=25000):
        s = MapSession(packs=[test_pack], saved_state={"lat": lat, "lon": lon, "zoom_m": zoom_m, "step_m": 1000})
        s.start()
        sessions.append(s)
        return s
    yield make
    for s in sessions:
        s.store.close()


def test_space_names_the_town_you_are_near(at):
    s = at(NEWPORT[0] + 0.01, NEWPORT[1])   # about 1.1 km north of Newport
    place = s._place_text()
    assert spoken(s.press("Space")) == ["Near Newport. " + place]
    assert place.startswith("Isle of Wight")


def test_space_says_only_the_place_beyond_every_towns_reach(at):
    s = at(NEWPORT[0] - 0.05, NEWPORT[1] + 0.1)   # about 9 km south-east of Newport, beyond its 3 km
    assert spoken(s.press("Space")) == [s._place_text()]


def test_a_large_city_is_near_further_out(at):
    s = at(PARIS[0] + 0.1, PARIS[1])   # 11 km north of Paris, within its 30 km
    assert spoken(s.press("Space")) == ["Near Paris. " + s._place_text()]


def test_a_town_of_the_same_name_as_an_area_you_are_in_is_not_said_twice(at):
    s = at(*SAO_PAULO)
    place = s._place_text()
    assert place.startswith("São Paulo")
    assert spoken(s.press("Space")) == [place]


def test_no_town_is_named_when_the_towns_layer_is_off_or_out_of_its_zoom_range(at):
    s = at(NEWPORT[0] + 0.01, NEWPORT[1])
    s.run("layers.set", layer="towns", field="on", value=False)
    assert spoken(s.press("Space")) == [s._place_text()]
    s.run("layers.set", layer="towns", field="on", value=True)
    s.world.zoom_index = s.world.zoom_list.index(500000)   # beyond the towns' 250 km (DP160, ANN-7)
    assert spoken(s.press("Space")) == [s._place_text()]


def test_only_space_names_the_town_not_a_step(at):
    s = at(NEWPORT[0] + 0.01, NEWPORT[1])
    s.world.lat -= 0.0001
    assert not any(t.startswith("Near") for t in spoken(s._arrived(s._moved())))
