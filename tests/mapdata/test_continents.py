"""P3-T1e: the continents, built from the countries (DAT-12, DP174, DP88)."""
import pytest
import shapely

from mapdata.stages import continents

DATA = continents.load_settings()
ZONES = continents.zones(DATA)


def zone_name(lon: float, lat: float) -> str:
    p = shapely.Point(lon, lat)
    found = [c["name"] for c, g in ZONES if g.covers(p)]
    assert len(found) >= 1
    return found[0]


def test_the_continents_cover_the_world_once():
    """No land in no continent, and no land in two: the zones cover the whole world, without overlaps."""
    assert [c["name"] for c, _g in ZONES] == ["Antarctica", "South America", "Africa", "Europe", "North America",
                                              "Oceania", "Asia"]
    total = sum(g.area for _c, g in ZONES)
    assert total == pytest.approx(360 * 180, rel=1e-9)
    for i, (_a, ga) in enumerate(ZONES):
        for _b, gb in ZONES[i + 1:]:
            assert shapely.intersection(ga, gb).area < 1e-6
    for _c, g in ZONES:
        assert g.is_valid


@pytest.mark.parametrize("place, lon, lat, expected", [
    # The places the plan names.
    ("Moscow, Russia west of the Urals", 37.62, 55.75, "Europe"),
    ("Novosibirsk, Russia east of the Urals", 82.92, 55.03, "Asia"),
    ("Istanbul, the European side (Fatih)", 28.95, 41.01, "Europe"),
    ("Istanbul, the Asian side (Kadikoy)", 29.03, 40.99, "Asia"),
    ("Tenerife", -16.6, 28.3, "Africa"),
    # The dividing lines.
    ("Perm, west of the Urals", 56.23, 58.01, "Europe"),
    ("Chelyabinsk, east of the Urals", 61.4, 55.16, "Asia"),
    ("Orenburg, north of the Ural River", 55.1, 51.79, "Europe"),
    ("Aktobe, Kazakhstan east of the Ural River", 57.2, 50.28, "Asia"),
    ("Atyrau, west bank of the Ural River", 51.85, 47.11, "Europe"),
    ("Makhachkala, Dagestan, north of the Caucasus", 47.5, 42.98, "Europe"),
    ("Tbilisi, south of the Caucasus", 44.8, 41.7, "Asia"),
    ("Baku, south of the Caucasus", 49.87, 40.41, "Asia"),
    ("Quba, Azerbaijan north of the main ridge", 48.51, 41.36, "Europe"),
    ("Sochi, Russia on the Black Sea", 39.73, 43.6, "Europe"),
    ("Edirne, Turkey in Thrace", 26.56, 41.68, "Europe"),
    ("Ankara", 32.85, 39.93, "Asia"),
    ("Canakkale, the Asian side of the Dardanelles", 26.41, 40.14, "Asia"),
    ("Gelibolu, the European side of the Dardanelles", 26.67, 40.41, "Europe"),
    ("Cairo", 31.24, 30.04, "Africa"),
    ("Sinai, Saint Catherine", 33.95, 28.56, "Asia"),
    ("Ismailia, the west bank of the Suez Canal", 32.27, 30.59, "Africa"),
    ("Jayapura, Indonesia on New Guinea", 140.7, -2.53, "Oceania"),
    ("Sorong, Indonesia on New Guinea", 131.25, -0.88, "Oceania"),
    ("Ambon, Indonesia in Maluku", 128.18, -3.69, "Asia"),
    ("Kupang, Timor", 123.6, -10.17, "Asia"),
    ("Darwin", 130.84, -12.46, "Oceania"),
    ("Panama City", -79.52, 8.98, "North America"),
    ("Bogota", -74.07, 4.71, "South America"),
    ("Big Diomede, Russia", -169.06, 65.78, "Asia"),
    ("Little Diomede, USA", -168.93, 65.75, "North America"),
    # Distant parts, by where they are (DP88).
    ("Madeira", -16.9, 32.75, "Africa"),
    ("The Azores", -25.7, 37.8, "Europe"),
    ("Iceland", -19.0, 64.9, "Europe"),
    ("Svalbard", 15.6, 78.2, "Europe"),
    ("Franz Josef Land", 52.0, 80.6, "Europe"),
    ("Novaya Zemlya", 56.0, 74.0, "Europe"),
    ("Severnaya Zemlya", 97.0, 79.5, "Asia"),
    ("Greenland, Nuuk", -51.7, 64.18, "North America"),
    ("Greenland, the north-east", -20.0, 81.0, "North America"),
    ("Bermuda", -64.78, 32.3, "North America"),
    ("Hawaii", -155.5, 19.6, "Oceania"),
    ("Midway", -177.37, 28.21, "Oceania"),
    ("Attu, the far end of the Aleutians", 173.0, 52.9, "North America"),
    ("The Commander Islands, Russia", 166.0, 55.2, "Asia"),
    ("Wrangel Island", -179.5, 71.2, "Asia"),
    ("Chukotka east of 180", -173.2, 64.4, "Asia"),
    ("Guam", 144.8, 13.45, "Oceania"),
    ("Palau", 134.5, 7.5, "Oceania"),
    ("Taiwan", 121.0, 23.7, "Asia"),
    ("Easter Island", -109.35, -27.12, "Oceania"),
    ("The Galapagos", -90.5, -0.7, "South America"),
    ("The Falklands", -59.0, -51.7, "South America"),
    ("South Georgia", -36.5, -54.3, "South America"),
    ("Trinidad", -61.25, 10.45, "North America"),
    ("Aruba", -69.97, 12.52, "North America"),
    ("San Andres, Colombia", -81.7, 12.55, "North America"),
    ("Cape Verde", -23.5, 15.1, "Africa"),
    ("Madagascar", 46.9, -18.8, "Africa"),
    ("Reunion", 55.5, -21.1, "Africa"),
    ("Rodrigues", 63.42, -19.7, "Africa"),
    ("Kerguelen", 69.5, -49.3, "Africa"),
    ("Heard Island", 73.5, -53.1, "Oceania"),
    ("Socotra", 53.8, 12.5, "Asia"),
    ("The Maldives", 73.5, 4.2, "Asia"),
    ("Christmas Island", 105.7, -10.45, "Asia"),
    ("Cyprus", 33.4, 35.1, "Europe"),
    ("Crete", 24.9, 35.2, "Europe"),
    ("Malta", 14.45, 35.9, "Europe"),
    ("Tunis", 10.18, 36.8, "Africa"),
    ("Bouvet Island", 3.35, -54.42, "Antarctica"),
    ("The South Pole", 0.0, -89.9, "Antarctica"),
    ("Macquarie Island", 158.9, -54.6, "Oceania"),
    ("Beirut", 35.5, 33.89, "Asia"),
])
def test_each_place_is_in_its_continent(place, lon, lat, expected):
    assert zone_name(lon, lat) == expected, place


