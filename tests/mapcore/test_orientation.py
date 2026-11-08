"""The three orientations, turning, crossing the poles and relative directions
(P2-T1a and P2-T1b; NAV-3, NAV-11, NAV-12, ANN-5, SON-2)."""
import pytest

from mapcore.describe import describer, words
from mapcore.geo import formats, geodesy
from mapcore.session import MapSession
from mapcore.world import WorldState
from mapcore.world.state import nearest_cardinal

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


def world(lat, lon, orientation="north-fixed", heading=0.0, step_m=50_000):
    w = WorldState(lat=lat, lon=lon, heading=heading, orientation=orientation)
    w.step_list = (step_m,)
    w.step_index = 0
    return w


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


# P2-T1a: stepping ------------------------------------------------------------------

def test_nav3_free_facing_over_the_north_pole():
    w = world(80.0, 0.0, "free", 0.0, 2_000_000)
    r = w.step("north")
    assert r.moved and r.pole == "north"
    assert r.lat == pytest.approx(82.0, abs=0.1) and abs(r.lon) == pytest.approx(180.0, abs=0.01)
    assert r.heading == pytest.approx(180.0, abs=0.01)


@pytest.mark.parametrize("lat, heading, pole", [(89.9, 0.0, "north"), (-89.9, 180.0, "south")])
def test_cardinal_facing_crosses_a_pole_onto_the_far_meridian_facing_back(lat, heading, pole):
    w = world(lat, 10.0, "cardinal", heading)
    r = w.step("north")   # Up: forward
    assert r.moved and r.pole == pole
    assert r.lon == pytest.approx(-170.0) and r.heading == (180.0 if pole == "north" else 0.0)
    assert abs(r.lat) == pytest.approx(90.0 - (50_000 - 11_170) / 111_700, abs=0.01)   # 11.17 km to the pole


def test_a_cardinal_step_that_does_not_reach_the_pole_follows_the_meridian():
    w = world(50.0, 10.0, "cardinal", 0.0)
    r = w.step("north")
    assert r.lon == 10.0 and r.lat == pytest.approx(50.449, abs=0.001) and r.heading == 0.0 and r.pole is None


def test_cardinal_facing_east_follows_the_line_of_latitude_as_north_fixed_does():
    facing = world(50.0, 10.0, "cardinal", 90.0)
    fixed = world(50.0, 10.0)
    a, b = facing.step("north"), fixed.step("east")
    assert (a.lat, a.lon) == (b.lat, b.lon) and a.lat == 50.0 and a.heading == 90.0
    back = facing.step("south")   # Down: back west, still facing east
    assert back.lon == pytest.approx(10.0) and back.heading == 90.0


def test_north_fixed_still_blocks_at_the_pole():
    r = world(89.9, 10.0).step("north")
    assert not r.moved and not r.turned


def test_free_facing_back_keeps_facing_the_same_way():
    w = world(50.0, 0.0, "free", 47.0, 500_000)
    there = w.step("north")
    back = w.step("south")
    assert back.lat == pytest.approx(50.0, abs=1e-6) and back.lon == pytest.approx(0.0, abs=1e-6)
    assert back.heading == pytest.approx(47.0, abs=1e-6) and there.heading != 47.0


def test_every_move_gives_its_path_including_over_a_pole():
    r = world(89.0, 10.0, "free", 0.0, 300_000).step("north")
    assert len(r.path) > 20 and geodesy.pole_crossed(r.path) == "north"
    assert all(geodesy.inverse(*a, *b)[0] <= geodesy.PATH_SPACING_M * 1.01 for a, b in zip(r.path, r.path[1:]))


def test_turning():
    cardinal = world(50.0, 0.0, "cardinal", 0.0)
    assert cardinal.step("east").turned and cardinal.heading == 90.0
    assert cardinal.step("west").heading == 0.0 and cardinal.step("west").heading == 270.0
    free = world(50.0, 0.0, "free", 358.0)
    assert free.step("east", turn_deg=5).heading == 3.0
    assert free.turn(-90).heading == 273.0
    fixed = world(50.0, 0.0)
    r = fixed.turn(90)
    assert not r.moved and not r.turned and fixed.heading == 0.0


def test_switching_orientation_never_moves_you():
    w = world(50.0, 0.0, "free", 47.0)
    assert w.next_orientation() == "north-fixed" and w.heading == 0.0 and (w.lat, w.lon) == (50.0, 0.0)
    w = world(50.0, 0.0, "free", 47.0)
    w.set_orientation("cardinal")
    assert w.heading == 90.0 and (w.lat, w.lon) == (50.0, 0.0)
    assert w.next_orientation() == "free" and w.heading == 90.0
    assert [nearest_cardinal(h) for h in (0, 44.9, 45, 134, 226, 316, 359)] == [0, 0, 90, 90, 270, 0, 0]


def test_typing_a_bearing_switches_to_free_facing():
    w = world(50.0, 0.0, "cardinal", 90.0)
    w.face(-13)
    assert w.orientation == "free" and w.heading == 347.0


