"""The layer catalogue (P2-T3a; SCP-6, SCP-7, architecture 5.2 and 6.2).

The catalogue is made from the layer definitions in the installed packs, with
the user's own changes on top. The definitions come from the data manager's
layer files (mapdata/config/layers), written into each pack. The user's
changes are kept with the settings, by layer identifier, so they survive a
pack being rebuilt or replaced.

Every part of the core that finds features asks the catalogue which layers
are on: "where am I", change detection, Nearby and the map scene, and from
P2-T5 Crossed and passed. A layer that is off is gone from all of them (SCP-6).

A pack built before P2-T3 has only each layer's id and name. Its layers get
the defaults below: an area layer, on, at every zoom, with no sounds.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

GEOMETRIES = ("area", "line", "point")
DEFAULT_MIN_SIZE = 0.02   # an area must be at least 2% of the zoom distance across (DP80)

# What a layer definition may hold, with the value used when a pack leaves it out.
DEFAULTS = {
    "group": "",
    "geometry": "area",
    "switched_on": True,       # "on" in YAML 1.1 would be read as true, so the definition says switched_on
    "min_zoom_m": 0.0,         # the minimum zoom, the closest at which the layer is visible
    "max_zoom_m": None,        # the maximum zoom, the farthest; None for no limit
    "min_size": DEFAULT_MIN_SIZE,
    "crossing_earcon": None,   # an earcon event, played when a line of the layer is crossed
    "crossing_earcons": None,  # {line type: earcon event}: a line of that type plays its own instead
    "sound": None,             # the sound of its features in "hear its direction" and look around
}
# What the user can change in the layers list (SCP-7).
USER_FIELDS = ("on", "min_zoom_m", "max_zoom_m", "crossing_earcon", "sound")


@dataclass(frozen=True)
class Layer:
    id: str
    name: str
    group: str = ""
    geometry: str = "area"
    on: bool = True
    min_zoom_m: float = 0.0
    max_zoom_m: float | None = None
    min_size: float = DEFAULT_MIN_SIZE
    crossing_earcon: str | None = None
    crossing_earcons: tuple = ()   # (line type, earcon event) pairs, from the layer file
    sound: str | None = None
    changed: tuple = ()        # the fields the user has changed from the pack's definition

    def in_zoom(self, zoom_m: float) -> bool:
        """Whether a zoom distance is within the layer's zoom range (NAV-13)."""
        top = math.inf if self.max_zoom_m is None else self.max_zoom_m
        return self.min_zoom_m <= zoom_m <= top

    def crossing_sound(self, record: dict) -> str | None:
        """The sound for crossing one of the layer's lines: the one its type has, if the layer
        file gives its type one, else the layer's own. A layer switched to no crossing sound is
        silent for every line (SCP-7)."""
        if self.crossing_earcon is None:
            return None
        return dict(self.crossing_earcons).get(record.get("type"), self.crossing_earcon)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "group": self.group, "geometry": self.geometry, "on": self.on,
                "min_zoom_m": self.min_zoom_m, "max_zoom_m": self.max_zoom_m, "min_size": self.min_size,
                "crossing_earcon": self.crossing_earcon, "sound": self.sound, "changed": list(self.changed)}


