"""The dialogs of the desktop shell (UX section 14, ACC-7).

Every dialog has a Close, OK or Cancel button, so Escape is never needed. What
is in the settings dialog comes from the core (session.settings_schema()), so
the web version shows the same settings.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                               QDoubleSpinBox, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QTabWidget,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from desktop.keys import key_name
from desktop.panel_tree import PanelTree
from desktop.unavailable_button import UnavailableButton


def button_row(parent_layout, labels: list[str], default: bool = True, cls=QPushButton) -> list[QPushButton]:
    """Buttons in a row, in the order given, which is also their Tab order. A
    button with the focus takes Enter, as Space does: Cancel cancels (P2-T17b,
    ACC-7). Anywhere else in the dialog, Enter presses the first button, OK,
    unless `default` is False, as for a row with no OK. (QDialogButtonBox put
    Cancel before OK in the Tab order: PO feedback on checklist 11, second pass.) `cls` is the kind of
    button, such as UnavailableButton."""
    row = QHBoxLayout()
    row.addStretch(1)
    buttons = []
    for label in labels:
        b = cls(label)
        b.setAutoDefault(True)   # Qt's word for "takes Enter while it has the focus"
        row.addWidget(b)
        buttons.append(b)
    if default:
        buttons[0].setDefault(True)
    for a, b in zip(buttons, buttons[1:]):
        QWidget.setTabOrder(a, b)
    parent_layout.addLayout(row)
    return buttons



class _HomeEnd:
    """In a number box, Home sets the largest value, as Home is above End on the keyboard, and End
    the smallest (P2-T17m, the PO's note on desktop checklist 12.4). A plain spin box moved the
    text cursor instead."""

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.NoModifier and event.key() in (Qt.Key.Key_Home, Qt.Key.Key_End):
            self.setValue(self.maximum() if event.key() == Qt.Key.Key_Home else self.minimum())
            self.selectAll()
            return
        super().keyPressEvent(event)


class NumberBox(_HomeEnd, QSpinBox):
    """A number box in whole numbers."""


class DecimalBox(_HomeEnd, QDoubleSpinBox):
    """A number box whose setting has a step with a fraction, such as the beacon's 0.5 seconds. A
    whole number box showed 0 for 0.5 and could not be set to it (P2-T17m)."""

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
        # One line of text, one line on screen, so the screen reader moves a line
        # at a time (PO feedback on checklist 2, second pass).
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.text)
        buttons = QDialogButtonBox()
        self.close_button = buttons.addButton(close_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(720, 460)
        self.text.setFocus()


class ListDialog(QDialog):
    """A list of lines, one per item, with a Close button: the location history (NAV-10)."""

    def __init__(self, parent, title: str, lines: list[str], close_label: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.addItems(lines)
        self.list.setAccessibleName(title)
        if lines:
            self.list.setCurrentRow(0)
        layout.addWidget(self.list)
        buttons = QDialogButtonBox()
        self.close_button = buttons.addButton(close_label, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(560, 420)
        self.list.setFocus()


class HistoryDialog(ListDialog):
    """The location history, newest first, opened on where you are now. Enter on a place goes
    there (NAV-10, DP158); if the core refuses, it says why and the list stays open. A Help line
    above the list says what Enter does."""

    def __init__(self, parent, title: str, lines: list[str], close_label: str, help_text: str, go, speak=None,
                 current: int = 0):
        super().__init__(parent, title, lines, close_label)
        if 0 <= current < len(lines):
            self.list.setCurrentRow(current)
        self._go, self._speak = go, speak
        self.response = None
        self.help = QLabel(help_text)
        self.help.setWordWrap(True)
        self.list.setAccessibleDescription(help_text)
        self.message = QLabel("")
        self.layout().insertWidget(0, self.help)
        self.layout().insertWidget(2, self.message)
        self.list.itemActivated.connect(lambda _item: self.go_to_selected())

    def go_to_selected(self):
        if self.response is not None:   # Enter reaches both the list and the dialog: go once
            return
        row = self.list.currentRow()
        response = self._go(row)
        if response.error:
            self.message.setText(response.error)
            self.message.setAccessibleDescription(response.error)
            if self._speak is not None:
                self._speak(response.error)
            self.list.setFocus()
        else:
            self.response = response
            self.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):   # Enter goes there and never just closes
            self.go_to_selected()
            return
        super().keyPressEvent(event)


class SearchDialog(QDialog):
    """Search (P3-T8c, P3-T8d; SRB-1, SRB-2, NAV-8): a field, a choice of where to search, and the results
    below, found after a short pause in typing. Down in the field moves into the list; Enter on a result,
    or in the field, goes to the selected result and closes. Go and Cancel are buttons (ACC-7). The core
    does the searching and gives every word; `run` is session.run."""

    def __init__(self, parent, dialog: dict, run, speak=None):
        from PySide6.QtCore import QTimer

        super().__init__(parent)
        self._run, self._speak, self._dialog = run, speak, dialog
        self._ids: list[str] = []
        self.response = None
        self.setWindowTitle(dialog["title"])
        layout = QVBoxLayout(self)
        label = QLabel(dialog["label"])
        layout.addWidget(label)
        self.field = QLineEdit()
        self.field.setAccessibleName(dialog["label"])
        self.field.setAccessibleDescription(dialog["help"])
        label.setBuddy(self.field)
        layout.addWidget(self.field)
        scope_label = QLabel(dialog["scope_label"])
        layout.addWidget(scope_label)
        self.scope = QComboBox()
        self.scope.setAccessibleName(dialog["scope_label"])
        for s in dialog["scopes"]:
            self.scope.addItem(s["label"], s["id"])
        scope_label.setBuddy(self.scope)
        layout.addWidget(self.scope)
        results_label = QLabel(dialog["results_label"])
        layout.addWidget(results_label)
        self.list = QListWidget()
        self.list.setAccessibleName(dialog["results_label"])
        results_label.setBuddy(self.list)
        layout.addWidget(self.list)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.go_button, self.cancel_button = button_row(layout, [dialog["go_label"], dialog["cancel"]])
        self.go_button.setAutoDefault(False)
        self.go_button.setDefault(False)
        self.go_button.clicked.connect(self.go_to_selected)
        self.cancel_button.clicked.connect(self.reject)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(int(dialog["delay_ms"]))
        self._timer.timeout.connect(self.search_now)
        self.field.textChanged.connect(lambda _t: self._timer.start())
        self.scope.currentIndexChanged.connect(lambda _i: self._timer.start())
        self.field.installEventFilter(self)
        self.list.installEventFilter(self)
        self.list.itemActivated.connect(lambda _item: self.go_to_selected())
        self.resize(560, 480)
        self.field.setFocus()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.Type.KeyPress and not event.modifiers():
            key = event.key()
            if obj is self.field and key == Qt.Key.Key_Down:
                self._flush()
                if self.list.count():
                    self.list.setCurrentRow(max(0, self.list.currentRow()))
                    self.list.setFocus()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and obj in (self.field, self.list):
                self.go_to_selected()
                return True
        return super().eventFilter(obj, event)

    def _flush(self) -> None:
        """Search at once if a search is waiting for the pause to end."""
        if self._timer.isActive():
            self._timer.stop()
            self.search_now()

    def search_now(self) -> None:
        response = self._run(self._dialog["query"], text=self.field.text(), scope=self.scope.currentData())
        found = response.found or {"lines": [], "ids": [], "none": ""}
        self._ids = list(found["ids"])
        self.list.clear()
        self.list.addItems(found["lines"])
        if self._ids:
            self.list.setCurrentRow(0)
        self.message.setText(found["none"])
        self.message.setAccessibleDescription(found["none"])
        if found["none"] and self._speak is not None:
            self._speak(found["none"])

    def go_to_selected(self) -> None:
        if self.response is not None:   # Enter can reach the list and the dialog: go once
            return
        self._flush()
        row = self.list.currentRow()
        if not 0 <= row < len(self._ids):
            return
        response = self._run(self._dialog["go"], id=self._ids[row])
        if response.error:
            self.message.setText(response.error)
            if self._speak is not None:
                self._speak(response.error)
            return
        self.response = response
        self.accept()


class QueryDialog(QDialog):
    """The query builder (P3-T10b, INF-9): three lists, Find (layers), Relation and Of, a distance field shown
    only when the chosen relation has a distance, and OK and Cancel (ACC-7). OK runs the core's query.run with
    the chosen ids; an error is shown and spoken and the form stays open, an answer closes it. The core gives
    every word; `run` is session.run."""

    def __init__(self, parent, dialog: dict, run, speak=None):
        super().__init__(parent)
        self._run, self._speak, self._dialog = run, speak, dialog
        self.response = None
        self.setWindowTitle(dialog["title"])
        layout = QVBoxLayout(self)
        self.help = QLabel(dialog["help"])
        self.help.setWordWrap(True)
        layout.addWidget(self.help)
        self.layer_list = self._list(layout, dialog["find_label"], dialog["layers"])
        self.relation_list = self._list(layout, dialog["relation_label"], dialog["relations"])
        self.of_list = self._list(layout, dialog["of_label"], dialog["of"])
        self.distance_label = QLabel(dialog["distance_label"])
        self.distance = QLineEdit(str(dialog["distance"]))
        self.distance.setAccessibleName(dialog["distance_label"])
        self.distance_label.setBuddy(self.distance)
        for box, key in ((self.layer_list, "layer"), (self.relation_list, "relation"), (self.of_list, "of")):
            self._select(box, (dialog.get("chosen") or {}).get(key))   # coming back from search (P3-T28q)
        layout.addWidget(self.distance_label)
        layout.addWidget(self.distance)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.ok_button, self.cancel_button = button_row(layout, [dialog["ok"], dialog["cancel"]])
        self.ok_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)
        self.distance.returnPressed.connect(self.apply)
        self.relation_list.currentRowChanged.connect(lambda _r: self._show_distance())
        self._show_distance()
        self.resize(560, 560)
        self.layer_list.setFocus()

    @staticmethod
    def _list(layout, label_text: str, items: list[dict]) -> QListWidget:
        label = QLabel(label_text)
        box = QListWidget()
        box.setAccessibleName(label_text)
        label.setBuddy(box)
        for item in items:
            row = QListWidgetItem(item["label"])
            row.setData(Qt.ItemDataRole.UserRole, item["id"])
            box.addItem(row)
        if items:
            box.setCurrentRow(0)
        layout.addWidget(label)
        layout.addWidget(box)
        return box

    @staticmethod
    def _select(box: QListWidget, identifier) -> None:
        for row in range(box.count()):
            if identifier and box.item(row).data(Qt.ItemDataRole.UserRole) == identifier:
                box.setCurrentRow(row)

    def _show_distance(self) -> None:
        row = self.relation_list.currentRow()
        wanted = 0 <= row < len(self._dialog["relations"]) and bool(self._dialog["relations"][row].get("distance"))
        self.distance_label.setVisible(wanted)
        self.distance.setVisible(wanted)

    @staticmethod
    def _chosen(box: QListWidget) -> str:
        item = box.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else ""

    def apply(self) -> None:
        if self.response is not None:   # Enter can arrive twice: answer once
            return
        args = {"layer": self._chosen(self.layer_list), "relation": self._chosen(self.relation_list),
                "of": self._chosen(self.of_list)}
        if self.distance.isVisible():
            args["distance"] = self.distance.text()
        response = self._run(self._dialog["run"], **args)
        if response.error:
            self.message.setText(response.error)
            self.message.setAccessibleDescription(response.error)
            if self._speak is not None:
                self._speak(response.error)
            return
        self.response = response
        self.accept()


class WorldTreeDialog(QDialog):
    """The world tree (P3-T9a, SRB-3): World, then its continents, countries and so on, in the Information
    panel's own tree, so NVDA says each item's level and position. A branch is read from the core, with the
    command in dialog["children"], only when it is opened. Enter, or Go, on an item goes there and closes;
    Cancel closes (ACC-7). The core gives every word; `run` is session.run."""

    def __init__(self, parent, dialog: dict, run, speak=None):
        super().__init__(parent)
        self._run, self._speak, self._dialog = run, speak, dialog
        self.response = None
        self.setWindowTitle(dialog["title"])
        layout = QVBoxLayout(self)
        self.tree = PanelTree()
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName(dialog["title"])
        self.tree.setAccessibleDescription(dialog["help"])
        layout.addWidget(self.tree)
        root = dialog["root"]
        self.world = self._item(root["label"], root["id"])
        self.tree.addTopLevelItem(self.world)
        self._fill(self.world, root["items"])
        self.world.setExpanded(True)
        self.go_button, self.cancel_button = button_row(layout, [dialog["go_label"], dialog["cancel"]])
        self.go_button.setAutoDefault(False)
        self.go_button.setDefault(False)
        self.go_button.clicked.connect(self.go_to_selected)
        self.cancel_button.clicked.connect(self.reject)
        self.tree.itemExpanded.connect(self._opened)
        self.tree.itemActivated.connect(lambda _item, _c: self.go_to_selected())
        self.tree.installEventFilter(self)
        first = self.world.child(0)
        self.tree.setCurrentItem(self._reopen(dialog) or (first if first is not None else self.world))
        # Each move tells the core where the focus is, so W opens the tree there again (P3-T19e).
        self.tree.currentItemChanged.connect(self._moved)
        self.resize(560, 480)
        self.tree.setFocus()

    def _reopen(self, dialog: dict) -> QTreeWidgetItem | None:
        """The branches open when the tree last closed, with their items from the core, and the item that had
        the focus; None the first time."""
        node = self.world
        for branch in dialog.get("open") or []:
            child = next((node.child(i) for i in range(node.childCount())
                          if node.child(i).data(0, Qt.ItemDataRole.UserRole) == branch["id"]), None)
            if child is None:
                return None
            if not child.childCount():
                child.setData(0, Qt.ItemDataRole.UserRole + 1, True)   # read already
                self._fill(child, branch["items"])
            child.setExpanded(True)
            node = child
        focus = dialog.get("focus")
        if not focus:
            return None
        if node.data(0, Qt.ItemDataRole.UserRole) == focus:
            return node
        return next((node.child(i) for i in range(node.childCount())
                     if node.child(i).data(0, Qt.ItemDataRole.UserRole) == focus), None)

    def _moved(self, current, _previous) -> None:
        if current is None or not self._dialog.get("at"):
            return
        path = []
        while current is not None:
            path.insert(0, current.data(0, Qt.ItemDataRole.UserRole))
            current = current.parent()
        self._run(self._dialog["at"], path=path)

    @staticmethod
    def _item(label: str, identifier: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, identifier)
        return item

    def _fill(self, parent: QTreeWidgetItem, nodes: list[dict]) -> None:
        for node in nodes:
            child = self._item(node["label"], node["id"])
            # Opened when asked for: a branch is read only then (SRB-3). An item the core knows has nothing
            # under it is not a branch, so NVDA does not say "collapsed" (P3-T19e).
            child.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator if node.get("leaf")
                                          else QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            parent.addChild(child)

    def _opened(self, item: QTreeWidgetItem) -> None:
        if item.childCount() or item is self.world or item.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        item.setData(0, Qt.ItemDataRole.UserRole + 1, True)   # read once
        branch = self._run(self._dialog["children"], id=item.data(0, Qt.ItemDataRole.UserRole)).branch or {}
        self._fill(item, branch.get("items", []))
        if not item.childCount():   # nothing below it: not a branch after all, and it is said
            item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)
            if branch.get("none") and self._speak is not None:
                self._speak(branch["none"])

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if obj is self.tree and event.type() == QEvent.Type.KeyPress and not event.modifiers() \
                and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.go_to_selected()
            return True
        return super().eventFilter(obj, event)

    def go_to_selected(self) -> None:
        item = self.tree.currentItem()
        if self.response is not None or item is None:   # Enter can arrive twice: go once
            return
        response = self._run(self._dialog["go"], id=item.data(0, Qt.ItemDataRole.UserRole))
        if response.error:
            if self._speak is not None:
                self._speak(response.error)
            return
        self.response = response
        self.accept()


class InputDialog(QDialog):
    """A box to type in, with OK and Cancel (ACC-7): a bearing or coordinates. The core reads what
    was typed; if it can't, its words open in a message box with an OK button, and after OK you are
    back in the box with your text (P2-T17o, the PO's notes on desktop checklist 3.5 and 5.3). The
    screen reader reads the message box as it opens, so the words are not spoken as well."""

    def __init__(self, parent, dialog: dict, submit):
        super().__init__(parent)
        self._submit = submit
        self._ok_word = dialog["ok"]
        self.response = None
        self.error_box: QMessageBox | None = None
        self.setWindowTitle(dialog["title"])
        layout = QVBoxLayout(self)
        label = QLabel(dialog["label"])
        layout.addWidget(label)
        self.field = QLineEdit()
        self.field.setAccessibleName(dialog["label"])
        label.setBuddy(self.field)
        layout.addWidget(self.field)
        self.help = QLabel(dialog["help"])
        self.help.setWordWrap(True)
        if dialog["help"]:   # neither box has one now: their labels are enough (the PO, P2-T17o)
            self.field.setAccessibleDescription(dialog["help"])
            layout.addWidget(self.help)
        self.ok_button, self.cancel_button = button_row(layout, [dialog["ok"], dialog["cancel"]])
        self.ok_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)
        self.field.returnPressed.connect(self.apply)
        self.resize(520, 140)
        self.field.setFocus()

    def apply(self):
        if self.error_box is not None:   # Enter can reach the box twice: one message box at a time
            return
        response = self._submit(self.field.text())
        if response.error:
            self._show_error(response.error)
        else:
            self.response = response
            self.accept()

    def _show_error(self, text: str) -> None:
        """The core's words in a message box, titled as this box, with one OK button. It is opened,
        not run, so nothing waits on it; OK, Enter or Space close it, and the focus comes back to
        the field with the text chosen, so typing replaces it."""
        box = QMessageBox(QMessageBox.Icon.Warning, self.windowTitle(), text, QMessageBox.StandardButton.NoButton, self)
        ok = box.addButton(self._ok_word, QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(ok)
        box.setEscapeButton(ok)
        box.finished.connect(self._error_closed)
        self.error_box = box
        box.open()

    def _error_closed(self, _result) -> None:
        self.error_box.deleteLater()
        self.error_box = None
        self.field.setFocus()
        self.field.selectAll()


class BookmarkDialog(QDialog):
    """The bookmark dialog (P4-T8b, USR-1, DP219), in Tab order: Name (filled and numbered), Feature and Coordinates
    (read-only, but reached by Tab so the screen reader reads them), the Bookmark list box on the list used last,
    New list, OK and Cancel (ACC-7). Every word and value comes from the core; OK runs its bookmark.add with the
    name and the chosen list, and a refusal opens in a message box with an OK button, as InputDialog's does.
    New list asks for a name in an InputDialog and the core adds it to the list box, chosen. `run` is session.run."""

    def __init__(self, parent, dialog: dict, run):
        super().__init__(parent)
        self._dialog, self._run = dialog, run
        words = dialog["words"]
        self.response = None
        self.input_box: InputDialog | None = None
        self.error_box: QMessageBox | None = None
        self.setWindowTitle(dialog["title"])
        layout = QVBoxLayout(self)
        self.help = QLabel(dialog["help"])
        self.help.setWordWrap(True)
        layout.addWidget(self.help)
        self.name = self._field(layout, words["name_label"], dialog["name"], False)
        self.feature = self._field(layout, words["feature_label"], dialog["feature"], True)
        self.coordinates = self._field(layout, words["coordinates_label"], dialog["coordinates"], True)
        label = QLabel(words["list_label"])
        self.list = QListWidget()
        self.list.setAccessibleName(words["list_label"])
        label.setBuddy(self.list)
        self.list.setMaximumHeight(120)
        layout.addWidget(label)
        layout.addWidget(self.list)
        self.new_button, self.ok_button, self.cancel_button = button_row(
            layout, [words["new_list"], words["ok"], words["cancel"]], default=False)
        self.ok_button.setDefault(True)
        self.new_button.setDefault(False)
        self.new_button.clicked.connect(self.new_list)
        self.ok_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)
        self.name.returnPressed.connect(self.apply)
        self.fill(dialog["lists"])
        self.resize(520, 420)
        self.name.setFocus()
        self.name.selectAll()

    @staticmethod
    def _field(layout, label_text: str, value: str, read_only: bool) -> QLineEdit:
        label = QLabel(label_text)
        field = QLineEdit(value)
        field.setReadOnly(read_only)
        field.setAccessibleName(label_text)
        label.setBuddy(field)
        layout.addWidget(label)
        layout.addWidget(field)
        return field

    def fill(self, lists: dict) -> None:
        self.list.clear()
        self.list.addItems(lists["items"])
        self.list.setCurrentRow(lists["current"])

    def new_list(self) -> None:
        words = self._dialog["words"]
        box = InputDialog(self, {"title": words["new_list_title"], "label": words["new_list_label"],
                                 "help": words["new_list_help"], "ok": words["ok"], "cancel": words["cancel"]},
                          submit=lambda text: self._run(self._dialog["new_list"], text=text))
        self.input_box = box
        box.finished.connect(lambda _r, b=box: self._new_list_closed(b))
        box.open()

    def _new_list_closed(self, box) -> None:
        self.input_box = None
        if box.response is not None and box.response.bookmark_lists is not None:
            self.fill(box.response.bookmark_lists)
        self.list.setFocus()

    def apply(self) -> None:
        if self.response is not None or self.error_box is not None or self.input_box is not None:
            return   # Enter can arrive twice: answer once
        response = self._run(self._dialog["add"], text=self.name.text(), list=self.list.currentRow())
        if response.error:
            box = QMessageBox(QMessageBox.Icon.Warning, self.windowTitle(), response.error,
                              QMessageBox.StandardButton.NoButton, self)
            ok = box.addButton(self._dialog["words"]["ok"], QMessageBox.ButtonRole.AcceptRole)
            box.setDefaultButton(ok)
            box.setEscapeButton(ok)
            box.finished.connect(self._error_closed)
            self.error_box = box
            box.open()
            return
        self.response = response
        self.accept()

    def _error_closed(self, _result) -> None:
        self.error_box.deleteLater()
        self.error_box = None
        self.name.setFocus()
        self.name.selectAll()


class ConfirmBox(QMessageBox):
    """A question in a message box, such as Reset all settings (P2-T18h): the core's title and
    words, its button to go ahead and Cancel. Cancel has the focus first and is the default, so
    Enter straight away changes nothing; Enter on the other button presses it (P2-T17b).
    `confirmed` says which was pressed, once the box has closed."""

    def __init__(self, parent, dialog: dict):
        super().__init__(QMessageBox.Icon.Warning, dialog["title"], dialog["text"], QMessageBox.StandardButton.NoButton,
                         parent)
        self.ok_button = self.addButton(dialog["ok"], QMessageBox.ButtonRole.AcceptRole)
        self.cancel_button = self.addButton(dialog["cancel"], QMessageBox.ButtonRole.RejectRole)
        self.setDefaultButton(self.cancel_button)
        self.setEscapeButton(self.cancel_button)

    @property
    def confirmed(self) -> bool:
        return self.clickedButton() is self.ok_button


class SoundsDialog(ListDialog):
    """Help, The sounds: each sound with its file and meaning. Enter, Space or
    Play plays the selected one (DP134, PO feedback on checklist 12); Close leaves."""

    def __init__(self, parent, title: str, items: list[dict], play_label: str, close_label: str, play):
        super().__init__(parent, title, [i["label"] for i in items], close_label)
        self._events = [i["event"] for i in items]
        self._play = play
        self.play_button = QPushButton(play_label)
        self.play_button.setAutoDefault(False)
        self.play_button.clicked.connect(self.play_selected)
        self.layout().insertWidget(1, self.play_button)
        self.list.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if obj is self.list and event.type() == QEvent.Type.KeyPress and not event.modifiers() \
                and event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.play_selected()
            return True
        return super().eventFilter(obj, event)

    def play_selected(self):
        row = self.list.currentRow()
        if 0 <= row < len(self._events):
            self._play(self._events[row])

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):   # Enter plays and never closes the dialog
            self.play_selected()
            return
        super().keyPressEvent(event)


class KeyCaptureDialog(QDialog):
    """Press the key you want. OK applies it; the core says if it is taken (ACC-3).
    The message is shown and spoken, and goes when the key is changed or cleared
    (PO feedback on checklist 2.6)."""

    def __init__(self, parent, session, command: dict, words: dict, speak=None):
        super().__init__(parent)
        self.session, self.command, self.key = session, command, command["key"]
        self._speak = speak
        self.setWindowTitle(command["label"])
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(words["key_prompt"]))
        self.field = QLineEdit(session.key_text(self.key))
        self.field.setReadOnly(True)
        self.field.setAccessibleName(words["key_field"])
        self.field.installEventFilter(self)
        layout.addWidget(self.field)
        self.message = QLabel("")
        self.message.setAccessibleName(words["key_message"])
        layout.addWidget(self.message)
        self.ok_button, self.clear_button, self.cancel_button = button_row(
            layout, [words["ok"], words["key_clear"], words["cancel"]])
        self.ok_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)
        self.clear_button.clicked.connect(self._clear)
        self.field.setFocus()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if obj is self.field and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                return False   # Tab still leaves the field
            name = key_name(event, mac=self.session.system == "mac")
            if name:
                self.key = name
                self.field.setText(self.session.key_text(name))
                self._show_message("")
            return True
        return super().eventFilter(obj, event)

    def _clear(self):
        self.key = ""
        self.field.setText("")
        self._show_message("")

    def _show_message(self, text: str) -> None:
        self.message.setText(text)
        self.message.setAccessibleDescription(text)
        if text and self._speak is not None:
            self._speak(text, "assertive")

    def apply(self):
        response = self.session.run("keys.remap", command=self.command["name"], key=self.key)
        text = " ".join(a["text"] for a in response.announcements)
        if response.settings_changed:
            self.result_response = response
            self.accept()
        else:
            self._show_message(text)
            self.result_response = response
            self.field.setFocus()


class LayerSettingsDialog(QDialog):
    """The settings of one layer: the minimum and maximum zoom it is visible at, and the sound when
    a line or border of it is crossed (SCP-7). OK checks the range with the core and stays open, saying
    why, if the minimum zoom is larger than the maximum. Every word and choice comes from the core."""

    def __init__(self, parent, layer: dict, dialog: dict, check, speak=None):
        super().__init__(parent)
        words = dialog["words"]
        self._check, self._speak = check, speak
        self.setWindowTitle(words["settings_title"].format(layer=layer["name"]))
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.min_zoom = self._zoom_box(dialog, words["min_zoom"], layer["min_zoom_m"] or 0.0, 0.0)
        self.max_zoom = self._zoom_box(dialog, words["max_zoom"], layer["max_zoom_m"], None)
        self.crossing = QComboBox()
        self.crossing.setAccessibleName(words["crossing"])
        self.crossing.addItem(words["no_sound"], None)
        for e in dialog["earcons"]:
            self.crossing.addItem(e["label"], e["event"])
        self.crossing.setCurrentIndex(max(0, self.crossing.findData(layer["crossing_earcon"])))
        self.sound = QComboBox()
        self.sound.setAccessibleName(words["layer_sound"])
        self.sound.addItem(words["no_sound"], None)
        for e in dialog["earcons"]:
            self.sound.addItem(e["label"], e["event"])
        self.sound.setCurrentIndex(max(0, self.sound.findData(layer.get("sound"))))
        for label, box in ((words["min_zoom"], self.min_zoom), (words["max_zoom"], self.max_zoom),
                           (words["crossing"], self.crossing), (words["layer_sound"], self.sound)):
            form.addRow(label, box)
        layout.addLayout(form)
        # Whether its areas' outlines are drawn on the map, for an area layer (P3-T23, DP198).
        self.outline = QCheckBox(words["outline"])
        self.outline.setChecked(bool(layer.get("outline", True)))
        self.outline.setVisible(layer.get("geometry", "area") == "area")
        layout.addWidget(self.outline)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.ok_button, self.cancel_button = button_row(layout, [words["ok"], words["cancel"]])
        self.ok_button.clicked.connect(self._ok)
        self.cancel_button.clicked.connect(self.reject)
        self.min_zoom.setFocus()

    @staticmethod
    def _zoom_box(dialog: dict, name: str, current, none_value) -> QComboBox:
        """A choice of the zoom list, with "no limit" first. The core's list already holds any zoom
        a layer has that is not one of the usual ones, such as one a pack chose."""
        box = QComboBox()
        box.setAccessibleName(name)
        box.addItem(dialog["every_zoom"], none_value)
        for z in dialog["zooms"]:
            box.addItem(z["label"], z["value"])
        box.setCurrentIndex(max(0, box.findData(current)))
        return box

    def values(self) -> dict:
        return {"min_zoom_m": self.min_zoom.currentData() or 0.0, "max_zoom_m": self.max_zoom.currentData(),
                "crossing_earcon": self.crossing.currentData(), "sound": self.sound.currentData(),
                "outline": self.outline.isChecked()}

    def _ok(self):
        v = self.values()
        response = self._check(v["min_zoom_m"], v["max_zoom_m"])
        if response.error:
            self.message.setText(response.error)
            self.message.setAccessibleDescription(response.error)
            if self._speak is not None:
                self._speak(response.error)
            self.min_zoom.setFocus()
            return
        self.accept()


class ViewsDialog(QDialog):
    """The map views (P3-T23, P3-T28h, P4-T14g; ACC-7): the list of views, open on the one in use, with Add,
    Save changes, Rename and Delete buttons, and OK and Cancel. Enter is OK and Escape is Cancel. The core keeps
    the changes in a copy: the four buttons only change that, and OK (views.apply, run by the window) keeps them
    and uses the view chosen, which is `row`; Cancel runs nothing. `run` is session.run.

    Save changes, Rename and Delete are unavailable on a line the core marks so (a built-in view, Custom, or for
    Save changes a view holding the layers as they are): they stay in the Tab order and NVDA says "unavailable"
    (desktop/unavailable_button.py), and pressing one does nothing."""

    def __init__(self, parent, dialog: dict, run, speak=None):
        super().__init__(parent)
        self._dialog, self._run, self._speak = dialog, run, speak
        self.items: list[dict] = []
        self.input_box: InputDialog | None = None
        words = dialog["words"]
        self.setWindowTitle(dialog["title"])
        layout = QVBoxLayout(self)
        help_label = QLabel(dialog["help"])
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.list = QListWidget()
        self.list.setAccessibleName(words["list"])
        self.list.setAccessibleDescription(dialog["help"])
        layout.addWidget(self.list)
        self.add_button, self.save_button, self.rename_button, self.delete_button = button_row(
            layout, [words["add"], words["save"], words["rename"], words["delete"]], default=False,
            cls=UnavailableButton)
        self.add_button.on_press(self.add)
        self.save_button.on_press(self.save)
        self.rename_button.on_press(self.rename)
        self.delete_button.on_press(self.delete)
        self.list.currentRowChanged.connect(lambda _row: self._mark_buttons())
        self.ok_button, self.cancel_button = button_row(layout, [words["ok"], words["cancel"]])
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.fill(dialog["views"])
        self.resize(520, 420)
        self.list.setFocus()   # on the view in use

    @property
    def row(self) -> int:
        return self.list.currentRow()

    def fill(self, listing: dict) -> None:
        self.items = listing["items"]
        self.list.clear()
        self.list.addItems([i["label"] for i in self.items])
        self.list.setCurrentRow(listing["current"])
        self._mark_buttons()

    def _mark_buttons(self) -> None:
        """Save changes, Rename and Delete can be pressed only where the core's line says so."""
        row = self.row
        item = self.items[row] if 0 <= row < len(self.items) else {}
        self.save_button.set_available(item.get("save", False))
        self.rename_button.set_available(item.get("own", False))
        self.delete_button.set_available(item.get("own", False))

    def _input(self, title: str, name: str, submit) -> None:
        words = self._dialog["words"]
        box = InputDialog(self, {"title": title, "label": words["name_label"], "help": words["name_help"],
                                 "ok": words["ok"], "cancel": words["cancel"]}, submit=submit)
        self.input_box = box
        box.finished.connect(lambda _r, b=box: self._input_closed(b))
        box.open()
        box.field.setText(name)
        box.field.selectAll()

    def _input_closed(self, box) -> None:
        self.input_box = None
        if box.response is not None and box.response.views is not None:
            self.fill(box.response.views)
            self._say(box.response)
        self.list.setFocus()

    def _say(self, response) -> None:
        if self._speak is not None:
            for a in response.announcements:
                self._speak(a["text"])

    def add(self) -> None:
        self._input(self._dialog["words"]["add_title"], "",
                    lambda text: self._run(self._dialog["add"], text=text))

    def rename(self) -> None:
        row = self.row
        if not 0 <= row < len(self.items) or not self.items[row]["own"]:
            return
        name = self.items[row]["id"]
        self._input(self._dialog["words"]["rename_title"].replace("{name}", name), name,
                    lambda text: self._run(self._dialog["rename"], index=row, text=text))

    def delete(self) -> None:
        self._change(self._run(self._dialog["delete"], index=self.row))

    def save(self) -> None:
        self._change(self._run(self._dialog["save"], index=self.row))

    def _change(self, response) -> None:
        """The list as the core now has it, what it says, and the focus back on the list."""
        if response.views is None:   # nothing changed
            return
        self.fill(response.views)
        self._say(response)
        self.list.setFocus()


def save_text_file(parent, spec: dict) -> str | None:
    """The standard Save box for the core's Response.save_file (P4-T9d): the text is written as UTF-8 with LF line
    ends. Returns what the core says (saved, or could not be saved), or None on Cancel."""
    path, _ = QFileDialog.getSaveFileName(parent, spec["title"], spec["name"], spec["filter"])
    if not path:
        return None
    try:
        with open(path, "w", encoding="utf-8", newline=chr(10)) as f:
            f.write(spec["text"])
    except OSError:
        return spec["failed"]
    return spec["saved"]


def ask_text_file(parent, spec: dict) -> tuple[str, str] | None:
    """The standard Open box for the core's Response.open_file: (text, file name), the text "" if the file cannot be
    read (the core says why it is not a bookmark file), or None on Cancel."""
    path, _ = QFileDialog.getOpenFileName(parent, spec["title"], "", spec["filter"])
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline=None) as f:
            text = f.read()
    except OSError:
        text = ""
    return text, Path(path).name


class _BookmarkListsDialog(QDialog):
    """What the bookmark manager and the bookmark list dialog share (P4-T8e; USR-3, ACC-7). Neither has OK: each
    change is run in the core at once, and `handle` (the window's) writes the bookmarks file, fills the panel again
    and speaks what the core said. Delete in the core is a question, shown in a ConfirmBox with Cancel the default;
    Delete runs the core's submit. Every word and every line comes from the core."""

    def __init__(self, parent, dialog: dict, run, handle, speak=None):
        super().__init__(parent)
        self._dialog, self._run, self._handle, self._speak = dialog, run, handle, speak
        self.items: list[dict] = []
        self.child_box: QDialog | None = None
        self.setWindowTitle(dialog["title"])

    def _do(self, command: str, **args):
        """Run a command; a question is asked here, and any other answer is handled. Returns the response, or None
        when it was a question or was refused (a refusal is spoken)."""
        response = self._run(command, **args)
        if response.dialog and response.dialog.get("kind") == "confirm":
            self._ask(response.dialog)
            return None
        if response.error:
            if self._speak is not None:
                self._speak(response.error)
            return None
        self._apply(response)
        return response

    def _apply(self, response) -> None:
        self._handle(response)
        if response.open_file:   # Open a file (P4-T9d): the standard Open box; the core takes the text
            self._open_file(response.open_file)
        listing = response.bookmark_manager if response.bookmark_manager is not None else response.bookmark_list
        if listing is not None:
            self.fill(listing)

    def _open_file(self, spec: dict) -> None:
        """The standard Open box; the file is read as UTF-8 and its text and name go to the core's command. Cancel
        does nothing. The focus comes back to the list."""
        chosen = ask_text_file(self, spec)
        if chosen is not None:
            self._apply(self._run(spec["submit"], text=chosen[0], file=chosen[1]))
        self.list.setFocus()

    def _ask(self, dialog: dict) -> None:
        box = ConfirmBox(self, dialog)
        self.child_box = box
        box.finished.connect(lambda _r, b=box, d=dialog: self._asked(b, d))
        box.open()

    def _asked(self, box, dialog: dict) -> None:
        self.child_box = None
        if box.confirmed:
            self._apply(self._run(dialog["submit"]))
        self.list.setFocus()

    @staticmethod
    def _buttons(layout, labels: list[str]):
        return button_row(layout, labels, default=False, cls=UnavailableButton)

    def keyPressEvent(self, event):
        """Enter anywhere but on a button does what the dialog's main action is (_enter), once: Qt would press
        whichever button came first, which is not always the one that makes sense."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not isinstance(self.focusWidget(), QPushButton):
            event.accept()
            self._enter()
            return
        super().keyPressEvent(event)

    def _enter(self) -> None:
        pass


class BookmarkManagerDialog(_BookmarkListsDialog):
    """The bookmark manager (P4-T8e; USR-3, DP219 point 7), for the bookmark lists themselves. In Tab order: the lists
    (a check box for each, Space switches it on or off, Enter is Open list), Open list, New list, Rename, Move up,
    Move down, Delete list, Zoom range, Save to a file, Open a file and Close. Move up is unavailable on the first
    list and Move down on the last: they stay in the Tab order and NVDA says "unavailable"."""

    def __init__(self, parent, dialog: dict, run, handle, speak=None):
        super().__init__(parent, dialog, run, handle, speak)
        words, commands = dialog["words"], dialog["commands"]
        self._words, self._commands = words, commands
        self.input_box: InputDialog | None = None
        layout = QVBoxLayout(self)
        help_label = QLabel(dialog["help"])
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.list = QListWidget()
        self.list.setAccessibleName(words["list"])
        self.list.setAccessibleDescription(dialog["help"])
        layout.addWidget(self.list)
        (self.open_button, self.new_button, self.rename_button, self.up_button, self.down_button, self.delete_button,
         self.zoom_button) = self._buttons(layout, [words["open_list"], words["new"], words["rename"], words["up"],
                                                    words["down"], words["delete"], words["zoom"]])
        self.save_button, self.open_file_button = self._buttons(layout, [words["save_file"], words["open_file"]])
        (self.close_button,) = button_row(layout, [words["close"]], default=False)
        self.open_button.on_press(self.open_list)
        self.new_button.on_press(self.new)
        self.rename_button.on_press(self.rename)
        self.up_button.on_press(lambda: self.move(-1))
        self.down_button.on_press(lambda: self.move(1))
        self.delete_button.on_press(lambda: self._do(commands["delete"], index=self.row))
        self.zoom_button.on_press(self.zoom)
        self.save_button.on_press(lambda: self._do(commands["save_file"], index=self.row))
        self.open_file_button.on_press(lambda: self._do(commands["open_file"]))
        self.close_button.clicked.connect(self.accept)
        chain = [self.list, self.open_button, self.new_button, self.rename_button, self.up_button, self.down_button,
                 self.delete_button, self.zoom_button, self.save_button, self.open_file_button, self.close_button]
        for a, b in zip(chain, chain[1:]):
            QWidget.setTabOrder(a, b)
        self.list.currentRowChanged.connect(lambda _row: self._mark_buttons())
        self.list.itemChanged.connect(self._item_changed)
        self.fill(dialog["lists"])
        self.resize(560, 460)
        self.list.setFocus()

    @property
    def row(self) -> int:
        return self.list.currentRow()

    def fill(self, listing: dict) -> None:
        self.items = listing["items"]
        self.list.blockSignals(True)
        self.list.clear()
        for item in self.items:
            line = QListWidgetItem(item["label"])
            line.setFlags(line.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            line.setCheckState(Qt.CheckState.Checked if item["on"] else Qt.CheckState.Unchecked)
            self.list.addItem(line)
        self.list.setCurrentRow(listing["current"])
        self.list.blockSignals(False)
        self._mark_buttons()

    def _mark_buttons(self) -> None:
        item = self.items[self.row] if 0 <= self.row < len(self.items) else {}
        self.up_button.set_available(item.get("up", False))
        self.down_button.set_available(item.get("down", False))

    def _item_changed(self, line) -> None:
        row = self.list.row(line)
        on = line.checkState() == Qt.CheckState.Checked
        if 0 <= row < len(self.items) and on != self.items[row]["on"]:
            self._do(self._commands["on"], index=row, on=on)

    def _enter(self) -> None:
        self.open_list()

    def move(self, by: int) -> None:
        self._do(self._commands["move"], index=self.row, by=by)
        self.list.setFocus()

    def _input(self, title: str, name: str, submit) -> None:
        words = self._words
        box = InputDialog(self, {"title": title, "label": words["name_label"], "help": words["name_help"],
                                 "ok": words["ok"], "cancel": words["cancel"]}, submit=submit)
        self.input_box = box
        box.finished.connect(lambda _r, b=box: self._input_closed(b))
        box.open()
        box.field.setText(name)
        box.field.selectAll()

    def _input_closed(self, box) -> None:
        self.input_box = None
        if box.response is not None:
            self._apply(box.response)
        self.list.setFocus()

    def new(self) -> None:
        self._input(self._words["new_title"], "", lambda text: self._run(self._commands["new"], text=text))

    def rename(self) -> None:
        row = self.row
        if not 0 <= row < len(self.items):
            return
        name = self.items[row]["name"]
        self._input(self._words["rename_title"].replace("{name}", name), name,
                    lambda text: self._run(self._commands["rename"], index=row, text=text))

    def zoom(self) -> None:
        row = self.row
        if not 0 <= row < len(self.items):
            return
        box = BookmarkZoomDialog(self, self._dialog, self.items[row], check=lambda low, high: self._run(
            self._commands["zoom"], index=row, low=low, high=high), speak=self._speak)
        self.child_box = box
        box.finished.connect(lambda _r, b=box: self._zoom_closed(b))
        box.open()

    def _zoom_closed(self, box) -> None:
        self.child_box = None
        if box.response is not None:
            self._apply(box.response)
        self.list.setFocus()

    def open_list(self) -> None:
        """The bookmark list dialog for the chosen list; the lines are counted again when it closes."""
        row = self.row
        if not 0 <= row < len(self.items):
            return
        response = self._run(self._commands["open_list"], index=row)
        box = BookmarkListDialog(self, response.dialog, self._run, self._handle, self._speak)
        self.child_box = box
        box.finished.connect(lambda _r, r=row: self._list_closed(r))
        box.open()

    def _list_closed(self, row: int) -> None:
        self.child_box = None
        self.fill(self._run(self._commands["listing"], index=row).bookmark_manager)
        self.list.setFocus()


class BookmarkZoomDialog(QDialog):
    """The zoom range of one bookmark list (P4-T8e), as a layer's (LayerSettingsDialog): Show from and Show up to,
    each a choice of the zoom list with "No limit", OK and Cancel. OK runs the core's command through `check`, which
    changes it; a refusal stays here and is said. `response` is the core's answer after OK."""

    def __init__(self, parent, dialog: dict, item: dict, check, speak=None):
        super().__init__(parent)
        words = dialog["words"]
        self._check, self._speak = check, speak
        self.response = None
        self.setWindowTitle(words["zoom_title"].replace("{name}", item["name"]))
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.min_zoom = self._box(dialog, words["min_zoom"], item["min_zoom_m"] or 0.0, 0.0)
        self.max_zoom = self._box(dialog, words["max_zoom"], item["max_zoom_m"], None)
        form.addRow(words["min_zoom"], self.min_zoom)
        form.addRow(words["max_zoom"], self.max_zoom)
        layout.addLayout(form)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.ok_button, self.cancel_button = button_row(layout, [words["ok"], words["cancel"]])
        self.ok_button.clicked.connect(self._ok)
        self.cancel_button.clicked.connect(self.reject)
        self.min_zoom.setFocus()

    @staticmethod
    def _box(dialog: dict, name: str, current, none_value) -> QComboBox:
        box = QComboBox()
        box.setAccessibleName(name)
        box.addItem(dialog["every_zoom"], none_value)
        for z in dialog["zooms"]:
            box.addItem(z["label"], z["value"])
        box.setCurrentIndex(max(0, box.findData(current)))
        return box

    def _ok(self) -> None:
        response = self._check(self.min_zoom.currentData() or 0.0, self.max_zoom.currentData())
        if response.error:
            self.message.setText(response.error)
            self.message.setAccessibleDescription(response.error)
            if self._speak is not None:
                self._speak(response.error)
            self.min_zoom.setFocus()
            return
        self.response = response
        self.accept()


class BookmarkListDialog(_BookmarkListsDialog):
    """The bookmark list dialog (P4-T8e; USR-3, DP219 point 7), for one list's bookmarks. In Tab order: the
    bookmarks, Move up, Move down, Other list (the lists a bookmark can go to), Copy to list, Move to list, Delete
    and Close. Move up, Move down, Copy to list, Move to list and Delete are unavailable where they cannot act: they
    stay in the Tab order and NVDA says "unavailable"."""

    def __init__(self, parent, dialog: dict, run, handle, speak=None):
        super().__init__(parent, dialog, run, handle, speak)
        words, commands = dialog["words"], dialog["commands"]
        self._words, self._commands, self._li = words, commands, dialog["list"]
        self.targets = dialog["lists"]["targets"]
        layout = QVBoxLayout(self)
        help_label = QLabel(dialog["help"])
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.list = QListWidget()
        self.list.setAccessibleName(words["list"])
        layout.addWidget(self.list)
        self.up_button, self.down_button = self._buttons(layout, [words["up"], words["down"]])
        label = QLabel(words["target_label"])
        self.target = QComboBox()
        self.target.setAccessibleName(words["target_label"])
        label.setBuddy(self.target)
        for t in self.targets:
            self.target.addItem(t["name"], t["index"])
        if not self.targets:
            self.target.addItem(words["no_target"], None)
        layout.addWidget(label)
        layout.addWidget(self.target)
        self.copy_button, self.move_button, self.delete_button = self._buttons(
            layout, [words["copy"], words["move"], words["delete"]])
        (self.close_button,) = button_row(layout, [words["close"]], default=False)
        self.up_button.on_press(lambda: self.move(-1))
        self.down_button.on_press(lambda: self.move(1))
        self.copy_button.on_press(lambda: self._to("copy"))
        self.move_button.on_press(lambda: self._to("move_to"))
        self.delete_button.on_press(lambda: self._do(commands["delete"], list=self._li, index=self.row))
        self.close_button.clicked.connect(self.accept)
        chain = [self.list, self.up_button, self.down_button, self.target, self.copy_button, self.move_button,
                 self.delete_button, self.close_button]
        for a, b in zip(chain, chain[1:]):
            QWidget.setTabOrder(a, b)
        self.list.currentRowChanged.connect(lambda _row: self._mark_buttons())
        self.fill(dialog["lists"])
        self.resize(520, 440)
        self.list.setFocus()

    @property
    def row(self) -> int:
        return self.list.currentRow()

    def fill(self, listing: dict) -> None:
        self.items = listing["items"]
        self.list.blockSignals(True)
        self.list.clear()
        self.list.addItems([i["label"] for i in self.items])
        self.list.setCurrentRow(listing["current"] if self.items else -1)
        self.list.blockSignals(False)
        self.list.setAccessibleDescription(listing["empty"])
        self._mark_buttons()

    def _mark_buttons(self) -> None:
        item = self.items[self.row] if 0 <= self.row < len(self.items) else None
        self.up_button.set_available(bool(item and item["up"]))
        self.down_button.set_available(bool(item and item["down"]))
        can_go = item is not None and bool(self.targets)
        self.copy_button.set_available(can_go)
        self.move_button.set_available(can_go)
        self.delete_button.set_available(item is not None)

    def move(self, by: int) -> None:
        self._do(self._commands["move"], list=self._li, index=self.row, by=by)
        self.list.setFocus()

    def _to(self, which: str) -> None:
        target = self.target.currentData()
        if target is not None and 0 <= self.row < len(self.items):
            self._do(self._commands[which], list=self._li, index=self.row, target=target)
        self.list.setFocus()

class LayersDialog(QDialog):
    """The layers list (SCP-6, SCP-7): a check box for each layer under its group, Space switches it,
    and a Settings button opens the selected layer's zoom range and crossing sound. OK keeps the changes,
    which `changes` lists as (layer id, {field: value}), one entry for each layer changed; Cancel keeps none."""

    def __init__(self, parent, dialog: dict, check, speak=None):
        super().__init__(parent)
        self.dialog, self._check, self._speak = dialog, check, speak
        words = dialog["words"]
        self.setWindowTitle(dialog["title"])
        self.layers = {l["id"]: dict(l) for g in dialog["groups"] for l in g["layers"]}
        self._start = {k: dict(v) for k, v in self.layers.items()}
        layout = QVBoxLayout(self)
        # The Information panel's tree, whose accessibility stays right as groups close (P2-T18b, DP135).
        self.tree = PanelTree()
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName(dialog["title"])
        self.items: dict[str, QTreeWidgetItem] = {}
        for group in dialog["groups"]:
            top = QTreeWidgetItem([group["name"]])
            self.tree.addTopLevelItem(top)
            for layer in group["layers"]:
                child = QTreeWidgetItem([layer["name"]])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked if layer["on"] else Qt.CheckState.Unchecked)
                child.setData(0, Qt.ItemDataRole.UserRole, layer["id"])
                top.addChild(child)
                self.items[layer["id"]] = child
            top.setExpanded(True)
        layout.addWidget(self.tree)
        (self.settings_button,) = button_row(layout, [words["settings_button"]], default=False)
        self.settings_button.clicked.connect(self.open_settings)
        self.ok_button, self.cancel_button = button_row(layout, [words["ok"], words["cancel"]])
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.tree.itemChanged.connect(self._item_changed)
        first = next(iter(self.items.values()), None)
        if first is not None:
            self.tree.setCurrentItem(first)
        self.resize(560, 460)
        self.tree.setFocus()

    def _item_changed(self, item, _column):
        layer_id = item.data(0, Qt.ItemDataRole.UserRole)
        if layer_id in self.layers:
            self.layers[layer_id]["on"] = item.checkState(0) == Qt.CheckState.Checked

    def selected_layer(self) -> str | None:
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None

    def open_settings(self):
        layer_id = self.selected_layer()
        if layer_id is None:   # a group heading is selected: say so, rather than nothing
            if self._speak is not None:
                self._speak(self.dialog["words"]["choose_layer"])
            return
        box = LayerSettingsDialog(self, self.layers[layer_id], self.dialog, self._check, self._speak)
        box.accepted.connect(lambda: self.layers[layer_id].update(box.values()))
        box.exec()
        self.tree.setFocus()

    def changes(self) -> list[tuple[str, dict]]:
        out = []
        for layer_id, now in self.layers.items():
            changed = {f: now.get(f) for f in ("on", "min_zoom_m", "max_zoom_m", "crossing_earcon", "sound", "outline")
                       if now.get(f) != self._start[layer_id].get(f)}
            if changed:
                out.append((layer_id, changed))
        return out


