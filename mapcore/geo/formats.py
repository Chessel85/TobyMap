"""Distances, bearings and coordinates as numbers and keys (ANN-5, LOC-1).

These functions hold no wording. They return the number to say, as text
rounded the way it should be spoken, and a short key for the unit, compass
point or hemisphere. The templates (P1-T7, section 3.4) turn the keys into
words, so "NE" becomes "north-east" and "km" becomes "kilometres".

Keys used:

* units: "m", "km", "yd", "mi", "nmi"
* bearing kinds: "degrees", "about_degrees", "clock", "point"
* compass points: "N", "NbE", "NNE", "NEbN", "NE" and so on round to "NbW"
* hemispheres: "N", "S", "E", "W", or "" on the equator, the prime meridian
  and the 180 degree line
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from mapcore.geo.geodesy import wrap_lon

METRES_PER_MILE = 1609.344
METRES_PER_YARD = 0.9144
METRES_PER_NAUTICAL_MILE = 1852.0

UNIT_SYSTEMS = ("metric", "imperial", "nautical")
BEARING_STYLES = ("exact", "round5", "round10", "clock", "points4", "points8", "points16", "points32")

# The 32 points of the compass, clockwise from north, 11.25 degrees apart.
POINTS_32 = (
    "N", "NbE", "NNE", "NEbN", "NE", "NEbE", "ENE", "EbN",
    "E", "EbS", "ESE", "SEbE", "SE", "SEbS", "SSE", "SbE",
    "S", "SbW", "SSW", "SWbS", "SW", "SWbW", "WSW", "WbS",
    "W", "WbN", "WNW", "NWbW", "NW", "NWbN", "NNW", "NbW",
)


def _half_up(x: float) -> int:
    return math.floor(x + 0.5)


# Distances ---------------------------------------------------------------------------

def spoken_number(x: float) -> str:
    """A number rounded as it is spoken: 4.5, 92, 180, 1,050.

    Below 10 it keeps one decimal place unless that is 0; below 100 it is a
    whole number; from 100 it is rounded to the nearest 10.
    """
    if x < 9.95:
        return f"{_half_up(x * 10) / 10:.1f}".removesuffix(".0")
    if x < 99.5:
        return str(_half_up(x))
    return f"{_half_up(x / 10) * 10:,}"


@dataclass(frozen=True)
class Distance:
    value: str  # the number to say, already rounded
    unit: str   # "m", "km", "yd", "mi" or "nmi"


def distance_parts(metres: float, system: str = "metric") -> Distance:
    """A distance in the user's units (ANN-5).

    "metric" gives metres below 1 km and kilometres from there; "imperial"
    gives yards below a quarter of a mile and miles from there; "nautical",
    the extra option for sea, gives metres below a tenth of a nautical mile
    and nautical miles from there. The caller decides when nautical miles
    apply, which is at sea if the user has chosen them.
    """
    metres = abs(metres)
    if system == "metric":
        if metres < 999.5:
            return Distance(_short_number(metres), "m")
        return Distance(spoken_number(metres / 1000), "km")
    if system == "imperial":
        if metres < METRES_PER_MILE / 4:
            return Distance(_short_number(metres / METRES_PER_YARD), "yd")
        return Distance(spoken_number(metres / METRES_PER_MILE), "mi")
    if system == "nautical":
        if metres < METRES_PER_NAUTICAL_MILE / 10:
            return Distance(_short_number(metres), "m")
        return Distance(spoken_number(metres / METRES_PER_NAUTICAL_MILE), "nmi")
    raise ValueError(f"unknown unit system {system!r}")


def _short_number(x: float) -> str:
    """Metres or yards: whole numbers below 100, then to the nearest 10."""
    if x < 99.5:
        return str(_half_up(x))
    return f"{_half_up(x / 10) * 10:,}"


# Bearings ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Bearing:
    kind: str   # "degrees", "about_degrees", "clock" or "point"
    value: str  # "47", "50", "2", or a compass point key such as "NE"


def compass_point(bearing: float, points: int = 8) -> str:
    """The nearest of 4, 8, 16 or 32 compass points, as a key such as "NE"."""
    if points not in (4, 8, 16, 32):
        raise ValueError(f"compass points must be 4, 8, 16 or 32, not {points}")
    step = 32 // points
    index = _half_up((bearing % 360.0) / (360.0 / points)) % points
    return POINTS_32[index * step]


def bearing_parts(bearing: float, style: str = "points8") -> Bearing:
    """A bearing in the user's chosen style (ANN-5).

    For 47 degrees: exact gives 47, rounded to 10 gives about 50, clock face
    gives 2, and 8, 16 or 32 points give NE.
    """
    b = bearing % 360.0
    if style == "exact":
        return Bearing("degrees", str(_half_up(b) % 360))
    if style in ("round5", "round10"):
        size = 5 if style == "round5" else 10
        return Bearing("about_degrees", str(_half_up(b / size) * size % 360))
    if style == "clock":
        hour = _half_up(b / 30.0) % 12
        return Bearing("clock", str(hour or 12))
    if style.startswith("points") and style[6:].isdigit():
        return Bearing("point", compass_point(b, int(style[6:])))
    raise ValueError(f"unknown bearing style {style!r}")


# Coordinates -------------------------------------------------------------------------

@dataclass(frozen=True)
class Angle:
    """One latitude or longitude, without its sign."""
    degrees: str      # "51.50740" in decimal style, "51" in DMS style
    minutes: str      # "" in decimal style
    seconds: str      # "" in decimal style; one decimal place in DMS style
    hemisphere: str   # "N", "S", "E", "W" or ""


@dataclass(frozen=True)
class Coordinates:
    lat: Angle
    lon: Angle


def _hemisphere(value: float, positive: str, negative: str, is_lon: bool) -> str:
    if value == 0 or (is_lon and abs(value) == 180):
        return ""
    return positive if value > 0 else negative


def _angle(value: float, style: str, positive: str, negative: str, is_lon: bool) -> Angle:
    if style == "decimal":
        rounded = round(value, 5)
        return Angle(f"{abs(rounded):.5f}", "", "", _hemisphere(rounded, positive, negative, is_lon))
    if style == "dms":
        tenths = _half_up(abs(value) * 36000)  # tenths of a second
        deg, rest = divmod(tenths, 36000)
        minutes, sec_tenths = divmod(rest, 600)
        signed = math.copysign(tenths, value) if tenths else 0
        return Angle(str(deg), str(minutes), f"{sec_tenths / 10:.1f}",
                     _hemisphere(signed / 36000, positive, negative, is_lon))
    raise ValueError(f"unknown coordinate style {style!r}")


def coordinate_parts(lat: float, lon: float, style: str = "decimal") -> Coordinates:
    """Latitude and longitude in decimal degrees to 5 places (about 1 metre),
    or in degrees, minutes and seconds to a tenth of a second (LOC-1)."""
    return Coordinates(_angle(lat, style, "N", "S", False), _angle(wrap_lon(lon), style, "E", "W", True))
