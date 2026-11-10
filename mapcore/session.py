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
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import yaml

import mapcore
from mapcore import settings as settings_mod
from mapcore.commands import registry
from mapcore.describe import describer, say, templates, words
from mapcore.describe.describer import HERE_M
from mapcore.geo import formats, geodesy, parse
from mapcore.layers import LayerCatalogue
from mapcore.layers.visible import VisibleRule
from mapcore.world import WorldState
from mapcore.sound.stretch import split_rate
from mapcore.world.state import nearest_index

DEFAULTS_FILE = Path(__file__).resolve().parent / "defaults.yaml"
SPEECH, BRAILLE = "speech", "braille"
ASSERTIVE, POLITE = "assertive", "polite"
PLACE_LIMIT = 1000   # places kept in the location history (NAV-10, DP142, DP158)
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
    # The crossing sounds among the earcons, kept so that joined moves lose none (SCP-7, ANN-3).
    # Not sent to the shells: the earcons already hold them.
    crossings: list[str] = field(default_factory=list)
    # Work for the shell to start in the background after this response is handled:
    # the Crossed and passed search (P2-T5). The shell calls crossed_job() and so on.
    background: bool = False
    # Sounds placed in space by the sound scene (P2-T6, AD-10): each is mapcore.sound.scene.Placed
    # as a dict, with "file", the earcon_file() to play. The shells' sound players carry them out.
    sounds: list[dict] = field(default_factory=list)
    # A label in the spatial voice (P2-T7, SON-3, AD-10): {"text", "placed", "rate", "stretch", "after"}.
    # placed is the sound scene's Placed as a dict, for the voice; rate is the speed Piper is
    # asked for, 1 normal; stretch is how many times faster mapcore.sound.stretch.speed_up then
    # makes it, at the same pitch, 1 for none; pitch is the voice's own, lower behind you, made
    # without slowing it (P2-T16g). Both go to stretch.shape_voice; placed["pitch"] is then 1;
    # after says the label waits for the sounds of this response to finish. A newer label
    # stops an older one that is still playing (ANN-3).
    voice: dict | None = None
    # True when the shell stops the spatial voice before anything else in this response, so it never
    # talks over the screen reader (P2-T17n, SON-3). Every command's response has it, except one that
    # starts a label, which stops the older label itself (ANN-3).
    stop_voice: bool = False
    # A spatial label, kept for Repeat even when muted (ANN-4). Not sent to the shells.
    label: str | None = None
    # The orientation beacon now (P2-T9, SON-10): {"on", "placed", "interval_s"}, as beacon() gives it.
    # Every command's response has it; None, as in a sound problem's response, means no change. The
    # shell repeats placed every interval_s on its own timer, from where it is now; placed is None
    # when the beacon is off, muted or silent near the North Pole.
    beacon: dict | None = None

    def speak(self, text: str, priority: str = POLITE) -> "Response":
        self.announcements.append({"text": text, "channel": SPEECH, "priority": priority})
        return self

    def earcon(self, name: str) -> "Response":
        self.earcons.append(name)
        return self

    def to_dict(self) -> dict:
        out = asdict(self)
        out.pop("crossings")
        out.pop("label")
        return out


