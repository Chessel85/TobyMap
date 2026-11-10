"""Reset all settings, in the Map menu (P2-T18h): everything as on a new installation, after a
yes in a message box."""
from mapcore.commands import registry
from mapcore.session import MapSession


def fresh(test_pack):
    return MapSession(packs=[test_pack])


def test_it_is_in_the_map_menu_and_asks_first(test_pack):
    command = registry.by_name("settings.reset")
    assert command.menu == "Map" and command.label == "Reset all settings"
    s = fresh(test_pack)
    s.settings.set("units", "imperial")
    r = s.run("settings.reset")
    assert r.dialog["kind"] == "confirm" and r.dialog["submit"] == "settings.reset_confirm"
    assert (r.dialog["ok"], r.dialog["cancel"]) == ("Reset", "Cancel")
    assert "cannot be undone" in r.dialog["text"]
    assert s.settings["units"] == "imperial"   # nothing changes until the answer


def test_the_answer_puts_everything_back_as_on_a_new_installation(test_pack):
    new = fresh(test_pack).save()
    s = MapSession(packs=[test_pack], settings={"values": {"units": "imperial", "beacon_on": True},
                                                 "keys": {"move.north": "K"}},
                   saved_state={"lat": 10.0, "lon": 20.0, "zoom_m": 250000, "step_m": 25000})
    s.run("goto.set", text="11, 21")
    s.run("layers.set", layer="regions", values={"on": False})
    assert s.save() != new and s.settings["units"] == "imperial" and s.settings.keys
    r = s.run("settings.reset_confirm")
    assert s.save() == new
    assert not s.back_places and not s.forward_places
    assert r.action == "reset" and r.settings_changed and r.redraw
    assert r.beacon["on"] is False
    assert r.announcements[0]["text"].startswith("All settings are reset, as on a new installation. ")
    assert s.store.packs   # the packs stay open
    assert s.run("move.north").redraw   # and the session goes on working
    assert s.settings["units"] == "metric" and not s.settings.keys
