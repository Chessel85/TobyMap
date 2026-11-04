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

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

import mapcore
from mapcore import settings as settings_mod
from mapcore.commands import registry
from mapcore.describe import describer, say, templates, words
from mapcore.geo import geodesy
from mapcore.world import WorldState

DEFAULTS_FILE = Path(__file__).resolve().parent / "defaults.yaml"
SPEECH, BRAILLE = "speech", "braille"
ASSERTIVE, POLITE = "assertive", "polite"
HISTORY_LIMIT = 200  # at least the last 50 (ANN-4)
REGIONS = ("map", "panel", "details", "menu")


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
                 saved_state: dict | None = None, clock=time.perf_counter):
        from mapcore.store import Store

        self.platform = platform
        self.defaults = yaml.safe_load(DEFAULTS_FILE.read_text(encoding="utf-8"))
        self.store = store or Store(list(packs or []))
        self.settings = settings_mod.Settings.from_dict(settings)
        self.world = WorldState.from_defaults(self.defaults)
        if saved_state:
            self.world.restore(saved_state)
        elif self.settings["link"]:
            self.world.set_link(True)
        self.world.link = bool(self.settings["link"]) if not saved_state else self.world.link
        self.settings.set("link", self.world.link)
        self.clock = clock
        self.areas: list = []          # the areas at the last described place, smallest first
        self.last_spoken: str | None = None
        self.history: list[str] = []
        self.describing = False        # the key describer (Shift+F1)
        self.selected: str | None = None   # the Information panel item chosen, an area id
        self.panel_item: str | None = None  # the item last focused there, for F3 (DP106)
        self.held_moves = 0
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
            "settings.open": self._settings_open,
            "settings.set": self._settings_set,
            "keys.remap": self._remap,
            "help.keys": self._help_keys,
            "help.describer": self._describer,
            "help.about": self._about,
            "help.about_data": self._about_data,
            "help.earcons": self._earcons_help,
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
        r.speak(say("start", place=describer.place_text(self.areas)), POLITE)
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
        return merged

    def press(self, key: str, region: str = "map") -> Response | None:
        """A key pressed in a region ("map", "panel", "details" or "menu").
        Returns None when the key is not one of ours, so the shell lets it through.
        In the key describer nothing is carried out: the key is only described."""
        command = registry.command_for_key(self.platform, key, region, self.settings.keys)
        if self.describing:
            if command is not None and command.name == "help.describer":
                return self.run("help.describer")
            text = (say("describer.key", key=key, label=command.label) if command is not None
                    else say("describer.unassigned", key=key))
            return self._record("describe", Response().speak(text, ASSERTIVE))
        if command is None:
            return None
        if command.name == "help.keys":
            return self.run("help.keys", region=region)
        return self.run(command.name)

    def release(self) -> Response:
        """The held movement key was let go: describe the place it ended at,
        and only that (ANN-3)."""
        if not self.held_moves:
            return Response()
        self.held_moves = 0
        return self._record("release", self._arrived(Response(redraw=True)))

    def scene(self, width: int, height: int) -> dict:
        from mapcore.render import scene as scene_mod

        self.map_size = (width, height)
        if self._scene is None:
            self._scene = scene_mod.SceneBuilder(self.store)
        current = self.areas[0].id if self.areas else None
        frame = self._scene.build(self.world, width, height, current=current, highlight=self.selected,
                                  centre_cross=self.settings["centre_cross"])
        self.last_frame = {"project_ms": frame["project_ms"], "points": frame["points"]}
        return frame

    def panel(self) -> list[dict]:
        """The Information panel groups (UX section 6), as plain data."""
        key = (self.world.lat, self.world.lon, self.settings["units"], self.settings["bearing"],
               self.settings["nearby_count"], self.settings["nearby_radius_km"])
        if self._panel_cache and self._panel_cache[0] == key:
            return self._panel_cache[1]
        within = [{"id": a.id, "label": a.name, "level": 1} for a in self.areas]
        inside = {a.id for a in self.areas}
        count = self.settings["nearby_count"]
        near = self.store.nearby(self.world.lat, self.world.lon, self.settings["nearby_radius_km"] * 1000.0,
                                 limit=count + len(inside), exclude=inside)
        units = self.settings["units"]
        nearby = [{"id": n.area.id, "label": describer.nearby_label(n, units, self.settings["bearing"]),
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
            lines.append(say("details.centre", value=words.coordinates_text(s.lat, s.lon, self.settings["coordinates"])))
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
        return [{"name": c.name, "label": c.label, "key": registry.key_of(c, self.settings.keys), "default": c.key}
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
        return say("map_label", place=describer.place_text(self.areas))

    def words(self) -> dict:
        """The window's own words: region names, title and button labels."""
        return dict(say("ui"))

    def frame_painted(self, paint_ms: float) -> None:
        self.paint_ms = paint_ms

    def startup_took(self, startup_ms: float) -> None:
        self.startup_ms = startup_ms

    def save(self) -> dict:
        """Everything to keep between runs: settings, keys and the world state (PLT-5)."""
        return {"settings": self.settings.to_dict(), "state": self.world.to_dict()}

    # Internals -------------------------------------------------------------

    def _record(self, name: str, response: Response, started: float | None = None) -> Response:
        if self.settings["mute"]:
            response.earcons = []
        spoken = [a["text"] for a in response.announcements if a["channel"] == SPEECH]
        if spoken and name not in ("speech.repeat", "speech.history"):
            self.last_spoken = " ".join(spoken)
            self.history.append(self.last_spoken)
            del self.history[:-HISTORY_LIMIT]
        elif name == "speech.repeat" and spoken and self.last_spoken:
            self.history.append(self.last_spoken)
        if started is not None:
            self.trace.append({"command": name, "ms": (self.clock() - started) * 1000, "at": time.time(),
                               "spoken": spoken, "earcons": list(response.earcons)})
            del self.trace[:-2000]
        return response

    def _here(self) -> list:
        return self.store.at(self.world.lat, self.world.lon)

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
        text = describer.announcement(self.areas, new)
        self.areas = new
        r.panel_stale = r.details_stale = True
        self.selected = None
        if text:
            r.speak(text, ASSERTIVE)
        else:
            r.earcon("tick")
        return r

    def _move(self, direction: str, held: bool = False, **_a) -> Response:
        result = self.world.step(direction)
        if not result.moved:
            return Response().earcon("blocked")  # nothing spoken (NAV-1)
        r = self._moved()
        if held:
            self.held_moves += 1
            return r
        self.held_moves = 0
        return self._arrived(r)

    def _zoom(self, direction: int) -> Response:
        if not self.world.change_zoom(direction):
            key = "movement.zoom_end_out" if direction > 0 else "movement.zoom_end_in"
            return Response().speak(say(key, zoom_step=self._zoom_step()), ASSERTIVE)
        self._settings_link_sync()
        return Response(redraw=True, panel_stale=True).speak(self._zoom_step(), ASSERTIVE)

    def _step_size(self, direction: int) -> Response:
        if not self.world.change_step(direction):
            key = "movement.step_end_larger" if direction > 0 else "movement.step_end_smaller"
            return Response().speak(say(key, zoom_step=self._zoom_step()), ASSERTIVE)
        return Response(redraw=True, panel_stale=True).speak(self._zoom_step(), ASSERTIVE)

    def _settings_link_sync(self) -> None:
        self.settings.set("link", self.world.link, quiet=True)

    def _link(self, on: bool | None = None, **_a) -> Response:
        self.world.set_link(not self.world.link if on is None else bool(on))
        self._settings_link_sync()
        key = "movement.link_on" if self.world.link else "movement.link_off"
        return Response(redraw=True, settings_changed=True).speak(say(key, zoom_step=self._zoom_step()), ASSERTIVE)

    def _where_am_i(self, **_a) -> Response:
        self.areas = self._here()
        return Response(panel_stale=True).speak(describer.place_text(self.areas), ASSERTIVE)

    def _coordinates(self, **_a) -> Response:
        return Response().speak(words.coordinates_text(self.world.lat, self.world.lon,
                                                       self.settings["coordinates"]), ASSERTIVE)

    def _heading(self, **_a) -> Response:
        return Response().speak(describer.heading_report(self.world, self._units()), ASSERTIVE)

    def _visible(self, **_a) -> Response:
        width_m = self.world.zoom_m
        return Response().speak(say("visible.area", width=words.distance_text(width_m, self._units())), ASSERTIVE)

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
                                "text": "\n".join(lines)})

    def _braille_test(self, **_a) -> Response:
        fallback = say("braille_web") if self.platform == "web" else say("braille_fallback")
        r = Response()
        r.announcements.append({"text": say("braille_test", place=describer.place_text(self.areas)),
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
        self._panel_cache = None
        return Response(settings_changed=True, panel_stale=True, details_stale=True, redraw=True)

    def _remap(self, command: str, key: str, **_a) -> Response:
        """Give a command a different key (ACC-3). A key that is in use is refused,
        and the command that has it is named."""
        if key and not registry.valid_key(key):
            return Response().speak(say("keys.invalid", key=key), ASSERTIVE)
        other = registry.clash(self.platform, command, key, self.settings.keys) if key else None
        if other is not None:
            return Response().speak(say("keys.taken", key=key, other=other.label), ASSERTIVE)
        default = registry.by_name(command).key
        if key == default:
            self.settings.keys.pop(command, None)
        else:
            self.settings.keys[command] = key
        label = registry.by_name(command).label
        return Response(settings_changed=True).speak(
            say("keys.changed", label=label, key=key) if key else say("keys.cleared", label=label), ASSERTIVE)

    def _help_keys(self, region: str = "map", **_a) -> Response:
        """F1: the commands for the focused region, each with its key (ACC-3)."""
        region = region if region in REGIONS else "map"
        lines = [say("dialogs.keys_intro_region", region=say(f"ui.{'menu_bar' if region == 'menu' else region}"))]
        for c in registry.for_platform(self.platform):
            if c.pointer or (c.region == "map" and region != "map"):
                continue
            key = registry.key_of(c, self.settings.keys)
            lines.append(say("dialogs.keys_line", label=c.label, key=key) if key
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

        lines = [say("dialogs.earcons_line", name=e["label"], file=e["file"], meaning=e["meaning"])
                 for e in earcon_list()]
        return Response(dialog={"kind": "text", "title": say("dialogs.earcons_title"), "text": "\n".join(lines)})

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
        areas = self.store.at(point[0], point[1])
        return Response().speak(describer.place_text(areas[:1]), POLITE)

    def _zoom_to(self, direction: int = 0, **_a) -> Response:
        """The wheel or a pinch: to the nearest zoom in the list, one step each time (NAV-13)."""
        return self._zoom(+1 if direction > 0 else -1)
