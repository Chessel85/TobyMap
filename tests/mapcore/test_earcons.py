"""The earcons: every event has a placeholder tone, short and distinct, own files fall back, and each
has its own switch and its own volume, with the master mute over them all (P1-T12, P2-T8, P2-T17p;
SON-6, SON-7, SON-8, DP163)."""
import wave

import pytest

from mapcore import settings as settings_mod
from mapcore.describe import earcon_list
from mapcore.session import MapSession
from tools import make_placeholder_sounds as make


def test_every_earcon_gets_a_short_distinct_file(tmp_path):
    assert make.main(["--out", str(tmp_path)]) == 0
    sizes = {}
    for e in earcon_list():
        with wave.open(str(tmp_path / e["file"])) as w:
            assert w.getnframes() / w.getframerate() < 0.5   # short, so it never gets in the way of speech
            sizes[e["event"]] = (w.getnframes(), (tmp_path / e["file"]).read_bytes())
    assert len({b for _n, b in sizes.values()}) == len(sizes)   # no two are the same


def test_an_existing_file_is_never_overwritten(tmp_path):
    (tmp_path / "tick.wav").write_bytes(b"mine")
    make.main(["--out", str(tmp_path)])
    assert (tmp_path / "tick.wav").read_bytes() == b"mine"


def test_phase_1_uses_the_tick_and_blocked_sounds():
    assert {e["event"] for e in earcon_list() if e["phase"] == 1} == {"tick", "blocked"}


def test_an_own_sound_file_is_offered_and_a_failure_is_spoken(test_pack):
    s = MapSession(packs=[test_pack])
    assert s.earcon_file("tick") == {"event": "tick", "custom": None, "default": "click.wav", "gain": 1.0}
    s.run("settings.set", field="earcon_tick", value="C:/mine/tick.wav")
    assert s.earcon_file("tick")["custom"] == "C:/mine/tick.wav"
    r = s.earcon_failed("tick")
    assert r.announcements[0]["text"] ==         "Your own sound file for Tick could not be played, so the default sound is used."


# P2-T8: every earcon switchable, one volume, and the master mute -----------------

@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.9, "lon": -1.45, "zoom_m": 5000, "step_m": 1000})
    s.start()
    yield s
    s.store.close()


def earcons_tab():
    return next(t for t in settings_mod.schema()["tabs"] if t["id"] == "earcons")


def test_every_earcon_has_a_switch_a_volume_and_an_own_file_in_the_earcons_tab():
    fields = {f["id"]: f for f in earcons_tab()["fields"]}
    for e in earcon_list():
        if not e.get("listed", True):    # the beacon: its settings are in the Sound tab (P2-T17p)
            assert not any(f.get("earcon") == e["event"] for f in fields.values())
            continue
        on, volume, own = fields[f"earcon_on_{e['event']}"], fields[f"earcon_volume_{e['event']}"], fields[f"earcon_{e['event']}"]
        assert on["kind"] == "yes_no" and on["default"] is True and on["label"] == f"{e['label']}: play it"
        assert volume["kind"] == "number" and volume["default"] == 100 and (volume["min"], volume["max"]) == (0, 100)
        assert volume["label"] == f"{e['label']}: volume, in percent"
        assert own["kind"] == "sound_file" and own["default"] == ""
        assert own["label"] == f"{e['label']}: your own sound file"
    sound = next(t for t in settings_mod.schema()["tabs"] if t["id"] == "sound")
    assert [f["id"] for f in sound["fields"] if f["id"].startswith("earcon")] == ["earcon_beacon"]


def test_there_is_no_volume_for_every_earcon_together():
    """DP163: the PO wants no volume over all the earcons, only each earcon's own."""
    assert "earcon_volume" not in settings_mod.fields()


def test_the_earcons_tab_is_one_list_with_the_ids_of_each_earcons_controls():
    tab = earcons_tab()
    assert tab["list_label"] == "Earcons"
    rows = tab["earcons"]
    assert [r["label"] for r in rows] == [e["label"] for e in earcon_list() if e["event"] != "beacon"]
    assert rows[0] == {"event": "tick", "label": "Tick", "on": "earcon_on_tick",
                       "volume": "earcon_volume_tick", "file": "earcon_tick"}
    ids = {f["id"] for f in tab["fields"]}
    assert all({r["on"], r["volume"], r["file"]} <= ids for r in rows)


