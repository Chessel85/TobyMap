"""The dialogs of the desktop shell (UX section 14, ACC-7).

Every dialog has a Close, OK or Cancel button, so Escape is never needed. What
is in the settings dialog comes from the core (session.settings_schema()), so
the web version shows the same settings.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                               QListWidget, QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout,
                               QWidget)

from desktop.keys import key_name


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


class SoundsDialog(ListDialog):
    """Help, The sounds: each sound with its file and meaning. Enter or Play plays
    the selected one (DP134); Close leaves."""

    def __init__(self, parent, title: str, items: list[dict], play_label: str, close_label: str, play):
        super().__init__(parent, title, [i["label"] for i in items], close_label)
        self._events = [i["event"] for i in items]
        self._play = play
        self.play_button = QPushButton(play_label)
        self.play_button.setAutoDefault(False)
        self.play_button.clicked.connect(self.play_selected)
        self.layout().insertWidget(1, self.play_button)

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
        self.field = QLineEdit(self.key)
        self.field.setReadOnly(True)
        self.field.setAccessibleName(words["key_field"])
        self.field.installEventFilter(self)
        layout.addWidget(self.field)
        self.message = QLabel("")
        self.message.setAccessibleName(words["key_message"])
        layout.addWidget(self.message)
        buttons = QDialogButtonBox()
        self.ok_button = buttons.addButton(words["ok"], QDialogButtonBox.ButtonRole.AcceptRole)
        self.clear_button = buttons.addButton(words["key_clear"], QDialogButtonBox.ButtonRole.ActionRole)
        self.cancel_button = buttons.addButton(words["cancel"], QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        self.clear_button.clicked.connect(self._clear)
        layout.addWidget(buttons)
        self.field.setFocus()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if obj is self.field and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                return False   # Tab still leaves the field
            name = key_name(event)
            if name:
                self.key = name
                self.field.setText(name)
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


class SettingsDialog(QDialog):
    """The settings, from the core's schema, with OK and Cancel (PLT-5, ACC-7)."""

    def __init__(self, parent, session, words: dict, export_cb=None, import_cb=None):
        super().__init__(parent)
        self.session, self.words = session, words
        self.setWindowTitle(words["settings_title"])
        schema = session.settings_schema()
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
            self.tabs.addTab(page, tab["label"])
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
        buttons = QDialogButtonBox()
        self.ok_button = buttons.addButton(words["ok"], QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = buttons.addButton(words["cancel"], QDialogButtonBox.ButtonRole.RejectRole)
        if export_cb:
            self.export_button = buttons.addButton(words["export"], QDialogButtonBox.ButtonRole.ActionRole)
            self.export_button.clicked.connect(export_cb)
        if import_cb:
            self.import_button = buttons.addButton(words["import"], QDialogButtonBox.ButtonRole.ActionRole)
            self.import_button.clicked.connect(lambda: (import_cb(), self.reject()))
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(560, 460)
        self.tabs.setFocus()
        self.responses: list = []

    def _control(self, f: dict, value):
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
            key = c["key"] or self.words["no_key"]
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
        current = self.session.settings.values
        for field_id, control in self.controls.items():
            value = self._value(control)
            if value != current.get(field_id):
                self.responses.append(self.session.run("settings.set", field=field_id, value=value))
        self.accept()
