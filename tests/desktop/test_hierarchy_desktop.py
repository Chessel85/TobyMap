"""Hierarchy mode's lists on the desktop (P3-T6b; NAV-4, ACC-7): the ambiguous up and Down's two lists
are the location history's list with a Cancel button, offscreen, with a recording announcer and sounds."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import HistoryDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


def press(qtbot, widget, key):
    qtbot.keyClick(widget, key)
    QApplication.processEvents()


def the_list(window):
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(HistoryDialog) if d.isVisible()]
    return box


def choose(qtbot, box, starts):
    row = next(i for i in range(box.list.count()) if box.list.item(i).text().startswith(starts))
    box.list.setCurrentRow(row)
    press(qtbot, box.list, Qt.Key.Key_Return)


def test_m_enters_hierarchy_mode_and_the_menu_shows_its_tick(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_M)
    assert window.announcer.texts[-1] == "Hierarchy mode. Hampshire."
    assert window.session.toggles()["mode.toggle"] is True


def test_down_then_a_kind_then_a_feature_goes_there(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_M)
    press(qtbot, window.map, Qt.Key.Key_Down)
    box = the_list(window)
    assert box.windowTitle() == "Inside Hampshire" and box.close_button.text() == "Cancel"
    choose(qtbot, box, "Railway stations")
    second = the_list(window)   # the kind's features, in a box of their own, with the focus in it
    assert second is not box and second.windowTitle() == "Railway stations in Hampshire"
    choose(qtbot, second, "Brockenhurst")
    assert not second.isVisible() and window.session.current_feature.name == "Brockenhurst"


def test_the_ambiguous_up_plays_its_sound_and_cancel_stays(window, qtbot):
    s = window.session
    s.run("mode.toggle")
    kinds = s.run("move.south").dialog["lines"]
    s.run("hierarchy.choose", index=next(i for i, k in enumerate(kinds) if k.startswith("Railway stations")))
    s.run("hierarchy.choose", index=0)
    assert s.current_feature.name == "Brockenhurst"
    before = (window.session.world.lat, window.session.world.lon)
    press(qtbot, window.map, Qt.Key.Key_Up)
    assert "ambiguous_up" in window.sounds.played
    box = the_list(window)
    assert [box.list.item(i).text() for i in range(box.list.count())] == [
        "New Forest National Park, national park", "Hampshire, county of England"]
    box.close_button.click()
    QApplication.processEvents()
    assert not box.isVisible() and (window.session.world.lat, window.session.world.lon) == before
    assert window.session.current_feature.name == "Brockenhurst"
