"""The map session: the one object both shells talk to (AD-2, architecture 5.3).

A shell sends a command name and its arguments to run(), or a key to press(),
and gets a Response back: what to announce, which earcons to play, and whether
the map, the Information panel or Details need refreshing, where focus should
go, a dialog to open, or an action such as exit. The shells then ask for
scene(), panel() and details() as needed.

Phase 1 (P1-T7, P1-T8): the location is a WorldState stepped north-fixed over
the packs through the Store. Every word comes from the templates (3.4).
"""
from __future__ import annotations

import copy
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

import mapcore
from mapcore import settings as settings_mod
from mapcore.commands import registry
from mapcore.describe import describer, say, templates, words
from mapcore.geo import geodesy, parse
from mapcore.layers import LayerCatalogue
from mapcore.layers.visible import VisibleRule
from mapcore.world import WorldState
from mapcore.world.state import nearest_index

DEFAULTS_FILE = Path(__file__).resolve().parent / "defaults.yaml"
SPEECH, BRAILLE = "speech", "braille"
ASSERTIVE, POLITE = "assertive", "polite"
HISTORY_LIMIT = 200  # at least the last 50 (ANN-4)
PLACE_LIMIT = 100    # places kept to go back to (NAV-10, DP142)
# The commands whose announcements belong to a place, so Enter in the announcement
# history can go back there (ANN-4, DP141). Help, settings and the like have none.
PLACE_COMMANDS = {"start", "release", "move.north", "move.south", "move.east", "move.west", "zoom.in", "zoom.out",
                  "step.larger", "step.smaller", "step.link", "where.am_i", "where.coordinates", "where.heading",
                  "where.visible", "map.click", "map.hover", "map.drag", "orientation.cycle", "turn.left",
                  "turn.right", "turn.fine_left", "turn.fine_right", "bearing.set", "goto.set", "history.back",
                  "history.forward", "history.go", "layers.set"}
REGIONS = ("map", "panel", "details", "menu")
# Holding an arrow key (DP129, DP140). The shells step on a timer of their own, at
# the times the core gives, so the clicks never wait for the map to be drawn.
HOLD_SILENCE_S = 1.5     # no key repeat from the system for this long: the key was let go unseen
HOLD_LOOKAHEAD_S = 2.0   # how far ahead the core says whether held steps will move (the web's clicks)


@dataclass
class Response:
    announcements: list[dict] = field(default_factory=list)
    earcons: list[str] = field(default_factory=list)
    redraw: bool = False
    panel_stale: bool = False
    details_stale: bool = False
    focus: dict | None = None
    dialog: dict | None = None
    action: str | None = None
    settings_changed: bool = False
    error: str | None = None    # a typed answer was refused: the box stays open and shows and says this

    def speak(self, text: str, priority: str = POLITE) -> "Response":
        self.announcements.append({"text": text, "channel": SPEECH, "priority": priority})
        return self

    def earcon(self, name: str) -> "Response":
        self.earcons.append(name)
        return self

    def to_dict(self) -> dict:
        return asdict(self)


