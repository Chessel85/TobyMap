r"""The listening test for sound in space and the voice (P2-T17u; SON-1, SON-2, SON-3, SON-9; DP164).

    .venv\Scripts\python.exe -m tools.listening_test.compass [--name NAME] [--rate PERCENT]
    .venv\Scripts\python.exe -m tools.listening_test.compass --analyse docs\spikes\listening-test\compass-*.csv

It runs in the command window, with no window of its own, on your own headphones. You face
north. Eight places, one at each of the eight compass points, are played with each sound
model in turn. Each is the item's direction sound followed by its name and distance in the
Alba voice, from the same place, as Hear its direction plays them in TobyMap. No echo
(DP164). You type the compass point you heard it from.

The sound models:

* now: stereo with a lower pitch behind, as TobyMap plays it now.
* hrtf: HRTF with a lower pitch behind, the other choice in Settings.
* lower: stereo with twice the lower pitch behind: the sound 6 semitones lower instead of
  3, the voice 3 instead of 1.5.
* muffled: stereo with more muffling behind: the cut-off behind is 0.3 of what it is in
  front, instead of 0.7.

Everything else is as TobyMap plays it: the core's sound scene places each sound
(mapcore/sound/scene.py), the desktop's spatial code makes it (desktop/audio/spatial.py),
and the voice is shaped by the core's time stretching. The places are 30 kilometres away
with the zoom at 100 kilometres, so they are clear but not at full loudness.

The names are only labels, and each block puts them at new compass points, so a name never
tells you its direction. Answers are written after each one into a CSV file in
docs/spikes/listening-test, and --analyse writes the findings there for you.

The flow, the sounds and the results file need no sound device, so the tests run them with
a stand-in voice and player (rule 5).
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "docs" / "spikes" / "listening-test"
ITEM_SOUND = ROOT / "sounds" / "item-direction.wav"

RANGE_M = 100_000.0           # the zoom, so the hearing range: 100 km
DISTANCE_M = 30_000.0         # each place is 30 km away
DISTANCE_TEXT = "30 kilometres"
MORE_MUFFLE = 0.3             # the "muffled" model's cut-off behind, as a share of the cut-off in front

POINTS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"]
SHORT = ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
NAMES = ["Berlin", "Lake Geneva", "Isle of Skye", "River Thames", "Kilimanjaro", "Saint Petersburg",
         "Bay of Biscay", "Southampton"]

MODELS = [
    {"key": "now", "words": "stereo with a lower pitch behind, as TobyMap plays it now"},
    {"key": "hrtf", "words": "HRTF with a lower pitch behind, the other choice in Settings, made for headphones"},
    {"key": "lower", "words": "stereo with twice the lower pitch behind"},
    {"key": "muffled", "words": "stereo with more muffling behind"},
]

COLUMNS = ["participant", "date", "time", "block", "model", "kind", "trial", "name", "played_point",
           "played_bearing", "heard_point", "heard_bearing", "plays", "rating", "voice_rate"]


def bearing_of(point: int) -> float:
    return point * 45.0


def parse_point(text: str) -> int | None:
    """The compass point typed, 0 to 7 from north clockwise; -1 for "can't tell"; None if not understood.

    Takes n, ne, north east, north-east, northeast and so on, in any case, and 0 or ? for can't tell."""
    t = text.strip().lower().replace("-", " ").replace("  ", " ")
    if t in ("0", "?"):
        return -1
    t = t.replace(" ", "")
    for i, (long, short) in enumerate(zip(POINTS, SHORT)):
        if t in (short, long.replace("-", "")):
            return i
    return None


def parse_rating(text: str) -> int | None:
    t = text.strip()
    return int(t) if t.isdigit() and 1 <= int(t) <= 5 else None


@dataclass
class Trial:
    block: int
    model: str
    number: int
    point: int
    name: str
    heard: int | None = None      # 0 to 7, or -1 for can't tell
    plays: int = 1

    @property
    def bearing(self) -> float:
        return bearing_of(self.point)

    @property
    def label(self) -> str:
        return f"{self.name}, {DISTANCE_TEXT}"


def make_trials(block: int, model: str, seed: int) -> list[Trial]:
    """The eight compass points in a mixed order, each with a name, both mixed afresh for each
    block, the same for the same seed."""
    rng = random.Random(seed * 100 + block)
    points = list(range(8))
    rng.shuffle(points)
    names = list(NAMES)
    rng.shuffle(names)
    return [Trial(block, model, i + 1, p, n) for i, (p, n) in enumerate(zip(points, names))]


# Making the sound: the core's sound scene, changed only where the model differs.

