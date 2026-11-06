"""Settings (PLT-5, ANN-5, LOC-1): the schema in settings.yaml, the values, saving and restoring.

The user's changes to layers are kept here too, by layer identifier (SCP-6).

The values are plain JSON-able data, so the desktop keeps them in a file and
the web version in the browser. The remapped keys are kept with them (ACC-3).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

SCHEMA_FILE = Path(__file__).resolve().parent / "settings.yaml"


# Settings renamed since they were first saved: old id -> new id. A saved value
# under the old id is kept under the new one.
RENAMED = {"crossed_earcon": "earcon_on_crossed_added"}
# The switches a verbosity preset sets (P2-T11, DP144).
PRESET_SWITCHES = ("say_area", "say_zoom_step", "say_heading", "say_heading_on_step")


@lru_cache(maxsize=1)
def schema() -> dict:
    data = yaml.safe_load(SCHEMA_FILE.read_text(encoding="utf-8"))
    for tab in data["tabs"]:
        each = tab.pop("each_earcon", None)
        if each:
            tab["fields"] += earcon_fields(each)
    return data


def earcon_fields(each: dict) -> list[dict]:
    """A switch and an own file for every earcon (P2-T8; SON-6, SON-8). Every earcon is
    on at first. The file is a "sound_file": the desktop keeps its path, the web version
    the name of the file kept in the browser."""
    from mapcore.describe import earcon_list

    out = []
    for e in earcon_list():
        if e.get("switch", True):
            out.append({"id": f"earcon_on_{e['event']}", "label": each["on_label"].format(name=e["label"]),
                        "kind": "yes_no", "default": True, "earcon": e["event"]})
        out.append({"id": f"earcon_{e['event']}", "label": each["file_label"].format(name=e["label"]),
                    "kind": "sound_file", "default": "", "earcon": e["event"], "name": e["label"]})
    return out


def fields() -> dict[str, dict]:
    return {f["id"]: f for tab in schema()["tabs"] for f in tab["fields"]}


def defaults() -> dict:
    return {fid: f["default"] for fid, f in fields().items()}


def presets() -> dict[str, dict]:
    """The verbosity presets: the switches each one sets (P2-T11; ACC-5, DP144)."""
    return schema().get("presets", {})


def preset_matching(values: dict) -> str:
    """The preset whose switches are all as in values, or "custom"."""
    for name, switches in presets().items():
        if all(values.get(k) == v for k, v in switches.items()):
            return name
    return "custom"


def checked(field_id: str, value):
    """The value in the type the field wants, or ValueError."""
    f = fields().get(field_id)
    if f is None:
        raise ValueError(f"unknown setting {field_id!r}")
    kind = f["kind"]
    if kind == "yes_no":
        if not isinstance(value, bool):
            raise ValueError(f"{field_id} must be yes or no")
        return value
    if kind == "choice":
        if value not in [c[0] for c in f["choices"]]:
            raise ValueError(f"{value!r} is not a choice for {field_id}")
        return value
    if kind in ("text", "sound_file"):
        if not isinstance(value, str):
            raise ValueError(f"{field_id} must be text")
        return value.strip()
    number = float(value)
    if not f["min"] <= number <= f["max"]:
        raise ValueError(f"{field_id} must be from {f['min']} to {f['max']}")
    return int(number) if number == int(number) else number


class Settings:
    def __init__(self, values: dict | None = None, keys: dict | None = None, layers: dict | None = None):
        self.values = defaults()
        self.keys: dict[str, str] = dict(keys or {})  # command name -> key, the user's own
        # The user's changes to layers, by layer id: {"regions": {"on": False}} (SCP-6, SCP-7).
        self.layers: dict[str, dict] = {k: dict(v) for k, v in (layers or {}).items() if isinstance(v, dict)}
        for k, v in (values or {}).items():
            if k in RENAMED and RENAMED[k] not in (values or {}):
                k = RENAMED[k]
            self.set(k, v, quiet=True)

    def __getitem__(self, field_id: str):
        return self.values[field_id]

    def set(self, field_id: str, value, quiet: bool = False) -> bool:
        """Set one value. Choosing a verbosity preset sets its switches; changing a switch
        makes the preset the one it now matches, or Custom (P2-T11, DP144)."""
        try:
            self.values[field_id] = checked(field_id, value)
            switches = presets().get(self.values[field_id]) if field_id == "verbosity" else None
            if switches:
                self.values.update(switches)
            elif field_id in PRESET_SWITCHES:
                self.values["verbosity"] = preset_matching(self.values)
            return True
        except (ValueError, TypeError):
            if quiet:
                return False
            raise

    def to_dict(self) -> dict:
        return {"values": dict(self.values), "keys": dict(self.keys),
                "layers": {k: dict(v) for k, v in self.layers.items()}}

    @classmethod
    def from_dict(cls, d: dict | None) -> "Settings":
        d = d or {}
        return cls(d.get("values"), d.get("keys"), d.get("layers"))
