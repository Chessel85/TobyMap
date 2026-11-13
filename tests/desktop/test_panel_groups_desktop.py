"""The desktop Information panel with the eight groups (P3-T4a): a group not yet filled can be opened,
and is filled when it is; Shift and a number fills its group; an item under a heading inside a group
is level 3 to screen readers (INF-10, DP135, NFR-1)."""
import pytest
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import QApplication

from desktop.window import ITEM_ID
from tests.desktop.test_window import make_window

SWITZERLAND = {"lat": 46.8, "lon": 8.2, "zoom_m": 100000, "step_m": 1000}


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    return make_window(qtbot, test_pack, tmp_path, state=SWITZERLAND)


def top(window, gid):
    return next(window.tree.topLevelItem(i) for i in range(window.tree.topLevelItemCount())
                if window.tree.topLevelItem(i).data(0, ITEM_ID) == f"group:{gid}")


def test_the_panel_has_eight_groups_and_a_closed_one_can_be_opened(window):
    assert window.tree.topLevelItemCount() == 8
    bordering = top(window, "bordering")
    assert bordering.text(0) == "Bordering Switzerland" and bordering.childCount() == 0
    state = window.tree.accessible().item_interface(bordering).state()
    assert state.expandable and state.collapsed     # NVDA says "collapsed", so Right is worth pressing


def test_opening_a_group_fills_it(window):
    bordering = top(window, "bordering")
    bordering.setExpanded(True)
    QApplication.processEvents()
    assert bordering.text(0) == "Bordering Switzerland, 5 items" and bordering.childCount() == 5


def test_shift_5_goes_to_bordering_and_fills_it(window, qtbot):
    window.handle(window.session.press("Shift+5", "map"))
    QApplication.processEvents()
    item = window.tree.currentItem()
    assert item.parent() is top(window, "bordering") and item.parent().childCount() == 5


def test_an_item_under_a_heading_is_level_3(window, monkeypatch):
    """Contains will list types, then their features (P3-T4b): the tree shows any depth, with its level."""
    from mapcore import panel as panel_table

    def contains(current, heading):
        regions = [panel_table.item("osm:r1", "Bern", "Bern", 1.0, 0.0), panel_table.item("osm:r2", "Uri", "Uri", 2.0, 1.0)]
        return [panel_table.heading("regions", "Regions 2", regions)], ""

    monkeypatch.setattr(window.session, "_group_contains", contains)
    group = top(window, "contains")
    group.setExpanded(True)
    QApplication.processEvents()
    heading = group.child(0)
    assert heading.text(0) == "Regions 2" and heading.child(1).text(0) == "Uri"
    heading.setExpanded(True)
    tree = window.tree.accessible()
    iface = tree.item_interface(heading.child(1))
    assert iface.attributes.attributeValue(QAccessible.Attribute.Level) == 3
    assert iface.parent() is tree.item_interface(heading) and tree.item_interface(heading).childCount() == 2
    window.tree.setCurrentItem(heading.child(1))
    assert window.session.panel_item == "osm:r2" and window.session.panel_group == "contains"
    window.tree.setCurrentItem(heading)
    assert window.session.selected is None    # a heading is not a feature
