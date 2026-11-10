"""Hear its direction (P2-T7c; DP143, SON-3, ANN-4, ACC-1, AD-10).

On an item of Nearby or Crossed and passed, Space in the Information panel plays the item's
sound from its direction and distance, then its name and distance in the spatial voice from
the same place. The core says how both are heard; it plays nothing. The label is what Shift+Space
repeats, goes to Braille without speech on the desktop, and to the screen reader only when
"also speak spatial labels" is on.
"""
import pytest

from mapcore.geo import geodesy
from mapcore.session import MapSession
from mapcore.sound.scene import BEHIND_PITCH, VOICE_BEHIND_PITCH
from mapcore.sound.stretch import piper_speed

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
    assert voice["gain"] == sound["gain"] and voice["pitch"] == 1.0 and r.voice["pitch"] == 1.0
    assert r.voice["after"], "the label waits for the item's sound"


def test_behind_you_the_label_has_the_lower_pitch(test_pack):
    s = make(test_pack, lon=STATION[1] + 0.03)   # the station is to the west
    s.world.set_orientation("free")
    s.world.face(90.0)
    r = hear_station(s)
    # The item's sound is played slower, so lower; the label is made lower at the same speed by
    # the core's time stretching, so the shells must not slow it too (P2-T16g, the PO's sample 9).
    assert r.sounds[0]["pitch"] == BEHIND_PITCH
    assert r.voice["placed"]["behind"] and r.voice["placed"]["pitch"] == 1.0
    assert r.voice["pitch"] == VOICE_BEHIND_PITCH   # 1.5 semitones lower, the PO's choice
    s.store.close()


def test_facing_the_item_puts_the_label_ahead(session):
    session.world.set_orientation("free")
    session.world.face(90.0)
    r = hear_station(session)
    assert abs(r.voice["placed"]["pan"]) < 0.2


def test_the_label_is_repeated_and_goes_to_braille_without_speech(session):
    r = hear_station(session)
    label = r.voice["text"]
    assert session.last_spoken == label
    assert [a["channel"] for a in r.announcements] == ["braille"]
    assert r.announcements[0]["text"] == label and r.announcements[0]["fallback"] is None


def test_also_speak_sends_the_label_to_the_screen_reader_once(session):
    session.run("settings.set", field="voice_also_speak", value=True)
    r = hear_station(session)
    assert r.announcements == [{"text": r.voice["text"], "channel": "speech", "priority": "polite"}],         "spoken, and so brailled by the screen reader, once"
    assert session.last_spoken == r.voice["text"]


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
    assert loud["stretch"] == 1.0 and quiet["stretch"] > 1.0   # Piper alone is slower than asked (P2-T16g)


def test_the_voice_goes_up_to_five_times_as_fast(session):
    """PO note on checklist 9.7: up to 500 percent."""
    field = next(f for tab in session.settings_schema()["tabs"] for f in tab["fields"] if f["id"] == "voice_rate")
    assert (field["min"], field["max"]) == (50, 500)
    session.run("settings.set", field="voice_rate", value=500)
    voice = hear_station(session).voice
    # Piper as fast as it cleanly can, and time stretching the rest, at the same pitch (P2-T16g).
    assert voice["rate"] == 2.0
    assert piper_speed(voice["rate"]) * voice["stretch"] == pytest.approx(5.0)


def test_muted_nothing_plays_but_the_label_can_be_repeated(session):
    session.run("sound.mute", on=True)
    r = hear_station(session)
    assert r.voice is None and not r.sounds
    assert session.last_spoken.startswith("Southampton Central, ")


def test_not_on_an_item_it_says_and_does_nothing(session):
    r = session.run("panel.hear", item="no-such-item", group="within")
    assert r.voice is None and not r.sounds and not r.announcements   # P2-T18a


def test_on_a_group_heading_after_an_item_it_says_and_does_nothing(session):
    """P2-T17f, desktop checklist 11.6: a group heading is selected with no item. Space there
    said the item last focused again, as F3 keeps that item to go back to. Now it says and
    plays nothing (P2-T18a, the PO, 10 November 2026)."""
    hear_station(session)
    session.run("panel.select", item=None, group=None)   # Up to the group's heading
    r = session.press("Space", "panel")
    assert r.voice is None and not r.sounds and not r.announcements
    session.run("panel.select", item=station_id(session), group="nearby")
    assert session.press("Space", "panel").voice is not None


