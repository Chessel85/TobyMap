"""Ctrl+Shift+M on the desktop (P4-T9a; USR-4): on the map it puts the measure start back to where you are, said."""
import pytest
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state={"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


def test_ctrl_shift_m_on_the_map_says_where_you_measure_from(window):
    window.session._measure_start = {"name": "Rome", "lat": 41.9, "lon": 12.5, "mark": None}
    assert window.dispatch_key("Ctrl+Shift+M", "map")
    QApplication.processEvents()
    assert "Measuring from where you are." in window.announcer.texts
    assert window.session._measure_start is None
