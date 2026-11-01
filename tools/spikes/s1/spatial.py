"""Spike S1: placing a sound in space, without playing it (architecture 12.2).

Each engine turns a mono sound into stereo for one direction and distance.
Playing is done separately (play()), so the tests never open an audio device.

Engines in this file:

* "hrtf": the project's own HRTF processing. Each sound is convolved with the
  MIT KEMAR head-related impulse responses for its direction (Gardner and
  Martin, MIT Media Lab, 1994, provided without usage restrictions). This is
  the same kind of processing the browser does for Web Audio.
* "stereo": the speakers mode of SON-1. Equal-power stereo panning, with
  sounds behind you pitched lower so front and back can be told apart.

Synthizer and OpenAL Soft are the other desktop candidates. They need the
PO's permission to build or load their libraries on this laptop, so they are
added once that is given.

Directions are bearings relative to ahead, in degrees clockwise: 0 ahead,
90 right, 180 behind, 270 left. Distance is a fraction of the hearing range,
which is the view radius at the current zoom (SON-9): 1 is the edge of the view.
"""
from __future__ import annotations

import io
import math
import wave
import zipfile
from pathlib import Path

import numpy as np

RATE = 44100
HERE = Path(__file__).resolve().parent
KEMAR_ZIP = HERE / "downloads" / "mit_kemar_compact.zip"

# SON-9: full loudness at a twentieth of the range or closer, each doubling of
# distance equally quieter, down to QUIET_DB at the edge of the view.
NEAR = 0.05
QUIET_DB = -30.0
# The second distance cue: muffling, by a low-pass filter whose cut-off falls
# from bright when near to dull at the edge of the view, and duller beyond.
BRIGHT_HZ = 16000.0
DULL_HZ = 1500.0
BEYOND_HZ = 900.0


# Distance -----------------------------------------------------------------

def distance_gain_db(fraction: float) -> float:
    if fraction <= NEAR:
        return 0.0
    if fraction >= 1.0:
        return QUIET_DB
    return QUIET_DB * math.log2(fraction / NEAR) / math.log2(1.0 / NEAR)


def muffle_cutoff_hz(fraction: float) -> float:
    if fraction > 1.0:
        return BEYOND_HZ
    if fraction <= NEAR:
        return BRIGHT_HZ
    t = math.log2(fraction / NEAR) / math.log2(1.0 / NEAR)
    return BRIGHT_HZ * (DULL_HZ / BRIGHT_HZ) ** t


def lowpass(x: np.ndarray, cutoff_hz: float) -> np.ndarray:
    """A gentle two-pole low-pass (two one-pole stages), enough for muffling."""
    if cutoff_hz >= RATE / 2 * 0.9:
        return x
    a = math.exp(-2 * math.pi * cutoff_hz / RATE)
    y = x.astype(np.float64)
    for _ in range(2):
        out = np.empty_like(y)
        state = 0.0
        b = 1 - a
        for i, v in enumerate(y):  # short sounds only; fine for a spike
            state = b * v + a * state
            out[i] = state
        y = out
    return y.astype(np.float32)


def apply_distance(stereo: np.ndarray, fraction: float) -> np.ndarray:
    gain = 10 ** (distance_gain_db(fraction) / 20)
    cutoff = muffle_cutoff_hz(fraction)
    left = lowpass(stereo[:, 0], cutoff)
    right = lowpass(stereo[:, 1], cutoff)
    return (np.stack([left, right], axis=1) * gain).astype(np.float32)


# HRTF ---------------------------------------------------------------------

class Kemar:
    """The horizontal-plane KEMAR responses, every 5 degrees all the way round."""

    def __init__(self, zip_path: Path = KEMAR_ZIP):
        if not zip_path.is_file():
            raise FileNotFoundError(f"{zip_path} is missing. Run: python tools/spikes/s1/demo.py --fetch")
        self.right_side: dict[int, np.ndarray] = {}
        with zipfile.ZipFile(zip_path) as z:
            for az in range(0, 181, 5):
                data = z.read(f"elev0/H0e{az:03d}a.wav")
                with wave.open(io.BytesIO(data)) as w:
                    frames = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2)
                self.right_side[az] = frames.astype(np.float32) / 32768.0
        # The compact set measures sources on the right (0 to 180 degrees).
        # A source on the left is the mirror image: swap the ears.
        peak = max(np.abs(h).max() for h in self.right_side.values())
        self.scale = 0.5 / peak

    def response(self, bearing: float) -> np.ndarray:
        """Stereo impulse response (left, right) for a bearing, nearest 5 degrees."""
        b = round((bearing % 360) / 5) * 5 % 360
        if b <= 180:
            h = self.right_side[b]
        else:
            h = self.right_side[360 - b][:, ::-1]
        return h * self.scale


