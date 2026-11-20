"""Key names and the NVDA client's safe fallbacks (no screen reader is contacted)."""
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from desktop.keys import key_name
from desktop.nvda import NvdaClient


def press(key, mods=Qt.KeyboardModifier.NoModifier):
    return QKeyEvent(QEvent.Type.KeyPress, key, mods)


@pytest.mark.parametrize("key, mods, name", [
    (Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier, "Up"),
    (Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier, "Page Down"),
    (Qt.Key.Key_Space, Qt.KeyboardModifier.ShiftModifier, "Shift+Space"),
    (Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier, "Ctrl+Space"),
    (Qt.Key.Key_R, Qt.KeyboardModifier.NoModifier, "R"),
    (Qt.Key.Key_Comma, Qt.KeyboardModifier.ControlModifier, "Ctrl+,"),
    (Qt.Key.Key_Slash, Qt.KeyboardModifier.ControlModifier, "Ctrl+/"),
    (Qt.Key.Key_Semicolon, Qt.KeyboardModifier.NoModifier, ";"),
    (Qt.Key.Key_Less, Qt.KeyboardModifier.ShiftModifier, "<"),
    (Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier, "F1"),
    (Qt.Key.Key_Up, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier, "Ctrl+Shift+Up"),
])
def test_key_names(key, mods, name):
    assert key_name(press(key, mods), mac=False) == name


@pytest.mark.parametrize("key, mods, name", [
    # Qt calls Command Control and Control Meta on a Mac; the key maps call them Cmd and Ctrl (P3-T31a).
    (Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier, "Cmd+F"),
    (Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier, "Shift+Cmd+F"),
    (Qt.Key.Key_M, Qt.KeyboardModifier.MetaModifier, "Ctrl+M"),
    (Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier, "Alt+Left"),
    (Qt.Key.Key_Comma, Qt.KeyboardModifier.MetaModifier, "Ctrl+,"),
    (Qt.Key.Key_Space, Qt.KeyboardModifier.MetaModifier | Qt.KeyboardModifier.ControlModifier, "Ctrl+Cmd+Space"),
])
def test_key_names_on_a_mac(key, mods, name):
    assert key_name(press(key, mods), mac=True) == name


def test_the_windows_key_is_not_named_on_windows():
    assert key_name(press(Qt.Key.Key_H, Qt.KeyboardModifier.MetaModifier), mac=False) == "H"


@pytest.mark.parametrize("symbol", [Qt.Key.Key_Percent, Qt.Key.Key_ParenLeft])
def test_shift_with_a_number_key_is_named_by_the_key_whatever_the_symbol(symbol):
    """Shift+5 makes "%" on a UK or US keyboard, and "(" on a French one: it is "Shift+5" (DP109)."""
    import sys

    native = {"win32": 0x35, "darwin": 0x17}.get(sys.platform)
    if native is None:
        pytest.skip("only Windows and macOS key codes are known")
    event = QKeyEvent(QEvent.Type.KeyPress, symbol, Qt.KeyboardModifier.ShiftModifier, 0, native, 0, "%")
    assert key_name(event) == "Shift+5"


def test_modifier_alone_has_no_name():
    assert key_name(press(Qt.Key.Key_Shift, Qt.KeyboardModifier.ShiftModifier)) is None


def test_missing_library_means_no_braille(tmp_path: Path):
    client = NvdaClient(dll_path=tmp_path / "missing.dll")
    assert not client.loaded
    assert not client.is_running()
    assert client.braille("hello") is False
