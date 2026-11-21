"""The measure start (P4-T9a; USR-4, DP214): Ctrl+Shift+M on an item or bookmark makes it where Shift+M measures
from; Ctrl+Shift+M on the map puts it back to where you are. Moving does not change it, and it is not saved."""
import pytest
from geographiclib.geodesic import Geodesic

from mapcore import settings as settings_mod
from mapcore.commands import keys as keymaps
from mapcore.commands import registry
from mapcore.describe import words
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
ROME = (41.9, 12.5)


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    s.bookmarks.lists[0].name = "Castles"
    s.bookmarks.add(0, "Rome", *ROME)
    s.bookmarks.add(0, "Paris", 48.85, 2.35)
    s.bookmarks_changed(s.start())
    s.panel(open={"bookmarks"})
    yield s
    s.store.close()


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def test_the_keys():
    assert registry.default_key("measure.start") == "Ctrl+Shift+M"
    assert registry.command_for_key("desktop", "Ctrl+Shift+M", "panel").name == "measure.start"
    assert registry.command_for_key("desktop", "Ctrl+Shift+M", "map").name == "measure.start_here"
    assert registry.command_for_key("web", "Ctrl+Shift+M", "panel").name == "measure.start"
    assert registry.command_for_key("web", "Ctrl+Shift+M", "map").name == "measure.start_here"
    desktop = keymaps.resolve("mac-desktop", "desktop", "mac")
    browser = keymaps.resolve("mac-browser", "web", "mac")
    assert desktop["measure.start"] == desktop["measure.start_here"] == "Shift+Cmd+M"
    assert browser["measure.start"] == browser["measure.start_here"] == "Ctrl+Shift+Y"
    assert browser["focus.menu"] == "Ctrl+Shift+M"


def test_ctrl_shift_m_on_a_bookmark_makes_it_the_start(s):
    r = s.run("measure.start", item="bookmark:0:0", group="bookmarks")
    assert said(r) == "Measuring from Rome."
    assert s._measure_start["name"] == "Rome" and s._measure_start["lat"] == pytest.approx(ROME[0])
    assert (s.world.lat, s.world.lon) == pytest.approx((HAMPSHIRE["lat"], HAMPSHIRE["lon"]))   # it never moves you


def test_shift_m_measures_from_the_start_to_an_item(s):
    s.run("measure.start", item="bookmark:0:0", group="bookmarks")
    text = said(s.run("measure.to", item="bookmark:0:1", group="bookmarks"))
    assert text.startswith("Paris, ") and text.endswith(", from Rome") and "north-west" in text
    # from where you are, Paris is to the south-east
    s.run("measure.start_here")
    assert "south-east" in said(s.run("measure.to", item="bookmark:0:1", group="bookmarks"))
    assert "from Rome" not in said(s.run("measure.to", item="bookmark:0:1", group="bookmarks"))


def test_an_ordinary_item_can_be_the_start_and_moving_does_not_change_it(s):
    hampshire = next(a for a in s.areas if a.name == "Hampshire")
    r = s.run("measure.start", item=hampshire.id, group="within")
    assert said(r) == "Measuring from Hampshire."
    s.run("move.north")
    assert s._measure_start["name"] == "Hampshire"
    assert said(s.run("measure.to", item="bookmark:0:0", group="bookmarks")).endswith(", from Hampshire")


def test_ctrl_shift_m_on_the_map_puts_the_start_back(s):
    s.run("measure.start", item="bookmark:0:0", group="bookmarks")
    r = s.press("Ctrl+Shift+M", "map")
    assert said(r) == "Measuring from where you are."
    assert s._measure_start is None
    assert "from" not in said(s.run("measure.to", item="bookmark:0:1", group="bookmarks")).split(", ", 2)[-1]


def test_on_a_group_heading_nothing_happens(s):
    heading = next(g for g in s.panel(open={"bookmarks"}) if g["id"] == "bookmarks")["items"][0]
    r = s.run("measure.start", item=heading["id"], group="bookmarks")
    assert not r.announcements and s._measure_start is None


def test_shift_m_on_the_map_measures_from_the_start_to_the_current_bookmark(s):
    s.run("panel.go", item="bookmark:0:1", group="bookmarks")   # at Paris, which becomes the current bookmark
    s.run("measure.start", item="bookmark:0:0", group="bookmarks")
    s.run("panel.select", item=None, group="bookmarks")
    text = said(s.run("measure.to"))
    assert text.startswith("Paris, ") and text.endswith(", from Rome")


def test_a_deleted_bookmark_puts_the_start_back_and_says_so_once(s):
    s.run("measure.start", item="bookmark:0:0", group="bookmarks")
    s.bookmarks.delete(0, 0)
    s.bookmarks_changed(s.start())
    s.panel(open={"bookmarks"})
    first = said(s.run("measure.to", item="bookmark:0:0", group="bookmarks"))
    assert first.startswith("The bookmark Rome is gone, so measuring from where you are.")
    assert "from Rome" not in first and s._measure_start is None
    assert "is gone" not in said(s.run("measure.to", item="bookmark:0:0", group="bookmarks"))


def test_the_start_is_not_saved(s):
    s.run("measure.start", item="bookmark:0:0", group="bookmarks")
    assert "measure_start" not in str(s.save())


def test_figures_agree_with_geographiclib_within_a_metre(s):
    s.run("measure.start", item="bookmark:0:0", group="bookmarks")
    paris = (48.85, 2.35)
    reference = Geodesic.WGS84.Inverse(ROME[0], ROME[1], *paris)
    olat, olon, name = s._measure_origin()
    assert name == "Rome"
    from mapcore.geo import geodesy
    distance, bearing, _ = geodesy.inverse(olat, olon, *paris)
    assert distance == pytest.approx(reference["s12"], abs=1.0)
    assert (bearing - reference["azi1"] + 180) % 360 - 180 == pytest.approx(0.0, abs=1e-4)
    said_text = said(s.run("measure.to", item="bookmark:0:1", group="bookmarks"))
    assert words.distance_text(reference["s12"], s._units()) in said_text
