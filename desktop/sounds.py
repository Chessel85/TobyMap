"""The stand-in sound player: plays the earcon files (P1-T10, SON-7, SON-8).

Spatial sound comes in Phase 2. Here each earcon is a short WAV played with
QSoundEffect, loaded in advance so it starts within 50 ms (NFR-1). It plays at
the same time as speech and never waits for it. Tests use RecordingSounds.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOUNDS = ROOT / "sounds"


class SoundPlayer:
    def __init__(self, folder: Path | None = None):
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QSoundEffect

        self._QUrl, self._Effect = QUrl, QSoundEffect
        self.folder = folder or SOUNDS
        self._effects: dict[str, object] = {}
        self.failed: list[str] = []

    def _effect(self, path: Path):
        key = str(path)
        if key not in self._effects:
            effect = self._Effect()
            effect.setSource(self._QUrl.fromLocalFile(key))
            self._effects[key] = effect
        return self._effects[key]

    def preload(self, infos: list[dict]) -> None:
        """Load every earcon at start, and play each once silently, so the sound
        device is open before the first real one. Without this, the first tick
        after start was very quiet or cut short (PO feedback on checklist 5,
        second pass)."""
        for info in infos:
            for name in (info.get("custom"), info.get("default")):
                if not name:
                    continue
                path = Path(name) if Path(name).is_absolute() else self.folder / name
                if path.is_file():
                    self._warm_up(self._effect(path))
                    break

    def _warm_up(self, effect) -> None:
        state = {"done": False}

        def go():
            if state["done"] or effect.status() != self._Effect.Status.Ready:
                return
            state["done"] = True
            effect.setVolume(0.0)
            effect.playingChanged.connect(lambda: effect.isPlaying() or effect.setVolume(1.0))
            effect.play()

        effect.statusChanged.connect(go)
        go()

    def play(self, info: dict) -> tuple[bool, bool]:
        """info is the core's earcon_file(): the user's own file, else the default.
        Returns (played, own file failed): if the user's own file cannot be
        played, the default plays and the caller tells the user (SON-8)."""
        custom_failed = False
        for name in (info.get("custom"), info.get("default")):
            if not name:
                continue
            path = Path(name) if Path(name).is_absolute() else self.folder / name
            if path.is_file():
                effect = self._effect(path)
                effect.setVolume(1.0)   # in case the silent warm-up is still playing
                effect.play()
                return True, custom_failed
            custom_failed = custom_failed or name == info.get("custom")
        return False, custom_failed


class RecordingSounds:
    """Stand-in for tests: records the earcons that would have played."""

    def __init__(self):
        self.played: list[str] = []
        self.failed: list[str] = []
        self.preloaded: list[str] = []

    def preload(self, infos: list[dict]) -> None:
        self.preloaded = [i["event"] for i in infos]

    def play(self, info: dict) -> tuple[bool, bool]:
        self.played.append(info["event"])
        return True, bool(info.get("custom")) and info["custom"] in self.failed
