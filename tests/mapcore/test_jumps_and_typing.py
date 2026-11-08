"""Typed bearings and coordinates, the position history and Enter in the announcement history
(P2-T1c, P2-T2, P2-T15; NAV-8, NAV-10, NAV-12, ANN-4, DP141, DP142)."""
import pytest

from mapcore.geo.parse import parse_bearing, parse_coordinates
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}
NIAGARA = (43.0962, -79.0377)


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


def near(s, lat, lon):
    return s.world.lat == pytest.approx(lat, abs=1e-5) and s.world.lon == pytest.approx(lon, abs=1e-5)


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


# Reading what is typed ---------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "51.5, -0.12", "51.5 -0.12", "51.5,-0.12", "51.5N 0.12W", "51.5 N, 0.12 W", "N51.5 W0.12", "n 51.5 w 0.12",
    "51.5°N 0.12°W", "51°30′N 0°07.2′W", "51°30'0\"N 0°7'12\"W", "51°30′00″N 0°07′12″W", "51°30'00''N 0°07'12''W",
    "51.5 N 0.12 W", "51.5; -0.12", "+51.5, -0.12",
])
def test_every_format_gives_the_same_place(text):
    lat, lon = parse_coordinates(text)
    assert lat == pytest.approx(51.5, abs=1e-5) and lon == pytest.approx(-0.12, abs=1e-5)


def test_south_and_west_are_negative_and_seconds_may_have_decimals():
    assert parse_coordinates("33.9S 18.4E") == pytest.approx((-33.9, 18.4))
    lat, lon = parse_coordinates("33°54′30.5″S 18°25′E")
    assert lat == pytest.approx(-(33 + 54 / 60 + 30.5 / 3600)) and lon == pytest.approx(18 + 25 / 60)


@pytest.mark.parametrize("text", [
    "91, 0", "0, 181", "-91, 0", "51.5 W 0.12 N", "0.12W 51.5N", "-51.5S 0.12E", "51.5", "",
    "hello", "51°75′N 0°E", "51°30′N 0°60′W", "51.5°30′N 0°E", "51 30 N 0 7 W", "51.5, -0.12, 3",
])
def test_out_of_range_or_ambiguous_coordinates_are_refused(text):
    with pytest.raises(ValueError):
        parse_coordinates(text)


@pytest.mark.parametrize("text, degrees", [
    ("47", 47.0), ("47.5", 47.5), ("47°", 47.0), ("47 degrees", 47.0), ("0", 0.0), ("360", 0.0), ("NE", 45.0),
    ("ne", 45.0), ("north-east", 45.0), ("north east", 45.0), ("northeast", 45.0), ("S", 180.0),
    ("WNW", 292.5), ("west", 270.0),
])
def test_a_bearing_is_degrees_or_a_compass_point(text, degrees):
    assert parse_bearing(text) == degrees


@pytest.mark.parametrize("text", ["361", "-5", "", "east by north", "up", "47 47"])
def test_a_bad_bearing_is_refused(text):
    with pytest.raises(ValueError):
        parse_bearing(text)


# The orientation key and the bearing box ---------------------------------------------

def test_the_orientation_key_cycles_and_says_where_you_face(session):
    assert spoken(session.press("O")) == ["Cardinal facing, north."]
    session.press("Shift+Right")
    assert spoken(session.press("O")) == ["Free facing, 90 degrees."]
    assert session.world.orientation == "free" and session.world.heading == 90.0
    assert spoken(session.press("O")) == ["North-fixed."]
    assert session.world.heading == 0.0 and near(session, 51.2, 1.2)


def test_the_bearing_box_asks_and_refuses_with_the_accepted_words(session):
    r = session.press("Ctrl+B")
    d = r.dialog
    assert d["kind"] == "input" and d["title"] == "Type a bearing" and d["submit"] == "bearing.set"
    assert d["ok"] == "OK" and d["cancel"] == "Cancel" and "compass point" in d["help"]
    bad = session.run("bearing.set", text="up")
    assert bad.error.startswith("That is not a bearing") and not bad.announcements
    assert session.world.orientation == "north-fixed"


