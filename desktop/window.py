"""The main window: the four regions (UX section 2) around one map session.

Tab and Shift+Tab move between the map, the Information panel and Details,
wrapping round. Alt reaches the menu bar, and Tab leaves it (DP93). Every key
and menu entry comes from the command registry (AD-3), and every word from the
core's templates (3.4). This module only translates: keys and clicks into
commands, responses into speech, sound, painting and focus.

Keys are handled in one place, an application-wide key filter, which asks the
session what a key means in the focused region. So remapped keys, the key
describer and F1 for the focused region all work the same everywhere.

Holding an arrow key (ANN-3, DP129, DP140): the first press is described at
once. Then the window's own hold clock, a small thread, makes each step, with
its click, at the times the core gives; the system's key repeats only show that the key is
still down. Speech is held back, and when the key is let go only the final
place is spoken. The map is drawn in a thread of its own (map_widget.py), so a
slow drawing never delays a click.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow, QMenu, QPlainTextEdit, QSplitter,
                               QTreeWidgetItem)

from desktop import storage
from desktop.announcer import Announcer
from desktop.dialogs import HistoryDialog, InputDialog, ListDialog, SettingsDialog, SoundsDialog, TextDialog
from desktop.keys import key_name
from desktop.map_widget import MapWidget
from desktop.panel_tree import PanelTree
from desktop.sounds import SoundPlayer
from mapcore.commands import registry
from mapcore.session import HOLD_SILENCE_S, MapSession, Response

ITEM_ID = Qt.ItemDataRole.UserRole
TOGGLES = {"step.link": lambda s: s.world.link, "sound.mute": lambda s: s.settings["mute"],
           "help.describer": lambda s: s.describing}


class _HoldClock(QObject):
    """The held key's clock (P2-T14, DP140): a thread of its own sleeps until
    each step is due and then tells the window at once. Qt's timers on Windows
    keep to a 15.6 ms beat, which made the clicks uneven by up to 16 ms; Python's
    sleep is exact to about a millisecond."""

    due = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._wake = threading.Condition()
        self._at: float | None = None
        self._stopped = False
        self._thread = threading.Thread(target=self._run, name="held key clock", daemon=True)
        self._thread.start()

    def arm(self, at: float) -> None:
        """Send due at time.perf_counter() == at."""
        with self._wake:
            self._at = at
            self._wake.notify()

    def cancel(self) -> None:
        with self._wake:
            self._at = None
            self._wake.notify()

    def stop(self) -> None:
        with self._wake:
            self._stopped = True
            self._at = None
            self._wake.notify()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while True:
            with self._wake:
                while self._at is None and not self._stopped:
                    self._wake.wait()
                if self._stopped:
                    return
                at = self._at
            left = at - time.perf_counter()
            if left > 0:
                time.sleep(min(left, 0.05))   # in short sleeps, so a new time or a cancel is seen soon
                continue
            with self._wake:
                if self._at != at:
                    continue
                self._at = None
            self.due.emit()


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


class _KeyFilter(QObject):
    """Every key press and release in the main window goes through here."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._window = window

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            return False
        window = self._window
        if QApplication.activeWindow() is not window or QApplication.activePopupWidget() is not None \
                and kind == QEvent.Type.KeyRelease:
            return False
        if kind == QEvent.Type.KeyRelease:
            return window.key_released(event)
        return window.key_pressed(event)


