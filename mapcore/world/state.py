"""World state: location, heading, zoom, step and the link between them.

Phase 1 is north-fixed: the heading is always north. Orientation and movement
mode are kept ready for Phase 2 (NAV-1, NAV-2, NAV-13, PLT-5).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from mapcore.geo import geodesy
from mapcore.geo.formats import METRES_PER_MILE, METRES_PER_YARD

DEFAULT_ZOOMS = (100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000,
                 250000, 500000, 1000000, 2500000, 10000000)
DEFAULT_STEPS = (10, 25, 50, 100, 250, 500, 1000, 5000, 25000, 100000, 250000, 1000000)

DIRECTIONS = {"north": ("meridian", 1), "south": ("meridian", -1),
              "east": ("parallel", 1), "west": ("parallel", -1)}


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
    """What one move did. moved is False when blocked (the blocked sound, no speech)."""
    moved: bool
    lat: float
    lon: float
    heading: float
    path: tuple = ()


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
    def step(self, direction: str) -> StepResult:
        """One north-fixed move: north/south along the meridian, east/west along the
        line of latitude, across the 180 degree line, blocked at the poles (NAV-1)."""
        kind, sign = DIRECTIONS[direction]
        fn = geodesy.step_meridian if kind == "meridian" else geodesy.step_parallel
        mv = fn(self.lat, self.lon, sign * self.step_m)
        if mv is None:
            return StepResult(False, self.lat, self.lon, self.heading)
        self.lat, self.lon = mv.lat, mv.lon
        return StepResult(True, mv.lat, mv.lon, mv.heading, mv.path)

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
        self.heading = float(d.get("heading", 0.0))
        self.zoom_index = nearest_index(self.zoom_list, d.get("zoom_m", self.zoom_m))
        self.step_index = nearest_index(self.step_list, d.get("step_m", self.step_m))
        self.link = bool(d.get("link", False))
        self.orientation = d.get("orientation", self.orientation)
        self.movement_mode = d.get("movement_mode", self.movement_mode)