def test_the_orientation_and_heading_are_saved():
    w = world(50.0, 0.0, "free", 47.5)
    again = WorldState()
    again.restore(w.to_dict())
    assert again.orientation == "free" and again.heading == 47.5
    w = world(50.0, 0.0, "cardinal", 47.5)   # a damaged save: cardinal keeps to the four points
    again.restore(w.to_dict())
    assert again.heading == 90.0


# P2-T1b: directions relative to the way you face -----------------------------------

def test_nav12_a_feature_at_90_degrees_is_east_or_ahead():
    assert words.direction_text(90.0, "points8") == "east"
    assert words.direction_text(90.0, "points8", heading=90.0) == "ahead"
    assert words.direction_text(90.0, "clock", heading=90.0) == "12 o'clock"
    assert words.direction_text(90.0, "clock") == "3 o'clock"


@pytest.mark.parametrize("bearing, style, text", [
    (137.0, "points4", "to your right"),
    (137.0, "points8", "ahead right"),
    (137.0, "points16", "ahead right"),
    (137.0, "points32", "ahead right"),
    (110.0, "points16", "ahead, slightly right"),
    (270.0, "points8", "behind"),
    (0.0, "points8", "to your left"),
    (47.0, "points8", "ahead left"),
    (137.0, "exact", "47 degrees to your right"),
    (43.0, "exact", "47 degrees to your left"),
    (90.0, "exact", "ahead"),
    (271.0, "round10", "behind"),
    (139.0, "round10", "about 50 degrees to your right"),
    (137.0, "clock", "2 o'clock"),
])
def test_relative_directions_in_each_format(bearing, style, text):
    assert words.direction_text(bearing, style, heading=90.0) == text


def test_the_one_rule_gives_a_relative_bearing():
    assert formats.relative_bearing(90.0, 90.0) == 0.0
    assert formats.relative_bearing(10.0, 350.0) == 20.0
    assert describer.facing(world(0, 0)) is None
    assert describer.facing(world(0, 0, "free", 47.0)) == 47.0


# The session ------------------------------------------------------------------------

@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


def test_nearby_is_relative_in_a_facing_orientation(session):
    def labels():
        return [i["label"] for g in session.panel() if g["id"] == "nearby" for i in g["items"]]
    fixed = labels()
    session.world.set_orientation("cardinal")
    session.world.turn(90)
    facing = labels()
    assert fixed != facing
    assert any("south" in label for label in fixed)
    assert not any(" south" in label or "north" in label for label in facing)


def test_turning_says_the_heading_and_moves_nothing(session):
    session.world.set_orientation("free")
    before = (session.world.lat, session.world.lon)
    r = session.press("Right")
    assert spoken(r) == ["Facing 5 degrees."] and r.redraw and r.earcons == []
    assert (session.world.lat, session.world.lon) == before
    session.release()
    session.world.set_orientation("cardinal")
    assert spoken(session.press("Left")) == ["Facing west."]   # 5 degrees became north, then a quarter turn left


def test_holding_a_turn_ticks_and_says_the_heading_on_release(session):
    session.world.set_orientation("free")
    session.run("move.east")
    for _ in range(3):
        r = session.run("move.east", held=True, repeat=True)
        assert spoken(r) == [] and r.earcons == ["tick"]
    assert spoken(session.release()) == ["Facing 20 degrees."]


def test_releasing_a_held_turn_with_the_heading_switched_off_plays_no_tick_of_its_own(session):
    session.world.set_orientation("free")
    session.run("settings.set", field="say_heading", value=False)
    session.run("move.east")
    assert session.run("move.east", held=True, repeat=True).earcons == ["tick"]
    done = session.release()
    assert "tick" not in done.earcons and spoken(done) == []


def test_the_fine_turn_and_the_large_turn(session):
    assert session._turn(sign=1).earcons == []                   # north-fixed: nothing at all
    session.world.set_orientation("cardinal")
    assert session._turn("fine_turn_deg", 1).earcons == []       # cardinal facing: nothing either
    assert not session._turn(sign=1).announcements and session.world.heading == 0.0
    session.world.set_orientation("free")
    assert spoken(session._turn(sign=1)) == ["Facing 90 degrees."]
    assert spoken(session._turn("fine_turn_deg", -1)) == ["Facing 89 degrees."]


def test_crossing_a_pole_says_so(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 89.9, "lon": 10.0, "zoom_m": 25000, "step_m": 50000,
                                                    "orientation": "cardinal", "heading": 0.0})
    s.start()
    said = spoken(s.press("Up"))
    assert said[0] == "Crossed the North Pole. Now facing south."
    assert s.world.heading == 180.0 and s.world.lon == pytest.approx(-170.0)
    s.store.close()


def test_h_says_the_orientation(session):
    session.world.set_orientation("free")
    session.world.turn(47)
    assert spoken(session.press("H")) == ["Facing 47 degrees. Free facing. Stepping. Zoom 25 kilometres, step 25 kilometres."]
