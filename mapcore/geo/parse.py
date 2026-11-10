"""Reading what the user types: a bearing (NAV-12) and coordinates (NAV-8).

Both refuse anything out of range or that could be read two ways, with a
ValueError. The session turns the error into the words from the templates, which
list what is accepted.
"""
from __future__ import annotations

import re

from mapcore.geo.formats import METRES_PER_MILE, METRES_PER_YARD, POINTS_32

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


def _amount(n: str) -> str:
    """degrees [° or d [minutes ′ or m [seconds ″ or s]]]. Minutes and seconds need their own
    marks, so "51.5 0.12" is two numbers, not minutes, and "48 51 30 N" is refused: with spaces
    alone it is not clear which numbers are minutes (the PO's answer, 8 November 2026)."""
    return (rf"(?P<deg{n}>{_NUMBER})\s*(?:[°d]\s*"
            rf"(?:(?P<min{n}>{_NUMBER})\s*['m]\s*(?:(?P<sec{n}>{_NUMBER})\s*[\"s]\s*)?)?)?")


def _component(n: str) -> str:
    """One coordinate: [sign] amount [letter]. A letter before the number is a direction to
    move in, not a hemisphere: "north 5", "n 5" (parse_goto)."""
    return rf"(?P<sign{n}>[-+])?\s*{_amount(n)}(?:\s*(?P<post{n}>[nsew]))?"


# Between the two: a comma or semicolon, or a space, or nothing after a letter or a mark ("51.5N0.12W").
_SEP = r"(?:\s*[,;]\s*|\s+|(?<=[nsew°'\"dm]))"

_PAIR = re.compile(rf"{_component('1')}{_SEP}{_component('2')}")
_ONE = re.compile(rf"(?P<comma>[,;]\s*)?{_component('1')}")

# Moving by an amount: a direction, by word or letter, then degrees, once or for each axis,
# with or without a comma between: "north 5", "s 2, e 3", "west 0d 30m".
_DIRECTIONS = {"north": "n", "south": "s", "east": "e", "west": "w", "n": "n", "s": "s", "e": "e", "w": "w"}
_WAY = r"north|south|east|west|[nsew]"
_MOVE = re.compile(rf"(?P<way1>{_WAY})\s*{_amount('1')}(?:(?:\s*,\s*|\s*)(?P<way2>{_WAY})\s*{_amount('2')})?")


# Forward and back by a distance, in cardinal and free facing (P2-T17r, DP161): "f 24", "F24mi240yds",
# "back 24 km 50 m". A number alone is in the user's own distance unit; units may be typed, one or more.
_AHEAD = re.compile(r"(?P<way>forwards?|f|backwards?|backward|back|b)\s*(?P<amount>.+)")
_UNITS = {"km": 1000.0, "kilometre": 1000.0, "kilometres": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
          "mi": METRES_PER_MILE, "mile": METRES_PER_MILE, "miles": METRES_PER_MILE,
          "m": 1.0, "metre": 1.0, "metres": 1.0, "meter": 1.0, "meters": 1.0,
          "yds": METRES_PER_YARD, "yd": METRES_PER_YARD, "yard": METRES_PER_YARD, "yards": METRES_PER_YARD}
_UNIT = "|".join(sorted(_UNITS, key=len, reverse=True))   # the longest first: "mi" before "m"
_PART = re.compile(rf"(?P<n>{_NUMBER})\s*(?P<unit>{_UNIT})\s*(?:,\s*)?(?:and\s+)?")


def _distance(text: str, unit_m: float) -> float:
    """Metres from "24", in the user's unit, or from parts each with a unit: "24mi240yds",
    "24 km 50 m", "2 miles and 100 yards". Each unit at most once."""
    text = text.strip()
    if re.fullmatch(_NUMBER, text):
        return float(text) * unit_m
    metres, seen, at = 0.0, set(), 0
    while at < len(text):
        m = _PART.match(text, at)
        if not m:
            raise ValueError(f"not a distance: {text!r}")
        unit = _UNITS[m.group("unit")]
        if unit in seen:
            raise ValueError(f"one unit twice: {text!r}")
        seen.add(unit)
        metres += float(m.group("n")) * unit
        at = m.end()
    return metres


def _clean(text: str) -> str:
    cleaned = str(text).strip().lower()
    for old, new in (("′′", '"'), ("''", '"'), ("′", "'"), ("’", "'"), ("‘", "'"), ("`", "'"), ("″", '"'),
                     ("”", '"'), ("“", '"'), ("−", "-"), ("º", "°"), ("˚", "°")):
        cleaned = cleaned.replace(old, new)
    return cleaned


