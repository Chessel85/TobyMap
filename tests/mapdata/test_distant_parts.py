"""DP191: a country's parts on another continent become areas of their own in the Countries layer.

The stage's rule is the continents stage's: the same groups, the same continents, the same settings. These
tests use made-up shapes on the real continents' areas: Spain's mainland is in Europe, the Canary Islands in
Africa.
"""
import shapely

from mapdata.stages import continents
from mapdata.stages import distant_parts as dp

SETTINGS = continents.load_settings()
MAINLAND = shapely.box(-6.0, 37.0, -1.0, 42.0)            # Europe
CANARIES = shapely.MultiPolygon([shapely.box(-16.7, 28.0, -16.2, 28.5), shapely.box(-15.7, 27.8, -15.3, 28.2)])
CORSICA = shapely.box(8.6, 41.5, 9.5, 43.0)               # Europe, like the mainland


def country(id_, name, *parts, **extra):
    return dict({"id": id_, "layer": "countries", "name": name, "type": "country", "colour": 1}, **extra), \
        shapely.MultiPolygon([p for g in parts for p in shapely.get_parts(g)])


def run(items, min_share=0.5):
    records = [r for r, _g in items]
    geoms = [g for _r, g in items]
    lines, logs = [], []
    new, changed, reparent = dp.split_countries(records, lambda idx: {i: geoms[i] for i in idx}, SETTINGS,
                                                min_share, lines.append, logs.append)
    return records, new, changed, reparent, lines, logs


def test_a_group_on_another_continent_becomes_an_area_named_after_its_region():
    spain = country("osm:r1", "Spain", MAINLAND, CANARIES, wikidata="Q29")
    region = ({"id": "osm:r2", "layer": "regions", "name": "Canary Islands", "parent": "osm:r1", "wikidata": "Q5813",
               "local_name": "Canarias"}, CANARIES)
    records, new, changed, reparent, lines, _ = run([spain, region])
    assert len(new) == 1
    rec, shape = new[0]
    assert rec["id"] == "part:osm:r2" and rec["name"] == "Canary Islands" and rec["layer"] == "countries"
    assert rec["sovereign"] == "Spain" and rec["sovereign_id"] == "osm:r1" and rec["named_from"] == "osm:r2"
    assert rec["wikidata"] == "Q5813" and rec["local_name"] == "Canarias" and rec["type"] == "distant part"
    assert "parent" not in rec   # Spain does not hold it
    assert shape.equals(CANARIES)
    assert changed[0].equals(MAINLAND)
    assert reparent == {1: "part:osm:r2"}
    assert lines == ["Distant part: Canary Islands, 4,480 km2, in Africa, is now an area of its own, with Spain as "
                     "its sovereign state."]


def test_a_distant_part_on_the_same_continent_stays_with_its_country():
    """Corsica, like Alaska, is on its country's continent, so it stays."""
    france = country("osm:r3", "France", shapely.box(-1.0, 43.5, 5.0, 49.0), CORSICA)
    _, new, changed, reparent, _, _ = run([france])
    assert new == [] and changed == {} and reparent == {}


def test_a_country_split_along_continent_lines_is_left_whole():
    russia = country("osm:r4", "Russia", shapely.box(37.0, 55.0, 39.0, 56.0), shapely.box(130.0, 43.0, 132.0, 44.0),
                     wikidata="Q159")
    _, new, changed, _, _, _ = run([russia])
    assert new == [] and changed == {}


def test_a_region_mostly_elsewhere_does_not_name_the_part_its_county_does():
    """Easter Island is in the region of Valparaiso, which is mostly on the mainland: its county names it."""
    island = shapely.box(-109.45, -27.2, -109.2, -27.05)
    mainland = shapely.box(-72.0, -34.0, -70.0, -32.0)
    chile = country("osm:r5", "Chile", mainland, island)
    valparaiso = ({"id": "osm:r6", "layer": "regions", "name": "Valparaiso", "parent": "osm:r5"},
                  shapely.union(mainland, island))
    province = ({"id": "osm:r7", "layer": "counties", "name": "Easter Island Province", "parent": "osm:r6"}, island)
    _, new, _, reparent, _, _ = run([chile, valparaiso, province])
    assert [r["name"] for r, _ in new] == ["Easter Island Province"]
    assert reparent == {}   # a county keeps its region as its parent


def test_a_region_with_the_countrys_own_name_is_passed_over():
    """The Netherlands' region named Netherlands holds only its Caribbean municipalities: they name the parts."""
    bonaire = shapely.box(-68.4, 12.0, -68.2, 12.3)
    saba = shapely.box(-63.25, 17.6, -63.2, 17.65)
    nl = country("osm:r8", "Netherlands", shapely.box(4.0, 51.5, 6.5, 53.0), bonaire, saba)
    region = ({"id": "osm:r9", "layer": "regions", "name": "Netherlands", "parent": "osm:r8"},
              shapely.union(bonaire, saba))
    counties = [({"id": f"osm:r{n}", "layer": "counties", "name": name, "parent": "osm:r9"}, g)
                for n, name, g in ((10, "Bonaire", bonaire), (11, "Saba", saba))]
    _, new, _, _, _, _ = run([nl, region, *counties])
    assert sorted(r["name"] for r, _ in new) == ["Bonaire", "Saba"]


def test_land_in_no_region_is_named_after_its_largest_island_or_its_continent():
    wake = shapely.box(166.6, 19.27, 166.66, 19.32)
    wilkes = shapely.box(166.56, 19.27, 166.59, 19.29)
    jarvis = shapely.box(-160.03, -0.38, -159.99, -0.36)
    usa = country("osm:r12", "United States", shapely.box(-100.0, 35.0, -90.0, 45.0), wake, wilkes, jarvis)
    islands = [({"id": "osm:w1", "layer": "islands", "name": "Wake Island", "type": "island"}, wake),
               ({"id": "osm:w2", "layer": "islands", "name": "Wilkes Island", "type": "island"}, wilkes)]
    _, new, _, _, _, logs = run([usa, *islands])
    by_name = {r["name"]: (r, g) for r, g in new}
    assert sorted(by_name) == ["United States in Oceania", "Wake Island"]
    rec, shape = by_name["Wake Island"]
    assert rec["id"] == "part:osm:w1" and shape.equals(shapely.union(wake, wilkes))   # one area for the atoll
    assert by_name["United States in Oceania"][0]["id"] == "part:osm:r12:continent:oceania"
    assert any("named after its largest named island, Wake Island" in s for s in logs)
    assert any("is named United States in Oceania" in s for s in logs)


def test_a_new_area_takes_a_colour_apart_from_its_neighbours():
    """French Guiana borders Brazil and Suriname, so it is coloured apart from them (AD-19)."""
    guiana = shapely.box(-54.0, 2.5, -51.6, 5.7)
    france = country("osm:r13", "France", shapely.box(-1.0, 43.5, 5.0, 49.0), guiana)
    brazil = country("osm:r14", "Brazil", shapely.box(-60.0, -30.0, -40.0, 2.5))
    brazil[0]["colour"] = 2
    suriname = country("osm:r15", "Suriname", shapely.box(-57.0, 2.5, -54.0, 6.0))
    suriname[0]["colour"] = 3
    region = ({"id": "osm:r16", "layer": "regions", "name": "French Guiana", "parent": "osm:r13"}, guiana)
    _, new, _, _, _, _ = run([france, brazil, suriname, region])
    assert new[0][0]["colour"] not in (2, 3)
