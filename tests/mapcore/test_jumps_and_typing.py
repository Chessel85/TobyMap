"""Typed bearings and coordinates, and the location history
(P2-T1c, P2-T2, P2-T15, P2-T17t; NAV-8, NAV-10, NAV-12, DP142, DP158)."""
import pytest

from mapcore.geo import geodesy
from mapcore.geo.parse import parse_bearing, parse_coordinates, parse_goto
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
    "51.5, -0.12", "51.5 -0.12", "51.5,-0.12", "51.5N 0.12W", "51.5 N, 0.12 W", "51.5n0.12w",
    "51d 30m N, 0d 7m 12s W", "51D 30M N 0D 7M 12S W", "51d30mN 0d7m12sW", "51.5d n, 0.12d w",
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
    "48 51 30 N, 2 21 E", "51 30 N", "N51.5 W0.12",
    "hello", "51°75′N 0°E", "51°30′N 0°60′W", "51.5°30′N 0°E", "51 30 N 0 7 W", "51.5, -0.12, 3",
])
def test_out_of_range_or_ambiguous_coordinates_are_refused(text):
    with pytest.raises(ValueError):
        parse_coordinates(text)


def same(a, b):
    return a[0] == b[0] and all((x is None and y is None) or (x is not None and y is not None and abs(x - y) < 1e-9)
                                for x, y in zip(a[1:], b[1:]))


@pytest.mark.parametrize("text, reading", [
    ("48D 30M 15S S", ("to", -(48 + 30 / 60 + 15 / 3600), None)),   # the last S is south
    ("48d 51m n, 2d 21m e", ("to", 48.85, 2.35)),
    ("51.5", ("to", 51.5, None)), ("-33", ("to", -33.0, None)), ("33S", ("to", -33.0, None)),
    (", -0.12", ("to", None, -0.12)), (",18", ("to", None, 18.0)), ("18E", ("to", None, 18.0)),
    ("north 5", ("by", 5.0, 0.0)), ("n 5", ("by", 5.0, 0.0)), ("W 10", ("by", 0.0, -10.0)),
    ("south 2 east 3", ("by", -2.0, 3.0)), ("s 2, e 3", ("by", -2.0, 3.0)), ("East 3 South 2", ("by", -2.0, 3.0)),
    ("west 0d 30m", ("by", 0.0, -0.5)), ("N51.5 W0.12", ("by", 51.5, -0.12)),
])
def test_go_to_reads_one_number_a_comma_and_a_number_and_a_direction_and_an_amount(text, reading):
    """The PO's answers, 8 November 2026. A direction first moves by that many degrees; a number
    first is where to go."""
    assert same(parse_goto(text), reading), parse_goto(text)


# P2-T17r, DP161: forward and back. A number alone is in the user's unit; units may be typed.
MILE, YARD = 1609.344, 0.9144


@pytest.mark.parametrize("text, unit_m, metres", [
    ("F24", 1000.0, 24_000), ("f 24", MILE, 24 * MILE), ("forward 2.5", 1000.0, 2_500), ("B24", 1000.0, -24_000),
    ("back 3", 1852.0, -3 * 1852.0), ("backward 1", 1000.0, -1000), ("forwards 1", 1000.0, 1000),
    ("F24mi240yds", 1000.0, 24 * MILE + 240 * YARD), ("B24km50m", MILE, -24_050), ("B24.05km", MILE, -24_050),
    ("f 24 mi 240 yds", 1000.0, 24 * MILE + 240 * YARD), ("f 2 miles and 100 yards", 1000.0, 2 * MILE + 100 * YARD),
    ("f 500 m", MILE, 500), ("f 3 kilometres", MILE, 3000), ("b 10 yd", 1000.0, -10 * YARD), ("f 0.5mi", 1000.0, MILE / 2),
])
def test_go_to_reads_forward_and_back_with_a_distance(text, unit_m, metres):
    kind, amount, other = parse_goto(text, unit_m)
    assert kind == "ahead" and other is None and amount == pytest.approx(metres)


