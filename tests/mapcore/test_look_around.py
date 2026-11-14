"""Look around (P3-T11a; SON-4, SON-3, SON-2, NAV-13, INF-10).

L plays the Nearby group as sound: at most 12 items, in bearing order clockwise from ahead, each
with its layer's sound from its direction, then its name and distance in the spatial voice from the
same place. The core gives the order and how each is heard; the shell plays them one after another
and tells the core, with scan_item, which one is playing, so Enter on the map goes there. Any other
key stops the scan.
"""
import pytest

from mapcore.session import SCAN_LIMIT, MapSession, box_centre

STATION = (50.9074977, -1.4142289)


def make(test_pack, lat=STATION[0], lon=STATION[1] - 0.03, zoom_m=10000, **settings):
    s = MapSession(packs=[test_pack], settings={"values": settings} if settings else None,
                   saved_state={"lat": lat, "lon": lon, "zoom_m": zoom_m, "step_m": 1000})
    s.start()
    return s


@pytest.fixture
def session(test_pack):
    s = make(test_pack, zoom_m=50000, nearby_count=20)   # 15 items in Nearby here
    yield s
    s.store.close()


def nearby(s):
    return next(g for g in s.panel() if g["id"] == "nearby")["items"]


def look(s):
    return s.press("L", "map")


@pytest.fixture
def close(test_pack):
    """Zoomed in to 5 km, where Southampton Central is in Nearby."""
    s = make(test_pack, zoom_m=5000)
    yield s
    s.store.close()


def test_l_on_the_map_is_look_around_and_enter_in_the_panel_still_goes_to_the_item(session):
    assert look(session).scan is not None
    from mapcore.commands import registry

    assert registry.command_for_key("desktop", "Enter", "panel", {}).name == "panel.go"
    assert registry.command_for_key("web", "Enter", "map", {}).name == "look.go"


def test_the_items_played_are_nearbys_first_12_clockwise_from_ahead(session):
    near = nearby(session)
    assert len(near) > SCAN_LIMIT, "the test needs more nearby items than look around plays"
    r = look(session)
    expected = sorted(near, key=lambda i: (i["bearing_deg"], i["id"]))[:SCAN_LIMIT]
    assert [i["id"] for i in r.scan["items"]] == [i["id"] for i in expected]
    degrees = [i["sound"]["relative_deg"] for i in r.scan["items"]]
    assert degrees == sorted(degrees)
    assert r.scan["gap_s"] > 0


def test_with_the_default_count_every_nearby_item_is_played(test_pack):
    s = make(test_pack)
    assert {i["id"] for i in look(s).scan["items"]} == {i["id"] for i in nearby(s)}
    s.store.close()


def test_clockwise_from_the_way_you_face(session):
    session.world.set_orientation("free")
    session.world.face(90.0)
    items = look(session).scan["items"]
    degrees = [i["sound"]["relative_deg"] for i in items]
    assert degrees == sorted(degrees)
    north = sorted(nearby(session), key=lambda i: i["bearing_deg"])
    assert [i["id"] for i in items] == [i["id"] for i in north[:SCAN_LIMIT]]   # the panel's bearings are from ahead too


def test_each_item_sounds_as_hear_its_direction_does(session):
    for item in look(session).scan["items"][:4]:
        session.run("panel.select", item=item["id"], group="nearby")
        heard = session.press("Space", "panel")
        assert item["sound"] == heard.sounds[0]
        assert item["voice"] == heard.voice
        assert item["voice"]["after"], "the label waits for the item's sound"
        assert item["voice"]["placed"]["relative_deg"] == item["sound"]["relative_deg"]


def test_only_visible_features_are_played(test_pack):
    """NAV-13: zoomed out beyond the stations' zoom range, they are left out of Nearby, and so of the scan."""
    s = make(test_pack, zoom_m=5000, nearby_count=20)
    items = look(s).scan["items"]
    station = next(i for i in items if i["voice"]["text"].startswith("Southampton Central"))
    s.run("layers.set", layer=s.store.feature(station["id"]).layer, field="max_zoom_m", value=20000)
    while s.world.zoom_m < 50000:
        s.run("zoom.out")
    far = look(s).scan["items"]
    assert {i["id"] for i in far} <= {i["id"] for i in nearby(s)}
    assert not any(i["voice"]["text"].startswith("Southampton Central") for i in far)
    s.store.close()


