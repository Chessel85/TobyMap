"""The earcons: every event has a placeholder tone, short and distinct, own files fall back, and each
has its own switch, with one volume and the master mute over them all (P1-T12, P2-T8; SON-6, SON-7, SON-8)."""
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


def test_every_earcon_has_a_switch_and_an_own_file_in_the_earcons_tab():
    fields = {f["id"]: f for f in earcons_tab()["fields"]}
    assert fields["earcon_volume"]["kind"] == "number"
    for e in earcon_list():
        own = fields[f"earcon_{e['event']}"]
        if e.get("switch", True):   # the beacon's switch is B and its own setting (P2-T9)
            on = fields[f"earcon_on_{e['event']}"]
            assert on["kind"] == "yes_no" and on["default"] is True and on["label"] == f"{e['label']}: play it"
        assert own["kind"] == "sound_file" and own["default"] == ""
        assert own["label"] == f"{e['label']}: your own sound file"
    sound = next(t for t in settings_mod.schema()["tabs"] if t["id"] == "sound")
    assert not any(f["id"].startswith("earcon") for f in sound["fields"])   # all in one place


def test_the_old_crossed_and_passed_switch_is_kept_under_its_new_name():
    s = settings_mod.Settings({"crossed_earcon": False})
    assert s["earcon_on_crossed_added"] is False
    assert "crossed_earcon" not in s.values


def blocked(s):
    return s.press("Shift+Left")   # turning in north-fixed is blocked (NAV-12)


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


def test_the_earcon_volume_goes_with_every_earcon_and_placed_sound(test_pack):
    from tests.mapcore.test_hear_direction import hear_station, make

    s = make(test_pack)
    full = hear_station(s).sounds[0]["gain"]
    s.run("settings.set", field="earcon_volume", value=40)
    assert s.earcon_file("tick")["gain"] == pytest.approx(0.4)
    r = hear_station(s)
    assert r.sounds[0]["gain"] == pytest.approx(full * 0.4)
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
