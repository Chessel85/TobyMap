"""P3-T9a: the world tree on the desktop (SRB-3, ACC-7). The level and position NVDA reads come from the
Information panel's own tree code, PanelTree."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import WorldTreeDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession

SWITZERLAND = {"lat": 46.95, "lon": 7.45, "zoom_m": 100000, "step_m": 10000}


@pytest.fixture
def window(qtbot, continents_pack, tmp_path):
    session = MapSession(packs=[continents_pack], saved_state=dict(SWITZERLAND))
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


def open_box(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_W)
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(WorldTreeDialog) if d.isVisible()]
    return box


def item_named(parent, text):
    return next(parent.child(i) for i in range(parent.childCount()) if parent.child(i).text(0).startswith(text))


def test_w_opens_the_tree_with_world_open_and_the_continents_under_it(window, qtbot):
    box = open_box(window, qtbot)
    assert box.tree.hasFocus() and box.cancel_button.text() == "Cancel"
    assert box.world.text(0) == "World" and box.world.isExpanded() and box.world.childCount() == 7
    assert box.tree.currentItem().text(0) == "Africa, continent"


def test_opening_a_continent_reads_its_countries_and_gives_the_screen_reader_levels(window, qtbot):
    from desktop.panel_tree import PanelAccessible
    from PySide6.QtGui import QAccessible

    box = open_box(window, qtbot)
    europe = item_named(box.world, "Europe")
    assert europe.childCount() == 0   # not read until opened
    box.tree.setCurrentItem(europe)
    qtbot.keyClick(box.tree, Qt.Key.Key_Right)
    assert europe.isExpanded() and item_named(europe, "France").text(0) == "France, country"
    iface = QAccessible.queryAccessibleInterface(box.tree)
    assert isinstance(iface, PanelAccessible)
    path = (0, box.world.indexOfChild(europe), europe.indexOfChild(item_named(europe, "France")))
    item = iface.item_at(path)
    assert item.attributes.level == 3 and item.text(QAccessible.Text.Name) == "France, country"


def test_a_branch_with_nothing_below_is_said_and_stops_being_a_branch(window, qtbot):
    box = open_box(window, qtbot)
    europe = item_named(box.world, "Europe")
    box.tree.setCurrentItem(europe)
    qtbot.keyClick(box.tree, Qt.Key.Key_Right)
    swiss = item_named(europe, "Switzerland")
    box.tree.setCurrentItem(swiss)
    qtbot.keyClick(box.tree, Qt.Key.Key_Right)
    assert swiss.childCount() == 0
    assert "Switzerland has no areas below it in the tree." in window.announcer.texts


def test_enter_goes_to_the_item_and_closes_into_the_map(window, qtbot):
    box = open_box(window, qtbot)
    europe = item_named(box.world, "Europe")
    box.tree.setCurrentItem(europe)
    qtbot.keyClick(box.tree, Qt.Key.Key_Right)
    box.tree.setCurrentItem(item_named(europe, "Germany"))
    qtbot.keyClick(box.tree, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert not box.isVisible() and window.session.current_feature.name == "Germany"


def test_the_world_itself_is_not_a_place_and_cancel_closes(window, qtbot):
    box = open_box(window, qtbot)
    box.tree.setCurrentItem(box.world)
    qtbot.keyClick(box.tree, Qt.Key.Key_Return)
    assert box.isVisible()
    qtbot.mouseClick(box.cancel_button, Qt.MouseButton.LeftButton)
    assert not box.isVisible()