def test_l_stops_the_older_voice_and_scan_and_any_key_stops_it(session):
    r = look(session)
    assert r.stop_voice and r.voice is None, "the shell stops what is playing before the scan starts"
    session.scan_item(0)
    after = session.press("Down", "map")
    assert after.stop_voice and after.scan is None
    r = session.press("Enter", "map")
    assert r.scan is None and "Nothing to go to" in r.announcements[0]["text"], "the scan ended with the key"


def test_scan_item_neither_stops_the_voice_nor_ends_the_scan(session):
    look(session)
    r = session.scan_item(1)
    assert not r.stop_voice and r.scan is None
    assert session._scan_at == 1


def test_enter_during_an_item_goes_to_it(session):
    items = look(session).scan["items"]
    target = items[2]
    session.scan_item(0)
    session.scan_item(2)
    area, lat, lon = next(s for k, s in session._spots.items() if k == ("nearby", target["id"]))
    r = session.press("Enter", "map")
    if session._geometry(area) == "area" and area.record.get("bbox"):
        lat, lon = box_centre(area.record["bbox"])
    assert (session.world.lat, session.world.lon) == pytest.approx((lat, lon))
    assert r.announcements and r.stop_voice and r.focus is None, "the place is said; the focus stays on the map"
    assert session.back_places, "a jump, so Alt+comma comes back"


def test_enter_after_the_scan_has_ended_goes_nowhere(session):
    look(session)
    session.scan_item(3)
    session.scan_item(None)
    place = (session.world.lat, session.world.lon)
    r = session.press("Enter", "map")
    assert (session.world.lat, session.world.lon) == place
    assert "blocked" in r.earcons and r.announcements[0]["text"] == (
        "Nothing to go to. Press Enter while look around plays an item to go to it.")


def test_each_item_playing_goes_to_braille_and_can_be_repeated(session):
    items = look(session).scan["items"]
    r = session.scan_item(1)
    label = items[1]["voice"]["text"]
    assert r.announcements == [{"text": label, "channel": "braille", "priority": "polite", "fallback": None}]
    assert session.press("Shift+Space", "map").announcements[0]["text"] == label


def test_also_speak_sends_each_label_to_the_screen_reader(test_pack):
    s = make(test_pack, voice_also_speak=True)
    items = look(s).scan["items"]
    assert s.scan_item(0).announcements == [{"text": items[0]["voice"]["text"], "channel": "speech",
                                             "priority": "polite"}]
    s.store.close()


def test_muted_it_says_so_and_plays_nothing(session):
    session.run("sound.mute", on=True)
    r = look(session)
    assert r.scan is None and r.announcements[0]["text"] == "Sound is muted, so look around has nothing to play."


def test_nothing_nearby_says_so(test_pack):
    s = make(test_pack, lat=50.9, lon=-1.4, zoom_m=500)   # nothing within 500 metres here in the test pack
    assert not nearby(s)
    r = look(s)
    assert r.scan is None and r.announcements[0]["text"] == "Nothing nearby."
    s.store.close()


def test_a_switched_off_layer_sound_leaves_the_voice(close):
    close.run("settings.set", field="earcon_on_item_direction", value=False)
    items = look(close).scan["items"]
    station = next(i for i in items if i["voice"]["text"].startswith("Southampton Central"))
    assert station["sound"] is None and station["voice"] is not None


def test_joined_commands_a_later_key_stops_an_earlier_scan(session):
    assert session.run_many([("look.around", {})]).scan is not None
    assert session.run_many([("look.around", {}), ("move.north", {})]).scan is None
    assert session.run_many([("move.north", {}), ("look.around", {})]).scan is not None
