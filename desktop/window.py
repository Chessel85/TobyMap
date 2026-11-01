"""The main window: the four regions (UX section 2) around one map session.

Tab and Shift+Tab move between the map, the Information panel, Details and the
menu bar, wrapping round. Every key and menu entry comes from the command
registry (AD-3), and every word from the core's templates (3.4). This module
only translates: keys and clicks into commands, responses into speech,
painting and focus.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAccessible, QAccessibleTableModelChangeEvent, QAction, QKeySequence
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QMainWindow, QMenu, QPlainTextEdit, QSplitter,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from desktop.announcer import Announcer
from desktop.map_widget import MapWidget
from mapcore.session import MapSession

ITEM_ID = Qt.ItemDataRole.UserRole


def qt_shortcut(key: str) -> QKeySequence:
    """Registry key names to Qt's own names, for menu shortcuts."""
    return QKeySequence(key.replace("Page Up", "PgUp").replace("Page Down", "PgDown"))


class TextDialog(QDialog):
    """A read-only text with a Close button, so Escape is never needed (ACC-7)."""

    def __init__(self, parent, title: str, text: str, close_label: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        self.text = QPlainTextEdit(text)
        self.text.setReadOnly(True)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard
                                          | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text.setTabChangesFocus(True)
        self.text.setAccessibleName(title)
        layout.addWidget(self.text)
        buttons = QDialogButtonBox()
        self.close_button = buttons.addButton(close_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(560, 420)
        self.text.setFocus()


class _MenuTabFilter(QObject):
    """Tab inside an open menu closes it and moves on to the next region."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._window = window

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            forward = event.key() == Qt.Key.Key_Tab and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            obj.hide()
            self._window.menuBar().setActiveAction(None)
            self._window.focus_region("map" if forward else "details")
            return True
        return False


class MainWindow(QMainWindow):
    REGIONS = ("map", "panel", "details", "menu")

    def __init__(self, session: MapSession | None = None, announcer=None):
        super().__init__()
        self.session = session or MapSession(platform="desktop")
        self.words = self.session.words()
        self.setWindowTitle(self.words["window_title"])
        self.announcer = announcer or Announcer(self)
        self._registry = self.session.registry()
        self._dialogs: list[QDialog] = []

        self.map = MapWidget(self, self.session)
        self.tree = QTreeWidget()
        self.tree.setObjectName("panel")
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName(self.words["panel"])
        self.tree.currentItemChanged.connect(self._tree_item_changed)
        # Qt 6.12 does not refresh a tree's accessible items when a group is
        # closed, so NVDA was told focus was on a hidden item and stayed silent
        # (PO feedback on spike S5). Tell Qt to rebuild them on open and close.
        self.tree.expanded.connect(self._tree_layout_changed)
        self.tree.collapsed.connect(self._tree_layout_changed)
        self.details = QPlainTextEdit()
        self.details.setObjectName("details")
        self.details.setReadOnly(True)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard
                                             | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.setTabChangesFocus(True)
        self.details.setAccessibleName(self.words["details"])

        side = QSplitter(Qt.Orientation.Vertical)
        side.addWidget(self.tree)
        side.addWidget(self.details)
        main = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(self.map)
        main.addWidget(side)
        main.setStretchFactor(0, 3)
        main.setStretchFactor(1, 1)
        self.setCentralWidget(main)

        self._menu_filter = _MenuTabFilter(self)
        self.actions_by_name: dict[str, QAction] = {}
        self._build_menus()
        self.menuBar().setAccessibleName(self.words["menu_bar"])
        self.resize(1200, 800)

        self.handle(self.session.start())
        self.map.setFocus()

    # Menus, from the registry -------------------------------------------

    def _build_menus(self):
        global_keys = self._registry["keymap"]["global"]
        for menu in self._registry["menus"]:
            qmenu: QMenu = self.menuBar().addMenu(self._with_access(menu["label"], menu.get("access", "")))
            qmenu.installEventFilter(self._menu_filter)
            for item in menu["items"]:
                name = item["name"]
                if item["key"] and global_keys.get(item["key"]) == name:
                    # Global keys work anywhere, through the action.
                    action = QAction(item["label"], self)
                    action.setShortcut(qt_shortcut(item["key"]))
                    action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
                elif item["key"]:
                    # Map keys are only shown after a tab, and handled by the map
                    # itself, so they never act in the tree or inside a menu.
                    action = QAction(f"{item['label']}\t{item['key']}", self)
                else:
                    action = QAction(item["label"], self)
                action.triggered.connect(lambda _checked=False, n=name: self._menu_command(n))
                qmenu.addAction(action)
                self.actions_by_name[name] = action

    @staticmethod
    def _with_access(label: str, letter: str) -> str:
        """Mark the access letter with "&", so Alt+letter opens the menu."""
        i = label.lower().find(letter.lower()) if letter else -1
        return label if i < 0 else f"{label[:i]}&{label[i:]}"

    def _menu_command(self, name: str):
        self.dispatch(name)
        if self.focusWidget() is None or self.focusWidget() is self.menuBar():
            self.map.setFocus()

    # Focus between the four regions --------------------------------------

    def region_of(self, widget) -> str | None:
        while widget is not None:
            if widget is self.map:
                return "map"
            if widget is self.tree:
                return "panel"
            if widget is self.details:
                return "details"
            if widget is self.menuBar() or isinstance(widget, QMenu):
                return "menu"
            widget = widget.parentWidget()
        return None

    def focus_region(self, region: str):
        if region == "map":
            self.map.setFocus(Qt.FocusReason.TabFocusReason)
        elif region == "panel":
            if self.tree.currentItem() is None and self.tree.topLevelItemCount():
                self.tree.setCurrentItem(self.tree.topLevelItem(0))
            self.tree.setFocus(Qt.FocusReason.TabFocusReason)
        elif region == "details":
            self.details.setFocus(Qt.FocusReason.TabFocusReason)
        elif region == "menu":
            bar = self.menuBar()
            bar.setFocus(Qt.FocusReason.TabFocusReason)
            if bar.actions():
                bar.setActiveAction(bar.actions()[0])

    def focusNextPrevChild(self, forward: bool) -> bool:
        current = self.region_of(self.focusWidget()) or "map"
        i = self.REGIONS.index(current)
        self.focus_region(self.REGIONS[(i + (1 if forward else -1)) % len(self.REGIONS)])
        return True

    # Commands and responses ---------------------------------------------

    def dispatch_key(self, key: str, region: str) -> bool:
        name = self._registry["keymap"].get(region, {}).get(key)
        if not name:
            return False
        self.dispatch(name)
        return True

    def dispatch(self, name: str, **args):
        self.handle(self.session.run(name, **args))

    def handle(self, response):
        for a in response.announcements:
            if a["channel"] == "braille":
                if not self.announcer.braille(a["text"]):
                    self.announcer.speak(a["fallback"], "polite")
            else:
                self.announcer.speak(a["text"], a["priority"])
        if response.redraw:
            self.map.update()
        if response.panel_stale:
            self.map.refresh_name()
            self._fill_tree()
        if response.details_stale:
            self.details.setPlainText(self.session.details())
        if response.focus:
            self._apply_focus(response.focus)
        if response.dialog:
            self._open_dialog(response.dialog)
        if response.action == "exit":
            self.close()

    def _apply_focus(self, focus: dict):
        if focus["region"] == "details":
            self.details.moveCursor(self.details.textCursor().MoveOperation.Start)
            self.details.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        if focus["region"] == "panel":
            group = self._group_item(focus.get("group"))
            if group is not None:
                group.setExpanded(True)
                self.tree.setCurrentItem(group.child(0) if group.childCount() else group)
            self.tree.setFocus(Qt.FocusReason.OtherFocusReason)

    def _open_dialog(self, dialog: dict):
        box = TextDialog(self, dialog["title"], dialog["text"], self.words["close"])
        self._dialogs.append(box)
        box.finished.connect(lambda _r, b=box: self._dialog_closed(b))
        box.open()

    def _dialog_closed(self, box):
        if box in self._dialogs:
            self._dialogs.remove(box)
        self.map.setFocus()

    # The Information panel ------------------------------------------------

    def _group_item(self, group_id: str | None):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, ITEM_ID) == f"group:{group_id}":
                return item
        return None

    def _fill_tree(self):
        expanded = {self.tree.topLevelItem(i).data(0, ITEM_ID)
                    for i in range(self.tree.topLevelItemCount()) if self.tree.topLevelItem(i).isExpanded()}
        self.tree.blockSignals(True)
        try:
            self.tree.clear()
            for group in self.session.panel():
                g = QTreeWidgetItem([group["label"]])
                g.setData(0, ITEM_ID, f"group:{group['id']}")
                for item in group["items"]:
                    child = QTreeWidgetItem([item["label"]])
                    child.setData(0, ITEM_ID, item["id"])
                    g.addChild(child)
                if not group["items"] and group["empty"]:
                    child = QTreeWidgetItem([group["empty"]])
                    child.setData(0, ITEM_ID, None)
                    g.addChild(child)
                self.tree.addTopLevelItem(g)
                g.setExpanded(g.data(0, ITEM_ID) in expanded)
        finally:
            self.tree.blockSignals(False)

    def _tree_layout_changed(self, *_args):
        QAccessible.updateAccessibility(QAccessibleTableModelChangeEvent(
            self.tree, QAccessibleTableModelChangeEvent.ModelChangeType.ModelReset))

    def _tree_item_changed(self, current, _previous):
        item_id = current.data(0, ITEM_ID) if current is not None else None
        if item_id is not None and str(item_id).startswith("group:"):
            item_id = None
        self.dispatch("panel.select", item=item_id)