def test_a_saved_volume_for_every_earcon_becomes_each_earcons_own():
    s = settings_mod.Settings({"earcon_volume": 40, "earcon_volume_blocked": 70})
    assert s["earcon_volume_tick"] == 40 and s["earcon_volume_blocked"] == 70
    assert "earcon_volume" not in s.values


def test_the_old_crossed_and_passed_switch_is_kept_under_its_new_name():
    s = settings_mod.Settings({"crossed_earcon": False})
    assert s["earcon_on_crossed_added"] is False
    assert "crossed_earcon" not in s.values


def blocked(s):
    s.back_places.clear()
    return s.press("Alt+,")        # nowhere to go back to is blocked (NAV-10)


def test_the_tick_and_blocked_play_and_each_can_be_switched_off(session):
    assert session.run("move.east", held=True, repeat=True).earcons == ["tick"]
    assert blocked(session).earcons == ["blocked"]
    session.run("settings.set", field="earcon_on_tick", value=False)
    assert session.run("move.east", held=True, repeat=True).earcons == []
    assert blocked(session).earcons == ["blocked"]        # only the one switched off is silent
    session.run("settings.set", field="earcon_on_blocked", value=False)
    assert blocked(session).earcons == []


def test_the_held_keys_clicks_follow_the_ticks_switch(session):
    session.run("move.east")
    session.holding = "move.east"
    assert session.hold_info()["tick"] is True
    session.run("settings.set", field="earcon_on_tick", value=False)
    assert session.hold_info()["tick"] is False


def test_a_placed_earcon_can_be_switched_off(test_pack):
    from tests.mapcore.test_hear_direction import hear_station, make

    s = make(test_pack)
    s.run("settings.set", field="earcon_on_item_direction", value=False)
    r = hear_station(s)
    assert r.sounds == [] and r.voice is not None   # the label is still said
    s.store.close()


def test_each_earcons_own_volume_goes_with_it_alone_and_with_its_placed_sound(test_pack):
    from tests.mapcore.test_hear_direction import hear_station, make

    s = make(test_pack)
    full = hear_station(s).sounds[0]["gain"]
    s.run("settings.set", field="earcon_volume_tick", value=40)
    assert s.earcon_file("tick")["gain"] == pytest.approx(0.4)
    assert s.earcon_file("blocked")["gain"] == pytest.approx(1.0)      # the others are unchanged
    assert hear_station(s).sounds[0]["gain"] == pytest.approx(full)
    s.run("settings.set", field="earcon_volume_item_direction", value=25)
    r = hear_station(s)
    assert r.sounds[0]["gain"] == pytest.approx(full * 0.25)
    assert r.voice["placed"]["gain"] == pytest.approx(full)   # the voice has its own volume
    s.store.close()


def test_mute_silences_earcons_placed_sounds_and_the_voice(test_pack):
    from tests.mapcore.test_hear_direction import hear_station, make

    s = make(test_pack)
    assert s.press("Ctrl+M").settings_changed
    r = hear_station(s)
    assert r.sounds == [] and r.voice is None and r.earcons == []
    assert s.run("move.east", held=True, repeat=True).earcons == []
    assert s.run("sound.preview", event="tick").earcons == []
    s.store.close()


def test_the_sounds_in_help_plays_an_earcon_even_when_it_is_switched_off(session):
    session.run("settings.set", field="earcon_on_ding", value=False)
    assert session.run("sound.preview", event="ding").earcons == ["ding"]


def test_with_the_fixed_tone_switched_off_a_sound_beyond_the_view_is_quiet_and_muffled(session):
    session.run("settings.set", field="beyond_view", value="tone")
    far = (session.world.lat + 5, session.world.lon)   # far beyond a 5 km view
    assert session.place_sound("item_direction", *far)["sound"] == "beyond_view"
    session.run("settings.set", field="earcon_on_beyond_view", value=False)
    placed = session.place_sound("item_direction", *far)
    assert placed["sound"] == "item_direction" and placed["beyond"]
