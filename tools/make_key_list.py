"""Make docs/plan/phase-2-keys.csv from the command registry (P2-T0c, DP109; ACC-3, ACC-4).

The file has one line for every command now in the registry and one for every
new Phase 2 command, so the product owner can write the key wanted in the last
column. It can be made again at any time. The end of each line is CRLF and
there is no BOM, as in the discussion points file.

Usage: python tools/make_key_list.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "mapcore" / "commands" / "registry.yaml"
OUT = REPO / "docs" / "plan" / "phase-2-keys.csv"

COLUMNS = ["Command", "Where it works", "Phase", "Key now", "Key proposed", "Your key", "Notes"]

# New Phase 2 commands: (command, where, key proposed, note). Keys are from the user
# experience description, section 12, except where the note says they are new.
NEW = [
    ("Cycle the orientation: north-fixed, cardinal facing, free facing", "the map", "F", "P2-T1"),
    ("Turn 90 degrees left", "the map", "Shift+Left", "P2-T1"),
    ("Turn 90 degrees right", "the map", "Shift+Right", "P2-T1"),
    ("Fine turn left, in free facing", "the map", "Ctrl+Left", "P2-T1"),
    ("Fine turn right, in free facing", "the map", "Ctrl+Right", "P2-T1"),
    ("Type a bearing", "the map", "A", "P2-T1"),
    ("Go to coordinates", "the map", "G", "P2-T2"),
    ("Back through the location history", "the map", "Backspace", "P2-T2"),
    ("Forward through the location history", "the map", "Shift+Backspace", "P2-T2"),
    ("Go to a place in the location history", "the location history", "Enter", "P2-T15, P2-T17t. In the location history."),
    ("Layers list", "anywhere", "Shift+L", "P2-T3"),
    ("Orientation beacon on or off", "the map", "B", "P2-T9"),
    ("Hear its direction", "the Information panel", "Ctrl+Enter", "DP143, P2-T7. On Nearby and Crossed and passed items."),
    ("Isolate the current feature, and again to show everything", "the map", "Ctrl+I", "P2-T12. New, proposed by me; no key was set in the design."),
    ("Next verbosity preset", "anywhere", "Ctrl+Shift+V", "P2-T11. New, proposed by me; no key was set in the design."),
    ("Next theme", "anywhere", "Ctrl+Shift+T", "P2-T12. New, proposed by me; no key was set in the design."),
]

# Information panel group keys (DP109). Proposed to be dropped, so that you can keep any you want.
PANEL = [
    ("Panel group: Contains", "I"),
    ("Panel group: Bordering", "N"),
    ("Panel group: Overlapping", "O"),
    ("Panel group: Crossing", "X"),
    ("Panel group: Crossed and passed", "Shift+X"),
]


def where(region: str) -> str:
    return {"map": "the map", "panel": "the Information panel"}.get(region, "anywhere")


def rows() -> list[list[str]]:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    out = []
    for c in registry["commands"]:
        notes = []
        if c.get("pointer"):
            notes.append("Sent by the mouse, touch or a list; it has no key.")
        if c.get("platforms") and c["platforms"] != ["desktop", "web"]:
            notes.append("Only in the " + " and ".join(c["platforms"]) + " version.")
        if c.get("toggle"):
            notes.append("On or off.")
        key = c.get("key") or ""
        out.append([c["label"], where(c["region"]), "1", key, key, "", " ".join(notes)])
    for label, place, key, note in NEW:
        out.append([label, place, "2", "", key, "", note])
    for label, key in PANEL:
        out.append([label, "the Information panel", "2", "", "",
                    "", f"Proposed to be dropped (DP109). The key in the design is {key}. Write it in Your key to keep it."])
    return out


def has_your_keys() -> bool:
    """True when the file already holds keys written by the product owner."""
    if not OUT.is_file():
        return False
    with OUT.open(encoding="utf-8-sig", newline="") as f:
        return any(r.get("Your key", "").strip() for r in csv.DictReader(f))


def main() -> int:
    if has_your_keys() and "--force" not in sys.argv:
        print(f"{OUT} already holds your keys, so it was not changed. Use --force to make it again.")
        return 1
    data = rows()
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(COLUMNS)
        w.writerows(data)
    print(f"Wrote {len(data)} commands to {OUT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
