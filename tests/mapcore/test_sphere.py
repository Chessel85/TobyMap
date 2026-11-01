"""Spike-level spherical geometry and wording of positions (P0-T8)."""
import pytest

from mapcore.geo import sphere


def test_london_to_paris_is_about_344_km():
    # INF-3 gives about 344 km on the ellipsoid; the sphere is within 1 km here.
    km = sphere.distance_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert km == pytest.approx(343.5, abs=1.5)


def test_bearing_paris_from_london_is_south_east():
    bearing = sphere.bearing_deg(51.5074, -0.1278, 48.8566, 2.3522)
    assert 145 < bearing < 150
    assert sphere.compass_point(bearing) == "south-east"


@pytest.mark.parametrize("deg, name", [(0, "north"), (44, "north-east"), (90, "east"), (181, "south"),
                                       (225, "south-west"), (300, "north-west"), (359, "north")])
def test_compass_points(deg, name):
    assert sphere.compass_point(deg) == name


@pytest.mark.parametrize("lat, lon, text", [
    (52, -1, "52 degrees north, 1 degree west"),
    (-33.86, 151.21, "33.9 degrees south, 151.2 degrees east"),
    (0, 0, "0 degrees, 0 degrees"),
    (90, 180, "90 degrees north, 180 degrees"),
])
def test_coordinates_in_words(lat, lon, text):
    assert sphere.coordinates_text(lat, lon) == text


@pytest.mark.parametrize("km, text", [(0.4, "less than 1 kilometre"), (1, "1 kilometre"), (7.26, "7 kilometres"),
                                      (343.5, "340 kilometres"), (1049, "1,050 kilometres")])
def test_distance_in_words(km, text):
    assert sphere.distance_text(km) == text


def test_wrap_longitude():
    assert sphere.wrap_lon(190) == -170
    assert sphere.wrap_lon(-180) == 180
    assert sphere.wrap_lon(180) == 180
    assert sphere.wrap_lon(-190) == 170