def _number(value, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be a number of metres, 0 or more")
    return number


def checked(field: str, value):
    """A user's change in the type the field wants, or ValueError."""
    if field not in USER_FIELDS:
        raise ValueError(f"{field!r} is not something a user can change in a layer")
    if field == "on":
        if not isinstance(value, bool):
            raise ValueError("on must be yes or no")
        return value
    if field == "min_zoom_m":
        return _number(value, field)
    if field == "max_zoom_m":
        return None if value is None or value == "" else _number(value, field)
    # A sound: an earcon event, or None for no sound.
    if value is None or value == "":
        return None
    from mapcore.describe import earcon_list

    if value not in {e["event"] for e in earcon_list()}:
        raise ValueError(f"{value!r} is not one of TobyMap's sounds")
    return value


def from_definition(d: dict) -> Layer:
    """A layer from a pack's layer definition, with the defaults for what it leaves out."""
    values = {k: d.get(k, v) for k, v in DEFAULTS.items()}
    if values["geometry"] not in GEOMETRIES:
        values["geometry"] = "area"
    values["min_zoom_m"] = float(values["min_zoom_m"] or 0.0)
    if values["max_zoom_m"] is not None:
        values["max_zoom_m"] = float(values["max_zoom_m"])
    values["min_size"] = float(values["min_size"])
    values["on"] = bool(values.pop("switched_on"))
    by_type = values["crossing_earcons"]
    values["crossing_earcons"] = tuple(sorted((str(k), str(v)) for k, v in by_type.items())) \
        if isinstance(by_type, dict) else ()
    return Layer(id=d["id"], name=d.get("name") or d["id"], **values)


class LayerCatalogue:
    """The layers of the installed packs, in the packs' order, with the user's changes.

    `changes` is a callable giving the user's changes, {layer id: {field: value}},
    so the catalogue always sees the settings in use, even after they are
    replaced by an import. Changes to layers that no pack has are kept, so they
    come back when a pack with that layer is installed.
    """

    def __init__(self, packs, changes):
        self._changes = changes
        self._defined: dict[str, Layer] = {}
        for pack in packs:
            for d in getattr(pack, "layers", None) or []:
                if d.get("id") and d["id"] not in self._defined:   # the first pack's definition wins
                    self._defined[d["id"]] = from_definition(d)

    def _with_changes(self, layer: Layer) -> Layer:
        mine = self._changes().get(layer.id) or {}
        values = {}
        for field, value in mine.items():
            try:
                values[field] = checked(field, value)
            except (ValueError, TypeError):
                continue   # a damaged saved change is left out, never stops the map
        if not values:
            return layer
        return replace(layer, **values, changed=tuple(f for f in USER_FIELDS if f in values))

    def layers(self) -> list[Layer]:
        """Every layer, in display order, as the user has them."""
        return [self._with_changes(layer) for layer in self._defined.values()]

    def get(self, layer_id: str) -> Layer | None:
        layer = self._defined.get(layer_id)
        return None if layer is None else self._with_changes(layer)

    def active(self) -> frozenset:
        """The identifiers of the layers that are on."""
        return frozenset(layer.id for layer in self.layers() if layer.on)

    def is_on(self, layer_id: str) -> bool:
        layer = self.get(layer_id)
        return True if layer is None else layer.on

    def groups(self) -> list[tuple[str, list[Layer]]]:
        """The layers in their groups, each group where its first layer is."""
        out: dict[str, list[Layer]] = {}
        for layer in self.layers():
            out.setdefault(layer.group, []).append(layer)
        return list(out.items())

    def change(self, layer_id: str, field: str, value) -> Layer:
        """Change one thing about a layer: see change_many."""
        return self.change_many(layer_id, {field: value})

    def change_many(self, layer_id: str, values: dict) -> Layer:
        """Change several things about a layer at once, all or none. A change back to the
        pack's own value is forgotten, so a later pack with a new default is followed.
        ValueError for an unknown layer or a value that cannot be used, or a minimum zoom
        larger than the maximum, judged on the layer as it will be, not step by step."""
        base = self._defined.get(layer_id)
        if base is None:
            raise ValueError(f"there is no layer {layer_id!r}")
        values = {field: checked(field, value) for field, value in values.items()}
        current = self.get(layer_id)
        low = values.get("min_zoom_m", current.min_zoom_m)
        high = values.get("max_zoom_m", current.max_zoom_m)
        if high is not None and low > high:
            raise ValueError("the minimum zoom must not be larger than the maximum zoom")
        changes = self._changes()
        mine = dict(changes.get(layer_id) or {})
        for field, value in values.items():
            if getattr(base, field) == value:
                mine.pop(field, None)
            else:
                mine[field] = value
        if mine:
            changes[layer_id] = mine
        else:
            changes.pop(layer_id, None)
        return self.get(layer_id)
