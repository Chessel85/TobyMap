"""Spike S6 desktop voice demo: place names spoken from a direction, for listening with headphones.

Run in a console window, from the repository folder:

    .venv\\Scripts\\python.exe tools\\spikes\\s6\\demo.py

Plain lines of text; type a number and press Enter. Nothing plays until you
press Enter. Each label is spoken by the chosen voice and placed in space by
the spike S1 HRTF processing (or stereo panning, if you choose it).

It also reports how long each voice took to start and to speak each label.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "tools" / "spikes" / "s1"))

import spatial  # noqa: E402
import voices  # noqa: E402
from demo_common import ask, choose  # noqa: E402

LABELS = ["Berlin", "Bay of Biscay", "Llívia", "Isle of Skye", "Mont Saint-Michel", "Kilimanjaro",
          "River Thames", "Saint Petersburg"]
DIRECTIONS = [(0, "ahead"), (45, "ahead right"), (90, "right"), (135, "behind right"),
              (180, "behind"), (225, "behind left"), (270, "left"), (315, "ahead left")]

_loaded: dict = {}


def voice(key: str):
    if key not in _loaded:
        print(f"Loading {voices.VOICES[key]}.")
        v, seconds = voices.load(key)
        _loaded[key] = v
        print(f"Loaded in {seconds:.1f} seconds.")
    return _loaded[key]


def say_at(key: str, text: str, bearing: float, engine: str) -> float:
    """Speak text from a bearing. Returns the time from request to sound, in ms."""
    start = time.perf_counter()
    mono = voice(key).speak(text)
    stereo = spatial.render(engine, mono, bearing, 0.1)
    ready_ms = (time.perf_counter() - start) * 1000
    spatial.play(stereo)
    return ready_ms


def tour(key: str, engine: str) -> None:
    print("Eight place names, one from each direction, clockwise from ahead.")
    for (bearing, name), label in zip(DIRECTIONS, LABELS):
        print(f"{label}, from {name}.")
        ask("Press Enter to play.")
        ms = say_at(key, label, bearing, engine)
        print(f"Ready in {ms:.0f} ms.")


def side_by_side(engine: str) -> None:
    label = choose("Which place name?", [(l, l) for l in LABELS])
    if label is None:
        return
    bearing = choose("From which direction?", [(str(b), f"{n.capitalize()}, {b} degrees") for b, n in DIRECTIONS])
    if bearing is None:
        return
    for key in voices.available():
        voice(key)
        print(f"{voices.VOICES[key]}.")
        ask("Press Enter to play.")
        ms = say_at(key, label, float(bearing), engine)
        print(f"Ready in {ms:.0f} ms.")


def timings() -> None:
    print("Timing every voice on every place name. Nothing is played.")
    for key in voices.available():
        v = voice(key)
        times = []
        for label in LABELS:
            start = time.perf_counter()
            v.speak(label)
            times.append((time.perf_counter() - start) * 1000)
        times.sort()
        print(f"{voices.VOICES[key]}: median {times[len(times) // 2]:.0f} ms, slowest {times[-1]:.0f} ms.")


def main() -> int:
    print("TobyMap spike S6: spatial voices. Use headphones.")
    available = voices.available()
    key, engine = available[0], "hrtf"
    if not spatial.KEMAR_ZIP.is_file():
        print("The S1 HRTF data is missing, so stereo panning is used. Run tools\\spikes\\s1\\demo.py once to fetch it.")
        engine = "stereo"
    while True:
        print()
        print(f"Voice: {voices.VOICES[key]}. Placing: {spatial.ENGINES[engine][0]}.")
        action = choose("Main menu", [
            ("tour", "Eight place names from eight directions"),
            ("side", "Side by side: one name, one direction, every voice"),
            ("timings", "Time every voice, without playing"),
            ("voice", "Change the voice"),
            ("engine", "Change between HRTF and stereo"),
        ])
        if action is None:
            print("Goodbye.")
            return 0
        if action == "voice":
            key = choose("Voices", [(k, voices.VOICES[k]) for k in available]) or key
        elif action == "engine":
            engine = choose("Placing", [(k, v[0]) for k, v in spatial.ENGINES.items()]) or engine
        elif action == "tour":
            tour(key, engine)
        elif action == "side":
            side_by_side(engine)
        elif action == "timings":
            timings()


if __name__ == "__main__":
    sys.exit(main())
