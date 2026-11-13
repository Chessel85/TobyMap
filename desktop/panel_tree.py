"""The Information panel's tree, with accessibility that NVDA reads levels from (DP135).

Qt's own tree tells screen readers every item is straight under the tree, so
NVDA, which works out a tree item's level by counting the tree items above it,
says "level 1" for every item. This tree keeps Qt's QTreeWidget for drawing,
keys and the mouse, but gives it its own accessibility: the groups are the
tree's children and each group's items are that group's children. NVDA then
says level 1 for a group and level 2 for an item in it, and level 3 for an item
under a heading inside a group, such as a region under Contains' "Regions 13"
(P3-T4a). The level is also sent as an aria level, for other screen readers.

Three things found with the test window, tools/spikes/tree_level/harness.py:

* The tree's accessibility must be a QAccessibleWidget. A plain
  QAccessibleObject has no window, so Qt's UI Automation made every item look
  like the window itself, and NVDA ignored the focus events as repeats.
* interface_cast must answer "none" with a real null pointer: PySide 6.12
  crashes when Python returns None or 0 there.
* Qt's tree sends its own focus and selection events, numbered as a flat list
  of rows. Those would name the wrong item here, so this tree replaces them
  with focus events sent to the item itself.

The layers list uses this tree too (P2-T18b), as Qt's own tree went wrong there in the same
way once a group was closed: a blank line, or silence. Its items are check boxes, so an item
with a check box tells screen readers it is checkable and whether it is ticked, and Space
ticking it sends that change.

Items are found by their path of positions, such as (group number, item number), not by
QTreeWidgetItem.
The window updates the tree in place, so a position keeps its accessible object
while its words change, and accessible objects are never thrown away while Qt
may still hold them.
"""
from __future__ import annotations

import shiboken6
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import (QAccessible, QAccessibleAttributesInterface, QAccessibleEvent, QAccessibleInterface,
                           QAccessibleStateChangeEvent)
from PySide6.QtWidgets import QAccessibleWidget, QTreeWidget, QTreeWidgetItem

NULL_POINTER = shiboken6.VoidPtr(0)


class PanelTree(QTreeWidget):
    """A QTreeWidget whose accessibility is nested by group (see the module notes)."""

    def __init__(self):
        install_accessible_factory()
        super().__init__()
        self.expanded.connect(self._expanded_or_collapsed)
        self.collapsed.connect(self._expanded_or_collapsed)
        self.itemChanged.connect(self._item_changed)

    def accessible(self) -> "PanelAccessible":
        return QAccessible.queryAccessibleInterface(self)

    def currentChanged(self, current, previous):
        # Qt's own version also sends a focus event numbered as a flat row, which
        # names the wrong item in the nested tree. Do its drawing, then send ours.
        if current.isValid():
            self.scrollTo(current)
        self.viewport().update()
        self.announce_current()

    def selectionChanged(self, _selected, _deselected):
        # Qt's own version sends selection events numbered as flat rows. Only redraw.
        self.viewport().update()

    def _expanded_or_collapsed(self, _index):
        # The current group's state changed: say it again, as expanded or collapsed.
        self.announce_current()

    def _item_changed(self, item, _column):
        # A check box ticked or cleared, as by Space in the layers list: say so (P2-T18b).
        if not QAccessible.isActive() or not has_check_box(item):
            return
        iface = self.accessible().item_interface(item)
        if iface is not None:
            changed = QAccessible.State()
            changed.checked = True
            QAccessible.updateAccessibility(QAccessibleStateChangeEvent(iface, changed))

    def announce_current(self) -> None:
        """Tell screen readers the focus is on the current item."""
        if not QAccessible.isActive() or not self.hasFocus():
            return
        item = self.currentItem()
        if item is None:
            return
        iface = self.accessible().item_interface(item)
        if iface is not None:
            QAccessible.updateAccessibility(QAccessibleEvent(iface, QAccessible.Event.Focus))


def has_check_box(item) -> bool:
    """Only an item given a check state has a check box. Qt's flags say every item can be
    ticked, so they would have made NVDA say "not checked" on every Information panel item."""
    return item.data(0, Qt.ItemDataRole.CheckStateRole) is not None


class LevelAttributes(QAccessibleAttributesInterface):
    """An item's level, which Qt passes on as an aria level. A separate object, so the
    pointer Qt gets from interface_cast is the attributes interface itself."""

    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def attributeKeys(self):
        return [QAccessible.Attribute.Level]

    def attributeValue(self, key):
        return self.level if key == QAccessible.Attribute.Level else None