def placed_for(model: str, sound: str, bearing: float) -> dict:
    """The core's placing of a sound for this model, facing north."""
    from mapcore.sound import scene
    from mapcore.sound.curve import CurveSettings

    mode = "hrtf" if model == "hrtf" else "stereo"
    p = scene.place(sound, bearing, DISTANCE_M, 0.0, RANGE_M, CurveSettings(), mode).to_dict()
    if p["behind"]:
        if model == "lower":   # twice as many semitones lower
            p["pitch"] = (scene.VOICE_BEHIND_PITCH if sound == "voice" else scene.BEHIND_PITCH) ** 2
        elif model == "muffled":
            p["cutoff_hz"] *= MORE_MUFFLE / scene.BEHIND_MUFFLE
    return p


def render(trial: Trial, speaker: Callable[[str, float], np.ndarray], item_sound: np.ndarray,
           voice_rate: float = 1.0) -> np.ndarray:
    """The item's direction sound, then the label in the voice from the same place, as stereo samples.

    As in TobyMap (Session._hear and SpatialVoice): the voice starts when the sound ends, its
    lower pitch behind is made by time stretching at the same speed, and its speed above 100
    percent is shared between Piper and time stretching."""
    from desktop.audio import spatial
    from mapcore.sound.stretch import shape_voice, split_rate

    sound = spatial.placed(item_sound, placed_for(trial.model, "item_direction", trial.bearing))
    voice = placed_for(trial.model, "voice", trial.bearing)
    pitch, voice["pitch"] = voice["pitch"], 1.0
    piper, stretch = split_rate(voice_rate)
    mono = shape_voice(speaker(trial.label, piper), spatial.RATE, stretch, pitch)
    said = spatial.placed(mono, voice) if len(mono) else np.zeros((0, 2), np.float32)
    return np.concatenate([sound, said]).astype(np.float32)


# The results file.

class Results:
    def __init__(self, participant: str, folder: Path, voice_rate: int, when: datetime | None = None):
        self.participant = participant
        self.folder = Path(folder)
        self.voice_rate = voice_rate
        self.when = when or datetime.now()
        self.rows: list[dict] = []

    @property
    def path(self) -> Path:
        return self.folder / f"compass-{self.participant}-{self.when:%Y-%m-%d-%H%M}.csv"

    def _row(self, **values) -> dict:
        row = {c: "" for c in COLUMNS}
        row.update(participant=self.participant, date=self.when.date().isoformat(), time=f"{self.when:%H:%M}",
                   voice_rate=self.voice_rate)
        row.update(values)
        return row

    def add_trial(self, t: Trial) -> None:
        heard_point = "" if t.heard is None else ("can't tell" if t.heard < 0 else POINTS[t.heard])
        heard_bearing = "" if t.heard is None or t.heard < 0 else bearing_of(t.heard)
        self.rows.append(self._row(block=t.block, model=t.model, kind="direction", trial=t.number, name=t.name,
                                   played_point=POINTS[t.point], played_bearing=t.bearing,
                                   heard_point=heard_point, heard_bearing=heard_bearing, plays=t.plays))
        self.write()

    def add_rating(self, block: int, model: str, kind: str, rating: int) -> None:
        self.rows.append(self._row(block=block, model=model, kind=kind, rating=rating))
        self.write()

    def write(self) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, COLUMNS, lineterminator="\r\n")
            writer.writeheader()
            writer.writerows(self.rows)
        return self.path


# The test, in the command window.

class Stop(Exception):
    pass


