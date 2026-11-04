"""Acceptance scripts (architecture 11.3): small files of key presses and the expected announcements.

Each script in tests/acceptance/scripts is run by tests/acceptance/test_scripts.py as an
automatic test, and tools/make_checklists.py turns the same files into the PO's
checklist, docs/checklists/phase-1.md. The expected words are the approved wording.

A step is one of:

* press: a key name, as the registry spells it (the region is the map);
* run: a command name, with args: its arguments;

and says what must follow:

* say: the exact announcements, in order ([] means nothing is spoken);
* earcons: the earcons that play, in order;
* lon: the longitude afterwards, to 3 decimal places;
* panel_has: labels that must be in the Information panel's Nearby group.
"""
from __future__ import annotations

from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent / "scripts"


def load_all() -> list[tuple[str, dict]]:
    return [(p.stem, yaml.safe_load(p.read_text(encoding="utf-8"))) for p in sorted(SCRIPTS.glob("*.yaml"))]


def spoken(response) -> list[str]:
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


def run_script(script: dict, packs: dict[str, Path]):
    """Run a script and return a list of problems, empty when it passes."""
    from mapcore.session import MapSession

    pack = packs.get(script["pack"])
    if pack is None:
        raise FileNotFoundError(script["pack"])
    session = MapSession(packs=[pack], saved_state=dict(script["start"]))
    session.start()
    problems = []
    for n, step in enumerate(script["steps"], 1):
        if "press" in step:
            response = session.press(step["press"])
            what = f"press {step['press']}"
        elif "run" in step:
            response = session.run(step["run"], **step.get("args", {}))
            what = f"run {step['run']}"
        else:
            response, what = None, "check"
        if response is not None:
            if "say" in step and spoken(response) != step["say"]:
                problems.append(f"step {n} ({what}): said {spoken(response)}, wanted {step['say']}")
            if "earcons" in step and response.earcons != step["earcons"]:
                problems.append(f"step {n} ({what}): earcons {response.earcons}, wanted {step['earcons']}")
        if "lon" in step and abs(session.world.lon - step["lon"]) > 0.001:
            problems.append(f"step {n} ({what}): longitude {session.world.lon:.4f}, wanted {step['lon']}")
        if "panel_has" in step:
            labels = [i["label"] for g in session.panel() if g["id"] == "nearby" for i in g["items"]]
            for want in step["panel_has"]:
                if want not in labels:
                    problems.append(f"step {n} ({what}): Nearby has {labels}, wanted {want!r}")
    return problems
