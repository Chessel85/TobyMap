"""Make the PO's acceptance checklist from the acceptance scripts (architecture 11.3, P1-T7).

    .venv\\Scripts\\python.exe tools\\make_checklists.py

Writes docs/checklists/phase-1.md: real headings, one numbered list per
script, no tables. The expected words are those in tests/acceptance/scripts,
which are the approved wording; tests check them on every push.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.acceptance import runner  # noqa: E402

OUT = ROOT / "docs" / "checklists" / "phase-1.md"

INTRO = """# Phase 1 acceptance checklist

This checklist is made by tools/make_checklists.py from the acceptance scripts in tests/acceptance/scripts, so the words below are the words the automatic tests check. If you change any wording, tell me, and it goes back into the templates and the scripts.

For each part, do the steps in order and say what you heard. Write your answers in a text file or in the discussion points file, with the part's number.
"""

MANUAL = [
    ("Installing and opening", ["DEL-5", "PLT-1", "PLT-3"], [
        "Install the desktop version with the installer, and start it. It says where you start, then 'Press F1 for keys'.",
        "Open the web version in Firefox. It says the same.",
    ]),
    ("Keys and regions", ["ACC-3", "ACC-7", "NAV-1"], [
        "Press F1 on the map. It lists the commands for the map with their keys.",
        "Press Shift+F1, then Up, Page Up and a key with no command. Each is described and nothing is carried out. Press Shift+F1 again.",
        "Press F2, F3 and F4 from each region. They go to the map, the Information panel and Details.",
        "Change the key of Heading to one that is free. Then try one that is taken. You are told which command has it.",
        "On the desktop, press Alt to reach the menu bar, Tab along its menus, and Alt or Escape to leave. On the web, Ctrl+Alt+M reaches the menu bar.",
    ]),
    ("Held keys", ["ANN-3"], [
        "Hold the Right arrow for two seconds and let go. Only the last place is spoken, and it interrupts anything still being said.",
    ]),
    ("The Information panel", ["INF-10"], [
        "Press F3. NVDA says the item and its level, and reads the item without pressing Up then Down.",
    ]),
    ("Settings and sound", ["PLT-5", "SON-7", "SON-8"], [
        "Open Settings with Ctrl+comma. It has OK and Cancel buttons. Change the units, close TobyMap, open it again. Your settings and place are back.",
        "Press Ctrl+M to mute, move, and press it again. The tick and blocked sounds stop and come back.",
        "Open Help, then The sounds. The earcons and their file names are listed.",
    ]),
    ("Braille", ["ACC-1"], [
        "Read the announcements on your Braille display or in NVDA's Braille viewer.",
    ]),
    ("Listening test", ["SON-1", "SON-9"], [
        "Run the full listening test (tools/listening_test) and send me the results file.",
    ]),
]


def describe_step(step: dict) -> str:
    if "press" in step:
        what = f"Press {step['press']}."
    elif "run" in step:
        what = f"Choose the command {step['run']}" + (f" with {step['args']}." if step.get("args") else ".")
    else:
        what = "Open the Information panel."
    if "say" in step:
        what += " Nothing is spoken." if not step["say"] else " You hear: " + "; then ".join(f'"{t}"' for t in step["say"]) + "."
    if step.get("earcons"):
        what += " You hear the " + " and ".join(step["earcons"]) + " sound."
    elif "earcons" in step and not step["earcons"]:
        what += " No sound plays."
    if "panel_has" in step:
        what += " The Nearby group has: " + "; ".join(f'"{t}"' for t in step["panel_has"]) + "."
    return what


def build() -> str:
    parts = [INTRO]
    n = 0
    for _name, script in runner.load_all():
        n += 1
        parts.append(f"## Part {n}: {script['title']}\n")
        parts.append(f"Requirements: {', '.join(script['requirements'])}.\n")
        start = script["start"]
        parts.append(f"Start at latitude {start['lat']}, longitude {start['lon']}, with the zoom and step as given in the script file "
                     f"({'the world pack' if script['pack'] == 'world' else 'the test pack'}).\n")
        parts += [f"{i}. {describe_step(s)}" for i, s in enumerate(script["steps"], 1)]
        parts.append("")
    for title, reqs, steps in MANUAL:
        n += 1
        parts.append(f"## Part {n}: {title}\n")
        parts.append(f"Requirements: {', '.join(reqs)}.\n")
        parts += [f"{i}. {s}" for i, s in enumerate(steps, 1)]
        parts.append("")
    return "\n".join(parts)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