@pytest.mark.parametrize("text", ["f", "b", "f km", "f 24 km 3", "f 2km 3km", "f -5", "f 5 feet", "fore 5", "f 5 north"])
def test_go_to_refuses_a_forward_or_back_it_cannot_read(text):
    with pytest.raises(ValueError):
        parse_goto(text)


@pytest.mark.parametrize("text", ["north 5 south 2", "n -5", "up 5", "north", "5 north 3", ", 0.12N", "91",
                                  "48 51 30 N, 2 21 E"])
def test_go_to_refuses_what_it_cannot_read(text):
    with pytest.raises(ValueError):
        parse_goto(text)


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
    session.press("Right")
    assert spoken(session.press("O")) == ["Free facing, 90 degrees."]
    assert session.world.orientation == "free" and session.world.heading == 90.0
    assert spoken(session.press("O")) == ["North-fixed."]
    assert session.world.heading == 0.0 and near(session, 51.2, 1.2)


def test_the_bearing_box_asks_and_refuses_with_the_accepted_words(session):
    r = session.press("Ctrl+B")
    d = r.dialog
    assert d["kind"] == "input" and d["title"] == "Type a bearing" and d["submit"] == "bearing.set"
    assert d["ok"] == "OK" and d["cancel"] == "Cancel"
    # The label alone, with no help line (P2-T17o, the PO's note on desktop checklist 3.5).
    assert d["label"] == "Enter a bearing in degrees, or a compass direction:" and d["help"] == ""
    bad = session.run("bearing.set", text="hello")
    assert bad.error == ("hello is not a valid bearing. Enter a value in degrees in the range 0 to 360. "
                         "Or enter a compass direction such as north or SW.")
    assert not bad.announcements and session.world.orientation == "north-fixed"


def test_a_refused_entry_is_named_once_trimmed_and_nothing_typed_says_so(session):
    assert session.run("bearing.set", text="  up   high ").error.startswith("up high is not a valid bearing.")
    assert session.run("bearing.set", text="400").error.startswith("400 is not a valid bearing.")
    assert session.run("bearing.set", text="  ").error.startswith("No bearing was entered. Enter a value in degrees")
    assert session.run("goto.set", text="").error.startswith("Nothing was entered. Enter latitude and then longitude")
    assert session.run("goto.set", text="{x}").error.startswith("{x} is not a valid entry.")   # braces are only text


def test_a_typed_bearing_switches_to_free_facing_and_says_so(session):
    r = session.run("bearing.set", text="NE")
    assert spoken(r) == ["Free facing, 45 degrees."] and session.world.orientation == "free"
    assert session.world.heading == 45.0 and r.redraw
    assert spoken(session.run("bearing.set", text="100")) == ["Facing 100 degrees."]


def test_the_turning_keys(session):
    session.press("O")
    session.press("O")   # free
    assert spoken(session.press("Ctrl+Right")) == ["Facing 1 degrees."]
    assert spoken(session.press("Shift+Right")) == ["Facing 91 degrees."]
    assert spoken(session.press("Ctrl+Left")) == ["Facing 90 degrees."]
    assert spoken(session.press("Shift+Left")) == ["Facing 0 degrees."]


def test_the_large_turn_is_a_setting_starting_at_90(session):
    field = next(f for tab in session.settings_schema()["tabs"] for f in tab["fields"] if f["id"] == "large_turn_deg")
    assert field["label"] == "Free facing: degrees turned by Shift with Left and Right" and field["default"] == 90
    session.run("settings.set", field="large_turn_deg", value=45)
    session.press("O")
    session.press("O")   # free
    assert spoken(session.press("Shift+Right")) == ["Facing 45 degrees."]
    assert spoken(session.press("Shift+Left")) == ["Facing 0 degrees."]


@pytest.mark.parametrize("presses", [0, 1], ids=["north-fixed", "cardinal facing"])
def test_shift_and_ctrl_turns_do_nothing_outside_free_facing(session, presses):
    """PO notes on checklist 2.2 and 2.3: no turn, no sound and nothing said."""
    for _ in range(presses):
        session.press("O")
    heading = session.world.heading
    for key in ("Shift+Left", "Shift+Right", "Ctrl+Left", "Ctrl+Right"):
        r = session.press(key)
        assert r.earcons == [] and not r.announcements and not r.redraw
    assert session.world.heading == heading


