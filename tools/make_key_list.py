"""Make docs/design/keymap.csv from the command list and the key maps (P3-T31c, ACC-3, ACC-4).

One line for every command. The four key columns hold the command's key in each key map that TobyMap
starts with: Windows desktop, Mac desktop, Windows browser and Mac browser, read with the same functions
the shells use (mapcore/commands/keys.py). The Variations column names the common keyboard layouts
(tools/data/keyboard_layouts.yaml) where that key is a problem, and the Notes column says why and which
key the Alternative key map uses. A test (tests/tools/test_keymap_csv.py) fails if the file is out of date.

The end of each line is CRLF and there is no BOM, as in the discussion points file.

Usage: python tools/make_key_list.py [--check]
Without --check the file is written; with it nothing is written, and the exit code is 1 when the file
is out of date.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
REGISTRY = REPO / "mapcore" / "commands" / "registry.yaml"
LAYOUTS = REPO / "tools" / "data" / "keyboard_layouts.yaml"
OUT = REPO / "docs" / "design" / "keymap.csv"

COLUMNS = ["Command", "Where it works", "Windows desktop", "Mac desktop", "Windows browser", "Mac browser",
           "Variations", "Notes on the variations"]
# Each key map column: its name in the key map files, the version and the system as the session names them.
KEY_COLUMNS = [("Windows desktop", "windows-desktop", "desktop", "windows"),
               ("Mac desktop", "mac-desktop", "desktop", "mac"),
               ("Windows browser", "windows-browser", "web", "windows"),
               ("Mac browser", "mac-browser", "web", "mac")]
# The information panel's groups: the key map holds one key for each, the command list one command for all.
GROUPS = [("within", "Within"), ("nearby", "Nearby"), ("bordering", "Bordering"), ("contains", "Contains"),
          ("overlapping", "Overlapping"), ("crossed", "Passed over"), ("search", "Search")]
CHARACTER_NAMES = {",": "comma", ".": "full stop", "/": "slash", "\\": "backslash", "[": "left bracket",
                   "]": "right bracket", "-": "minus", "=": "equals", "+": "plus", ";": "semicolon",
                   ":": "colon", "'": "apostrophe", '"': "quotation mark", "`": "grave accent",
                   "~": "tilde", "^": "caret"}
HOW = {"shift": "needs Shift", "altgr": "needs AltGr", "dead": "is a dead key, which waits for the next letter",
       "none": "is not on the keyboard"}
NO_KEY, NOT_HERE = "No key", "Not in this version"


def where(region: str) -> str:
    return {"map": "the map", "panel": "the Information panel"}.get(region, "anywhere")


def layouts() -> list[dict]:
    return yaml.safe_load(LAYOUTS.read_text(encoding="utf-8"))["layouts"]


def problems(key: str, system: str, layout: dict) -> list[str]:
    """Why this key, in a key map for this system, is a problem on this keyboard layout: sentences, or none."""
    from mapcore.commands import keys as keymaps

    if not key:
        return []
    mods, base = keymaps.split_key(key)
    if len(base) != 1:
        return []
    out = []
    unsure = " (unsure)" if layout.get("unsure") else ""
    if system == "windows" and layout["system"] == "windows" and "Ctrl" in mods and "Alt" in mods:
        table = layout["altgr_digits"] if base.isdigit() else layout["altgr_letters"]
        if base.upper() in table:
            out.append(f"{key} is AltGr+{base.upper()}, which types {table[base.upper()]}{unsure}.")
    if system == "mac" and layout.get("option_types_characters") and "Alt" in mods:
        out.append(f"Option with {CHARACTER_NAMES.get(base, base)} types a character on a Mac.")
    if not base.isalnum() and layout["system"] == "windows" and base in layout["punctuation"]:
        name = CHARACTER_NAMES.get(base, base)
        out.append(f"The {name} key {HOW[layout['punctuation'][base]]}, so {key} is hard to press there{unsure}.")
    return out


def key_rows() -> list[tuple[str, str, dict[str, str], str]]:
    """Each command as (label, where it works, key by column, name), in the command list's order."""
    from mapcore.commands import keys as keymaps

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    resolved = {col: keymaps.resolve(name, version, system) for col, name, version, system in KEY_COLUMNS}
    commands = []
    for c in registry["commands"]:
        if c["name"] == "panel.group":
            for short, label in GROUPS:
                commands.append((f"Go to {label}", where(c["region"]), f"panel.{short}", None))
        else:
            commands.append((c["label"], where(c["region"]), c["name"], c.get("platforms")))
    out = []
    for label, place, name, platforms in commands:
        keys = {}
        for col, _n, version, _s in KEY_COLUMNS:
            if platforms and version not in platforms:
                keys[col] = NOT_HERE
            else:
                keys[col] = resolved[col].get(name, "") or NO_KEY
        out.append((label, place, keys, name))
    return out


def alternative_hint(name: str, problem_columns: list[str]) -> str:
    """The key the Alternative key map uses for this command, in the columns that had a problem."""
    from mapcore.commands import keys as keymaps

    by_key: dict[str, list[str]] = {}
    for col, _n, version, system in KEY_COLUMNS:
        if col not in problem_columns:
            continue
        key = keymaps.resolve(keymaps.ALTERNATIVE, version, system).get(name, "")
        if key:
            by_key.setdefault(key, []).append(col)
    parts = [f"{' and '.join(cols)}: {key}" for key, cols in by_key.items()]
    return "Use the Alternative key map, which has " + "; ".join(parts) + "." if parts else ""


def rows() -> list[list[str]]:
    all_layouts = layouts()
    out = []
    for label, place, keys, name in key_rows():
        found: dict[str, list[str]] = {}
        problem_columns = []
        for col, _n, _v, system in KEY_COLUMNS:
            key = keys[col]
            if key in (NO_KEY, NOT_HERE):
                continue
            for layout in all_layouts:
                for why in problems(key, system, layout):
                    if why not in found.setdefault(layout["name"], []):
                        found[layout["name"]].append(why)
                    if col not in problem_columns:
                        problem_columns.append(col)
        variations = "; ".join(found) if found else "None known"
        notes = " ".join(f"{lay}: {' '.join(whys)}" for lay, whys in found.items())
        if found:
            notes = " ".join(x for x in (notes, alternative_hint(name, problem_columns)) if x)
        out.append([label, place] + [keys[col] for col, *_ in KEY_COLUMNS] + [variations, notes or "No problem known."])
    return out


def csv_text() -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    writer.writerows(rows())
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Make docs/design/keymap.csv from the key maps.")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if the file is out of date")
    args = parser.parse_args()
    text = csv_text()
    if args.check:
        current = OUT.read_bytes().decode("utf-8") if OUT.is_file() else None
        if current != text:
            print(f"{OUT} is out of date. Run tools/make_key_list.py to make it again.")
            return 1
        print(f"{OUT} is up to date.")
        return 0
    OUT.write_bytes(text.encode("utf-8"))
    print(f"Wrote {len(rows())} commands to {OUT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
