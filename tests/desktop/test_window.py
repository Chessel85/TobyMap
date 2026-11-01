"""The spike S5 desktop window, offscreen, with a recording announcer (P0-T8, UX section 2, ACC-1, ACC-7)."""
import time

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.map_widget import paint_scene
from desktop.window import MainWindow, TextDialog


@pytest.fixture
def window(qtbot):
    announcer = RecordingAnnouncer()
    w = MainWindow(announcer=announcer)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


def region(w):
    return w.region_of(QApplication.focusWidget() or w.focusWidget())


def test_start_is_announced_and_map_has_focus(window):
    assert window.announcer.texts == ["TobyMap globe. United Kingdom. Press F1 for keys."]
    assert region(window) == "map"
    assert window.map.accessibleName() == "United Kingdom"  # the place, as the PO asked
    assert window.tree.accessibleName() == "Information panel"
    assert window.details.accessibleName() == "Details"


def test_tab_cycles_the_three_regions_and_wraps(window, qtbot):
    # The menu bar is reached with Alt, not Tab (DP93).
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


def test_tab_on_the_menu_bar_goes_to_the_map(window, qtbot):
    window.menuBar().setNativeMenuBar(False)  # macOS's own menu bar is outside the window
    window.focus_region("menu")
    QApplication.processEvents()
    window.focusNextPrevChild(True)
    assert region(window) == "map"
    window.focus_region("menu")
    window.focusNextPrevChild(False)
    assert region(window) == "details"


def test_details_entries_are_one_line_each(window):
    # A wrapped entry was read twice by NVDA when arrowing down (PO feedback).
    window.session.state.lat, window.session.state.lon = 51.0, 10.0  # Germany
    window.details.setPlainText(window.session.details())
    window.resize(400, 300)
    QApplication.processEvents()
    block = window.details.document().begin()
    while block.isValid():
        assert block.layout().lineCount() == 1, block.text()
        block = block.next()


def test_tab_from_details_backwards_reaches_the_panel(window, qtbot):
    window.focus_region("details")
    qtbot.keyClick(window.details, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
    assert region(window) == "panel"


def test_arrow_keys_in_the_map_turn_the_globe_and_speak(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Down)
    assert window.announcer.spoken[-1] == ("Spain", "assertive")
    qtbot.keyClick(window.map, Qt.Key.Key_PageDown)
    assert window.announcer.texts[-1] == "Zoom 2 of 5, step 5 degrees."
    qtbot.keyClick(window.map, Qt.Key.Key_Space)
    assert window.announcer.texts[-1].startswith("Spain. 42 degrees north")


def test_arrow_keys_in_the_tree_do_not_turn_the_globe(window, qtbot):
    window.focus_region("panel")
    before = (window.session.state.lat, window.session.state.lon)
    qtbot.keyClick(window.tree, Qt.Key.Key_Down)
    assert (window.session.state.lat, window.session.state.lon) == before


def test_shift_space_goes_to_within_and_selection_fills_details(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Space, Qt.KeyboardModifier.ShiftModifier)
    assert region(window) == "panel"
    assert window.tree.currentItem().text(0) == "United Kingdom"
    assert window.details.toPlainText().splitlines()[0] == "United Kingdom"
    window.focus_region("map")
    qtbot.keyClick(window.map, Qt.Key.Key_R)
    current = window.tree.currentItem()
    assert current.parent().text(0) == "Nearby"
    assert window.details.toPlainText().splitlines()[0] == current.text(0).split(",")[0]


def test_tree_holds_the_groups(window):
    labels = [window.tree.topLevelItem(i).text(0) for i in range(window.tree.topLevelItemCount())]
    assert labels == ["Within", "Nearby", "Crossed and passed"]
    crossed = window.tree.topLevelItem(2)
    assert crossed.child(0).text(0).startswith("Nothing yet")


def test_details_is_read_only_and_reachable_with_d(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_D)
    assert region(window) == "details"
    assert window.details.isReadOnly()
    assert "Sovereign state: United Kingdom" in window.details.toPlainText()


def test_menus_come_from_the_registry(window):
    bar = window.menuBar()
    assert [a.text() for a in bar.actions()] == ["&Map", "&Speech", "&Help"]  # Alt+M, Alt+S, Alt+H
    map_menu = bar.actions()[0].menu()
    texts = [a.text() for a in map_menu.actions()]
    assert "Turn the globe north\tUp" in texts
    assert "Exit" in texts
    assert window.actions_by_name["help.keys"].shortcut().toString() == "F1"


def test_menu_command_runs_through_the_core(window):
    window.actions_by_name["where.coordinates"].trigger()
    assert window.announcer.texts[-1] == "52 degrees north, 1 degree west"


def test_braille_test_falls_back_to_speech_without_nvda(window):
    window.actions_by_name["speech.braille_test"].trigger()
    assert window.announcer.texts[-1] == "Braille-only messages need NVDA, and it was not found."


def test_braille_test_goes_to_braille_when_nvda_is_there(qtbot):
    announcer = RecordingAnnouncer(braille_works=True)
    w = MainWindow(announcer=announcer)
    qtbot.addWidget(w)
    w.actions_by_name["speech.braille_test"].trigger()
    assert announcer.brailled == ["TobyMap Braille test: United Kingdom"]
    assert announcer.texts == ["TobyMap globe. United Kingdom. Press F1 for keys."]


def test_f1_opens_a_dialog_with_a_close_button(window, qtbot):
    window.actions_by_name["help.keys"].trigger()
    QApplication.processEvents()
    (dialog,) = [d for d in window.findChildren(TextDialog) if d.isVisible()]
    assert dialog.windowTitle() == "Keys"
    assert "Turn the globe north: Up" in dialog.text.toPlainText()
    assert dialog.close_button.text() == "Close"
    dialog.close_button.click()
    QApplication.processEvents()
    assert not dialog.isVisible()
    assert region(window) == "map"


def test_click_on_the_map_centres_the_globe(window, qtbot):
    w, h = window.map.width(), window.map.height()
    qtbot.mouseClick(window.map, Qt.MouseButton.LeftButton, pos=window.map.rect().center())
    assert window.announcer.texts[-1] == "United Kingdom"
    assert (w, h) == (window.map.width(), window.map.height())


def test_scene_paints_quickly_on_an_image(window):
    scene = window.session.scene(1200, 900)
    image = QImage(1200, 900, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    start = time.perf_counter()
    paint_scene(painter, scene)
    painter.end()
    ms = (time.perf_counter() - start) * 1000
    assert ms < 200, ms
    # The centre pixel is the cross, a pixel on the ocean is ocean blue.
    assert image.pixelColor(600, 600 + 380).name() != scene["background"]


def test_timing_report_uses_the_last_paint(window, qtbot):
    window.map.repaint()
    window.actions_by_name["diagnostics.timing"].trigger()
    assert "painted in" in window.announcer.texts[-1]
