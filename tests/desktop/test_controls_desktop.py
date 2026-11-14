"""The status line and the move and zoom buttons in the desktop window (P3-T18, VIS-1, SCP-2, ACC-2)."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

from desktop.announcer import RecordingAnnouncer
from desktop.audio.player import RecordingSpatial
from desktop.audio.voice import RecordingVoice
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": -1.0, "zoom_m": 5000, "step_m": 1000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(braille_works=True), sounds=RecordingSounds(),
                   data_folder=tmp_path, spatial=RecordingSpatial(), voice=RecordingVoice())
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


def test_the_line_says_the_same_as_c_and_h_after_a_step(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Up)
    c = window.session.run("where.coordinates").announcements[0]["text"]
    h = window.session.run("where.heading").announcements[0]["text"]
    assert window.status_line.text() == f"{c}. {h}"


def test_a_button_sends_its_command(window):
    before = window.status_line.text()
    window.control_buttons["move.north"].click()
    assert window.status_line.text() != before
    assert window.session.world.lat > 51.2


def test_neither_is_reached_by_tab(window):
    widgets = [window.status_line, *window.control_buttons.values()]
    assert all(w.focusPolicy() == Qt.FocusPolicy.NoFocus for w in widgets)
    window.control_buttons["zoom.in"].click()
    assert not any(b.hasFocus() for b in window.findChildren(QPushButton))


def test_the_setting_hides_both(window):
    assert window.controls.isVisibleTo(window)
    window.handle(window.session.run("settings.set", field="show_controls", value=False))
    assert not window.controls.isVisibleTo(window)
    window.handle(window.session.run("settings.set", field="show_controls", value=True))
    assert window.controls.isVisibleTo(window)


def test_the_buttons_are_renamed_when_the_orientation_changes(window, qtbot):
    assert window.control_buttons["move.north"].text() == "North"
    qtbot.keyClick(window.map, Qt.Key.Key_O)
    assert window.control_buttons["move.north"].text() == "Forward"
    assert window.control_buttons["move.west"].text() == "Turn left"
