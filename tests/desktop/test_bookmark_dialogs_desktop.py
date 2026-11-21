"""The bookmark manager and the bookmark list dialog on the desktop (P4-T8e; USR-3, ACC-7, DP219 point 7):
Tab order, unavailable buttons that stay in it, each change kept and said at once, deleting asks, and Close."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop import dialogs, storage
from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import HistoryDialog, BookmarkListDialog, BookmarkManagerDialog, BookmarkZoomDialog, ConfirmBox, InputDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    b = session.bookmarks
    b.lists[0].name = "Castles"
    b.add(0, "Winchester", 51.06, -1.31)
    b.add(0, "Alpha", 51.06, -1.11)
    b.add(0, "Corfe", 50.6, -2.05)
    b.new_list("Holidays")
    b.add(1, "Rome", 41.9, 12.5)
    b.use(0)
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


def shown(window, cls):
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(cls) if d.isVisible()]
    return box


def manager(window):
    window.dispatch("bookmark.manager_open")
    return shown(window, BookmarkManagerDialog)


def lines(dialog):
    return [dialog.list.item(i).text() for i in range(dialog.list.count())]


def has_focus(widget) -> bool:
    """The widget has the focus, or will have it as its dialog is active (offscreen, a dialog may not be)."""
    return widget.hasFocus() or widget.window().focusWidget() is widget


def tab_order(dialog, widgets):
    """The widgets in the order Tab reaches them, from the first."""
    wanted, order, w = set(widgets), [], widgets[0]
    for _ in range(200):
        if w in wanted and w not in order:
            order.append(w)
        w = w.nextInFocusChain()
    return order


# The bookmark manager ---------------------------------------------------------------------------------

def test_the_manager_opens_on_the_lists_with_its_buttons_in_tab_order_and_a_close_button(window):
    dialog = manager(window)
    assert lines(dialog) == ["Castles, 3 bookmarks", "Holidays, 1 bookmark"]
    assert dialog.list.currentRow() == 0 and has_focus(dialog.list)
    assert dialog.list.accessibleName() == "Bookmark lists"
    buttons = [dialog.open_button, dialog.new_button, dialog.rename_button, dialog.up_button, dialog.down_button,
               dialog.delete_button, dialog.zoom_button, dialog.save_button, dialog.open_file_button, dialog.close_button]
    assert [b.text() for b in buttons] == ["Open list", "New list", "Rename", "Move up", "Move down", "Delete list",
                                          "Zoom range", "Save to a file", "Open a file", "Close"]
    assert tab_order(dialog, [dialog.list, *buttons]) == [dialog.list, *buttons]
    dialog.close_button.click()
    QApplication.processEvents()
    assert not dialog.isVisible()


def test_the_lists_are_check_boxes_and_space_writes_the_change_at_once(window, qtbot, tmp_path):
    dialog = manager(window)
    assert dialog.list.item(1).checkState() == Qt.CheckState.Checked
    dialog.list.item(1).setCheckState(Qt.CheckState.Unchecked)
    assert not window.session.bookmarks.lists[1].on
    assert '"on": false' in storage.load_bookmarks(tmp_path)
    assert window.announcer.texts == []   # the screen reader says the check box's state itself
    dialog.close_button.click()


def test_move_up_is_unavailable_on_the_first_and_pressing_it_does_nothing(window):
    dialog = manager(window)
    assert not dialog.up_button.available and dialog.down_button.available
    said = list(window.announcer.texts)
    dialog.up_button.click()
    assert [l.name for l in window.session.bookmarks.lists] == ["Castles", "Holidays"] and window.announcer.texts == said
    dialog.list.setCurrentRow(1)
    assert dialog.up_button.available and not dialog.down_button.available
    dialog.close_button.click()


def test_move_down_keeps_the_focus_on_the_moved_list_and_says_nothing(window, tmp_path):
    dialog = manager(window)
    dialog.down_button.click()
    assert lines(dialog) == ["Holidays, 1 bookmark", "Castles, 3 bookmarks"] and dialog.list.currentRow() == 1
    assert has_focus(dialog.list) and window.announcer.texts == []
    import json

    assert [l["name"] for l in json.loads(storage.load_bookmarks(tmp_path))["tobymap"]["lists"]] == ["Holidays", "Castles"]
    dialog.close_button.click()


def test_new_list_asks_for_a_name_and_the_focus_goes_to_the_new_line(window, tmp_path):
    dialog = manager(window)
    dialog.new_button.click()
    box = shown(window, InputDialog)
    box.field.setText("Forts")
    box.ok_button.click()
    QApplication.processEvents()
    assert lines(dialog)[-1] == "Forts, no bookmarks" and dialog.list.currentRow() == 2 and has_focus(dialog.list)
    assert '"name": "Forts"' in storage.load_bookmarks(tmp_path)
    dialog.close_button.click()


def test_a_name_in_use_is_refused_in_the_name_box_with_its_words(window):
    dialog = manager(window)
    dialog.new_button.click()
    box = shown(window, InputDialog)
    box.field.setText("castles")
    box.ok_button.click()
    QApplication.processEvents()
    assert box.error_box is not None and "already a bookmark list called castles" in box.error_box.text()
    box.error_box.accept()
    box.cancel_button.click()
    dialog.close_button.click()


def test_rename_says_what_changed(window):
    dialog = manager(window)
    dialog.list.setCurrentRow(1)
    dialog.rename_button.click()
    box = shown(window, InputDialog)
    assert box.windowTitle() == "Rename the bookmark list Holidays" and box.field.text() == "Holidays"
    box.field.setText("Trips")
    box.ok_button.click()
    QApplication.processEvents()
    assert lines(dialog)[1] == "Trips, 1 bookmark" and "Renamed Holidays to Trips." in window.announcer.texts
    dialog.close_button.click()


def test_delete_list_asks_cancel_keeps_it_and_delete_says_so(window, tmp_path):
    dialog = manager(window)
    dialog.delete_button.click()
    box = shown(window, ConfirmBox)
    assert box.text() == "Delete the list Castles and its 3 bookmarks?" and box.defaultButton() is box.cancel_button
    box.cancel_button.click()
    QApplication.processEvents()
    assert len(lines(dialog)) == 2 and "Deleted Castles." not in window.announcer.texts and has_focus(dialog.list)
    dialog.delete_button.click()
    shown(window, ConfirmBox).ok_button.click()
    QApplication.processEvents()
    assert lines(dialog) == ["Holidays, 1 bookmark"] and "Deleted Castles." in window.announcer.texts
    assert "Castles" not in storage.load_bookmarks(tmp_path)
    dialog.close_button.click()


def test_zoom_range_uses_the_layers_choices_and_refuses_a_minimum_over_the_maximum(window):
    dialog = manager(window)
    dialog.zoom_button.click()
    box = shown(window, BookmarkZoomDialog)
    assert box.windowTitle() == "Zoom range of Castles"
    assert box.min_zoom.itemText(0) == "No limit" and box.max_zoom.itemText(0) == "No limit"
    box.min_zoom.setCurrentIndex(box.min_zoom.count() - 1)
    box.max_zoom.setCurrentIndex(1)
    box.ok_button.click()
    QApplication.processEvents()
    assert box.isVisible() and box.message.text()   # refused, and it stays
    assert window.session.bookmarks.lists[0].max_zoom_m is None
    box.min_zoom.setCurrentIndex(0)
    box.ok_button.click()
    QApplication.processEvents()
    assert not box.isVisible() and window.session.bookmarks.lists[0].max_zoom_m is not None
    assert "zoom up to" in lines(dialog)[0] and any(t.startswith("Zoom range of Castles:") for t in window.announcer.texts)
    dialog.close_button.click()


def test_ctrl_shift_b_opens_the_manager_from_the_map(window):
    assert window.dispatch_key("Ctrl+Shift+B", "map")
    shown(window, BookmarkManagerDialog).close_button.click()


# The bookmark list dialog -----------------------------------------------------------------------------

def list_dialog(window):
    dialog = manager(window)
    dialog.open_button.click()
    return dialog, shown(window, BookmarkListDialog)


def test_open_list_opens_the_list_dialog_with_its_buttons_in_tab_order_and_a_close_button(window):
    manager_box, box = list_dialog(window)
    assert box.windowTitle() == "Bookmarks in Castles" and lines(box) == ["Winchester", "Alpha", "Corfe"]
    widgets = [box.list, box.up_button, box.down_button, box.target, box.copy_button, box.move_button, box.delete_button,
               box.close_button]
    assert [w.text() for w in widgets[1:3] + widgets[4:]] == ["Move up", "Move down", "Copy to list", "Move to list",
                                                                "Delete", "Close"]
    assert tab_order(box, widgets) == widgets
    assert [box.target.itemText(i) for i in range(box.target.count())] == ["Holidays"]
    assert box.target.accessibleName() == "Other list"
    box.close_button.click()
    QApplication.processEvents()
    assert not box.isVisible() and manager_box.isVisible() and has_focus(manager_box.list)


def test_enter_in_the_manager_list_opens_the_list_dialog(window, qtbot):
    dialog = manager(window)
    qtbot.keyClick(dialog.list, Qt.Key.Key_Return)
    shown(window, BookmarkListDialog).close_button.click()
    dialog.close_button.click()


def test_move_up_and_down_in_the_list_are_unavailable_at_the_ends_and_say_nothing(window, tmp_path):
    _manager, box = list_dialog(window)
    assert not box.up_button.available and box.down_button.available
    box.down_button.click()
    assert lines(box) == ["Alpha", "Winchester", "Corfe"] and box.list.currentRow() == 1 and has_focus(box.list)
    assert window.announcer.texts == []
    assert [m.name for m in window.session.bookmarks.lists[0].bookmarks] == ["Alpha", "Winchester", "Corfe"]
    box.list.setCurrentRow(2)
    assert not box.down_button.available and box.up_button.available
    box.close_button.click()
    _manager.close_button.click()


def test_copy_and_move_to_another_list_say_where_the_bookmark_went(window, tmp_path):
    manager_box, box = list_dialog(window)
    box.list.setCurrentRow(1)
    box.copy_button.click()
    assert "Copied Alpha to Holidays as Alpha_1." in window.announcer.texts and lines(box) == ["Winchester", "Alpha", "Corfe"]
    box.move_button.click()
    assert "Moved Alpha to Holidays." in window.announcer.texts and lines(box) == ["Winchester", "Corfe"]
    assert [m.name for m in window.session.bookmarks.lists[1].bookmarks] == ["Rome", "Alpha_1", "Alpha"]
    assert "Alpha_1" in storage.load_bookmarks(tmp_path)
    box.close_button.click()
    QApplication.processEvents()
    assert lines(manager_box) == ["Castles, 2 bookmarks", "Holidays, 3 bookmarks"]   # counted again on return
    manager_box.close_button.click()


def test_delete_a_bookmark_asks_and_the_focus_goes_to_the_next(window, tmp_path):
    manager_box, box = list_dialog(window)
    box.list.setCurrentRow(1)
    box.delete_button.click()
    question = shown(window, ConfirmBox)
    assert question.text() == "Delete the bookmark Alpha from Castles?"
    question.cancel_button.click()
    QApplication.processEvents()
    assert lines(box) == ["Winchester", "Alpha", "Corfe"]
    box.delete_button.click()
    shown(window, ConfirmBox).ok_button.click()
    QApplication.processEvents()
    assert lines(box) == ["Winchester", "Corfe"] and box.list.currentRow() == 1 and has_focus(box.list)
    assert "Deleted Alpha." in window.announcer.texts and "Alpha" not in storage.load_bookmarks(tmp_path)
    box.close_button.click()
    manager_box.close_button.click()


def test_an_empty_list_leaves_every_button_unavailable_that_needs_a_bookmark(window):
    window.session.bookmarks.new_list("Empty")
    manager_box = manager(window)
    manager_box.list.setCurrentRow(2)
    manager_box.open_button.click()
    box = shown(window, BookmarkListDialog)
    assert lines(box) == [] and box.list.accessibleDescription() == "This list has no bookmarks."
    assert not any(b.available for b in (box.up_button, box.down_button, box.copy_button, box.move_button,
                                         box.delete_button))
    box.close_button.click()
    manager_box.close_button.click()


def test_the_only_list_has_no_other_list_so_copy_and_move_are_unavailable(window):
    window.session.run("bookmark.manager_delete", index=1)
    window.session.run("bookmark.manager_delete_confirm")
    _manager, box = list_dialog(window)
    assert box.target.itemText(0) == "There is no other bookmark list"
    assert not box.copy_button.available and not box.move_button.available and box.delete_button.available
    box.close_button.click()
    _manager.close_button.click()


def test_the_list_dialog_opens_from_the_map_menu_on_the_list_used_last(window):
    window.session.bookmarks.use(1)
    window.dispatch("bookmark.list_open")
    box = shown(window, BookmarkListDialog)
    assert box.windowTitle() == "Bookmarks in Holidays" and lines(box) == ["Rome"]
    box.close_button.click()


def test_enter_in_the_bookmarks_list_does_nothing_and_enter_on_close_closes(window, qtbot):
    _manager, box = list_dialog(window)
    qtbot.keyClick(box.list, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert box.isVisible() and lines(box) == ["Winchester", "Alpha", "Corfe"] and window.announcer.texts == []
    box.close_button.setFocus()
    qtbot.keyClick(box.close_button, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert not box.isVisible()
    _manager.close_button.click()


# Bookmark files (P4-T9d; USR-5, DP217, DP219): the standard Save and Open boxes ----------------------

def choose_line(window, dialog, row):
    """Save to a file, then the core's four lines: the line chosen with Enter."""
    dialog.save_button.click()
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(HistoryDialog) if d.isVisible()]
    box.list.setCurrentRow(row)
    box.go_to_selected()
    QApplication.processEvents()


