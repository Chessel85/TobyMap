"""Spike S1 desktop sound demo, for listening with headphones.

Run in a console window, from the repository folder:

    .venv\\Scripts\\python.exe tools\\spikes\\s1\\demo.py

Everything is plain lines of text, and you answer by typing a number and
pressing Enter, so it works with NVDA in the console. Nothing plays until you
press Enter, so speech and sound do not overlap.

The quiz saves your answers to docs/spikes/s1-listening/, one CSV file per
quiz, with the direction played and the direction you heard.

    --fetch   download the MIT KEMAR HRTF data first (about 230 KB)
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import spatial  # noqa: E402
from demo_common import ask, choose  # noqa: E402

KEMAR_URL = "http://sound.media.mit.edu/resources/KEMAR/compact.zip"
RESULTS = ROOT / "docs" / "spikes" / "s1-listening"
DIRECTIONS = [(0, "ahead"), (45, "ahead right"), (90, "right"), (135, "behind right"),
              (180, "behind"), (225, "behind left"), (270, "left"), (315, "ahead left")]


def fetch() -> None:
    spatial.KEMAR_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if spatial.KEMAR_ZIP.is_file():
        print("The KEMAR data is already downloaded.")
        return
    print(f"Downloading {KEMAR_URL}")
    with urllib.request.urlopen(KEMAR_URL, timeout=60) as r:
        spatial.KEMAR_ZIP.write_bytes(r.read())
    print("Done.")


def sound_choices() -> list[tuple[str, str]]:
    options = [(k, label) for k, (label, _f) in spatial.SOUNDS.items()]
    for path in sorted((ROOT / "sounds").glob("*.wav")):
        options.append((f"file:{path}", f"Your sound file {path.name}"))
    return options


def make_sound(key: str):
    if key.startswith("file:"):
        return spatial.wav_file(Path(key[5:]))
    return spatial.SOUNDS[key][1]()


def engine_choices() -> list[tuple[str, str]]:
    return [(k, label) for k, (label, _f) in spatial.ENGINES.items()]


def wait_then_play(stereo) -> None:
    ask("Press Enter to play.")
    spatial.play(stereo)


def tour(engine: str, sound) -> None:
    print("A walk round eight directions, starting ahead and going clockwise.")
    for bearing, name in DIRECTIONS:
        print(f"{name.capitalize()}, {bearing} degrees.")
        wait_then_play(spatial.render(engine, sound, bearing))
    print("That was all eight.")


def distances(engine: str, sound) -> None:
    print("The same sound ahead right, from near to far. The range is the edge of the view (SON-9).")
    for fraction, name in [(0.03, "very near"), (0.1, "a tenth of the way to the edge of the view"),
                           (0.25, "a quarter of the way"), (0.5, "halfway"), (1.0, "at the edge of the view"),
                           (2.0, "beyond the view")]:
        print(f"{name.capitalize()}.")
        wait_then_play(spatial.render(engine, sound, 45, fraction))
    print("Done.")


def side_by_side(sound) -> None:
    bearing = choose("Which direction?", [(str(b), f"{n.capitalize()}, {b} degrees") for b, n in DIRECTIONS])
    if bearing is None:
        return
    for key, (label, _f) in spatial.ENGINES.items():
        print(f"{label}.")
        wait_then_play(spatial.render(key, sound, float(bearing)))
    print("Done. Choose again from the menu to repeat.")


def quiz(engine: str, sound_key: str, sound, trials: int = 8) -> None:
    print(f"Listening quiz: {trials} sounds from random directions. After each, type where you heard it.")
    print("1 ahead, 2 ahead right, 3 right, 4 behind right, 5 behind, 6 behind left, 7 left, 8 ahead left.")
    print("Type r to hear it again, or q to stop.")
    rng = random.Random()
    rows = []
    for n in range(1, trials + 1):
        bearing, _name = rng.choice(DIRECTIONS)
        stereo = spatial.render(engine, sound, bearing)
        print(f"Sound {n} of {trials}.")
        wait_then_play(stereo)
        while True:
            answer = ask("Where was it? 1 to 8:")
            if answer == "r":
                spatial.play(stereo)
                continue
            if answer == "q":
                break
            if answer.isdigit() and 1 <= int(answer) <= 8:
                break
            print("Please type 1 to 8, r to replay, or q to stop.")
        if answer == "q":
            break
        heard = DIRECTIONS[int(answer) - 1][0]
        error = abs((heard - bearing + 180) % 360 - 180)
        rows.append({"time": datetime.now().isoformat(timespec="seconds"), "engine": engine, "sound": sound_key,
                     "played_degrees": bearing, "heard_degrees": heard, "error_degrees": error})
    if not rows:
        return
    within = sum(1 for r in rows if r["error_degrees"] <= 45)
    front_back = sum(1 for r in rows if (r["played_degrees"] + r["heard_degrees"]) % 360 == 180
                     and r["played_degrees"] not in (90, 270))
    print(f"{within} of {len(rows)} within 45 degrees. Front and back mixed up {front_back} times.")
    print("The played directions were: " + ", ".join(
        f"{DIRECTIONS[[b for b, _ in DIRECTIONS].index(r['played_degrees'])][1]}" for r in rows) + ".")
    RESULTS.mkdir(parents=True, exist_ok=True)
    name = sound_key if not sound_key.startswith("file:") else Path(sound_key[5:]).stem
    out = RESULTS / f"{datetime.now():%Y-%m-%d-%H%M}-{engine}-{name}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
    shown = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"Saved to {shown}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spike S1 desktop sound demo.")
    parser.add_argument("--fetch", action="store_true", help="download the MIT KEMAR HRTF data")
    args = parser.parse_args(argv)
    if args.fetch or not spatial.KEMAR_ZIP.is_file():
        fetch()
    print("TobyMap spike S1: spatial sound. Use headphones.")
    engine, sound_key = "hrtf", "chime"  # the PO found the chime easier to place
    while True:
        sound_label = dict(sound_choices()).get(sound_key, sound_key)
        print()
        print(f"Engine: {spatial.ENGINES[engine][0]}. Sound: {sound_label}.")
        action = choose("Main menu", [
            ("tour", "Walk round eight directions"),
            ("distance", "Near to far"),
            ("side", "Side by side: one direction through every engine"),
            ("quiz", "Listening quiz, saved to a file"),
            ("engine", "Change the engine"),
            ("sound", "Change the sound"),
        ])
        if action is None:
            print("Goodbye.")
            return 0
        if action == "engine":
            engine = choose("Engines", engine_choices()) or engine
            continue
        if action == "sound":
            sound_key = choose("Sounds", sound_choices()) or sound_key
            continue
        sound = make_sound(sound_key)
        if action == "tour":
            tour(engine, sound)
        elif action == "distance":
            distances(engine, sound)
        elif action == "side":
            side_by_side(sound)
        elif action == "quiz":
            quiz(engine, sound_key, sound)


if __name__ == "__main__":
    sys.exit(main())
