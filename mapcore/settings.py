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


@lru_cache(maxsize=1)
def schema() -> dict:
    return yaml.safe_load(SCHEMA_FILE.read_text(encoding="utf-8"))


def fields() -> dict[str, dict]:
    return {f["id"]: f for tab in schema()["tabs"] for f in tab["fields"]}


def defaults() -> dict:
    return {fid: f["default"] for fid, f in fields().items()}


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
    if kind == "text":
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
            self.set(k, v, quiet=True)

    def __getitem__(self, field_id: str):
        return self.values[field_id]

    def set(self, field_id: str, value, quiet: bool = False) -> bool:
        try:
            self.values[field_id] = checked(field_id, value)
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
