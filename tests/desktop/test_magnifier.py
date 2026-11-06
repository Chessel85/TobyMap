"""Magnifier support on the desktop (P2-T13a; ACC-8, DP146): while the map has focus, the
square it reports as the text cursor holds the map centre, after a step, a click and a jump,
at three window sizes. The real caret needs a real window; offscreen, the square is checked."""
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from tests.desktop.test_window import make_window


def centre_in_window(w):
    m = w.map
    c = m.mapTo(w, QPoint(m.width() // 2, m.height() // 2))
    ratio = w.devicePixelRatioF()
    return c.x() * ratio, c.y() * ratio


def holds_centre(w):
    x, y, width, height = w.map.caret.rect
    cx, cy = centre_in_window(w)
    return x <= cx <= x + width and y <= cy <= y + height and width <= 16 and height <= 16


@pytest.mark.parametrize("size", [(700, 500), (1024, 768), (1600, 1000)])
def test_the_caret_holds_the_map_centre_after_a_step_a_click_and_a_jump(qtbot, test_pack, tmp_path, size):
    w = make_window(qtbot, test_pack, tmp_path)
    w.resize(*size)
    QApplication.processEvents()
    assert w.map.hasFocus()
    before = w.map.caret.moves
    qtbot.keyClick(w.map, Qt.Key.Key_Down)                      # a step
    assert w.map.caret.moves > before and holds_centre(w)
    before = w.map.caret.moves
    w.dispatch("map.click", x=w.map.width() / 3, y=w.map.height() / 3, width=w.map.width(), height=w.map.height())
    assert w.map.caret.moves > before and holds_centre(w)
    before = w.map.caret.moves
    w.dispatch("goto.set", text="48.85, 2.35")                  # a jump
    assert w.map.caret.moves > before and holds_centre(w)


def test_no_caret_while_the_map_does_not_have_focus(qtbot, test_pack, tmp_path):
    w = make_window(qtbot, test_pack, tmp_path)
    w.tree.setFocus()
    QApplication.processEvents()
    before = w.map.caret.moves
    w.dispatch("goto.set", text="48.85, 2.35")
    assert w.map.caret.moves == before