class PanelItemAccessible(QAccessibleInterface):
    """An item of the tree, at a path of positions: (group,) for a group, (group, item) for an item
    in it, and (group, heading, item) for an item under a heading inside a group, such as a region
    under Contains' "Regions 13" (P3-T4a). Its level is the path's length. It has no QObject of its
    own, like the items of Qt's own tree."""

    def __init__(self, panel: "PanelAccessible", path: tuple[int, ...]):
        super().__init__()
        self.panel, self.path = panel, path
        self.attributes = LevelAttributes(len(path))

    def item(self):
        tree = self.panel.tree
        if self.path[0] >= tree.topLevelItemCount():
            return None
        node = tree.topLevelItem(self.path[0])
        for i in self.path[1:]:
            if i >= node.childCount():
                return None
            node = node.child(i)
        return node

    def _shown_children(self) -> int:
        """A closed item shows no items, so it has none to screen readers either."""
        node = self.item()
        if node is None or not node.isExpanded():
            return 0
        return node.childCount()

    # QAccessibleInterface
    def isValid(self):
        return self.item() is not None

    def object(self):
        return None

    def window(self):
        return self.panel.tree.window().windowHandle()

    def setText(self, _t, _text):
        pass

    def role(self):
        return QAccessible.Role.TreeItem

    def text(self, t):
        item = self.item()
        return item.text(0) if item is not None and t == QAccessible.Text.Name else ""

    def state(self):
        s = QAccessible.State()
        item = self.item()
        if item is None:
            s.invalid = True
            return s
        tree = self.panel.tree
        s.focusable = True
        s.selectable = True
        if has_check_box(item):   # a layer's check box (P2-T18b)
            s.checkable = True
            s.checked = item.checkState(0) == Qt.CheckState.Checked
        if can_open(item):
            s.expandable = True
            s.expanded = item.isExpanded()
            s.collapsed = not item.isExpanded()
        if item is tree.currentItem():
            s.selected = True
            s.focused = tree.hasFocus()
        return s

    def rect(self):
        item = self.item()
        if item is None:
            return QRect()
        tree = self.panel.tree
        r = tree.visualItemRect(item)
        return QRect(tree.viewport().mapToGlobal(r.topLeft()), r.size())

    def parent(self):
        return self.panel if len(self.path) == 1 else self.panel.item_at(self.path[:-1])

    def childCount(self):
        return self._shown_children()

    def child(self, i):
        return self.panel.item_at(self.path + (i,)) if 0 <= i < self._shown_children() else None

    def indexOfChild(self, child):
        if isinstance(child, PanelItemAccessible) and child.path[:-1] == self.path                 and 0 <= child.path[-1] < self._shown_children():
            return child.path[-1]
        return -1

    def childAt(self, x, y):
        for i in range(self._shown_children()):
            kid = self.panel.item_at(self.path + (i,))
            if kid.rect().contains(x, y) or kid.childAt(x, y) is not None:
                return kid   # childAt gives the direct child; Qt asks again lower down
        return None

    def focusChild(self):
        return None

    def interface_cast(self, kind):
        if kind == QAccessible.InterfaceType.AttributesInterface:
            return self.attributes
        return NULL_POINTER


def can_open(item) -> bool:
    """An item with items under it, or a group not yet filled, which is filled when it is opened (P3-T4a)."""
    return bool(item.childCount()) or         item.childIndicatorPolicy() == QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator


class PanelAccessible(QAccessibleWidget):
    """The tree itself, whose children are the groups."""

    def __init__(self, tree: PanelTree):
        super().__init__(tree, QAccessible.Role.Tree)
        self.tree = tree
        self._items: dict[tuple[int, ...], PanelItemAccessible] = {}

    def item_at(self, path: tuple[int, ...]) -> PanelItemAccessible:
        iface = self._items.get(path)
        if iface is None:
            iface = self._items[path] = PanelItemAccessible(self, path)
        return iface

    def item_interface(self, item) -> PanelItemAccessible | None:
        path = []
        while item.parent() is not None:
            path.append(item.parent().indexOfChild(item))
            item = item.parent()
        top = self.tree.indexOfTopLevelItem(item)
        if top < 0:
            return None
        return self.item_at((top, *reversed(path)))

    def role(self):
        return QAccessible.Role.Tree

    def childCount(self):
        return self.tree.topLevelItemCount()

    def child(self, i):
        return self.item_at((i,)) if 0 <= i < self.childCount() else None

    def indexOfChild(self, child):
        if isinstance(child, PanelItemAccessible) and len(child.path) == 1 and child.path[0] < self.childCount():
            return child.path[0]
        return -1

    def focusChild(self):
        item = self.tree.currentItem()
        return self.item_interface(item) if item is not None and self.tree.hasFocus() else None

    def childAt(self, x, y):
        for i in range(self.childCount()):
            group = self.item_at((i,))
            if group.rect().contains(x, y) or group.childAt(x, y) is not None:
                return group   # childAt gives the direct child; Qt asks again lower down
        return None


def _accessible_factory(_key, obj):
    if isinstance(obj, PanelTree):
        iface = getattr(obj, "_panel_accessible", None)
        if iface is None:
            # Kept on the tree: Python must keep the item objects alive while Qt uses them.
            iface = obj._panel_accessible = PanelAccessible(obj)
        return iface
    return None


_factory_installed = False


def install_accessible_factory() -> None:
    global _factory_installed
    if not _factory_installed:
        QAccessible.installFactory(_accessible_factory)
        _factory_installed = True
