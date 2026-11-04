"""The spoken label voice for the desktop: Piper with the Alba voice (spike S6, AD-10, SON-3).

Alba (Scottish female, CC-BY 4.0) gave the best sense of direction when you listened on 1 November.
The voice files are not kept in git: they are in voices/piper (see docs/spikes/S6-spatial-voice.md).
Importing this module loads nothing; load() reads the voice, which takes a few seconds.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from desktop.audio.spatial import RATE, resample

VOICE_DIR = Path(__file__).resolve().parents[2] / "voices" / "piper"
VOICE_FILE = "en_GB-alba-medium.onnx"
CREDIT = "Voice: Alba, Scottish English female, from Piper voices, CC-BY 4.0."

_voice = None


def available() -> bool:
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    return (VOICE_DIR / VOICE_FILE).is_file()


def load():
    global _voice
    if _voice is None:
        from piper import PiperVoice

        _voice = PiperVoice.load(str(VOICE_DIR / VOICE_FILE))
        list(_voice.synthesize("Ready"))     # the first label is slow otherwise
    return _voice


def _trim(samples: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    loud = np.nonzero(np.abs(samples) > threshold)[0]
    return samples if len(loud) == 0 else samples[max(0, loud[0] - 100): loud[-1] + 400]


def speak(text: str) -> np.ndarray:
    """The label as mono samples at the sound rate, trimmed of silence, peak 0.8."""
    voice = load()
    chunks = [c.audio_float_array for c in voice.synthesize(text)]
    samples = _trim(np.concatenate(chunks) if chunks else np.zeros(0, np.float32))
    samples = resample(samples, voice.config.sample_rate / RATE) if voice.config.sample_rate != RATE else samples
    top = float(np.abs(samples).max()) if len(samples) else 0.0
    return (samples / top * 0.8).astype(np.float32) if top else samples
