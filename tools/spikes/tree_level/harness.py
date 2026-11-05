r"""Test window: can NVDA hear the level of an item in a tree? (DP135, checklist 12.1)

Qt's Windows accessibility never sends a level for the items of a QTreeWidget, so
NVDA hears every item in the Information panel as level 1. Qt can send a level
only as an "aria level" (UI Automation's AriaProperties, "level=2"), and only for
accessibility objects that the program writes itself. This window tries that.

It has two trees with the same items, and a Close button:

1. Standard tree: Qt's own QTreeWidget, as the Information panel is today.
2. Own tree: drawn by this script, with accessibility written in Python. Its
   items are nested (England inside Within), because NVDA works out a tree item's
   level by counting the tree items above it. Qt's own tree reports every item
   straight under the tree, so NVDA says level 1 for all of them. The aria level
   is still sent, for other screen readers.

Run:   .venv\Scripts\python.exe tools\spikes\tree_level\harness.py

Tab moves between the trees and the button. Up and Down move through items.
Listen for "level 1" and "level 2" in each tree.
"""
from __future__ import annotations

import os
import sys

import shiboken6
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import (QAccessible, QAccessibleAttributesInterface, QAccessibleEvent, QAccessibleInterface,
                           QPainter)
from PySide6.QtWidgets import (QAccessibleWidget, QApplication, QDialog, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                               QWidget)

NULL_POINTER = shiboken6.VoidPtr(0)
TITLE = "TobyMap tree level test"
GROUPS = [("Within", ["England", "United Kingdom"]), ("Nearby", ["France, 40 kilometres south-east", "Belgium, 120 kilometres east"])]
ROW_HEIGHT = 24


