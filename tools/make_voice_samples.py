"""Make WAV samples of the spatial voice for the PO to judge (P2-T16g, SON-3).

The same label at 100 to 500 percent speed, made as TobyMap now makes it: Piper as fast as it
cleanly can, then the core's time stretching (mapcore/sound/stretch.py). For comparison, 500
percent made as before, by Piper alone. Then the voice behind you: lower and slower, as it was
(BEHIND_PITCH), and lower at the same speed, by time stretching, which the PO chose and
TobyMap now uses.

    .venv\\Scripts\\python.exe tools\\make_voice_samples.py

Needs the Piper voice (tools/fetch_vendor.py --voice). The files go in voices/samples, which
is not in git, and are plain mono, with no direction, so only the speed and pitch differ.
"""
from __future__ import annotations

import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop.audio.spatial import RATE, resample  # noqa: E402
from desktop.audio.voice import PiperSpeaker, voice_path  # noqa: E402
from mapcore.sound.scene import BEHIND_PITCH, VOICE_BEHIND_PITCH  # noqa: E402
from mapcore.sound.stretch import lower_pitch, speed_up, split_rate  # noqa: E402

OUT = ROOT / "voices" / "samples"
TEXT = "Southampton Central, 2.1 kilometres"


def write(name: str, samples: np.ndarray) -> float:
    OUT.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(OUT / name), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())
    return len(samples) / RATE


def main() -> int:
    if voice_path() is None:
        print("The Piper voice is not installed. Run: .venv\\Scripts\\python.exe tools\\fetch_vendor.py --voice")
        return 1
    speaker = PiperSpeaker()
    speaker.load()
    print(f'Samples of "{TEXT}", in {OUT}')
    normal = None
    for number, percent in enumerate((100, 200, 300, 400, 500), start=1):
        piper, stretch = split_rate(percent / 100)
        mono = speaker(TEXT, piper)
        started = time.perf_counter()
        mono = speed_up(mono, RATE, stretch)
        ms = (time.perf_counter() - started) * 1000
        seconds = write(f"{number} speed {percent} percent.wav", mono)
        normal = normal or seconds
        print(f"* {percent} percent: {seconds:.2f} seconds, {normal / seconds:.1f} times as fast; "
              f"time stretching took {ms:.0f} ms")
    seconds = write("6 speed 500 percent, Piper alone, as before.wav", speaker(TEXT, 5.0))
    print(f"* 500 percent by Piper alone, as before: {seconds:.2f} seconds, {normal / seconds:.1f} times as fast")
    ahead = speaker(TEXT, 1.0)
    write("7 ahead, for comparison.wav", ahead)
    seconds = write("8 behind, 3 semitones lower and slower, as before.wav", resample(ahead, BEHIND_PITCH))
    print(f"* Behind, lower and slower, as before: {seconds:.2f} seconds")
    seconds = write("9 behind, 1.5 semitones lower at the same speed, as now.wav", lower_pitch(ahead, RATE, VOICE_BEHIND_PITCH))
    print(f"* Behind, lower at the same speed, as now: {seconds:.2f} seconds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
