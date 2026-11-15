"""P3-T19: fixes from the PO's first pass of the Phase 3 desktop checklist."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import SearchDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession

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


def test_details_is_about_the_search_result_gone_to_after_tab(window, qtbot):
    """13.3: after Enter on a search result, Tab through the panel to Details: Details is about the result."""
    window.focus_region("panel")          # an item of the panel was focused before
    qtbot.keyClick(window.tree, Qt.Key.Key_Down)
    QApplication.processEvents()
    window.map.setFocus()
    qtbot.keyClick(window.map, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(SearchDialog) if d.isVisible()]
    qtbot.keyClicks(box.field, "Itchen")
    qtbot.waitUntil(lambda: box.list.count() > 0, timeout=3000)
    name = box.list.item(0).text().split(",")[0]
    qtbot.keyClick(box.field, Qt.Key.Key_Return)
    QApplication.processEvents()
    window.focus_region("panel")        # Tab from the map to the panel, then to Details, as the PO did
    QApplication.processEvents()
    window.focus_region("details")
    QApplication.processEvents()
    assert window.details.toPlainText().splitlines()[0] == name