class OwnTree(QWidget):
    """A simple tree that is always open: groups at level 1, their items at level 2."""

    def __init__(self, name: str):
        super().__init__()
        self.setObjectName("own_tree")
        self.setAccessibleName(name)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.rows: list[tuple[str, int, int, int]] = []   # (text, level, position in set, size of set)
        for gi, (group, items) in enumerate(GROUPS):
            self.rows.append((group, 1, gi + 1, len(GROUPS)))
            for ii, item in enumerate(items):
                self.rows.append((item, 2, ii + 1, len(items)))
        self.current = 0
        self.setMinimumHeight(ROW_HEIGHT * len(self.rows) + 4)

    def row_rect(self, i: int) -> QRect:
        level = self.rows[i][1]
        return QRect(4 + 20 * (level - 1), 2 + i * ROW_HEIGHT, self.width() - 8, ROW_HEIGHT)

    def paintEvent(self, _event):
        p = QPainter(self)
        for i, (text, _level, _pos, _size) in enumerate(self.rows):
            r = self.row_rect(i)
            if i == self.current:
                p.fillRect(r, self.palette().highlight() if self.hasFocus() else self.palette().midlight())
            p.drawText(r.adjusted(4, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, text)

    def keyPressEvent(self, event):
        step = {Qt.Key.Key_Up: -1, Qt.Key.Key_Down: 1}.get(Qt.Key(event.key()))
        if step is None:
            return super().keyPressEvent(event)
        new = max(0, min(len(self.rows) - 1, self.current + step))
        if new != self.current:
            self.current = new
            self.update()
            self.announce_focus()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.announce_focus()

    def announce_focus(self):
        """Tell screen readers the focus is on the current item. The items are nested, so
        a child number on the tree cannot name them: the event goes to the item itself."""
        tree_iface = QAccessible.queryAccessibleInterface(self)
        event = QAccessibleEvent(tree_iface.all[self.current], QAccessible.Event.Focus)
        QAccessible.updateAccessibility(event)


class LevelAttributes(QAccessibleAttributesInterface):
    """An item's attributes: only its level. A separate object, so the pointer Qt gets
    from interface_cast is the attributes interface itself."""

    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def attributeKeys(self):
        return [QAccessible.Attribute.Level]

    def attributeValue(self, key):
        return self.level if key == QAccessible.Attribute.Level else None


class OwnTreeItemAccessible(QAccessibleInterface):
    """One item of OwnTree, with its level as an attribute (Qt passes it on as aria level).
    Like Qt's own tree items, it has no QObject of its own."""

    def __init__(self, tree: OwnTree, index: int, parent_iface):
        super().__init__()
        self.tree, self.index, self._parent = tree, index, parent_iface
        self.attributes = LevelAttributes(tree.rows[index][1])
        self.kids: list[OwnTreeItemAccessible] = []   # nested items: NVDA counts tree items above for the level

    # QAccessibleInterface
    def isValid(self):
        return True

    def object(self):
        return None

    def window(self):
        return self.tree.window().windowHandle()

    def setText(self, _t, _text):
        pass

    def focusChild(self):
        return None

    def role(self):
        return QAccessible.Role.TreeItem

    def text(self, t):
        if t == QAccessible.Text.Name:
            return self.tree.rows[self.index][0]
        return ""

    def state(self):
        s = QAccessible.State()
        s.focusable = True
        s.selectable = True
        if self.tree.rows[self.index][1] == 1:
            s.expandable = True
            s.expanded = True
        if self.index == self.tree.current:
            s.selected = True
            s.focused = self.tree.hasFocus()
        return s

    def rect(self):
        r = self.tree.row_rect(self.index)
        return QRect(self.tree.mapToGlobal(r.topLeft()), r.size())

    def parent(self):
        return self._parent

    def childCount(self):
        return len(self.kids)

    def child(self, i):
        return self.kids[i] if 0 <= i < len(self.kids) else None

    def indexOfChild(self, child):
        return self.kids.index(child) if child in self.kids else -1

    def childAt(self, x, y):
        for kid in self.kids:
            if kid.rect().contains(x, y):
                return kid
        return None

    def interface_cast(self, kind):
        if kind == QAccessible.InterfaceType.AttributesInterface:
            return self.attributes
        # A null pointer. PySide 6.12 crashes converting None or 0 (shiboken VoidPtr::getSize).
        return NULL_POINTER


class OwnTreeAccessible(QAccessibleWidget):
    """The tree itself: role Tree, with one child per row.

    It must be a QAccessibleWidget, not a plain QAccessibleObject: Qt's UI Automation
    treats an element as the root of a window when its parent reports a different
    window, and QAccessibleObject reports none. Then every item had the window's own
    runtime ID, and NVDA dropped each focus event as a repeat."""

    def __init__(self, tree: OwnTree):
        super().__init__(tree, QAccessible.Role.Tree)
        self.tree = tree
        # Every row, in row order; only the groups (level 1) are the tree's own children,
        # and each group's items are its children. NVDA works out an item's level by
        # counting the tree items above it, and ignores the aria level.
        self.all: list[OwnTreeItemAccessible] = []
        self.items: list[OwnTreeItemAccessible] = []
        for i, (_text, level, _pos, _size) in enumerate(tree.rows):
            if level == 1:
                item = OwnTreeItemAccessible(tree, i, self)
                self.items.append(item)
            else:
                group = self.items[-1]
                item = OwnTreeItemAccessible(tree, i, group)
                group.kids.append(item)
            self.all.append(item)

    def isValid(self):
        return True

    def role(self):
        return QAccessible.Role.Tree

    def text(self, t):
        return self.tree.accessibleName() if t == QAccessible.Text.Name else ""

    def state(self):
        s = QAccessible.State()
        s.focusable = True
        s.focused = self.tree.hasFocus()
        return s

    def childCount(self):
        return len(self.items)

    def child(self, i):
        return self.items[i] if 0 <= i < len(self.items) else None

    def indexOfChild(self, child):
        return self.items.index(child) if child in self.items else -1

    def focusChild(self):
        return self.all[self.tree.current] if self.tree.hasFocus() else None

    def childAt(self, x, y):
        for item in self.items:
            if item.rect().contains(x, y):
                return item
            for kid in item.kids:
                if kid.rect().contains(x, y):
                    return item   # childAt gives the direct child; Qt asks again lower down
        return None


_keep: dict[int, OwnTreeAccessible] = {}   # Python must keep the interfaces alive for Qt


def factory(class_name: str, obj):
    if isinstance(obj, OwnTree):
        iface = _keep.get(id(obj))
        if iface is None:
            iface = _keep[id(obj)] = OwnTreeAccessible(obj)
        return iface
    return None


def build() -> QDialog:
    dialog = QDialog()
    dialog.setWindowTitle(TITLE)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("Two trees with the same items. Listen for level 1 and level 2. Tab moves between them."))
    standard = QTreeWidget()
    standard.setHeaderHidden(True)
    standard.setAccessibleName("Standard tree")
    for group, items in GROUPS:
        g = QTreeWidgetItem([group])
        standard.addTopLevelItem(g)
        for item in items:
            g.addChild(QTreeWidgetItem([item]))
        g.setExpanded(True)
    standard.setCurrentItem(standard.topLevelItem(0))
    layout.addWidget(standard)
    layout.addWidget(OwnTree("Own tree"))
    close = QPushButton("Close")
    close.clicked.connect(dialog.reject)
    layout.addWidget(close)
    dialog.resize(480, 420)
    return dialog


def main(argv: list[str]) -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    QAccessible.installFactory(factory)
    dialog = build()
    dialog.show()
    if "--self-drive" in argv:   # for Claude Code's check: step down each tree with real key events, then close
        from PySide6.QtCore import QTimer
        from PySide6.QtTest import QTest

        standard = dialog.findChild(QTreeWidget)
        tree = dialog.findChild(OwnTree)
        dialog.activateWindow()
        steps = [lambda: standard.setFocus()] + [lambda: QTest.keyClick(standard, Qt.Key.Key_Down)] * 3
        steps += [lambda: tree.setFocus()] + [lambda: QTest.keyClick(tree, Qt.Key.Key_Down)] * 3
        for i, step in enumerate(steps):
            QTimer.singleShot(1500 + 1000 * i, step)
        QTimer.singleShot(1500 + 1000 * len(steps) + 500, dialog.reject)
    # Closing ends the program at once: Qt tidying up the accessibility objects
    # that Python made crashed it. Finding a clean way is part of the real work.
    dialog.finished.connect(lambda _result: os._exit(0))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
