"""The wording of distances, directions, coordinates and changes (P1-T7; ANN-1, ANN-5, LOC-1, LOC-7)."""
import pytest

from mapcore import settings
from mapcore.describe import describer, words
from mapcore.world import WorldState


class A:
    def __init__(self, id, name, layer="regions"):
        self.id, self.name, self.layer = id, name, layer


@pytest.mark.parametrize("style, text", [
    ("exact", "47 degrees"), ("round10", "about 50 degrees"), ("round5", "about 45 degrees"),
    ("clock", "2 o'clock"), ("points8", "north-east"), ("points16", "north-east"), ("points32", "north-east"),
    ("points4", "east"),
])
def test_ann5_examples_for_47_degrees(style, text):
    assert words.bearing_text(47, style) == text


def test_32_points_name_the_in_between_points():
    assert words.bearing_text(11.25, "points32") == "north by east"
    assert words.bearing_text(33.75, "points32") == "north-east by north"


@pytest.mark.parametrize("metres, system, text", [
    (250, "metric", "250 metres"), (1000, "metric", "1 kilometre"), (1500, "metric", "1.5 kilometres"),
    (92_000, "metric", "92 kilometres"), (10_000_000, "metric", "10,000 kilometres"),
    (100, "imperial", "110 yards"), (5000, "imperial", "3.1 miles"), (1609.344, "imperial", "1 mile"),
    (3704, "nautical", "2 nautical miles"), (1852, "nautical", "1 nautical mile"),
])
def test_distances(metres, system, text):
    assert words.distance_text(metres, system) == text


def test_coordinates_in_both_formats():
    assert words.coordinates_text(51.5074, -0.1278) == "51.50740 degrees north, 0.12780 degrees west"
    assert words.coordinates_text(-33.8688, 151.2093, "dms") == \
        "33 degrees 52 minutes 7.7 seconds south, 151 degrees 12 minutes 33.5 seconds east"


def test_the_equator_the_prime_meridian_and_the_180_degree_line_have_no_hemisphere():
    assert words.coordinates_text(0, 0) == "0.00000 degrees, 0.00000 degrees"
    assert words.coordinates_text(10, 180) == "10.00000 degrees north, 180.00000 degrees"


def test_what_changed_is_listed_smallest_to_largest():
    england, uk, kent, france = A("e", "England"), A("u", "United Kingdom"), A("k", "Kent"), A("f", "France")
    assert describer.announcement([kent, england, uk], [england, uk]) is None   # nothing new
    assert describer.announcement([kent, england, uk], [france]) == "France"
    assert describer.announcement([france], [kent, england, uk]) == "Kent, England, United Kingdom"
    # Into the next county of the same country: only the county is new.
    surrey = A("s", "Surrey")
    assert describer.announcement([kent, england, uk], [surrey, england, uk]) == "Surrey"


def test_always_says_the_place_when_nothing_changed():
    """P2-T17q, DP162: terse the smallest area, normal it and its country, detailed the whole place."""
    kent, england, uk = A("k", "Kent", "counties"), A("e", "England", "regions"), A("u", "United Kingdom", "countries")
    here = [kent, england, uk]
    assert describer.announcement(here, here, say_area="smallest", always=True) == "Kent"
    assert describer.announcement(here, here, say_area="changed", always=True) == "Kent, United Kingdom"
    assert describer.announcement(here, here, say_area="whole", always=True) == "Kent, England, United Kingdom"
    assert describer.announcement(here, here, say_area="off", always=True) is None
    assert describer.announcement(here, here, say_area="changed") is None   # the switch off: the tick
    sea = [A("o", "North Atlantic Ocean", "oceans")]
    assert describer.announcement(sea, sea, say_area="changed", always=True) == "North Atlantic Ocean"
    country = [uk]
    assert describer.announcement(country, country, say_area="changed", always=True) == "United Kingdom"
    assert describer.announcement([], [], why_none="layers_off", always=True) == describer.place_text([], "layers_off")


def test_a_place_is_never_blank():
    assert describer.place_text([]) == "No area here"
    assert describer.announcement([A("a", "A")], []) == "No area here"
    assert describer.announcement([], []) is None


def test_the_heading_report():
    w = WorldState(zoom_index=5, step_index=4)
    assert describer.heading_report(w, "metric") == "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 250 metres."


def test_areas_in_square_kilometres_or_miles():
    assert words.area_text(1, "metric") == "1 square kilometre"
    assert words.area_text(41_682_627, "metric") == "41,700,000 square kilometres"
    assert words.area_text(2.59, "imperial") == "1 square mile"


def test_settings_check_their_values_and_ignore_what_is_unknown():
    s = settings.Settings({"units": "imperial", "bearing": "nonsense", "nobody": 1, "nearby_count": 500})
    assert s["units"] == "imperial" and s["bearing"] == "points8" and s["nearby_count"] == 8
    assert settings.Settings.from_dict(s.to_dict()).values == s.values
    with pytest.raises(ValueError):
        s.set("coordinates", "mgrs")
    with pytest.raises(ValueError):
        s.set("link", "yes")


def test_every_settings_field_has_a_default_among_its_choices():
    for field in settings.fields().values():
        if field["kind"] == "choice":
            assert field["default"] in [c[0] for c in field["choices"]]
