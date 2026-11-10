"""The desktop window, offscreen, with a recording announcer and recording sounds (UX section 2, ACC-1, ACC-7, ANN-3)."""
import json
import time

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QImage, QKeyEvent, QPainter
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import (HistoryDialog, InputDialog, KeyCaptureDialog, LayerSettingsDialog, LayersDialog, ListDialog,
                             SettingsDialog, SoundsDialog,
                             TextDialog)
from desktop.map_widget import paint_scene
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


def make_window(qtbot, test_pack, tmp_path, state=None, **kw):
    session = MapSession(packs=[test_pack], saved_state=dict(state or KENT))
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path, **kw)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    return make_window(qtbot, test_pack, tmp_path)


def region(w):
    return w.region_of(QApplication.focusWidget() or w.focusWidget())


def key_event(kind, key, mods=Qt.KeyboardModifier.NoModifier, auto=False):
    return QKeyEvent(kind, key, mods, "", auto)


def click_dialog(window, cls):
    QApplication.processEvents()
    (dialog,) = [d for d in window.findChildren(cls) if d.isVisible()]
    return dialog


def test_start_is_the_map_name_as_focus_arrives_and_map_has_focus(window):
    # Spoken, the start was cut off by NVDA reading the window's title and the map's name as the
    # window appeared, so "Press F1 for keys" was never heard (P2-T17d, desktop checklist 1.2).
    assert window.announcer.texts == []
    assert region(window) == "map"
    assert window.map.accessibleName() == "Kent, England, United Kingdom. Press F1 for keys."
    assert window.windowTitle() == "TobyMap"
    assert window.session.history[0] == "TobyMap. Kent, England, United Kingdom. Press F1 for keys."
    assert window.tree.accessibleName() == "Information panel"
    assert window.details.accessibleName() == "Details"


def test_tab_cycles_the_three_regions_and_wraps(window, qtbot):
    seen = []
    for _ in range(3):
        qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab)
        seen.append(region(window))
    assert seen == ["panel", "details", "map"]
    qtbot.keyClick(window.map, Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier)
    assert region(window) == "details"


def test_tab_in_an_open_menu_closes_it_and_goes_to_the_map(window, qtbot):
    menu = window.menuBar().actions()[0].menu()
    menu.popup(window.mapToGlobal(window.rect().topLeft()))
    QApplication.processEvents()
    assert menu.isVisible()
    qtbot.keyClick(menu, Qt.Key.Key_Tab)
    assert not menu.isVisible()
    assert region(window) == "map"


def test_tab_from_details_backwards_reaches_the_panel(window, qtbot):
    window.focus_region("details")
    qtbot.keyClick(window.details, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
    assert region(window) == "panel"


def test_details_entries_are_one_line_each(window):
    window.details.setPlainText(window.session.details())
    window.resize(400, 300)
    QApplication.processEvents()
    block = window.details.document().begin()
    while block.isValid():
        assert block.layout().lineCount() == 1, block.text()
        block = block.next()


def test_arrow_keys_step_and_speak_and_tick(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Down)
    assert window.announcer.spoken[-1] == ("North Atlantic Ocean", "assertive")
    qtbot.keyClick(window.map, Qt.Key.Key_Down)
    qtbot.keyClick(window.map, Qt.Key.Key_Space)
    assert window.session.world.lat < 51.2                      # the location moved to the click
    assert window.announcer.texts[-1] == "North Atlantic Ocean"


def test_arrow_keys_in_the_tree_do_not_step(window, qtbot):
    window.focus_region("panel")
    before = (window.session.world.lat, window.session.world.lon)
    qtbot.keyClick(window.tree, Qt.Key.Key_Down)
    assert (window.session.world.lat, window.session.world.lon) == before


def test_f2_f3_f4_go_where_they_should_from_each_region(window, qtbot):
    for start in ("map", "panel", "details"):
        window.focus_region(start)
        qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_F4)
        assert region(window) == "details"
        qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_F3)
        assert region(window) == "panel"
        qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_F2)
        assert region(window) == "map"
    window.focus_region("menu")
    qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_F2)
    assert region(window) == "map"


def test_f3_lands_on_within_first_and_then_on_the_item_last_focused(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_F3)
    assert window.tree.currentItem().text(0) == "Kent, centre 35 kilometres west"
    assert window.details.toPlainText().splitlines()[0] == "Kent"
    window.tree.setCurrentItem(window.tree.topLevelItem(1).child(0))
    qtbot.keyClick(window.tree, Qt.Key.Key_F2)
    qtbot.keyClick(window.map, Qt.Key.Key_F3)
    assert window.tree.currentItem().parent().text(0).startswith("Nearby, ")


def test_an_area_in_two_groups_is_selected_and_heard_in_the_group_focused(qtbot, test_pack, tmp_path):
    """Phase 2 web checklist: the River Itchen, just crossed, is in Nearby and in Crossed and
    passed. Each item says its own group, so each is heard from its own place, and F3 goes
    back to the one last focused."""
    w = make_window(qtbot, test_pack, tmp_path, state={"lat": 50.9074977, "lon": -1.4442289,
                                                         "zoom_m": 10000, "step_m": 1000})
    for _ in range(5):
        w.dispatch("move.east")
    near, crossed = w._group_item("nearby").child(0), w._group_item("crossed").child(0)
    qtbot.waitUntil(lambda: crossed.text(0).startswith("River Itchen"), timeout=5000)
    assert near.text(0) == "River Itchen, 320 metres north-west"
    assert crossed.text(0) == "River Itchen, crossed, 730 metres west"
    for item, said in ((near, "River Itchen, 320 metres"), (crossed, "River Itchen, 730 metres")):
        w.tree.setCurrentItem(item)
        assert w.session.run("panel.hear").voice["text"] == said
    qtbot.keyClick(w.tree, Qt.Key.Key_F2)
    qtbot.keyClick(w.map, Qt.Key.Key_F3)
    assert w.tree.currentItem() is crossed


def test_space_on_a_group_heading_says_it_works_on_an_item(window, qtbot):
    """P2-T17f, desktop checklist 11.6: Space on a group heading, after an item, said that
    item again instead of where Hear its direction works."""
    window.focus_region("panel")
    within = window._group_item("within")
    window.tree.setCurrentItem(within.child(0))
    qtbot.keyClick(window.tree, Qt.Key.Key_Space)
    window.tree.setCurrentItem(within)
    qtbot.keyClick(window.tree, Qt.Key.Key_Space)
    assert window.announcer.texts[-1] == "Hear its direction works on an item, not on a group."
    assert window.session.history[-1] == "Hear its direction works on an item, not on a group."


