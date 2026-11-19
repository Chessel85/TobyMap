"""P3-T10b: the query builder's form on the desktop (INF-9, ACC-7)."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import QueryDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}
GERMANY = "osm:r51477"


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    session.run("search.query", text="Germany")
    session.run("search.go", id=GERMANY)
    return w


def open_box(window, qtbot):
    qtbot.keyClick(window.map, Qt.Key.Key_Q)
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(QueryDialog) if d.isVisible()]
    return box


def choose(box, widget, label):
    for row in range(widget.count()):
        if widget.item(row).text() == label:
            widget.setCurrentRow(row)
            return
    raise AssertionError(label)


def test_q_opens_three_lists_ok_and_cancel_with_no_distance_yet(window, qtbot):
    box = open_box(window, qtbot)
    assert box.layer_list.hasFocus() and box.ok_button.text() == "OK" and box.cancel_button.text() == "Cancel"
    assert box.layer_list.count() and box.relation_list.count() and box.of_list.count()
    assert not box.distance.isVisible()


def test_the_distance_field_shows_only_for_within_a_distance_of(window, qtbot):
    box = open_box(window, qtbot)
    for row in range(box.relation_list.count()):
        box.relation_list.setCurrentRow(row)
        near = window.session.run("query.open").dialog["relations"][row]["distance"]
        assert box.distance.isVisible() == near


def test_ok_runs_the_query_and_closes(window, qtbot):
    box = open_box(window, qtbot)
    choose(box, box.layer_list, "Rivers")
    choose(box, box.relation_list, "crossing")
    box.ok_button.click()
    QApplication.processEvents()
    assert not box.isVisible()
    group = next(g for g in window.session.panel(open={"search"}) if g["id"] == "search")
    assert group["label"] == "Rivers crossing Germany, 1 item, by name"


def test_nothing_found_keeps_the_form_open_and_says_it(window, qtbot):
    box = open_box(window, qtbot)
    choose(box, box.layer_list, "Lakes")
    choose(box, box.relation_list, "crossing")
    box.ok_button.click()
    QApplication.processEvents()
    assert box.isVisible() and box.message.text() == "No lakes crossing Germany."


def test_cancel_closes_and_changes_nothing(window, qtbot):
    box = open_box(window, qtbot)
    box.cancel_button.click()
    QApplication.processEvents()
    assert not box.isVisible() and window.session.current_feature.id == GERMANY


def open_search(window):
    from desktop.dialogs import SearchDialog
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(SearchDialog) if d.isVisible()]
    return box


def test_search_for_a_feature_comes_back_with_it_chosen(window, qtbot):
    box = open_box(window, qtbot)
    choose(box, box.layer_list, "Rivers")
    choose(box, box.relation_list, "bordering")
    choose(box, box.of_list, "Search for a feature")
    box.ok_button.click()
    search = open_search(window)
    assert not box.isVisible()
    search.field.setText("Switzerland")
    search.search_now()
    search.go_to_selected()
    QApplication.processEvents()
    (again,) = [d for d in window.findChildren(QueryDialog) if d.isVisible()]
    assert again.layer_list.currentItem().text() == "Rivers"
    assert again.relation_list.currentItem().text() == "bordering"
    assert again.of_list.currentItem().text().startswith("Switzerland")
    assert window.session.current_feature.id == GERMANY


def test_cancelling_that_search_comes_back_to_the_form(window, qtbot):
    box = open_box(window, qtbot)
    choose(box, box.layer_list, "Rivers")
    choose(box, box.of_list, "Search for a feature")
    box.ok_button.click()
    open_search(window).cancel_button.click()
    QApplication.processEvents()
    (again,) = [d for d in window.findChildren(QueryDialog) if d.isVisible()]
    assert again.layer_list.currentItem().text() == "Rivers"
    assert again.of_list.currentItem().text().startswith("Germany")
