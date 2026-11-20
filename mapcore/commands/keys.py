"""The key maps and your keys (P3-T31a, AD-3).

The command list (registry.yaml) holds the commands; the key maps hold their keys. There are five
key maps, each a file in keymaps/, read when TobyMap starts: Windows desktop, Mac desktop, Windows
browser, Mac browser and Alternative. A key map may be based on another and list only the keys that
differ:

* In a Windows key map the keys are as pressed.
* A Mac key map based on a Windows one turns Ctrl into Cmd in every key it takes from it, so most
  keys are written once for both systems. Its own keys are as pressed on a Mac: Ctrl is the Control
  key, Alt is Option and Cmd is Command.
* Alternative is based on the key map for your system and version, and replaces only the keys there
  that use Ctrl+Alt with a letter or a number (AltGr on many keyboards), or a punctuation key.

Your keys are the keys you changed, kept as changes on top of the key map you chose, never as a full
copy, so a key added in a new version still reaches you. A key file is your keys with the name of the
key map they are based on.

Versions are named as the session names them: "desktop" and "web". The key map files say "browser".
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml

KEYMAP_DIR = Path(__file__).resolve().parent / "keymaps"
WINDOWS_DESKTOP, MAC_DESKTOP = "windows-desktop", "mac-desktop"
WINDOWS_BROWSER, MAC_BROWSER = "windows-browser", "mac-browser"
ALTERNATIVE = "alternative"
KEYMAPS = (WINDOWS_DESKTOP, MAC_DESKTOP, WINDOWS_BROWSER, MAC_BROWSER, ALTERNATIVE)
SYSTEMS = ("windows", "mac")
VERSIONS = ("desktop", "web")
# The key map for each system and version, picked when TobyMap first starts.
_DEFAULTS = {("windows", "desktop"): WINDOWS_DESKTOP, ("mac", "desktop"): MAC_DESKTOP,
             ("windows", "web"): WINDOWS_BROWSER, ("mac", "web"): MAC_BROWSER}
KEY_FILE_KIND = "TobyMap key file"
KEY_FILE_FORMAT = 1


def _system(system: str | None) -> str:
    return system if system in SYSTEMS else "windows"


@lru_cache(maxsize=None)
def _file(name: str) -> dict:
    if name not in KEYMAPS:
        raise KeyError(name)
    data = yaml.safe_load((KEYMAP_DIR / f"{name}.yaml").read_text(encoding="utf-8")) or {}
    data["keys"] = {str(k): str(v or "") for k, v in (data.get("keys") or {}).items()}
    return data


def own_keys(name: str) -> dict[str, str]:
    """The keys written in one key map file, without those of the key map it is based on."""
    return dict(_file(name)["keys"])


def default_keymap(system: str, version: str, layout: str | None = None) -> str:
    """The key map TobyMap picks for your system and version when it first starts.

    This is where the keyboard layout fits later (P3-T31): the desktop can ask Windows or macOS for it,
    and Chrome and Edge can tell the page, but Firefox and Safari cannot. A layout where Ctrl+Alt with a
    letter types a character would pick Alternative. Detection is not made yet, so the layout is not used."""
    del layout   # the place for detecting the keyboard layout; nothing detects it yet
    return _DEFAULTS[(_system(system), version if version in VERSIONS else "desktop")]


def for_version(name: str | None, version: str, system: str) -> str:
    """The key map to use in this version: the one chosen, or its own version's (a key file made in the
    other version is based on that version's key map), or the default for an unknown name."""
    if name == ALTERNATIVE:
        return name
    if name in KEYMAPS:
        return _DEFAULTS[(_file(name)["system"], version if version in VERSIONS else "desktop")]
    return default_keymap(system, version)


def choices(version: str) -> list[str]:
    """The key maps that can be chosen in this version: Windows, Mac and Alternative."""
    return [k for k in KEYMAPS if k == ALTERNATIVE or _file(k)["version"] == ("browser" if version == "web" else "desktop")]


def split_key(key: str) -> tuple[list[str], str]:
    """"Ctrl+Shift+Page Up" as (["Ctrl", "Shift"], "Page Up"); "Ctrl++" is (["Ctrl"], "+")."""
    if key.endswith("+") and (len(key) == 1 or key[-2] == "+"):
        mods = key[:-2].split("+") if len(key) > 1 else []
        return [m for m in mods if m], "+"
    parts = key.split("+")
    return parts[:-1], parts[-1]


