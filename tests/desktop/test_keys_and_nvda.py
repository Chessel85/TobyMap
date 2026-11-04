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
    (Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier, "F1"),
    (Qt.Key.Key_Up, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier, "Ctrl+Shift+Up"),
])
def test_key_names(key, mods, name):
    assert key_name(press(key, mods)) == name


def test_modifier_alone_has_no_name():
    assert key_name(press(Qt.Key.Key_Shift, Qt.KeyboardModifier.ShiftModifier)) is None


def test_missing_library_means_no_braille(tmp_path: Path):
    client = NvdaClient(dll_path=tmp_path / "missing.dll")
    assert not client.loaded
    assert not client.is_running()
    assert client.braille("hello") is False