def test_a_held_turn_counts_for_the_web_clicks(session):
    session.world.face(10.0)
    session.press("Left")
    info = session.hold_info()
    assert info["command"] == "move.west" and info["left"] > 0


# Going to coordinates and the position history ----------------------------------------

def test_the_go_to_box_asks_and_refuses_what_it_cannot_read(session):
    d = session.press("Ctrl+G").dialog
    assert d["kind"] == "input" and d["submit"] == "goto.set"
    assert d["label"] == "Enter latitude and longitude:" and d["help"] == ""   # the PO: no long help
    bad = session.run("goto.set", text="91, 0")
    assert bad.error == ("91, 0 is not a valid entry. Enter latitude and then longitude, such as 51.5, -0.12 "
                         "or 51d 30m N, 0d 7m W. Latitude is up to 90 degrees and longitude up to 180. "
                         "Or enter one of them alone to keep the other. "
                         "Or enter a direction and degrees to move, such as north 5. "
                         "In cardinal or free facing, enter f or b and a distance to move forward or back, "
                         "such as f 24 or b 2 km 500 m.")
    assert not bad.announcements and near(session, 51.2, 1.2)


def test_go_to_with_one_number_keeps_the_other_and_a_direction_moves_by_it(session):
    session.run("goto.set", text="52")
    assert near(session, 52.0, 1.2)
    session.run("goto.set", text=", -1.5")
    assert near(session, 52.0, -1.5)
    session.run("goto.set", text="south 2 east 3")
    assert near(session, 50.0, 1.5)
    session.run("goto.set", text="n 50")       # past the pole, the move stops at it
    assert session.world.lat == 90.0
    session.run("goto.set", text="0, 179")
    session.run("goto.set", text="east 2")     # across the 180 degree line
    assert near(session, 0.0, -179.0)
    assert len(session.back_places) == 6       # each is a jump, so Alt+comma comes back


def test_forward_and_back_in_go_to_work_only_when_facing(session):
    r = session.run("goto.set", text="f 24")
    assert r.error == "Forward and back work in cardinal and free facing. Press O to change the orientation, or enter where to go."
    assert not r.announcements and near(session, 51.2, 1.2) and not session.back_places


def test_forward_in_go_to_moves_the_distance_the_way_you_face(session):
    session.world.set_orientation("free")
    session.world.heading = 90.0
    r = session.run("goto.set", text="f 24")      # kilometres, as the units are metric
    distance, bearing, _ = geodesy.inverse(51.2, 1.2, session.world.lat, session.world.lon)
    assert distance == pytest.approx(24_000, abs=1) and bearing == pytest.approx(90.0, abs=0.01)
    assert r.error is None and r.announcements and len(session.back_places) == 1   # a jump: Alt+comma comes back
    session.run("goto.set", text="b24km")       # back the same way, still facing about east
    assert geodesy.distance_m(51.2, 1.2, session.world.lat, session.world.lon) < 1
    assert session.world.heading == pytest.approx(90.0, abs=0.5) and session.world.orientation == "free"


def test_back_in_cardinal_facing_and_the_users_own_unit(session):
    session.run("settings.set", field="units", value="imperial")
    session.world.set_orientation("cardinal")      # facing north
    session.run("goto.set", text="b 10")           # 10 miles south
    assert geodesy.distance_m(51.2, 1.2, session.world.lat, session.world.lon) == pytest.approx(10 * MILE, abs=1)
    assert session.world.lat < 51.2 and session.world.lon == pytest.approx(1.2) and session.world.heading == 0.0


def test_forward_over_a_pole_comes_out_facing_the_other_way_and_says_so(session):
    session.run("goto.set", text="89.9, 0")
    session.world.set_orientation("cardinal")
    r = session.run("goto.set", text="f 50")
    assert session.world.heading == 180.0 and session.world.lat < 89.9
    assert any(a["text"].startswith("Crossed the North Pole. Now facing south.") for a in r.announcements)


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


