"""The world sample stage turns Natural Earth countries into the small globe file (P0-T8, VIS-5)."""
import json

from mapdata.stages import world_sample


def _feature(name, geometry, colour=3, adm="AAA"):
    return {
        "type": "Feature",
        "properties": {
            "NAME": name, "NAME_LONG": name + " long", "SOVEREIGNT": name, "CONTINENT": "Europe",
            "SUBREGION": "Western Europe", "POP_EST": 1234.0, "MAPCOLOR7": colour, "ADM0_A3": adm,
            "LABEL_X": 1.23456, "LABEL_Y": 2.34567,
        },
        "geometry": geometry,
    }


SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
HOLE = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]


def test_polygon_and_multipolygon_become_flat_rings():
    source = {"type": "FeatureCollection", "features": [
        _feature("Squareland", {"type": "Polygon", "coordinates": [SQUARE, HOLE]}, adm="SQL"),
        _feature("Twoland", {"type": "MultiPolygon", "coordinates": [[SQUARE], [HOLE]]}, adm="TWL"),
    ]}
    out = world_sample.convert(source, source_name="test")
    assert out["format"] == world_sample.FORMAT
    first, second = out["countries"]
    assert first["id"] == "ne:SQL"
    assert first["name"] == "Squareland"
    assert first["population"] == 1234
    assert first["colour"] == 3
    assert first["centre"] == [1.235, 2.346]
    # One polygon with an outer ring and a hole; closing points are dropped.
    assert first["polygons"] == [[[0, 0, 10, 0, 10, 10, 0, 10], [4, 4, 6, 4, 6, 6, 4, 6]]]
    assert len(second["polygons"]) == 2


def test_countries_are_sorted_by_name_so_the_output_repeats():
    source = {"type": "FeatureCollection", "features": [
        _feature("Zed", {"type": "Polygon", "coordinates": [SQUARE]}, adm="ZED"),
        _feature("Abc", {"type": "Polygon", "coordinates": [SQUARE]}, adm="ABC"),
    ]}
    out = world_sample.convert(source, source_name="test")
    assert [c["name"] for c in out["countries"]] == ["Abc", "Zed"]
    text1 = world_sample.dumps(out)
    text2 = world_sample.dumps(world_sample.convert(source, source_name="test"))
    assert text1 == text2
    assert json.loads(text1) == out


def test_missing_colour_gets_a_default():
    feature = _feature("Nocolour", {"type": "Polygon", "coordinates": [SQUARE]})
    del feature["properties"]["MAPCOLOR7"]
    out = world_sample.convert({"type": "FeatureCollection", "features": [feature]}, source_name="test")
    assert out["countries"][0]["colour"] == 1
