"""The map session over the test pack: commands in, responses out, with exact wording (AD-2, 3.4, NFR-5).

The approved wording of the walks is in tests/acceptance/scripts. These tests hold the rest:
history, repeat, remapping, the key describer, held keys, F3, settings, details and saving.
"""
import pytest

from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


def test_start_announces_the_place(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    r = s.start()
    assert spoken(r) == ["TobyMap. Kent, England, United Kingdom. Press F1 for keys."]
    assert r.redraw and r.panel_stale and r.details_stale


def test_the_map_is_named_with_the_start_less_the_window_title(test_pack):
    # The screen reader reads the window's title, then the map's name, as the window appears (P2-T17d).
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    assert s.start_label() == "Kent, England, United Kingdom. Press F1 for keys."


def test_a_move_that_changes_nothing_is_only_a_tick(session):
    r = session.press("Up")
    assert spoken(r) == [] and r.earcons == ["tick"]


def test_every_command_tells_the_shell_to_stop_the_voice_except_one_that_starts_a_label(session):
    """P2-T17n, SON-3: a key press never leaves the voice talking over the screen reader."""
    assert session.run("move.south").stop_voice
    assert session.run("speech.repeat").stop_voice
    assert session.run_many([("move.north", {}), ("move.south", {})]).stop_voice
    session.run("sound.mute")
    assert session.run("move.south").stop_voice


def test_unknown_keys_are_left_to_the_shell(session):
    assert session.press("F9") is None
    assert session.press("Y") is None


def test_ctrl_shift_space_opens_the_location_history(session):
    r = session.press("Ctrl+Shift+Space")       # DP158: the announcement history is now the location history
    assert r.dialog["kind"] == "history" and r.dialog["lines"] == ["Here: Kent, England, United Kingdom"]


def test_nothing_to_repeat(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    assert spoken(s.press("Shift+Space")) == ["Nothing to repeat."]


def test_repeat_says_the_last_announcement_again(session):
    session.press("Space")
    assert spoken(session.press("Shift+Space")) == ["Kent, England, United Kingdom"]


def test_ten_joined_moves_describe_only_the_last_place(session):
    r = session.run_many([("move.south", {})] * 10)
    assert session.world.lat < 50.0
    assert len(r.announcements) <= 1
    assert spoken(r) == ["France"]   # 250 km south: one description, of the last place


def test_held_moves_are_all_made_but_nothing_is_said_until_release(session):
    out = [session.run("move.south", held=True) for _ in range(3)]
    assert all(not r.announcements and not r.earcons for r in out)
    assert session.world.lat < 51.2 - 0.5
    done = session.release()
    assert spoken(done) == ["North Atlantic Ocean"]
    assert not session.release().announcements   # a second release says nothing


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def hold(s, clock, seconds: float):
    """Hold a key for `seconds`, stepping when hold_due() says, as the shells' timers do.
    Returns the times of the steps and of the drawings asked for."""
    steps, draws = [], []
    end = clock.now + seconds
    while True:
        due = s.hold_due()
        if clock.now + due > end + 1e-6:
            break
        clock.now += due
        r = s.run(s.holding, held=True, repeat=True)
        assert r.earcons == ["tick"] and not r.announcements
        steps.append(clock.now)
        if r.redraw:
            draws.append(clock.now)
    clock.now = end
    return steps, draws


def test_a_held_key_steps_after_the_repeat_delay_then_at_the_repeat_rate(test_pack):
    """DP129, DP140: the shell's timer steps when the core says: after the delay
    (500 ms), then at the rate (6 a second), whatever the system's key repeat does.
    Each of those steps ticks, and nothing is said until the release."""
    clock = FakeClock()
    s = MapSession(packs=[test_pack], saved_state=dict(KENT), clock=clock)
    s.start()
    assert s.hold_due() is None                           # no key held
    first = s.run("move.south")                           # the press steps and speaks at once
    assert spoken(first) and first.redraw
    assert s.hold_due() == pytest.approx(0.5)
    steps, _ = hold(s, clock, 2.0)
    assert steps[0] == pytest.approx(100.5)
    assert [round(b - a, 6) for a, b in zip(steps, steps[1:])] == [round(1 / 6, 6)] * (len(steps) - 1)
    assert len(steps) == 10                               # 1.5 seconds after the delay, 6 a second
    assert spoken(s.release())
    assert s.hold_due() is None


def test_the_repeat_delay_and_rate_are_settings(test_pack):
    clock = FakeClock()
    s = MapSession(packs=[test_pack], saved_state=dict(KENT), clock=clock)
    s.start()
    s.run("settings.set", field="repeat_delay_ms", value=200)
    s.run("settings.set", field="repeat_rate", value=10)
    s.run("move.south")
    steps, _ = hold(s, clock, 1.0)
    assert len(steps) == 9                                # 0.8 seconds after the delay, 10 a second


def test_a_late_timer_keeps_the_beat_and_never_makes_two_steps_at_once(test_pack):
    clock = FakeClock()
    s = MapSession(packs=[test_pack], saved_state=dict(KENT), clock=clock)
    s.start()
    s.run("move.south")
    clock.now += 0.5 + 0.05                               # 50 ms late: the next is still on the beat
    s.run("move.south", held=True, repeat=True)
    assert s.hold_due() == pytest.approx(1 / 6 - 0.05)
    clock.now += 1.0                                      # very late: the next is half a step from now
    s.run("move.south", held=True, repeat=True)
    assert s.hold_due() == pytest.approx(1 / 12)


def test_while_a_key_is_held_the_map_is_drawn_at_most_4_times_a_second_then_once_after(test_pack):
    """DP140: the drawing never holds up the steps. Held steps ask for a drawing
    at most held_draw_rate times a second; the release always draws."""
    clock = FakeClock()
    s = MapSession(packs=[test_pack], saved_state=dict(KENT), clock=clock)
    s.start()
    s.run("settings.set", field="repeat_rate", value=10)
    s.run("move.south")
    steps, draws = hold(s, clock, 3.0)
    assert len(steps) == 26
    assert 9 <= len(draws) <= 10                          # 2.5 seconds of steps, 4 drawings a second
    assert all(b - a >= 0.249 for a, b in zip(draws, draws[1:]))
    assert s.release().redraw


def test_held_steps_leave_the_panel_and_details_until_the_release(session):
    r = session.run("move.south")
    assert r.panel_stale and r.details_stale
    r = session.run("move.south", held=True, repeat=True)
    assert not r.panel_stale and not r.details_stale
    done = session.release()
    assert done.panel_stale and done.details_stale and done.redraw


def test_the_hold_says_how_many_steps_will_move_for_the_web_clicks(test_pack):
    """The web page plays each click at its due time without waiting for the
    worker, so the core says how many of the next steps will move (DP140)."""
    s = MapSession(packs=[test_pack], saved_state={"lat": 89.0, "lon": 0, "zoom_m": 250000, "step_m": 25000})
    s.start()
    s.run("move.south")
    info = s.hold_info()
    assert info["command"] == "move.south" and info["delay_ms"] == 500 and info["every_ms"] == pytest.approx(1000 / 6)
    assert info["unlimited"] and info["left"] == 13 and info["tick"]
    s.release()
    s.run("move.north")                                   # back to 89 north: 4 more 25 km steps, then the pole
    info = s.hold_info()
    assert not info["unlimited"] and info["left"] == 4
    assert (s.world.lat, s.world.lon) == (pytest.approx(89.0, abs=0.01), 0)   # the probe never moves you
    s.run("sound.mute")
    assert s.hold_info()["tick"] is False                 # muted: the page plays no clicks
    s.release()
    assert s.hold_info() is None


def test_drawings_go_into_the_trace_in_their_parts(session):
    from mapcore import diagnostics

    session.scene(800, 600)
    session.frame_painted(12.5)
    event = session.trace[-1]
    assert event["command"] == "draw" and event["paint_ms"] == 12.5
    assert event["choose_ms"] >= 0 and event["project_ms"] >= 0 and event["points"] > 0
    session.press("Space")
    diagnostics.add_shell(session, key_pressed_at=None, handed_over_at=event["at"] + 1)
    assert "handed_to_screen_reader_ms" in session.trace[-1] and "handed_to_screen_reader_ms" not in event
    assert "painting 12.5 ms" in diagnostics.report(session)


def test_release_after_a_hold_that_changed_nothing_plays_no_tick_of_its_own(session):
    """Each held step has clicked already, so a tick on the release was a second click
    when the key was let go (Phase 2 web checklist 2.10)."""
    r = session.run("move.north", held=True, repeat=True)
    assert r.earcons == ["tick"]
    done = session.release()
    assert "tick" not in done.earcons and not done.announcements and done.redraw


def test_holding_across_a_border_speaks_the_place_it_ends_in_against_where_it_began(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.9753, "lon": 1.2, "zoom_m": 25000, "step_m": 25000})
    s.start()
    for _ in range(2):
        s.run("move.east", held=True)
    assert spoken(s.release()) == ["Pas-de-Calais, Hauts-de-France, France"]


def test_a_block_at_the_pole_is_silent(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": -89.9, "lon": 0, "zoom_m": 250000, "step_m": 25000})
    s.start()
    r = s.run("move.south")
    assert r.earcons == ["blocked"] and not r.announcements and not r.redraw


def test_the_key_describer_describes_and_does_nothing(session):
    r = session.press("Shift+F1")
    assert "Key describer on" in spoken(r)[0]
    before = (session.world.lat, session.world.zoom_index)
    assert spoken(session.press("Up")) == ["Up: Step north or forward"]
    assert spoken(session.press("Page Up")) == ["Page Up: Zoom out"]
    assert spoken(session.press("F9")) == ["F9: no command."]
    assert (session.world.lat, session.world.zoom_index) == before
    assert spoken(session.press("Shift+F1")) == ["Key describer off."]
    assert not session.describing
    assert session.press("Up").earcons == ["tick"]


def test_the_key_describer_is_the_same_in_every_region(session):
    """PO feedback on checklist 2.2: the describer says what a key does anywhere,
    and Tab is caught and does nothing."""
    session.press("Shift+F1")
    for region in ("map", "panel", "details"):
        assert spoken(session.press("Down", region)) == ["Down: Step south or back"]
        assert spoken(session.press("Tab", region)) == ["Tab: no command."]
        assert spoken(session.press("Shift+Tab", region)) == ["Shift+Tab: no command."]
    assert session.world.lat == KENT["lat"]


def test_the_key_describer_lists_every_command_on_a_key(session, monkeypatch):
    """A key with one command on the map and another in the panel says both."""
    from mapcore.commands import registry

    real = registry.for_platform
    extra = registry.Command(name="panel.sort", label="Sort the list", key="Down", region="panel", menu="",
                             platforms=("desktop", "web"))
    monkeypatch.setattr(registry, "for_platform", lambda platform: real(platform) + [extra])
    session.press("Shift+F1")
    assert spoken(session.press("Down", "panel")) == [
        "Down: Step south or back, on the map. Sort the list, in the Information panel."]


def test_f1_lists_the_commands_for_the_focused_region_with_keys(session):
    on_map = session.press("F1", "map").dialog["text"]
    assert "Step north or forward: Up" in on_map and "Heading: H" in on_map
    in_panel = session.press("F1", "panel").dialog["text"]
    assert "Step north or forward" not in in_panel and "Go to Details: F4" in in_panel
    assert "Link step to zoom: S" in on_map and "Link step to zoom" not in in_panel
    assert "Send a Braille-only message: in the Speech menu" in on_map


def test_remapping_to_a_key_in_use_names_the_other_command(session):
    r = session.run("keys.remap", command="where.heading", key="C")
    assert spoken(r) == ["C is already used by Coordinates. Choose another key."]
    assert session.settings.keys == {}
    r = session.run("keys.remap", command="where.heading", key="Ctrl+Q")
    assert spoken(r) == ["Heading is now Ctrl+Q."] and r.settings_changed
    assert session.press("Ctrl+Q").announcements and session.press("H") is None
    assert session.run("keys.remap", command="where.heading", key="H").settings_changed
    assert session.settings.keys == {}


def test_a_global_key_clashes_with_a_map_key(session):
    r = session.run("keys.remap", command="where.heading", key="F2")
    assert "already used by Go to the map" in spoken(r)[0]


def test_an_invalid_key_is_refused(session):
    assert "not a key" in spoken(session.run("keys.remap", command="where.heading", key="Control+Q"))[0]


def test_f2_f3_f4_go_to_the_regions_from_anywhere(session):
    for region in ("map", "panel", "details", "menu"):
        assert session.press("F2", region).focus == {"region": "map"}
        assert session.press("F4", region).focus == {"region": "details"}
    first = session.press("F3", "map").focus
    assert first["region"] == "panel" and first["item"] == session.areas[0].id


def test_f3_goes_back_to_the_item_last_focused(session):
    nearby_item = session.panel()[1]["items"][0]["id"]
    session.run("panel.select", item=nearby_item)
    assert session.press("F3", "details").focus["item"] == nearby_item
    session.run("move.north")
    assert session.press("F3", "map").focus["item"] in {i["id"] for g in session.panel() for i in g["items"]}


def test_the_panel_has_within_and_nearby_with_levels(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 43.08, "lon": -79.08, "zoom_m": 5000, "step_m": 100})
    s.start()
    within, nearby, _crossed = s.panel()[:3]
    assert [i["label"].split(",")[0] for i in within["items"]] == ["Niagara Region", "Ontario", "Canada"]
    assert all(", centre " in i["label"] for i in within["items"])   # its centre's distance and direction (P2-T17k)
    assert nearby["items"][0]["label"].startswith("United States, 410 metres east")
    assert all(i["level"] == 1 for g in (within, nearby) for i in g["items"])
    assert {i["id"] for i in within["items"]}.isdisjoint({i["id"] for i in nearby["items"]})


def test_selecting_an_item_shows_it_in_details_and_clears_on_a_move(session):
    session.world.step_index = 0
    session.run("panel.select", item=session.areas[-1].id)
    assert session.details().splitlines()[0] == "United Kingdom"
    session.run("move.north")
    assert session.details().splitlines()[0] == "Kent"


def test_details_name_type_parents_area_and_source(session):
    lines = session.details().splitlines()
    assert lines[0] == "Kent" and lines[1] == "Type: county of England"   # its tier and the area above (P3-T17)
    assert lines[2].startswith("Part of:") and any(line.startswith("Source:") for line in lines)


def test_the_sounds_in_help_can_be_played(session):
    """DP134: Help, The sounds lists each sound, and each can be played from the list."""
    d = session.run("help.earcons").dialog
    assert d["kind"] == "sounds" and d["play"] == "Play"
    assert d["items"][0] == {"event": "tick", "label": "Tick, click.wav: A step that changed nothing."}
    assert session.run("sound.preview", event="blocked").earcons == ["blocked"]
    assert not session.run("sound.preview", event="blocked").announcements


def test_mute_drops_the_earcons_and_is_a_setting(session):
    session.world.step_index = 0
    session.press("Ctrl+M")
    assert session.press("Up").earcons == [] and session.settings["mute"]
    session.press("Ctrl+M")
    assert session.press("Up").earcons == ["tick"]


def test_settings_are_checked(session):
    assert session.run("settings.set", field="units", value="furlongs").announcements
    assert session.settings["units"] == "metric"
    assert session.run("settings.set", field="nearby_count", value=3).settings_changed
    assert len(session.panel()[1]["items"]) <= 3


def test_the_visible_map_is_width_by_height(session):
    """V gives both sides (DP99). The zoom distance is drawn 300 pixels from the centre
    (DP138), so a 600 pixel side is twice the zoom, and a bigger window shows more."""
    session.map_size = (800, 600)
    assert spoken(session.press("V")) == ["Visible map: 67 kilometres wide by 50 kilometres high."]
    session.map_size = (600, 600)
    assert spoken(session.press("V")) == ["Visible map: 50 kilometres wide by 50 kilometres high."]
    session.map_size = (600, 900)
    assert spoken(session.press("V")) == ["Visible map: 50 kilometres wide by 75 kilometres high."]
    session.map_size = (1200, 1200)            # a bigger window shows more (DP138)
    assert spoken(session.press("V")) == ["Visible map: 100 kilometres wide by 100 kilometres high."]


def test_the_zoom_is_the_distance_to_the_nearer_edge(session):
    """NAV-13, DP138: a point 25 km north is 300 pixels up, the top edge of an 800 by 600 map."""
    from mapcore.render import globe, scene

    view = scene.view_for(session.world, 800, 600)
    lat_edge = session.world.lat + 25000 / 6371008.8 * 180 / 3.141592653589793
    x, y = globe.to_screen(view, 800, 600, lat_edge, session.world.lon)
    assert abs(y) < 1.0 and abs(x - 400) < 1.0


def test_imperial_zoom_and_step_are_round_numbers(session):
    """Checklist 7.5, DP136: imperial zoom and step are round sizes, and Page Up goes on through them."""
    session.run("settings.set", field="units", value="imperial")
    assert "Zoom 10 miles, step 10 miles." in spoken(session.press("H"))[0]     # nearest to 25 kilometres
    assert spoken(session.press("Page Up")) == ["Zoom 25 miles."]
    assert spoken(session.press("Page Down")) == ["Zoom 10 miles."]


def test_only_the_size_that_changed_is_said(session):
    """PO feedback on checklist 7, second pass: the zoom keys say the zoom, the step
    keys the step. Linked, both change, so both are said."""
    assert spoken(session.press("Page Down")) == ["Zoom 10 kilometres."]
    said = spoken(session.press("Shift+Page Down"))[0]
    assert said.startswith("Step ") and "Zoom" not in said
    session.run("step.link", on=True)
    said = spoken(session.press("Page Up"))[0]
    assert said.startswith("Zoom 25 kilometres, step ")


def test_linked_both_are_said_even_when_the_nearest_step_is_the_same(session):
    """Web checklist 16.2, desktop 16.2 (P2-T17j, NAV-2, NAV-13): linked, the step is the one in
    the list nearest a quarter of the zoom. With the step sizes of P3-T0f every zoom from 1 to
    1,000 kilometres has its own step, so Page Up changes both; both are still said, as NAV-2 asks.
    The same step for two zooms remains below 1 kilometre, tested next."""
    session.press("S")
    assert session.world.step_m == 5000
    assert spoken(session.press("Page Up")) == ["Zoom 50 kilometres, step 10 kilometres."]
    assert session.world.step_m == 10000
    assert spoken(session.press("Page Up")) == ["Zoom 100 kilometres, step 25 kilometres."]
    assert spoken(session.press("Page Down")) == ["Zoom 50 kilometres, step 10 kilometres."]


def test_linked_the_step_keys_say_both_even_when_the_nearest_zoom_is_the_same(session):
    """P2-T17j, NAV-2: the step keys, linked, say the zoom and the step too. Steps of 25 and
    10 metres both give a zoom of 100 metres, the smallest."""
    session.press("S")
    for _ in range(8):   # 5 kilometres down to 10 metres
        said = spoken(session.press("Shift+Page Down"))[0]
        assert said.startswith("Zoom ") and ", step " in said, said
    assert said == "Zoom 100 metres, step 10 metres."


def test_s_links_the_step_to_the_zoom_on_the_map_only(session):
    """PO note on checklist 13.6: S for Link step to zoom. On the map only, so letters in the
    Information panel and Details still go to the item starting with that letter."""
    r = session.press("S")
    assert session.world.link and spoken(r)[0].startswith("Step linked to zoom.")
    session.press("S")
    assert not session.world.link
    for region in ("panel", "details"):
        assert session.press("S", region) is None and session.press("A", region) is None
    assert not session.world.link


def test_at_the_end_of_the_list_only_that_size_is_said(session):
    for _ in range(40):
        r = session.press("Shift+Page Down")
    assert spoken(r)[0].startswith("Smallest step. Step ") and "Zoom" not in spoken(r)[0]


def test_coordinates_have_the_places_the_step_needs(session):
    """PO feedback on checklist 4, second pass: a 25 kilometre step needs one decimal place."""
    assert spoken(session.press("C")) == ["51.2 degrees north, 1.2 degrees east"]
    session.run("settings.set", field="coordinate_places", value="fixed")
    assert spoken(session.press("C")) == ["51.20000 degrees north, 1.20000 degrees east"]


def test_symbol_keys_are_said_as_words(session):
    """PO feedback on checklist 2, second pass: "Ctrl+Comma", not "Ctrl+,", for any symbol."""
    assert "Settings: Ctrl+Comma" in session.press("F1", "map").dialog["text"]
    session.press("Shift+F1")
    assert spoken(session.press("Ctrl+,")) == ["Ctrl+Comma: Settings"]
    assert spoken(session.press("Ctrl+/")) == ["Ctrl+Slash: no command."]
    session.press("Shift+F1")
    r = session.run("keys.remap", command="where.heading", key="Ctrl+,")
    assert spoken(r) == ["Ctrl+Comma is already used by Settings. Choose another key."]
    r = session.run("keys.remap", command="where.heading", key="Ctrl+;")
    assert spoken(r) == ["Heading is now Ctrl+Semicolon."]
    assert next(c for c in session.key_table() if c["name"] == "where.heading")["key_text"] == "Ctrl+Semicolon"


def test_f1_starts_with_short_lines(session):
    """PO feedback on checklist 2, second pass: one short sentence a line."""
    lines = session.press("F1", "map").dialog["text"].splitlines()
    assert lines[0] == "These are the commands that work when the Map has focus."
    assert all(len(line) < 80 for line in lines[:3])


def test_state_and_settings_come_back_after_a_restart(test_pack):
    a = MapSession(packs=[test_pack], saved_state=dict(KENT))
    a.start()
    a.run("settings.set", field="units", value="imperial")
    a.run("move.south")
    a.run("zoom.in")
    saved = a.save()
    b = MapSession(packs=[test_pack], settings=saved["settings"], saved_state=saved["state"])
    assert b.settings["units"] == "imperial"
    assert (b.world.lat, b.world.lon, b.world.zoom_m, b.world.step_m) == (
        a.world.lat, a.world.lon, a.world.zoom_m, a.world.step_m)
    assert spoken(b.start())[0].endswith("Press F1 for keys.")


def test_a_saved_link_comes_back(test_pack):
    a = MapSession(packs=[test_pack], saved_state=dict(KENT))
    a.run("step.link", on=True)
    saved = a.save()
    b = MapSession(packs=[test_pack], settings=saved["settings"], saved_state=saved["state"])
    assert b.world.link and b.settings["link"]


def test_about_keeps_its_lines_so_each_is_read_on_its_own(session):
    import mapcore

    lines = session.run("help.about").dialog["text"].splitlines()
    assert lines == [
        f"TobyMap version {mapcore.version()}.",
        "An accessible map for blind and partially sighted people.",
        "TobyMap is free software under the GNU General Public License version 3.",
        "The spatial voice is Alba, a Scottish English voice from Piper voices, made from recordings by the "
        "University of Edinburgh, licensed CC-BY 4.0.",
        "Every library and its licence is in THIRD_PARTY_NOTICES.txt, in the folder TobyMap is installed in.",
    ]


def test_about_data_gives_the_attribution(session):
    text = session.run("help.about_data").dialog["text"]
    assert "OpenStreetMap" in text and "ODbL" in text


def test_the_earcons_help_lists_the_files(session):
    assert "click.wav" in session.run("help.earcons").dialog["text"]


def test_braille_only_message_is_on_its_own_channel(session):
    r = session.run("speech.braille_test")
    assert r.announcements[0]["channel"] == "braille" and "Braille" in r.announcements[0]["text"]


def test_a_click_moves_the_location_and_describes_the_place(session):
    from mapcore.render import globe, scene as scene_mod

    view = scene_mod.view_for(session.world, 800, 600)
    x, y = globe.to_screen(view, 800, 600, 50.9, 1.2)
    r = session.run("map.click", x=x, y=y, width=800, height=600)
    assert abs(session.world.lat - 50.9) < 0.01 and abs(session.world.lon - 1.2) < 0.01
    assert spoken(r) == ["North Atlantic Ocean"]


def test_hover_is_silent_unless_switched_on(session):
    assert not session.run("map.hover", x=400, y=300, width=800, height=600).announcements
    session.run("settings.set", field="hover_announce", value=True)
    assert spoken(session.run("map.hover", x=400, y=300, width=800, height=600)) == ["Kent"]
    assert (session.world.lat, session.world.lon) == pytest.approx((51.2, 1.2))


def test_the_wheel_changes_the_zoom_one_step(session):
    assert spoken(session.run("map.zoom_to", direction=-1))[0].startswith("Zoom 10 kilometres")
    assert spoken(session.run("map.zoom_to", direction=1))[0].startswith("Zoom 25 kilometres")


def test_the_trace_records_commands_and_what_was_said(session):
    session.press("Space")
    last = session.trace[-1]
    assert last["command"] == "where.am_i" and last["spoken"] == ["Kent, England, United Kingdom"] and last["ms"] >= 0


def test_the_start_option_overrides_the_saved_place_but_keeps_the_zoom(test_pack):
    saved = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}
    s = MapSession(packs=[test_pack], saved_state=saved, start_at="-16.5,179.99")
    assert (s.world.lat, s.world.lon) == (-16.5, 179.99)
    assert s.world.zoom_m == 25000
    ignored = MapSession(packs=[test_pack], saved_state=saved, start_at="nowhere")
    assert (ignored.world.lat, ignored.world.lon) == pytest.approx((51.2, 1.2))