class SoundFileField(QWidget):
    """Your own sound file for an earcon (P2-T8, SON-8): its path, Choose file and Use the
    default. A chosen file that is not a WAV sound TobyMap can play is refused, and you are
    told why, so the sound is not changed. The words stay on screen under the field and take
    the focus: spoken alone, NVDA read the focus coming back from the file dialog over them
    (PO note on checklist 14.5)."""

    def __init__(self, value: str, field: dict, words: dict, speak=None, choose=None):
        super().__init__()
        from desktop.sounds import readable_wav

        self._readable, self._speak, self.words = readable_wav, speak, words
        self._choose_dialog = choose or self._ask
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        column.addLayout(row)
        self.edit = QLineEdit(value)
        self.edit.setPlaceholderText(words["default_sound"])
        self.choose_button = QPushButton(words["choose_file"])
        self.choose_button.setAccessibleName(words["choose_file_for"].format(name=field["name"]))
        self.default_button = QPushButton(words["use_default"])
        self.default_button.setAccessibleName(words["use_default_for"].format(name=field["name"]))
        for w in (self.edit, self.choose_button, self.default_button):
            row.addWidget(w)
        self.choose_button.clicked.connect(self.choose)
        self.default_button.clicked.connect(self.use_default)
        # Shown only when there is something to say; it can take the focus, so Tab and the
        # screen reader reach it, and its name is its words.
        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard
                                             | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.message.hide()
        column.addWidget(self.message)

    def _tell(self, text: str) -> None:
        self.message.setText(text)
        self.message.setAccessibleName(text)
        self.message.setVisible(bool(text))

    def setAccessibleName(self, name: str) -> None:   # the field's label goes on the path box
        self.edit.setAccessibleName(name)

    def show_for(self, field: dict, value: str) -> None:
        """The same controls for another earcon, chosen in the Earcons tab's list (P2-T17p): its
        file, and names that say which earcon they are for."""
        self.edit.setText(value)
        self.edit.setAccessibleName(field["label"])
        self.choose_button.setAccessibleName(self.words["choose_file_for"].format(name=field["name"]))
        self.default_button.setAccessibleName(self.words["use_default_for"].format(name=field["name"]))
        self._tell("")

    def _ask(self) -> str:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, self.choose_button.accessibleName(), self.edit.text(),
                                              self.words["sound_files"])
        return path

    def choose(self) -> None:
        path = self._choose_dialog()
        if not path:
            return
        if self._readable(Path(path)):
            self.edit.setText(path)
            self._tell("")
            self.choose_button.setFocus()
        else:
            self._tell(self.words["file_unreadable"].format(file=Path(path).name))
            self.message.setFocus()

    def use_default(self) -> None:
        self.edit.clear()
        self._tell("")
        self.edit.setFocus()

    def text(self) -> str:
        return self.edit.text()


