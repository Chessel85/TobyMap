"""Look around on the desktop (P3-T11a; SON-4, SON-3, INF-10, AD-10).

The core's Response.scan lists the items to play, in order, each with its sound and its spatial
voice label already placed. This plays them one after another on the window's own sound player:
the item's sound, then its label when the sound ends (as Hear its direction does), then, once both
have finished, a short pause, then the next. As each item starts, the core is told with
session.scan_item(index), so Enter on the map goes to that item and Shift+Space repeats it; at
the end, session.scan_item(None).

A timer looks every 20 ms whether the item is still sounding: the item's sound in the mixer, under
the tag "scan", or a label still being made or played. Without a sound device or a voice, nothing
sounds, and the items go by at the pace of the pause alone.

A key that runs a command stops it: the window stops the scan wherever it stops the voice
(Response.stop_voice, P2-T17n).
"""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer

TICK_MS = 20
ITEM_LIMIT_S = 15.0   # an item never holds the scan longer, in case the voice stops answering


class ScanPlayer(QObject):
    """window gives play_scan_item(item, first), scan_sounding() and handle(response); session gives
    scan_item(index). clock is for the tests."""

    def __init__(self, window, clock=time.perf_counter):
        super().__init__(window)
        self.window = window
        self.clock = clock
        self.items: list[dict] = []
        self.index = -1
        self.gap_s = 0.3
        self._pause_until: float | None = None
        self._item_at = 0.0
        self.started: list[str] = []   # the id of each item started, for the tests
        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self.tick)

    @property
    def playing(self) -> bool:
        return bool(self.items)

    def start(self, scan: dict) -> None:
        self.stop()
        self.items = list(scan["items"])
        self.gap_s = float(scan.get("gap_s", 0.3))
        self.index = -1
        self._next()
        if self.playing:
            self.timer.start()

    def stop(self) -> None:
        """Stops at once. The core has ended the scan itself, as the key's command was carried out."""
        self.timer.stop()
        self.items = []
        self.index = -1
        self._pause_until = None

    def _next(self) -> None:
        self.index += 1
        self._pause_until = None
        if self.index >= len(self.items):
            self.stop()
            self.window.handle(self.window.session.scan_item(None))
            return
        item = self.items[self.index]
        self.started.append(item["id"])
        self._item_at = self.clock()
        self.window.handle(self.window.session.scan_item(self.index))   # Braille, and Repeat, for this item
        self.window.play_scan_item(item, first=self.index == 0)

    def tick(self) -> None:
        if not self.playing:
            return
        now = self.clock()
        if self.window.scan_sounding() and now - self._item_at < ITEM_LIMIT_S:
            return
        if self._pause_until is None:
            self._pause_until = now + self.gap_s
        elif now >= self._pause_until:
            self._next()
