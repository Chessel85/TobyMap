"""The dialogs of the desktop shell (UX section 14, ACC-7).

Every dialog has a Close, OK or Cancel button, so Escape is never needed. What
is in the settings dialog comes from the core (session.settings_schema()), so
the web version shows the same settings.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QTabWidget,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from desktop.keys import key_name
from mapcore.commands.registry import key_text


def button_row(parent_layout, labels: list[str], default: bool = True) -> list[QPushButton]:
    """Buttons in a row, in the order given, which is also their Tab order. A
    button with the focus takes Enter, as Space does: Cancel cancels (P2-T17b,
    ACC-7). Anywhere else in the dialog, Enter presses the first button, OK,
    unless `default` is False, as for a row with no OK. (QDialogButtonBox put
    Cancel before OK in the Tab order: PO feedback on checklist 11, second pass.)"""
    row = QHBoxLayout()
    row.addStretch(1)
    buttons = []
    for label in labels:
        b = QPushButton(label)
        b.setAutoDefault(True)   # Qt's word for "takes Enter while it has the focus"
        row.addWidget(b)
        buttons.append(b)
    if default:
        buttons[0].setDefault(True)
    for a, b in zip(buttons, buttons[1:]):
        QWidget.setTabOrder(a, b)
    parent_layout.addLayout(row)
    return buttons


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
    """A list of lines, one per item, with a Close button: the announcement history (ANN-4)."""

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
    """The announcement history, newest first. Enter on an entry goes back to the place it was said
    at (ANN-4, DP141); an entry with no place says so and the list stays open. A Help line above
    the list says what Enter does."""

    def __init__(self, parent, title: str, lines: list[str], close_label: str, help_text: str, go, speak=None):
        super().__init__(parent, title, lines, close_label)
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


class InputDialog(QDialog):
    """A box to type in, with OK and Cancel (ACC-7): a bearing or coordinates. The core reads what
    was typed; if it can't, the words it gives are shown and spoken and the box stays open."""

    def __init__(self, parent, dialog: dict, submit, speak=None):
        super().__init__(parent)
        self._submit, self._speak = submit, speak
        self.response = None
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
        if dialog["help"]:   # Go to has none: its label is enough (the PO, 8 November 2026)
            self.field.setAccessibleDescription(dialog["help"])
            layout.addWidget(self.help)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.ok_button, self.cancel_button = button_row(layout, [dialog["ok"], dialog["cancel"]])
        self.ok_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)
        self.field.returnPressed.connect(self.apply)
        self.resize(520, 200)
        self.field.setFocus()

    def apply(self):
        response = self._submit(self.field.text())
        if response.error:
            self.message.setText(response.error)
            self.message.setAccessibleDescription(response.error)
            if self._speak is not None:
                self._speak(response.error)
            self.field.setFocus()
            self.field.selectAll()
        else:
            self.response = response
            self.accept()


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
        self.field = QLineEdit(key_text(self.key))
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
            name = key_name(event)
            if name:
                self.key = name
                self.field.setText(key_text(name))
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
        for label, box in ((words["min_zoom"], self.min_zoom), (words["max_zoom"], self.max_zoom),
                           (words["crossing"], self.crossing)):
            form.addRow(label, box)
        layout.addLayout(form)
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
                "crossing_earcon": self.crossing.currentData()}

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
        self.tree = QTreeWidget()
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
            changed = {f: now[f] for f in ("on", "min_zoom_m", "max_zoom_m", "crossing_earcon")
                       if now[f] != self._start[layer_id][f]}
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
        for tab in schema["tabs"]:
            page = QWidget()
            form = QFormLayout(page)
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
        self.key_list = QListWidget()
        self.key_list.setAccessibleName(words["keys_tab"])
        key_layout.addWidget(self.key_list)
        self.change_key = QPushButton(words["key_change"])
        self.change_key.clicked.connect(self._change_key)
        key_layout.addWidget(self.change_key)
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
            spin = QSpinBox()
            spin.setRange(int(f["min"]), int(f["max"]))
            spin.setValue(int(value))
            return spin
        return QLineEdit(str(value))

    @staticmethod
    def _value(control):
        if isinstance(control, QComboBox):
            return control.currentData()
        if isinstance(control, QCheckBox):
            return control.isChecked()
        if isinstance(control, QSpinBox):
            return control.value()
        return control.text()

    def _fill_keys(self, keep: int | None = None):
        self._commands = self.session.key_table()
        self.key_list.clear()
        for c in self._commands:
            key = c["key_text"] or self.words["no_key"]
            self.key_list.addItem(f"{c['label']}: {key}")
        self.key_list.setCurrentRow(keep if keep is not None else 0)

    def _change_key(self):
        row = self.key_list.currentRow()
        if row < 0:
            return
        announcer = getattr(self.parent(), "announcer", None)
        dialog = KeyCaptureDialog(self, self.session, self._commands[row], self.words,
                                  speak=announcer.speak if announcer is not None else None)
        dialog.exec()
        if getattr(dialog, "result_response", None) is not None:
            self.responses.append(dialog.result_response)
        self._fill_keys(row)
        self.key_list.setFocus()

    def apply(self):
        for field_id, control in self.controls.items():
            value = self._value(control)
            if value != self._opened.get(field_id):
                self.responses.append(self.session.run("settings.set", field=field_id, value=value))
        self.accept()
