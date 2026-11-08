r"""Make a short, distinct placeholder tone for every earcon (P1-T12, SON-6, SON-8).

    .venv\Scripts\python.exe tools\make_placeholder_sounds.py [--out sounds]

Writes one WAV file for each earcon in mapcore/describe/earcons.yaml. A file
that already exists is left alone, so your own sounds are never overwritten
(DP111). Only the standard library is used, except for the beacon: the soft whump
the PO chose from tools/make_beacon_samples.py (P2-T16h), made with NumPy.
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
    "beyond_view": [(500, 0.15)],
    "item_direction": [(520, 0.07), (780, 0.1)],
    "meridian_crossed": [(700, 0.05), (1050, 0.05)],    # stand-ins only: the product owner's own files are kept in git
    "equator_crossed": [(1050, 0.05), (700, 0.05)],
    "beacon": [],   # made by make_beacon_samples.soft_whump instead (P2-T16h)
}
VOLUME = 0.35
SOFTER: dict[str, float] = {}   # earcons quieter than VOLUME


def samples(tones, volume: float = VOLUME) -> list[int]:
    out: list[int] = []
    for freq, seconds in tones:
        n = int(RATE * seconds)
        for i in range(n):
            fade = min(1.0, i / (RATE * 0.004), (n - i) / (RATE * 0.008))   # no clicks at the ends
            out.append(int(32767 * volume * fade * math.sin(2 * math.pi * freq * i / RATE)))
    return out


def write(path: Path, tones, volume: float = VOLUME) -> None:
    data = samples(tones, volume)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack(f"<{len(data)}h", *data))


def write_beacon(path: Path) -> None:
    """The beacon: the soft whump, a low tone falling in pitch as it dies away (P2-T16h, SON-10)."""
    sys.path.insert(0, str(ROOT / "tools"))
    import make_beacon_samples

    make_beacon_samples.write(path, make_beacon_samples.soft_whump())


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
        if e["event"] == "beacon":
            write_beacon(target)
        else:
            write(target, TONES[e["event"]], SOFTER.get(e["event"], VOLUME))
        print(f"Wrote {target.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
