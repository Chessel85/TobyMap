"""P3-T33a: the importance search gives each feature (SRB-1, architecture 7.9).

The records are cut down from the world pack of 20 November, with the counts of Wikimedia sites the wikidata stage
kept for them. The test of the whole order, from where you are, is in tests/mapcore/test_search.py.
"""
from mapdata.stages import search_index

W = search_index.SETTINGS["weights"]


def importance(rec, sites=None):
    return search_index.importance(rec, sites, W)


def road(width_km):
    return {"layer": "roads", "rank": 8, "area_km2": 0.0, "width_km": width_km}


def test_a_line_with_no_length_is_as_important_as_it_is_long():
    # Every road and railway scored 19 on the world pack, so the M3 in Malawi came before the M3 in Hungary.
    short, long_ = importance(road(1.5)), importance(road(234.0))
    assert short < long_
    assert importance(road(0.0)) < short
    # A length from Wikidata still counts before the extent
    river = {"layer": "rivers", "rank": 8, "area_km2": 0.0, "width_km": 10.0, "facts": {"length_km": {"value": 1232.7}}}
    assert importance(river) == importance({**river, "width_km": 2000.0})


WINCHESTER_ENGLAND = {"layer": "towns", "rank": 8, "area_km2": 0.0, "width_km": 0.0, "type": "city",
                      "facts": {"population": {"value": 35200}}}
WINCHESTER_VIRGINIA = {"layer": "counties", "rank": 6, "area_km2": 23.871, "width_km": 8.198,
                       "facts": {"population": {"value": 28120}}}


def test_a_city_is_weighed_fairly_against_a_county():
    # Winchester in England, a city with more people and more Wikimedia sites, came after Winchester in Virginia,
    # a county-level city, as a town is a point with no area and its layer's rank is lower.
    assert importance(WINCHESTER_ENGLAND, 88) > importance(WINCHESTER_VIRGINIA, 50)
    # Luxembourg the city before Luxembourg the Belgian province: half the people, twice the sites
    city = {"layer": "towns", "rank": 8, "area_km2": 0.0, "facts": {"population": {"value": 137678}}}
    province = {"layer": "counties", "rank": 6, "area_km2": 4459.4, "facts": {"population": {"value": 296008}}}
    assert importance(city, 175) > importance(province, 85)
    # A county of more note still wins: Paris the county over Paris in Texas
    paris = {"layer": "counties", "rank": 6, "area_km2": 105.4, "facts": {"population": {"value": 2_104_000}}}
    texas = {"layer": "towns", "rank": 8, "area_km2": 0.0, "facts": {"population": {"value": 24_476}}}
    assert importance(paris, 300) > importance(texas, 60) + 100


def test_a_country_still_comes_before_a_region_of_its_name():
    country = {"layer": "countries", "rank": 2, "area_km2": 69646.9, "facts": {"population": {"value": 3929581}}}
    state = {"layer": "regions", "rank": 4, "area_km2": 152540.5, "facts": {"population": {"value": 10711908}}}
    assert importance(country, 299) > importance(state, 233)


def test_a_feature_without_people_is_weighed_on_what_it_has():
    # A river has no people, so towns weighed by their people must not bury it: the River Thames, with 132 sites,
    # before Thames in New Zealand, a town of 7,380 people with 15.
    river = {"layer": "rivers", "rank": 8, "area_km2": 0.0, "width_km": 187.7, "facts": {"length_km": {"value": 334.0}}}
    town = {"layer": "towns", "rank": 8, "area_km2": 0.0, "facts": {"population": {"value": 7380}}}
    assert importance(river, 132) > importance(town, 15) + 50
    # Still from 0 to 1,000
    assert 0 <= importance(road(0.0)) and importance({"layer": "countries", "rank": 1, "area_km2": 1e8,
                                                      "population": 1e10}, 1000) == 1000
