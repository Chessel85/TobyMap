"""Placing a sound in space for the desktop (AD-10, moved here from spike S1).

Modes (SON-1):

* "stereo": the speakers mode. Equal-power panning, with sounds behind you
  pitched lower so ahead and behind can be told apart.
* "hrtf_pitch": the project's own HRTF processing with the MIT KEMAR
  impulse responses (Gardner and Martin, MIT Media Lab, 1994, provided without
  usage restrictions), with the same lower pitch behind.
* "hrtf": HRTF without the pitch cue.

Bearings are relative to ahead, clockwise: 0 ahead, 90 right, 180 behind,
270 left. Distance is a fraction of the hearing range: 1 is the edge of the view.
The distance curve is the core's (mapcore.sound).
"""
from __future__ import annotations

import io
import math
import wave
import zipfile
from pathlib import Path

import numpy as np

from mapcore.sound import CurveSettings, gain, muffle_cutoff_hz

RATE = 44100
BEHIND_PITCH = 0.84   # about three semitones lower for sounds behind
KEMAR_ZIP = Path(__file__).resolve().parents[2] / "tools" / "spikes" / "s1" / "downloads" / "mit_kemar_compact.zip"
CURVE = CurveSettings()


def lowpass(x: np.ndarray, cutoff_hz: float) -> np.ndarray:
    """A gentle two-pole low-pass (two one-pole stages), enough for muffling."""
    if cutoff_hz >= RATE / 2 * 0.9:
        return x
    a = math.exp(-2 * math.pi * cutoff_hz / RATE)
    y = x.astype(np.float64)
    b = 1 - a
    for _ in range(2):
        out = np.empty_like(y)
        state = 0.0
        for i, v in enumerate(y):
            state = b * v + a * state
            out[i] = state
        y = out
    return y.astype(np.float32)


def apply_distance(stereo_samples: np.ndarray, fraction: float, curve: CurveSettings = CURVE) -> np.ndarray:
    cutoff = muffle_cutoff_hz(fraction, curve)
    left = lowpass(stereo_samples[:, 0], cutoff)
    right = lowpass(stereo_samples[:, 1], cutoff)
    return (np.stack([left, right], axis=1) * gain(fraction, curve)).astype(np.float32)


def resample(mono: np.ndarray, factor: float) -> np.ndarray:
    """Play at factor times the speed: below 1 is lower and longer."""
    n = int(len(mono) / factor)
    return np.interp(np.arange(n) * factor, np.arange(len(mono)), mono).astype(np.float32)


def is_behind(bearing: float) -> bool:
    return math.cos(math.radians(bearing % 360)) < -1e-9


class Kemar:
    """The horizontal-plane KEMAR responses, every 5 degrees all the way round."""

    def __init__(self, zip_path: Path = KEMAR_ZIP):
        if not Path(zip_path).is_file():
            raise FileNotFoundError(f"{zip_path} is missing. Run: python tools/spikes/s1/demo.py --fetch")
        self.right_side: dict[int, np.ndarray] = {}
        with zipfile.ZipFile(zip_path) as z:
            for az in range(0, 181, 5):
                with wave.open(io.BytesIO(z.read(f"elev0/H0e{az:03d}a.wav"))) as w:
                    frames = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2)
                self.right_side[az] = frames.astype(np.float32) / 32768.0
        self.scale = 0.5 / max(np.abs(h).max() for h in self.right_side.values())

    def response(self, bearing: float) -> np.ndarray:
        b = round((bearing % 360) / 5) * 5 % 360
        h = self.right_side[b] if b <= 180 else self.right_side[360 - b][:, ::-1]   # a source on the left is the mirror image
        return h * self.scale


_kemar: Kemar | None = None


def kemar() -> Kemar:
    global _kemar
    if _kemar is None:
        _kemar = Kemar()
    return _kemar


def hrtf_available() -> bool:
    return KEMAR_ZIP.is_file()


def stereo(mono: np.ndarray, bearing: float, fraction: float, curve: CurveSettings = CURVE,
           pitch: bool = True) -> np.ndarray:
    pan = math.sin(math.radians(bearing % 360))     # -1 left, 1 right
    source = resample(mono, BEHIND_PITCH) if pitch and is_behind(bearing) else mono
    angle = (pan + 1) * math.pi / 4                 # equal-power law
    out = np.stack([source * math.cos(angle), source * math.sin(angle)], axis=1) * 0.5
    return apply_distance(out.astype(np.float32), fraction, curve)


def hrtf(mono: np.ndarray, bearing: float, fraction: float, curve: CurveSettings = CURVE, pitch: bool = False):
    source = resample(mono, BEHIND_PITCH) if pitch and is_behind(bearing) else mono
    h = kemar().response(bearing)
    both = np.stack([np.convolve(source, h[:, 0]), np.convolve(source, h[:, 1])], axis=1).astype(np.float32)
    return apply_distance(both, fraction, curve)


MODES = {
    "stereo": lambda m, b, f, c: stereo(m, b, f, c),
    "hrtf_pitch": lambda m, b, f, c: hrtf(m, b, f, c, pitch=True),
    "hrtf": lambda m, b, f, c: hrtf(m, b, f, c, pitch=False),
}


def render(mode: str, mono: np.ndarray, bearing: float, fraction: float, curve: CurveSettings = CURVE):
    return MODES[mode](mono, bearing, fraction, curve)


def render_moving(mode: str, mono: np.ndarray, start: float, end: float, fraction: float,
                  curve: CurveSettings = CURVE, pieces: int = 8) -> np.ndarray:
    """A sound heard while your position steps past it: its bearing moves from start to end
    (the short way round), in `pieces` parts."""
    delta = (end - start + 180) % 360 - 180
    edges = np.linspace(0, len(mono), pieces + 1).astype(int)
    parts = []
    for k in range(pieces):
        bearing = start + delta * (k + 0.5) / pieces
        parts.append(render(mode, mono[edges[k]:edges[k + 1]], bearing, fraction, curve))
    return np.concatenate(parts)


def to_wav_bytes(stereo_samples: np.ndarray) -> bytes:
    peak = float(np.abs(stereo_samples).max()) or 1.0
    scaled = stereo_samples / max(1.0, peak)
    data = (np.clip(scaled, -1, 1) * 32767).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    return out.getvalue()


def noise_bursts(count: int = 3, burst_ms: int = 180, gap_ms: int = 90, seed: int = 1) -> np.ndarray:
    """Pink-ish noise in short bursts: broadband sound is easiest to place."""
    rng = np.random.default_rng(seed)
    parts = []
    ramp_n = int(RATE * 0.01)
    ramp = np.linspace(0, 1, ramp_n, dtype=np.float32)
    for _ in range(count):
        white = rng.standard_normal(int(RATE * burst_ms / 1000))
        spectrum = np.fft.rfft(white)
        freqs = np.fft.rfftfreq(len(white), 1 / RATE)
        spectrum[1:] /= np.sqrt(freqs[1:])
        spectrum[0] = 0
        burst = np.fft.irfft(spectrum, len(white))
        burst = (burst / np.abs(burst).max() * 0.8).astype(np.float32)
        burst[:ramp_n] *= ramp
        burst[-ramp_n:] *= ramp[::-1]
        parts += [burst, np.zeros(int(RATE * gap_ms / 1000), np.float32)]
    return np.concatenate(parts)