def save_as(window, monkeypatch, path, row):
    monkeypatch.setattr(dialogs.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(path), "")))
    dialog = manager(window)
    choose_line(window, dialog, row)
    return dialog


@pytest.mark.parametrize("row, name, start", [(0, "castles.geojson", '{'), (1, "castles.gpx", "<?xml")])
def test_a_list_saved_as_geojson_or_gpx_is_written_as_the_cores_text_and_opens_back_as_castles_2(
        window, monkeypatch, tmp_path, row, name, start):
    path = tmp_path / name
    dialog = save_as(window, monkeypatch, path, row)
    text = path.read_bytes().decode("utf-8")
    assert text.lstrip().startswith(start) and "\r" not in text
    assert "Winchester" in text and "Corfe" in text
    assert has_focus(dialog.list)
    assert "Castles" in window.announcer.spoken[-1][0]
    monkeypatch.setattr(dialogs.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
    dialog.open_file_button.click()
    QApplication.processEvents()
    assert lines(dialog)[-1].startswith("Castles 2, 3 bookmarks")
    b = window.session.bookmarks
    mine, copy = b.lists[0], b.lists[-1]
    assert [m.name for m in copy.bookmarks] == [m.name for m in mine.bookmarks]
    assert has_focus(dialog.list)


def test_cancel_in_the_save_or_open_box_does_nothing(window, monkeypatch):
    spoken = len(window.announcer.spoken)
    dialog = save_as(window, monkeypatch, "", 0)
    assert len(window.announcer.spoken) == spoken and has_focus(dialog.list)
    monkeypatch.setattr(dialogs.QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    dialog.open_file_button.click()
    QApplication.processEvents()
    assert lines(dialog) == ["Castles, 3 bookmarks", "Holidays, 1 bookmark"]
    assert len(window.announcer.spoken) == spoken and has_focus(dialog.list)


def test_a_file_that_cannot_be_written_says_so(window, monkeypatch, tmp_path):
    save_as(window, monkeypatch, tmp_path / "no folder" / "x.geojson", 0)
    assert "could not" in window.announcer.spoken[-1][0].lower()
