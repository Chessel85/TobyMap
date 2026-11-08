r"""Make three lower "whump" sounds for the orientation beacon, for the PO to choose from (P2-T16h, SON-10).

    .venv\Scripts\python.exe tools\make_beacon_samples.py [--out sounds\samples]

Writes beacon-1-soft-whump.wav, beacon-2-deep-thud.wav and beacon-3-heartbeat.wav. Each is a
low tone whose pitch falls quickly as it dies away, which sounds like a soft knock on a drum.
A little of the tone an octave up is added, so it is still heard on laptop speakers, which
play almost nothing below about 150 Hz. The files are made, not recorded, so they are under the
same GPL-3.0 licence as the code. The folder is not in git.

To try one, choose it as the beacon's own sound file in Settings, Sounds. The PO chose sample 1,
the soft whump, which tools/make_placeholder_sounds.py now makes as the default beacon.wav.
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RATE = 44100
PEAK = 0.5


def whump(start_hz: float, end_hz: float, seconds: float, decay_s: float, overtone: float = 0.35,
          knock: float = 0.0) -> np.ndarray:
    """A tone falling from start_hz to end_hz, dying away with time constant decay_s."""
    t = np.arange(int(RATE * seconds)) / RATE
    freq = end_hz + (start_hz - end_hz) * np.exp(-t / (seconds / 4))   # falls fast, then settles
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    tone = np.sin(phase) + overtone * np.sin(2 * phase)
    envelope = np.exp(-t / decay_s) * np.minimum(1.0, t / 0.003)       # 3 ms rise, so no click
    out = tone * envelope
    if knock:
        # A short, soft knock at the start: noise, smoothed so it is a thud, not a hiss.
        n = int(RATE * 0.015)
        noise = np.random.default_rng(7).standard_normal(n)
        noise = np.convolve(noise, np.ones(40) / 40, mode="same")
        out[:n] += knock * noise / np.abs(noise).max() * np.linspace(1, 0, n)
    fade = int(RATE * 0.01)
    out[-fade:] *= np.linspace(1, 0, fade)                              # no click at the end
    return out


def normalised(x: np.ndarray) -> np.ndarray:
    return (x / np.abs(x).max() * PEAK).astype(np.float32)


def soft_whump() -> np.ndarray:
    """Sample 1, the PO's choice on 8 November 2026: the default beacon.wav (tools/make_placeholder_sounds.py)."""
    return normalised(whump(150, 60, 0.3, 0.08))


def samples() -> dict[str, np.ndarray]:
    lub = whump(130, 55, 0.2, 0.06)
    dub = whump(160, 70, 0.22, 0.06) * 0.7
    gap = np.zeros(int(RATE * 0.12))
    return {
        "beacon-1-soft-whump.wav": soft_whump(),
        "beacon-2-deep-thud.wav": normalised(whump(110, 45, 0.4, 0.12, overtone=0.45, knock=0.4)),
        "beacon-3-heartbeat.wav": normalised(np.concatenate([lub, gap, dub])),
    }


def write(path: Path, mono: np.ndarray) -> None:
    data = (np.clip(mono, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "sounds" / "samples"))
    out = Path(parser.parse_args(argv).out)
    out.mkdir(parents=True, exist_ok=True)
    for name, mono in samples().items():
        write(out / name, mono)
        print(f"Wrote {name}, {len(mono) / RATE:.2f} seconds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