def test_on_a_within_item_it_comes_from_the_centre_of_the_area(session):
    """The PO's answer, 8 November 2026 (checklist 9.5): you are inside the area, so its sound
    and its label come from the centre of the area, with the distance to it."""
    from mapcore.describe import words
    from mapcore.session import box_centre

    area = session.areas[0]
    session.run("panel.select", item=area.id, group="within")
    r = session.press("Space", "panel")
    lat, lon = box_centre(area.record["bbox"])
    distance, _, _ = geodesy.inverse(session.world.lat, session.world.lon, lat, lon)
    assert r.voice["text"] == f"{area.name}, {words.distance_text(distance, 'metric')}" and r.sounds


def test_the_centre_of_a_box_across_the_180_degree_line():
    from mapcore.session import box_centre

    assert box_centre((170.0, -20.0, -170.0, -10.0)) == pytest.approx((-15.0, 180.0))
    assert box_centre((-10.0, 40.0, 10.0, 60.0)) == pytest.approx((50.0, 0.0))


def test_it_works_on_crossed_and_passed(session):
    lat, lon = STATION
    session.world.lat, session.world.lon = lat + 0.003, lon - 0.02
    session.world.step_index = session.world.step_list.index(5000)
    session.run("move.east")
    session.crossed_now()
    crossed = next(g for g in session.panel() if g["id"] == "crossed")["items"]
    item = next(i for i in crossed if i["label"].startswith("Southampton Central"))
    session.run("panel.select", item=item["id"], group="crossed")
    r = session.press("Space", "panel")
    assert r.voice["text"].startswith("Southampton Central, ")
    assert 180 < r.voice["placed"]["relative_deg"] < 360   # behind, to the west, after the step east


def test_joined_commands_keep_the_sound_and_the_label(session):
    """The web version sends its commands through run_many (ANN-3)."""
    session.run("panel.select", item=station_id(session))
    r = session.run_many([("panel.hear", {})])
    assert [s["sound"] for s in r.sounds] == ["item_direction"] and r.voice is not None


def crossed_the_itchen(test_pack):
    """Four steps of 1 km east from west of the station: the last crosses the River Itchen, which
    is then in Crossed and passed, where it was crossed, and first in Nearby, nearer still."""
    s = MapSession(packs=[test_pack], saved_state={"lat": STATION[0], "lon": STATION[1] - 0.03,
                                                    "zoom_m": 10000, "step_m": 1000})
    s.start()
    for _ in range(5):
        s.run("move.east")
        s.crossed_now()
    return s


def distance_words(label):
    """The distance in an item's words, such as "320 metres" in "River Itchen, 320 metres north-west"
    or "730 metres" in "River Itchen, crossed, 730 metres west"."""
    return next(" ".join(part.split(" ")[:2]) for part in label.split(", ")[1:] if part[0].isdigit())


def test_an_area_in_nearby_and_in_crossed_and_passed_is_heard_from_each_ones_own_place(test_pack):
    """Phase 2 web checklist: the first Nearby item said another distance. The area just crossed
    is first in Nearby, and its Nearby item said where it was crossed, not its nearest point."""
    s = crossed_the_itchen(test_pack)
    groups = {g["id"]: g["items"] for g in s.panel()}
    near = groups["nearby"][0]
    crossed = next(i for i in groups["crossed"] if i["id"] == near["id"])
    assert near["label"].startswith("River Itchen, ") and distance_words(near["label"]) != distance_words(crossed["label"])
    for group, item in (("nearby", near), ("crossed", crossed)):
        s.run("panel.select", item=item["id"], group=group)
        said = s.press("Space", "panel").voice["text"]
        assert said == f"River Itchen, {distance_words(item['label'])}", (group, item["label"], said)
    s.store.close()


def test_every_nearby_item_says_its_own_distance(test_pack):
    s = crossed_the_itchen(test_pack)
    for item in nearby(s):
        s.run("panel.select", item=item["id"], group="nearby")
        said = s.press("Space", "panel").voice["text"]
        assert item["label"].startswith(said + " ") or item["label"] == said, (item["label"], said)
    s.store.close()


def test_f3_goes_back_to_the_group_of_the_item_last_focused(test_pack):
    s = crossed_the_itchen(test_pack)
    itchen = nearby(s)[0]["id"]
    s.run("panel.select", item=itchen, group="crossed")
    s.run("focus.map")
    assert s.run("focus.panel").focus == {"region": "panel", "group": "crossed", "item": itchen}
    s.run("panel.select", item=itchen, group="nearby")
    assert s.run("focus.panel").focus == {"region": "panel", "group": "nearby", "item": itchen}
    s.store.close()