def test_the_panel_keeps_its_items_when_refreshed(window):
    window.session.world.step_index = 0
    first = window.tree.topLevelItem(0).child(0)
    ids = [window.tree.topLevelItem(g) for g in range(window.tree.topLevelItemCount())]
    window.dispatch("move.north")
    assert window.tree.topLevelItem(0).child(0) is first       # changed in place, not rebuilt
    assert [window.tree.topLevelItem(g) for g in range(len(ids))] == ids


def test_panel_items_are_one_level_below_their_groups(window):
    for g in range(window.tree.topLevelItemCount()):
        group = window.tree.topLevelItem(g)
        assert group.parent() is None
        for i in range(group.childCount()):
            assert group.child(i).parent() is group     # NVDA says "level 2" for these


def test_menus_come_from_the_registry(window):
    bar = window.menuBar()
    assert [a.text() for a in bar.actions()] == ["&Map", "&Speech", "Se&ttings", "&Help"]
    texts = [a.text() for a in bar.actions()[0].menu().actions()]
    assert "Step north or forward\tUp" in texts and "Exit" in texts and "Link step to zoom	S" in texts
    assert window.actions_by_name["step.link"].isCheckable()


def test_menu_command_runs_through_the_core(window):
    window.actions_by_name["where.coordinates"].trigger()
    assert window.announcer.texts[-1] == "51.2 degrees north, 1.2 degrees east"   # step 25 km


def test_the_link_menu_item_shows_its_state(window):
    window.actions_by_name["step.link"].trigger()
    assert window.session.world.link and window.actions_by_name["step.link"].isChecked()
    assert window.announcer.texts[-1].startswith("Step linked to zoom.")


def test_s_then_page_up_says_the_zoom_and_the_step(window, qtbot):
    """Desktop and web checklist 16.2 (P2-T17j, NAV-2, NAV-13): linked by S, Page Up says
    both, even from 25 to 50 kilometres, where the step stays at 5 kilometres."""
    qtbot.keyClick(window.map, Qt.Key.Key_S)
    assert window.announcer.texts[-1].startswith("Step linked to zoom.")
    qtbot.keyClick(window.map, Qt.Key.Key_PageUp)
    assert window.announcer.texts[-1] == "Zoom 50 kilometres, step 5 kilometres."
    qtbot.keyClick(window.map, Qt.Key.Key_PageUp)
    assert window.announcer.texts[-1] == "Zoom 100 kilometres, step 25 kilometres."


def test_braille_test_falls_back_to_speech_without_nvda(window):
    window.actions_by_name["speech.braille_test"].trigger()
    assert window.announcer.texts[-1] == "Braille-only messages need NVDA, and it was not found."