# The location history (NAV-10, DP158) ------------------------------------------------

def walk_to_france(session):
    """Kent, two places at sea, then France: four places, each in the oceans layer or not."""
    for key in ("Down", "Right", "Right"):
        session.press(key)


def test_the_location_history_lists_the_places_newest_first_and_opens_on_here(session):
    walk_to_france(session)
    session.press("Alt+,")                          # back to sea: France is now a place forward
    r = session.press("Ctrl+Shift+Space")
    d = r.dialog
    assert d["kind"] == "history" and d["title"] == "Location history" and d["go"] == "history.go"
    assert d["help"] == ("Newest first. Press Enter on a place to go there. "
                         "Alt+comma and Alt+full stop go through the same places.")
    assert d["lines"] == ["Pas-de-Calais, Hauts-de-France, France", "Here: North Atlantic Ocean",
                          "North Atlantic Ocean", "Kent, England, United Kingdom"]
    assert d["current"] == 1


def test_only_places_go_into_it_not_other_announcements(session):
    for command in ("where.heading", "sound.mute", "sound.mute", "beacon.toggle", "where.am_i"):
        session.run(command)
    assert session.run("history.list").dialog["lines"] == ["Here: Kent, England, United Kingdom"]
    assert not hasattr(session, "history")          # the announcement history is gone (DP158)


def test_enter_on_a_place_goes_there_as_alt_comma_would(session):
    session.press("Page Up")                        # Kent is kept at this zoom by the step after it
    zoom = session.world.zoom_m
    walk_to_france(session)
    lines = session.run("history.list").dialog["lines"]
    go = session.run("history.go", index=len(lines) - 1)
    assert (session.world.lat, session.world.lon, session.world.zoom_m) == (51.2, 1.2, zoom)
    assert spoken(go) == ["Kent, England, United Kingdom"] and go.redraw and not go.error
    assert len(session.back_places) == 0 and len(session.forward_places) == 3   # no place added
    d = session.run("history.list").dialog
    assert d["lines"][-1] == "Here: Kent, England, United Kingdom" and d["current"] == 3
    session.run("history.go", index=0)              # and forward again, to France
    assert spoken(session.press("Space")) == ["Pas-de-Calais, Hauts-de-France, France"]
    assert not session.forward_places


def test_enter_on_here_says_the_place_and_stays(session):
    session.press("Down")
    before = (list(session.back_places), session.world.lat, session.world.lon)
    session.run("history.list")
    r = session.run("history.go", index=0)
    assert spoken(r) == ["North Atlantic Ocean"]
    assert (session.back_places, session.world.lat, session.world.lon) == before


def test_a_place_in_a_layer_switched_off_is_left_out_and_passed_over(session):
    walk_to_france(session)
    session.run("layers.set", layer="oceans", field="on", value=False)
    assert session.run("history.list").dialog["lines"] == ["Here: Pas-de-Calais, Hauts-de-France, France",
                                                           "Kent, England, United Kingdom"]
    back = session.press("Alt+,")                   # over both places at sea, straight to Kent
    assert spoken(back) == ["Kent, England, United Kingdom"] and near(session, 51.2, 1.2)
    assert session.press("Alt+,").earcons == ["blocked"]
    session.press("Alt+.")                          # and forward, straight to France
    assert spoken(session.press("Space")) == ["Pas-de-Calais, Hauts-de-France, France"]
    session.run("layers.set", layer="oceans", field="on", value=True)
    assert len(session.run("history.list").dialog["lines"]) == 4   # kept, and listed again


def test_a_place_outside_its_layers_zoom_range_is_left_out(session):
    walk_to_france(session)
    session.run("layers.set", layer="oceans", field="max_zoom_m", value=10_000)   # the places are at 25 km
    assert "North Atlantic Ocean" not in session.run("history.list").dialog["lines"]


def test_a_wrong_row_does_nothing(session):
    session.press("Down")
    session.run("history.list")
    r = session.run("history.go", index=50)
    assert r.earcons == ["blocked"] and not r.announcements and not r.error
