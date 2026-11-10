"""World state: location, heading, zoom, step and the link between them.

The three orientations (NAV-3, NAV-11, NAV-12, P2-T1a):

* north-fixed: the user always faces north. The arrow keys step north, south,
  east and west; a step that would reach a pole is blocked (NAV-1, DP42).
* cardinal: the user faces north, east, south or west. Up moves forward and
  Down back. Facing east or west, the move follows the line of latitude, as in
  north-fixed (DP69). Facing north or south, it follows the meridian and may
  carry on over the pole, coming out on the meridian 180 degrees away, facing
  the other way. Left and Right turn 90 degrees.
* free: the user faces any bearing. Up and Down follow the shortest line on
  the ellipsoid; the heading on arrival is the direction of travel at the end,
  and moving back keeps facing the same way. Left and Right turn by the turn
  amount the session gives.

Movement mode is kept ready for later phases (NAV-2, NAV-13, PLT-5).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from mapcore.geo import geodesy
from mapcore.geo.formats import METRES_PER_MILE, METRES_PER_YARD

DEFAULT_ZOOMS = (100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000,
                 250000, 500000, 1000000, 2500000, 10000000)
DEFAULT_STEPS = (10, 25, 50, 100, 250, 500, 1000, 5000, 25000, 100000, 250000, 1000000)

DIRECTIONS = {"north": ("meridian", 1), "south": ("meridian", -1),
              "east": ("parallel", 1), "west": ("parallel", -1)}
ORIENTATIONS = ("north-fixed", "cardinal", "free")   # the order the orientation key cycles through
FACING = ("cardinal", "free")
# What the arrow keys do in a facing orientation: Up and Down move, Left and Right turn.
FACING_KEYS = {"north": ("move", 1), "south": ("move", -1), "west": ("turn", -1), "east": ("turn", 1)}


def norm_heading(degrees: float) -> float:
    """A heading from 0 up to 360, with tiny rounding errors taken out, so 359.9999999 is 0."""
    h = round(float(degrees) % 360.0, 9)
    return 0.0 if h >= 360.0 else h


def nearest_cardinal(heading: float) -> float:
    """The nearest of north, east, south and west. Exactly half way, it turns clockwise."""
    return norm_heading(math.floor(norm_heading(heading) / 90.0 + 0.5) * 90.0)


def _imperial_metres(pairs) -> tuple:
    """[[100, "yd"], [0.5, "mi"], ...] in metres."""
    return tuple(n * (METRES_PER_YARD if unit == "yd" else METRES_PER_MILE) for n, unit in pairs)


def nearest_index(values, target: float) -> int:
    """Index of the value nearest to target (ties go to the smaller)."""
    return min(range(len(values)), key=lambda i: (abs(values[i] - target), values[i]))


def parse_lat_lon(text: str) -> tuple[float, float]:
    """"51.2,1.2" (latitude then longitude, in decimal degrees, south and west negative)
    as numbers. Raises ValueError for anything else. Used by the shells' start option
    for testing, --at on the desktop and ?at= in the web address."""
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) != 2:
        raise ValueError(f"expected latitude,longitude, not {text!r}")
    lat, lon = float(parts[0]), float(parts[1])
    if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
        raise ValueError(f"latitude or longitude out of range: {text!r}")
    return lat, lon


@dataclass
class StepResult:
    """What one move did. moved is False when blocked (the blocked sound, no speech).
    turned is True for a turn on the spot, which moves nothing. pole is "north" or
    "south" when the move went over that pole, so the new heading can be said (NAV-3)."""
    moved: bool
    lat: float
    lon: float
    heading: float
    path: tuple = ()
    turned: bool = False
    pole: str | None = None


@dataclass
class WorldState:
    lat: float = 52.0
    lon: float = -1.0
    heading: float = 0.0
    zoom_list: tuple = DEFAULT_ZOOMS
    step_list: tuple = DEFAULT_STEPS
    zoom_index: int = 5
    step_index: int = 3
    link: bool = False
    orientation: str = "north-fixed"
    movement_mode: str = "stepping"
    # The zoom and step lists for each unit system: {"metric": (zooms, steps), "imperial": ...}
    lists: dict = field(default_factory=dict)

    @classmethod
    def from_defaults(cls, d: dict) -> "WorldState":
        zooms = tuple(d.get("zoom_list_m", DEFAULT_ZOOMS))
        steps = tuple(d.get("step_list_m", DEFAULT_STEPS))
        w = d.get("world", {})
        st = d.get("start", {})
        lists = {"metric": (zooms, steps)}
        if d.get("zoom_list_imperial") and d.get("step_list_imperial"):
            lists["imperial"] = (_imperial_metres(d["zoom_list_imperial"]), _imperial_metres(d["step_list_imperial"]))
        return cls(lat=st.get("lat", 52.0), lon=geodesy.wrap_lon(st.get("lon", -1.0)),
                   zoom_list=zooms, step_list=steps, lists=lists,
                   zoom_index=nearest_index(zooms, w.get("zoom_m", 5000)),
                   step_index=nearest_index(steps, w.get("step_m", 100)),
                   link=bool(w.get("link_step_to_zoom", False)))

    @property
    def zoom_m(self) -> float:
        return self.zoom_list[self.zoom_index]

    @property
    def step_m(self) -> float:
        return self.step_list[self.step_index]

    # Zoom and step ---------------------------------------------------------------
    def use_units(self, system: str) -> None:
        """Use the zoom and step lists of a unit system, moving to the nearest sizes in
        them (DP136). Nautical miles, and any system without its own lists, use metric."""
        zooms, steps = self.lists.get(system) or self.lists.get("metric") or (self.zoom_list, self.step_list)
        if (zooms, steps) == (self.zoom_list, self.step_list):
            return
        zoom_m, step_m = self.zoom_m, self.step_m
        self.zoom_list, self.step_list = zooms, steps
        self.zoom_index = nearest_index(zooms, zoom_m)
        self.step_index = nearest_index(steps, zoom_m / 4) if self.link else nearest_index(steps, step_m)

    def change_zoom(self, direction: int) -> bool:
        """+1 zooms out (larger distance), -1 zooms in. False at the end of the list."""
        i = self.zoom_index + direction
        if not 0 <= i < len(self.zoom_list):
            return False
        self.zoom_index = i
        if self.link:  # the step is a quarter of the zoom distance (NAV-2)
            self.step_index = nearest_index(self.step_list, self.zoom_m / 4)
        return True

    def change_step(self, direction: int) -> bool:
        i = self.step_index + direction
        if not 0 <= i < len(self.step_list):
            return False
        self.step_index = i
        if self.link:  # the zoom is four steps
            self.zoom_index = nearest_index(self.zoom_list, self.step_m * 4)
        return True

    def set_link(self, on: bool) -> None:
        self.link = on
        if on:
            self.step_index = nearest_index(self.step_list, self.zoom_m / 4)

    # Stepping --------------------------------------------------------------------
    def step(self, direction: str, turn_deg: float = 15.0) -> StepResult:
        """What an arrow key does. In north-fixed, a move north, south, east or west.
        In a facing orientation, "north" (Up) moves forward, "south" (Down) back, and
        "west" and "east" (Left and Right) turn: 90 degrees in cardinal facing,
        turn_deg in free facing (NAV-3)."""
        if self.orientation not in FACING:
            return self._step_north_fixed(direction)
        action, sign = FACING_KEYS[direction]
        if action == "turn":
            return self.turn(sign * (90.0 if self.orientation == "cardinal" else turn_deg))
        return self.forward(sign)

    def _step_north_fixed(self, direction: str) -> StepResult:
        """One north-fixed move: north/south along the meridian, east/west along the
        line of latitude, across the 180 degree line, blocked at the poles (NAV-1)."""
        kind, sign = DIRECTIONS[direction]
        fn = geodesy.step_meridian if kind == "meridian" else geodesy.step_parallel
        mv = fn(self.lat, self.lon, sign * self.step_m)
        if mv is None:
            return StepResult(False, self.lat, self.lon, self.heading)
        self.lat, self.lon = mv.lat, mv.lon
        return StepResult(True, mv.lat, mv.lon, mv.heading, mv.path)   # the direction of travel

    def forward(self, sign: int = 1, metres: float | None = None) -> StepResult:
        """Move forward (sign 1) or back (sign -1) by the step, or by metres if given (Go to,
        P2-T17r), in a facing orientation. Moving back keeps facing the same way: the heading
        is the direction of travel on arrival, turned round."""
        if self.orientation not in FACING:
            return self._step_north_fixed("north" if sign > 0 else "south")
        distance = self.step_m if metres is None else metres
        travel = norm_heading(self.heading if sign > 0 else self.heading + 180.0)
        if self.orientation == "cardinal" and travel in (90.0, 270.0):
            # East and west follow the line of latitude, as in north-fixed (DP69).
            mv = geodesy.step_parallel(self.lat, self.lon, distance if travel == 90.0 else -distance)
            if mv is None:   # at a pole there is no east or west
                return StepResult(False, self.lat, self.lon, self.heading)
            self.lat, self.lon = mv.lat, mv.lon
            return StepResult(True, mv.lat, mv.lon, self.heading, mv.path)
        mv = geodesy.step_heading(self.lat, self.lon, travel, distance)
        arrival = mv.heading if sign > 0 else mv.heading + 180.0
        self.heading = nearest_cardinal(arrival) if self.orientation == "cardinal" else norm_heading(arrival)
        self.lat, self.lon = max(-90.0, min(90.0, mv.lat)), mv.lon
        return StepResult(True, self.lat, self.lon, self.heading, mv.path, pole=geodesy.pole_crossed(mv.path))

    def turn(self, degrees: float) -> StepResult:
        """Turn on the spot, clockwise for positive degrees. In cardinal facing the
        heading stays on north, east, south or west. North-fixed cannot turn: the
        result is blocked (NAV-12)."""
        if self.orientation not in FACING:
            return StepResult(False, self.lat, self.lon, self.heading)
        heading = self.heading + degrees
        self.heading = nearest_cardinal(heading) if self.orientation == "cardinal" else norm_heading(heading)
        return StepResult(False, self.lat, self.lon, self.heading, turned=True)

    def face(self, bearing: float) -> None:
        """Face an exact bearing, switching to free facing if needed (NAV-12, the typed bearing)."""
        self.orientation = "free"
        self.heading = norm_heading(bearing)

    def set_orientation(self, orientation: str) -> None:
        """Switch orientation without moving (NAV-11). North-fixed faces north;
        cardinal facing turns to the nearest of north, east, south and west."""
        if orientation not in ORIENTATIONS:
            raise ValueError(f"unknown orientation {orientation!r}")
        self.orientation = orientation
        if orientation == "north-fixed":
            self.heading = 0.0
        elif orientation == "cardinal":
            self.heading = nearest_cardinal(self.heading)

    def next_orientation(self, direction: int = 1) -> str:
        """Cycle north-fixed, cardinal facing, free facing, then north-fixed (NAV-12), or the
        other way with a direction of -1 (P2-T17l)."""
        i = ORIENTATIONS.index(self.orientation) if self.orientation in ORIENTATIONS else (-1 if direction > 0 else 0)
        self.set_orientation(ORIENTATIONS[(i + direction) % len(ORIENTATIONS)])
        return self.orientation

    def step_many(self, directions) -> list[StepResult]:
        """Carry out every queued move; the caller describes only the last place (ANN-3)."""
        return [self.step(d) for d in directions]

    # Saving (PLT-5) --------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"lat": self.lat, "lon": self.lon, "heading": self.heading,
                "zoom_m": self.zoom_m, "step_m": self.step_m, "link": self.link,
                "orientation": self.orientation, "movement_mode": self.movement_mode}

    def restore(self, d: dict) -> None:
        self.lat = max(-90.0, min(90.0, float(d["lat"])))
        self.lon = geodesy.wrap_lon(float(d["lon"]))
        self.heading = norm_heading(d.get("heading", 0.0))
        self.zoom_index = nearest_index(self.zoom_list, d.get("zoom_m", self.zoom_m))
        self.step_index = nearest_index(self.step_list, d.get("step_m", self.step_m))
        self.link = bool(d.get("link", False))
        orientation = d.get("orientation", self.orientation)
        if orientation in ORIENTATIONS:
            self.set_orientation(orientation)
            if orientation == "free":
                self.heading = norm_heading(d.get("heading", 0.0))
        self.movement_mode = d.get("movement_mode", self.movement_mode)
