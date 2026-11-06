"""Turning Qt key events into the registry's shared key names (mapcore/commands/registry.py)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

_NAMED = {
    Qt.Key.Key_Up: "Up", Qt.Key.Key_Down: "Down", Qt.Key.Key_Left: "Left", Qt.Key.Key_Right: "Right",
    Qt.Key.Key_PageUp: "Page Up", Qt.Key.Key_PageDown: "Page Down", Qt.Key.Key_Home: "Home",
    Qt.Key.Key_End: "End", Qt.Key.Key_Space: "Space", Qt.Key.Key_Return: "Enter", Qt.Key.Key_Enter: "Enter",
    Qt.Key.Key_Backspace: "Backspace", Qt.Key.Key_Delete: "Delete", Qt.Key.Key_Escape: "Escape",
    Qt.Key.Key_Tab: "Tab", Qt.Key.Key_Backtab: "Tab", Qt.Key.Key_Insert: "Insert",
    **{getattr(Qt.Key, f"Key_F{i}"): f"F{i}" for i in range(1, 13)},
}
# Shift with a number key makes a symbol that differs by keyboard layout ("%" or "("), so
# the key itself is found from the system's own key code: Windows' virtual keys "0" to "9",
# and macOS's key codes for the number row (DP109).
_WINDOWS_DIGITS = {0x30 + i: str(i) for i in range(10)}
_MAC_DIGITS = {0x1D: "0", 0x12: "1", 0x13: "2", 0x14: "3", 0x15: "4", 0x17: "5", 0x16: "6", 0x1A: "7", 0x1C: "8",
               0x19: "9"}
_MODIFIER_KEYS = {Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_AltGr}


def key_name(event: QKeyEvent) -> str | None:
    key = Qt.Key(event.key())
    if key in _MODIFIER_KEYS:
        return None
    digit = _shifted_digit(event)
    if key in _NAMED:
        base = _NAMED[key]
    elif digit is not None:
        base = digit
    elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z or Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        base = chr(int(key.value))
    elif 0x21 <= int(key.value) <= 0x7E or 0xA1 <= int(key.value) <= 0xFF:
        # A symbol, such as "," or "/": Qt's key code is the character. Shift is
        # part of the symbol it makes, as in the web version, so it is not added.
        base = chr(int(key.value))
    else:
        return None
    mods = event.modifiers()
    parts = []
    if mods & Qt.KeyboardModifier.ControlModifier:
        parts.append("Ctrl")
    if mods & Qt.KeyboardModifier.AltModifier:
        parts.append("Alt")
    if (mods & Qt.KeyboardModifier.ShiftModifier and (len(base) > 1 or base.isalnum())) \
            or key == Qt.Key.Key_Backtab:
        parts.append("Shift")
    return "+".join(parts + [base])


def _shifted_digit(event: QKeyEvent) -> str | None:
    """The number key under a shifted symbol, or None."""
    if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier or Qt.Key.Key_0 <= event.key() <= Qt.Key.Key_9:
        return None
    import sys

    table = _MAC_DIGITS if sys.platform == "darwin" else _WINDOWS_DIGITS if sys.platform == "win32" else {}
    return table.get(event.nativeVirtualKey())
