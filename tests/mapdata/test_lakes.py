"""P3-T1h: the lakes, from OpenStreetMap, checked against HydroLAKES (DAT-1, DP169, LOC-2)."""
import shapely

from mapdata.pipeline.build import STAGES
from mapdata.pipeline.settings import load_pack, stage_sources
from mapdata.stages import osm_layer


def test_the_world_pack_reads_lakes_of_10_km2_or_more_into_their_own_layer():
    pack = load_pack("world")
    stage = next(s for s in pack.stages if s["stage"] == "osm-layer" and s["layer"] == "lakes")
    assert stage["min_km2"] == 10   # DP169
    assert stage["same_as"] == ["oceans", "seas"]   # the Caspian Sea is said once
    assert {q["type"] for q in stage["queries"]} == {"lake", "reservoir", "lagoon"}
    assert any("water=pond" in q["query"] for q in stage["queries"])   # the Etang de Berre
    assert "hydrolakes-points" in stage_sources(stage)   # the check's source is fingerprinted and credited
    lakes = pack.layers["lakes"]
    assert lakes.kind == "land" and lakes.made_by == "osm-layer"   # nothing is taken out of a lake
    assert dict(lakes.shown)["fill"] == "water"


def test_on_a_lake_you_hear_the_lake_before_the_county():
    """LOC-2: the location is announced as the lake. The core orders areas by rank, highest first."""
    layers = load_pack("world").layers
    assert layers["lakes"].rank > layers["counties"].rank > layers["regions"].rank


def test_the_stage_is_known_and_reads_in_its_own_process():
    assert STAGES["osm-layer"].module == "mapdata.stages.osm_layer"
    assert callable(osm_layer.main)


def test_a_large_lake_with_none_of_the_layer_nearby_is_listed_as_missing():
    geneva = shapely.box(6.15, 46.2, 6.9, 46.5)
    lakes = [{"id": 1, "name": "Leman", "km2": 580.0, "point": shapely.Point(6.16, 46.21)},     # on its edge
             {"id": 2, "name": "Bodensee", "km2": 536.0, "point": shapely.Point(9.4, 47.6)},
             {"id": 3, "name": "", "km2": 120.0, "point": shapely.Point(6.9 + 0.015, 46.3)}]   # 1.2 km away
    gone = osm_layer.missing(lakes, [geneva], within_km=2)
    assert [lk["id"] for lk in gone] == [2]
    assert osm_layer.missing(lakes, [], within_km=2) == lakes
    assert osm_layer.missing([], [geneva], within_km=2) == []


def test_a_lake_whose_outlet_is_downstream_is_found_by_its_name():
    """HydroLAKES's point for Lake Vattern is at its outlet, 1.8 km from the shore, and at 58.5 degrees north;
    Lake Maggiore's is 14 km down the Ticino. Both are found, by distance in km or by name, ignoring accents."""
    vattern = shapely.box(14.11, 57.78, 15.0, 58.86)
    maggiore = shapely.box(8.48, 45.80, 8.87, 46.18)
    records = [{"name": "Vättern"}, {"name": "Lake Maggiore", "local_name": "Lago Maggiore"}]
    lakes = [{"id": 104, "name": "Vattern", "km2": 1888.0, "point": shapely.Point(15.031, 58.5323)},
             {"id": 1275, "name": "Maggiore", "km2": 208.0, "point": shapely.Point(8.6822, 45.6735)},
             {"id": 9, "name": "Elsewhere", "km2": 300.0, "point": shapely.Point(8.6822, 45.6735)}]
    gone = osm_layer.missing(lakes, [vattern, maggiore], within_km=2, records=records)
    assert [lk["id"] for lk in gone] == [9]


def test_a_large_lake_is_looked_for_by_name_farther_from_its_outlet():
    """Great Slave Lake's outlet point in HydroLAKES is 60 km down the Mackenzie: a lake of 26,734 km2 is looked
    for by its name up to 1.5 times the side of a square of its area, 245 km; a small one only 30 km."""
    shore = shapely.box(-116.0, 61.0, -109.0, 62.9)
    records = [{"name": "Great Slave Lake"}]
    big = {"id": 1, "name": "Great Slave", "km2": 26734.0, "point": shapely.Point(-117.1, 61.3)}
    small = {"id": 2, "name": "Great Slave", "km2": 150.0, "point": shapely.Point(-117.1, 61.3)}
    assert osm_layer.missing([big, small], [shore], within_km=2, records=records) == [small]


def test_a_simplified_outline_keeps_only_its_areas():
    bow = shapely.Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])   # crosses itself
    g = osm_layer.polygonal(bow)
    assert g.is_valid and g.geom_type == "MultiPolygon" and g.area > 0
    assert osm_layer.polygonal(shapely.LineString([(0, 0), (1, 1)])) is None
