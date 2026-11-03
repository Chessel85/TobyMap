"""mapdata inspect writes a point as people say it (DMT-2)."""
from mapdata.__main__ import place_words


def test_north_and_east():
    assert place_words(68.234, 14.568) == "68.234 north, 14.568 east"


def test_south_and_west():
    assert place_words(-90.0, 0.0) == "90.0 south, 0.0 east"
    assert place_words(-16.84, -179.995) == "16.84 south, 179.995 west"
