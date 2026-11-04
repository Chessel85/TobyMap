"""The listening test's trials, answers and results file (P1-T13, SON-1, SON-9).

No sound and no window here, so it is tested without either. A trial plays one
sound from a direction (a clock hour, 1 to 12) and a distance level (1 very near
to 5 beyond the view). The listener types the hour, Enter, then the distance, Enter.
0 for the hour means "can't tell".
"""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Distance levels as a fraction of the hearing range (SON-9): 5 is beyond the view.
LEVEL_FRACTION = {1: 0.04, 2: 0.15, 3: 0.4, 4: 0.9, 5: 1.5}
LEVEL_WORDS = {1: "very near", 2: "near", 3: "middle", 4: "far, near the edge", 5: "beyond the view"}
HOUR_BEARING = {h: (h % 12) * 30 for h in range(1, 13)}   # 12 o'clock is ahead

BLOCKS = [
    {"id": 1, "key": "stereo", "mode": "stereo", "trials": 12, "kind": "static",
     "words": "Block 1 of 5: stereo with a lower pitch behind, the speakers mode. Each time, press Space to hear a sound. "
              "Type the clock hour it came from, 1 to 12, with 12 straight ahead, then press Enter. Type 0 if you can't tell. "
              "Then type how far away it was, from 1, very near, to 5, beyond the view, and press Enter. R plays it again."},
    {"id": 2, "key": "hrtf_pitch", "mode": "hrtf_pitch", "trials": 12, "kind": "static",
     "words": "Block 2 of 5: head-related sound with a lower pitch behind, best on headphones. Same as before: Space to hear, "
              "the clock hour then Enter, then the distance from 1 to 5 then Enter."},
    {"id": 3, "key": "beyond", "mode": "stereo", "trials": 10, "kind": "beyond",
     "words": "Block 3 of 5: sounds beyond the view. Some are quiet and muffled, some are a fixed tone. Press Space to hear one. "
              "Type the hour and Enter, then the distance 1 to 5 and Enter. Distance 5 means beyond the view."},
    {"id": 4, "key": "moving", "mode": "stereo", "trials": 6, "kind": "moving",
     "words": "Block 4 of 5: a sound heard while you step past it. Press Space. Type the clock hour where the sound ended, "
              "and Enter, then its distance and Enter."},
    {"id": 5, "key": "labels", "mode": "stereo", "trials": 6, "kind": "labels",
     "words": "Block 5 of 5: spoken labels from behind. Press Space. Type the clock hour and Enter, then the distance and Enter. "
              "Some have no pitch change, some a lower pitch, some a short tone before the label."},
]
LABEL_STYLES = ("plain", "lower", "tone")
BEYOND_STYLES = ("muffled", "tone")


@dataclass
class Trial:
    block: int
    number: int
    kind: str
    bearing: float            # the bearing played (where it ended, for a moving sound)
    level: int
    start_bearing: float | None = None
    style: str = ""
    heard_hour: int | None = None
    heard_level: int | None = None
    plays: int = 1

    @property
    def fraction(self) -> float:
        return LEVEL_FRACTION[self.level]

    @property
    def hour(self) -> int:
        return round(self.bearing / 30) % 12 or 12


def make_trials(block: dict, seed: int) -> list[Trial]:
    """The trials of a block: directions and distances spread evenly and mixed, the same for the same seed."""
    rng = random.Random(seed * 10 + block["id"])
    n = block["trials"]
    hours = [(i % 12) + 1 for i in range(n)]
    rng.shuffle(hours)
    levels = [(i % 4) + 1 for i in range(n)]       # levels 1 to 4 in turn
    rng.shuffle(levels)
    trials = []
    for i in range(n):
        level = levels[i]
        style = ""
        start = None
        if block["kind"] == "beyond":
            level = 5 if i % 2 == 0 else level   # half are beyond the view
            style = BEYOND_STYLES[(i // 2) % 2] if level == 5 else ""
        elif block["kind"] == "labels":
            style = LABEL_STYLES[i % 3]
            hours[i] = rng.choice([5, 6, 7])            # from behind
        elif block["kind"] == "moving":
            start = HOUR_BEARING[hours[i]] + rng.choice([-120, 120])
        trials.append(Trial(block["id"], i + 1, block["kind"], float(HOUR_BEARING[hours[i]]), level,
                            start_bearing=None if start is None else float(start % 360), style=style))
    return trials


def parse_hour(text: str) -> int | None:
    """The hour typed: 0 to 12, or None if it is not one."""
    text = text.strip()
    if text.isdigit() and 0 <= int(text) <= 12:
        return int(text)
    return None


def parse_level(text: str) -> int | None:
    text = text.strip()
    if text.isdigit() and 1 <= int(text) <= 5:
        return int(text)
    return None


COLUMNS = ["participant", "date", "block", "block_name", "trial", "kind", "style", "mode", "played_hour",
           "played_bearing", "start_bearing", "played_level", "played_fraction", "heard_hour", "heard_bearing",
           "heard_level", "plays"]


@dataclass
class Results:
    participant: str
    folder: Path
    rows: list[dict] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return self.folder / f"{self.participant}-{date.today().isoformat()}.csv"

    def add(self, trial: Trial, mode: str, block_name: str) -> None:
        heard_bearing = "" if trial.heard_hour in (None, 0) else HOUR_BEARING[trial.heard_hour]
        self.rows.append({
            "participant": self.participant, "date": date.today().isoformat(), "block": trial.block,
            "block_name": block_name, "trial": trial.number, "kind": trial.kind, "style": trial.style, "mode": mode,
            "played_hour": trial.hour, "played_bearing": trial.bearing,
            "start_bearing": "" if trial.start_bearing is None else trial.start_bearing,
            "played_level": trial.level, "played_fraction": trial.fraction,
            "heard_hour": "" if trial.heard_hour is None else trial.heard_hour, "heard_bearing": heard_bearing,
            "heard_level": "" if trial.heard_level is None else trial.heard_level, "plays": trial.plays,
        })
        self.write()

    def write(self) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, COLUMNS, lineterminator="\r\n")
            writer.writeheader()
            writer.writerows(self.rows)
        return self.path


def read_results(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
