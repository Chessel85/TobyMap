"""The Phase 0 wording of positions (P0-T8), kept until P1-T7 moves it into the templates."""
import pytest

from mapcore.geo import phase0_words as words
from mapcore.geo import geodesy


def test_paris_from_london_is_south_east():
    assert words.compass_point(geodesy.bearing_deg(51.5074, -0.1278, 48.8566, 2.3522)) == "south-east"


@pytest.mark.parametrize("deg, name", [(0, "north"), (44, "north-east"), (90, "east"), (181, "south"),
                                       (225, "south-west"), (300, "north-west"), (359, "north")])
def test_compass_points(deg, name):
    assert words.compass_point(deg) == name


@pytest.mark.parametrize("lat, lon, text", [
    (52, -1, "52 degrees north, 1 degree west"),
    (-33.86, 151.21, "33.9 degrees south, 151.2 degrees east"),
    (0, 0, "0 degrees, 0 degrees"),
    (90, 180, "90 degrees north, 180 degrees"),
])
def test_coordinates_in_words(lat, lon, text):
    assert words.coordinates_text(lat, lon) == text


@pytest.mark.parametrize("km, text", [(0.4, "less than 1 kilometre"), (1, "1 kilometre"), (7.26, "7 kilometres"),
                                      (343.5, "340 kilometres"), (1049, "1,050 kilometres")])
def test_distance_in_words(km, text):
    assert words.distance_text(km) == text


def test_km_number_rounds_like_spoken_distances():
    assert [words.km_number(k) for k in (4.46, 7.0, 92.4, 182.0, 1047.0)] == ["4.5", "7", "92", "180", "1,050"]
