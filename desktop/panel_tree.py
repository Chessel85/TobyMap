"""The Information panel's tree, with accessibility that NVDA reads levels from (DP135).

Qt's own tree tells screen readers every item is straight under the tree, so
NVDA, which works out a tree item's level by counting the tree items above it,
says "level 1" for every item. This tree keeps Qt's QTreeWidget for drawing,
keys and the mouse, but gives it its own accessibility: the groups are the
tree's children and each group's items are that group's children. NVDA then
says level 1 for a group and level 2 for an item in it. The level is also sent
as an aria level, for other screen readers.

Three things found with the test window, tools/spikes/tree_level/harness.py:

* The tree's accessibility must be a QAccessibleWidget. A plain
  QAccessibleObject has no window, so Qt's UI Automation made every item look
  like the window itself, and NVDA ignored the focus events as repeats.
* interface_cast must answer "none" with a real null pointer: PySide 6.12
  crashes when Python returns None or 0 there.
* Qt's tree sends its own focus and selection events, numbered as a flat list
  of rows. Those would name the wrong item here, so this tree replaces them
  with focus events sent to the item itself.

Items are found by position (group number, item number), not by QTreeWidgetItem.
The window updates the tree in place, so a position keeps its accessible object
while its words change, and accessible objects are never thrown away while Qt
may still hold them.
"""
from __future__ import annotations

import shiboken6
from PySide6.QtCore import QRect
from PySide6.QtGui import QAccessible, QAccessibleAttributesInterface, QAccessibleEvent, QAccessibleInterface
from PySide6.QtWidgets import QAccessibleWidget, QTreeWidget

NULL_POINTER = shiboken6.VoidPtr(0)


class PanelTree(QTreeWidget):
    """A QTreeWidget whose accessibility is nested by group (see the module notes)."""

    def __init__(self):
        install_accessible_factory()
        super().__init__()
        self.expanded.connect(self._expanded_or_collapsed)
        self.collapsed.connect(self._expanded_or_collapsed)

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
    """A group (item number -1) or an item in a group. It has no QObject of its own,
    like the items of Qt's own tree."""

    def __init__(self, panel: "PanelAccessible", group: int, index: int):
        super().__init__()
        self.panel, self.group, self.index = panel, group, index
        self.attributes = LevelAttributes(1 if index < 0 else 2)

    def item(self):
        tree = self.panel.tree
        if self.group >= tree.topLevelItemCount():
            return None
        g = tree.topLevelItem(self.group)
        if self.index < 0:
            return g
        return g.child(self.index) if self.index < g.childCount() else None

    def _shown_children(self) -> int:
        """A closed group shows no items, so it has none to screen readers either."""
        g = self.item()
        if self.index >= 0 or g is None or not g.isExpanded():
            return 0
        return g.childCount()

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
        if self.index < 0 and item.childCount():
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
        return self.panel if self.index < 0 else self.panel.group_interface(self.group)

    def childCount(self):
        return self._shown_children()

    def child(self, i):
        return self.panel.item_at(self.group, i) if self.index < 0 and 0 <= i < self._shown_children() else None

    def indexOfChild(self, child):
        if self.index < 0 and isinstance(child, PanelItemAccessible) and child.group == self.group \
                and 0 <= child.index < self._shown_children():
            return child.index
        return -1

    def childAt(self, x, y):
        for i in range(self._shown_children()):
            kid = self.panel.item_at(self.group, i)
            if kid.rect().contains(x, y):
                return kid
        return None

    def focusChild(self):
        return None

    def interface_cast(self, kind):
        if kind == QAccessible.InterfaceType.AttributesInterface:
            return self.attributes
        return NULL_POINTER


class PanelAccessible(QAccessibleWidget):
    """The tree itself, whose children are the groups."""

    def __init__(self, tree: PanelTree):
        super().__init__(tree, QAccessible.Role.Tree)
        self.tree = tree
        self._items: dict[tuple[int, int], PanelItemAccessible] = {}

    def item_at(self, group: int, index: int) -> PanelItemAccessible:
        key = (group, index)
        iface = self._items.get(key)
        if iface is None:
            iface = self._items[key] = PanelItemAccessible(self, group, index)
        return iface

    def group_interface(self, group: int) -> PanelItemAccessible:
        return self.item_at(group, -1)

    def item_interface(self, item) -> PanelItemAccessible | None:
        parent = item.parent()
        if parent is None:
            group = self.tree.indexOfTopLevelItem(item)
            return self.group_interface(group) if group >= 0 else None
        group = self.tree.indexOfTopLevelItem(parent)
        return self.item_at(group, parent.indexOfChild(item)) if group >= 0 else None

    def role(self):
        return QAccessible.Role.Tree

    def childCount(self):
        return self.tree.topLevelItemCount()

    def child(self, i):
        return self.group_interface(i) if 0 <= i < self.childCount() else None

    def indexOfChild(self, child):
        if isinstance(child, PanelItemAccessible) and child.index < 0 and child.group < self.childCount():
            return child.group
        return -1

    def focusChild(self):
        item = self.tree.currentItem()
        return self.item_interface(item) if item is not None and self.tree.hasFocus() else None

    def childAt(self, x, y):
        for i in range(self.childCount()):
            group = self.group_interface(i)
            if group.rect().contains(x, y):
                return group
            if group.childAt(x, y) is not None:
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
