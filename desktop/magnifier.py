"""Magnifier support on the desktop (P2-T13a; ACC-8, DP146).

Windows Magnifier, ZoomText and others can follow the text cursor. A Windows text
cursor, the system caret, is a small invisible rectangle a window owns; a magnifier
reads where it is and keeps it in view. While the map has focus, the map owns a caret
on the small square round its centre that the core gives (session.focus_rect), and
after every move it says the caret has moved, so the magnifier brings the centre, where
the location always is, back into view.

The caret is never shown, so nothing blinks on the map. Screen readers ignore a caret
in a pane, which has no text. Elsewhere than Windows, and in the tests, where Qt has no
real window, nothing is done, but the square asked for is still kept in `rect`.
"""
from __future__ import annotations

import sys

EVENT_OBJECT_LOCATIONCHANGE = 0x800B
OBJID_CARET = -8
CHILDID_SELF = 0


def _user32():
    if sys.platform != "win32":
        return None
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.platformName() != "windows":   # offscreen, in the tests
        return None
    import ctypes

    return ctypes.windll.user32


class CaretTracker:
    def __init__(self, widget):
        self._widget = widget
        self._user32 = _user32()
        self._owned = False
        self.rect: tuple[int, int, int, int] | None = None   # the last square, in the window's pixels
        self.moves = 0

    def place(self, focus: dict) -> None:
        """Put the caret on the core's square, in the map's own coordinates, and tell
        the magnifier it moved. Only while the map has focus."""
        from PySide6.QtCore import QPoint

        w = self._widget
        if not w.hasFocus():
            return
        top = w.window()
        ratio = top.devicePixelRatioF()
        corner = w.mapTo(top, QPoint(round(focus["x"]), round(focus["y"])))
        x, y = round(corner.x() * ratio), round(corner.y() * ratio)
        width, height = max(1, round(focus["width"] * ratio)), max(1, round(focus["height"] * ratio))
        self.rect = (x, y, width, height)
        self.moves += 1
        u = self._user32
        if u is None:
            return
        hwnd = int(top.winId())
        if not self._owned:
            self._owned = bool(u.CreateCaret(hwnd, None, width, height))
        if self._owned:
            u.SetCaretPos(x, y)
            # The same place as before sends no event of its own, so say it moved.
            u.NotifyWinEvent(EVENT_OBJECT_LOCATIONCHANGE, hwnd, OBJID_CARET, CHILDID_SELF)

    def release(self) -> None:
        """The map lost focus: the caret goes, so the next window's own caret is followed."""
        if self._owned and self._user32 is not None:
            self._user32.DestroyCaret()
        self._owned = False
