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


def test_a_move_that_changes_nothing_is_only_a_tick(session):
    r = session.press("Up")
    assert spoken(r) == [] and r.earcons == ["tick"]


def test_unknown_keys_are_left_to_the_shell(session):
    assert session.press("F9") is None
    assert session.press("Y") is None


def test_history_keeps_at_least_50_and_lists_the_latest_first(session):
    for _ in range(60):
        session.run("where.heading")
    r = session.press("Ctrl+Shift+Space")
    assert r.dialog["kind"] == "history" and len(r.dialog["lines"]) >= 50
    session.press("Space")
    assert session.run("speech.history").dialog["lines"][0] == "Kent, England, United Kingdom"


def test_empty_history_and_nothing_to_repeat(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    assert spoken(s.press("Ctrl+Space")) == ["Nothing to repeat."]
    assert s.run("speech.history").dialog["lines"] == ["Nothing has been announced yet."]


def test_repeat_says_the_last_announcement_again(session):
    session.press("Space")
    assert spoken(session.press("Ctrl+Space")) == ["Kent, England, United Kingdom"]


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


def test_release_after_a_hold_that_changed_nothing_is_a_tick(session):
    session.run("move.north", held=True)
    assert session.release().earcons == ["tick"]


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
    assert spoken(session.press("Up")) == ["Up: Step north"]
    assert spoken(session.press("Page Up")) == ["Page Up: Zoom out"]
    assert spoken(session.press("F9")) == ["F9: no command."]
    assert (session.world.lat, session.world.zoom_index) == before
    assert spoken(session.press("Shift+F1")) == ["Key describer off."]
    assert not session.describing
    assert session.press("Up").earcons == ["tick"]


def test_f1_lists_the_commands_for_the_focused_region_with_keys(session):
    on_map = session.press("F1", "map").dialog["text"]
    assert "Step north: Up" in on_map and "Heading: H" in on_map
    in_panel = session.press("F1", "panel").dialog["text"]
    assert "Step north" not in in_panel and "Go to Details: F4" in in_panel
    assert "Link step to zoom: in the Map menu" in on_map


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
    within, nearby = s.panel()
    assert [i["label"] for i in within["items"]] == ["Niagara Region", "Ontario", "Canada"]
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
    assert lines[0] == "Kent" and lines[1] == "Type: county"
    assert lines[2].startswith("Part of:") and any(line.startswith("Source:") for line in lines)


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


def test_the_visible_map_is_the_zoom_distance(session):
    assert spoken(session.press("V")) == ["Visible map: 25 kilometres across."]


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


def test_about_data_gives_the_attribution(session):
    text = session.run("help.about_data").dialog["text"]
    assert "OpenStreetMap" in text and "ODbL" in text


def test_the_earcons_help_lists_the_files(session):
    assert "tick.wav" in session.run("help.earcons").dialog["text"]


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
