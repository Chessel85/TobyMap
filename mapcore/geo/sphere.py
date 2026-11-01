"""Spherical geometry for spike S5 only.

AD-7 says every distance and bearing is worked out on the WGS84 ellipsoid with
GeographicLib. That arrives in Phase 1 with stepping. The globe spike only
needs rough distances to the nearest countries, so the mean-radius sphere is
used here, which is within about half a percent.

The wording helpers (coordinates, distances, compass points) are written for a
screen reader: words, not symbols, and no degree signs.
"""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088

COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great circle bearing from point 1 to point 2, clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(y, x)) % 360


def compass_point(bearing: float) -> str:
    return COMPASS[int(((bearing % 360) + 22.5) // 45) % 8]


def wrap_lon(lon: float) -> float:
    """Longitude in the range above -180 up to 180."""
    wrapped = ((lon + 180) % 360) - 180
    return 180 if wrapped == -180 else wrapped


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
