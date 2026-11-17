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
    assert box.world.text(0) == "World" and box.world.isExpanded() and box.world.childCount() == 9   # seven continents, Disputed areas and Unclaimed areas
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


def test_an_item_with_nothing_below_is_not_a_branch(window, qtbot):
    """P3-T19e, checklist 11.3: the core says which items have nothing under them, so they are never shown as
    branches and NVDA does not say "collapsed"; Right on one does nothing."""
    from PySide6.QtWidgets import QTreeWidgetItem

    box = open_box(window, qtbot)
    europe = item_named(box.world, "Europe")
    box.tree.setCurrentItem(europe)
    qtbot.keyClick(box.tree, Qt.Key.Key_Right)
    swiss = item_named(europe, "Switzerland")
    assert swiss.childIndicatorPolicy() == QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
    assert item_named(europe, "France").childIndicatorPolicy() == QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
    box.tree.setCurrentItem(swiss)
    qtbot.keyClick(box.tree, Qt.Key.Key_Right)
    assert swiss.childCount() == 0 and not swiss.isExpanded()


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


def test_w_opens_the_tree_again_where_the_focus_was(window, qtbot):
    """P3-T19e, checklist 11.5: Europe opened, Switzerland focused, Cancel; W again opens Europe on Switzerland."""
    box = open_box(window, qtbot)
    europe = item_named(box.world, "Europe")
    europe.setExpanded(True)
    QApplication.processEvents()
    box.tree.setCurrentItem(item_named(europe, "Switzerland"))
    box.cancel_button.click()
    QApplication.processEvents()
    window.activateWindow()   # offscreen: the window is not given back the keyboard when a box closes
    window.map.setFocus()
    QApplication.processEvents()
    box = open_box(window, qtbot)
    current = box.tree.currentItem()
    assert current.text(0).startswith("Switzerland") and current.parent().text(0).startswith("Europe")
    assert current.parent().isExpanded()
