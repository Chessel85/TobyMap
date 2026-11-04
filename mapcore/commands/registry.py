"""Reading the command registry (AD-3).

Key names are shared by both shells. Each shell turns its own key events into
these names, then looks them up in the key map built here:

* letters and digits: "C", "R", "1"
* named keys: Up, Down, Left, Right, Page Up, Page Down, Home, End, Space,
  Enter, Backspace, Delete, Escape, Tab, F1 to F12
* modifiers first, in the order Ctrl, Alt, Shift, joined with "+":
  "Shift+Space", "Ctrl+Space", "Ctrl+Shift+Page Up"
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

REGISTRY_FILE = Path(__file__).resolve().parent / "registry.yaml"
ALL_PLATFORMS = ("desktop", "web")
MODIFIERS = ("Ctrl", "Alt", "Shift")
NAMED_KEYS = {"Up", "Down", "Left", "Right", "Page Up", "Page Down", "Home", "End", "Space", "Enter",
              "Backspace", "Delete", "Escape", "Tab", "Insert", "Caps Lock", *(f"F{i}" for i in range(1, 13))}


@dataclass(frozen=True)
class Command:
    name: str
    label: str
    key: str
    region: str
    menu: str
    platforms: tuple[str, ...]
    latest_only: bool = False
    pointer: bool = False


def valid_key(key: str) -> bool:
    parts = key.split("+")
    mods, base = parts[:-1], parts[-1]
    if any(m not in MODIFIERS for m in mods) or len(set(mods)) != len(mods):
        return False
    if mods != sorted(mods, key=MODIFIERS.index):
        return False
    return base in NAMED_KEYS or (len(base) == 1 and (base.isupper() or base.isdigit() or not base.isalpha()))


@lru_cache(maxsize=1)
def _raw() -> dict:
    return yaml.safe_load(REGISTRY_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load() -> tuple[Command, ...]:
    return tuple(
        Command(
            name=c["name"], label=c["label"], key=c.get("key") or "", region=c.get("region", "map"),
            menu=c.get("menu") or "", platforms=tuple(c.get("platforms") or ALL_PLATFORMS),
            latest_only=bool(c.get("latest_only")), pointer=bool(c.get("pointer")),
        )
        for c in _raw()["commands"]
    )


def by_name(name: str) -> Command:
    for c in load():
        if c.name == name:
            return c
    raise KeyError(name)


def for_platform(platform: str) -> list[Command]:
    return [c for c in load() if platform in c.platforms]


def keymap(platform: str) -> dict[str, dict[str, str]]:
    """{region: {key: command name}} for one platform."""
    out: dict[str, dict[str, str]] = {"map": {}, "global": {}}
    for c in for_platform(platform):
        if c.key:
            out.setdefault(c.region, {})[c.key] = c.name
    return out


def menus(platform: str) -> list[dict]:
    """The menu bar: [{label, access, items: [{name, label, key}]}], in registry order."""
    out = []
    for menu in _raw()["menus"]:
        items = [{"name": c.name, "label": c.label, "key": c.key}
                 for c in for_platform(platform) if c.menu == menu["label"]]
        if items:
            out.append({"label": menu["label"], "access": menu.get("access", ""), "items": items})
    return out


def latest_only(platform: str) -> list[str]:
    return [c.name for c in for_platform(platform) if c.latest_only]


def describe(platform: str) -> dict:
    """Everything a shell needs from the registry, as plain data."""
    return {"keymap": keymap(platform), "menus": menus(platform), "latest_only": latest_only(platform)}
