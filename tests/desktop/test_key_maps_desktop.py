"""Settings, Keys on the desktop: choose a key map, Save keys as, Open key file, Reset keys (P3-T31b).
No file dialog is opened: the tests give the dialogs their file names."""
import json

import pytest
from PySide6.QtWidgets import QApplication

from desktop import dialogs
from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import SettingsDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    yield w
    w.close()


def open_settings(window):
    window.dispatch("settings.open")
    QApplication.processEvents()
    (dialog,) = [d for d in window.findChildren(SettingsDialog) if d.isVisible()]
    return dialog


def test_the_key_map_box_lists_the_key_maps_with_the_chosen_one(window):
    dialog = open_settings(window)
    labels = [dialog.keymap_box.itemText(i) for i in range(dialog.keymap_box.count())]
    assert labels == [k["label"] for k in window.session.keymap_choices()]
    assert dialog.keymap_box.currentText() == "Windows desktop"
    assert dialog.keymap_box.accessibleName() == "Key map"
    dialog.reject()


def test_choosing_a_key_map_applies_at_once_and_is_said(window):
    dialog = open_settings(window)
    dialog.keymap_box.setCurrentIndex(dialog.keymap_box.findData("alternative"))
    assert window.session.settings.keymap == "alternative"
    assert dialog.keys_message.text() == "Key map: Alternative."
    dialog.reject()


def test_reset_keys_gives_back_the_key_maps_own_keys(window):
    window.session.run("keys.remap", command="where.heading", key="G")
    dialog = open_settings(window)
    dialog.reset_keys.click()
    assert window.session.settings.keys == {}
    assert dialog.keys_message.text().startswith("Your keys are reset.")
    dialog.reject()


def test_save_then_open_a_key_file(window, tmp_path, monkeypatch):
    window.session.run("keys.remap", command="where.heading", key="G")
    path = tmp_path / "mine.json"
    monkeypatch.setattr(dialogs.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(path), "")))
    dialog = open_settings(window)
    dialog.save_keys.click()
    assert json.loads(path.read_text(encoding="utf-8"))["keys"] == {"where.heading": "G"}
    dialog.reset_keys.click()
    assert window.session.settings.keys == {}
    monkeypatch.setattr(dialogs.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
    dialog.open_keys.click()
    assert window.session.settings.keys == {"where.heading": "G"}
    assert dialog.keys_message.text() == "Key file opened. The key map is Windows desktop."
    dialog.reject()


def test_a_bad_key_file_says_why_and_changes_nothing(window, tmp_path, monkeypatch):
    window.session.run("keys.remap", command="where.heading", key="G")
    path = tmp_path / "bad.json"
    path.write_text("this is not a key file", encoding="utf-8")
    monkeypatch.setattr(dialogs.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
    dialog = open_settings(window)
    dialog.open_keys.click()
    assert window.session.settings.keys == {"where.heading": "G"}
    assert dialog.keys_message.text() == "That is not a key file TobyMap can read, so your keys are not changed."
    dialog.reject()
