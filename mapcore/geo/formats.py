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


METRES_PER_DEGREE = 111_320.0   # along a meridian, near enough for choosing decimal places
DECIMAL_PLACES = 5               # about 1 metre
SECOND_METRES = METRES_PER_DEGREE / 3600


def decimal_places(step_m: float | None) -> int:
    """How many decimal places of a degree show a step of this size: enough that
    one step changes the last place, and no more (PO feedback on checklist 4,
    second pass). A step of 100 kilometres, just under a degree, gives 1 place;
    1 kilometre gives 3; 1 metre or less, 5. None gives 5."""
    if not step_m or step_m <= 0:
        return DECIMAL_PLACES
    return max(1, min(DECIMAL_PLACES, math.ceil(math.log10(METRES_PER_DEGREE / step_m))))


def _angle(value: float, style: str, positive: str, negative: str, is_lon: bool,
           places: int = DECIMAL_PLACES, second_places: int = 1) -> Angle:
    if style == "decimal":
        rounded = round(value, places)
        return Angle(f"{abs(rounded):.{places}f}", "", "", _hemisphere(rounded, positive, negative, is_lon))
    if style == "dms":
        scale = 10 ** second_places
        parts = _half_up(abs(value) * 3600 * scale)  # tenths of a second, or whole seconds
        deg, rest = divmod(parts, 3600 * scale)
        minutes, sec_parts = divmod(rest, 60 * scale)
        signed = math.copysign(parts, value) if parts else 0
        return Angle(str(deg), str(minutes), f"{sec_parts / scale:.{second_places}f}",
                     _hemisphere(signed / (3600 * scale), positive, negative, is_lon))
    raise ValueError(f"unknown coordinate style {style!r}")


def coordinate_parts(lat: float, lon: float, style: str = "decimal", step_m: float | None = None) -> Coordinates:
    """Latitude and longitude in decimal degrees to 5 places (about 1 metre),
    or in degrees, minutes and seconds to a tenth of a second (LOC-1). Given a
    step size, only as many places as that step needs: a 100 kilometre step
    gives "51.2 degrees north", and seconds are whole unless the step is
    smaller than a second, about 31 metres."""
    places = decimal_places(step_m)
    second_places = 1 if step_m is None or step_m < SECOND_METRES else 0
    return Coordinates(_angle(lat, style, "N", "S", False, places, second_places),
                       _angle(wrap_lon(lon), style, "E", "W", True, places, second_places))