def test_a_typed_bearing_switches_to_free_facing_and_says_so(session):
    r = session.run("bearing.set", text="NE")
    assert spoken(r) == ["Free facing, 45 degrees."] and session.world.orientation == "free"
    assert session.world.heading == 45.0 and r.redraw
    assert spoken(session.run("bearing.set", text="100")) == ["Facing 100 degrees."]


def test_the_turning_keys(session):
    session.press("O")   # cardinal
    assert spoken(session.press("Shift+Right")) == ["Facing east."]
    assert spoken(session.press("Shift+Left")) == ["Facing north."]
    assert session.press("Ctrl+Right").earcons == ["blocked"]   # the fine turn is for free facing only
    session.press("O")   # free
    assert spoken(session.press("Ctrl+Right")) == ["Facing 1 degrees."]
    assert spoken(session.press("Shift+Right")) == ["Facing 91 degrees."]
    assert spoken(session.press("Ctrl+Left")) == ["Facing 90 degrees."]


def test_turning_in_north_fixed_is_blocked_and_silent(session):
    for key in ("Shift+Left", "Shift+Right", "Ctrl+Left", "Ctrl+Right"):
        r = session.press(key)
        assert r.earcons == ["blocked"] and not r.announcements


def test_a_held_turn_counts_for_the_web_clicks(session):
    session.world.face(10.0)
    session.press("Left")
    info = session.hold_info()
    assert info["command"] == "move.west" and info["left"] > 0


# Going to coordinates and the position history ----------------------------------------

def test_the_go_to_box_asks_and_refuses_what_it_cannot_read(session):
    d = session.press("Ctrl+G").dialog
    assert d["kind"] == "input" and d["submit"] == "goto.set" and "51.5N 0.12W" in d["help"]
    bad = session.run("goto.set", text="91, 0")
    assert bad.error.startswith("Those are not coordinates") and near(session, 51.2, 1.2)


def test_a_jump_keeps_the_zoom_and_says_the_place(session):
    r = session.run("goto.set", text="52.1, -1.3")
    assert near(session, 52.1, -1.3) and session.world.zoom_m == 25000
    assert r.redraw and len(spoken(r)) == 1


def test_jump_step_three_times_back_returns_with_the_zoom(session):
    session.run("goto.set", text="52.1, -1.3")
    session.press("Page Up")   # zoom out, so the jump's place has a different zoom from the start
    for _ in range(3):
        session.press("Right")
    for _ in range(3):         # every step is a place: back through each of them (DP142)
        session.press("Alt+,")
    assert near(session, 52.1, -1.3)
    back = session.press("Alt+,")
    assert near(session, 51.2, 1.2) and session.world.zoom_m == 25000
    assert spoken(back) == ["Kent, England, United Kingdom"]


def test_every_step_adds_a_place_and_back_and_forward_add_none(session):
    places = []
    for key in ("Right", "Right", "Down"):
        places.append((session.world.lat, session.world.lon))
        session.press(key)
    end = (session.world.lat, session.world.lon)
    assert len(session.back_places) == 3
    for lat, lon in reversed(places):
        session.press("Alt+,")
        assert near(session, lat, lon)
    assert session.press("Alt+,").earcons == ["blocked"]
    for _ in range(3):
        session.press("Alt+.")
    assert near(session, *end)
    assert len(session.back_places) == 3 and not session.forward_places


def test_a_step_after_going_back_clears_the_way_forward(session):
    session.press("Right")
    session.press("Right")
    session.press("Alt+,")
    session.press("Up")
    assert not session.forward_places and session.press("Alt+.").earcons == ["blocked"]


def test_a_held_key_adds_one_place_where_the_hold_started(session):
    session.press("Right")                         # the press: one step, then the hold
    session.run("move.east", held=True, repeat=True)
    session.run("move.east", held=True, repeat=True)
    session.release()
    assert len(session.back_places) == 1
    session.press("Alt+,")
    assert near(session, 51.2, 1.2)                # back to before the whole held run


