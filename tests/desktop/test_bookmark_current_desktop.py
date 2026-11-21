"""A bookmark as the current feature on the desktop (P4-T8d; USR-1, DP219 point 6, ACC-7): Delete asks in a
message box, and Cancel keeps it; the keys reach the core only from the map and the Information panel, so the
search box and Details keep Ctrl+C (docs/plan/p4-t0f-keys.md)."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop import storage
from desktop.announcer import RecordingAnnouncer
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
CTRL = Qt.KeyboardModifier.ControlModifier


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


def make_current(window):
    """Castles with Alpha, made the current feature by Enter in the Bookmarks group."""
    s = window.session
    s.bookmarks.lists[0].name = "Castles"
    s.bookmarks.add(0, "Alpha", 51.06, -1.11)
    window.handle(s.bookmarks_changed(s.run("focus.map")))
    s.panel(open={"bookmarks"})
    window.handle(s.run("panel.go", item="bookmark:0:0", group="bookmarks"))
    window.map.setFocus()
    QApplication.processEvents()
    assert s.current_bookmark is not None


def confirm_box(window):
    from desktop.dialogs import ConfirmBox

    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(ConfirmBox) if d.isVisible()]
    return box


def test_delete_asks_and_cancel_keeps_it(window, qtbot, tmp_path):
    make_current(window)
    written = storage.load_bookmarks(tmp_path)
    window.announcer.spoken.clear()
    qtbot.keyClick(window.map, Qt.Key.Key_Delete)
    box = confirm_box(window)
    assert box.text() == "Delete the bookmark Alpha from Castles?"
    assert box.ok_button.text() == "Delete" and box.cancel_button.text() == "Cancel"
    assert box.defaultButton() is box.cancel_button   # Enter straight away changes nothing
    box.cancel_button.click()
    QApplication.processEvents()
    assert [m.name for m in window.session.bookmarks.lists[0].bookmarks] == ["Alpha"]
    assert storage.load_bookmarks(tmp_path) == written
    assert not any("Deleted" in t for t in window.announcer.texts)
    assert window.session.current_bookmark is not None


def test_delete_after_asking_writes_the_file_and_says_it(window, qtbot, tmp_path):
    make_current(window)
    qtbot.keyClick(window.map, Qt.Key.Key_Delete)
    box = confirm_box(window)
    box.ok_button.click()
    QApplication.processEvents()
    assert window.session.bookmarks.lists[0].bookmarks == []
    assert "Alpha" not in storage.load_bookmarks(tmp_path)
    assert "Deleted Alpha." in window.map.accessibleName() or "Deleted Alpha." in window.announcer.texts


def test_ctrl_c_on_the_map_copies_the_bookmark(window, qtbot):
    make_current(window)
    qtbot.keyClick(window.map, Qt.Key.Key_C, CTRL)
    assert "Copied Alpha." in window.announcer.texts


def test_ctrl_c_in_the_search_box_still_copies_text(window, qtbot):
    from desktop.dialogs import SearchDialog

    make_current(window)
    QApplication.clipboard().setText("")
    qtbot.keyClick(window.map, Qt.Key.Key_F, CTRL)
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(SearchDialog) if d.isVisible()]
    box.field.setText("Winchester")
    box.field.selectAll()
    window.announcer.spoken.clear()
    qtbot.keyClick(box.field, Qt.Key.Key_C, CTRL)
    QApplication.processEvents()
    assert QApplication.clipboard().text() == "Winchester"
    assert window.session._bookmark_clip is None and not window.announcer.texts
    qtbot.keyClick(box.field, Qt.Key.Key_Delete)   # Delete edits the text, and asks nothing
    QApplication.processEvents()
    assert box.field.text() == ""
    from desktop.dialogs import ConfirmBox
    assert not [d for d in window.findChildren(ConfirmBox) if d.isVisible()]
    box.cancel_button.click()


def test_ctrl_c_in_details_copies_its_text(window, qtbot):
    make_current(window)
    QApplication.clipboard().setText("")
    window.focus_region("details")
    QApplication.processEvents()
    window.details.selectAll()
    window.announcer.spoken.clear()
    qtbot.keyClick(window.details, Qt.Key.Key_C, CTRL)
    QApplication.processEvents()
    assert QApplication.clipboard().text().startswith("Alpha")   # Details is about the bookmark
    assert window.session._bookmark_clip is None and not window.announcer.texts
