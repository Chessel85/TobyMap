"""Distances, bearings and coordinates as numbers and keys (P1-T1; ANN-5, LOC-1)."""
import pytest

from mapcore.geo import formats as f


# Bearings: the ANN-5 examples for 47 degrees ------------------------------------------

@pytest.mark.parametrize("style, kind, value", [
    ("exact", "degrees", "47"),
    ("round10", "about_degrees", "50"),
    ("round5", "about_degrees", "45"),
    ("clock", "clock", "2"),
    ("points8", "point", "NE"),
    ("points16", "point", "NE"),
    ("points32", "point", "NE"),
    ("points4", "point", "E"),  # 47 degrees is just past half way from north to east
])
def test_ann5_examples_for_47_degrees(style, kind, value):
    assert f.bearing_parts(47, style) == f.Bearing(kind, value)


def test_32_points_gives_north_east_from_39_4_to_50_6_degrees():
    assert f.compass_point(39.4, 32) == "NE"
    assert f.compass_point(50.6, 32) == "NE"
    assert f.compass_point(39.3, 32) == "NEbN"
    assert f.compass_point(50.7, 32) == "NEbE"


@pytest.mark.parametrize("deg, points, key", [
    (0, 8, "N"), (359, 8, "N"), (181, 8, "S"), (225, 8, "SW"), (300, 8, "NW"),
    (22.6, 16, "NNE"), (348.7, 16, "NNW"), (348.8, 16, "N"), (101.25, 32, "EbS"), (360, 32, "N"),
    (44.9, 4, "N"), (45, 4, "E"), (270, 4, "W"),
])
def test_compass_points(deg, points, key):
    assert f.compass_point(deg, points) == key


def test_compass_points_must_be_4_8_16_or_32():
    with pytest.raises(ValueError):
        f.compass_point(10, 12)


@pytest.mark.parametrize("deg, hour", [(0, "12"), (15, "1"), (90, "3"), (180, "6"), (350, "12"), (344, "11")])
def test_clock_face(deg, hour):
    assert f.bearing_parts(deg, "clock").value == hour


def test_rounded_and_exact_degrees_wrap_at_360():
    assert f.bearing_parts(359.6, "exact").value == "0"
    assert f.bearing_parts(356, "round10").value == "0"
    assert f.bearing_parts(-10, "exact").value == "350"


def test_unknown_bearing_style():
    with pytest.raises(ValueError):
        f.bearing_parts(10, "points")


# Distances ---------------------------------------------------------------------------

@pytest.mark.parametrize("metres, system, value, unit", [
    (344_000, "metric", "340", "km"),
    (1_047_000, "metric", "1,050", "km"),
    (4_460, "metric", "4.5", "km"),
    (7_000, "metric", "7", "km"),
    (92_400, "metric", "92", "km"),
    (999.4, "metric", "1,000", "m"),
    (1_000, "metric", "1", "km"),
    (5, "metric", "5", "m"),
    (346, "metric", "350", "m"),
    (344_000, "imperial", "210", "mi"),
    (100, "imperial", "110", "yd"), (50, "imperial", "55", "yd"),
    (402.336, "imperial", "0.3", "mi"),
    (1_852, "nautical", "1", "nmi"),
    (100, "nautical", "100", "m"),
    (18_520, "nautical", "10", "nmi"),
])
def test_distances(metres, system, value, unit):
    assert f.distance_parts(metres, system) == f.Distance(value, unit)


def test_unknown_unit_system():
    with pytest.raises(ValueError):
        f.distance_parts(10, "furlongs")


def test_spoken_numbers():
    assert [f.spoken_number(x) for x in (4.46, 7.0, 9.96, 92.4, 99.6, 182.0, 1047.0)] == \
        ["4.5", "7", "10", "92", "100", "180", "1,050"]


# Coordinates (LOC-1) -----------------------------------------------------------------

def test_decimal_coordinates_to_5_places():
    c = f.coordinate_parts(51.5073509, -0.1277583)
    assert c.lat == f.Angle("51.50735", "", "", "N")
    assert c.lon == f.Angle("0.12776", "", "", "W")


def test_dms_coordinates():
    c = f.coordinate_parts(-33.8688, 151.2093, "dms")
    assert c.lat == f.Angle("33", "52", "7.7", "S")
    assert c.lon == f.Angle("151", "12", "33.5", "E")


def test_dms_carries_the_seconds_over():
    c = f.coordinate_parts(10.999999, 0.0, "dms")
    assert c.lat == f.Angle("11", "0", "0.0", "N")


@pytest.mark.parametrize("lat, lon, lat_h, lon_h", [
    (0, 0, "", ""), (0.000001, 0, "", ""), (90, 180, "N", ""), (-10, -180, "S", ""), (10, 190, "N", "W"),
])
def test_hemispheres(lat, lon, lat_h, lon_h):
    for style in ("decimal", "dms"):
        c = f.coordinate_parts(lat, lon, style)
        assert (c.lat.hemisphere, c.lon.hemisphere) == (lat_h, lon_h), style


def test_unknown_coordinate_style():
    with pytest.raises(ValueError):
        f.coordinate_parts(0, 0, "grid")
