r"""Make a short, distinct placeholder tone for every earcon (P1-T12, SON-6, SON-8).

    .venv\Scripts\python.exe tools\make_placeholder_sounds.py [--out sounds]

Writes one WAV file for each earcon in mapcore/describe/earcons.yaml. A file
that already exists is left alone, so your own sounds are never overwritten
(DP111). Only the standard library is used.
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mapcore.describe import earcon_list  # noqa: E402

RATE = 44100
# event: list of (frequency in Hz, seconds); the tick is soft and the blocked sound is low and flat.
TONES = {
    "tick": [(1800, 0.025)],
    "blocked": [(180, 0.12), (140, 0.16)],
    "crossed_added": [(880, 0.06), (1320, 0.08)],
    "ding": [(1568, 0.25)],
    "no_data": [(330, 0.1), (330, 0.1)],
    "ambiguous_up": [(660, 0.08), (990, 0.08), (660, 0.08)],
    "line_crossing": [(1200, 0.04), (900, 0.04)],
}
VOLUME = 0.35


def samples(tones) -> list[int]:
    out: list[int] = []
    for freq, seconds in tones:
        n = int(RATE * seconds)
        for i in range(n):
            fade = min(1.0, i / (RATE * 0.004), (n - i) / (RATE * 0.008))   # no clicks at the ends
            out.append(int(32767 * VOLUME * fade * math.sin(2 * math.pi * freq * i / RATE)))
    return out


def write(path: Path, tones) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack(f"<{len(samples(tones))}h", *samples(tones)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "sounds"))
    out = Path(parser.parse_args(argv).out)
    out.mkdir(parents=True, exist_ok=True)
    for e in earcon_list():
        target = out / e["file"]
        if target.exists():
            print(f"Kept {target.name}, which is already there.")
            continue
        write(target, TONES[e["event"]])
        print(f"Wrote {target.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
