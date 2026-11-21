"""Bookmarks on the desktop's map (P4-T8f; DP219 point 5): each mark is painted as a diamond where the core put it,
in the theme's bookmark colour, or the highlight's when it is the item selected, on top of everything."""
import pytest
from PySide6.QtGui import QImage, QPainter

from desktop.map_widget import paint_scene
from mapcore.render import themes
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    s.bookmarks.add(0, "Wantsum", 51.2, 1.3)
    s.bookmarks_changed(s.start())
    yield s
    s.store.close()


def painted(scene):
    scene["cross"] = scene["heading"] = None
    image = QImage(scene["width"], scene["height"], QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    paint_scene(painter, scene)
    painter.end()
    return image


def test_a_bookmark_is_painted_as_a_diamond_in_its_own_colour(qtbot, session):
    scene = session.scene(400, 300)
    [m] = scene["bookmarks"]
    assert m["text"] == "Wantsum"
    image = painted(scene)
    assert image.pixelColor(round(m["x"]), round(m["y"])).name() == themes.theme("standard")["bookmark"]
    # A diamond, not a square: the corner of the square around it is not painted.
    corner = image.pixelColor(round(m["x"] + m["half"] - 1), round(m["y"] - m["half"] + 1)).name()
    assert corner != themes.theme("standard")["bookmark"]


def test_a_selected_bookmark_is_painted_in_the_highlight(qtbot, session):
    session.selected = "bookmark:0:0"
    scene = session.scene(400, 300)
    [m] = scene["bookmarks"]
    image = painted(scene)
    assert image.pixelColor(round(m["x"]), round(m["y"])).name() == themes.theme("standard")["highlight_fill"]


def test_with_the_layer_off_nothing_is_painted(qtbot, session):
    session.run("layers.set", layer="bookmarks", field="on", value=False)
    assert session.scene(400, 300)["bookmarks"] == []