def _degrees(m: re.Match, n: str, what: str) -> float:
    degrees, minutes, seconds = m.group(f"deg{n}"), m.group(f"min{n}"), m.group(f"sec{n}")
    if minutes is not None and "." in degrees:
        raise ValueError(f"decimal degrees with minutes on the {what}")
    if seconds is not None and "." in minutes:
        raise ValueError(f"decimal minutes with seconds on the {what}")
    if (minutes is not None and float(minutes) >= 60) or (seconds is not None and float(seconds) >= 60):
        raise ValueError(f"minutes and seconds are under 60 on the {what}")
    return float(degrees) + float(minutes or 0) / 60.0 + float(seconds or 0) / 3600.0


def _value(m: re.Match, n: str, letters: str, limit: float, what: str) -> float:
    letter = (m.group(f"post{n}") or "").lower()
    if letter and letter not in letters:
        raise ValueError(f"{letter.upper()} cannot be the {what}")
    sign = m.group(f"sign{n}")
    if letter and sign:
        raise ValueError(f"a sign and a letter on the {what} could be read two ways")
    value = _degrees(m, n, what)
    if value > limit:
        raise ValueError(f"the {what} is out of range")
    negative = sign == "-" or letter == letters[1]
    return -value if negative and value else value


def parse_coordinates(text: str) -> tuple[float, float]:
    """Latitude and longitude in decimal degrees from every format in NAV-8: "51.5, -0.12",
    "51.5 -0.12", "51.5N 0.12W" and "51°30′N 0°07′W". The latitude comes first. S and W, or a
    minus sign, are negative; both together are refused. The near variants people type are read
    too: ' and " for the prime marks, D, M and S for degrees, minutes and seconds, in either case
    ("48D 30M 15S S"), and seconds with decimals. Raises ValueError for anything out of range or
    that could be read two ways."""
    m = _PAIR.fullmatch(_clean(text))
    if not m:
        raise ValueError(f"not coordinates: {text!r}")
    return _value(m, "1", "ns", 90.0, "latitude"), _value(m, "2", "ew", 180.0, "longitude")


def parse_goto(text: str, unit_m: float = 1000.0) -> tuple[str, float | None, float | None]:
    """What is typed in Go to (NAV-8, the PO's answers of 8 November 2026), as one of:

    * ("to", lat, lon): both coordinates, as parse_coordinates reads them.
    * ("to", lat, None): one number, the latitude; the longitude stays. One with E or W is
      the longitude, as there is no other way to read it.
    * ("to", None, lon): a comma, then one number: the longitude; the latitude stays.
    * ("by", north, east): a direction, by word or letter, then degrees, for one axis or both,
      with or without a comma: "north 5", "s 2 e 3", "west 10, n 1". South and west are
      negative. A direction comes first; a number first is always where to go, so "-33" is
      33 degrees south and nothing clashes.
    * ("ahead", metres, None): f or forward, or b or back, then a distance; back is negative
      (DP161). A number alone is in unit_m, the user's own unit: "f 24" is 24 kilometres in
      metric. Units may be typed instead: km, mi, m and yds, or their words, and several
      together: "F24mi240yds", "b 24km 50m". Only cardinal and free facing use it.

    Raises ValueError for anything else."""
    cleaned = _clean(text)
    m = _AHEAD.fullmatch(cleaned)
    if m:
        metres = _distance(m.group("amount"), unit_m)
        return "ahead", (-metres if m.group("way").startswith("b") else metres), None
    m = _MOVE.fullmatch(cleaned)
    if m:
        moves = {"n": 0.0, "e": 0.0}
        ways = [w for w in ("1", "2") if m.group(f"way{w}")]
        axes = set()
        for n in ways:
            way = _DIRECTIONS[m.group(f"way{n}")]
            axis = "n" if way in "ns" else "e"
            if axis in axes:
                raise ValueError("two amounts for one direction")
            axes.add(axis)
            value = _degrees(m, n, "amount")
            moves[axis] = -value if way in "sw" else value
        return "by", moves["n"], moves["e"]
    m = _ONE.fullmatch(cleaned)
    if m:
        longitude = bool(m.group("comma")) or (m.group("post1") or "") in ("e", "w")
        if longitude:
            return "to", None, _value(m, "1", "ew", 180.0, "longitude")
        return "to", _value(m, "1", "ns", 90.0, "latitude"), None
    lat, lon = parse_coordinates(text)
    return "to", lat, lon
