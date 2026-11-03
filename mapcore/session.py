"""The map session: the one object the shells talk to (AD-2, architecture 5.3).

A shell sends a command name and its arguments to run(), and gets a Response
back: what to announce, and whether the map, the Information panel or Details
need refreshing, where focus should go, a dialog to open, or an action such as
exit. The shells then ask for scene(), panel() and details() as needed.

This is the spike S5 session: it turns a globe of Natural Earth countries. The
stepping, orientation and hierarchy of the full design arrive in Phase 1.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

import mapcore
from mapcore.commands import registry
from mapcore.describe import say
from mapcore.geo import geodesy
from mapcore.geo import phase0_words as words
from mapcore.render import globe
from mapcore.store.world_sample import WorldSample

DEFAULTS_FILE = Path(__file__).resolve().parent / "defaults.yaml"
SPEECH, BRAILLE = "speech", "braille"
ASSERTIVE, POLITE = "assertive", "polite"


@dataclass
class Response:
    announcements: list[dict] = field(default_factory=list)
    redraw: bool = False
    panel_stale: bool = False
    details_stale: bool = False
    focus: dict | None = None
    dialog: dict | None = None
    action: str | None = None

    def speak(self, text: str, priority: str = POLITE) -> "Response":
        self.announcements.append({"text": text, "channel": SPEECH, "priority": priority})
        return self

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class State:
    lat: float
    lon: float
    zoom: int  # index into the zoom list
    selected: str | None = None


class MapSession:
    def __init__(self, platform: str = "desktop", world: WorldSample | None = None):
        self.platform = platform
        self.defaults = yaml.safe_load(DEFAULTS_FILE.read_text(encoding="utf-8"))
        self.zooms = self.defaults["zooms"]
        self.world = world or WorldSample.load()
        self.geometry = globe.GlobeGeometry.from_world(self.world)
        self.theme = globe.load_theme()
        start = self.defaults["start"]
        self.state = State(lat=start["lat"], lon=start["lon"], zoom=start["zoom"] - 1)
        self.last_spoken: str | None = None
        self.last_frame: dict | None = None
        self.paint_ms: float | None = None
        self.startup_ms: float | None = None
        self.map_size: tuple[int, int] = (800, 600)  # until the shell first draws
        self._handlers = {
            "globe.north": lambda **a: self._turn(1, 0),
            "globe.south": lambda **a: self._turn(-1, 0),
            "globe.east": lambda **a: self._turn(0, 1),
            "globe.west": lambda **a: self._turn(0, -1),
            "zoom.in": lambda **a: self._zoom(1),
            "zoom.out": lambda **a: self._zoom(-1),
            "where.am_i": self._where_am_i,
            "where.coordinates": self._coordinates,
            "where.visible": self._visible,
            "panel.within": lambda **a: Response(focus={"region": "panel", "group": "within"}, panel_stale=True),
            "panel.nearby": lambda **a: Response(focus={"region": "panel", "group": "nearby"}, panel_stale=True),
            "panel.select": self._select,
            "details.show": lambda **a: Response(focus={"region": "details"}, details_stale=True),
            "focus.menu": lambda **a: Response(focus={"region": "menu"}),
            "focus.map": lambda **a: Response(focus={"region": "map"}),
            "speech.repeat": self._repeat,
            "speech.braille_test": self._braille_test,
            "help.keys": self._help_keys,
            "help.about": self._about,
            "diagnostics.timing": self._timing,
            "map.click": self._click,
            "app.exit": lambda **a: Response(action="exit"),
        }

    # The shell-facing interface ------------------------------------------

    def handles(self, name: str) -> bool:
        return name in self._handlers

    def start(self) -> Response:
        return self._record(Response(redraw=True, panel_stale=True, details_stale=True)
                            .speak(say("start", place=self._place_name()), POLITE))

    def run(self, name: str, **args) -> Response:
        handler = self._handlers[name]  # KeyError for an unknown command
        return self._record(handler(**args))

    def run_many(self, commands: list[tuple[str, dict]]) -> Response:
        """Carry out several commands that arrived faster than they could be
        answered. Every one is carried out, but only the last one's
        announcements are kept, so speech never falls behind (ANN-3)."""
        merged = Response()
        for name, args in commands:
            r = self.run(name, **args)
            merged.announcements = r.announcements or merged.announcements
            merged.redraw |= r.redraw
            merged.panel_stale |= r.panel_stale
            merged.details_stale |= r.details_stale
            merged.focus = r.focus or merged.focus
            merged.dialog = r.dialog or merged.dialog
            merged.action = r.action or merged.action
        return merged

    def scene(self, width: int, height: int) -> dict:
        self.map_size = (width, height)  # for the size of the visible map
        current = self._current()
        frame = globe.build_scene(self.geometry, self._view(), width, height,
                                  current=current.id if current else None,
                                  highlight=self.state.selected, theme=self.theme)
        self.last_frame = {"project_ms": frame["project_ms"], "points": frame["points"]}
        return frame

    def panel(self) -> list[dict]:
        """The Information panel groups (UX section 6), as plain data."""
        current = self._current()
        within = ([{"id": current.id, "label": current.name}] if current else []) + \
                 [{"id": "earth", "label": say("panel.earth")}]
        nearby = [
            {"id": c.id, "label": say("panel.nearby_item", name=c.name, distance=words.distance_text(km),
                                      direction=words.compass_point(b))}
            for c, km, b in self.world.nearest(self.state.lat, self.state.lon,
                                               count=self.defaults["nearby_count"],
                                               exclude=current.id if current else None)
        ]
        return [
            {"id": "within", "label": say("panel.within"), "items": within, "empty": ""},
            {"id": "nearby", "label": say("panel.nearby"), "items": nearby, "empty": ""},
            {"id": "crossed", "label": say("panel.crossed"), "items": [], "empty": say("panel.empty_later")},
        ]

    def details(self) -> str:
        """Details of the selected item, or of the country under the centre."""
        s = self.state
        target = self.state.selected
        if target == "earth":
            return "\n".join([say("details.earth"), say("details.earth_note")])
        country = self.world.by_id(target) if target else self._current()
        if country is None:
            return "\n".join([say("details.sea"), say("details.sea_note"),
                              say("details.centre", value=words.coordinates_text(s.lat, s.lon))])
        lines = [country.name]
        if country.long_name != country.name:
            lines.append(say("details.long_name", value=country.long_name))
        lines += [
            say("details.sovereign", value=country.sovereign),
            say("details.continent", value=country.continent),
            say("details.subregion", value=country.subregion),
            say("details.population", value=f"{country.population:,}"),
            say("details.label_point", value=words.coordinates_text(country.centre_lat, country.centre_lon)),
        ]
        if target and (self._current() is None or self._current().id != target):
            km = geodesy.distance_m(s.lat, s.lon, country.centre_lat, country.centre_lon) / 1000
            b = geodesy.bearing_deg(s.lat, s.lon, country.centre_lat, country.centre_lon)
            lines.append(say("details.from_centre", distance=words.distance_text(km),
                             direction=words.compass_point(b)))
        lines.append(say("details.source", value=self.world.source))
        return "\n".join(lines)

    def registry(self) -> dict:
        return registry.describe(self.platform)

    def map_label(self) -> str:
        """The map region's accessible name: the place under the centre. Shells
        update it only while the map does not have focus, so the screen reader
        does not say each place twice while turning."""
        return say("map_label", place=self._place_name())

    def words(self) -> dict:
        """The window's own words: region names, title and button labels."""
        return dict(say("ui"))

    def frame_painted(self, paint_ms: float) -> None:
        """The shell reports how long its last paint took, for the timing report."""
        self.paint_ms = paint_ms

    def startup_took(self, startup_ms: float) -> None:
        self.startup_ms = startup_ms

    # Internals -------------------------------------------------------------

    def _record(self, response: Response) -> Response:
        spoken = [a["text"] for a in response.announcements if a["channel"] == SPEECH]
        if spoken:
            self.last_spoken = " ".join(spoken)
        return response

    def _view(self) -> globe.View:
        return globe.View(lat=self.state.lat, lon=self.state.lon, scale=self.zooms[self.state.zoom]["scale"])

    def _current(self):
        return self.world.country_at(self.state.lat, self.state.lon)

    def _place_name(self) -> str:
        c = self._current()
        return c.name if c else say("place_sea")

    def _step(self) -> float:
        return self.zooms[self.state.zoom]["step"]

    def _step_text(self) -> str:
        step = self._step()
        if step == 0.5:
            return say("step_half")
        if step == 1:
            return say("step_one_degree")
        return say("step_degrees", value=f"{step:g}")

    def _zoom_text(self) -> str:
        return say("zoom", zoom=self.state.zoom + 1, zooms=len(self.zooms), step=self._step_text())

    def _moved(self) -> Response:
        self.state.selected = None
        return Response(redraw=True, panel_stale=True, details_stale=True)

    def _turn(self, north: int, east: int) -> Response:
        s = self.state
        step = self._step()
        r = self._moved()
        if north:
            lat = s.lat + north * step
            pole = None
            if lat >= 90:
                lat, pole = 90, "pole_north"
            elif lat <= -90:
                lat, pole = -90, "pole_south"
            s.lat = round(lat, 6)
            if pole:
                return r.speak(say(pole, place=self._place_name()), ASSERTIVE)
        if east:
            s.lon = round(geodesy.wrap_lon(s.lon + east * step), 6)
        return r.speak(self._place_name(), ASSERTIVE)

    def _zoom(self, direction: int) -> Response:
        s = self.state
        new = s.zoom + direction
        if new < 0 or new >= len(self.zooms):
            key = "zoom_whole" if new < 0 else "zoom_closest"
            return Response().speak(say(key, zoom=self._zoom_text()), ASSERTIVE)
        s.zoom = new
        r = Response(redraw=True)
        text = self._zoom_text()
        if new == 0:
            text = say("zoom_whole", zoom=text)
        elif new == len(self.zooms) - 1:
            text = say("zoom_closest", zoom=text)
        return r.speak(text, ASSERTIVE)

    def _where_am_i(self, **_a) -> Response:
        s = self.state
        return Response().speak(say("where_am_i", place=self._place_name(),
                                    coordinates=words.coordinates_text(s.lat, s.lon), zoom=self._zoom_text()),
                                ASSERTIVE)

    def _coordinates(self, **_a) -> Response:
        return Response().speak(words.coordinates_text(self.state.lat, self.state.lon), ASSERTIVE)

    def _visible(self, **_a) -> Response:
        extent = globe.visible_extent(self._view(), *self.map_size)
        if extent is None:
            return Response().speak(say("visible_globe"), ASSERTIVE)
        across, down = (words.km_number(a * geodesy.R_MEAN_M / 1000) for a in extent)
        return Response().speak(say("visible_area", width=across, height=down), ASSERTIVE)

    def _repeat(self, **_a) -> Response:
        return Response().speak(self.last_spoken or say("nothing_to_repeat"), ASSERTIVE)

    def _braille_test(self, **_a) -> Response:
        fallback = say("braille_web") if self.platform == "web" else say("braille_fallback")
        r = Response()
        r.announcements.append({"text": say("braille_test", place=self._place_name()), "channel": BRAILLE,
                                "priority": POLITE, "fallback": fallback})
        return r

    def _select(self, item: str | None = None, **_a) -> Response:
        if item == self.state.selected:
            return Response()
        self.state.selected = item
        return Response(redraw=True, details_stale=True)

    def _click(self, x: float, y: float, width: float, height: float, **_a) -> Response:
        point = globe.from_screen(self._view(), width, height, x, y)
        if point is None:
            return Response().speak(say("off_globe"), ASSERTIVE)
        self.state.lat, self.state.lon = round(point[0], 6), round(point[1], 6)
        return self._moved().speak(self._place_name(), ASSERTIVE)

    def _help_keys(self, platform: str | None = None, **_a) -> Response:
        platform = platform or self.platform
        lines = [say("dialogs.keys_intro"), ""]
        for c in registry.for_platform(platform):
            if c.pointer:
                continue
            if c.key:
                lines.append(say("dialogs.keys_line", label=c.label, key=c.key))
            else:
                lines.append(say("dialogs.keys_menu_only", label=c.label, menu=c.menu))
        return Response(dialog={"title": say("dialogs.keys_title"), "text": "\n".join(lines)})

    def _about(self, **_a) -> Response:
        return Response(dialog={"title": say("dialogs.about_title"),
                                "text": say("dialogs.about_text", version=mapcore.version())})

    def _timing(self, **_a) -> Response:
        paint_ms, startup_ms = self.paint_ms, self.startup_ms
        r = Response()
        if self.last_frame:
            paint = "an unknown number of" if paint_ms is None else f"{round(paint_ms):d}"
            r.speak(say("timing", project=f"{round(self.last_frame['project_ms']):d}", paint=paint,
                        points=f"{self.last_frame['points']:,}"))
        if startup_ms is not None:
            r.speak(say("timing_startup", seconds=f"{startup_ms / 1000:.1f}"))
        return r
