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


def name_after_of(name: str) -> str:
    """A name as said after "of": "the United Kingdom", "the Isle of Wight", "the Gambia", but "France"
    (P3-T17). A name takes "the" when it has one of the words in templates.yaml, details, the_words."""
    if name.startswith("The "):
        return "the " + name[4:]
    words = set(name.replace(",", " ").split())
    return f"the {name}" if words & set(templates()["details"]["the_words"]) else name


def point_text(key: str) -> str:
    return templates()["points"][key]


def bearing_text(bearing: float, style: str = "points8") -> str:
    """For 47 degrees: "47 degrees", "about 50 degrees", "2 o'clock", "north-east"."""
    b = formats.bearing_parts(bearing, style)
    value = point_text(b.value) if b.kind == "point" else b.value
    return say(f"bearing.{b.kind}", value=value)


def direction_text(bearing: float, style: str = "points8", heading: float | None = None) -> str:
    """The direction to something (NAV-12, ANN-5). With heading None, a compass direction
    in the chosen format: "north-east", "47 degrees". With the heading the user faces, the
    same format measured from it, with "at your" (DP159): "at your north-east" is ahead
    right, "at your 2 o'clock", "at your 47 degrees"."""
    if heading is None:
        return bearing_text(bearing, style)
    b = formats.bearing_parts(formats.relative_bearing(bearing, heading), style)
    value = point_text(b.value) if b.kind == "point" else b.value
    return say(f"relative.{b.kind}", value=value)


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


def date_text(date: str) -> str:
    """A date as said: "2020", "March 2020" or "1 March 2020", from "2020", "2020-03" or "2020-03-01" (P3-T2b)."""
    parts = date.split("-") if not date.startswith("-") else [date]
    months = templates()["details"]["months"]
    if len(parts) == 3:
        return f"{int(parts[2])} {months[int(parts[1]) - 1]} {parts[0]}"
    if len(parts) == 2:
        return f"{months[int(parts[1]) - 1]} {parts[0]}"
    return date


def height_text(metres: float, system: str = "metric") -> str:
    """A height, such as "4,808 metres" or "15,774 feet", to the nearest whole unit (P3-T2b)."""
    if system == "metric":
        value, unit = metres, "m"
    else:
        value, unit = metres / 0.3048, "ft"
    number = f"{round(value):,}"
    return f"{number} {_unit(unit, number)}"


def fact_value_text(key: str, value, system: str = "metric") -> str:
    """A fact's value in words: a population as a whole number with commas, an area or a height in the units
    chosen, a capital or a list of capitals joined as a list is (P3-T2b)."""
    if key == "population":
        return f"{int(value):,}"
    if key == "area_km2":
        return area_text(float(value), system)
    if key == "elevation_m":
        return height_text(float(value), system)
    if key == "length_km":
        return distance_text(float(value) * 1000, system)
    if isinstance(value, list):
        return say("place.list_separator").join(str(v) for v in value)
    return str(value)
