"""What the desktop window tells screen readers, from the PO's NVDA test of spike S5.

* The map is a pane named after the place under the centre, so NVDA says
  "United Kingdom" when Tab arrives, not "Map grouping".
* The tree's accessible items stay right after a group is closed. Qt 6.12
  left closed groups' children in place, so NVDA stayed silent.

Qt only keeps its accessible items up to date while accessibility is active,
so these tests switch it on, and off again afterwards. No screen reader is
contacted.
"""
import pytest
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    QAccessible.setActive(True)
    session = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    yield w
    QAccessible.setActive(False)


def names(widget):
    iface = QAccessible.queryAccessibleInterface(widget)
    return [iface.child(i).text(QAccessible.Text.Name) for i in range(iface.childCount())]


def focus_name(widget):
    child = QAccessible.queryAccessibleInterface(widget).focusChild()
    return child.text(QAccessible.Text.Name) if child else None


def test_map_is_a_pane_named_after_the_place(window):
    iface = QAccessible.queryAccessibleInterface(window.map)
    assert iface.role() == QAccessible.Role.Pane
    assert iface.text(QAccessible.Text.Name) == "Kent, England, United Kingdom. Press F1 for keys."   # the start (P2-T17d)


def test_map_name_changes_only_while_it_does_not_have_focus(window, qtbot):
    window.map.setFocus()
    QApplication.processEvents()
    window.dispatch("move.south")
    assert window.map.accessibleName() == "Kent, England, United Kingdom. Press F1 for keys."  # unchanged while focused
    window.focus_region("panel")
    QApplication.processEvents()
    assert window.map.accessibleName() == "North Atlantic Ocean"           # updated on leaving


def test_tree_items_are_nested_in_their_groups(window):
    """NVDA counts the tree items above an item for its level (DP135), so a group's
    items must be its children, not the tree's."""
    tree = window.tree
    tree.topLevelItem(0).setExpanded(True)
    QApplication.processEvents()
    assert names(tree)[:2] == ["Within, 3 items", "Nearby, 1 item"]   # with the count (P2-T17k)
    within = QAccessible.queryAccessibleInterface(tree).child(0)
    kent = within.child(0)
    assert within.role() == QAccessible.Role.TreeItem
    assert [within.child(i).text(QAccessible.Text.Name).split(",")[0] for i in range(within.childCount())][:3] == \
        ["Kent", "England", "United Kingdom"]
    assert kent.parent().text(QAccessible.Text.Name) == "Within, 3 items"
    assert kent.parent().parent().role() == QAccessible.Role.Tree
    assert within.state().expanded and not kent.state().expandable


def test_tree_focus_is_the_current_item_at_any_level(window):
    tree = window.tree
    tree.setFocus()
    tree.setCurrentItem(tree.topLevelItem(0).child(1))
    QApplication.processEvents()
    assert focus_name(tree) == "England, centre 140 kilometres west"
    tree.setCurrentItem(tree.topLevelItem(1))
    QApplication.processEvents()
    assert focus_name(tree) == "Nearby, 1 item"


def test_tree_items_are_right_after_a_group_is_closed(window):
    tree = window.tree
    tree.setFocus()
    tree.setCurrentItem(tree.topLevelItem(1))
    within = tree.topLevelItem(0)
    within.setExpanded(True)
    QApplication.processEvents()
    group = QAccessible.queryAccessibleInterface(tree).child(0)
    assert group.childCount() == within.childCount() > 0
    within.setExpanded(False)
    QApplication.processEvents()
    assert group.childCount() == 0
    assert group.state().collapsed
    assert focus_name(tree) == "Nearby, 1 item"


def test_alt_letters_open_the_menus(window):
    texts = [a.text() for a in window.menuBar().actions()]
    assert texts == ["&Map", "&Speech", "Se&ttings", "&Help"]