class CompassTest:
    """The test's flow. ask(prompt) gives what was typed (EOFError stops); tell(text) shows text;
    play(samples) plays stereo samples. All three are the console's in a real run."""

    def __init__(self, results: Results, speaker, item_sound: np.ndarray, ask, tell, play,
                 hrtf: bool = True, seed: int = 1, voice_rate: float = 1.0):
        self.results = results
        self.speaker = speaker
        self.item_sound = item_sound
        self.ask, self.tell, self.play = ask, tell, play
        self.hrtf = hrtf
        self.seed = seed
        self.voice_rate = voice_rate

    def _ask(self, prompt: str) -> str:
        try:
            text = self.ask(prompt)
        except EOFError:
            raise Stop from None
        if text.strip().lower() in ("q", "quit"):
            raise Stop
        return text

    def _hear(self, trial: Trial) -> None:
        self.play(render(trial, self.speaker, self.item_sound, self.voice_rate))

    def run(self) -> Path:
        models = [m for m in MODELS if self.hrtf or m["key"] != "hrtf"]
        try:
            self.tell(f"The listening test for sound in space and the voice. Put your headphones on. You face north. "
                      f"There are {len(models)} blocks of 8, one block for each sound model. Each time you hear the "
                      f"item's direction sound, then a name and distance in the voice, from the same place. The names "
                      f"are only labels: they are not where those places really are. Type the compass point it came "
                      f"from, such as n, ne, e or south west, and press Enter. Type 0 if you can't tell, r to hear it "
                      f"again, or q to stop. Your answers are saved after each one.")
            if not self.hrtf:
                self.tell("The HRTF files are not on this computer, so the HRTF block is left out. "
                          "Run tools\\fetch_vendor.py to get them.")
            if self._ask("Type d and press Enter to hear all eight compass points in order first, as TobyMap plays "
                         "them now, or just press Enter to start. ").strip().lower() == "d":
                for i in range(8):
                    self.tell(POINTS[i])
                    self._hear(Trial(0, "now", i + 1, i, NAMES[i]))
                    self._ask("Press Enter for the next. ")
            for number, model in enumerate(models, start=1):
                self._block(number, len(models), model)
        except Stop:
            self.tell(f"Stopped. Your answers so far are in {self.results.write()}.")
            return self.results.path
        self.tell(f"The listening test is finished. Thank you. Your answers are in {self.results.write()}.")
        return self.results.path

    def _block(self, number: int, count: int, model: dict) -> None:
        self.tell(f"Block {number} of {count}: {model['words']}.")
        for trial in make_trials(number, model["key"], self.seed):
            self._ask(f"Sound {trial.number} of 8. Press Enter to hear it. ")
            self._hear(trial)
            while True:
                text = self._ask("Where did it come from? ")
                if text.strip().lower() == "r":
                    trial.plays += 1
                    self._hear(trial)
                    continue
                point = parse_point(text)
                if point is None:
                    self.tell("Type a compass point, such as n, ne or south west, or 0 if you can't tell, or r to hear it again.")
                    continue
                trial.heard = point
                break
            self.results.add_trial(trial)
        for kind, question in (("ease", "How easy was it to tell where the sounds came from in this block, from 1, "
                                        "very hard, to 5, very easy? "),
                               ("voice", "How clear and pleasant was the voice in this block, from 1 to 5? ")):
            while (rating := parse_rating(self._ask(question))) is None:
                self.tell("Type a number from 1 to 5.")
            self.results.add_rating(number, model["key"], kind, rating)


class ConsolePlayer:
    """Plays stereo samples on the default sound device with sounddevice, without waiting."""

    def __init__(self):
        import sounddevice

        self.sd = sounddevice

    def __call__(self, samples: np.ndarray) -> None:
        from desktop.audio.spatial import RATE

        peak = float(np.abs(samples).max()) if len(samples) else 0.0
        self.sd.stop()
        self.sd.play(samples / max(1.0, peak), RATE)


# The analysis.

