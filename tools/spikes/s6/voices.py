"""Spike S6: built-in voices for spatial labels (architecture 12.7, SON-3, DP82).

Each voice turns a label, such as "Berlin", into mono audio samples, which the
S1 code then places in space. Nothing here plays sound or opens a device.

Voices:

* eSpeak NG (GPL-3.0), through the library in the espeakng-loader package.
  Small and fast, and familiar to many screen reader users.
* Piper (GPL-3.0) neural voices, each about 60 MB, from rhasspy/piper-voices:
  Cori (public domain), Alba (CC-BY 4.0) and Northern English male
  (CC-BY-SA 4.0). Voices with unclear or non-commercial licences are left out.

Windows voices are not used (DP90).
"""
from __future__ import annotations

import ctypes
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PIPER_DIR = ROOT / "voices" / "piper"
RATE = 44100  # the S1 engines' rate

PIPER_VOICES = {
    "cori": ("Piper, Cori, southern English female", "en_GB-cori-medium.onnx", "public domain"),
    "alba": ("Piper, Alba, Scottish female", "en_GB-alba-medium.onnx", "CC-BY 4.0"),
    "northern": ("Piper, northern English male", "en_GB-northern_english_male-medium.onnx", "CC-BY-SA 4.0"),
}


def to_rate(samples: np.ndarray, rate: int) -> np.ndarray:
    if rate == RATE:
        return samples.astype(np.float32)
    n = int(len(samples) * RATE / rate)
    return np.interp(np.arange(n) * rate / RATE, np.arange(len(samples)), samples).astype(np.float32)


def normalise(samples: np.ndarray, peak: float = 0.8) -> np.ndarray:
    top = float(np.abs(samples).max()) if len(samples) else 0.0
    return (samples / top * peak).astype(np.float32) if top else samples


class Espeak:
    """eSpeak NG speaking into memory, through its library (no sound device)."""

    AUDIO_OUTPUT_SYNCHRONOUS = 2
    POS_CHARACTER = 1
    CHARS_UTF8 = 1

    def __init__(self, voice: str = "en-gb", rate_wpm: int = 175):
        import espeakng_loader

        self.lib = ctypes.CDLL(espeakng_loader.get_library_path())
        data = espeakng_loader.get_data_path().encode("utf-8")
        self.lib.espeak_Initialize.restype = ctypes.c_int
        self.lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        self.rate = self.lib.espeak_Initialize(self.AUDIO_OUTPUT_SYNCHRONOUS, 0, data, 0)
        if self.rate <= 0:
            raise RuntimeError("eSpeak NG did not start")
        self._buffer: list[np.ndarray] = []
        callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

        def collect(wav, count, _events):
            if count > 0:
                self._buffer.append(np.ctypeslib.as_array(wav, shape=(count,)).astype(np.float32) / 32768.0)
            return 0

        self._callback = callback_type(collect)  # kept alive for the library
        self.lib.espeak_SetSynthCallback(self._callback)
        self.lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
        self.lib.espeak_SetVoiceByName(voice.encode())
        self.lib.espeak_SetParameter(1, rate_wpm, 0)  # espeakRATE
        self.lib.espeak_Synth.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int,
                                          ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]

    def speak(self, text: str) -> np.ndarray:
        self._buffer = []
        data = text.encode("utf-8")
        self.lib.espeak_Synth(data, len(data) + 1, 0, self.POS_CHARACTER, 0, self.CHARS_UTF8, None, None)
        samples = np.concatenate(self._buffer) if self._buffer else np.zeros(0, np.float32)
        return normalise(to_rate(_trim(samples), self.rate))


class Piper:
    def __init__(self, key: str):
        from piper import PiperVoice

        self.voice = PiperVoice.load(str(PIPER_DIR / PIPER_VOICES[key][1]))
        self.rate = self.voice.config.sample_rate

    def speak(self, text: str) -> np.ndarray:
        chunks = [c.audio_float_array for c in self.voice.synthesize(text)]
        samples = np.concatenate(chunks) if chunks else np.zeros(0, np.float32)
        return normalise(to_rate(_trim(samples), self.rate))


def _trim(samples: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    """Drop silence at the start and end, so the label starts at once."""
    loud = np.nonzero(np.abs(samples) > threshold)[0]
    if len(loud) == 0:
        return samples
    return samples[max(0, loud[0] - 100): loud[-1] + 400]


VOICES = {"espeak": "eSpeak NG, British English", **{k: v[0] for k, v in PIPER_VOICES.items()}}


def load(key: str):
    """A voice and how long it took to load, in seconds."""
    start = time.perf_counter()
    voice = Espeak() if key == "espeak" else Piper(key)
    return voice, time.perf_counter() - start


def available() -> list[str]:
    keys = ["espeak"]
    keys += [k for k, v in PIPER_VOICES.items() if (PIPER_DIR / v[1]).is_file()]
    return keys
