"""Hear its direction (P2-T7c; DP143, SON-3, ANN-4, ACC-1, AD-10).

On an item of Nearby or Crossed and passed, Space in the Information panel plays the item's
sound from its direction and distance, then its name and distance in the spatial voice from
the same place. The core says how both are heard; it plays nothing. The label goes into the
announcement history, to Braille without speech on the desktop, and to the screen reader only
when "also speak spatial labels" is on.
"""
import pytest

from mapcore.geo import geodesy
from mapcore.session import MapSession
from mapcore.sound.scene import BEHIND_PITCH

STATION = (50.9074977, -1.4142289)


def make(test_pack, platform="desktop", lat=STATION[0], lon=STATION[1] - 0.03):
    s = MapSession(platform=platform, packs=[test_pack],
                   saved_state={"lat": lat, "lon": lon, "zoom_m": 5000, "step_m": 1000})
    s.start()
    return s


@pytest.fixture
def session(test_pack):
    s = make(test_pack)
    yield s
    s.store.close()


def nearby(s):
    return next(g for g in s.panel() if g["id"] == "nearby")["items"]


def station_id(s):
    return next(i["id"] for i in nearby(s) if i["label"].startswith("Southampton Central"))


def hear_station(s):
    s.run("panel.select", item=station_id(s))
    return s.press("Space", "panel")


def test_space_hears_the_item_in_the_panel_and_is_still_where_am_i_on_the_map(session):
    r = hear_station(session)
    assert r.voice is not None and r.voice["text"].startswith("Southampton Central, ")
    assert session.press("Space", "map").voice is None


def test_the_label_is_the_name_and_distance(session):
    r = hear_station(session)
    distance, _, _ = geodesy.inverse(session.world.lat, session.world.lon, *STATION)
    assert r.voice["text"] == f"Southampton Central, {distance / 1000:.1f} kilometres"


def test_the_sound_and_the_label_come_from_the_same_place_to_the_east(session):
    r = hear_station(session)
    sound, voice = r.sounds[0], r.voice["placed"]
    assert sound["sound"] == "item_direction"   # the stations layer has no sound of its own
    assert 80 < sound["relative_deg"] < 100
    assert voice["relative_deg"] == sound["relative_deg"] and voice["pan"] == sound["pan"]
    assert voice["gain"] == sound["gain"] and voice["pitch"] == 1.0
    assert r.voice["after"], "the label waits for the item's sound"


def test_behind_you_the_label_has_the_lower_pitch(test_pack):
    s = make(test_pack, lon=STATION[1] + 0.03)   # the station is to the west
    s.world.set_orientation("free")
    s.world.face(90.0)
    r = hear_station(s)
    assert r.voice["placed"]["behind"] and r.voice["placed"]["pitch"] == BEHIND_PITCH
    assert r.sounds[0]["pitch"] == BEHIND_PITCH
    s.store.close()


def test_facing_the_item_puts_the_label_ahead(session):
    session.world.set_orientation("free")
    session.world.face(90.0)
    r = hear_station(session)
    assert abs(r.voice["placed"]["pan"]) < 0.2


def test_the_label_goes_into_the_history_and_to_braille_without_speech(session):
    r = hear_station(session)
    label = r.voice["text"]
    assert session.history[-1] == label
    assert [a["channel"] for a in r.announcements] == ["braille"]
    assert r.announcements[0]["text"] == label and r.announcements[0]["fallback"] is None


def test_also_speak_sends_the_label_to_the_screen_reader_once(session):
    session.run("settings.set", field="voice_also_speak", value=True)
    r = hear_station(session)
    assert r.announcements == [{"text": r.voice["text"], "channel": "speech", "priority": "polite"}],         "spoken, and so brailled by the screen reader, once"
    assert session.history.count(r.voice["text"]) == 1


def test_the_web_has_no_braille_only_route(test_pack):
    s = make(test_pack, platform="web")
    r = hear_station(s)
    assert not r.announcements and r.voice is not None
    s.store.close()


def test_volume_and_speed_are_the_voices_own(session):
    loud = hear_station(session).voice
    session.run("settings.set", field="voice_volume", value=50)
    session.run("settings.set", field="voice_rate", value=150)
    quiet = hear_station(session).voice
    assert quiet["placed"]["gain"] == pytest.approx(loud["placed"]["gain"] / 2)
    assert quiet["rate"] == 1.5 and loud["rate"] == 1.0


def test_the_voice_goes_up_to_five_times_as_fast(session):
    """PO note on checklist 9.7: up to 500 percent."""
    field = next(f for tab in session.settings_schema()["tabs"] for f in tab["fields"] if f["id"] == "voice_rate")
    assert (field["min"], field["max"]) == (50, 500)
    session.run("settings.set", field="voice_rate", value=500)
    assert hear_station(session).voice["rate"] == 5.0


def test_muted_nothing_plays_but_the_label_is_kept_in_the_history(session):
    session.run("sound.mute", on=True)
    r = hear_station(session)
    assert r.voice is None and not r.sounds
    assert session.history[-1].startswith("Southampton Central, ")


def test_not_on_an_item_it_says_where_it_works(session):
    session.run("panel.select", item=session.areas[0].id)   # an item of Contains
    r = session.press("Space", "panel")
    assert r.voice is None
    assert r.announcements[0]["text"] == "Hear its direction works on an item of Nearby or Crossed and passed."


def test_it_works_on_crossed_and_passed(session):
    lat, lon = STATION
    session.world.lat, session.world.lon = lat + 0.003, lon - 0.02
    session.world.step_index = session.world.step_list.index(5000)
    session.run("move.east")
    session.crossed_now()
    crossed = next(g for g in session.panel() if g["id"] == "crossed")["items"]
    item = next(i for i in crossed if i["label"].startswith("Southampton Central"))
    session.run("panel.select", item=item["id"])
    r = session.press("Space", "panel")
    assert r.voice["text"].startswith("Southampton Central, ")
    assert 180 < r.voice["placed"]["relative_deg"] < 360   # behind, to the west, after the step east


def test_joined_commands_keep_the_sound_and_the_label(session):
    """The web version sends its commands through run_many (ANN-3)."""
    session.run("panel.select", item=station_id(session))
    r = session.run_many([("panel.hear", {})])
    assert [s["sound"] for s in r.sounds] == ["item_direction"] and r.voice is not None
