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
    held: bool = False
    toggle: bool = False


def split_key(key: str) -> tuple[list[str], str]:
    """"Ctrl+Shift+Page Up" as (["Ctrl", "Shift"], "Page Up"). The plus key itself
    is the last "+": "Ctrl++" is (["Ctrl"], "+")."""
    if key.endswith("+") and (len(key) == 1 or key[-2] == "+"):
        mods = key[:-2].split("+") if len(key) > 1 else []
        return [m for m in mods if m], "+"
    parts = key.split("+")
    return parts[:-1], parts[-1]


def key_text(key: str) -> str:
    """A key as it is said and shown: a symbol becomes a word, so a screen reader
    that does not say punctuation still says it: "Ctrl+," is "Ctrl+Comma" (PO
    feedback on checklist 2, second pass). Any symbol works: one not in the
    templates is named from its Unicode name."""
    if not key:
        return key
    from mapcore.describe import templates

    mods, base = split_key(key)
    if len(base) == 1 and not base.isalnum():
        word = templates().get("key_names", {}).get(base)
        if word is None:
            import unicodedata

            word = unicodedata.name(base, base).capitalize()
        base = word
    return "+".join(mods + [base])


def valid_key(key: str) -> bool:
    mods, base = split_key(key)
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
            held=bool(c.get("held")), toggle=bool(c.get("toggle")),
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


def key_of(command: Command, overrides: dict | None = None) -> str:
    """The command's key: the user's own if they changed it (ACC-3), else the default."""
    if overrides and command.name in overrides:
        return overrides[command.name]
    return command.key


def keymap(platform: str, overrides: dict | None = None) -> dict[str, dict[str, str]]:
    """{region: {key: command name}} for one platform."""
    out: dict[str, dict[str, str]] = {"map": {}, "panel": {}, "global": {}}
    for c in for_platform(platform):
        key = key_of(c, overrides)
        if key:
            out.setdefault(c.region, {})[key] = c.name
    return out


def command_for_key(platform: str, key: str, region: str = "map", overrides: dict | None = None) -> Command | None:
    """The command a key runs when the given region has focus: the region's own
    keys (the map's, or the Information panel's), then the keys that work anywhere."""
    found = [c for c in for_platform(platform) if key_of(c, overrides) == key and c.region in (region, "global")]
    return next((c for c in found if c.region == region), found[0] if found else None)


def commands_for_key(platform: str, key: str, overrides: dict | None = None) -> list[Command]:
    """Every command on a key, in any region: what the key describer lists."""
    return [c for c in for_platform(platform) if key and key_of(c, overrides) == key]


def clash(platform: str, command: str, key: str, overrides: dict | None = None) -> Command | None:
    """The other command that already has this key where they would meet, or
    None. A global key meets every command; a map key meets map and global ones."""
    mine = by_name(command)
    for c in for_platform(platform):
        if c.name == command or key_of(c, overrides) != key:
            continue
        if mine.region == "global" or c.region == "global" or mine.region == c.region:
            return c
    return None


def menus(platform: str, overrides: dict | None = None) -> list[dict]:
    """The menu bar: [{label, access, items: [{name, label, key, key_text, toggle}]}], in registry order."""
    out = []
    for menu in _raw()["menus"]:
        items = [{"name": c.name, "label": c.label, "key": key_of(c, overrides),
                  "key_text": key_text(key_of(c, overrides)), "toggle": c.toggle}
                 for c in for_platform(platform) if c.menu == menu["label"]]
        if items:
            out.append({"label": menu["label"], "access": menu.get("access", ""), "items": items})
    return out


def latest_only(platform: str) -> list[str]:
    return [c.name for c in for_platform(platform) if c.latest_only]


def held_keys(platform: str) -> list[str]:
    return [c.name for c in for_platform(platform) if c.held]


def describe(platform: str, overrides: dict | None = None) -> dict:
    """Everything a shell needs from the registry, as plain data."""
    return {"keymap": keymap(platform, overrides), "menus": menus(platform, overrides),
            "latest_only": latest_only(platform), "held": held_keys(platform)}
