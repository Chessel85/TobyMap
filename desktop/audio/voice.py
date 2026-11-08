"""The spatial voice on the desktop: Piper with the Alba voice (P2-T7a; SON-3, ANN-3, AD-10).

Alba (Scottish English, female, CC-BY 4.0) gave the best sense of direction when you
listened in spike S6. Each label is made into sound in memory, then placed by the core's
sound scene like any other sound, with the lower pitch behind (DP137), and mixed by the
spatial player's mixer. So the voice never goes through the screen reader.

* The voice is loaded on a thread of its own while TobyMap starts, about 8 seconds, and
  one silent label is made then, so the first real label is not slow.
* Labels are made on that thread too, about 100 ms each, so the window never waits.
* Above 100 percent speed, the core's time stretching makes up what Piper cannot, and makes
  the voice behind you lower without slowing it (P2-T16g).
* A newer label stops an older one, whether it is still being made or already playing (ANN-3).
* A label that waits for the item's sound (Response.voice["after"]) starts when that sound ends.

The voice files are not kept in git. tools/fetch_vendor.py --voice puts them in
desktop/vendor/piper; spike S6's own copy in voices/piper is used if that is missing.
Importing this module loads nothing.
"""
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

import numpy as np

from desktop.audio import spatial
from desktop.audio.spatial import RATE, resample
from mapcore.sound.stretch import shape_voice

VOICE_FILE = "en_GB-alba-medium.onnx"
VOICE_DIRS = (Path(__file__).resolve().parents[1] / "vendor" / "piper",
              Path(__file__).resolve().parents[2] / "voices" / "piper")
CREDIT = "Voice: Alba, Scottish English female, from Piper voices, CC-BY 4.0."
PEAK = 0.8


def voice_path() -> Path | None:
    for folder in VOICE_DIRS:
        if (folder / VOICE_FILE).is_file() and (folder / (VOICE_FILE + ".json")).is_file():
            return folder / VOICE_FILE
    return None


def available() -> bool:
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    return voice_path() is not None


def trim(samples: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    """Silence at the start and end is cut, so the label starts at once."""
    loud = np.nonzero(np.abs(samples) > threshold)[0]
    return samples if len(loud) == 0 else samples[max(0, loud[0] - 100): loud[-1] + 400]


def even_out(samples: np.ndarray) -> np.ndarray:
    top = float(np.abs(samples).max()) if len(samples) else 0.0
    return (samples / top * PEAK).astype(np.float32) if top else samples.astype(np.float32)


class PiperSpeaker:
    """Text to mono samples at the player's rate, with Piper. load() takes a few seconds."""

    def __init__(self, path: Path | None = None):
        self.path = path or voice_path()
        self._voice = None

    def load(self) -> None:
        from piper import PiperVoice

        if self.path is None:
            raise FileNotFoundError(VOICE_FILE)
        self._voice = PiperVoice.load(str(self.path))
        self(".", 1.0)   # the first label is slow otherwise

    def __call__(self, text: str, rate: float = 1.0) -> np.ndarray:
        from piper import SynthesisConfig

        voice = self._voice
        base = voice.config.length_scale or 1.0
        config = SynthesisConfig(length_scale=base / max(0.25, rate))
        chunks = [c.audio_float_array for c in voice.synthesize(text, syn_config=config)]
        samples = trim(np.concatenate(chunks) if chunks else np.zeros(0, np.float32))
        if voice.config.sample_rate != RATE:
            samples = resample(samples, voice.config.sample_rate / RATE)
        return even_out(samples)


_speaker: PiperSpeaker | None = None


def load() -> PiperSpeaker:
    """The one shared speaker, loaded: for the listening test (tools/listening_test)."""
    global _speaker
    if _speaker is None:
        speaker = PiperSpeaker()
        speaker.load()
        _speaker = speaker
    return _speaker


def speak(text: str) -> np.ndarray:
    """A label as mono samples at the sound rate, trimmed of silence, peak 0.8: for the listening test."""
    return load()(text)


class SpatialVoice:
    """Labels in the spatial voice, placed by the core and mixed with the other sounds.

    speaker turns text into mono samples (PiperSpeaker, or a stand-in in the tests); player
    is the SpatialPlayer whose mixer plays them. state is "loading", "ready", "missing" (no
    Piper or no voice files) or "failed" (it would not load)."""

    def __init__(self, player, speaker=None, start: bool = True):
        self.player = player
        self.speaker = speaker
        self.state = "loading"
        self.timings: list[dict] = []   # each label: text and milliseconds from asking to sound
        self._gen = 0
        self._pending = 0
        self._lock = threading.Lock()
        self._jobs: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="spatial voice", daemon=True)
        if start:
            self._thread.start()

    def _load(self) -> None:
        if self.speaker is None:
            if not available():
                self.state = "missing"
                return
            self.speaker = PiperSpeaker()
        try:
            load = getattr(self.speaker, "load", None)
            if load is not None:
                load()
        except Exception:
            self.state = "failed"
            return
        self.state = "ready"

    def _run(self) -> None:
        self._load()
        while True:
            job = self._jobs.get()
            if job is None:
                return
            self._make(*job)

    def say(self, voice: dict, start_frame: int | None = None) -> str:
        """Ask for a label (the core's Response.voice). Gives the voice's state: if it is not
        "ready" nothing is said, and the window tells the user why. start_frame is the
        mixer frame the label may start at, after the item's sound."""
        if self.state != "ready":
            return self.state
        with self._lock:
            self._gen += 1
            self._pending += 1
            gen = self._gen
        self.player.mixer.stop("voice")   # a newer label stops the older one at once (ANN-3)
        self._jobs.put((gen, voice, start_frame, time.perf_counter()))
        return self.state

    def stop(self) -> None:
        with self._lock:
            self._gen += 1
        self.player.mixer.stop("voice")

    def _make(self, gen: int, voice: dict, start_frame: int | None, asked: float) -> None:
        try:
            self._make_one(gen, voice, start_frame, asked)
        finally:
            with self._lock:
                self._pending -= 1

    def _make_one(self, gen: int, voice: dict, start_frame: int | None, asked: float) -> None:
        if gen != self._gen:
            return   # a newer label was asked for before this one was begun
        try:
            mono = self.speaker(voice["text"], voice.get("rate", 1.0))
            # Faster than Piper can speak, and lower behind you without slowing: the core's
            # time stretching (P2-T16g).
            mono = shape_voice(mono, RATE, voice.get("stretch", 1.0), voice.get("pitch", 1.0))
        except Exception:
            return
        samples = spatial.placed(mono, voice["placed"]) if len(mono) else None
        with self._lock:
            if gen != self._gen or samples is None:
                return
            self.player.mixer.add(samples, tag="voice", start_frame=start_frame)
        self.timings.append({"text": voice["text"], "ms": (time.perf_counter() - asked) * 1000})
        del self.timings[:-200]

    def wait(self, timeout: float = 10.0) -> bool:
        """For the tests: wait until every label asked for has been made."""
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            if self.state != "loading" and self._pending == 0:
                return True
            time.sleep(0.005)
        return False

    def close(self) -> None:
        self.stop()
        self._jobs.put(None)


class RecordingVoice:
    """Stand-in for the window's tests: records the labels that would have been said."""

    def __init__(self, state: str = "ready"):
        self.state = state
        self.said: list[tuple[dict, int | None]] = []

    def say(self, voice: dict, start_frame: int | None = None) -> str:
        if self.state == "ready":
            self.said.append((voice, start_frame))
        return self.state

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass
