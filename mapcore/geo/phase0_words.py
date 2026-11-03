"""The Phase 0 wording of coordinates, distances and directions.

Kept only until P1-T7, when these words move into the templates (section
3.4) and the numbers come from mapcore.geo.formats. The sums themselves are
in mapcore.geo.geodesy, on the WGS 84 ellipsoid (AD-7).

Written for a screen reader: words, not symbols, and no degree signs.
"""
from __future__ import annotations

from mapcore.geo.formats import compass_point as _point_key
from mapcore.geo.geodesy import wrap_lon

_WORDS = {"N": "north", "NE": "north-east", "E": "east", "SE": "south-east",
          "S": "south", "SW": "south-west", "W": "west", "NW": "north-west"}


def compass_point(bearing: float) -> str:
    return _WORDS[_point_key(bearing, 8)]


def _degrees(value: float) -> str:
    rounded = round(abs(value), 1)
    number = f"{rounded:.0f}" if rounded == int(rounded) else f"{rounded:.1f}"
    return f"{number} degree" if number == "1" else f"{number} degrees"


def coordinates_text(lat: float, lon: float) -> str:
    """For example "52 degrees north, 1 degree west"."""
    lat_r, lon_r = round(lat, 1), round(wrap_lon(lon), 1)
    lat_word = "" if lat_r == 0 else (" north" if lat_r > 0 else " south")
    lon_word = "" if lon_r in (0, 180, -180) else (" east" if lon_r > 0 else " west")
    return f"{_degrees(lat_r)}{lat_word}, {_degrees(lon_r)}{lon_word}"


def km_number(km: float) -> str:
    """A distance in kilometres as a rounded number: 4.5, 92, 180, 1,050."""
    if km < 10:
        return f"{km:.1f}".removesuffix(".0")
    if km < 100:
        return str(round(km))
    return f"{int(round(km, -1)):,}"


def distance_text(km: float) -> str:
    """Rounded so it reads naturally: 7 kilometres, 340 kilometres, 1,050 kilometres."""
    if km < 0.5:
        return "less than 1 kilometre"
    if km < 100:
        value = round(km)
    else:
        value = int(round(km, -1))
    return "1 kilometre" if value == 1 else f"{value:,} kilometres"
