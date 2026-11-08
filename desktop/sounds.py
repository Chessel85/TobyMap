"""The earcon player (P1-T10, P2-T16h; SON-7, SON-8).

Each earcon is a short WAV, read in advance and played through the spatial sound
player's mixer, so it starts within 50 ms (NFR-1). It plays at the same time as
speech and never waits for it. Tests use RecordingSounds.
"""
from __future__ import annotations

import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOUNDS = ROOT / "sounds"


def readable_wav(path: Path) -> bool:
    """Whether a file is a WAV sound TobyMap can play: 8, 16 or 32-bit samples, not empty (SON-8)."""
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() > 0 and w.getsampwidth() in (1, 2, 4)
    except (OSError, EOFError, wave.Error):
        return False


class SoundPlayer:
    """The earcons, played through the spatial sound player's mixer (P2-T16h, SON-7, SON-8).

    Until P2-T16h they went through Qt's QSoundEffect, a second player beside the mixer. On
    Windows it sometimes added a swish to the tick when a sound started again before it had
    ended, and an old sound could half play. The web version always used its one player.
    """

    def __init__(self, spatial):
        self.spatial = spatial
        self.failed: list[str] = []

    def preload(self, infos: list[dict]) -> None:
        self.spatial.preload(infos)

    def play(self, info: dict) -> tuple[bool, bool]:
        """info is the core's earcon_file(): the user's own file, else the default. Returns
        (played, own file failed): if the user's own file cannot be played, the default plays
        and the caller tells the user (SON-8). It plays at the earcon volume (P2-T8)."""
        return self.spatial.play_earcon(info)


class RecordingSounds:
    """Stand-in for tests: records the earcons that would have played."""

    def __init__(self):
        self.played: list[str] = []
        self.gains: list[float] = []
        self.failed: list[str] = []
        self.preloaded: list[str] = []
        self.times: list[float] = []   # when each was played, for the held key test (P2-T14)

    def preload(self, infos: list[dict]) -> None:
        self.preloaded = [i["event"] for i in infos]

    def play(self, info: dict) -> tuple[bool, bool]:
        self.played.append(info["event"])
        self.gains.append(info.get("gain", 1.0))
        self.times.append(time.perf_counter())
        return True, bool(info.get("custom")) and info["custom"] in self.failed