class MapSession:
    def __init__(self, platform: str = "desktop", packs=None, store=None, settings: dict | None = None,
                 saved_state: dict | None = None, clock=time.perf_counter, start_at: str | None = None):
        from mapcore.store import Store

        self.platform = platform
        self.defaults = yaml.safe_load(DEFAULTS_FILE.read_text(encoding="utf-8"))
        self.store = store or Store(list(packs or []))
        self.settings = settings_mod.Settings.from_dict(settings)
        # The layers, with the user's changes from the settings in use (SCP-6, SCP-7).
        self.layers = LayerCatalogue(self.store.packs, lambda: self.settings.layers)
        # Which features are visible: layer, zoom range, size and view (NAV-13, P2-T4a).
        self.visible = VisibleRule(self.store, self.layers)
        self.all_off_here = False   # there are areas here, but every one is in a layer that is off (LOC-6)
        self.world = WorldState.from_defaults(self.defaults)
        self.world.use_units(self.settings["units"])   # before restoring, so the saved sizes are found exactly
        if saved_state:
            self.world.restore(saved_state)
        elif self.settings["link"]:
            self.world.set_link(True)
        self.world.link = bool(self.settings["link"]) if not saved_state else self.world.link
        self.settings.set("link", self.world.link)
        if start_at:   # "lat,lon" from the shell's start option; a bad one is ignored
            from mapcore.world.state import parse_lat_lon

            try:
                self.world.lat, self.world.lon = parse_lat_lon(start_at)
            except ValueError:
                pass
        self.clock = clock
        self.areas: list = []          # the areas at the last described place, smallest first
        self.last_spoken: str | None = None
        self.history: list[str] = []
        self.history_places: list[dict | None] = []   # where each entry was said, or None (DP141)
        self.back_places: list[dict] = []     # the places before each jump, newest last (NAV-10, DP142)
        self.forward_places: list[dict] = []  # the places went back from, newest last
        if saved_state:
            jumps = saved_state.get("jumps") or {}
            self.back_places = [p for p in jumps.get("back", []) if self._valid_place(p)][-PLACE_LIMIT:]
            self.forward_places = [p for p in jumps.get("forward", []) if self._valid_place(p)][-PLACE_LIMIT:]
        self.describing = False        # the key describer (Shift+F1)
        self.selected: str | None = None   # the Information panel item chosen, an area id
        self.panel_item: str | None = None  # the item last focused there, for F3 (DP106)
        self.held_moves = 0
        self.held_turns = 0               # turns made while Left or Right is held in a facing orientation
        self.holding: str | None = None   # the movement command whose key is down (DP140)
        self._repeat_due = 0.0             # when the held key next steps (DP129)
        self._drawn_at = -math.inf         # when the map was last drawn for a held key
        self.paint_ms: float | None = None
        self.startup_ms: float | None = None
        self.last_frame: dict | None = None
        self.map_size: tuple[int, int] = (800, 600)
        self.trace: list[dict] = []
        self._panel_cache: tuple | None = None
        self._scene = None
        self._handlers = {
            "move.north": lambda **a: self._move("north", **a),
            "move.south": lambda **a: self._move("south", **a),
            "move.east": lambda **a: self._move("east", **a),
            "move.west": lambda **a: self._move("west", **a),
            "zoom.out": lambda **a: self._zoom(+1),
            "zoom.in": lambda **a: self._zoom(-1),
            "step.larger": lambda **a: self._step_size(+1),
            "step.smaller": lambda **a: self._step_size(-1),
            "step.link": self._link,
            "where.am_i": self._where_am_i,
            "where.coordinates": self._coordinates,
            "where.heading": self._heading,
            "where.visible": self._visible,
            "focus.map": lambda **a: Response(focus={"region": "map"}),
            "focus.panel": self._focus_panel,
            "focus.details": lambda **a: Response(focus={"region": "details"}, details_stale=True),
            "focus.menu": lambda **a: Response(focus={"region": "menu"}),
            "panel.select": self._select,
            "speech.repeat": self._repeat,
            "speech.history": self._history,
            "speech.braille_test": self._braille_test,
            "sound.mute": self._mute,
            "orientation.cycle": self._orientation_cycle,
            "turn.left": lambda **a: self._turn(sign=-1),
            "turn.right": lambda **a: self._turn(sign=1),
            "turn.fine_left": lambda **a: self._turn("fine_turn_deg", -1),
            "turn.fine_right": lambda **a: self._turn("fine_turn_deg", 1),
            "bearing.type": self._bearing_type,
            "bearing.set": self._bearing_set,
            "goto.coordinates": self._goto_coordinates,
            "goto.set": self._goto_set,
            "history.back": lambda **a: self._go_through(self.back_places, self.forward_places),
            "history.forward": lambda **a: self._go_through(self.forward_places, self.back_places),
            "history.go": self._history_go,
            "settings.open": self._settings_open,
            "settings.set": self._settings_set,
            "layers.open": self._layers_open,
            "layers.check": self._layers_check,
            "layers.set": self._layers_set,
            "keys.remap": self._remap,
            "help.keys": self._help_keys,
            "help.describer": self._describer,
            "help.about": self._about,
            "help.about_data": self._about_data,
            "help.earcons": self._earcons_help,
            "sound.preview": self._preview,
            "diagnostics.copy": self._diagnostics,
            "diagnostics.timing": self._timing,
            "map.click": self._click,
            "map.zoom_to": self._zoom_to,
            "map.hover": self._hover,
            "map.drag": self._drag,
            "app.exit": lambda **a: Response(action="exit"),
        }

    # The shell-facing interface ------------------------------------------

    def handles(self, name: str) -> bool:
        return name in self._handlers

    def start(self) -> Response:
        """The first announcement: the place the application starts at."""
        self.areas = self._here()
        r = Response(redraw=True, panel_stale=True, details_stale=True)
        if not self.store.packs:
            r.speak(say("packs.none_installed"), ASSERTIVE)
            return self._record("start", r)
        r.speak(say("start", place=self._place_text()), POLITE)
        return self._record("start", r)

    def run(self, name: str, **args) -> Response:
        started = self.clock()
        handler = self._handlers[name]  # KeyError for an unknown command
        r = self._record(name, handler(**args), started)
        return r

    def run_many(self, commands: list[tuple[str, dict]]) -> Response:
        """Carry out several commands that arrived faster than they could be
        answered. Every one is carried out, but only the last one is described,
        so speech never falls behind (ANN-3)."""
        merged = Response()
        last = len(commands) - 1
        for i, (name, args) in enumerate(commands):
            args = dict(args)
            if i < last and registry.by_name(name).held:
                args["held"] = True
            r = self.run(name, **args)
            merged.announcements = r.announcements or merged.announcements
            merged.earcons = r.earcons or merged.earcons
            merged.redraw |= r.redraw
            merged.panel_stale |= r.panel_stale
            merged.details_stale |= r.details_stale
            merged.focus = r.focus or merged.focus
            merged.dialog = r.dialog or merged.dialog
            merged.action = r.action or merged.action
            merged.settings_changed |= r.settings_changed
            merged.error = r.error or merged.error
        return merged

    def press(self, key: str, region: str = "map") -> Response | None:
        """A key pressed in a region ("map", "panel", "details" or "menu").
        Returns None when the key is not one of ours, so the shell lets it through.
        In the key describer nothing is carried out: the key is only described."""
        command = registry.command_for_key(self.platform, key, region, self.settings.keys)
        if self.describing:
            if command is not None and command.name == "help.describer":
                return self.run("help.describer")
            return self._record("describe", Response().speak(self._describe_key(key), ASSERTIVE))
        if command is None:
            return None
        if command.name == "help.keys":
            return self.run("help.keys", region=region)
        return self.run(command.name)

    def _describe_key(self, key: str) -> str:
        """What a key does, wherever the focus is (PO feedback on checklist 2.2). Keys
        with only their standard job in a list or text, such as Tab or Down in the
        Information panel, are not described."""
        commands = registry.commands_for_key(self.platform, key, self.settings.keys)
        key = registry.key_text(key)
        if not commands:
            return say("describer.unassigned", key=key)
        if len(commands) == 1:
            return say("describer.key", key=key, label=commands[0].label)
        regions = templates()["describer"]["regions"]
        return say("describer.several", key=key, list=" ".join(
            say("describer.in_region", label=c.label, region=regions.get(c.region, c.region)) for c in commands))

    def release(self) -> Response:
        """The held movement key was let go: describe the place it ended at,
        and only that (ANN-3), and draw it."""
        self.holding = None
        if self.held_turns and not self.held_moves:
            self.held_turns = 0
            return self._record("release", Response(redraw=True, panel_stale=True).speak(
                say("movement.facing", heading=describer.facing_text(self.world)), ASSERTIVE))
        self.held_turns = 0
        if not self.held_moves:
            return Response()
        self.held_moves = 0
        self._drawn_at = self.clock()
        return self._record("release", self._arrived(Response(redraw=True)))

    # Holding a movement key (DP129, DP140) --------------------------------

    def hold_due(self) -> float | None:
        """Seconds until the held key's next step, or None when no key is held.
        The shell's own timer makes the step then, with run(name, held=True,
        repeat=True), whatever the system's key repeat does. The first comes
        after the repeat delay, then at the repeat rate."""
        if self.holding is None:
            return None
        return max(0.0, self._repeat_due - self.clock())

    def hold_info(self) -> dict | None:
        """The held key's timing for a shell that cannot ask hold_due() at once
        (the web page, whose core is in a worker): when the steps are due, from
        the press, and how many of the next steps will move, so the page can
        play each click at its due time without waiting for the worker."""
        if self.holding is None:
            return None
        rate = max(1, self.settings["repeat_rate"])
        limit = math.ceil(rate * HOLD_LOOKAHEAD_S) + 1
        probe = copy.copy(self.world)
        direction = self.holding.split(".", 1)[1]
        left = 0
        while left < limit:   # a turn on the spot ticks as a move does
            r = probe.step(direction, turn_deg=self.settings["turn_deg"])
            if not (r.moved or r.turned):
                break
            left += 1
        return {"command": self.holding, "delay_ms": float(self.settings["repeat_delay_ms"]),
                "every_ms": 1000.0 / rate, "left": left, "unlimited": left >= limit,
                "tick": not self.settings["mute"], "earcon": self.earcon_file("tick"),
                "silence_ms": HOLD_SILENCE_S * 1000}

    def _draw_due(self, now: float) -> bool:
        """While a key is held the map is drawn at most held_draw_rate times a second (DP140)."""
        if now - self._drawn_at >= 1.0 / max(1, self.settings["held_draw_rate"]) - 0.001:
            self._drawn_at = now
            return True
        return False

    def scene(self, width: int, height: int) -> dict:
        from mapcore.render import scene as scene_mod

        self.map_size = (width, height)
        if self._scene is None:
            self._scene = scene_mod.SceneBuilder(self.store)
        areas = self.areas
        current = areas[0].id if areas else None
        # A copy of the place: on the desktop the map is drawn in a thread of its
        # own while the held key steps on (P2-T14).
        frame = self._scene.build(copy.copy(self.world), width, height, current=current, highlight=self.selected,
                                  centre_cross=self.settings["centre_cross"],
                                  layers=self.visible.shown_layers(self.world.zoom_m),
                                  min_widths=self.visible.min_widths(self.world.zoom_m))
        self.last_frame = {k: frame[k] for k in ("project_ms", "choose_ms", "projecting_ms", "points")}
        return frame

    def scene_background(self) -> str:
        """The colour behind the map, for a shell to show before the first drawing is ready."""
        from mapcore.render import globe

        return globe.load_theme()["background"]

    def panel(self) -> list[dict]:
        """The Information panel groups (UX section 6), as plain data."""
        zoom = self.world.zoom_m
        shown = self.visible.shown_layers(zoom)
        heading = describer.facing(self.world)
        key = (self.world.lat, self.world.lon, self.settings["units"], self.settings["bearing"],
               self.settings["nearby_count"], zoom, shown, heading)
        if self._panel_cache and self._panel_cache[0] == key:
            return self._panel_cache[1]
        within = [{"id": a.id, "label": a.name, "level": 1} for a in self.areas]
        inside = {a.id for a in self.areas}   # Contains is never limited by the zoom (ANN-7)
        count = self.settings["nearby_count"]
        # Nearby searches within the zoom (NAV-13), and lists only visible features.
        near = self.store.nearby(self.world.lat, self.world.lon, zoom, limit=count + len(inside), exclude=inside,
                                 layers=shown, accept=lambda a: self.visible.big_enough(self.layers.get(a.layer), a.record, zoom))
        units = self.settings["units"]
        nearby = [{"id": n.area.id, "label": describer.nearby_label(n, units, self.settings["bearing"], heading),
                   "level": 1} for n in near[:count]]
        groups = [
            {"id": "within", "label": say("panel.within"), "items": within, "empty": say("place.none")},
            {"id": "nearby", "label": say("panel.nearby"), "items": nearby, "empty": say("nearby.none")},
        ]
        self._panel_cache = (key, groups)
        return groups

    def details(self) -> str:
        """Details of the selected item, or of the smallest area here (DAT-9)."""
        area = self.store.feature(self.selected) if self.selected else (self.areas[0] if self.areas else None)
        if area is None:
            return say("details.nothing")
        rec = area.record
        layers = templates()["details"]["layers"]
        lines = [area.name, say("details.type", value=layers.get(area.layer, area.layer))]
        parents = [p for p in (self.store.feature(i) for i in rec.get("parents", [])) if p]
        if parents:
            lines.append(say("details.part_of", value=say("place.list_separator").join(p.name for p in parents)))
        if rec.get("disputed"):
            lines.append(say("details.disputed"))
        lines.append(say("details.area", value=words.area_text(area.area_km2, self.settings["units"])))
        s = self.world
        if self.selected and (not self.areas or self.areas[0].id != self.selected):
            lines.append(say("details.centre", value=words.coordinates_text(s.lat, s.lon, self.settings["coordinates"],
                                                                          self._coordinate_step())))
        lines.append(say("details.source", value=self._source_text(area)))
        return "\n".join(lines)

    def registry(self) -> dict:
        return registry.describe(self.platform, self.settings.keys)

    def settings_schema(self) -> dict:
        """The settings dialog: its tabs and fields, with the current values (P1-T10)."""
        return {"tabs": settings_mod.schema()["tabs"], "values": dict(self.settings.values),
                "keys": self.key_table()}

    def key_table(self) -> list[dict]:
        """Every command with its key now and its default, for the Keys tab (ACC-3)."""
        return [{"name": c.name, "label": c.label, "key": registry.key_of(c, self.settings.keys),
                 "key_text": registry.key_text(registry.key_of(c, self.settings.keys)), "default": c.key}
                for c in registry.for_platform(self.platform) if not c.pointer]

    def earcon_file(self, event: str) -> dict:
        """Which file to play for an earcon (SON-8): the user's own if one is set, else the default."""
        from mapcore.describe import earcon_list

        default = next((e["file"] for e in earcon_list() if e["event"] == event), None)
        custom = self.settings.values.get(f"earcon_{event}", "")
        return {"event": event, "custom": custom or None, "default": default}

    def earcon_failed(self, event: str) -> Response:
        """The shell could not play the user's own file: the default plays, and the user is told (SON-8)."""
        return Response().speak(say("sound.own_file_failed", sound=event), ASSERTIVE)

    def map_label(self) -> str:
        """The map region's accessible name: the place under the centre."""
        return say("map_label", place=self._place_text())

    def words(self) -> dict:
        """The window's own words: region names, title and button labels."""
        return dict(say("ui"))

    def frame_painted(self, paint_ms: float) -> None:
        """The shell painted the last frame: the drawing goes into the trace, in its parts (P2-T14b)."""
        self.paint_ms = paint_ms
        frame = self.last_frame
        if frame:
            self.trace.append({"command": "draw", "ms": frame["project_ms"] + paint_ms, "at": time.time(),
                               "spoken": [], "earcons": [], "choose_ms": frame["choose_ms"],
                               "project_ms": frame["projecting_ms"], "paint_ms": paint_ms,
                               "points": frame["points"]})
            del self.trace[:-2000]

    def startup_took(self, startup_ms: float) -> None:
        self.startup_ms = startup_ms

    def save(self) -> dict:
        """Everything to keep between runs: settings, keys and the world state (PLT-5)."""
        state = self.world.to_dict()
        state["jumps"] = {"back": self.back_places[-PLACE_LIMIT:], "forward": self.forward_places[-PLACE_LIMIT:]}
        return {"settings": self.settings.to_dict(), "state": state}

    # Internals -------------------------------------------------------------

    def _record(self, name: str, response: Response, started: float | None = None) -> Response:
        if self.settings["mute"]:
            response.earcons = []
        spoken = [a["text"] for a in response.announcements if a["channel"] == SPEECH]
        if spoken and name not in ("speech.repeat", "speech.history"):
            self.last_spoken = " ".join(spoken)
            self.history.append(self.last_spoken)
            self.history_places.append(self._place_now() if name in PLACE_COMMANDS else None)
            del self.history[:-HISTORY_LIMIT]
            del self.history_places[:-HISTORY_LIMIT]
        elif name == "speech.repeat" and spoken and self.last_spoken:
            self.history.append(self.last_spoken)
            self.history_places.append(self.history_places[-1] if self.history_places else None)
            del self.history[:-HISTORY_LIMIT]
            del self.history_places[:-HISTORY_LIMIT]
        if started is not None:
            self.trace.append({"command": name, "ms": (self.clock() - started) * 1000, "at": time.time(),
                               "spoken": spoken, "earcons": list(response.earcons)})
            del self.trace[:-2000]
        return response

    def _here(self) -> list:
        """The areas at the location from the layers that are on, smallest first.
        Notes whether there were areas here that every one is in a layer that is off."""
        everything = self.store.at(self.world.lat, self.world.lon)
        active = self.layers.active()
        areas = [a for a in everything if a.layer in active]
        self.all_off_here = bool(everything) and not areas
        return areas

    def _place_text(self) -> str:
        return describer.place_text(self.areas, self.all_off_here)

    def _units(self) -> str:
        return self.settings["units"]

    def _zoom_step(self) -> str:
        return describer.zoom_step_text(self.world, self._units())

    def _moved(self, **extra) -> Response:
        self.selected = None
        return Response(redraw=True, panel_stale=True, details_stale=True, **extra)

    def _arrived(self, r: Response) -> Response:
        """Describe the new place against the last described one (ANN-1)."""
        new = self._here()
        text = describer.announcement(self.areas, new, self.all_off_here)
        self.areas = new
        r.panel_stale = r.details_stale = True
        self.selected = None
        if text:
            r.speak(text, ASSERTIVE)
        else:
            r.earcon("tick")
        return r

    def _move(self, direction: str, held: bool = False, repeat: bool = False, **_a) -> Response:
        """A step. The first press steps and is described at once, and starts the
        hold. repeat is a step the shell's hold timer makes while the key is held,
        at the times hold_due() gives: after the repeat delay, then at the repeat
        rate, whatever the operating system sends (DP129). Each ticks. Nothing is
        said until release(), and the map is drawn at most held_draw_rate times a
        second, so the clicks keep their time (DP140)."""
        now = self.clock()
        if repeat:
            interval = 1.0 / max(1, self.settings["repeat_rate"])
            # Keep to the beat; if the timer was very late, start again from now
            # rather than making two steps at once.
            self._repeat_due = max(self._repeat_due + interval, now + interval / 2)
        elif not held:
            self._repeat_due = now + self.settings["repeat_delay_ms"] / 1000.0
            self.holding = f"move.{direction}"
        result = self.world.step(direction, turn_deg=self.settings["turn_deg"])
        if result.turned:
            return self._turned(held, repeat, now)
        if not result.moved:
            return Response().earcon("blocked")  # nothing spoken (NAV-1)
        if held:
            # The Information panel and Details wait for the release (ANN-3).
            self.selected = None
            self.held_moves += 1
            r = Response(redraw=self._draw_due(now))
            return r.earcon("tick") if repeat else r
        self.held_moves = 0
        self._drawn_at = now
        r = self._moved()
        if result.pole:   # over a pole, the heading turns round, and is said (NAV-3)
            r.speak(say("movement.pole_crossed", pole=say(f"movement.poles.{result.pole}"),
                        heading=describer.facing_text(self.world)), ASSERTIVE)
        return self._arrived(r)

    def _turned(self, held: bool, repeat: bool, now: float) -> Response:
        """A turn on the spot (NAV-3, NAV-12): the heading arrow is drawn again, and the
        new heading said. Held, the turns tick and the heading is said on release."""
        self._panel_cache = None
        if held:
            self.held_turns += 1
            r = Response(redraw=self._draw_due(now))
            return r.earcon("tick") if repeat else r
        self.held_turns = 0
        return Response(redraw=True, panel_stale=True).speak(
            say("movement.facing", heading=describer.facing_text(self.world)), ASSERTIVE)

    def _turn(self, degrees_setting: str | None = None, sign: int = 1, **_a) -> Response:
        """Shift and Ctrl with Left and Right: turn 90 degrees, or by the fine amount
        in free facing. In north-fixed, and the fine turn in cardinal facing, the
        blocked sound plays and nothing is said (NAV-12)."""
        if degrees_setting is not None and self.world.orientation != "free":
            return Response().earcon("blocked")
        degrees = 90.0 if degrees_setting is None else self.settings[degrees_setting]
        result = self.world.turn(sign * degrees)
        if not result.turned:
            return Response().earcon("blocked")
        return self._turned(False, False, self.clock())

    def _orientation_cycle(self, **_a) -> Response:
        """The orientation key: north-fixed, cardinal facing, free facing (NAV-11, NAV-12). It never
        moves you. The new orientation is said with the way you now face."""
        self.world.next_orientation()
        return self._orientation_said(Response(redraw=True, panel_stale=True))

    def _orientation_said(self, r: Response) -> Response:
        self._panel_cache = None
        return r.speak(say(f"movement.orientation_changed.{self.world.orientation}",
                           heading=describer.facing_text(self.world)), ASSERTIVE)

    def _bearing_type(self, **_a) -> Response:
        return Response(dialog={"kind": "input", "title": say("typing.bearing_title"),
                                "label": say("typing.bearing_label"), "help": say("typing.bearing_help"),
                                "submit": "bearing.set", "ok": say("ui.ok"), "cancel": say("ui.cancel")})

    def _bearing_set(self, text: str = "", **_a) -> Response:
        """A typed bearing: face it. In north-fixed or cardinal facing this switches to free
        facing, and says so (NAV-12). A bearing that can't be read is refused with the words
        that list what is accepted, and the box stays open."""
        try:
            bearing = parse.parse_bearing(text)
        except ValueError:
            return Response(error=say("typing.bearing_error"))
        was_free = self.world.orientation == "free"
        self.world.face(bearing)
        r = Response(redraw=True, panel_stale=True)
        if not was_free:
            return self._orientation_said(r)
        self._panel_cache = None
        return r.speak(say("movement.facing", heading=describer.facing_text(self.world)), ASSERTIVE)

    def _goto_coordinates(self, **_a) -> Response:
        return Response(dialog={"kind": "input", "title": say("typing.goto_title"),
                                "label": say("typing.goto_label"), "help": say("typing.goto_help"),
                                "submit": "goto.set", "ok": say("ui.ok"), "cancel": say("ui.cancel")})

    def _goto_set(self, text: str = "", **_a) -> Response:
        """Typed coordinates: jump there, keeping the zoom and step (NAV-8)."""
        try:
            lat, lon = parse.parse_coordinates(text)
        except ValueError:
            return Response(error=say("typing.goto_error"))
        return self._land(self._jump(lat, lon))

    # Jumping and the position history (NAV-8, NAV-10, DP142) -----------------

    @staticmethod
    def _valid_place(p) -> bool:
        return isinstance(p, dict) and all(isinstance(p.get(k), (int, float)) for k in ("lat", "lon", "zoom_m", "step_m"))

    def _place_now(self) -> dict:
        w = self.world
        return {"lat": w.lat, "lon": w.lon, "zoom_m": w.zoom_m, "step_m": w.step_m}

    def _remember_jump(self) -> None:
        """Before a jump the place, zoom and step are kept, and any way forward is forgotten."""
        self.back_places.append(self._place_now())
        del self.back_places[:-PLACE_LIMIT]
        self.forward_places.clear()

    def _jump(self, lat: float, lon: float, zoom_m: float | None = None, step_m: float | None = None) -> Response:
        """Move without a step. The zoom stays unless a place with its own is given."""
        self._remember_jump()
        self._go_to(lat, lon, zoom_m, step_m)
        return Response(redraw=True, panel_stale=True, details_stale=True, settings_changed=True)

    def _go_to(self, lat: float, lon: float, zoom_m: float | None, step_m: float | None) -> None:
        w = self.world
        w.lat, w.lon = max(-90.0, min(90.0, round(float(lat), 6))), round(geodesy.wrap_lon(float(lon)), 6)
        if zoom_m is not None:
            w.zoom_index = nearest_index(w.zoom_list, zoom_m)
        if step_m is not None:
            w.step_index = nearest_index(w.step_list, step_m)
        self._settings_link_sync()
        self.selected = None

    def _land(self, r: Response) -> Response:
        """After a jump, say the whole place, as Where am I does."""
        self.areas = self._here()
        r.panel_stale = r.details_stale = True
        return r.speak(self._place_text(), ASSERTIVE)

    def _go_through(self, source: list, other: list) -> Response:
        """Back or forward through the places: the zoom and step come back with the place (DP77).
        Nothing to go to plays the blocked sound."""
        if not source:
            return Response().earcon("blocked")
        other.append(self._place_now())
        del other[:-PLACE_LIMIT]
        place = source.pop()
        self._go_to(place["lat"], place["lon"], place["zoom_m"], place["step_m"])
        return self._land(Response(redraw=True, panel_stale=True, details_stale=True, settings_changed=True))

    def _changed_sizes(self, zoom_before: float, step_before: float) -> str:
        """Only what changed: the zoom, the step, or both when they are linked
        (PO feedback on checklist 7, second pass)."""
        units = self._units()
        zoom_changed, step_changed = self.world.zoom_m != zoom_before, self.world.step_m != step_before
        if zoom_changed and not step_changed:
            return say("movement.zoom_only", zoom=words.distance_text(self.world.zoom_m, units))
        if step_changed and not zoom_changed:
            return say("movement.step_only", step=words.distance_text(self.world.step_m, units))
        return self._zoom_step()

    def _zoom(self, direction: int) -> Response:
        before = (self.world.zoom_m, self.world.step_m)
        if not self.world.change_zoom(direction):
            key = "movement.zoom_end_out" if direction > 0 else "movement.zoom_end_in"
            return Response().speak(say(key, zoom_step=say(
                "movement.zoom_only", zoom=words.distance_text(self.world.zoom_m, self._units()))), ASSERTIVE)
        self._settings_link_sync()
        return Response(redraw=True, panel_stale=True).speak(self._changed_sizes(*before), ASSERTIVE)

    def _step_size(self, direction: int) -> Response:
        before = (self.world.zoom_m, self.world.step_m)
        if not self.world.change_step(direction):
            key = "movement.step_end_larger" if direction > 0 else "movement.step_end_smaller"
            return Response().speak(say(key, zoom_step=say(
                "movement.step_only", step=words.distance_text(self.world.step_m, self._units()))), ASSERTIVE)
        return Response(redraw=True, panel_stale=True).speak(self._changed_sizes(*before), ASSERTIVE)

    def _settings_link_sync(self) -> None:
        self.settings.set("link", self.world.link, quiet=True)

    def _link(self, on: bool | None = None, **_a) -> Response:
        self.world.set_link(not self.world.link if on is None else bool(on))
        self._settings_link_sync()
        key = "movement.link_on" if self.world.link else "movement.link_off"
        return Response(redraw=True, settings_changed=True).speak(say(key, zoom_step=self._zoom_step()), ASSERTIVE)

    def _where_am_i(self, **_a) -> Response:
        self.areas = self._here()
        return Response(panel_stale=True).speak(self._place_text(), ASSERTIVE)

    def _coordinates(self, **_a) -> Response:
        return Response().speak(words.coordinates_text(self.world.lat, self.world.lon, self.settings["coordinates"],
                                                       self._coordinate_step()), ASSERTIVE)

    def _coordinate_step(self) -> float | None:
        """The step the coordinates are rounded to, or None for every place (the setting)."""
        return self.world.step_m if self.settings["coordinate_places"] == "step" else None

    def _heading(self, **_a) -> Response:
        return Response().speak(describer.heading_report(self.world, self._units()), ASSERTIVE)

    def _visible(self, **_a) -> Response:
        """The size of the visible map, across and up and down the window (DP99).
        Measured along the ground through the centre; never more than the hemisphere."""
        width, height = self.map_size
        from mapcore.render import globe

        radius = globe._radius(self._view_scale(width, height), width, height)

        def across(pixels: float) -> float:
            return 2 * math.asin(min(1.0, pixels / 2 / radius)) * geodesy.R_MEAN_M

        units = self._units()
        return Response().speak(say("visible.area", width=words.distance_text(across(width), units),
                                    height=words.distance_text(across(height), units)), ASSERTIVE)

    def _focus_panel(self, **_a) -> Response:
        item = self.panel_item
        known = {i["id"] for g in self.panel() for i in g["items"]}
        if item not in known:
            item = self.areas[0].id if self.areas else None
        return Response(focus={"region": "panel", "group": "within" if not self.panel_item else None,
                               "item": item}, panel_stale=True)

    def _select(self, item: str | None = None, **_a) -> Response:
        self.panel_item = item or self.panel_item
        if item == self.selected:
            return Response()
        self.selected = item
        return Response(redraw=True, details_stale=True)

    def _repeat(self, **_a) -> Response:
        return Response().speak(self.last_spoken or say("history.nothing_to_repeat"), ASSERTIVE)

    def _history(self, **_a) -> Response:
        lines = list(reversed(self.history)) or [say("history.empty")]
        return Response(dialog={"kind": "history", "title": say("history.title"), "lines": lines,
                                "text": "\n".join(lines), "help": say("history.help"), "go": "history.go"})

    def _history_go(self, index: int = -1, **_a) -> Response:
        """Enter on an announcement history entry (listed newest first): go back to the place it
        was said at, as a jump, so Alt+comma comes back (ANN-4, NAV-8, DP141). An entry with no
        place says so, and the list stays open."""
        places = self.history_places[::-1]
        place = places[index] if 0 <= index < len(places) else None
        if place is None:
            return Response(error=say("history.no_place"))
        return self._land(self._jump(place["lat"], place["lon"], place["zoom_m"], place["step_m"]))

    def _braille_test(self, **_a) -> Response:
        fallback = say("braille_web") if self.platform == "web" else say("braille_fallback")
        r = Response()
        r.announcements.append({"text": say("braille_test", place=self._place_text()),
                                "channel": BRAILLE, "priority": POLITE, "fallback": fallback})
        return r

    def _mute(self, on: bool | None = None, **_a) -> Response:
        self.settings.set("mute", (not self.settings["mute"]) if on is None else bool(on))
        key = "sound.muted" if self.settings["mute"] else "sound.unmuted"
        return Response(settings_changed=True).speak(say(key), ASSERTIVE)

    def _settings_open(self, **_a) -> Response:
        return Response(dialog={"kind": "settings", "title": say("settings.title")})

    def _settings_set(self, field: str, value, **_a) -> Response:
        try:
            self.settings.set(field, value)
        except (ValueError, TypeError):
            return Response().speak(say("settings.bad_value"), ASSERTIVE)
        if field == "link":
            self.world.set_link(bool(value))
        if field == "units":
            self.world.use_units(value)   # imperial has its own round sizes, so the map may redraw (DP136)
        self._panel_cache = None
        return Response(settings_changed=True, panel_stale=True, details_stale=True, redraw=True)

    def layer_list(self) -> dict:
        """The layers list (SCP-6, SCP-7), as plain data for the shells' dialogs: each
        group with its layers, in display order. A group with no name in the pack
        is given the templates' word for other layers."""
        return {"title": say("layers.title"), "groups": [
            {"name": group or say("layers.other_group"), "layers": [layer.to_dict() for layer in members]}
            for group, members in self.layers.groups()]}

    def _layers_open(self, **_a) -> Response:
        """The layers dialog (SCP-6, SCP-7): a check box for each layer, in its group, and a Settings
        button for the selected layer. All its words and choices come from here. The shell sends one
        layers.set for each change when OK is pressed, and nothing when Cancel is."""
        from mapcore.describe import earcon_list

        units = self.settings["units"]
        zooms = [{"value": z, "label": words.distance_text(z, units)} for z in self.world.zoom_list]
        every = say("layers.every_zoom")
        data = self.layer_list()
        lines = []
        for group in data["groups"]:
            lines.append(group["name"])
            lines.extend(say("layers.item_on" if l["on"] else "layers.item_off", layer=l["name"])
                         for l in group["layers"])
        return Response(dialog={
            "kind": "layers", "title": data["title"], "groups": data["groups"], "text": "\n".join(lines),
            "zooms": zooms, "every_zoom": every,
            "earcons": [{"event": e["event"], "label": e["label"]} for e in earcon_list()],
            "words": {k: say(f"layers.{k}") for k in ("settings_button", "settings_title", "closest", "farthest",
                                                      "crossing", "no_sound")}
            | {"ok": say("ui.ok"), "cancel": say("ui.cancel")},
            "set": "layers.set", "check": "layers.check"})

    def _layers_check(self, low=0.0, high=None, **_a) -> Response:
        """Whether a closest and farthest zoom can go together; the words say what is wrong."""
        try:
            low = float(low or 0.0)
            high = None if high in (None, "") else float(high)
        except (TypeError, ValueError):
            return Response(error=say("settings.bad_value"))
        if high is not None and low > high:
            return Response(error=say("layers.range_error"))
        return Response()

    def _layers_set(self, layer: str, field: str = "", value=None, values: dict | None = None, **_a) -> Response:
        """Change one thing about a layer: switch it on or off, its zoom range or its
        sounds (SCP-6, SCP-7). The change is saved with the settings, by layer id.
        A layer switched off is gone from the map, the Information panel and every
        announcement at once. Nothing is said: the list the change was made in says it."""
        try:
            self.layers.change_many(layer, values if values is not None else {field: value})
        except (ValueError, TypeError):
            return Response().speak(say("settings.bad_value"), ASSERTIVE)
        self._panel_cache = None
        self.areas = self._here()
        if self.selected and self.store.feature(self.selected) is not None                 and not self.layers.is_on(self.store.feature(self.selected).layer):
            self.selected = None
        return Response(settings_changed=True, redraw=True, panel_stale=True, details_stale=True)

    def _remap(self, command: str, key: str, **_a) -> Response:
        """Give a command a different key (ACC-3). A key that is in use is refused,
        and the command that has it is named."""
        if key and not registry.valid_key(key):
            return Response().speak(say("keys.invalid", key=registry.key_text(key)), ASSERTIVE)
        other = registry.clash(self.platform, command, key, self.settings.keys) if key else None
        if other is not None:
            return Response().speak(say("keys.taken", key=registry.key_text(key), other=other.label), ASSERTIVE)
        default = registry.by_name(command).key
        if key == default:
            self.settings.keys.pop(command, None)
        else:
            self.settings.keys[command] = key
        label = registry.by_name(command).label
        return Response(settings_changed=True).speak(
            say("keys.changed", label=label, key=registry.key_text(key)) if key else say("keys.cleared", label=label), ASSERTIVE)

    def _help_keys(self, region: str = "map", **_a) -> Response:
        """F1: the commands for the focused region, each with its key (ACC-3)."""
        region = region if region in REGIONS else "map"
        region_name = say(f"ui.{'menu_bar' if region == 'menu' else region}")
        lines = [line.format(region=region_name) for line in templates()["dialogs"]["keys_intro_region"]]
        for c in registry.for_platform(self.platform):
            if c.pointer or (c.region == "map" and region != "map"):
                continue
            key = registry.key_of(c, self.settings.keys)
            lines.append(say("dialogs.keys_line", label=c.label, key=registry.key_text(key)) if key
                         else say("dialogs.keys_menu_only", label=c.label, menu=c.menu))
        return Response(dialog={"kind": "text", "title": say("dialogs.keys_title"), "text": "\n".join(lines)})

    def _describer(self, **_a) -> Response:
        self.describing = not self.describing
        return Response().speak(say("describer.started" if self.describing else "describer.stopped"), ASSERTIVE)

    def _about(self, **_a) -> Response:
        return Response(dialog={"kind": "text", "title": say("dialogs.about_title"),
                                "text": say("dialogs.about_text", version=mapcore.version())})

    def _about_data(self, **_a) -> Response:
        """The attribution and licence of every pack in use (DAT-9)."""
        parts = []
        for pack in self.store.packs:
            parts.append(say("dialogs.data_pack", name=pack.manifest.get("title") or pack.manifest["name"],
                             version=pack.manifest.get("version", ""), built=pack.manifest.get("built", "")))
            parts.append(pack.attribution)
            parts.append(pack.licence)
        return Response(dialog={"kind": "text", "title": say("dialogs.data_title"),
                                "text": "\n\n".join(parts) or say("dialogs.data_none")})

    def _earcons_help(self, **_a) -> Response:
        from mapcore.describe import earcon_list

        items = [{"event": e["event"], "label": say("dialogs.earcons_line", name=e["label"], file=e["file"],
                                                     meaning=e["meaning"])} for e in earcon_list()]
        return Response(dialog={"kind": "sounds", "title": say("dialogs.earcons_title"), "items": items,
                                "play": say("ui.play"), "text": "\n".join(i["label"] for i in items)})

    def _preview(self, event: str = "", **_a) -> Response:
        """Play one sound from Help, The sounds (DP134). Mute still applies."""
        return Response().earcon(event)

    def _source_text(self, area) -> str:
        source = area.record.get("source", "")
        for pack in self.store.packs:
            for s in pack.manifest.get("sources", []):
                if source and source.lower() in s["name"].lower().replace("openstreetmap", "osm"):
                    return f"{s['name']}, {s['licence']}"
        return source

    def _timing(self, **_a) -> Response:
        r = Response()
        if self.last_frame:
            paint = say("timing_unknown") if self.paint_ms is None else f"{round(self.paint_ms):d}"
            r.speak(say("timing", project=f"{round(self.last_frame['project_ms']):d}", paint=paint,
                        points=f"{self.last_frame['points']:,}"))
        if self.startup_ms is not None:
            r.speak(say("timing_startup", seconds=f"{self.startup_ms / 1000:.1f}"))
        return r

    def _diagnostics(self, **_a) -> Response:
        from mapcore import diagnostics

        text = diagnostics.report(self)
        return Response(dialog={"kind": "text", "title": say("diagnostics.title"), "text": text, "copy": text})

    # The mouse (NAV-9, NAV-13, VIS-4) ----------------------------------------

    def _view_scale(self, width: float, height: float):
        from mapcore.render import scene as scene_mod

        return scene_mod.view_for(self.world, width, height)

    def _click(self, x: float, y: float, width: float, height: float, **_a) -> Response:
        from mapcore.render import globe

        point = globe.from_screen(self._view_scale(width, height), width, height, x, y)
        if point is None:
            return Response().speak(say("off_globe"), ASSERTIVE)
        self._remember_jump()
        self.world.lat = max(-90.0, min(90.0, round(point[0], 6)))
        self.world.lon = round(geodesy.wrap_lon(point[1]), 6)
        return self._arrived(self._moved(settings_changed=False))

    def _drag(self, dx: float, dy: float, width: float, height: float, **_a) -> Response:
        """Dragging turns the globe and moves the location with it (VIS-4). Nothing is
        said until the drag ends and the shell calls release()."""
        from mapcore.render import globe

        point = globe.from_screen(self._view_scale(width, height), width, height, width / 2 - dx, height / 2 - dy)
        if point is None:
            return Response()
        self.world.lat = max(-90.0, min(90.0, round(point[0], 6)))
        self.world.lon = round(geodesy.wrap_lon(point[1]), 6)
        self.held_moves += 1
        return self._moved()

    def _hover(self, x: float, y: float, width: float, height: float, **_a) -> Response:
        """The place under the mouse, spoken only if the setting is on. The location does not move."""
        from mapcore.render import globe

        if not self.settings["hover_announce"]:
            return Response()
        point = globe.from_screen(self._view_scale(width, height), width, height, x, y)
        if point is None:
            return Response()
        everything = self.store.at(point[0], point[1])
        active = self.layers.active()
        areas = [a for a in everything if a.layer in active]
        return Response().speak(describer.place_text(areas[:1], bool(everything) and not areas), POLITE)

    def _zoom_to(self, direction: int = 0, **_a) -> Response:
        """The wheel or a pinch: to the nearest zoom in the list, one step each time (NAV-13)."""
        return self._zoom(+1 if direction > 0 else -1)