_kemar: Kemar | None = None


def kemar() -> Kemar:
    global _kemar
    if _kemar is None:
        _kemar = Kemar()
    return _kemar


def hrtf(mono: np.ndarray, bearing: float, fraction: float) -> np.ndarray:
    h = kemar().response(bearing)
    left = np.convolve(mono, h[:, 0])
    right = np.convolve(mono, h[:, 1])
    return apply_distance(np.stack([left, right], axis=1).astype(np.float32), fraction)


# Stereo (speakers mode) -----------------------------------------------------

BEHIND_PITCH = 0.84  # about three semitones lower for sounds behind


def resample(mono: np.ndarray, factor: float) -> np.ndarray:
    """Play at factor times the speed: below 1 is lower and longer."""
    n = int(len(mono) / factor)
    return np.interp(np.arange(n) * factor, np.arange(len(mono)), mono).astype(np.float32)


def stereo(mono: np.ndarray, bearing: float, fraction: float) -> np.ndarray:
    rad = math.radians(bearing % 360)
    pan = math.sin(rad)                 # -1 left, 1 right
    behind = math.cos(rad) < -1e-9
    source = resample(mono, BEHIND_PITCH) if behind else mono
    angle = (pan + 1) * math.pi / 4     # equal-power law
    out = np.stack([source * math.cos(angle), source * math.sin(angle)], axis=1) * 0.5
    return apply_distance(out.astype(np.float32), fraction)


ENGINES = {
    "hrtf": ("Own HRTF processing (MIT KEMAR)", hrtf),
    "stereo": ("Stereo panning with pitch, the speakers mode", stereo),
}


def render(engine: str, mono: np.ndarray, bearing: float, fraction: float = 0.1) -> np.ndarray:
    return ENGINES[engine][1](mono, bearing, fraction)


# Test sounds ----------------------------------------------------------------

def _fade(x: np.ndarray, ms: float = 10) -> np.ndarray:
    n = int(RATE * ms / 1000)
    ramp = np.linspace(0, 1, n, dtype=np.float32)
    x = x.copy()
    x[:n] *= ramp
    x[-n:] *= ramp[::-1]
    return x


def noise_bursts(count: int = 3, burst_ms: int = 180, gap_ms: int = 90, seed: int = 1) -> np.ndarray:
    """Pink-ish noise in short bursts: broadband sound is easiest to place."""
    rng = np.random.default_rng(seed)
    parts = []
    for _ in range(count):
        white = rng.standard_normal(int(RATE * burst_ms / 1000))
        spectrum = np.fft.rfft(white)
        freqs = np.fft.rfftfreq(len(white), 1 / RATE)
        spectrum[1:] /= np.sqrt(freqs[1:])  # pink: equal energy per octave
        spectrum[0] = 0
        burst = np.fft.irfft(spectrum, len(white))
        burst = (burst / np.abs(burst).max() * 0.8).astype(np.float32)
        parts += [_fade(burst), np.zeros(int(RATE * gap_ms / 1000), np.float32)]
    return np.concatenate(parts)


def chime(freq: float = 660, ms: int = 450) -> np.ndarray:
    """A bell-like tone: narrower in frequency, so harder to place."""
    t = np.arange(int(RATE * ms / 1000)) / RATE
    tone = sum(np.sin(2 * np.pi * freq * k * t) / k for k in (1, 2, 3, 4.2))
    tone = tone * np.exp(-t * 6)
    return _fade((tone / np.abs(tone).max() * 0.8).astype(np.float32))


def wav_file(path: Path) -> np.ndarray:
    """A WAV file as mono at 44.1 kHz, for trying the PO's own sounds."""
    with wave.open(str(path)) as w:
        width, channels, rate = w.getsampwidth(), w.getnchannels(), w.getframerate()
        raw = w.readframes(w.getnframes())
    dtype = {1: np.uint8, 2: "<i2", 4: "<i4"}[width]
    data = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    if width == 1:
        data = (data - 128) / 128
    else:
        data /= float(2 ** (8 * width - 1))
    data = data.reshape(-1, channels).mean(axis=1)
    if rate != RATE:
        data = resample(data, rate / RATE)
    peak = np.abs(data).max() or 1.0
    return (data / peak * 0.8).astype(np.float32)


SOUNDS = {
    "noise": ("Noise bursts", noise_bursts),
    "chime": ("Chime", chime),
}


def play(stereo_samples: np.ndarray) -> None:  # pragma: no cover - opens the audio device
    import sounddevice as sd

    sd.play(stereo_samples, RATE, blocking=True)
