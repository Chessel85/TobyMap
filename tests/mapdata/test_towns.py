"""P3-T1j: cities and towns as places, with their population from OSM and the areas each is in (DAT-1)."""
import shapely

from mapdata.stages import osm_places, write


def test_a_population_is_read_from_the_usual_ways_of_writing_it():
    assert osm_places.population("12345") == 12345
    assert osm_places.population("12 345") == 12345
    assert osm_places.population("2,161,000") == 2161000
    assert osm_places.population("1.234.567") == 1234567
    assert osm_places.population("about 5000") is None
    assert osm_places.population("") is None
    assert osm_places.population(None) is None


def test_a_place_has_the_areas_it_is_in_in_the_order_given():
    """Winchester is in Europe, the United Kingdom, England and Hampshire; a place at sea is in none."""
    areas = [("counties", "osm:r1", shapely.box(0, 0, 1, 1)),
             ("countries", "osm:r62149", shapely.box(-5, -5, 5, 5)),
             ("regions", "osm:r58447", shapely.box(-2, -2, 2, 2)),
             ("continents", "continent:europe", shapely.box(-50, -50, 50, 50)),
             ("counties", "osm:r2", shapely.box(3, 3, 4, 4))]
    order = ["continents", "countries", "regions", "islands", "counties"]
    got = osm_places.areas_within([shapely.Point(0.5, 0.5), shapely.Point(60, 60)], areas, order)
    assert got == [[{"layer": "continents", "id": "continent:europe"}, {"layer": "countries", "id": "osm:r62149"},
                    {"layer": "regions", "id": "osm:r58447"}, {"layer": "counties", "id": "osm:r1"}], []]


def test_the_areas_a_place_is_in_follow_an_id_changed_in_the_writing():
    """A county sharing an id with a region is written with an ending; the place in the county names it so."""
    records = [{"id": "osm:r5", "layer": "regions", "name": "Isle of Wight"},
               {"id": "osm:r5", "layer": "counties", "name": "Isle of Wight"},
               {"id": "osm:n1", "layer": "towns", "name": "Newport",
                "within": [{"layer": "regions", "id": "osm:r5"}, {"layer": "counties", "id": "osm:r5"}]}]
    renamed = {}
    assert write.keep_ids_unique(records, lambda _t: None, renamed) == 1
    write.resolve_within(records, renamed)
    assert records[2]["within"] == ["osm:r5", "osm:r5#as-counties"]


def test_a_harbour_town_off_the_coast_has_the_areas_nearest_it():
    """Looe's point is in its harbour. Within a kilometre of the land, a place has the nearest area of each layer;
    further out at sea, none."""
    areas = [("countries", "gb", shapely.box(0, 0, 1, 1)), ("counties", "cornwall", shapely.box(0, 0, 0.5, 1)),
             ("counties", "devon", shapely.box(0.5, 0, 1, 1))]
    off = shapely.Point(0.4, -0.005)   # about 550 metres south of Cornwall's coast
    far = shapely.Point(0.4, -0.05)    # about 5.5 km out
    got = osm_places.areas_within([off, far], areas, ["countries", "counties"])
    assert got == [[{"layer": "countries", "id": "gb"}, {"layer": "counties", "id": "cornwall"}], []]
