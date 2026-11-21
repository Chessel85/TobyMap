"""The beacon from a bookmark (P4-T8g; SON-10): any bookmark can be the beacon's source, chosen in Settings by
its list and name, or with Shift+B from the current bookmark. It falls back to the North Pole, and says so once,
when the bookmark is deleted or its list or the Bookmarks layer is switched off."""
import pytest

from mapcore import settings as settings_mod
from mapcore.commands import registry
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
ROME = settings_mod.beacon_bookmark_value("Castles", "Rome")


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    s.bookmarks.lists[0].name = "Castles"
    s.bookmarks.add(0, "Rome", 41.9, 12.5)
    s.bookmarks.add(0, "Alpha", 51.06, -1.31)
    s.bookmarks_changed(s.start())
    yield s
    s.store.close()


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def test_settings_lists_every_bookmark_by_list_and_name(s):
    field = next(f for t in s.settings_schema()["tabs"] for f in t["fields"] if f["id"] == "beacon_target")
    labels = [c[1] for c in field["choices"]]
    assert labels[:2] == ["The North Pole", "The South Pole"]
    assert labels[-2:] == ["Castles: Rome", "Castles: Alpha"]
    s.run("settings.set", field="beacon_target", value=field["choices"][-2][0])
    assert s.settings["beacon_target"] == ROME


def test_the_beacon_points_at_the_bookmark(s):
    s.run("settings.set", field="beacon_target", value=ROME)
    s.run("beacon.toggle")
    s.world.orientation, s.world.heading = "cardinal", 0.0
    p = s.beacon()["placed"]
    d, bearing = s._beacon_target()
    assert 1_400_000 < d < 1_600_000 and p["distance_m"] == pytest.approx(d)   # Winchester to Rome, about 1,500 km
    assert 100 < bearing < 140 and p["relative_deg"] == pytest.approx(bearing, abs=0.5)   # south east
    assert p["pan"] > 0


def test_it_follows_a_bookmark_that_is_moved_or_renamed(s):
    s.run("settings.set", field="beacon_target", value=ROME)
    s.run("beacon.toggle")
    s.bookmarks.rename(0, 0, "Roma")
    r = s.run("move.north")
    assert s.settings["beacon_target"] == settings_mod.beacon_bookmark_value("Castles", "Roma")
    assert r.settings_changed and "no longer" not in said(r)
    s.bookmarks.move_to(0, 0, s.bookmarks.new_list("Holidays"))
    s.run("move.south")
    assert s.settings["beacon_target"] == settings_mod.beacon_bookmark_value("Holidays", "Roma")


def test_a_deleted_bookmark_falls_back_to_the_north_pole_and_says_so_once(s):
    s.run("settings.set", field="beacon_target", value=ROME)
    s.run("beacon.toggle")
    s.bookmarks.delete(0, 0)
    r = s.run("move.north")
    assert said(r).count("The bookmark Rome is no longer shown, so the beacon now comes from the North Pole.") == 1
    assert s.settings["beacon_target"] == "north_pole" and r.settings_changed
    assert r.beacon["placed"] is not None and s._beacon_target()[1] == pytest.approx(0.0, abs=0.01)
    assert "no longer" not in said(s.run("move.north"))


def test_a_list_or_the_layer_switched_off_falls_back_too(s):
    s.run("settings.set", field="beacon_target", value=ROME)
    s.bookmarks.set_on(0, False)
    assert "no longer shown" in said(s.run("move.north"))
    assert s.settings["beacon_target"] == "north_pole"
    s.bookmarks.set_on(0, True)
    s.run("settings.set", field="beacon_target", value=ROME)
    assert "no longer shown" in said(s.run("layers.set", layer="bookmarks", field="on", value=False))
    assert s.settings["beacon_target"] == "north_pole"


def test_a_value_that_is_not_a_bookmark_is_refused_and_a_missing_one_falls_back():
    with pytest.raises(ValueError):
        settings_mod.checked("beacon_target", "bookmark:not json")
    with pytest.raises(ValueError):
        settings_mod.checked("beacon_target", "mars")


def test_shift_b_makes_the_current_bookmark_the_source(s):
    command = registry.by_name("beacon.bookmark")
    assert registry.default_key(command.name) == "Shift+B" and command.region == "map"
    assert "Alpha" not in said(s.press("Shift+B"))   # none current yet: it says how to make one
    assert s.settings["beacon_target"] == "north_pole"
    s.panel(open={"bookmarks"})
    s.run("panel.go", item="bookmark:0:1", group="bookmarks")
    s.run("panel.select", item=None, group="bookmarks")
    r = s.press("Shift+B")
    assert said(r) == "Beacon now comes from the bookmark Alpha."
    assert s.settings["beacon_target"] == settings_mod.beacon_bookmark_value("Castles", "Alpha")
    assert s.settings["beacon_on"] and r.settings_changed


def test_reset_all_settings_puts_the_beacon_back(s):
    s.run("settings.set", field="beacon_target", value=ROME)
    s.run("settings.reset_confirm")
    assert s.settings["beacon_target"] == "north_pole" and not s.settings["beacon_on"]
    assert s.bookmarks.lists[0].bookmarks[0].name == "Rome"   # the bookmarks stay


def test_the_setting_is_saved_and_read_back(s):
    s.run("settings.set", field="beacon_target", value=ROME)
    assert settings_mod.Settings.from_dict(s.save()["settings"])["beacon_target"] == ROME
