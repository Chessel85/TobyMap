"""Turning the numbers of mapcore.geo.formats into words (ANN-5, LOC-1, LOC-7).

All the words come from templates.yaml (architecture 3.4). This module only
chooses singular or plural and puts the parts together.
"""
from __future__ import annotations

from mapcore.describe import say, templates
from mapcore.geo import formats


def _unit(unit: str, value: str) -> str:
    singular, plural = templates()["units"][unit]
    return singular if value == "1" else plural


def distance_text(metres: float, system: str = "metric") -> str:
    """For example "250 metres", "1 kilometre", "0.4 miles"."""
    d = formats.distance_parts(metres, system)
    return f"{d.value} {_unit(d.unit, d.value)}"


def point_text(key: str) -> str:
    return templates()["points"][key]


def bearing_text(bearing: float, style: str = "points8") -> str:
    """For 47 degrees: "47 degrees", "about 50 degrees", "2 o'clock", "north-east"."""
    b = formats.bearing_parts(bearing, style)
    value = point_text(b.value) if b.kind == "point" else b.value
    return say(f"bearing.{b.kind}", value=value)


def _angle_text(angle: formats.Angle, dms: bool) -> str:
    key = ("dms_angle" if dms else "decimal_angle") + ("" if angle.hemisphere else "_plain")
    return say(f"coordinates.{key}", degrees=angle.degrees, minutes=angle.minutes, seconds=angle.seconds,
               hemisphere=templates()["hemispheres"].get(angle.hemisphere, ""))


def coordinates_text(lat: float, lon: float, style: str = "decimal", step_m: float | None = None) -> str:
    """For example "51.50740 degrees north, 0.12780 degrees west" (LOC-1). With
    step_m, only the decimal places that step needs: "51.5 degrees north"."""
    c = formats.coordinate_parts(lat, lon, style, step_m)
    dms = style == "dms"
    return say("coordinates.pair", lat=_angle_text(c.lat, dms), lon=_angle_text(c.lon, dms))


def heading_text(heading: float) -> str:
    return point_text(formats.compass_point(heading, 8))


def area_text(km2: float, system: str = "metric") -> str:
    """An area, such as "41,680,000 square kilometres" (Details)."""
    if system == "metric" or system == "nautical":
        value, unit = km2, "km2"
    else:
        value, unit = km2 / (formats.METRES_PER_MILE / 1000) ** 2, "mi2"
    if value >= 1000:  # three significant figures: 41,682,627 is "41,700,000"
        digits = len(str(int(value))) - 3
        number = f"{round(value, -digits):,.0f}"
    else:
        number = formats.spoken_number(value)
    return f"{number} {_unit(unit, number)}"