def test_braille_test_goes_to_braille_when_nvda_is_there(qtbot, test_pack, tmp_path):
    announcer = RecordingAnnouncer(braille_works=True)
    session = MapSession(packs=[test_pack], saved_state=dict(KENT))
    w = MainWindow(session=session, announcer=announcer, sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.actions_by_name["speech.braille_test"].trigger()
    assert announcer.brailled == ["TobyMap Braille test: Kent, England, United Kingdom"]


def test_f1_opens_a_dialog_for_the_focused_region_with_a_close_button(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_F1)
    dialog = click_dialog(window, TextDialog)
    assert dialog.windowTitle() == "Keys" and "Step north or forward: Up" in dialog.text.toPlainText()
    assert dialog.close_button.text() == "Close"
    dialog.close_button.click()
    QApplication.processEvents()
    assert not dialog.isVisible() and region(window) == "map"
    window.activateWindow()
    QApplication.processEvents()
    window.focus_region("panel")
    qtbot.keyClick(window.tree, Qt.Key.Key_F1)
    assert "Step north or forward" not in click_dialog(window, TextDialog).text.toPlainText()


def test_history_dialog_lists_the_announcements_with_a_close_button(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Space)
    qtbot.keyClick(window.map, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    dialog = click_dialog(window, ListDialog)
    assert dialog.list.item(0).text() == "Kent, England, United Kingdom"
    assert dialog.close_button.text() == "Close"


def test_the_key_describer_describes_and_does_nothing(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_F1, Qt.KeyboardModifier.ShiftModifier)
    qtbot.keyClick(window.map, Qt.Key.Key_Down)
    assert window.announcer.texts[-1] == "Down: Step south or back"
    assert window.session.world.lat == 51.2
    qtbot.keyClick(window.map, Qt.Key.Key_F1, Qt.KeyboardModifier.ShiftModifier)
    assert window.announcer.texts[-1] == "Key describer off."


def test_the_key_describer_catches_tab_and_works_in_every_region(window, qtbot):
    """PO feedback on checklist 2.2: Tab does nothing, and keys are described the same in the panel."""
    window.focus_region("panel")
    item = window.tree.currentItem()
    qtbot.keyClick(window.tree, Qt.Key.Key_F1, Qt.KeyboardModifier.ShiftModifier)
    qtbot.keyClick(window.tree, Qt.Key.Key_Tab)
    assert region(window) == "panel"
    assert window.announcer.texts[-1] == "Tab: no command."
    qtbot.keyClick(window.tree, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
    assert region(window) == "panel"
    assert window.announcer.texts[-1] == "Shift+Tab: no command."
    qtbot.keyClick(window.tree, Qt.Key.Key_Down)
    assert window.announcer.texts[-1] == "Down: Step south or back"
    assert window.tree.currentItem() is item
    qtbot.keyClick(window.tree, Qt.Key.Key_F1, Qt.KeyboardModifier.ShiftModifier)
    qtbot.keyClick(window.tree, Qt.Key.Key_Tab)
    assert region(window) == "details"


def hold_key(window, qtbot, key, seconds: float) -> None:
    """Hold a key in real time: the press, then the system's repeats every 33 ms, as Windows sends them."""
    w = window.map
    QApplication.sendEvent(w, key_event(QEvent.Type.KeyPress, key))
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        qtbot.wait(33)
        QApplication.sendEvent(w, key_event(QEvent.Type.KeyRelease, key, auto=True))
        QApplication.sendEvent(w, key_event(QEvent.Type.KeyPress, key, auto=True))


def test_holding_an_arrow_key_speaks_only_the_final_place_after_release(window, qtbot):
    """ANN-3: two seconds of key repeat, then let go."""
    announcer = window.announcer
    spoken_before = len(announcer.spoken)
    hold_key(window, qtbot, Qt.Key.Key_Down, 2.0)
    assert len(announcer.spoken) == spoken_before + 1, "only the press is spoken while the key is held"
    steps = round((51.2 - window.session.world.lat) / (25 / 111.2))
    assert 10 <= steps <= 11, steps         # the press, then 6 a second after the 500 ms delay (DP129)
    assert window.sounds.played.count("tick") >= steps - 1   # each repeated step ticks
    QApplication.sendEvent(window.map, key_event(QEvent.Type.KeyRelease, Qt.Key.Key_Down))
    assert len(announcer.spoken) == spoken_before + 2
    assert announcer.spoken[-1][1] == "assertive"       # it interrupts what the screen reader was still saying
    assert announcer.texts[-1] == "France"             # about 250 km south of Kent


def system_sleep_is_exact() -> bool:
    """Whether this computer wakes a sleeping thread on time. Windows and real Macs do, to
    about a millisecond. GitHub's macOS machines are virtual and do not: there even a bare
    time.sleep, with no window and no TobyMap code, woke 2 to 75 ms late (6 November 2026)."""
    for _ in range(4):
        t = time.perf_counter()
        time.sleep(0.05)
        if time.perf_counter() - t - 0.05 > 0.005:
            return False
    return True


def test_a_slow_drawing_never_delays_the_clicks_of_a_held_key(window, qtbot, monkeypatch):
    """DP140, P2-T14: each drawing takes 200 ms, yet a 3 second hold at 6 steps a
    second clicks within 10 ms of each due time. The map is drawn at most 4 times a
    second while the key is held, and once more after the release.

    On every computer, each click follows the clock's wake-up within 10 ms, so the
    drawing never holds it up. On a computer whose own sleep is not exact, the clock
    cannot wake on time, so the 10 ms from the due time is checked only where it is."""
    from desktop.window import _HoldClock

    exact = system_sleep_is_exact()
    woke = []
    fire = _HoldClock._fire
    monkeypatch.setattr(_HoldClock, "_fire", lambda clock: (woke.append(time.perf_counter()), fire(clock))[1])
    session = window.session
    real_scene = session.scene
    started = []

    def slow_scene(width, height):
        started.append(time.perf_counter())
        until = time.perf_counter() + 0.2
        while time.perf_counter() < until:   # Python busy for 200 ms, as a real drawing is
            sum(range(200))
        return real_scene(width, height)

    session.scene = slow_scene
    qtbot.waitUntil(window.map.drawing_done)
    ticks_before = len(window.sounds.times)
    pressed = time.perf_counter()
    hold_key(window, qtbot, Qt.Key.Key_Down, 0.0)
    first_due = time.perf_counter() + session.hold_due()
    end = pressed + 3.0
    while time.perf_counter() < end:
        qtbot.wait(33)
        QApplication.sendEvent(window.map, key_event(QEvent.Type.KeyRelease, Qt.Key.Key_Down, auto=True))
        QApplication.sendEvent(window.map, key_event(QEvent.Type.KeyPress, Qt.Key.Key_Down, auto=True))
    released = time.perf_counter()
    QApplication.sendEvent(window.map, key_event(QEvent.Type.KeyRelease, Qt.Key.Key_Down))
    qtbot.waitUntil(window.map.drawing_done, timeout=3000)
    qtbot.wait(50)

    ticks = [t for t, e in zip(window.sounds.times[ticks_before:], window.sounds.played[ticks_before:])
             if e == "tick" and t > first_due - 0.05]   # not the press's own, nor Crossed and passed's earcon
    due_before_release = sum(1 for k in range(40) if first_due + k / 6 < released)
    assert len(ticks) >= 15 and abs(len(ticks) - due_before_release) <= 1   # 2.5 seconds after the delay, 6 a second
    after_wake = [round((t - max(w for w in woke if w <= t)) * 1000, 1) for t in ticks]
    # The drawing never holds up a click. Where sleep is not exact, the window's own thread is
    # also woken late, by up to 11 ms on GitHub's Macs, so it has 25 ms there.
    assert all(d <= (10 if exact else 25) for d in after_wake), after_wake
    late = [round((t - (first_due + k / 6)) * 1000, 1) for k, t in enumerate(ticks)]
    if exact:
        assert all(-2 <= d <= 10 for d in late), late
    else:
        assert all(d >= -2 for d in late), late             # never early, even where the clock wakes late
    during = [t for t in started if pressed <= t < released]
    assert len(during) <= 3 * 4 + 1, during                          # at most 4 a second, and the press's own
    assert len([t for t in started if t >= released]) == 1           # one drawing of the final place
    assert window.announcer.texts[-1] == "France"


def test_a_step_is_announced_quickly(window, qtbot):
    times = []
    for _ in range(10):
        start = time.perf_counter()
        qtbot.keyClick(window.map, Qt.Key.Key_Left)
        times.append((time.perf_counter() - start) * 1000)
    assert sorted(times)[len(times) // 2] < 150   # NFR-1, offscreen, on the small test pack


def test_ctrl_comma_opens_settings_with_ok_and_cancel(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Comma, Qt.KeyboardModifier.ControlModifier)
    dialog = click_dialog(window, SettingsDialog)
    assert dialog.ok_button.text() == "OK" and dialog.cancel_button.text() == "Cancel"
    assert [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())] == \
        ["Units", "Movement", "Speech", "Layers", "Sound", "Earcons", "Display", "Keys"]
    dialog.controls["units"].setCurrentIndex(dialog.controls["units"].findData("imperial"))
    dialog.ok_button.click()
    QApplication.processEvents()
    assert window.session.settings["units"] == "imperial"


def test_tab_from_the_tabs_goes_straight_to_the_first_setting(window, qtbot):
    """P2-T17g, desktop checklist 2.10 (ACC-1): Tab from the tab control landed on the tab's
    scroll area, which NVDA calls "grouping", before the first setting. In every tab."""
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    schema = window.session.settings_schema()
    firsts = [dialog.controls[tab["fields"][0]["id"]] for tab in schema["tabs"]] + [dialog.key_list]
    assert len(firsts) == dialog.tabs.count()
    for index, first in enumerate(firsts):
        dialog.tabs.setCurrentIndex(index)
        dialog.tabs.tabBar().setFocus()
        QApplication.processEvents()
        qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab)
        focused = QApplication.focusWidget()
        assert focused is first or first.isAncestorOf(focused), \
            f"{dialog.tabs.tabText(index)}: {type(focused).__name__} {focused.accessibleName()!r}"
    dialog.reject()


def test_a_preset_chosen_in_settings_keeps_its_switches(window, qtbot):
    """OK sends only what was changed in the dialog, so the switches the preset has just set
    are not put back as they were (P2-T11, DP144)."""
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    dialog.controls["verbosity"].setCurrentIndex(dialog.controls["verbosity"].findData("terse"))
    dialog.ok_button.click()
    QApplication.processEvents()
    s = window.session.settings
    assert s["verbosity"] == "terse" and s["say_area"] == "smallest" and not s["say_zoom_step"]


def test_cancel_in_settings_changes_nothing(window, qtbot):
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    dialog.controls["units"].setCurrentIndex(dialog.controls["units"].findData("nautical"))
    dialog.cancel_button.click()
    QApplication.processEvents()
    assert window.session.settings["units"] == "metric"


def test_changing_a_key_in_the_keys_tab_warns_when_it_is_taken(window, qtbot):
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    row = [i for i, c in enumerate(dialog._commands) if c["name"] == "where.heading"][0]
    dialog.key_list.setCurrentRow(row)
    capture = KeyCaptureDialog(window, window.session, dialog._commands[row], window.words,
                               speak=window.announcer.speak)
    qtbot.addWidget(capture)
    capture.key = "C"
    capture.field.setText("C")
    capture.apply()
    assert "already used by Coordinates" in capture.message.text()
    assert "already used by Coordinates" in window.announcer.texts[-1]     # spoken too (checklist 2.6)
    assert window.session.settings.keys == {}
    qtbot.keyClick(capture.field, Qt.Key.Key_J)                               # a new key clears the message
    assert capture.message.text() == "" and capture.key == "J"
    capture.key = "C"
    capture.apply()
    capture.clear_button.click()                                              # so does No key
    assert capture.message.text() == ""
    capture.key = "Ctrl+Q"
    capture.apply()
    assert window.session.settings.keys == {"where.heading": "Ctrl+Q"}


def test_every_dialog_has_a_close_or_cancel_button(window, qtbot):
    for name in ("help.keys", "help.about", "help.about_data", "help.earcons", "speech.history", "settings.open"):
        window.dispatch(name)
        QApplication.processEvents()
        dialogs = [d for d in window.findChildren(TextDialog) + window.findChildren(ListDialog)
                   + window.findChildren(SettingsDialog) if d.isVisible()]
        assert dialogs, name
        d = dialogs[-1]
        button = getattr(d, "close_button", None) or getattr(d, "cancel_button")
        assert button.text() in ("Close", "Cancel"), name
        button.click()
        QApplication.processEvents()


def test_the_sounds_dialog_plays_the_chosen_sound(window, qtbot):
    """DP134: Enter or the Play button plays the selected sound."""
    window.dispatch("help.earcons")
    dialog = click_dialog(window, SoundsDialog)
    dialog.list.setCurrentRow(1)
    dialog.play_button.click()
    assert window.sounds.played[-1] == "blocked"
    dialog.list.setCurrentRow(0)
    qtbot.keyClick(dialog.list, Qt.Key.Key_Return)
    assert window.sounds.played[-1] == "tick"
    assert dialog.isVisible()                     # Enter plays; it does not close the dialog
    dialog.list.setCurrentRow(1)
    qtbot.keyClick(dialog.list, Qt.Key.Key_Space)  # so does Space (checklist 12, second pass)
    assert window.sounds.played[-1] == "blocked"
    assert dialog.isVisible()
    dialog.close_button.click()


def test_settings_buttons_tab_in_the_order_they_are_shown(window):
    """Checklist 11, second pass: OK came after Cancel in the Tab order."""
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    order = [dialog.ok_button]
    while len(order) < 4:
        order.append(order[-1].nextInFocusChain())
    assert order == [dialog.ok_button, dialog.cancel_button, dialog.export_button, dialog.import_button]
    xs = [b.geometry().x() for b in order]
    assert xs == sorted(xs)                       # left to right as well
    assert dialog.ok_button.isDefault()           # Enter is OK
    dialog.cancel_button.click()


def test_keys_dialog_lines_are_not_wrapped_and_symbols_are_words(window, qtbot):
    """Checklist 2, second pass: one line, one Down arrow; "Ctrl+Comma", not "Ctrl+,"."""
    qtbot.keyClick(window.map, Qt.Key.Key_F1)
    dialog = click_dialog(window, TextDialog)
    assert dialog.text.lineWrapMode() == dialog.text.LineWrapMode.NoWrap
    assert "Settings: Ctrl+Comma" in dialog.text.toPlainText()
    dialog.close_button.click()
    settings_action = window.actions_by_name["settings.open"]
    assert settings_action.text().endswith("\tCtrl+Comma")


def test_the_earcons_are_loaded_at_start(window):
    """Checklist 5, second pass: the first tick was quiet, so every earcon is loaded at start."""
    assert {"tick", "blocked"} <= set(window.sounds.preloaded)


def test_settings_and_place_come_back_after_closing_and_opening(qtbot, test_pack, tmp_path):
    first = make_window(qtbot, test_pack, tmp_path)
    first.dispatch("settings.set", field="units", value="imperial")
    first.dispatch("move.south")
    first.dispatch("zoom.in")
    where = (first.session.world.lat, first.session.world.lon, first.session.world.zoom_m)
    first.close()
    saved = json.loads((tmp_path / "settings.json").read_text())
    assert saved["settings"]["values"]["units"] == "imperial"
    session = MapSession(packs=[test_pack], settings=saved["settings"], saved_state=saved["state"])
    second = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(second)
    assert (second.session.world.lat, second.session.world.lon, second.session.world.zoom_m) == where
    assert second.session.settings["units"] == "imperial"


def test_the_window_builds_its_own_session_from_the_saved_file(qtbot, test_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("TOBYMAP_PACKS", str(test_pack))
    from desktop import storage

    storage.save({"settings": {"values": {"units": "imperial"}, "keys": {}}, "state": dict(KENT)}, tmp_path)
    w = MainWindow(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    assert w.session.settings["units"] == "imperial" and w.session.world.lat == 51.2


def test_a_missing_pack_is_explained(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("TOBYMAP_PACKS", str(tmp_path / "nothing-here"))
    w = MainWindow(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    assert w.map.accessibleName().startswith("No map pack is installed")


def test_mute_stops_the_earcons(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_M, Qt.KeyboardModifier.ControlModifier)
    window.session.world.step_index = 0
    qtbot.keyClick(window.map, Qt.Key.Key_Up)
    assert window.sounds.played == []
    assert window.actions_by_name["sound.mute"].isChecked()


def test_click_on_the_map_describes_the_place(window, qtbot):
    from PySide6.QtCore import QPoint

    qtbot.mouseClick(window.map, Qt.MouseButton.LeftButton, pos=window.map.rect().center() + QPoint(0, window.map.height() // 2 - 5))
    assert window.session.world.lat < 51.2                      # the location moved to the click
    assert window.announcer.texts[-1] == "North Atlantic Ocean" or window.sounds.played == ["tick"]


def test_the_wheel_changes_the_zoom(window, qtbot):
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent

    e = QWheelEvent(QPointF(100, 100), QPointF(100, 100), QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton,
                    Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(window.map, e)
    assert window.announcer.texts[-1].startswith("Zoom 10 kilometres")


def test_dragging_turns_the_globe_and_speaks_only_at_the_end(window, qtbot):
    count = len(window.announcer.spoken)
    qtbot.mousePress(window.map, Qt.MouseButton.LeftButton, pos=window.map.rect().center())
    centre = window.map.rect().center()
    from PySide6.QtCore import QPoint

    for dx in range(10, 90, 10):
        qtbot.mouseMove(window.map, pos=centre + QPoint(dx, 0))
    assert len(window.announcer.spoken) == count
    qtbot.mouseRelease(window.map, Qt.MouseButton.LeftButton, pos=centre + QPoint(80, 0))
    assert window.session.world.lon != 1.2


def test_the_map_is_drawn_in_its_own_thread_and_shown(window, qtbot):
    made = window.map.drawings_made
    window.map.redraw()
    qtbot.waitUntil(lambda: window.map.drawings_made > made)
    image = window.map.grab().toImage()
    centre = image.pixelColor(image.width() // 2 + 40, image.height() // 2 + 40).name()
    assert centre != window.session.scene_background()               # the map, not the empty background
    event = [e for e in window.session.trace if e["command"] == "draw"][-1]
    assert event["paint_ms"] >= 0 and event["points"] > 0


def test_scene_paints_quickly_on_an_image(window):
    scene = window.session.scene(1200, 900)
    image = QImage(1200, 900, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    start = time.perf_counter()
    paint_scene(painter, scene)
    painter.end()
    assert (time.perf_counter() - start) * 1000 < 300
    assert image.pixelColor(600, 450).name() != scene["background"]


def test_lines_and_markers_are_painted(window):
    """P2-T10a: the shell strokes each run of a line and draws each marker where the core put it."""
    import numpy as np

    scene = window.session.scene(400, 300)
    scene.update({"line_coords": np.array([50, 150, 350, 150], np.float32), "line_runs": np.array([0, 2], np.int32),
                  "line_style": np.array([0], np.int32), "line_area": ["a"],
                  "line_styles": [{"stroke": "#ff0000", "width": 3}],
                  "marker_coords": np.array([200, 60], np.float32), "marker_style": np.array([0], np.int32),
                  "marker_area": ["b"], "marker_styles": [{"fill": "#00ff00", "stroke": "#00ff00", "radius": 5}]})
    scene["cross"] = scene["heading"] = None
    scene["names"] = []   # a name could sit over the line
    image = QImage(400, 300, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    paint_scene(painter, scene)
    painter.end()
    assert image.pixelColor(120, 150).name() == "#ff0000"
    assert image.pixelColor(200, 60).name() == "#00ff00"


def test_timing_report_uses_the_last_paint(window, qtbot):
    window.map.redraw()
    qtbot.waitUntil(lambda: window.map.drawing_done() and window.session.paint_ms is not None)
    window.actions_by_name["diagnostics.timing"].trigger()
    assert "painted in" in window.announcer.texts[-1]


def test_copy_diagnostics_puts_the_text_on_the_clipboard(window):
    from PySide6.QtGui import QGuiApplication

    window.actions_by_name["diagnostics.copy"].trigger()
    assert "TobyMap" in QGuiApplication.clipboard().text() and "Location 51.20000" in QGuiApplication.clipboard().text()


def test_nothing_in_the_code_asks_for_the_location_of_the_computer():
    """SCP-1: no location service is used anywhere in the application."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    banned = ("QtPositioning", "QGeoPositionInfo", "geolocation", "navigator.geolocation", "getCurrentPosition")
    for folder in ("mapcore", "desktop", "web/js", "web/index.html", "web/worker.js"):
        path = root / folder
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.suffix in (".py", ".js", ".html")] if path.exists() else []
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            for word in banned:
                assert word not in text, (f, word)


# Orientation, turning, typed bearings and coordinates, and the place history (P2-T1c, P2-T2, P2-T15) --------------

def press(qtbot, widget, key, mods=Qt.KeyboardModifier.NoModifier):
    qtbot.keyClick(widget, key, mods)
    QApplication.processEvents()


def test_the_orientation_and_turning_keys(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_O)
    assert window.announcer.texts[-1] == "Cardinal facing, north."
    press(qtbot, window.map, Qt.Key.Key_Right)
    assert window.announcer.texts[-1] == "Facing east."
    assert window.session.world.heading == 90.0
    press(qtbot, window.map, Qt.Key.Key_O)
    press(qtbot, window.map, Qt.Key.Key_Left, Qt.KeyboardModifier.ControlModifier)
    assert window.announcer.texts[-1] == "Facing 89 degrees."
    press(qtbot, window.map, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    assert window.announcer.texts[-1] == "Facing 179 degrees."


def test_the_bearing_box_takes_a_bearing_and_refuses_what_it_cannot_read(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    assert box.windowTitle() == "Type a bearing" and box.ok_button.text() == "OK" and box.cancel_button.text() == "Cancel"
    box.field.setText("sideways")
    box.ok_button.click()
    assert box.isVisible() and box.error_box.text().startswith("sideways is not a valid bearing.")
    box.error_box.buttons()[0].click()
    QApplication.processEvents()
    box.field.setText("NE")
    box.ok_button.click()
    QApplication.processEvents()
    assert not box.isVisible() and window.map.accessibleName() == "Free facing, 45 degrees."   # said as focus returns
    assert window.session.world.heading == 45.0


def test_cancel_closes_the_go_to_box_and_moves_nothing(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_G, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    box.field.setText("10, 10")
    box.cancel_button.click()
    QApplication.processEvents()
    assert not box.isVisible() and window.session.world.lat == 51.2


def test_go_to_coordinates_then_back_through_the_places(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_G, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    box.field.setText("52.1 N 1.3 W")
    box.ok_button.click()
    QApplication.processEvents()
    assert window.session.world.lat == pytest.approx(52.1) and window.session.world.lon == pytest.approx(-1.3)
    window.activateWindow()   # offscreen: the window is not given back the keyboard when a box closes
    qtbot.waitUntil(lambda: QApplication.activeWindow() is window)
    press(qtbot, window.map, Qt.Key.Key_Comma, Qt.KeyboardModifier.AltModifier)
    assert window.session.world.lat == pytest.approx(51.2)


def test_enter_in_the_announcement_history_goes_back_there(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_PageUp)
    zoom = window.session.world.zoom_m
    window.session.run("goto.set", text="52.1, -1.3")
    press(qtbot, window.map, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    box = click_dialog(window, HistoryDialog)
    assert "Enter" in box.help.text()
    box.list.setCurrentRow(box.list.count() - 2)
    qtbot.keyClick(box.list, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert not box.isVisible()
    assert window.session.world.lat == pytest.approx(51.2) and window.session.world.zoom_m == zoom


def test_enter_on_an_entry_with_no_place_keeps_the_list_open(window, qtbot):
    window.session.run("sound.mute")
    press(qtbot, window.map, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    box = click_dialog(window, HistoryDialog)
    box.list.setCurrentRow(0)
    qtbot.keyClick(box.list, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert box.isVisible() and box.message.text() == "No place for this entry."
    assert window.announcer.texts[-1] == "No place for this entry."


# The layers dialog (P2-T3b; SCP-6, SCP-7, ACC-7) ----------------------------------------

def layer_item(dialog, layer_id):
    return dialog.items[layer_id]


def test_ctrl_shift_l_opens_the_layers_list_with_a_check_box_for_each_layer_in_its_group(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    dialog = click_dialog(window, LayersDialog)
    assert dialog.windowTitle() == "Layers"
    groups = [dialog.tree.topLevelItem(i) for i in range(dialog.tree.topLevelItemCount())]
    assert [g.text(0) for g in groups][:2] == ["Boundaries", "Water"]
    boundaries = [groups[0].child(i).text(0) for i in range(groups[0].childCount())]
    assert boundaries == ["Countries", "Regions", "Counties"]
    assert layer_item(dialog, "countries").checkState(0) == Qt.CheckState.Checked
    assert dialog.ok_button.text() == "OK" and dialog.cancel_button.text() == "Cancel"
    dialog.cancel_button.click()


def test_ok_in_the_layers_list_switches_the_layers_changed(window, qtbot):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    layer_item(dialog, "regions").setCheckState(0, Qt.CheckState.Unchecked)
    assert dialog.changes() == [("regions", {"on": False})]
    dialog.ok_button.click()
    QApplication.processEvents()
    assert not window.session.layers.is_on("regions")
    window.dispatch("where.am_i")
    assert window.announcer.texts[-1] == "Kent, United Kingdom"


def test_space_in_the_layers_list_ticks_and_enter_presses_ok(window, qtbot):
    # PO feedback on web checklist 2.6: Space switches a layer, Enter always presses OK.
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    dialog.tree.setCurrentItem(layer_item(dialog, "regions"))
    qtbot.keyClick(dialog.tree, Qt.Key.Key_Space)
    assert layer_item(dialog, "regions").checkState(0) == Qt.CheckState.Unchecked
    qtbot.keyClick(dialog.tree, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert layer_item(dialog, "regions").checkState(0) == Qt.CheckState.Unchecked
    assert not dialog.isVisible() and dialog.result() == 1
    assert not window.session.layers.is_on("regions")


def test_cancel_in_the_layers_list_changes_nothing(window, qtbot):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    layer_item(dialog, "regions").setCheckState(0, Qt.CheckState.Unchecked)
    dialog.cancel_button.click()
    QApplication.processEvents()
    assert window.session.layers.is_on("regions")


def test_settings_on_a_group_heading_says_to_choose_a_layer(window, qtbot):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(0))   # Boundaries, a group heading
    dialog.settings_button.click()
    assert window.announcer.texts[-1] == "Choose a layer first. The settings are for one layer."
    assert dialog.isVisible()
    dialog.cancel_button.click()


def test_a_layers_settings_change_its_zoom_range_and_a_wrong_range_is_refused_aloud(window, qtbot):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    layer = dialog.layers["counties"]
    box = LayerSettingsDialog(dialog, layer, dialog.dialog, dialog._check, speak=window.announcer.speak)
    qtbot.addWidget(box)
    assert box.max_zoom.currentText() == "100 kilometres"
    box.min_zoom.setCurrentIndex(box.min_zoom.findData(250000))
    box.ok_button.click()      # the minimum zoom is larger than the maximum
    assert "must not be larger" in box.message.text() and window.announcer.texts[-1] == box.message.text()
    assert box.result() == 0
    box.max_zoom.setCurrentIndex(box.max_zoom.findData(None))
    box.crossing.setCurrentIndex(box.crossing.findData("line_crossing"))
    box.ok_button.click()
    assert box.values() == {"min_zoom_m": 250000, "max_zoom_m": None, "crossing_earcon": "line_crossing"}
    dialog.layers["counties"].update(box.values())
    assert dialog.changes() == [("counties", {"min_zoom_m": 250000, "max_zoom_m": None,
                                               "crossing_earcon": "line_crossing"})]
    dialog.ok_button.click()
    QApplication.processEvents()
    counties = window.session.layers.get("counties")
    assert (counties.min_zoom_m, counties.max_zoom_m, counties.crossing_earcon) == (250000, None, "line_crossing")


def test_crossed_and_passed_is_filled_in_the_background_and_shift_3_goes_there(qtbot, test_pack, tmp_path):
    """P2-T5, ANN-2: after the step is spoken, the search runs on a thread of its own; the group is
    filled and the earcon plays, with nothing more spoken. Shift+3 goes to the group, the third (DP109)."""
    import json as _json
    from pathlib import Path as _Path

    from mapcore.geo import geodesy

    data = _json.loads((_Path(__file__).resolve().parents[1] / "samples" / "osm" / "southampton-itchen.geojson")
                       .read_text(encoding="utf-8"))
    river = next(f for f in data["features"] if f["properties"]["name"] == "River Itchen")
    line = max(river["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    west = lon - 300 / (geodesy.parallel_radius_m(lat) * 3.141592653589793 / 180)
    w = make_window(qtbot, test_pack, tmp_path, state={"lat": lat, "lon": west, "zoom_m": 5000, "step_m": 1000})
    spoken = len(w.announcer.texts)
    qtbot.keyClick(w.map, Qt.Key.Key_Right)
    group = w._group_item("crossed")
    qtbot.waitUntil(lambda: group.childCount() and group.child(0).text(0).startswith("River Itchen, crossed"),
                    timeout=5000)
    qtbot.waitUntil(lambda: "crossed_added" in w.sounds.played, timeout=2000)
    assert len(w.announcer.texts) == spoken    # still Southampton: only the tick; the river is never spoken
    qtbot.keyClick(w.map, Qt.Key.Key_3, Qt.KeyboardModifier.ShiftModifier)
    assert region(w) == "panel"
    assert w.tree.currentItem().text(0).startswith("River Itchen, crossed")


# Enter on a button presses that button (P2-T17b; desktop checklist 3.5, 5.3, 8.2, 8.6; ACC-7) -------------

def enter(qtbot, widget):
    qtbot.keyClick(widget, Qt.Key.Key_Return)
    QApplication.processEvents()


@pytest.mark.parametrize("key", [Qt.Key.Key_B, Qt.Key.Key_G], ids=["bearing", "go to"])
def test_enter_on_cancel_cancels_the_bearing_and_go_to_boxes(window, qtbot, key):
    press(qtbot, window.map, key, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    box.field.setText("hello")
    enter(qtbot, box.cancel_button)
    assert not box.isVisible() and box.result() == 0 and box.response is None
    assert box.error_box is None           # OK was not pressed: nothing was read
    assert window.session.world.lat == 51.2


def test_enter_on_ok_and_in_the_field_still_presses_ok(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    box.field.setText("hello")
    enter(qtbot, box.ok_button)
    assert box.isVisible() and box.error_box.text().startswith("hello is not a valid bearing.")
    enter(qtbot, box.error_box.buttons()[0])
    box.field.setText("NE")
    enter(qtbot, box.field)
    assert not box.isVisible() and window.session.world.heading == 45.0


@pytest.mark.parametrize("key, title, words", [
    (Qt.Key.Key_B, "Type a bearing", "hello is not a valid bearing. Enter a value in degrees in the range 0 to 360."),
    (Qt.Key.Key_G, "Go to coordinates", "hello is not a valid entry. Enter latitude and then longitude"),
], ids=["bearing", "go to"])
def test_a_wrong_entry_opens_a_message_box_and_ok_comes_back_to_the_text(window, qtbot, key, title, words):
    # P2-T17o, the PO's notes on desktop checklist 3.5 and 5.3: a message box with an OK button, not
    # words changed in the box; after OK you are back in the box with your text.
    press(qtbot, window.map, key, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    if key == Qt.Key.Key_B:
        assert box.field.accessibleName() == "Enter a bearing in degrees, or a compass direction:"
        assert box.field.accessibleDescription() == "" and box.help.parent() is None   # no help line
    before = len(window.announcer.texts)
    box.field.setText("hello")
    enter(qtbot, box.field)
    message = box.error_box
    assert message is not None and message.isVisible() and message.isModal()
    assert message.windowTitle() == title and message.text().startswith(words)
    assert [b.text() for b in message.buttons()] == ["OK"]
    assert window.announcer.texts[before:] == []   # the screen reader reads the message box itself
    enter(qtbot, message.buttons()[0])
    assert not message.isVisible() and box.error_box is None and box.isVisible()
    assert box.field.text() == "hello" and box.field.selectedText() == "hello"
    assert box.focusWidget() is box.field   # offscreen, no window is given the keyboard back


def test_enter_on_cancel_in_the_layers_list_changes_nothing(window, qtbot):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    layer_item(dialog, "regions").setCheckState(0, Qt.CheckState.Unchecked)
    enter(qtbot, dialog.cancel_button)
    assert not dialog.isVisible() and dialog.result() == 0
    assert window.session.layers.is_on("regions")


def test_enter_on_settings_for_this_layer_opens_it(window, qtbot, monkeypatch):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    opened = []
    monkeypatch.setattr(LayerSettingsDialog, "exec", lambda self: opened.append(self.windowTitle()))
    dialog.tree.setCurrentItem(layer_item(dialog, "counties"))
    enter(qtbot, dialog.settings_button)
    assert len(opened) == 1 and dialog.isVisible()
    enter(qtbot, dialog.tree)               # elsewhere in the list, Enter is still OK, not Settings
    assert len(opened) == 1 and not dialog.isVisible() and dialog.result() == 1


def test_enter_on_cancel_in_a_layers_settings_goes_back_unchanged(window, qtbot):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    box = LayerSettingsDialog(dialog, dialog.layers["counties"], dialog.dialog, dialog._check)
    qtbot.addWidget(box)
    box.show()
    box.min_zoom.setCurrentIndex(box.min_zoom.findData(250000))
    enter(qtbot, box.cancel_button)
    assert not box.isVisible() and box.result() == 0
    box = LayerSettingsDialog(dialog, dialog.layers["counties"], dialog.dialog, dialog._check)
    qtbot.addWidget(box)
    box.show()
    enter(qtbot, box.min_zoom)               # Enter in a field presses OK
    assert not box.isVisible() and box.result() == 1


def test_enter_on_each_button_in_settings_presses_that_button(window, qtbot):
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    dialog.controls["units"].setCurrentIndex(dialog.controls["units"].findData("imperial"))
    enter(qtbot, dialog.cancel_button)
    assert not dialog.isVisible() and window.session.settings["units"] == "metric"
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    dialog.controls["units"].setCurrentIndex(dialog.controls["units"].findData("imperial"))
    enter(qtbot, dialog.controls["units"])  # Enter in a field presses OK
    assert not dialog.isVisible() and window.session.settings["units"] == "imperial"


def test_enter_on_no_key_and_cancel_in_the_key_box(window, qtbot):
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    capture = KeyCaptureDialog(dialog, window.session, dialog._commands[0], window.words)
    qtbot.addWidget(capture)
    capture.show()
    enter(qtbot, capture.clear_button)
    assert capture.isVisible() and capture.key == ""
    enter(qtbot, capture.cancel_button)
    assert not capture.isVisible() and capture.result() == 0
    assert window.session.settings.keys == {}
    dialog.cancel_button.click()


def test_every_button_in_a_row_takes_enter_and_only_ok_is_the_default(window, qtbot):
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    rows = [dialog.settings_button, dialog.ok_button, dialog.cancel_button]
    assert all(b.autoDefault() for b in rows)
    assert [b.isDefault() for b in rows] == [False, True, False]
    dialog.cancel_button.click()


# The place said once as a dialog closes (P2-T17c; desktop checklist 5.2, 5.4, 7.4; web 8.2) -------------
# NVDA reads the map's name as the focus comes back from a dialog. So what the dialog's answer says
# becomes that name, and is not spoken as well; with nothing to say, the name is the place after the
# dialog's changes, never the place before them.

def said_once(window, before, text):
    spoken = window.announcer.texts[before:]
    assert text not in spoken, spoken
    assert window.map.accessibleName() == text


def test_go_to_says_the_new_place_once(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_G, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    before = len(window.announcer.texts)
    box.field.setText("52.1 N 1.3 W")
    enter(qtbot, box.field)
    assert not box.isVisible()
    place = window.session.map_label()
    assert place != "Kent, England, United Kingdom"
    said_once(window, before, place)
    assert window.announcer.texts[before:] == []
    assert place in window.session.run("speech.history").dialog["lines"]   # still in the announcement history


def test_enter_in_the_announcement_history_says_the_place_once(window, qtbot):
    window.dispatch("goto.set", text="52.1, -1.3")
    press(qtbot, window.map, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    box = click_dialog(window, HistoryDialog)
    before = len(window.announcer.texts)
    box.list.setCurrentRow(box.list.count() - 1)          # the oldest: the start, in Kent
    enter(qtbot, box.list)
    assert not box.isVisible() and window.session.world.lat == pytest.approx(51.2)
    said_once(window, before, "Kent, England, United Kingdom")


def test_closing_the_layers_list_names_the_map_after_the_changes(window, qtbot):
    # Web checklist 8.6: with every layer here switched off, the old place was said as the list closed.
    window.dispatch("layers.open")
    dialog = click_dialog(window, LayersDialog)
    for layer in ("countries", "regions", "counties"):
        layer_item(dialog, layer).setCheckState(0, Qt.CheckState.Unchecked)
    before = len(window.announcer.texts)
    dialog.ok_button.click()
    QApplication.processEvents()
    after = window.session.map_label()
    assert "United Kingdom" not in after
    said_once(window, before, after)


def test_cancel_names_the_map_after_the_place_unchanged(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_G, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    before = len(window.announcer.texts)
    enter(qtbot, box.cancel_button)
    said_once(window, before, "Kent, England, United Kingdom")
    assert window.announcer.texts[before:] == []


def test_after_a_bearing_leaving_the_map_names_it_after_the_place_again(window, qtbot):
    press(qtbot, window.map, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    box.field.setText("90")
    enter(qtbot, box.field)
    assert window.map.accessibleName() == "Free facing, 90 degrees."
    window.activateWindow()   # offscreen: the window is not given back the keyboard when a box closes
    qtbot.waitUntil(lambda: QApplication.activeWindow() is window)
    window.map.setFocus()
    window.tree.setFocus()
    QApplication.processEvents()
    assert window.map.accessibleName() == "Kent, England, United Kingdom"
    window.map.setFocus()
    press(qtbot, window.map, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)   # a later answer, named afresh
    box = click_dialog(window, InputDialog)
    box.field.setText("180")
    enter(qtbot, box.field)
    assert window.map.accessibleName() == "Facing 180 degrees."


# The Information panel (P2-T17k; INF-10, DP155, desktop checklist 10.4, 10.5, 11.5, 11.7) -------

def back_to_window(window, qtbot):
    window.activateWindow()   # offscreen: the window is not given back the keyboard when a box closes
    qtbot.waitUntil(lambda: QApplication.activeWindow() is window)


def test_each_group_heading_has_its_count_and_within_its_distances(window):
    within = window.tree.topLevelItem(0)
    assert within.text(0) == "Within, 3 items"
    assert window.tree.topLevelItem(1).text(0) == "Nearby, 1 item"
    assert within.child(0).text(0) == "Kent, centre 35 kilometres west"


def test_enter_on_a_within_item_goes_to_its_centre_and_stays_in_the_panel(window, qtbot):
    window.focus_region("panel")
    window.tree.setCurrentItem(window.tree.topLevelItem(0).child(1))   # England
    before = len(window.announcer.texts)
    press(qtbot, window.tree, Qt.Key.Key_Return)
    assert window.session.world.lon < 0   # England's centre is west of Greenwich in the test pack
    assert window.announcer.texts[before:] == [window.session._place_text()]
    assert region(window) == "panel"
    assert window.tree.currentItem() is window.tree.topLevelItem(0).child(0)


def test_enter_on_a_group_heading_says_it_works_on_an_item(window, qtbot):
    window.focus_region("panel")
    window.tree.setCurrentItem(window.tree.topLevelItem(1))
    press(qtbot, window.tree, Qt.Key.Key_Return)
    assert window.announcer.texts[-1] == "Go there works on an item, not on a group."
    assert window.session.world.lat == 51.2


@pytest.mark.parametrize("key", [Qt.Key.Key_G, Qt.Key.Key_B], ids=["go to", "bearing"])
def test_ctrl_g_and_ctrl_b_work_from_the_panel_and_come_back_there(window, qtbot, key):
    window.focus_region("panel")
    within = window.tree.topLevelItem(0)
    window.tree.setCurrentItem(within.child(2))
    press(qtbot, window.tree, key, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    before = len(window.announcer.texts)
    box.field.setText("51.3, 0.5" if key == Qt.Key.Key_G else "90")
    enter(qtbot, box.field)
    assert not box.isVisible()
    back_to_window(window, qtbot)
    assert region(window) == "panel"
    # After a jump, the first item of the same group; after a bearing, the same item.
    assert window.tree.currentItem() is within.child(0 if key == Qt.Key.Key_G else 2)
    said = window.announcer.texts[before:]
    assert said == ([window.session._place_text()] if key == Qt.Key.Key_G else ["Free facing, 90 degrees."])


def test_ctrl_g_works_from_details_and_comes_back_there(window, qtbot):
    window.focus_region("details")
    press(qtbot, window.details, Qt.Key.Key_G, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    box.field.setText("51.3, 0.5")
    enter(qtbot, box.field)
    back_to_window(window, qtbot)
    assert region(window) == "details" and window.session.world.lat == pytest.approx(51.3)


def test_cancel_from_the_panel_comes_back_to_the_same_item(window, qtbot):
    window.focus_region("panel")
    item = window.tree.topLevelItem(0).child(1)
    window.tree.setCurrentItem(item)
    press(qtbot, window.tree, Qt.Key.Key_G, Qt.KeyboardModifier.ControlModifier)
    box = click_dialog(window, InputDialog)
    before = len(window.announcer.texts)
    enter(qtbot, box.cancel_button)
    back_to_window(window, qtbot)
    assert region(window) == "panel" and window.tree.currentItem() is item
    assert window.announcer.texts[before:] == []


def test_shift_o_and_shift_a_go_the_other_way(window, qtbot):
    """P2-T17l, the PO's note on desktop checklist 4.4: Shift goes back round a list."""
    press(qtbot, window.map, Qt.Key.Key_O, Qt.KeyboardModifier.ShiftModifier)
    assert window.announcer.texts[-1].startswith("Free facing, ")
    press(qtbot, window.map, Qt.Key.Key_O, Qt.KeyboardModifier.ShiftModifier)
    assert window.announcer.texts[-1].startswith("Cardinal facing, ")
    press(qtbot, window.map, Qt.Key.Key_A, Qt.KeyboardModifier.ShiftModifier)
    assert window.announcer.texts[-1].startswith("Terse.")


def test_home_and_end_in_every_number_box_set_the_largest_and_smallest(window, qtbot):
    """P2-T17m, desktop checklist 12.4: Home sets the largest value, as it is above End on the
    keyboard, and End the smallest. Every number box in Settings, so none is missed."""
    window.dispatch("settings.open")
    dialog = click_dialog(window, SettingsDialog)
    numbers = [f for tab in window.session.settings_schema()["tabs"] for f in tab["fields"] if f["kind"] == "number"]
    assert len(numbers) > 5
    for f in numbers:
        box = dialog.controls[f["id"]]
        dialog.tabs.setCurrentWidget(next(dialog.tabs.widget(i) for i in range(dialog.tabs.count())
                                          if dialog.tabs.widget(i).isAncestorOf(box)))
        box.setFocus()
        qtbot.keyClick(box, Qt.Key.Key_Home)
        assert box.value() == f["max"], f["id"]
        qtbot.keyClick(box, Qt.Key.Key_End)
        assert box.value() == f["min"], f["id"]
    dialog.cancel_button.click()