def zone_index(name):
    return next(i for i, (c, _g) in enumerate(ZONES) if c["name"] == name)


def run_assign(geom, wikidata="Q1", name="Test"):
    rec = {"id": "t", "layer": "countries", "name": name, "wikidata": wikidata}
    shapes = continents.continent_shapes([rec], [geom], DATA, say=lambda s: None, log=lambda s: None)
    return {c["name"]: s for c, s in shapes}


def test_a_country_in_two_continents_is_split_along_the_dividing_line():
    """A rough Russia, from 30 to 100 degrees east: the part west of the Urals is in Europe, the rest in Asia,
    and together they are the whole country."""
    russia = shapely.box(30, 52, 100, 64)
    got = run_assign(russia, wikidata="Q159", name="Russia")
    assert set(got) == {"Europe", "Asia"}
    assert got["Europe"].covers(shapely.Point(37.6, 55.75))
    assert got["Asia"].covers(shapely.Point(82.9, 55.0))
    assert got["Europe"].area + got["Asia"].area == pytest.approx(russia.area, rel=1e-9)


def test_a_country_not_named_for_splitting_goes_whole_to_one_continent():
    """The same shape as a country not in the list stays in one continent: the one with most of it."""
    got = run_assign(shapely.box(30, 52, 100, 64), wikidata="Q999")
    assert set(got) == {"Asia"}


def test_distant_parts_go_by_where_they_are_and_near_islands_stay():
    """A rough Spain, with the Balearics nearby and the Canary Islands far away (DP88)."""
    spain = shapely.MultiPolygon([shapely.box(-9, 36.5, 3, 43.5), shapely.box(2.5, 39.3, 3.4, 39.9),
                                  shapely.box(-18, 27.6, -13.4, 29.4)])
    got = run_assign(spain)
    assert set(got) == {"Europe", "Africa"}
    assert got["Africa"].covers(shapely.Point(-16.6, 28.3))
    assert got["Europe"].covers(shapely.Point(3.0, 39.6))


def test_a_sliver_of_a_split_country_stays_with_its_part():
    """A part of a split country that reaches a few hundred metres over a dividing line keeps that sliver."""
    thrace = shapely.box(26.2, 40.95, 29.03, 41.8)   # reaches a little past the Bosphorus line
    got = run_assign(thrace, wikidata="Q43", name="Turkey")
    assert set(got) == {"Europe"}


def test_the_world_has_no_land_in_two_continents():
    a = shapely.box(-10, 35, 60, 70)
    b = shapely.box(60, 35, 140, 70)
    got = run_assign(shapely.MultiPolygon([a, b]), wikidata="Q159", name="Russia")
    names = list(got)
    for i, n in enumerate(names):
        for m in names[i + 1:]:
            assert shapely.intersection(got[n], got[m]).area < 1e-9
