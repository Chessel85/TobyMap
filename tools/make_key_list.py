"""Make a phase's key list from the command registry (P2-T0c, P3-T0c, DP109; ACC-3, ACC-4).

The file has one line for every command now in the registry and one for every
new command of the phase, so the product owner can write the key wanted in the
"Your key" column. Each proposed key is checked against the keys already in use
where they would meet, and against the keys screen readers and browsers keep
(tests/data/forbidden_keys.yaml); any clash is written in the Notes column.
It can be made again at any time. The end of each line is CRLF and there is no
BOM, as in the discussion points file.

Usage: python tools/make_key_list.py [--phase 2|3] [--force]
The phase is 3 unless given. A file that already holds the product owner's keys
is not changed without --force.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "mapcore" / "commands" / "registry.yaml"
FORBIDDEN = REPO / "tests" / "data" / "forbidden_keys.yaml"

COLUMNS = ["Command", "Where it works", "Phase", "Key now", "Key proposed", "Your key", "Notes"]

# New Phase 2 commands: (command, where, key proposed, note). Keys are from the user
# experience description, section 12, except where the note says they are new.
NEW_2 = [
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
PANEL_2 = [
    ("Panel group: Contains", "I"),
    ("Panel group: Bordering", "N"),
    ("Panel group: Overlapping", "O"),
    ("Panel group: Crossing", "X"),
    ("Panel group: Crossed and passed", "Shift+X"),
]

# New Phase 3 commands (docs/plan/phase-3-plan.md): (command, where, key proposed, note).
# Keys are from the user experience description, section 12, unless the note says otherwise.
NEW_3 = [
    ("Stepping mode", "the map", "1", "P3-T6. Goes back to stepping from hierarchy mode, without moving."),
    ("Hierarchy mode", "the map", "2", "P3-T6. In hierarchy mode, Up goes to the parent, Down lists what is inside, "
     "and Left and Right go to the neighbours, clockwise. No new keys for those."),
    ("Go to Contains", "anywhere", "Shift+4", "P3-T4. New groups go after the three you know, so Shift+1 to Shift+3 stay as they are (DP156)."),
    ("Go to Bordering", "anywhere", "Shift+5", "P3-T4."),
    ("Go to Overlapping", "anywhere", "Shift+6", "P3-T4."),
    ("Go to Crossing", "anywhere", "Shift+7", "P3-T4."),
    ("Go to Search", "anywhere", "Shift+8", "P3-T4. The search results, the world tree's lists and the query builder's answers."),
    ("Next sort order: name, distance, bearing", "the Information panel", "Ctrl+S", "P3-T4. Agreed in DP79."),
    ("Previous sort order", "the Information panel", "Ctrl+Shift+S",
     "P3-T4. New: Shift goes the other way round a list (P2-T17l)."),
    ("Bookmark the item", "the Information panel", "Ctrl+Enter",
     "Phase 4, from DP170. Until then it says that bookmarks come in Phase 4."),
    ("Measure to the item or the search result", "the map and the Information panel", "M",
     "P3-T7. You were not sure of this key (DP170); I ask again when P3-T7 is done."),
    ("Distance to a feature found by search, without moving", "the map", "Shift+M", "P3-T7, INF-8. New, proposed by me."),
    ("Search", "anywhere", "Ctrl+F", "P3-T8. In the web version, the page takes Ctrl+F from the browser's own find while TobyMap has focus; "
     "the browser tests check this in Chromium and Firefox."),
    ("World tree", "the map", "W", "P3-T9. The design had T, which is now Next theme; W for World. New, proposed by me."),
    ("Open the current feature's Wikipedia article", "anywhere", "Shift+W", "P3-T5. New, proposed by me; no key was set in the design."),
    ("List every feature of a kind in the current feature", "the map", "Ctrl+Shift+F",
     "P3-T9, SRB-4, such as every lake in Finland. New, proposed by me."),
    ("Query builder", "the map", "Q", "P3-T10."),
    ("Look around", "the map", "L", "P3-T11."),
    ("Pack manager", "the map", "P", "P3-T13. On the map only, so P still finds an item by its first letter in the panel."),
]

PHASES = {2: (NEW_2, PANEL_2), 3: (NEW_3, [])}
PLACES = {"the map": {"map"}, "the Information panel": {"panel"}, "anywhere": {"map", "panel", "global"},
          "the map and the Information panel": {"map", "panel"}}


def where(region: str) -> str:
    return {"map": "the map", "panel": "the Information panel"}.get(region, "anywhere")


def clash_notes(key: str, place: str, registry: dict, forbidden: dict) -> list[str]:
    """What the proposed key would clash with: a key already used where they meet,
    or a key a screen reader or browser keeps (ACC-4)."""
    notes = []
    regions = PLACES.get(place)
    if regions is not None:
        for c in registry["commands"]:
            if c.get("key") == key and (c["region"] == "global" or "global" in regions or c["region"] in regions):
                notes.append(f"Clash: {key} is already {c['label']}.")
    parts = key.split("+")
    if (key in forbidden["exact"] or key in forbidden["web_only"] or set(parts) & set(forbidden["no_modifier_words"])
            or (forbidden["digits_with_ctrl"] and parts[0] == "Ctrl" and parts[-1].isdigit())):
        notes.append(f"Clash: {key} belongs to the screen reader or the browser.")
    return notes


def rows(phase: int) -> list[list[str]]:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    forbidden = yaml.safe_load(FORBIDDEN.read_text(encoding="utf-8"))
    new, panel = PHASES[phase]
    earlier = "1" if phase == 2 else "earlier"
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
        if phase > 2:
            key = key.replace("{number}", "number")
        out.append([c["label"], where(c["region"]), earlier, key, key, "", " ".join(notes)])
    for label, place, key, note in new:
        notes = [note] + (clash_notes(key, place, registry, forbidden) if phase > 2 else [])
        out.append([label, place, str(phase), "", key, "", " ".join(notes)])
    for label, key in panel:
        out.append([label, "the Information panel", str(phase), "", "",
                    "", f"Proposed to be dropped (DP109). The key in the design is {key}. Write it in Your key to keep it."])
    return out


def has_your_keys(out: Path) -> bool:
    """True when the file already holds keys written by the product owner."""
    if not out.is_file():
        return False
    with out.open(encoding="utf-8-sig", newline="") as f:
        return any(r.get("Your key", "").strip() for r in csv.DictReader(f))


def main() -> int:
    phase = int(sys.argv[sys.argv.index("--phase") + 1]) if "--phase" in sys.argv else 3
    if phase not in PHASES:
        print(f"There is no key list for phase {phase}. Use --phase 2 or --phase 3.")
        return 1
    out = REPO / "docs" / "plan" / f"phase-{phase}-keys.csv"
    if has_your_keys(out) and "--force" not in sys.argv:
        print(f"{out} already holds your keys, so it was not changed. Use --force to make it again.")
        return 1
    data = rows(phase)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(COLUMNS)
        w.writerows(data)
    print(f"Wrote {len(data)} commands to {out}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
