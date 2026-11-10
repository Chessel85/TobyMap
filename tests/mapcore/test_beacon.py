"""The orientation beacon (P2-T9; SON-10, SON-2): B switches it on and off, it comes from the
North Pole relative to the way you face, with the lower pitch behind, it fades and goes silent
within 100 km of the pole, said once, and it comes back further away."""
import pytest

from mapcore import settings as settings_mod
from mapcore.commands import registry
from mapcore.describe import earcon_list
from mapcore.session import MapSession


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.9, "lon": -1.45, "zoom_m": 5000, "step_m": 1000})
    s.start()
    yield s
    s.store.close()


def spoken(r):
    return [a["text"] for a in r.announcements]


def face(s, orientation, heading):
    s.world.orientation = orientation
    s.world.heading = heading


def test_b_switches_the_beacon_on_and_off_and_says_which(session):
    command = registry.by_name("beacon.toggle")
    assert command.key == "B" and command.region == "map" and command.toggle
    r = session.press("B")
    assert spoken(r) == ["Beacon on."] and session.settings["beacon_on"]
    assert r.settings_changed and r.beacon["on"] and r.beacon["placed"] is not None
    r = session.press("B")
    assert spoken(r) == ["Beacon off."] and not session.settings["beacon_on"]
    assert r.beacon == {"on": False, "placed": None, "interval_s": 1.0}


def test_off_at_first(session):
    assert not session.settings["beacon_on"]
    assert session.run("where.am_i").beacon["placed"] is None


def test_north_fixed_straight_ahead(session):
    session.run("beacon.toggle")
    p = session.beacon()["placed"]
    assert p["sound"] == "beacon" and p["relative_deg"] == 0 and p["pan"] == 0
    assert p["pitch"] == 1.0 and not p["behind"] and not p["beyond"]


def test_facing_east_it_is_to_the_left_and_facing_south_behind(session):
    session.run("beacon.toggle")
    face(session, "cardinal", 90.0)
    p = session.beacon()["placed"]
    assert p["relative_deg"] == 270 and p["pan"] == -1   # full left
    face(session, "cardinal", 180.0)
    p = session.beacon()["placed"]
    assert p["relative_deg"] == 180 and p["behind"] and p["pitch"] < 1.0   # the lower pitch behind (DP137)
    face(session, "free", 45.0)
    p = session.beacon()["placed"]
    assert p["relative_deg"] == 315 and p["pan"] < 0


def test_every_response_carries_where_the_beacon_is_now(session):
    session.run("beacon.toggle")
    session.run("orientation.cycle")             # cardinal facing, north
    r = session.run("move.east")                  # now facing east
    assert r.beacon["placed"]["relative_deg"] == 270


def test_its_loudness_is_its_own_volume_not_the_distance_or_an_earcons_volume(session):
    session.run("beacon.toggle")
    session.run("settings.set", field="earcon_volume_tick", value=30)
    assert session.beacon()["placed"]["gain"] == pytest.approx(1.0)
    session.run("settings.set", field="beacon_volume", value=40)
    p = session.beacon()["placed"]
    assert p["gain"] == pytest.approx(0.4) and p["file"]["gain"] == pytest.approx(0.4)
    assert p["file"]["default"] == "beacon.wav"


def test_the_repeat_is_a_setting(session):
    session.run("beacon.toggle")
    session.run("settings.set", field="beacon_interval_s", value=2.5)
    assert session.beacon()["interval_s"] == 2.5


def test_the_target_is_the_north_pole_for_now():
    field = settings_mod.fields()["beacon_target"]
    assert field["default"] == "north_pole" and [c[0] for c in field["choices"]] == ["north_pole"]


def test_mute_silences_it_and_it_comes_back_after(session):
    session.run("beacon.toggle")
    r = session.run("sound.mute")
    assert r.beacon["on"] and r.beacon["placed"] is None
    r = session.run("sound.mute")
    assert r.beacon["placed"] is not None


def test_it_fades_near_the_pole(session):
    session.run("beacon.toggle")
    session.world.lat, session.world.lon = 88.0, 0.0       # about 223 km from the pole: full
    assert session.beacon()["placed"]["gain"] == pytest.approx(1.0)
    session.world.lat = 90.0 - 150 / 111.7                 # about 150 km: fading
    gain = session.beacon()["placed"]["gain"]
    assert 0.2 < gain < 0.8


def test_50_km_from_the_pole_it_is_silent_and_told_once(session):
    session.run("beacon.toggle")
    r = session.run("goto.set", text="89.55, 0")         # about 50 km from the North Pole
    told = [a["text"] for a in r.announcements]
    r = session.run("where.am_i")
    assert r.beacon["on"] and r.beacon["placed"] is None
    told += [a["text"] for a in r.announcements]
    told += [a["text"] for a in session.run("where.am_i").announcements]
    assert len([t for t in told if "Beacon off near the North Pole." in t]) == 1


def test_it_comes_back_further_away_and_says_so(session):
    session.run("beacon.toggle")
    session.run("goto.set", text="89.55, 0")
    r = session.run("goto.set", text="80, 0")
    assert r.beacon["placed"] is not None
    assert "Beacon back on." in spoken(r)
    r = session.run("goto.set", text="89.55, 0")
    assert "Beacon off near the North Pole." in spoken(r)   # told again on coming back


def test_switched_on_near_the_pole_it_says_why_it_is_silent(session):
    session.run("goto.set", text="89.55, 0")
    r = session.run("beacon.toggle")
    assert spoken(r) == ["Beacon on, but silent near the North Pole."]
    assert r.beacon["placed"] is None
    assert "Beacon off near the North Pole." not in " ".join(spoken(session.run("where.am_i")))


def test_switched_off_nothing_is_said_near_the_pole(session):
    r = session.run("goto.set", text="89.55, 0")
    assert not any("Beacon" in t for t in spoken(r))


def test_the_south_pole_is_not_silent(session):
    session.run("beacon.toggle")
    r = session.run("goto.set", text="-89.9, 0")
    assert r.beacon["placed"] is not None and not any("Beacon" in t for t in spoken(r))


def test_the_beacon_is_in_the_sounds_with_its_own_file_but_no_second_switch():
    beacon = next(e for e in earcon_list() if e["event"] == "beacon")
    assert beacon["file"] == "beacon.wav"
    fields = settings_mod.fields()
    assert "earcon_beacon" in fields and "earcon_on_beacon" not in fields   # B is its switch
    assert "earcon_volume_beacon" not in fields                            # beacon_volume is its volume


def test_the_beacons_switch_volume_and_own_file_are_in_the_sound_tab_not_the_earcons_list():
    """P2-T17p, DP163: the orientation beacon's settings are together, in the Sound tab."""
    tabs = {t["id"]: t for t in settings_mod.schema()["tabs"]}
    ids = [f["id"] for f in tabs["sound"]["fields"]]
    assert {"beacon_on", "beacon_volume", "beacon_interval_s", "earcon_beacon", "beacon_target"} <= set(ids)
    assert "beacon" not in [r["event"] for r in tabs["earcons"]["earcons"]]
    assert not any(f["id"].startswith("beacon") or f["id"] == "earcon_beacon" for f in tabs["earcons"]["fields"])


def test_joined_commands_keep_the_last_beacon(session):
    session.run("beacon.toggle")
    session.run("orientation.cycle")
    r = session.run_many([("move.east", {}), ("move.east", {})])   # facing south
    assert r.beacon["placed"]["behind"]