class EarconsPage(QWidget):
    """The Earcons tab (P2-T17p; SON-6, SON-7, SON-8, DP163, desktop checklist 10.6). One list of
    every earcon, each with a check box to play it or not: Space ticks it. Below the list, one set
    of controls for the earcon chosen in it: its own volume, your own file (empty for the
    default), Choose file and Use the default. Their labels and names say which earcon they are
    for. What is changed is kept for each earcon until OK or Cancel."""

    def __init__(self, tab: dict, values: dict, words: dict, speak=None):
        super().__init__()
        self.rows = tab["earcons"]
        self.fields = {f["id"]: f for f in tab["fields"]}
        self.values = {fid: values[fid] for fid in self.fields}
        self._row: dict | None = None
        layout = QVBoxLayout(self)
        label = QLabel(tab["list_label"])
        self.list = QListWidget()
        self.list.setAccessibleName(tab["list_label"])
        label.setBuddy(self.list)
        for r in self.rows:
            item = QListWidgetItem(r["label"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if self.values[r["on"]] else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        layout.addWidget(label)
        layout.addWidget(self.list)
        form = QFormLayout()
        self.volume_label, self.file_label = QLabel(), QLabel()
        self.volume = NumberBox()
        self.volume_label.setBuddy(self.volume)
        first = self.fields[self.rows[0]["file"]]
        self.file = SoundFileField("", first, words, speak=speak)
        self.file_label.setBuddy(self.file.edit)
        form.addRow(self.volume_label, self.volume)
        form.addRow(self.file_label, self.file)
        layout.addLayout(form)
        self.list.itemChanged.connect(self._ticked)
        self.list.currentRowChanged.connect(self._show)
        self.volume.valueChanged.connect(lambda v: self._keep("volume", v))
        self.file.edit.textChanged.connect(lambda text: self._keep("file", text))
        self.list.setCurrentRow(0)

    def _keep(self, which: str, value) -> None:
        if self._row is not None:
            self.values[self._row[which]] = value

    def _ticked(self, item) -> None:
        r = self.rows[self.list.row(item)]
        self.values[r["on"]] = item.checkState() == Qt.CheckState.Checked

    def _show(self, i: int) -> None:
        if i < 0:
            return
        self._row = None    # nothing is kept while the controls change to the new earcon
        r = self.rows[i]
        volume = self.fields[r["volume"]]
        self.volume.setRange(int(volume["min"]), int(volume["max"]))
        self.volume.setValue(int(self.values[r["volume"]]))
        self.volume_label.setText(volume["label"])
        self.volume.setAccessibleName(volume["label"])
        self.file_label.setText(self.fields[r["file"]]["label"])
        self.file.show_for(self.fields[r["file"]], str(self.values[r["file"]]))
        self._row = r


class SettingsDialog(QDialog):
    """The settings, from the core's schema, with OK and Cancel (PLT-5, ACC-7)."""

    def __init__(self, parent, session, words: dict, export_cb=None, import_cb=None):
        super().__init__(parent)
        self.session, self.words = session, words
        self.setWindowTitle(words["settings_title"])
        schema = session.settings_schema()
        # The values as the dialog opened: OK sends only what was changed here, so a verbosity
        # preset sent first is not undone by its switches, which the core has just set (P2-T11).
        self._opened = dict(schema["values"])
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setAccessibleName(words["settings_title"])
        self.controls: dict[str, QWidget] = {}
        self.earcons: EarconsPage | None = None
        for tab in schema["tabs"]:
            if tab.get("earcons"):    # one list, and one set of controls for its chosen earcon (P2-T17p)
                announcer = getattr(self.parent(), "announcer", None)
                page = self.earcons = EarconsPage(tab, schema["values"], words,
                                                  speak=announcer.speak if announcer is not None else None)
                tab = {**tab, "fields": []}
            else:
                page = QWidget()
            form = QFormLayout() if tab["fields"] else None
            if form is not None:
                page.setLayout(form)
            for f in tab["fields"]:
                control = self._control(f, schema["values"][f["id"]])
                control.setAccessibleName(f["label"])
                self.controls[f["id"]] = control
                form.addRow(f["label"], control)
            scroll = QScrollArea()   # the Earcons tab is taller than the dialog (P2-T8)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            # Tab goes from the tabs straight to the first setting: the scroll area took the
            # focus first, and NVDA called it "grouping" (P2-T17g, ACC-1). It still scrolls to
            # the setting with the focus.
            scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            scroll.setWidget(page)
            self.tabs.addTab(scroll, tab["label"])
        self.keys_page = QWidget()
        key_layout = QVBoxLayout(self.keys_page)
        self.keymap_box = QComboBox()   # a key map applies at once, as a changed key does (P3-T31b)
        self.keymap_box.setAccessibleName(words["keymap_label"])
        for k in session.keymap_choices():
            self.keymap_box.addItem(k["label"], k["id"])
            if k["chosen"]:
                self.keymap_box.setCurrentIndex(self.keymap_box.count() - 1)
        self.keymap_box.currentIndexChanged.connect(self._choose_keymap)
        key_layout.addWidget(QLabel(words["keymap_label"]))
        key_layout.addWidget(self.keymap_box)
        self.key_list = QListWidget()
        self.key_list.setAccessibleName(words["keys_tab"])
        key_layout.addWidget(self.key_list)
        self.change_key = QPushButton(words["key_change"])
        self.change_key.clicked.connect(self._change_key)
        key_layout.addWidget(self.change_key)
        self.save_keys = QPushButton(words["keys_save"])
        self.save_keys.clicked.connect(self._save_keys)
        self.open_keys = QPushButton(words["keys_open"])
        self.open_keys.clicked.connect(self._open_keys)
        self.reset_keys = QPushButton(words["keys_reset"])
        self.reset_keys.clicked.connect(self._reset_keys)
        for b in (self.save_keys, self.open_keys, self.reset_keys):
            key_layout.addWidget(b)
        self.keys_message = QLabel("")
        self.keys_message.setAccessibleName(words["key_message"])
        self.keys_message.setWordWrap(True)
        key_layout.addWidget(self.keys_message)
        self._commands: list[dict] = []
        self._fill_keys()
        self.tabs.addTab(self.keys_page, words["keys_tab"])
        layout.addWidget(self.tabs)
        # The tab bar's scroll arrows, shown when the tabs do not fit, are not stops for Tab:
        # Left and Right on the tabs already go to every tab (P2-T17g).
        for arrow in self.tabs.tabBar().findChildren(QToolButton):
            arrow.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        labels = [words["ok"], words["cancel"]] + ([words["export"]] if export_cb else []) \
            + ([words["import"]] if import_cb else [])
        buttons = button_row(layout, labels)
        self.ok_button, self.cancel_button = buttons[0], buttons[1]
        rest = buttons[2:]
        if export_cb:
            self.export_button = rest.pop(0)
            self.export_button.clicked.connect(export_cb)
        if import_cb:
            self.import_button = rest.pop(0)
            self.import_button.clicked.connect(lambda: (import_cb(), self.reject()))
        self.ok_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)
        self.resize(560, 460)
        self.tabs.setFocus()
        self.responses: list = []

    def _control(self, f: dict, value):
        if f["kind"] == "sound_file":
            announcer = getattr(self.parent(), "announcer", None)
            return SoundFileField(str(value), f, self.words, speak=announcer.speak if announcer is not None else None)
        if f["kind"] == "choice":
            box = QComboBox()
            for v, label in f["choices"]:
                box.addItem(label, v)
            box.setCurrentIndex(max(0, box.findData(value)))
            return box
        if f["kind"] == "yes_no":
            check = QCheckBox()
            check.setChecked(bool(value))
            return check
        if f["kind"] == "number":
            step = f.get("step", 1)
            if step == int(step):
                spin = NumberBox()
                spin.setRange(int(f["min"]), int(f["max"]))
                spin.setValue(int(value))
            else:
                spin = DecimalBox()
                spin.setDecimals(1)
                spin.setSingleStep(float(step))
                spin.setRange(float(f["min"]), float(f["max"]))
                spin.setValue(float(value))
            return spin
        return QLineEdit(str(value))

    @staticmethod
    def _value(control):
        if isinstance(control, QComboBox):
            return control.currentData()
        if isinstance(control, QCheckBox):
            return control.isChecked()
        if isinstance(control, (QSpinBox, QDoubleSpinBox)):
            return control.value()
        return control.text()

    def _fill_keys(self, keep: int | None = None):
        self._commands = self.session.key_table()
        self.key_list.clear()
        for c in self._commands:
            key = c["key_text"] or self.words["no_key"]
            self.key_list.addItem(f"{c['label']}: {key}")
        self.key_list.setCurrentRow(keep if keep is not None else 0)

    def _keys_ran(self, response) -> None:
        """A key map, key file or reset command ran: its words are shown and spoken, the list is made again."""
        text = self._said_now(response)
        self.keys_message.setText(text)
        self.keys_message.setAccessibleDescription(text)
        self._fill_keys(self.key_list.currentRow())

    def _said_now(self, response) -> str:
        """Speak a response's words now and keep the response for Settings closing, without its words, so
        they are not said again then. Everything else it carries is still handled on close."""
        text = " ".join(a["text"] for a in response.announcements)
        announcer = getattr(self.parent(), "announcer", None)
        if text and announcer is not None:
            announcer.speak(text, "assertive")
        response.announcements = []
        self.responses.append(response)
        return text

    def _show_chosen_keymap(self) -> None:
        self.keymap_box.blockSignals(True)
        for k in self.session.keymap_choices():
            if k["chosen"]:
                self.keymap_box.setCurrentIndex(self.keymap_box.findData(k["id"]))
        self.keymap_box.blockSignals(False)

    def _choose_keymap(self, _index=None):
        self._keys_ran(self.session.run("keys.keymap", keymap=self.keymap_box.currentData()))

    def _reset_keys(self):
        self._keys_ran(self.session.run("keys.reset"))

    def _save_keys(self):
        name, _ = QFileDialog.getSaveFileName(self, self.words["keys_save"], self.words["key_file_name"],
                                              self.words["key_files"])
        if name:
            with open(name, "w", encoding="utf-8") as f:
                f.write(self.session.key_file())

    def _open_keys(self):
        name, _ = QFileDialog.getOpenFileName(self, self.words["keys_open"], "", self.words["key_files"])
        if not name:
            return
        try:
            with open(name, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            text = ""   # not readable: the core says it is not a key file
        self._keys_ran(self.session.run("keys.open", text=text))
        self._show_chosen_keymap()

    def _change_key(self):
        row = self.key_list.currentRow()
        if row < 0:
            return
        announcer = getattr(self.parent(), "announcer", None)
        dialog = KeyCaptureDialog(self, self.session, self._commands[row], self.words,
                                  speak=announcer.speak if announcer is not None else None)
        dialog.exec()
        response = getattr(dialog, "result_response", None)
        if response is not None:
            if response.settings_changed:
                self._said_now(response)   # the new key is said now, not when Settings closes
            else:
                response.announcements = []   # a refusal: the capture dialog has already said it
                self.responses.append(response)
        self._fill_keys(row)
        self.key_list.setFocus()

    def apply(self):
        values = {field_id: self._value(control) for field_id, control in self.controls.items()}
        if self.earcons is not None:
            values.update(self.earcons.values)
        for field_id, value in values.items():
            if value != self._opened.get(field_id):
                self.responses.append(self.session.run("settings.set", field=field_id, value=value))
        self.accept()