def test_a_blocked_step_or_a_turn_adds_no_place(session):
    session.press("O")             # cardinal facing: Left and Right turn
    session.press("Right")
    session.press("O")
    session.press("O")             # north-fixed again
    assert not session.back_places
    session.run("goto.set", text="90, 0")
    session.back_places.clear()
    session.press("Up")            # at the North Pole in north-fixed, north is blocked
    assert not session.back_places


def test_back_then_forward_and_a_new_jump_clears_forward(session):
    session.run("goto.set", text="52.1, -1.3")
    session.press("Alt+,")
    session.press("Alt+.")
    assert near(session, 52.1, -1.3)
    session.press("Alt+,")
    session.run("goto.set", text="50, 0")
    r = session.press("Alt+.")
    assert r.earcons == ["blocked"] and not r.announcements


def test_nothing_to_go_back_to_plays_the_blocked_sound(session):
    r = session.press("Alt+,")
    assert r.earcons == ["blocked"] and not r.announcements
    assert session.press("Alt+.").earcons == ["blocked"]


def test_the_last_1000_places_are_kept(session):
    for i in range(1001):
        session.run("goto.set", text=f"{i % 80}, {i % 170}")
    assert len(session.back_places) == 1000
    assert session.back_places[0]["lat"] != 51.2   # the first place, the start, has gone
    again = MapSession(packs=[session.store.packs[0]], saved_state=session.save()["state"])
    assert len(again.back_places) == 1000          # all of them are saved and come back


def test_the_history_is_saved_with_the_state(test_pack, session):
    session.run("goto.set", text="10, 10")
    saved = session.save()["state"]
    again = MapSession(packs=[test_pack], saved_state=saved)
    again.press("Alt+,")
    assert near(again, 51.2, 1.2)
    again.store.close()


def test_the_places_can_be_cleared_on_start(test_pack, session):
    session.run("goto.set", text="10, 10")
    session.press("Alt+,")
    saved = session.save()
    assert saved["state"]["jumps"]["forward"]
    settings = dict(saved["settings"], values=dict(saved["settings"]["values"], places_clear_on_start=True))
    again = MapSession(packs=[test_pack], settings=settings, saved_state=saved["state"])
    assert not again.back_places and not again.forward_places
    assert again.press("Alt+,").earcons == ["blocked"]
    again.store.close()


def test_clearing_the_places_on_start_is_off_at_first(test_pack, session):
    assert session.settings["places_clear_on_start"] is False
    field = next(f for tab in session.settings_schema()["tabs"] for f in tab["fields"]
                 if f["id"] == "places_clear_on_start")
    assert field["label"] == "Clear the places on start" and field["kind"] == "yes_no"


def test_a_click_counts_as_a_jump(session):
    session.run("map.click", x=300, y=200, width=800, height=600)
    assert session.back_places and session.back_places[-1]["lat"] == 51.2
    session.press("Alt+,")
    assert near(session, 51.2, 1.2)


# Enter in the announcement history ----------------------------------------------------

def test_enter_on_a_history_entry_goes_back_to_its_place_and_zoom(session):
    session.press("Page Up")                        # said at Kent, at the wider zoom
    zoom = session.world.zoom_m
    session.run("goto.set", text="52.1, -1.3")
    session.press("Page Up")                        # said at the new place, wider still
    r = session.press("Ctrl+Shift+Space")
    assert r.dialog["go"] == "history.go" and "Enter" in r.dialog["help"]
    assert len(r.dialog["lines"]) == 4              # newest first: the zoom, the jump, the first zoom, the start
    go = session.run("history.go", index=2)
    assert (session.world.lat, session.world.lon, session.world.zoom_m) == (51.2, 1.2, zoom)
    assert go.redraw and not go.error
    session.press("Alt+,")                          # it was a jump, so back comes to where we were
    assert near(session, 52.1, -1.3)


def test_an_entry_with_no_place_says_so_and_does_nothing(session):
    session.run("sound.mute")                       # speaks, but has no place
    before = (session.world.lat, session.world.lon)
    r = session.run("history.go", index=0)
    assert r.error == "No place for this entry." and not r.redraw and not r.announcements
    assert (session.world.lat, session.world.lon) == before and not session.back_places
    assert session.run("history.go", index=50).error == "No place for this entry."
