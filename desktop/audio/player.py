"""The desktop's player for sounds placed in space (P2-T6b; AD-10, SON-1, SON-7, NFR-1).

The core's sound scene says how each sound should be heard; this player only carries it
out, with desktop/audio/spatial.py: the pitch, the pan or the KEMAR response, the muffling
and the loudness. Several sounds can play at once, each at its own loudness: an output
stream from sounddevice mixes whatever is playing, block by block, and never waits for
speech or for the map (SON-7).

The stream is opened when the player is made, before the first sound, so a sound starts
within 50 ms of being asked for (NFR-1). If there is no sound device, or sounddevice
cannot be loaded, the player is silent, and `missing` says so; the window tells the user
once, in the core's words.

How long each block took to mix is kept in `block_ms`, to check the mixing never falls
behind and crackles (phase 2 plan, risks).
"""
from __future__ import annotations

import threading
import time
import wave
from pathlib import Path

import numpy as np

from desktop.audio import spatial

BLOCK = 256          # frames a block: about 6 ms at 44.1 kHz
BLOCK_TIMES = 2000   # how many block times are kept


def read_mono(path: Path) -> np.ndarray:
    """A WAV file as mono samples from -1 to 1 at the player's rate."""
    with wave.open(str(path)) as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 1:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"{path.name}: {width * 8}-bit samples are not supported")
    mono = data.reshape(-1, channels).mean(axis=1)
    if rate != spatial.RATE:
        mono = spatial.resample(mono, rate / spatial.RATE)
    return mono.astype(np.float32)


class Mixer:
    """The sounds now playing, mixed a block at a time. Safe to add to from any thread."""

    def __init__(self):
        self._lock = threading.Lock()
        self._playing: list[list] = []   # [samples, position, tag]; a position below 0 is a wait
        self.block_ms: list[float] = []
        self.frames = 0                  # frames mixed so far: the mixer's own clock
        self.last_end = 0                # the frame the last sound added ends at

    def add(self, samples: np.ndarray, tag: str | None = None, start_frame: int | None = None) -> int:
        """Play samples from the next block, or from start_frame if that is later. A sound with a
        tag replaces one with the same tag (a newer label stops the older, ANN-3). Gives the frame
        it ends at."""
        with self._lock:
            if tag is not None:
                self._playing = [p for p in self._playing if p[2] != tag]
            wait = max(0, (start_frame or 0) - self.frames)
            self._playing.append([samples, -wait, tag])
            self.last_end = self.frames + wait + len(samples)
            return self.last_end

    def stop(self, tag: str) -> None:
        with self._lock:
            self._playing = [p for p in self._playing if p[2] != tag]

    def playing(self, tag: str) -> bool:
        with self._lock:
            return any(p[2] == tag for p in self._playing)

    @property
    def busy(self) -> bool:
        with self._lock:
            return bool(self._playing)

    def mix(self, frames: int) -> np.ndarray:
        started = time.perf_counter()
        out = np.zeros((frames, 2), dtype=np.float32)
        with self._lock:
            keep = []
            for item in self._playing:
                samples, at, _tag = item
                skip = min(frames, max(0, -at))   # still waiting to start
                part = samples[max(0, at):max(0, at) + frames - skip]
                out[skip:skip + len(part)] += part
                item[1] = at + frames
                if item[1] < len(samples):
                    keep.append(item)
            self._playing = keep
            self.frames += frames
        np.clip(out, -1.0, 1.0, out=out)
        self.block_ms.append((time.perf_counter() - started) * 1000)
        del self.block_ms[:-BLOCK_TIMES]
        return out


class SpatialPlayer:
    """Plays the core's placed sounds (Response.sounds) through the sound device."""

    def __init__(self, folder: Path | None = None, open_stream: bool = True):
        from desktop.sounds import SOUNDS

        self.folder = folder or SOUNDS
        self.mixer = Mixer()
        self._cache: dict[str, np.ndarray] = {}
        self.stream = None
        self.missing = False
        self.hrtf_missing = False
        if open_stream:
            self._open()

    def _open(self) -> None:
        try:
            import sounddevice as sd

            def callback(outdata, frames, _time, _status):
                outdata[:] = self.mixer.mix(frames)

            self.stream = sd.OutputStream(samplerate=spatial.RATE, channels=2, dtype="float32", blocksize=BLOCK,
                                          latency="low", callback=callback)
            self.stream.start()
        except Exception:   # no PortAudio, no device, or the device refused: carry on silent
            self.stream = None
            self.missing = True

    def close(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _mono(self, info: dict) -> tuple[np.ndarray | None, bool]:
        """The samples of the user's own file, else the default (SON-8): (samples, own file failed)."""
        custom_failed = False
        for name in (info.get("custom"), info.get("default")):
            if not name:
                continue
            path = Path(name) if Path(name).is_absolute() else self.folder / name
            key = str(path)
            if key not in self._cache:
                try:
                    self._cache[key] = read_mono(path)
                except (OSError, ValueError, EOFError, wave.Error):
                    custom_failed = custom_failed or name == info.get("custom")
                    continue
            return self._cache[key], custom_failed
        return None, custom_failed

    def render(self, placed: dict) -> tuple[np.ndarray | None, bool]:
        """The stereo samples for a placed sound, and whether the user's own file failed."""
        mono, custom_failed = self._mono(placed["file"])
        if mono is None:
            return None, custom_failed
        if placed["mode"] == "hrtf" and not spatial.hrtf_available():
            self.hrtf_missing = True
        return spatial.placed(mono, placed), custom_failed

    def play(self, placed: dict, tag: str | None = None) -> tuple[bool, bool]:
        """Play a placed sound at once, alongside anything already playing. With a tag, it
        replaces a sound with the same tag still playing. Returns (played, own file failed), as
        the earcon player does."""
        samples, custom_failed = self.render(placed)
        if samples is None or self.stream is None:
            return False, custom_failed
        self.mixer.add(samples, tag)
        return True, custom_failed

    @property
    def last_end(self) -> int:
        """The mixer frame the last sound played ends at: a label that waits for it starts there."""
        return self.mixer.last_end


class RecordingSpatial:
    """Stand-in for tests: records the placed sounds that would have played."""

    def __init__(self):
        self.played: list[dict] = []
        self.missing = False
        self.hrtf_missing = False
        self.last_end = 0

    def play(self, placed: dict, tag: str | None = None) -> tuple[bool, bool]:
        self.played.append(placed)
        return True, False

    def close(self) -> None:
        pass