class MainWindow(QMainWindow):
    REGIONS = ("map", "panel", "details")  # Tab never goes to the menu bar (DP93)

    def __init__(self, session: MapSession | None = None, announcer=None, sounds=None, data_folder=None,
                 install_filter: bool = True, start_at: str | None = None):
        super().__init__()
        self.data_folder = data_folder
        self.session = session or self._new_session(start_at)
        self.words = self.session.words()
        self.setWindowTitle(self.words["window_title"])
        self.announcer = announcer or Announcer(self)
        self.sounds = sounds if sounds is not None else SoundPlayer()
        self._registry = self.session.registry()
        self._dialogs: list[QDialog] = []
        self._held_key: str | None = None
        self._held_seen = 0.0              # when the system last said the held key is down
        self._hold_clock = _HoldClock(self)
        self._hold_clock.due.connect(self._hold_step)
        self.spoken_times: list[float] = []

        self.map = MapWidget(self, self.session)
        # Our own tree accessibility, so NVDA says level 1 for a group and level 2
        # for an item in it (DP135, INF-10). See desktop/panel_tree.py.
        self.tree = PanelTree()
        self.tree.setObjectName("panel")
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName(self.words["panel"])
        self.tree.currentItemChanged.connect(self._tree_item_changed)
        self.details = QPlainTextEdit()
        self.details.setObjectName("details")
        self.details.setReadOnly(True)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard
                                             | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.setTabChangesFocus(True)
        self.details.setAccessibleName(self.words["details"])
        # One entry, one line. A wrapped entry made NVDA read it again on each
        # screen line when arrowing down (PO feedback on spike S5).
        self.details.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        side = QSplitter(Qt.Orientation.Vertical)
        side.addWidget(self.tree)
        side.addWidget(self.details)
        main = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(self.map)
        main.addWidget(side)
        main.setStretchFactor(0, 3)
        main.setStretchFactor(1, 1)
        main.setSizes([800, 400])
        self.setCentralWidget(main)

        self._menu_filter = _MenuTabFilter(self)
        self.actions_by_name: dict[str, QAction] = {}
        self._build_menus()
        self.menuBar().setAccessibleName(self.words["menu_bar"])
        self.resize(1200, 800)

        self._key_filter = _KeyFilter(self)
        if install_filter:
            QApplication.instance().installEventFilter(self._key_filter)

        self.preload_sounds()
        self.handle(self.session.start())
        self.map.setFocus()

    def preload_sounds(self) -> None:
        """Every earcon loaded and the sound device opened before the first step."""
        from mapcore.describe import earcon_list

        preload = getattr(self.sounds, "preload", None)
        if preload is not None:
            preload([self.session.earcon_file(e["event"]) for e in earcon_list()])

    def _new_session(self, start_at: str | None = None) -> MapSession:
        saved = storage.load(self.data_folder)
        return MapSession(platform="desktop", packs=storage.find_packs(self.data_folder),
                          settings=saved.get("settings"), saved_state=saved.get("state"), start_at=start_at)

    def closeEvent(self, event):
        self.save()
        self._hold_clock.stop()
        QApplication.instance().removeEventFilter(self._key_filter)
        self.map.stop_drawing()
        self.session.store.close()
        super().closeEvent(event)

    def save(self) -> None:
        """Settings, changed keys and the last place, zoom and step (PLT-5)."""
        storage.save(self.session.save(), self.data_folder)

    # Menus, from the registry -------------------------------------------

    def _build_menus(self):
        self.menuBar().clear()
        self.actions_by_name.clear()
        for menu in self._registry["menus"]:
            qmenu: QMenu = self.menuBar().addMenu(self._with_access(menu["label"], menu.get("access", "")))
            qmenu.installEventFilter(self._menu_filter)
            for item in menu["items"]:
                name = item["name"]
                text = f"{item['label']}\t{item['key_text']}" if item["key"] else item["label"]
                action = QAction(text, self)
                if item["toggle"]:
                    action.setCheckable(True)
                    action.setChecked(bool(TOGGLES[name](self.session)))
                action.triggered.connect(lambda _checked=False, n=name: self._menu_command(n))
                qmenu.addAction(action)
                self.actions_by_name[name] = action

    def _refresh_toggles(self):
        for name, getter in TOGGLES.items():
            action = self.actions_by_name.get(name)
            if action is not None:
                action.setChecked(bool(getter(self.session)))

    @staticmethod
    def _with_access(label: str, letter: str) -> str:
        """Mark the access letter with "&", so Alt+letter opens the menu."""
        i = label.lower().find(letter.lower()) if letter else -1
        return label if i < 0 else f"{label[:i]}&{label[i:]}"

    def _menu_command(self, name: str):
        self.dispatch(name)
        if self.focusWidget() is None or self.focusWidget() is self.menuBar():
            self.map.setFocus()

    # Focus between the regions -------------------------------------------

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
        if current == "menu":  # leaving the menu bar: on to the map, or back to Details
            self.focus_region("map" if forward else "details")
            return True
        i = self.REGIONS.index(current)
        self.focus_region(self.REGIONS[(i + (1 if forward else -1)) % len(self.REGIONS)])
        return True

    # Keys -----------------------------------------------------------------

    def key_pressed(self, event) -> bool:
        """Returns True when the key was ours. Keys in dialogs and other windows are never touched."""
        name = key_name(event)
        if name is None or name in ("Tab", "Shift+Tab") and not self.session.describing:
            return False
        region = self.region_of(QApplication.focusWidget()) or "map"
        started = time.time()
        command = registry.command_for_key("desktop", name, region, self.session.settings.keys)
        if command is None and not self.session.describing:
            return False
        held = command is not None and not self.session.describing and command.held
        if held:
            if event.isAutoRepeat():   # the hold timer steps; a repeat only shows the key is still down
                if self._held_key == command.name:
                    self._held_seen = time.perf_counter()
                return True
            self._held_key = command.name
            self._held_seen = time.perf_counter()
        response = self.session.press(name, region)
        if response is None:
            return False
        self.handle(response, key_at=started)
        if held:
            self._arm_hold()
        return True

    def key_released(self, event) -> bool:
        if event.isAutoRepeat() or self._held_key is None:
            return False
        key = key_name(event)
        command = registry.command_for_key("desktop", key, "map", self.session.settings.keys) if key else None
        if command is not None and command.name == self._held_key:
            self.release_held()
        return False

    def release_held(self) -> None:
        """The held key or the drag ended: only the final place is spoken, and it interrupts older speech (ANN-3)."""
        self._held_key = None
        self._hold_clock.cancel()
        self.handle(self.session.release())

    def _arm_hold(self) -> None:
        due = self.session.hold_due()
        if due is not None and self._held_key is not None:
            self._hold_clock.arm(time.perf_counter() + due)

    def _hold_step(self) -> None:
        """The hold clock: the next step and its click, on time (DP129, DP140)."""
        if self._held_key is None:
            return
        if time.perf_counter() - self._held_seen > HOLD_SILENCE_S:
            self.release_held()   # the key was let go without our hearing of it
            return
        self.handle(self.session.run(self._held_key, held=True, repeat=True))
        self._arm_hold()

    def changeEvent(self, event):
        # Another window took the keyboard while a key was held: its release will never come here.
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow() and self._held_key:
            self.release_held()
        super().changeEvent(event)

    # Commands and responses ---------------------------------------------

    def dispatch_key(self, key: str, region: str) -> bool:
        response = self.session.press(key, region)
        if response is None:
            return False
        self.handle(response)
        return True

    def dispatch(self, name: str, **args):
        self.handle(self.session.run(name, **args))

    def handle(self, response, key_at: float | None = None):
        for a in response.announcements:
            if a["channel"] == "braille":
                if not self.announcer.braille(a["text"]):
                    self.announcer.speak(a["fallback"], "polite")
            else:
                self.announcer.speak(a["text"], a["priority"])
                self.spoken_times.append(time.time())
        for event in response.earcons:
            self._play(event)
        if response.announcements or response.earcons:
            from mapcore import diagnostics

            diagnostics.add_shell(self.session, key_pressed_at=key_at, handed_over_at=time.time())
        if response.redraw:
            self.map.redraw()
        if response.panel_stale:
            self.map.refresh_name()
            self._fill_tree()
        if response.details_stale:
            self.details.setPlainText(self.session.details())
        if response.settings_changed:
            self.save()
            self._registry = self.session.registry()
            self._build_menus()
        self._refresh_toggles()
        if response.focus:
            self._apply_focus(response.focus)
        if response.dialog:
            self._open_dialog(response.dialog)
        if response.action == "exit":
            self.close()

    def _play(self, event: str) -> None:
        played, custom_failed = self.sounds.play(self.session.earcon_file(event))
        if custom_failed:
            self.handle(self.session.earcon_failed(event))

    def _apply_focus(self, focus: dict):
        if focus["region"] == "map":
            self.map.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        if focus["region"] == "details":
            self.details.moveCursor(self.details.textCursor().MoveOperation.Start)
            self.details.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        if focus["region"] == "menu":
            self.focus_region("menu")
            return
        if focus["region"] == "panel":
            target = self._item_by_id(focus.get("item")) if focus.get("item") else None
            if target is None:
                group = self._group_item(focus.get("group") or "within")
                target = group.child(0) if group is not None and group.childCount() else group
            if target is not None:
                if target.parent() is not None:
                    target.parent().setExpanded(True)
                self.tree.setCurrentItem(target)
            self.tree.setFocus(Qt.FocusReason.OtherFocusReason)

    # Dialogs --------------------------------------------------------------

    def _open_dialog(self, dialog: dict):
        kind = dialog.get("kind", "text")
        if dialog.get("copy"):
            QGuiApplication.clipboard().setText(dialog["copy"])
        if kind == "settings":
            box = SettingsDialog(self, self.session, self.words, export_cb=self._export_settings,
                                 import_cb=self._import_settings)
            box.finished.connect(lambda _r, b=box: [self.handle(r) for r in b.responses])
        elif kind == "sounds":
            box = SoundsDialog(self, dialog["title"], dialog["items"], dialog["play"], self.words["close"],
                               play=lambda event: self.dispatch("sound.preview", event=event))
        elif kind == "history":
            box = HistoryDialog(self, dialog["title"], dialog["lines"], self.words["close"], dialog["help"],
                                go=lambda index: self.session.run(dialog["go"], index=index),
                                speak=lambda text: self.announcer.speak(text, "assertive"))
            box.accepted.connect(lambda b=box: self.handle(b.response))
        elif kind == "input":
            box = InputDialog(self, dialog, submit=lambda text: self.session.run(dialog["submit"], text=text),
                              speak=lambda text: self.announcer.speak(text, "assertive"))
            box.accepted.connect(lambda b=box: self.handle(b.response))
        else:
            box = TextDialog(self, dialog["title"], dialog["text"], self.words["close"])
        self._dialogs.append(box)
        box.finished.connect(lambda _r, b=box: self._dialog_closed(b))
        box.open()

    def _dialog_closed(self, box):
        if box in self._dialogs:
            self._dialogs.remove(box)
        self.map.setFocus()

    def _export_settings(self):
        path, _ = QFileDialog.getSaveFileName(self, self.words["export"], "tobymap-settings.json", "JSON (*.json)")
        if path:
            storage.export_to(self.session.save(), Path(path))

    def _import_settings(self):
        path, _ = QFileDialog.getOpenFileName(self, self.words["import"], "", "JSON (*.json)")
        if not path:
            return
        try:
            data = storage.import_from(Path(path))
        except (OSError, ValueError):
            return
        storage.save(data, self.data_folder)
        saved = storage.load(self.data_folder)
        self.session.settings = type(self.session.settings).from_dict(saved.get("settings"))
        self.session.world.use_units(self.session.settings["units"])
        self.session.world.restore(saved.get("state", self.session.world.to_dict()))
        self.session.areas = self.session._here()
        self.handle(self.session.run("where.am_i"))
        self.handle(Response(redraw=True, panel_stale=True, details_stale=True, settings_changed=True))

    # The Information panel ------------------------------------------------

    def _group_item(self, group_id: str | None):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, ITEM_ID) == f"group:{group_id}":
                return item
        return None

    def _item_by_id(self, item_id: str):
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                if group.child(j).data(0, ITEM_ID) == item_id:
                    return group.child(j)
        return None

    def _fill_tree(self):
        """Bring the tree up to date in place: existing items keep their identity and only
        change their words, so NVDA reads the item F3 moves to without Up then Down."""
        groups = self.session.panel()
        self.tree.blockSignals(True)
        try:
            while self.tree.topLevelItemCount() > len(groups):
                self.tree.takeTopLevelItem(self.tree.topLevelItemCount() - 1)
            for gi, group in enumerate(groups):
                if gi < self.tree.topLevelItemCount():
                    g = self.tree.topLevelItem(gi)
                else:
                    g = QTreeWidgetItem()
                    self.tree.addTopLevelItem(g)
                    g.setExpanded(group["id"] == "within")
                g.setText(0, group["label"])
                g.setData(0, ITEM_ID, f"group:{group['id']}")
                items = group["items"] or ([{"id": None, "label": group["empty"]}] if group["empty"] else [])
                while g.childCount() > len(items):
                    g.takeChild(g.childCount() - 1)
                for ii, item in enumerate(items):
                    child = g.child(ii) if ii < g.childCount() else None
                    if child is None:
                        child = QTreeWidgetItem()
                        g.addChild(child)
                    if child.text(0) != item["label"]:
                        child.setText(0, item["label"])
                    child.setData(0, ITEM_ID, item["id"])
        finally:
            self.tree.blockSignals(False)

    def _tree_item_changed(self, current, _previous):
        item_id = current.data(0, ITEM_ID) if current is not None else None
        if item_id is not None and str(item_id).startswith("group:"):
            item_id = None
        self.dispatch("panel.select", item=item_id)
