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
from desktop.dialogs import ConfirmBox, HistoryDialog, InputDialog, LayersDialog, ListDialog, SettingsDialog, SoundsDialog, TextDialog
from desktop.keys import key_name
from desktop.map_widget import MapWidget
from desktop.panel_tree import PanelTree
from desktop.sounds import SoundPlayer
from mapcore.commands import registry
from mapcore.session import HOLD_SILENCE_S, MapSession, Response

ITEM_ID = Qt.ItemDataRole.UserRole


class _Beacon(QObject):
    """The orientation beacon (P2-T9, P2-T16h; SON-10): the core's beacon, handed to the sound
    player, which plays it at once and then every interval on the sound card's own clock, so
    drawing the map after a turn never delays a beat. Each response's beacon replaces the sound
    from the next beat on, so a turn or a step moves it without a new beat. A response's beacon
    of None changes nothing; a placed sound of None stops it."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._window = window

    def update(self, beacon: dict | None) -> None:
        if beacon is None:
            return
        if beacon["placed"] is None:
            self.stop()
            return
        self._window._beat(beacon["placed"], beacon["interval_s"])

    def stop(self) -> None:
        self._window.spatial.stop_beat()


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
            self._fire()

    def _fire(self) -> None:
        """Woken: tell the window. A method of its own so a test can see when the clock woke."""
        self.due.emit()


class _Background(QObject):
    """Crossed and passed (P2-T5, architecture 7.5): the search along a move's path runs on a
    thread of its own, so the announcement never waits for it. The result comes back to the
    window's thread through a signal. A newer move makes the core throw an older search away.
    stop() ends a search before the window closes the store it reads (P2-T17w)."""

    done = Signal(object, object)

    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self.thread: threading.Thread | None = None
        self._stopping = threading.Event()

    def start(self) -> None:
        if self._stopping.is_set():
            return
        job = self.session.crossed_job()
        if job is None:
            return
        self.thread = threading.Thread(target=self._run, args=(job,), name="crossed and passed", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Tell the search to stop, and wait for it. Closing the store under a search still
        reading it made Windows stop the program with a memory fault."""
        self._stopping.set()
        if self.thread is not None:
            self.thread.join(timeout=10)

    def _run(self, job) -> None:
        try:
            found = self.session.crossed_search(job, cancelled=self._stopping.is_set)
        except Exception:   # a damaged pack tile must never stop the window; the list stays empty
            found = None
        if not self._stopping.is_set():
            self.done.emit(job, found)


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
                 install_filter: bool = True, start_at: str | None = None, spatial=None, voice=None):
        super().__init__()
        self.data_folder = data_folder
        self.session = session or self._new_session(start_at)
        self.words = self.session.words()
        self.setWindowTitle(self.words["window_title"])
        self.announcer = announcer or Announcer(self)
        # Sounds placed in space (P2-T6b). A window given stand-in sounds, as in the tests, never
        # opens the sound device (rule 5).
        if spatial is None:
            from desktop.audio.player import RecordingSpatial, SpatialPlayer

            spatial = SpatialPlayer() if sounds is None else RecordingSpatial()
        self.spatial = spatial
        # The earcons go through the same mixer (P2-T16h).
        self.sounds = sounds if sounds is not None else SoundPlayer(spatial)
        # The spatial voice (P2-T7a): loaded on a thread of its own while TobyMap starts.
        if voice is None:
            from desktop.audio.voice import RecordingVoice, SpatialVoice

            voice = SpatialVoice(spatial) if sounds is None else RecordingVoice()
        self.voice = voice
        self._told: set[str] = set()   # sound problems already told, each said once
        self._registry = self.session.registry()
        self._dialogs: list[QDialog] = []
        self._answer_words: list[str] | None = None   # while a dialog's answer is carried out (P2-T17c)
        self._said_on_return: list[str] = []          # what it said, for the map's name as focus comes back
        self._opened_in: dict = {}                     # each open dialog: the region it was opened in
        self._held_key: str | None = None
        self._held_seen = 0.0              # when the system last said the held key is down
        self._hold_clock = _HoldClock(self)
        self._hold_clock.due.connect(self._hold_step)
        self._beacon = _Beacon(self)
        self._background = _Background(self, self.session)
        self._background.done.connect(lambda job, found: self.handle(self.session.crossed_finish(job, found)))
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
        # The start is not spoken: as the window appears, NVDA reads its title and then the map's
        # name, which cut the start off, so "Press F1 for keys" was never heard. The map is named
        # with the rest of the start instead, so it is heard once, in full (P2-T17d, checklist 1.2).
        # Shift+Space still repeats it.
        self._carry_out_answer([self.session.start()])
        self._said_on_return = []
        self.map.name_at_start()
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
        self._beacon.stop()
        QApplication.instance().removeEventFilter(self._key_filter)
        self.map.stop_drawing()
        self.voice.close()
        self.spatial.close()
        self._background.stop()   # before the store it reads is closed (P2-T17w)
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
                    action.setChecked(bool(self.session.toggles().get(name)))
                action.triggered.connect(lambda _checked=False, n=name: self._menu_command(n))
                qmenu.addAction(action)
                self.actions_by_name[name] = action

    def _refresh_toggles(self):
        for name, on in self.session.toggles().items():
            action = self.actions_by_name.get(name)
            if action is not None:
                action.setChecked(on)

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
        # Focus moved within the window, as after Enter on an item of the Information panel, goes
        # first: the screen reader stops speaking when the focus moves, so the place said after the
        # move is heard (P2-T17k). The panel is brought up to date first, so the item is there.
        focus_first = bool(response.focus) and response.focus["region"] in ("panel", "details")
        if focus_first:
            self._refresh_regions(response)
            self._apply_focus(response.focus)
        for a in response.announcements:
            if a["channel"] == "braille":
                if not self.announcer.braille(a["text"]) and a.get("fallback"):
                    self.announcer.speak(a["fallback"], "polite")
            elif self._answer_words is not None:
                self._answer_words.append(a["text"])   # said once, by the map's name, as the dialog closes
                self.spoken_times.append(time.time())
            else:
                self.announcer.speak(a["text"], a["priority"])
                self.spoken_times.append(time.time())
        for event in response.earcons:
            self._play(event)
        for placed in response.sounds:
            self._play_placed(placed)
        if response.voice:
            self._say(response.voice, self.spatial.last_end if response.voice["after"] and response.sounds else None)
        self._beacon.update(response.beacon)
        if response.announcements or response.earcons:
            from mapcore import diagnostics

            diagnostics.add_shell(self.session, key_pressed_at=key_at, handed_over_at=time.time())
        if response.redraw:
            self.map.redraw()
        if not focus_first:
            self._refresh_regions(response)
        if response.settings_changed:
            self.save()
            self._registry = self.session.registry()
            self._build_menus()
        self._refresh_toggles()
        if response.focus and not focus_first:
            self._apply_focus(response.focus)
        if response.dialog:
            self._open_dialog(response.dialog)
        if response.action == "exit":
            self.close()
        if response.background:
            self._background.start()

    def _refresh_regions(self, response) -> None:
        if response.panel_stale:
            self.map.refresh_name()
            self._fill_tree()
        if response.details_stale:
            self.details.setPlainText(self.session.details())

    def _play(self, event: str) -> None:
        info = self.session.earcon_file(event)
        played, custom_failed = self.sounds.play(info)
        self._tell_own_file_failed(info, custom_failed)

    def _tell_own_file_failed(self, info: dict, failed: bool) -> None:
        """Your own file could not be played, so the default was: said once for each file,
        not at every step (SON-8)."""
        told = f"own_file {info['event']} {info.get('custom')}"
        if failed and told not in self._told:
            self._told.add(told)
            self.handle(self.session.earcon_failed(info["event"]))

    def _say(self, voice: dict, start_frame: int | None) -> None:
        """A label in the spatial voice (P2-T7). While the voice is starting, each label says so;
        a voice that is missing or would not start is told once."""
        state = self.voice.say(voice, start_frame)
        if state == "loading" or (state in ("missing", "failed") and f"voice_{state}" not in self._told):
            self._told.add(f"voice_{state}")
            self.handle(self.session.voice_problem(state))

    def _play_placed(self, placed: dict, tag: str | None = None) -> None:
        """A sound placed in space by the core (P2-T6). A missing sound device, or HRTF data, is
        told once, in the core's words, and the sound carries on as well as it can. A tag stops
        the last sound with the same tag, so they never pile up."""
        _played, custom_failed = self.spatial.play(placed, tag=tag)
        self._tell_placed_problems(placed, custom_failed)

    def _beat(self, placed: dict, interval_s: float) -> None:
        """The beacon's sound, repeated by the sound player (P2-T16h)."""
        _played, custom_failed = self.spatial.beat(placed, interval_s)
        self._tell_placed_problems(placed, custom_failed)

    def _tell_placed_problems(self, placed: dict, custom_failed: bool) -> None:
        self._tell_own_file_failed(placed["file"], custom_failed)
        for problem, happened in (("no_device", self.spatial.missing), ("no_hrtf", self.spatial.hrtf_missing)):
            if happened and problem not in self._told:
                self._told.add(problem)
                self.handle(self.session.sound_problem(problem))

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
            target = self._item_by_id(focus.get("item"), focus.get("group")) if focus.get("item") else None
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
            box.finished.connect(lambda _r, b=box: [self.handle(r) for r in b.responses])   # never moves you
        elif kind == "sounds":
            box = SoundsDialog(self, dialog["title"], dialog["items"], dialog["play"], self.words["close"],
                               play=lambda event: self.dispatch("sound.preview", event=event))
        elif kind == "history":
            box = HistoryDialog(self, dialog["title"], dialog["lines"], self.words["close"], dialog["help"],
                                go=lambda index: self.session.run(dialog["go"], index=index),
                                speak=lambda text: self.announcer.speak(text, "assertive"),
                                current=dialog.get("current", 0))
            box.accepted.connect(lambda b=box: self._carry_out_answer([b.response]))
        elif kind == "layers":
            box = LayersDialog(self, dialog, check=lambda low, high: self.session.run(dialog["check"], low=low, high=high),
                               speak=lambda text: self.announcer.speak(text, "assertive"))
            box.accepted.connect(lambda b=box: self._carry_out_answer(
                self.session.run(dialog["set"], layer=i, values=v) for i, v in b.changes()))
        elif kind == "input":
            box = InputDialog(self, dialog, submit=lambda text: self.session.run(dialog["submit"], text=text))
            box.accepted.connect(lambda b=box: self._carry_out_answer([b.response]))
        elif kind == "confirm":   # a question, such as Reset all settings (P2-T18h)
            box = ConfirmBox(self, dialog)
            box.finished.connect(lambda _r, b=box: b.confirmed and self._carry_out_answer(
                [self.session.run(dialog["submit"])]))
        else:
            box = TextDialog(self, dialog["title"], dialog["text"], self.words["close"])
        self._dialogs.append(box)
        # The focus goes back to where the box was opened: the Information panel or Details, or else
        # the map (P2-T17k, desktop checklist 10.5).
        opened_in = self.region_of(QApplication.focusWidget())
        self._opened_in[box] = opened_in if opened_in in ("panel", "details") else "map"
        box.finished.connect(lambda _r, b=box: self._dialog_closed(b))
        box.open()

    def _carry_out_answer(self, responses) -> None:
        """A dialog's answer, such as Go to's place or the layers changed. What it says is kept, not
        spoken: the dialog closes into the map, and NVDA reads the map's name as the focus arrives,
        so speaking it too said the place twice (P2-T17c, desktop checklist 5.2, 5.4, 7.4)."""
        self._answer_words = []
        try:
            for r in responses:
                self.handle(r)
        finally:
            self._said_on_return.extend(self._answer_words)
            self._answer_words = None

    def _dialog_closed(self, box):
        """The focus comes back to the map, named with what the dialog's answer said, or else with
        the place as it is now, after the dialog's changes: said once, and never the old place."""
        if box in self._dialogs:
            self._dialogs.remove(box)
        said, self._said_on_return = self._said_on_return, []
        region = self._opened_in.pop(box, "map")
        if region != "map":
            # Back in the panel or Details, the focus arrives on an item or the text, which the
            # screen reader reads; what the answer said follows it, spoken (P2-T17k).
            (self.tree if region == "panel" else self.details).setFocus(Qt.FocusReason.OtherFocusReason)
            for text in said:
                self.announcer.speak(text, "assertive")
            return
        self.map.name_on_return(" ".join(said) or None)
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

    def _item_by_id(self, item_id: str, group_id: str | None = None):
        """An area can be in two groups, so the item is looked for in its own group first."""
        groups = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        groups.sort(key=lambda g: g.data(0, ITEM_ID) != f"group:{group_id}")
        for group in groups:
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
        parent = current.parent() if current is not None else None
        # A group heading is in its own group: Go to comes back to it (P2-T17k).
        heading = current if current is not None and parent is None else parent
        group = str(heading.data(0, ITEM_ID)).removeprefix("group:") if heading is not None else None
        self.dispatch("panel.select", item=item_id, group=group)