def box_centre(bbox) -> tuple[float, float]:
    """The centre of an area's bounding box (west, south, east, north), as (lat, lon). A bounding box across the
    180 degree line has west greater than east (AD-17)."""
    west, south, east, north = bbox
    if west > east:
        east += 360.0
    return (south + north) / 2.0, geodesy.wrap_lon((west + east) / 2.0)


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
        # Why nothing is said here although there are areas: "layers_off" or "out_of_zoom" (LOC-6, DP160).
        self.why_none_here: str | None = None
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
        # The location history (NAV-10, DP142, DP158): the places before each step or jump, newest
        # last, and the places gone back from, newest last. Where you are now sits between them.
        self.back_places: list[dict] = []
        self.forward_places: list[dict] = []
        self._history_rows: list[int] = []   # the open list's rows, as places back (-) or forward (+)
        self._areas_at: dict[tuple[float, float], list] = {}   # every area at a place in the history
        if saved_state and not self.settings["places_clear_on_start"]:
            jumps = saved_state.get("jumps") or {}
            self.back_places = [p for p in jumps.get("back", []) if self._valid_place(p)][-PLACE_LIMIT:]
            self.forward_places = [p for p in jumps.get("forward", []) if self._valid_place(p)][-PLACE_LIMIT:]
        self.describing = False        # the key describer (Shift+F1)
        self.selected: str | None = None   # the Information panel item chosen, an area id
        self.panel_item: str | None = None  # the item last focused there, for F3 (DP106)
        self.panel_group: str | None = None  # and its group, as an area can be in two groups
        self.panel_on_item = True            # False while a group heading has the focus (P2-T17f)
        self.panel_at_group: str | None = None   # the group the focus is in, on an item or its heading
        self._pressed_in = "map"                 # the region of the key being carried out
        self._answer_to = "map"                  # where Go to's or the bearing's box was opened (P2-T17k)
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
        # Crossed and passed (P2-T5, ANN-2): the most recent move's list, the search waiting to
        # be done, and a number that changes with every move, so an old search is thrown away.
        self.crossed: list = []
        self._crossed_gen = 0
        self._crossed_job: dict | None = None
        self._held_path: list = []        # the path of a held key's steps, joined, until the release
        self._panel_cache: tuple | None = None
        # (group, item id): (feature, lat, lon) of Nearby and Crossed and passed. By group too, as an
        # area can be in both, at its nearest point in one and where it was crossed in the other.
        self._spots: dict[tuple[str, str], tuple] = {}
        self._scene = None
        self._beacon_near: bool | None = None   # the beacon is on and silent near the North Pole (P2-T9)
        self.isolated: str | None = None        # the one feature shown, with Isolate (VIS-2)
        self._theme_cache: tuple | None = None   # (the settings it was made from, (theme, refused colours))
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
            # Shift and a number: go to that group (INF-10, DP109).
            **{f"panel.{g}": (lambda g=g, **a: Response(focus={"region": "panel", "group": g}, panel_stale=True))
               for g in registry.panel_groups()},
            "panel.hear": self._hear,
            "panel.go": self._panel_go,
            "speech.repeat": self._repeat,
            "history.list": self._history,
            "speech.braille_test": self._braille_test,
            "sound.mute": self._mute,
            "verbosity.next": lambda **a: self._verbosity_step(+1),
            "verbosity.previous": lambda **a: self._verbosity_step(-1),
            "theme.next": lambda **a: self._theme_step(+1),
            "theme.previous": lambda **a: self._theme_step(-1),
            "isolate.toggle": self._isolate_toggle,
            "beacon.toggle": self._beacon_toggle,
            "orientation.cycle": lambda **a: self._orientation_step(+1),
            "orientation.previous": lambda **a: self._orientation_step(-1),
            "turn.left": lambda **a: self._turn(sign=-1),
            "turn.right": lambda **a: self._turn(sign=1),
            "turn.fine_left": lambda **a: self._turn("fine_turn_deg", -1),
            "turn.fine_right": lambda **a: self._turn("fine_turn_deg", 1),
            "bearing.type": self._bearing_type,
            "bearing.set": self._bearing_set,
            "goto.coordinates": self._goto_coordinates,
            "goto.set": self._goto_set,
            "history.back": lambda **a: self._go_through(-1),
            "history.forward": lambda **a: self._go_through(+1),
            "history.go": self._history_go,
            "settings.open": self._settings_open,
            "settings.set": self._settings_set,
            "settings.reset": self._reset_ask,
            "settings.reset_confirm": self._reset_all,
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

    def run(self, name: str, pressed_in: str | None = None, **args) -> Response:
        """Carry out a command. pressed_in is the region its key was pressed in, when a shell
        knows it: Go to and Type a bearing send the focus back there (P2-T17k). A menu item or
        a list gives none, which is the map."""
        started = self.clock()
        handler = self._handlers[name]  # KeyError for an unknown command
        self._pressed_in = pressed_in or "map"
        try:
            r = self._record(name, handler(**args), started)
        finally:
            self._pressed_in = "map"
        return r

    def run_many(self, commands: list[tuple[str, dict]]) -> Response:
        """Carry out several commands that arrived faster than they could be
        answered. Every one is carried out, but only the last one is described,
        so speech never falls behind (ANN-3). The crossing sounds of every one are
        kept, in order, so a line crossed on the way is still heard (SCP-7)."""
        merged = Response()
        others: list[str] = []
        last = len(commands) - 1
        for i, (name, args) in enumerate(commands):
            args = dict(args)
            if i < last and registry.by_name(name).held:
                args["held"] = True
            r = self.run(name, **args)
            merged.announcements = r.announcements or merged.announcements
            if r.earcons:
                others = list(r.earcons)
                for sound in r.crossings:
                    others.remove(sound)
            merged.crossings += r.crossings
            merged.earcons = others + merged.crossings
            merged.redraw |= r.redraw
            merged.panel_stale |= r.panel_stale
            merged.details_stale |= r.details_stale
            merged.focus = r.focus or merged.focus
            merged.dialog = r.dialog or merged.dialog
            merged.action = r.action or merged.action
            merged.settings_changed |= r.settings_changed
            merged.background |= r.background
            merged.error = r.error or merged.error
            merged.sounds += r.sounds
            merged.voice = r.voice or merged.voice
            merged.stop_voice |= r.stop_voice
            merged.label = r.label or merged.label
            merged.beacon = r.beacon or merged.beacon
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
        return self.run(command.name, pressed_in=region)

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
        and only that (ANN-3), and draw it. Each held step has clicked already, so the
        release plays no tick of its own where nothing changed: it was heard as a second
        click when the key was let go (Phase 2 web checklist 2.10)."""
        self.holding = None
        if self.held_turns and not self.held_moves:
            self.held_turns = 0
            r = self._heading_said(Response(redraw=True, panel_stale=True))
            return self._record("release", self._no_tick(r))
        self.held_turns = 0
        if not self.held_moves:
            return Response()
        self.held_moves = 0
        self._drawn_at = self.clock()
        r = self._no_tick(self._step_heading(self._arrived(Response(redraw=True))))
        path, self._held_path = self._held_path, []
        return self._record("release", self._crossed_after(r, path))

    @staticmethod
    def _no_tick(r: Response) -> Response:
        r.earcons = [e for e in r.earcons if e != "tick"]
        return r

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
                "tick": self.earcon_on("tick"), "earcon": self.earcon_file("tick"),
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
        v = self.settings
        frame = self._scene.build(copy.copy(self.world), width, height, current=current, highlight=self.selected,
                                  centre_cross=v["centre_cross"],
                                  layers=self.visible.shown_layers(self.world.zoom_m),
                                  min_widths=self.visible.min_widths(self.world.zoom_m),
                                  interval=self._interval(), theme=self.theme(), isolate=self.isolated,
                                  # Names are left out while a key is held, and drawn on the release.
                                  names=v["map_names"] and self.holding is None,
                                  label_scale=v["label_size"] / 100.0, heading_up=v["heading_up"])
        self.last_frame = {k: frame[k] for k in ("project_ms", "choose_ms", "projecting_ms", "points")}
        return frame

    def focus_rect(self, width: int, height: int) -> dict:
        """Where a magnifier should look on a map of this size: a small square round the
        centre, where the location always is (ACC-8, DP146)."""
        from mapcore.render import scene as scene_mod

        return scene_mod.focus_rect(width, height)

    def scene_background(self) -> str:
        """The colour behind the map, for a shell to show before the first drawing is ready."""
        return self.theme()["background"]

    def theme(self) -> dict:
        """The theme the map is drawn with: the chosen theme with the map display setting on top
        (VIS-2, DP108)."""
        return self._theme_and_refused()[0]

    def _theme_and_refused(self) -> tuple[dict, list[str]]:
        from mapcore.render import themes

        v = self.settings
        key = tuple(v[k] for k in ("theme", "map_fill", "map_borders", "fill_colour", "border_colour", "outline_colour"))
        if self._theme_cache is None or self._theme_cache[0] != key:
            self._theme_cache = (key, themes.effective(*key))
        return self._theme_cache[1]

    def panel(self) -> list[dict]:
        """The Information panel groups (UX section 6), as plain data."""
        zoom = self.world.zoom_m
        shown = self.visible.shown_layers(zoom)
        heading = describer.words_facing(self.world, self.settings)
        key = (self.world.lat, self.world.lon, self.settings["units"], self.settings["bearing"],
               self.settings["nearby_count"], zoom, shown, heading, self._interval(), self._crossed_gen,
               id(self.crossed))
        if self._panel_cache and self._panel_cache[0] == key:
            return self._panel_cache[1]
        units = self.settings["units"]
        within = []
        for a in self.areas:   # the distance and direction to its centre, as Nearby has (P2-T17k, DP155)
            distance, bearing, _ = geodesy.inverse(self.world.lat, self.world.lon, *box_centre(a.record["bbox"]))
            within.append({"id": a.id, "level": 1, "label": say(
                "within.here" if distance < HERE_M else "within.item", name=a.name,
                distance=words.distance_text(distance, units),
                direction=words.direction_text(bearing, self.settings["bearing"], heading))})
        inside = {a.id for a in self.areas}   # Contains is never limited by the zoom (ANN-7)
        count = self.settings["nearby_count"]
        # Nearby searches within the zoom (NAV-13), and lists only visible features.
        near = self.store.nearby(self.world.lat, self.world.lon, zoom, limit=count + len(inside) + 1, exclude=inside,
                                 layers=shown, accept=lambda a: self.visible.big_enough(self.layers.get(a.layer), a.record, zoom)
                                 and self._interval_ok(a.record))
        # A line you are on, such as the graticule's 100 degrees west at 100 degrees west, is not
        # nearby, as an area you are in is not: it was listed as "0 metres north" (P2-T18e).
        near = [n for n in near if n.distance_m >= HERE_M or self._geometry(n.area) != "line"]
        # Within: you are inside, so its place is the centre of the area, taken as the centre of
        # its bounding box (the PO's answer, 8 November 2026).
        self._spots = {("within", a.id): (a, *box_centre(a.record["bbox"])) for a in self.areas}
        self._spots.update({("nearby", n.area.id): (n.area, n.lat, n.lon) for n in near[:count]})
        self._spots.update({("crossed", c.area.id): (c.area, c.lat, c.lon) for c in self.crossed})
        nearby = [{"id": n.area.id, "label": describer.nearby_label(n, units, self.settings["bearing"], heading),
                   "level": 1} for n in near[:count]]
        crossed = self._crossed_items(heading)
        groups = {g["id"]: g for g in [
            {"id": "within", "label": self._group_label("within", within), "items": within, "empty": say("place.none")},
            {"id": "nearby", "label": self._group_label("nearby", nearby), "items": nearby, "empty": say("nearby.none")},
            {"id": "crossed", "label": self._group_label("crossed", crossed), "items": crossed,
             "empty": say("crossed.none")},
        ]}
        groups = [groups[g] for g in registry.panel_groups()]   # in the registry's order, as their keys are
        self._panel_cache = (key, groups)
        return groups

    def _geometry(self, area) -> str:
        layer = self.layers.get(area.layer)
        return layer.geometry if layer is not None else "area"

    @staticmethod
    def _group_label(group: str, items: list) -> str:
        """A group heading with how many items it holds, such as "Nearby, 5 items" (P2-T17k,
        desktop checklist 10.4). Go to Nearby and the like keep the plain name."""
        name, n = say(f"panel.{group}"), len(items)
        return say("panel.count_none", group=name) if n == 0 else (
            say("panel.count_one", group=name) if n == 1 else say("panel.count", group=name, count=n))

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
        layer = self.layers.get(area.layer)
        if layer is None or layer.geometry == "area":   # a line or a point has no area (P2-T5)
            lines.append(say("details.area", value=words.area_text(area.area_km2, self.settings["units"])))
        s = self.world
        if self.selected and (not self.areas or self.areas[0].id != self.selected):
            lines.append(say("details.centre", value=words.coordinates_text(s.lat, s.lon, self.settings["coordinates"],
                                                                          self._coordinate_step())))
        lines.append(say("details.source", value=self._source_text(area)))
        return "\n".join(lines)

    def registry(self) -> dict:
        return registry.describe(self.platform, self.settings.keys)

    def toggles(self) -> dict[str, bool]:
        """Whether each menu item with a tick is on, by command name."""
        return {"step.link": bool(self.world.link), "sound.mute": bool(self.settings["mute"]),
                "help.describer": bool(self.describing), "beacon.toggle": bool(self.settings["beacon_on"]),
                "isolate.toggle": self.isolated is not None}

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
        """Which file to play for an earcon (SON-8): the user's own if one is set, else the
        default, and how loud, from the earcon's own volume (P2-T17p, DP163). A sound with no
        volume of its own, such as the beacon, is at full volume here."""
        from mapcore.describe import earcon_list

        default = next((e["file"] for e in earcon_list() if e["event"] == event), None)
        custom = self.settings.values.get(f"earcon_{event}", "")
        return {"event": event, "custom": custom or None, "default": default,
                "gain": self.settings.values.get(f"earcon_volume_{event}", 100) / 100.0}

    def earcon_on(self, event: str) -> bool:
        """Whether an earcon plays: sound not muted, and its own switch on (P2-T8; SON-6, SON-7).
        A sound that is not an earcon, such as a layer's own, has no switch."""
        return not self.settings["mute"] and self.settings.values.get(f"earcon_on_{event}", True)

    # The sound scene (P2-T6a; SON-1, SON-2, SON-9, AD-10) --------------------------

    def curve(self):
        """The distance curve, with the user's choices: linear or logarithmic, and the minimum volume (DP137)."""
        from mapcore.sound import CurveSettings

        base = CurveSettings.from_defaults(self.defaults)
        return replace(base, model=self.settings["sound_curve"], min_gain=self.settings["min_volume"] / 100.0)

    def place_sound(self, sound: str, lat: float, lon: float) -> dict:
        """How to play `sound` heard from (lat, lon), from where you are: its direction relative to
        ahead in the orientation you are in (SON-2), its loudness for its distance against the zoom
        (SON-9), the lower pitch and muffling behind, and beyond the view (DP80). As a dict for the
        shells, with the file to play. Nothing is played here (AD-10)."""
        from mapcore.sound.scene import place

        w = self.world
        distance, bearing, _ = geodesy.inverse(w.lat, w.lon, lat, lon)
        ahead = describer.facing(w) or 0.0
        placed = place(sound, bearing, distance, ahead, w.zoom_m, self.curve(), self.settings["sound_mode"],
                       beyond_tone=self.settings["beyond_view"] == "tone"   # the tone switched off: quiet and muffled
                       and self.settings["earcon_on_beyond_view"]).to_dict()
        placed["file"] = self.earcon_file(placed["sound"])
        placed["gain"] *= placed["file"]["gain"]   # the earcon's own volume (P2-T17p)
        return placed

    # The orientation beacon (P2-T9; SON-10, SON-2) -----------------------------------

    def beacon(self) -> dict:
        """The beacon now: whether it is on, how often it repeats, and how to play it, placed by the
        sound scene from the direction of its target, the North Pole unless the setting chooses
        another place (P2-T18g), relative to the way you face, with the lower pitch and muffling
        behind. Its loudness is its own volume, not the distance: it fades near its target, where
        the direction is unstable, and is silent within 100 km.
        placed is None when it is off, muted or silent. Nothing is played here (AD-10)."""
        from mapcore.sound.scene import place

        on = bool(self.settings["beacon_on"])
        out = {"on": on, "placed": None, "interval_s": float(self.settings["beacon_interval_s"])}
        if not on or self.settings["mute"]:
            return out
        w = self.world
        distance, bearing = self._beacon_target()
        fade = self._beacon_fade(distance)
        if fade <= 0.0:
            return out
        placed = place("beacon", bearing, 0.0, describer.facing(w) or 0.0, w.zoom_m, self.curve(),
                       self.settings["sound_mode"]).to_dict()
        placed["distance_m"] = distance
        placed["file"] = self.earcon_file("beacon")
        placed["file"]["gain"] = self.settings["beacon_volume"] / 100.0   # its own volume, not the earcons'
        placed["gain"] = placed["file"]["gain"] * fade
        out["placed"] = placed
        return out

    # Where each choice of "Orientation beacon: comes from" is (P2-T18g). A pole has no one
    # longitude, so it is taken on your own, which gives the true direction to it.
    BEACON_TARGETS = {"north_pole": (90.0, None), "south_pole": (-90.0, None), "equator_0e": (0.0, 0.0),
                      "equator_90e": (0.0, 90.0), "equator_180": (0.0, 180.0), "equator_90w": (0.0, -90.0)}

    def _beacon_target(self) -> tuple[float, float]:
        """The distance and bearing from here to the beacon's target, the place chosen in Settings.
        Pins join the choices in Phase 4."""
        w = self.world
        lat, lon = self.BEACON_TARGETS.get(self.settings["beacon_target"], self.BEACON_TARGETS["north_pole"])
        distance, bearing, _ = geodesy.inverse(w.lat, w.lon, lat, w.lon if lon is None else lon)
        return distance, bearing

    def _beacon_target_name(self) -> str:
        """The target's name, as Settings lists it, such as "the South Pole", for "silent near ..."."""
        field = next(f for t in settings_mod.schema()["tabs"] for f in t["fields"] if f["id"] == "beacon_target")
        name = dict(field["choices"]).get(self.settings["beacon_target"], "")
        return name[:1].lower() + name[1:] if name.startswith("The ") else name

    def _beacon_fade(self, distance_m: float) -> float:
        """1 away from the pole, falling evenly to 0 at the silent distance."""
        d = self.defaults.get("beacon", {})
        silent, start = float(d.get("silent_within_m", 100000)), float(d.get("fade_from_m", 200000))
        if distance_m <= silent:
            return 0.0
        return min(1.0, (distance_m - silent) / (start - silent)) if start > silent else 1.0

    def _beacon_toggle(self, **_a) -> Response:
        on = not self.settings["beacon_on"]
        self.settings.set("beacon_on", on)
        r = Response(settings_changed=True)
        if not on:
            return r.speak(say("beacon.off"), ASSERTIVE)
        if self._beacon_fade(self._beacon_target()[0]) <= 0.0:
            return r.speak(say("beacon.on_near_pole", target=self._beacon_target_name()), ASSERTIVE)
        return r.speak(say("beacon.on_muted" if self.settings["mute"] else "beacon.on"), ASSERTIVE)

    def _beacon_told(self, name: str, response: Response) -> None:
        """Says once when the beacon goes silent near its target, and when it comes back
        further away (SON-10). Then gives the response the beacon as it is now."""
        if self.settings["beacon_on"]:
            near = self._beacon_fade(self._beacon_target()[0]) <= 0.0
            if name != "beacon.toggle" and self._beacon_near is not None and near != self._beacon_near:
                response.speak(say("beacon.near_pole", target=self._beacon_target_name()) if near
                               else say("beacon.back"), POLITE)
            self._beacon_near = near
        else:
            self._beacon_near = None
        response.beacon = self.beacon()

    def sound_problem(self, problem: str) -> Response:
        """The shell's sound player could not do something: "no_device" or "no_hrtf" (P2-T6b)."""
        return Response().speak(say(f"sound.{problem}"), ASSERTIVE)

    def earcon_failed(self, event: str) -> Response:
        """The shell could not play the user's own file: the default plays, and the user is told (SON-8)."""
        from mapcore.describe import earcon_list

        name = next((e["label"] for e in earcon_list() if e["event"] == event), event)
        return Response().speak(say("sound.own_file_failed", sound=name), ASSERTIVE)

    def start_label(self) -> str:
        """The map region's name as the focus first arrives on it at start (P2-T17d). The screen
        reader reads the window's title, TobyMap, then this name, so the start is heard in full.
        Spoken as well, the start was cut off by that reading and "Press F1 for keys" was lost."""
        if not self.store.packs:
            return say("packs.none_installed")
        return say("start_label", place=self._place_text())

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
        self._beacon_told(name, response)
        response.stop_voice = response.voice is None or self.settings["mute"]
        if self.settings["mute"]:
            response.earcons = []
            response.crossings = []
            response.sounds = []
            response.voice = None
        elif name != "sound.preview":   # The sounds in Help plays an earcon even when it is switched off
            response.earcons = [e for e in response.earcons if self.earcon_on(e)]
            response.crossings = [e for e in response.crossings if self.earcon_on(e)]
            response.sounds = [s for s in response.sounds if self.earcon_on(s["sound"])]
        spoken = [a["text"] for a in response.announcements if a["channel"] == SPEECH]
        label = response.label
        if label and label not in spoken:   # a spatial label can be repeated too (ANN-4)
            spoken.append(label)
        if spoken and name != "speech.repeat":
            self.last_spoken = " ".join(spoken)
        if started is not None:
            self.trace.append({"command": name, "ms": (self.clock() - started) * 1000, "at": time.time(),
                               "spoken": spoken, "earcons": list(response.earcons)})
            del self.trace[:-2000]
        return response

    def _here(self) -> list:
        """The areas at the location that are said, smallest first, and notes why none is."""
        areas, self.why_none_here = self._said_at(self.world.lat, self.world.lon)
        return areas

    def _said_at(self, lat: float, lon: float) -> tuple[list, str | None]:
        """The areas at a point from the layers that are on and inside their zoom range,
        smallest first: what is drawn is what is said (DP160, SCP-6). With none, why:
        "layers_off" when every area here is in a layer that is off, "out_of_zoom" when
        some are on but outside their zoom range, None when there are no areas here."""
        everything = self.store.at(lat, lon)
        shown = self.visible.shown_layers(self.world.zoom_m)
        areas = [a for a in everything if a.layer in shown]
        if areas or not everything:
            return areas, None
        active = self.layers.active()
        return areas, "out_of_zoom" if any(a.layer in active for a in everything) else "layers_off"

    def _place_text(self) -> str:
        return describer.place_text(self.areas, self.why_none_here)

    def _units(self) -> str:
        return self.settings["units"]

    def _zoom_step(self) -> str:
        return describer.zoom_step_text(self.world, self._units())

    def _interval(self) -> int:
        """Degrees between lines of latitude and longitude (DAT-13)."""
        return int(self.settings["graticule_interval"])

    def _interval_ok(self, record: dict) -> bool:
        """A line that names the intervals it belongs to is used only at an interval it names.
        Nothing here knows which layer it is (AD-11)."""
        intervals = record.get("intervals")
        return intervals is None or self._interval() in intervals

    def _crossing_sounds(self, r: Response, path) -> Response:
        """Add the crossing sound of each line a step's path crosses, in the order crossed, for
        the layers that are shown and have one (SCP-7, DAT-13). A layer with no crossing sound,
        or that is off or out of its zoom range, costs nothing. An area layer's sound, such as
        Countries', plays when the step ends in a different area of that layer from the one it
        started in, or in none: it crossed a border (P2-T17i). A step that leaves an area and
        comes back into it within the step is not counted."""
        shown = self.visible.shown_layers(self.world.zoom_m)
        layers = {l.id: l for l in self.layers.layers() if l.id in shown and l.crossing_earcon}
        if not layers or not path:
            return r
        sounds = [layers[c.area.layer].crossing_sound(c.area.record)   # its type's own, or the layer's
                  for c in self.store.crossed_lines(path, layers=set(layers),
                                                    accept=lambda a: self._interval_ok(a.record))]
        areas = [l for l in layers.values() if l.geometry == "area"]
        if areas:
            (lat0, lon0), (lat1, lon1) = path[0], path[-1]
            start = self.store.at(lat0, geodesy.wrap_lon(lon0))
            end = self.store.at(lat1, geodesy.wrap_lon(lon1))
            for layer in areas:
                if {a.id for a in start if a.layer == layer.id} != {a.id for a in end if a.layer == layer.id}:
                    sounds.append(layer.crossing_earcon)
        for sound in sounds:
            r.earcon(sound)
            r.crossings.append(sound)
        return r

    # Crossed and passed (P2-T5, ANN-2, architecture 7.5) ------------------------

    def _hold_path(self, path) -> None:
        """Join a held step's path to the steps before it, so the list after the release
        covers the whole run. Longitudes carry on, as in a path, so the joins never look
        like a jump over a pole."""
        path = list(path)
        if self._held_path and path:
            shift = round((self._held_path[-1][1] - path[0][1]) / 360.0) * 360.0
            path = [(lat, lon + shift) for lat, lon in path[1:]]
        self._held_path += path

    def _crossed_clear(self) -> None:
        """A jump: there is no path, so the list of the last move is emptied."""
        self._crossed_gen += 1
        self._crossed_job = None
        self.crossed = []
        self._held_path = []

    def passed_distance_m(self) -> float:
        """The passed nearby distance: a share of the step, or a fixed distance (ANN-2, DP58)."""
        if self.settings["passed_nearby"] == "fixed":
            return float(self.settings["passed_fixed_m"])
        return self.world.step_m * self.settings["passed_percent"] / 100.0

    def _crossed_after(self, r: Response, path) -> Response:
        """After a move is described, the search along its path waits to be done in the
        background (architecture 7.5); the list is emptied until it is."""
        self._crossed_gen += 1
        self.crossed = []
        path = [tuple(p) for p in path or ()]
        if len(path) < 2:
            self._crossed_job = None
            return r
        self._crossed_job = {"gen": self._crossed_gen, "path": path, "passed_m": self.passed_distance_m(),
                             "zoom_m": self.world.zoom_m, "layers": self.visible.shown_layers(self.world.zoom_m)}
        r.background = True
        return r

    def crossed_job(self) -> dict | None:
        """The search waiting to be done, taken, or None. Call on the shell's own thread."""
        job, self._crossed_job = self._crossed_job, None
        return job

    def crossed_search(self, job: dict, cancelled=None) -> list | None:
        """Search along the job's path. Safe on another thread: it only reads the store. Gives
        None when a newer move or jump has come since, or `cancelled` says to stop."""
        from mapcore.store.store import Cancelled

        zoom = job["zoom_m"]

        def stale() -> bool:
            return job["gen"] != self._crossed_gen or (cancelled is not None and cancelled())

        def accept(area) -> bool:
            return self.visible.big_enough(self.layers.get(area.layer), area.record, zoom) \
                and self._interval_ok(area.record)

        try:
            found = self.store.along_path(job["path"], job["passed_m"], layers=job["layers"], accept=accept,
                                          cancelled=stale)
        except Cancelled:
            return None
        return None if stale() else found

    def crossed_finish(self, job: dict, found: list | None) -> Response:
        """The search is done: the list replaces the last one, and the earcon says something
        was added, if it is switched on. Nothing is spoken (ANN-2). Call on the shell's thread."""
        if found is None or job["gen"] != self._crossed_gen:
            return Response()
        self.crossed = list(found)
        self._panel_cache = None
        r = Response(panel_stale=True)
        if found and self.earcon_on("crossed_added"):
            r.earcon("crossed_added")
        return r

    def crossed_now(self) -> Response:
        """The whole search at once, for the web worker between key presses, and for tests."""
        job = self.crossed_job()
        if job is None:
            return Response()
        return self.crossed_finish(job, self.crossed_search(job))

    def _crossed_items(self, heading: float | None) -> list[dict]:
        """The list's items, in the order along the path, each with its distance and direction
        from where you are now, relative to the way you face (ANN-2, NAV-12)."""
        units, style, w = self.settings["units"], self.settings["bearing"], self.world
        items = []
        for c in self.crossed:
            distance, bearing, _ = geodesy.inverse(w.lat, w.lon, c.lat, c.lon)
            fields = {"name": c.area.name, "distance": words.distance_text(distance, units),
                      "direction": words.direction_text(bearing, style, heading),
                      "closest": words.distance_text(c.closest_m, units)}
            kind = {"crossed": "crossed", "passed over": "passed_over", "passed": "passed"}[c.kind]
            if distance < HERE_M:   # the step ended on it: "here", not "0 metres north" (P2-T18e)
                kind += "_here"
            items.append({"id": c.area.id, "label": say(f"crossed.{kind}", **fields), "level": 1})
        return items

    def _moved(self, **extra) -> Response:
        self.selected = None
        return Response(redraw=True, panel_stale=True, details_stale=True, **extra)

    def _arrived(self, r: Response) -> Response:
        """Describe the new place against the last described one (ANN-1)."""
        new = self._here()
        text = describer.announcement(self.areas, new, self.why_none_here, self.settings["say_area"],
                                      self.settings["say_place_always"])
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
        before = self._place_now()
        result = self.world.step(direction, turn_deg=self.settings["turn_deg"])
        if result.turned:
            return self._turned(held, repeat, now)
        if not result.moved:
            return Response().earcon("blocked")  # nothing spoken (NAV-1)
        if not held:   # every step is a place to go back to; a held run is one, where it started (DP142)
            self._remember_place(before)
        if held:
            # The Information panel and Details wait for the release (ANN-3).
            self.selected = None
            self.held_moves += 1
            r = Response(redraw=self._draw_due(now))
            if repeat:
                r.earcon("tick")
            self._hold_path(result.path)
            return self._crossing_sounds(r, result.path)
        self.held_moves = 0
        self._drawn_at = now
        r = self._moved()
        if result.pole:   # over a pole, the heading turns round, and is said (NAV-3)
            r.speak(say("movement.pole_crossed", pole=say(f"movement.poles.{result.pole}"),
                        heading=describer.facing_text(self.world)), ASSERTIVE)
        self._held_path = []
        r = self._arrived(r)
        if not result.pole:   # over a pole the heading is said already
            self._step_heading(r)
        return self._crossed_after(self._crossing_sounds(r, result.path), result.path)

    def _turned(self, held: bool, repeat: bool, now: float) -> Response:
        """A turn on the spot (NAV-3, NAV-12): the heading arrow is drawn again, and the
        new heading said. Held, the turns tick and the heading is said on release."""
        self._panel_cache = None
        if held:
            self.held_turns += 1
            r = Response(redraw=self._draw_due(now))
            return r.earcon("tick") if repeat else r
        self.held_turns = 0
        return self._heading_said(Response(redraw=True, panel_stale=True))

    def _heading_said(self, r: Response) -> Response:
        """After a turn: the new heading, or only the tick when the verbosity switch is off (ACC-5)."""
        if not self.settings["say_heading"]:
            return r.earcon("tick")
        return r.speak(say("movement.facing", heading=describer.facing_text(self.world)), ASSERTIVE)

    def _step_heading(self, r: Response) -> Response:
        """In free facing the heading changes along the way; the detailed preset says it after
        every step (ACC-5, DP144)."""
        if self.settings["say_heading_on_step"] and self.world.orientation == "free":
            r.speak(say("movement.facing", heading=describer.facing_text(self.world)), ASSERTIVE)
        return r

    def _turn(self, degrees_setting: str = "large_turn_deg", sign: int = 1, **_a) -> Response:
        """Shift and Ctrl with Left and Right, in free facing: turn by the large or the
        fine amount (NAV-12). In north-fixed and cardinal facing they do nothing, with
        no sound, as Left and Right already turn 90 degrees in cardinal facing (PO notes
        on checklist 2.2 and 2.3)."""
        if self.world.orientation != "free":
            return Response()
        degrees = self.settings[degrees_setting]
        result = self.world.turn(sign * degrees)
        if not result.turned:
            return Response().earcon("blocked")
        return self._turned(False, False, self.clock())

    def _orientation_step(self, direction: int) -> Response:
        """O: north-fixed, cardinal facing, free facing, and round again; Shift+O the other way
        (NAV-11, NAV-12, P2-T17l). It never moves you. The new orientation is said with the way you
        now face."""
        self.world.next_orientation(direction)
        return self._orientation_said(Response(redraw=True, panel_stale=True))

    def _orientation_said(self, r: Response) -> Response:
        self._panel_cache = None
        return r.speak(say(f"movement.orientation_changed.{self.world.orientation}",
                           heading=describer.facing_text(self.world)), ASSERTIVE)

    def _bearing_type(self, **_a) -> Response:
        self._answer_to = self._pressed_in
        return Response(dialog={"kind": "input", "title": say("typing.bearing_title"),
                                "label": say("typing.bearing_label"), "help": say("typing.bearing_help"),
                                "submit": "bearing.set", "ok": say("ui.ok"), "cancel": say("ui.cancel")})

    def _bearing_set(self, text: str = "", **_a) -> Response:
        """A typed bearing: face it. In north-fixed or cardinal facing this switches to free
        facing, and says so (NAV-12). A bearing that can't be read is refused with words that
        name it and list what is accepted, which the shell shows in a message box; the box to
        type in stays open (P2-T17o)."""
        try:
            bearing = parse.parse_bearing(text)
        except ValueError:
            return Response(error=self._refused("bearing", text))
        was_free = self.world.orientation == "free"
        self.world.face(bearing)
        # No jump, so the focus stays on the same item; its words change with the facing.
        r = Response(redraw=True, panel_stale=True,
                     focus=self._focus_back(self.panel_item if self.panel_on_item else None))
        if not was_free:
            return self._orientation_said(r)
        self._panel_cache = None
        return r.speak(say("movement.facing", heading=describer.facing_text(self.world)), ASSERTIVE)

    @staticmethod
    def _refused(box: str, text: str) -> str:
        """The words for a typed answer that can't be read, naming what was typed, such as "hello
        is not a valid bearing." (P2-T17o, the PO's notes on desktop checklist 3.5 and 5.3)."""
        entry = " ".join(text.split())
        return say(f"typing.{box}_error", entry=entry) if entry else say(f"typing.{box}_empty")

    def _goto_coordinates(self, **_a) -> Response:
        self._answer_to = self._pressed_in
        return Response(dialog={"kind": "input", "title": say("typing.goto_title"),
                                "label": say("typing.goto_label"), "help": say("typing.goto_help"),
                                "submit": "goto.set", "ok": say("ui.ok"), "cancel": say("ui.cancel")})

    def _goto_set(self, text: str = "", **_a) -> Response:
        """Typed coordinates: jump there, keeping the zoom and step (NAV-8). One number keeps the
        longitude, a comma and a number keep the latitude, and a direction and degrees, such as
        "north 5", move by that much from here (parse_goto). Past a pole, the move stops at it.
        In cardinal and free facing, "f 24" or "b 2 km" moves forward or back (P2-T17r, DP161)."""
        unit_m = {"imperial": formats.METRES_PER_MILE, "nautical": formats.METRES_PER_NAUTICAL_MILE}
        try:
            kind, a, b = parse.parse_goto(text, unit_m.get(self.settings["units"], 1000.0))
        except ValueError:
            return Response(error=self._refused("goto", text))
        w = self.world
        if kind == "ahead":
            return self._goto_ahead(a)
        if kind == "by":
            lat, lon = w.lat + a, w.lon + b
        else:
            lat, lon = (w.lat if a is None else a), (w.lon if b is None else b)
        r = self._land(self._jump(lat, lon))
        r.focus = self._focus_back()
        return r

    def _goto_ahead(self, metres: float) -> Response:
        """Forward or back by a distance, along the way you face, as Up and Down step: over a
        pole you come out facing the other way, which is said. A jump, so Alt+comma comes back.
        North-fixed has no forward, so the box says so and stays open (DP161)."""
        w = self.world
        if w.orientation == "north-fixed":
            return Response(error=say("typing.goto_facing_only"))
        lat, lon = w.lat, w.lon
        result = w.forward(1 if metres >= 0 else -1, abs(metres))
        if not result.moved:   # east or west at a pole
            return Response().earcon("blocked")
        w.lat, w.lon = lat, lon   # the jump moves there, after keeping this place
        r = self._jump(result.lat, result.lon)
        if result.pole:
            r.speak(say("movement.pole_crossed", pole=say(f"movement.poles.{result.pole}"),
                        heading=describer.facing_text(w)), ASSERTIVE)
        r = self._land(r)
        r.focus = self._focus_back()
        return r

    # Jumping and the location history (NAV-8, NAV-10, DP142, DP158) ----------

    @staticmethod
    def _valid_place(p) -> bool:
        return isinstance(p, dict) and all(isinstance(p.get(k), (int, float)) for k in ("lat", "lon", "zoom_m", "step_m"))

    def _place_now(self) -> dict:
        w = self.world
        return {"lat": w.lat, "lon": w.lon, "zoom_m": w.zoom_m, "step_m": w.step_m}

    def _remember_place(self, place: dict | None = None) -> None:
        """Before a step or a jump the place, zoom and step are kept, and any way forward is
        forgotten (DP142). Back and forward never add one, so the whole list can be gone through."""
        self.back_places.append(place or self._place_now())
        del self.back_places[:-PLACE_LIMIT]
        self.forward_places.clear()

    def _jump(self, lat: float, lon: float, zoom_m: float | None = None, step_m: float | None = None) -> Response:
        """Move without a step. The zoom stays unless a place with its own is given."""
        self._remember_place()
        self._go_to(lat, lon, zoom_m, step_m)
        self._crossed_clear()
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

    def _history_words(self, place: dict) -> str | None:
        """What a place in the location history is called: the areas there in the layers shown at
        its zoom, smallest first. None when there are none, such as when its only areas are in a
        layer switched off since: then it is left out of the list, and Alt+comma and Alt+full stop
        pass over it, so you are never offered a place you cannot see (DP158, DP160). It stays in
        the history, and comes back if the layer is switched on again."""
        key = (place["lat"], place["lon"])
        if key not in self._areas_at:
            if len(self._areas_at) > 4 * PLACE_LIMIT:
                self._areas_at.clear()
            self._areas_at[key] = self.store.at(place["lat"], place["lon"])
        shown = self.visible.shown_layers(place["zoom_m"])
        areas = [a for a in self._areas_at[key] if a.layer in shown]
        return describer.place_text(areas, None) if areas else None

    def _history_place(self, offset: int) -> dict:
        """The place offset places back (-) or forward (+) from where you are now."""
        if offset < 0:
            return self.back_places[offset]
        return self.forward_places[-offset]

    def _go_through(self, direction: int) -> Response:
        """Alt+comma or Alt+full stop: back or forward to the next place in the location history
        that is listed in it (DP158). Nothing to go to plays the blocked sound."""
        source = self.back_places if direction < 0 else self.forward_places
        for n in range(1, len(source) + 1):
            if self._history_words(self._history_place(direction * n)) is not None:
                return self._travel(direction * n)
        return Response().earcon("blocked")

    def _travel(self, offset: int) -> Response:
        """Go offset places back (-) or forward (+) through the location history, as that many
        presses of Alt+comma or Alt+full stop would, places left out of the list included. The
        zoom and step come back with the place (DP77). No place is added, so the whole history
        can be gone through again (DP142)."""
        source, other = (self.back_places, self.forward_places) if offset < 0 else (self.forward_places,
                                                                                    self.back_places)
        place = self._place_now()
        for _ in range(abs(offset)):
            other.append(place)
            place = source.pop()
        del other[:-PLACE_LIMIT]
        self._go_to(place["lat"], place["lon"], place["zoom_m"], place["step_m"])
        self._crossed_clear()
        return self._land(Response(redraw=True, panel_stale=True, details_stale=True, settings_changed=True))

    def _changed_sizes(self, zoom_before: float, step_before: float) -> str:
        """Only what changed: the zoom, the step, or both when they are linked
        (PO feedback on checklist 7, second pass). Linked, both are always said, even when
        the nearest size in the list is the one already in use (NAV-2, P2-T17j)."""
        if self.world.link:
            return self._zoom_step()
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
        self.areas = self._here()   # a layer may have come into or gone out of its zoom range (DP160)
        return self._sizes_said(Response(redraw=True, panel_stale=True, details_stale=True), before)

    def _step_size(self, direction: int) -> Response:
        before = (self.world.zoom_m, self.world.step_m)
        if not self.world.change_step(direction):
            key = "movement.step_end_larger" if direction > 0 else "movement.step_end_smaller"
            return Response().speak(say(key, zoom_step=say(
                "movement.step_only", step=words.distance_text(self.world.step_m, self._units()))), ASSERTIVE)
        return self._sizes_said(Response(redraw=True, panel_stale=True), before)

    def _sizes_said(self, r: Response, before: tuple[float, float]) -> Response:
        """The new zoom or step, or only the tick when the verbosity switch is off (ACC-5).
        H still says them."""
        if not self.settings["say_zoom_step"]:
            return r.earcon("tick")
        return r.speak(self._changed_sizes(*before), ASSERTIVE)

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
        item, group = self.panel_item, self.panel_group
        known = {(g["id"], i["id"]) for g in self.panel() for i in g["items"]}
        if (group, item) not in known:
            group = next((g for g, i in known if i == item), None)
        if group is None:
            item = self.areas[0].id if self.areas else None
        return Response(focus={"region": "panel", "group": group or "within", "item": item}, panel_stale=True)

    def _select(self, item: str | None = None, group: str | None = None, **_a) -> Response:
        """The item focused in the Information panel, and its group (within, nearby or crossed).
        A group heading comes with no item: F3 still goes back to the item last focused, but
        Hear its direction is then on the heading, not on that item (P2-T17f)."""
        self.panel_on_item = bool(item)
        self.panel_at_group = group or self.panel_at_group
        if item:
            self.panel_item, self.panel_group = item, group
        if item == self.selected:
            return Response()
        self.selected = item
        return Response(redraw=True, details_stale=True)

    def _hear(self, item: str | None = None, group: str | None = None, **_a) -> Response:
        """Hear its direction (DP143, SON-3): on an item of the Information panel, its
        layer's sound from its direction and distance, then its name and distance in the spatial
        voice from the same place. The label also goes to Braille without speech, to the history,
        and, if that setting is on, to the screen reader (ANN-4, ACC-1). Nothing is played here:
        the sound scene says how, and the shells play it (AD-10)."""
        from mapcore.sound.scene import place

        self.panel()   # the items' places are kept as the panel is made
        if not item and self.panel_on_item:
            item, group = self.panel_item, self.panel_group
        groups = [group] if group else ["within", "nearby", "crossed"]
        spot = next((self._spots[(g, item)] for g in groups if (g, item) in self._spots), None)
        if spot is None:   # a group heading: nothing is said or done (the PO, 10 November 2026)
            return Response()
        area, lat, lon = spot
        w = self.world
        distance, bearing, _ = geodesy.inverse(w.lat, w.lon, lat, lon)
        label = say("hear.label", name=area.name, distance=words.distance_text(distance, self._units()))
        r = Response()
        layer = self.layers.get(area.layer)
        r.sounds.append(self.place_sound((layer.sound if layer else None) or "item_direction", lat, lon))
        voice = place("voice", bearing, distance, describer.facing(w) or 0.0, w.zoom_m, self.curve(),
                      self.settings["sound_mode"]).to_dict()   # the label is never swapped for the fixed tone
        voice["gain"] *= self.settings["voice_volume"] / 100.0
        piper, stretch = split_rate(self.settings["voice_rate"] / 100.0)
        # Behind you the label is lower at the same speed, made so by shape_voice, not played
        # slower as the item's sound is (P2-T16g, the PO's choice of sample 9).
        pitch, voice["pitch"] = voice["pitch"], 1.0
        r.voice = {"text": label, "placed": voice, "rate": piper, "stretch": stretch, "pitch": pitch, "after": True}
        if self.settings["voice_also_speak"]:   # the screen reader speaks it, and brailles it as it does all speech
            r.speak(label, POLITE)
        elif self.platform == "desktop":         # Braille without speech; a browser has no such route
            r.announcements.append({"text": label, "channel": BRAILLE, "priority": POLITE, "fallback": None})
        r.label = label
        return r

    def _panel_go(self, item: str | None = None, group: str | None = None, **_a) -> Response:
        """Enter on an item of the Information panel: go there, as a jump, so Alt+comma comes back
        (P2-T17k, INF-10, DP155). A point goes to the point; an area to its centre, the centre of
        its bounding box, as Within's distance is; a line to the place its item is about, the
        nearest point or where it was crossed. The focus stays in the panel, on the first item of
        the same group, as the group's items change with the place."""
        self.panel()   # the items' places are kept as the panel is made
        if not item and self.panel_on_item:
            item, group = self.panel_item, self.panel_group
        groups = [group] if group else ["within", "nearby", "crossed"]
        found = next(((g, self._spots[(g, item)]) for g in groups if (g, item) in self._spots), None)
        if found is None:   # a group heading: nothing is said or done (the PO, 10 November 2026)
            return Response()
        group, (area, lat, lon) = found
        layer = self.layers.get(area.layer)
        if (layer is None or layer.geometry == "area") and area.record.get("bbox"):
            lat, lon = box_centre(area.record["bbox"])
        r = self._land(self._jump(lat, lon))
        r.focus = {"region": "panel", "group": group, "item": None}
        return r

    def _focus_back(self, item: str | None = None) -> dict | None:
        """Where the focus goes once Go to's or the bearing's box has its answer: back to the
        Information panel or Details if it was opened there (P2-T17k, desktop checklist 10.5). In
        the panel, after a jump, the first item of the same group, as its items have changed. From
        the map or a menu, None: the shell's box closes into the map."""
        if self._answer_to == "details":
            return {"region": "details"}
        if self._answer_to == "panel":
            return {"region": "panel", "group": self.panel_at_group or "within", "item": item}
        return None

    def voice_problem(self, problem: str) -> Response:
        """The shell's voice could not do something: "missing", "failed" or "loading" (P2-T7)."""
        return Response().speak(say(f"voice.{problem}"), ASSERTIVE)

    def _repeat(self, **_a) -> Response:
        return Response().speak(self.last_spoken or say("history.nothing_to_repeat"), ASSERTIVE)

    def _history(self, **_a) -> Response:
        """The location history (NAV-10, DP158): the places you stopped at, the list that Alt+comma
        and Alt+full stop go through, newest first. Places gone back from come first, then where
        you are now, chosen as the list opens, then the places before it. A place whose areas are
        all in layers not shown is left out."""
        rows, lines = [], []
        for offset in range(len(self.forward_places), -len(self.back_places) - 1, -1):
            if offset == 0:
                areas, why = self._said_at(self.world.lat, self.world.lon)
                text = say("history.here", place=describer.place_text(areas, why))
            else:
                text = self._history_words(self._history_place(offset))
            if text is not None:
                rows.append(offset)
                lines.append(text)
        self._history_rows = rows
        return Response(dialog={"kind": "history", "title": say("history.title"), "lines": lines,
                                "text": "\n".join(lines), "help": say("history.help"), "go": "history.go",
                                "current": rows.index(0)})

    def _history_go(self, index: int = -1, **_a) -> Response:
        """Enter on a row of the location history: go there, as Alt+comma or Alt+full stop
        pressed until you arrive, so the list keeps its order and you can go on from there
        (DP158). The row where you are now says the place again."""
        if not 0 <= index < len(self._history_rows):
            return Response().earcon("blocked")
        offset = self._history_rows[index]
        if offset == 0:
            return self._land(Response())
        return self._travel(offset)

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

    def _verbosity_step(self, direction: int) -> Response:
        """A: the next verbosity preset, terse, normal, detailed, and round again; Shift+A the
        other way (P2-T17l). From Custom, A goes to terse and Shift+A to detailed. Says the preset
        and what it says (ACC-5, DP144)."""
        names = list(settings_mod.presets())
        now = self.settings["verbosity"]
        if now in names:
            preset = names[(names.index(now) + direction) % len(names)]
        else:
            preset = names[0] if direction > 0 else names[-1]
        self.settings.set("verbosity", preset)
        return Response(settings_changed=True).speak(say(f"verbosity.{preset}"), ASSERTIVE)

    # Themes, the map display setting and isolate (P2-T12; VIS-2, DP108) -------------------

    def _theme_step(self, direction: int) -> Response:
        """T and Shift+T: the next or previous theme, said by name."""
        from mapcore.render import themes

        names = themes.names()
        now = self.settings["theme"]
        name = names[(names.index(now) + direction) % len(names)] if now in names else names[0]
        self.settings.set("theme", name)
        r = Response(redraw=True, settings_changed=True).speak(
            say("display.theme", theme=themes.theme(name)["label"]), ASSERTIVE)
        return self._colours_kept(r)

    def _colours_kept(self, r: Response) -> Response:
        """In a high contrast theme, a chosen colour below 7 to 1 is not used: say which (VIS-2)."""
        from mapcore import settings as s

        for setting in self._theme_and_refused()[1]:
            r.speak(say("display.colour_refused", what=s.fields()[setting]["label"]), POLITE)
        return r

    def _isolate_toggle(self, **_a) -> Response:
        """Isolate: only the current feature and its outline, and again to show everything (VIS-2)."""
        if self.isolated is not None:
            return self._isolate_off()
        if not self.areas:
            return Response().speak(say("display.isolate_none"), ASSERTIVE)
        self.isolated = self.areas[0].id
        return Response(redraw=True).speak(say("display.isolated", name=self.areas[0].name), ASSERTIVE)

    def _isolate_off(self, **_a) -> Response:
        if self.isolated is None:
            return Response()
        self.isolated = None
        return Response(redraw=True).speak(say("display.isolate_off"), ASSERTIVE)

    def _settings_open(self, **_a) -> Response:
        return Response(dialog={"kind": "settings", "title": say("settings.title")})

    def _reset_ask(self, **_a) -> Response:
        """Reset all settings asks first, in a message box with Reset and Cancel, Cancel first
        (P2-T18h). Reset runs settings.reset_confirm."""
        return Response(dialog={"kind": "confirm", "title": say("reset.title"), "text": say("reset.question"),
                                "ok": say("reset.ok"), "cancel": say("ui.cancel"), "submit": "settings.reset_confirm"})

    def _reset_all(self, **_a) -> Response:
        """Everything back to a new installation's (P2-T18h): settings, keys, layer choices, the
        place, zoom and step, and the location history. The open packs stay. action "reset" tells
        the shell to forget what it keeps itself, such as the web's own sound files; it then saves,
        as settings_changed asks, which writes the new installation's settings."""
        keep = {"map_size": self.map_size, "trace": self.trace}
        self.__init__(platform=self.platform, store=self.store, clock=self.clock)
        for name, value in keep.items():
            setattr(self, name, value)
        self.areas = self._here()
        r = Response(redraw=True, panel_stale=True, details_stale=True, settings_changed=True, action="reset")
        return r.speak(say("reset.done", place=self._place_text()), ASSERTIVE)

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
        r = Response(settings_changed=True, panel_stale=True, details_stale=True, redraw=True)
        if field in ("theme", "map_fill", "map_borders", "fill_colour", "border_colour", "outline_colour"):
            self._colours_kept(r)
        return r

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
        every = say("layers.every_zoom")
        data = self.layer_list()
        # The zoom list, and any zoom a layer already has that is not in it, such as one a pack
        # chose, so the shells can show it in words without making any of their own (3.4).
        values = set(self.world.zoom_list)
        for group in data["groups"]:
            for layer in group["layers"]:
                values.update(z for z in (layer["min_zoom_m"], layer["max_zoom_m"]) if z)
        zooms = [{"value": z, "label": words.distance_text(z, units)} for z in sorted(values)]
        lines = []
        for group in data["groups"]:
            lines.append(group["name"])
            lines.extend(say("layers.item_on" if l["on"] else "layers.item_off", layer=l["name"])
                         for l in group["layers"])
        return Response(dialog={
            "kind": "layers", "title": data["title"], "groups": data["groups"], "text": "\n".join(lines),
            "zooms": zooms, "every_zoom": every,
            "earcons": [{"event": e["event"], "label": e["label"]} for e in earcon_list()],
            "words": {k: say(f"layers.{k}") for k in ("settings_button", "settings_title", "min_zoom", "max_zoom",
                                                      "crossing", "no_sound", "choose_layer", "list")}
            | {"ok": say("ui.ok"), "cancel": say("ui.cancel")},
            "set": "layers.set", "check": "layers.check"})

    def _layers_check(self, low=0.0, high=None, **_a) -> Response:
        """Whether a minimum and maximum zoom can go together; the words say what is wrong."""
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
            if c.pointer or c.region not in ("global", region):
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
        """Play one sound from Help, The sounds (DP134). Mute still applies, but the earcon's
        own switch does not, so you can hear one before switching it on (P2-T8)."""
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

        return scene_mod.view_for(self.world, width, height, self.settings["heading_up"])

    def _click(self, x: float, y: float, width: float, height: float, **_a) -> Response:
        from mapcore.render import globe

        point = globe.from_screen(self._view_scale(width, height), width, height, x, y)
        if point is None:
            return Response().speak(say("off_globe"), ASSERTIVE)
        self._remember_place()
        self.world.lat = max(-90.0, min(90.0, round(point[0], 6)))
        self.world.lon = round(geodesy.wrap_lon(point[1]), 6)
        self._crossed_clear()
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
        self._crossed_clear()
        return self._moved()

    def _hover(self, x: float, y: float, width: float, height: float, **_a) -> Response:
        """The place under the mouse, spoken only if the setting is on. The location does not move."""
        from mapcore.render import globe

        if not self.settings["hover_announce"]:
            return Response()
        point = globe.from_screen(self._view_scale(width, height), width, height, x, y)
        if point is None:
            return Response()
        areas, why_none = self._said_at(point[0], point[1])
        return Response().speak(describer.place_text(areas[:1], why_none), POLITE)

    def _zoom_to(self, direction: int = 0, **_a) -> Response:
        """The wheel or a pinch: to the nearest zoom in the list, one step each time (NAV-13)."""
        return self._zoom(+1 if direction > 0 else -1)