def angle_difference(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def read_rows(paths) -> list[dict]:
    rows = []
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            rows += list(csv.DictReader(f))
    return rows


def analyse(rows: list[dict]) -> dict:
    """For each model: how many were right, within one point, front and back mixed up, and the ratings."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    ratings: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["kind"] == "direction":
            by_model[r["model"]].append(r)
        elif r["rating"]:
            ratings[r["model"]][r["kind"]].append(int(r["rating"]))
    out = {}
    for m in [m["key"] for m in MODELS]:
        rs = by_model.get(m, [])
        if not rs:
            continue
        answered = [r for r in rs if r["heard_bearing"] != ""]
        diff = [angle_difference(float(r["played_bearing"]), float(r["heard_bearing"])) for r in answered]
        # Front and back: only where neither the place nor the answer is due east or west.
        fb = [r for r in answered if float(r["played_bearing"]) % 180 != 90 and float(r["heard_bearing"]) % 180 != 90]
        flips = [math.cos(math.radians(float(r["played_bearing"]))) * math.cos(math.radians(float(r["heard_bearing"]))) < 0
                 for r in fb]
        behind = [r for r in answered if math.cos(math.radians(float(r["played_bearing"]))) < -1e-9]
        out[m] = {
            "trials": len(rs),
            "cant_tell": len(rs) - len(answered),
            "right": sum(d < 1 for d in diff) / len(rs),
            "within_one": sum(d <= 45 for d in diff) / len(rs),
            "front_back": (sum(flips) / len(flips)) if flips else None,
            "behind_heard_behind": (sum(math.cos(math.radians(float(r["heard_bearing"]))) < -1e-9 for r in behind)
                                    / len(behind)) if behind else None,
            "replays": sum(int(r["plays"]) - 1 for r in rs),
            "ease": ratings[m].get("ease", []),
            "voice": ratings[m].get("voice", []),
        }
    return out


def percent(x) -> str:
    return "no answers" if x is None else f"{round(100 * x)} percent"


def mean(xs) -> str:
    return "not given" if not xs else f"{sum(xs) / len(xs):.1f} out of 5"


def score(r: dict) -> tuple:
    return (r["within_one"], -(r["front_back"] or 0), r["right"])


def findings(results: dict, files: list[str]) -> str:
    words = {m["key"]: m["words"] for m in MODELS}
    lines = ["# Listening test for sound in space and the voice: findings", "",
             "P2-T17u, made by tools/listening_test/compass.py from: " + ", ".join(files) + ".", "",
             "Each sound model played the eight compass points once, facing north, each with the item's direction "
             "sound and then a name in the voice. Phase 1's target is 80 percent within one compass point.", ""]
    for m, r in results.items():
        lines += [f"## {m}: {words[m]}", "",
                  f"* Places: {r['trials']}. You could not tell {r['cant_tell']}, and asked to hear again "
                  f"{'once' if r['replays'] == 1 else str(r['replays']) + ' times'}.",
                  f"* The right compass point: {percent(r['right'])}.",
                  f"* Within one compass point: {percent(r['within_one'])}.",
                  f"* Front and back mixed up: {percent(r['front_back'])}.",
                  f"* Places behind you heard as behind: {percent(r['behind_heard_behind'])}.",
                  f"* How easy to tell where: {mean(r['ease'])}. The voice: {mean(r['voice'])}.", ""]
    lines += ["## What I propose", ""]
    if not results:
        lines.append("* There are no answers yet. Run the listening test, then this again.")
    else:
        best = max(results, key=lambda m: score(results[m]))
        now = results.get("now")

        def clearly_better(r: dict) -> bool:
            """With eight places a model, one answer either way is chance: a model must get at least two
            more within one point, or two more exactly right with no more mix-ups, and not be rated harder."""
            if now is None:
                return True
            more_within = (r["within_one"] - now["within_one"]) * r["trials"] >= 2 - 1e-9
            more_right = ((r["right"] - now["right"]) * r["trials"] >= 2 - 1e-9
                          and (r["front_back"] or 0) <= (now["front_back"] or 0))
            easier = not r["ease"] or not now["ease"] or sum(r["ease"]) / len(r["ease"]) >= sum(now["ease"]) / len(now["ease"])
            return (more_within or more_right) and easier

        if best == "now" or not clearly_better(results[best]):
            lines.append("* Keep the sound as it is now: no other model did clearly better. With eight places a "
                         "model, one answer more or less is chance, so a model has to get at least two more right, "
                         "and not feel harder, before I suggest a change.")
        else:
            change = {"hrtf": "Make HRTF the first choice for headphones in Settings.",
                      "lower": "Make the lower pitch behind twice as low: 6 semitones for sounds, 3 for the voice.",
                      "muffled": "Muffle sounds behind more: a cut-off of 0.3 instead of 0.7 of the cut-off in front."}[best]
            lines.append(f"* {best} did best: {percent(results[best]['within_one'])} within one compass point. {change}")
        lines.append("* If two models are close, the better ratings decide, and I ask you before changing anything.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.listening_test.compass",
                                     description="The listening test for sound in space and the voice (P2-T17u).")
    parser.add_argument("--name", default="po", help="who is taking the test, for the results file name")
    parser.add_argument("--rate", type=int, default=100, help="the voice's speed in percent, as in Settings (50 to 500)")
    parser.add_argument("--seed", type=int, default=1, help="a different number mixes the order differently")
    parser.add_argument("--analyse", nargs="+", metavar="CSV", help="write the findings from these results files")
    args = parser.parse_args(argv)

    if args.analyse:
        paths = [Path(p) for p in args.analyse]
        target = paths[0].parent / "compass-findings.md"
        target.write_text(findings(analyse(read_rows(paths)), [p.name for p in paths]), encoding="utf-8")
        print(f"Wrote {target}")
        return 0

    from desktop.audio import spatial, voice
    from desktop.audio.player import read_mono

    if not voice.available():
        print("The Alba voice is not installed. Run: .venv\\Scripts\\python.exe tools\\fetch_vendor.py --voice")
        return 1
    if not ITEM_SOUND.is_file():
        print("The item's direction sound is missing. Run: .venv\\Scripts\\python.exe tools\\make_placeholder_sounds.py")
        return 1
    print("Loading the voice, a few seconds.")
    speaker = voice.PiperSpeaker()
    speaker.load()
    results = Results(args.name, RESULTS, args.rate)
    test = CompassTest(results, speaker, read_mono(ITEM_SOUND), ask=input, tell=print, play=ConsolePlayer(),
                       hrtf=spatial.hrtf_available(), seed=args.seed, voice_rate=max(50, min(500, args.rate)) / 100)
    test.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
