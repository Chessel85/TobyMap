"""Reading what the user types: a bearing (NAV-12) and coordinates (NAV-8).

Both refuse anything out of range or that could be read two ways, with a
ValueError. The session turns the error into the words from the templates, which
list what is accepted.
"""
from __future__ import annotations

import re

from mapcore.geo.formats import POINTS_32

# Compass points a person may type, by name or by letters: "NE", "north-east", "north east",
# "northeast". The 16 principal points; the "by" points are too fine to type.
_POINT_NAMES = {
    "N": "north", "NNE": "north-north-east", "NE": "north-east", "ENE": "east-north-east",
    "E": "east", "ESE": "east-south-east", "SE": "south-east", "SSE": "south-south-east",
    "S": "south", "SSW": "south-south-west", "SW": "south-west", "WSW": "west-south-west",
    "W": "west", "WNW": "west-north-west", "NW": "north-west", "NNW": "north-north-west",
}
_POINTS = {}
for _key, _name in _POINT_NAMES.items():
    _degrees = POINTS_32.index(_key) * 11.25
    for _form in (_key.lower(), _name, _name.replace("-", " "), _name.replace("-", "")):
        _POINTS[_form] = _degrees

_DEGREES = re.compile(r"(\d+(?:\.\d+)?)\s*(?:°|º|˚|deg(?:rees?)?)?")


def parse_bearing(text: str) -> float:
    """A bearing in degrees, 0 up to 360, from "47", "47.5", "47°", "47 degrees" or a compass
    point such as "NE" or "north-east". 360 is north. Raises ValueError otherwise."""
    cleaned = str(text).strip().lower()
    if cleaned in _POINTS:
        return _POINTS[cleaned]
    match = _DEGREES.fullmatch(cleaned)
    if not match:
        raise ValueError(f"not a bearing: {text!r}")
    value = float(match.group(1))
    if value > 360.0:
        raise ValueError(f"a bearing is 0 to 360 degrees: {text!r}")
    return 0.0 if value == 360.0 else value


# Coordinates -----------------------------------------------------------------------

_NUMBER = r"\d+(?:\.\d+)?"


def _component(n: str, after: bool = True) -> str:
    """One of the two coordinates: [letter] [sign] degrees [° [minutes ′ [seconds ″]]] [letter].
    Minutes and seconds need their own marks, so "51.5 0.12" is two numbers, not minutes.
    after: the letter may come after the number as well as before it."""
    tail = rf"(?:\s*(?P<post{n}>[nsew]))?" if after else ""
    return (rf"(?:(?P<pre{n}>[nsew])\s*)?(?P<sign{n}>[-+])?\s*(?P<deg{n}>{_NUMBER})\s*(?:°\s*"
            rf"(?:(?P<min{n}>{_NUMBER})\s*'\s*(?:(?P<sec{n}>{_NUMBER})\s*\"\s*)?)?)?" + tail)


# Between the two: a comma or semicolon, or a space, or nothing after a letter or a mark ("51.5N0.12W").
_SEP = r"(?:\s*[,;]\s*|\s+|(?<=[nsew°'\"]))"

# "n 51.5 w 0.12" has a letter before the second number, which the first reading takes as the
# first number's letter after it. So a second reading, with the first number's letter only
# allowed before it, is tried when the first fails.
_PAIRS = (re.compile(rf"{_component('1')}{_SEP}{_component('2')}"),
          re.compile(rf"{_component('1', after=False)}{_SEP}{_component('2')}"))


def _value(m: re.Match, n: str, letters: str, limit: float, what: str) -> float:
    pre, post = m.group(f"pre{n}"), m.groupdict().get(f"post{n}")
    if pre and post:
        raise ValueError(f"two letters on the {what}")
    letter = (pre or post or "").lower()
    if letter and letter not in letters:
        raise ValueError(f"{letter.upper()} cannot be the {what}")
    sign = m.group(f"sign{n}")
    if letter and sign:
        raise ValueError(f"a sign and a letter on the {what} could be read two ways")
    degrees, minutes, seconds = m.group(f"deg{n}"), m.group(f"min{n}"), m.group(f"sec{n}")
    if minutes is not None and "." in degrees:
        raise ValueError(f"decimal degrees with minutes on the {what}")
    if seconds is not None and "." in minutes:
        raise ValueError(f"decimal minutes with seconds on the {what}")
    if (minutes is not None and float(minutes) >= 60) or (seconds is not None and float(seconds) >= 60):
        raise ValueError(f"minutes and seconds are under 60 on the {what}")
    value = float(degrees) + float(minutes or 0) / 60.0 + float(seconds or 0) / 3600.0
    if value > limit:
        raise ValueError(f"the {what} is out of range")
    negative = sign == "-" or letter == letters[1]
    return -value if negative and value else value


def parse_coordinates(text: str) -> tuple[float, float]:
    """Latitude and longitude in decimal degrees from every format in NAV-8: "51.5, -0.12",
    "51.5 -0.12", "51.5N 0.12W", "N51.5 W0.12" and "51°30′N 0°07′W". The latitude comes
    first. S and W, or a minus sign, are negative; both together are refused. The near
    variants people type are read too: ' and " for the prime marks, seconds with decimals.
    Raises ValueError for anything out of range or that could be read two ways."""
    cleaned = str(text).strip().lower()
    for old, new in (("′′", '"'), ("''", '"'), ("′", "'"), ("’", "'"), ("‘", "'"), ("`", "'"), ("″", '"'),
                     ("”", '"'), ("“", '"'), ("−", "-"), ("º", "°"), ("˚", "°")):
        cleaned = cleaned.replace(old, new)
    error = ValueError(f"not coordinates: {text!r}")
    for pattern in _PAIRS:
        m = pattern.fullmatch(cleaned)
        if m:
            try:
                return _value(m, "1", "ns", 90.0, "latitude"), _value(m, "2", "ew", 180.0, "longitude")
            except ValueError as e:
                error = e
    raise error
