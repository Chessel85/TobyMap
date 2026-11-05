"""The desktop window, offscreen, with a recording announcer and recording sounds (UX section 2, ACC-1, ACC-7, ANN-3)."""
import json
import time

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QImage, QKeyEvent, QPainter
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import KeyCaptureDialog, ListDialog, SettingsDialog, SoundsDialog, TextDialog
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


def test_start_is_announced_and_map_has_focus(window):
    assert window.announcer.texts == ["TobyMap. Kent, England, United Kingdom. Press F1 for keys."]
    assert region(window) == "map"
    assert window.map.accessibleName() == "Kent, England, United Kingdom"
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
    assert window.tree.currentItem().text(0) == "Kent"
    assert window.details.toPlainText().splitlines()[0] == "Kent"
    window.tree.setCurrentItem(window.tree.topLevelItem(1).child(0))
    qtbot.keyClick(window.tree, Qt.Key.Key_F2)
    qtbot.keyClick(window.map, Qt.Key.Key_F3)
    assert window.tree.currentItem().parent().text(0) == "Nearby"


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
    assert "Step north\tUp" in texts and "Exit" in texts and "Link step to zoom" in texts
    assert window.actions_by_name["step.link"].isCheckable()


def test_menu_command_runs_through_the_core(window):
    window.actions_by_name["where.coordinates"].trigger()
    assert window.announcer.texts[-1] == "51.20000 degrees north, 1.20000 degrees east"


def test_the_link_menu_item_shows_its_state(window):
    window.actions_by_name["step.link"].trigger()
    assert window.session.world.link and window.actions_by_name["step.link"].isChecked()
    assert window.announcer.texts[-1].startswith("Step linked to zoom.")


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
    assert dialog.windowTitle() == "Keys" and "Step north: Up" in dialog.text.toPlainText()
    assert dialog.close_button.text() == "Close"
    dialog.close_button.click()
    QApplication.processEvents()
    assert not dialog.isVisible() and region(window) == "map"
    window.activateWindow()
    QApplication.processEvents()
    window.focus_region("panel")
    qtbot.keyClick(window.tree, Qt.Key.Key_F1)
    assert "Step north" not in click_dialog(window, TextDialog).text.toPlainText()


def test_history_dialog_lists_the_announcements_with_a_close_button(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Space)
    qtbot.keyClick(window.map, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    dialog = click_dialog(window, ListDialog)
    assert dialog.list.item(0).text() == "Kent, England, United Kingdom"
    assert dialog.close_button.text() == "Close"


def test_the_key_describer_describes_and_does_nothing(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_F1, Qt.KeyboardModifier.ShiftModifier)
    qtbot.keyClick(window.map, Qt.Key.Key_Down)
    assert window.announcer.texts[-1] == "Down: Step south"
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
    assert window.announcer.texts[-1] == "Down: Step south"
    assert window.tree.currentItem() is item
    qtbot.keyClick(window.tree, Qt.Key.Key_F1, Qt.KeyboardModifier.ShiftModifier)
    qtbot.keyClick(window.tree, Qt.Key.Key_Tab)
    assert region(window) == "details"


def test_holding_an_arrow_key_speaks_only_the_final_place_after_release(window):
    """ANN-3: two seconds of key repeat, then let go."""
    announcer = window.announcer
    w = window.map
    clock = [100.0]
    window.session.clock = lambda: clock[0]
    QApplication.sendEvent(w, key_event(QEvent.Type.KeyPress, Qt.Key.Key_Down))          # the first press speaks
    spoken_after_first = len(announcer.spoken)
    start = time.perf_counter()
    for _ in range(60):                                                                    # 2 seconds of repeats
        clock[0] += 1 / 30
        QApplication.sendEvent(w, key_event(QEvent.Type.KeyPress, Qt.Key.Key_Down, auto=True))
        QApplication.sendEvent(w, key_event(QEvent.Type.KeyRelease, Qt.Key.Key_Down, auto=True))
    assert len(announcer.spoken) == spoken_after_first, "nothing is spoken while the key is held"
    steps = round((51.2 - window.session.world.lat) / (25 / 111.2))
    assert 9 <= steps <= 11, steps          # the press, then 6 a second after the 500 ms delay (DP129)
    assert window.sounds.played.count("tick") >= steps - 1   # each repeated step ticks
    QApplication.sendEvent(w, key_event(QEvent.Type.KeyRelease, Qt.Key.Key_Down))
    assert len(announcer.spoken) == spoken_after_first + 1
    assert announcer.spoken[-1][1] == "assertive"       # it interrupts what the screen reader was still saying
    assert announcer.texts[-1] == "France"             # about 250 km south of Kent
    assert time.perf_counter() - start < 5


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
        ["Units", "Movement", "Sound", "Display", "Keys"]
    dialog.controls["units"].setCurrentIndex(dialog.controls["units"].findData("imperial"))
    dialog.ok_button.click()
    QApplication.processEvents()
    assert window.session.settings["units"] == "imperial"


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
    dialog.close_button.click()


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
    assert w.announcer.texts[0].startswith("No map pack is installed")


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


def test_scene_paints_quickly_on_an_image(window):
    scene = window.session.scene(1200, 900)
    image = QImage(1200, 900, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    start = time.perf_counter()
    paint_scene(painter, scene)
    painter.end()
    assert (time.perf_counter() - start) * 1000 < 300
    assert image.pixelColor(600, 450).name() != scene["background"]


def test_timing_report_uses_the_last_paint(window):
    window.map.repaint()
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