MODIFIERS = ("Ctrl", "Alt", "Shift", "Cmd")


def join_key(mods, base: str) -> str:
    return "+".join([m for m in MODIFIERS if m in mods] + [base])


def to_mac(key: str) -> str:
    """A Windows key on a Mac: Ctrl becomes Cmd, as in Visual Studio Code. "Ctrl+Shift+F" is "Shift+Cmd+F"."""
    if not key:
        return key
    mods, base = split_key(key)
    return join_key(["Cmd" if m == "Ctrl" else m for m in mods], base)


def needs_alternative(key: str) -> bool:
    """True for a key the Alternative key map replaces: Ctrl+Alt with a letter or a number, which is
    AltGr on many keyboards, or a punctuation key, which moves between keyboard layouts. Shift with a
    number is found by the key's place, so it stays."""
    if not key:
        return False
    mods, base = split_key(key)
    if len(base) != 1:
        return False
    return not base.isalnum() or ("Ctrl" in mods and "Alt" in mods)


@lru_cache(maxsize=None)
def _resolved(name: str) -> dict[str, str]:
    """A Windows or Mac key map's keys, with those of the key map it is based on."""
    data = _file(name)
    keys: dict[str, str] = {}
    if data.get("based_on"):
        base = _resolved(data["based_on"])
        if data["system"] == "mac" and _file(data["based_on"])["system"] != "mac":
            base = {c: to_mac(k) for c, k in base.items()}
        keys.update(base)
    keys.update(data["keys"])
    return keys


@lru_cache(maxsize=None)
def _resolved_for(name: str, version: str, system: str) -> dict[str, str]:
    name = for_version(name, version, system)
    if name != ALTERNATIVE:
        return _resolved(name)
    keys = dict(_resolved_for(default_keymap(system, version), version, system))
    for command, key in own_keys(ALTERNATIVE).items():
        if needs_alternative(keys.get(command, "")):
            keys[command] = to_mac(key) if system == "mac" else key
    return keys


def resolve(name: str | None, version: str, system: str = "windows") -> dict[str, str]:
    """The key map's keys, by command name, for this version on this system: a command with no key has
    none here. name None, or one not known, is the default key map for the system and version."""
    return dict(_resolved_for(name if name in KEYMAPS else None, version, _system(system)))


def keys_in_use(name: str | None, version: str, system: str, yours: dict | None) -> dict[str, str]:
    """The keys a shell uses: the chosen key map's, with your keys on top. Every command in the key map
    is in it, with "" for a key you took away."""
    keys = resolve(name, version, system)
    keys.update({str(c): str(k or "") for c, k in (yours or {}).items()})
    return keys


def only_changes(name: str | None, version: str, system: str, yours: dict | None) -> dict[str, str]:
    """Your keys with any that are the key map's own left out: what is kept, never a full copy."""
    base = resolve(name, version, system)
    return {c: k for c, k in (yours or {}).items() if base.get(c, "") != k}


def key_file_text(name: str, yours: dict | None) -> str:
    """A key file: your keys with the key map they are based on, as text to save (P3-T31b)."""
    return json.dumps({"kind": KEY_FILE_KIND, "format": KEY_FILE_FORMAT, "based_on": name,
                       "keys": dict(sorted((yours or {}).items()))}, indent=2, ensure_ascii=False) + "\n"


def read_key_file(text: str) -> tuple[str, dict[str, str]]:
    """The key map and your keys from a key file's text. ValueError if it is not a key file, names a key
    map that is not known, or holds a key TobyMap cannot use."""
    from mapcore.commands.registry import valid_key

    try:
        data = json.loads(text)
    except (TypeError, ValueError) as e:
        raise ValueError("not a key file") from e
    if not isinstance(data, dict) or data.get("kind") != KEY_FILE_KIND or not isinstance(data.get("keys"), dict):
        raise ValueError("not a key file")
    name = data.get("based_on")
    if name not in KEYMAPS:
        raise ValueError(f"no key map {name!r}")
    keys = {}
    for command, key in data["keys"].items():
        if not isinstance(command, str) or not isinstance(key, str) or (key and not valid_key(key)):
            raise ValueError(f"not a key: {key!r}")
        keys[command] = key
    return name, keys
