"""Reading the command list, registry.yaml (AD-3): the commands, where each works and its menu.

The keys are in the key maps (keys.py, P3-T31a). The functions here that need keys take "keys", the
keys in use by command name, as the session makes them from the chosen key map and your keys. A
command missing from them has the key of its version's Windows key map, and with no keys at all
that key map's keys are used.

Key names are shared by both shells. Each shell turns its own key events into
these names, then looks them up in the keys built here:

* letters and digits: "C", "R", "1"
* named keys: Up, Down, Left, Right, Page Up, Page Down, Home, End, Space,
  Enter, Backspace, Delete, Escape, Tab, F1 to F12
* modifiers first, in the order Ctrl, Alt, Shift, Cmd, joined with "+":
  "Shift+Space", "Ctrl+Space", "Ctrl+Shift+Page Up", "Shift+Cmd+F". On a Mac,
  Ctrl is the Control key, Alt is Option and Cmd is Command; Windows has no Cmd.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from mapcore.commands import keys as keymaps
from mapcore.commands.keys import MODIFIERS, split_key

__all__ = ["MODIFIERS", "split_key"]   # kept here too, for the shells and tools that read them from here

REGISTRY_FILE = Path(__file__).resolve().parent / "registry.yaml"
ALL_PLATFORMS = ("desktop", "web")
NAMED_KEYS = {"Up", "Down", "Left", "Right", "Page Up", "Page Down", "Home", "End", "Space", "Enter",
              "Backspace", "Delete", "Escape", "Tab", "Insert", "Caps Lock", *(f"F{i}" for i in range(1, 13))}


@dataclass(frozen=True)
class Command:
    name: str
    label: str
    region: str
    menu: str
    platforms: tuple[str, ...]
    latest_only: bool = False
    pointer: bool = False
    held: bool = False
    toggle: bool = False


def key_text(key: str, system: str = "windows") -> str:
    """A key as it is said and shown: a symbol becomes a word, so a screen reader
    that does not say punctuation still says it: "Ctrl+," is "Ctrl+Comma" (PO
    feedback on checklist 2, second pass). Any symbol works: one not in the
    templates is named from its Unicode name. On a Mac the modifiers have the
    Mac's names: "Shift+Cmd+F" is "Shift+Command+F", "Alt+Left" is "Option+Left"."""
    if not key:
        return key
    from mapcore.describe import templates

    mods, base = split_key(key)
    if system == "mac":
        names = templates().get("mac_modifiers", {})
        mods = [names.get(m, m) for m in mods]
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


def panel_groups() -> list[str]:
    """The Information panel's groups, by id, in order."""
    return list(_raw()["panel_groups"])


def _entries() -> list[dict]:
    """The registry's commands, with an each_panel_group entry made into one command for each
    panel group: panel.within, panel.nearby, and so on. Their keys are in the key maps."""
    from mapcore.describe import say

    out = []
    for c in _raw()["commands"]:
        if not c.get("each_panel_group"):
            out.append(c)
            continue
        for group in panel_groups():
            out.append({**c, "name": f"panel.{group}", "label": c["label"].format(group=say(f"panel.{group}"))})
    return out


@lru_cache(maxsize=1)
def load() -> tuple[Command, ...]:
    return tuple(
        Command(
            name=c["name"], label=c["label"], region=c.get("region", "map"),
            menu=c.get("menu") or "", platforms=tuple(c.get("platforms") or ALL_PLATFORMS),
            latest_only=bool(c.get("latest_only")), pointer=bool(c.get("pointer")),
            held=bool(c.get("held")), toggle=bool(c.get("toggle")),
        )
        for c in _entries()
    )


def by_name(name: str) -> Command:
    for c in load():
        if c.name == name:
            return c
    raise KeyError(name)


def for_platform(platform: str) -> list[Command]:
    return [c for c in load() if platform in c.platforms]


def default_keys(platform: str) -> dict[str, str]:
    """The keys of the platform's Windows key map, by command name: the keys when no others are given."""
    return keymaps.resolve(None, platform, "windows")


def default_key(name: str, platform: str = "desktop") -> str:
    """One command's key in the platform's Windows key map, or "" for none."""
    return default_keys(platform).get(name, "")


def _keys(platform: str, keys: dict | None) -> dict[str, str]:
    return {**default_keys(platform), **keys} if keys else default_keys(platform)


def key_of(command: Command, keys: dict[str, str]) -> str:
    """The command's key in the keys in use, or "" for none."""
    return keys.get(command.name, "")


def keymap(platform: str, keys: dict | None = None) -> dict[str, dict[str, str]]:
    """{region: {key: command name}} for one platform."""
    keys = _keys(platform, keys)
    out: dict[str, dict[str, str]] = {"map": {}, "panel": {}, "details": {}, "global": {}}
    for c in for_platform(platform):
        key = key_of(c, keys)
        if key:
            out.setdefault(c.region, {})[key] = c.name
    return out


def command_for_key(platform: str, key: str, region: str = "map", keys: dict | None = None) -> Command | None:
    """The command a key runs when the given region has focus: the region's own
    keys (the map's, or the Information panel's), then the keys that work anywhere."""
    keys = _keys(platform, keys)
    found = [c for c in for_platform(platform) if key_of(c, keys) == key and c.region in (region, "global")]
    return next((c for c in found if c.region == region), found[0] if found else None)


def commands_for_key(platform: str, key: str, keys: dict | None = None) -> list[Command]:
    """Every command on a key, in any region: what the key describer lists."""
    keys = _keys(platform, keys)
    return [c for c in for_platform(platform) if key and key_of(c, keys) == key]


def clash(platform: str, command: str, key: str, keys: dict | None = None) -> Command | None:
    """The other command that already has this key where they would meet, or
    None. A global key meets every command; a map key meets map and global ones."""
    keys = _keys(platform, keys)
    mine = by_name(command)
    for c in for_platform(platform):
        if c.name == command or key_of(c, keys) != key:
            continue
        if mine.region == "global" or c.region == "global" or mine.region == c.region:
            return c
    return None


def menus(platform: str, keys: dict | None = None, system: str = "windows") -> list[dict]:
    """The menu bar: [{label, access, items: [{name, label, key, key_text, toggle}]}], in registry order."""
    keys = _keys(platform, keys)
    out = []
    for menu in _raw()["menus"]:
        items = [{"name": c.name, "label": c.label, "key": key_of(c, keys),
                  "key_text": key_text(key_of(c, keys), system), "toggle": c.toggle}
                 for c in for_platform(platform) if c.menu == menu["label"]]
        if items:
            out.append({"label": menu["label"], "access": menu.get("access", ""), "items": items})
    return out


def latest_only(platform: str) -> list[str]:
    return [c.name for c in for_platform(platform) if c.latest_only]


def held_keys(platform: str) -> list[str]:
    return [c.name for c in for_platform(platform) if c.held]


def describe(platform: str, keys: dict | None = None, system: str = "windows") -> dict:
    """Everything a shell needs from the command list and the keys in use, as plain data."""
    return {"keymap": keymap(platform, keys), "menus": menus(platform, keys, system),
            "latest_only": latest_only(platform), "held": held_keys(platform)}
