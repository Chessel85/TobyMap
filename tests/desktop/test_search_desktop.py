"""P3-T8c and P3-T8d: the search dialog on the desktop (SRB-1, SRB-2, NAV-8, ACC-7)."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.dialogs import SearchDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession
from desktop.announcer import RecordingAnnouncer

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}


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


def open_box(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(SearchDialog) if d.isVisible()]
    return box


def test_ctrl_f_opens_it_with_a_field_choice_list_and_cancel(window, qtbot):
    box = open_box(window, qtbot)
    assert box.field.hasFocus() and box.cancel_button.text() == "Cancel"
    assert box.scope.itemText(0) == "Everywhere" and box.list.count() == 0


def test_typing_lists_results_after_the_pause_and_down_reaches_them(window, qtbot):
    box = open_box(window, qtbot)
    qtbot.keyClicks(box.field, "Sao Paulo")
    qtbot.waitUntil(lambda: box.list.count() > 0, timeout=3000)
    assert "São Paulo" in box.list.item(0).text()
    qtbot.keyClick(box.field, Qt.Key.Key_Down)
    assert box.list.hasFocus()


def test_nothing_found_says_so(window, qtbot):
    box = open_box(window, qtbot)
    qtbot.keyClicks(box.field, "qqzzxx")
    qtbot.waitUntil(lambda: box.message.text() != "", timeout=3000)
    assert box.message.text() == "Nothing found for qqzzxx."


def test_enter_goes_to_the_result_and_closes(window, qtbot):
    box = open_box(window, qtbot)
    qtbot.keyClicks(box.field, "Sao Paulo")
    qtbot.waitUntil(lambda: box.list.count() > 0, timeout=3000)
    qtbot.keyClick(box.field, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert not box.isVisible()
    assert window.session.current_feature.name == "São Paulo"


def test_narrowing_to_a_layer_is_sent(window, qtbot):
    box = open_box(window, qtbot)
    box.scope.setCurrentIndex(box.scope.count() - 1)
    qtbot.keyClicks(box.field, "Paris")
    qtbot.waitUntil(lambda: box.message.text() != "" or box.list.count() > 0, timeout=3000)
    assert box.scope.currentData().startswith("layer:")


def test_cancel_closes_and_stays(window, qtbot):
    box = open_box(window, qtbot)
    box.cancel_button.click()
    QApplication.processEvents()
    assert not box.isVisible()
    assert (window.session.world.lat, window.session.world.lon) == pytest.approx((51.06, -1.31))
