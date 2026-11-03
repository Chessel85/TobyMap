"""The spike S5 map session: commands in, responses out, with exact wording (AD-2, 3.4, NFR-5).

These are the announcement baselines for the spike. A wording change must be
made in mapcore/describe/templates.yaml and here together.
"""
import pytest

from mapcore.session import MapSession


@pytest.fixture
def session():
    return MapSession()


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


def test_start_announcement(session):
    r = session.start()
    assert spoken(r) == ["TobyMap globe. United Kingdom. Press F1 for keys."]
    assert r.redraw and r.panel_stale and r.details_stale


def test_turning_announces_the_country_under_the_centre(session):
    session.start()
    assert spoken(session.run("globe.south")) == ["Spain"]          # 42 north, 1 west
    assert spoken(session.run("globe.east")) == ["France"]         # 42 north, 9 east: Corsica
    assert session.state.lat == 42 and session.state.lon == 9


def test_sea(session):
    session.start()
    session.run("globe.west")   # 52 north, 11 west, Atlantic
    assert spoken(session.run("where.am_i")) == ["Sea. 52 degrees north, 11 degrees west. Zoom 1 of 5, step 10 degrees."]


def test_where_am_i_and_coordinates(session):
    session.start()
    assert spoken(session.run("where.am_i")) == ["United Kingdom. 52 degrees north, 1 degree west. Zoom 1 of 5, step 10 degrees."]
    assert spoken(session.run("where.coordinates")) == ["52 degrees north, 1 degree west"]


def test_zoom_changes_the_step(session):
    session.start()
    assert spoken(session.run("zoom.in")) == ["Zoom 2 of 5, step 5 degrees."]
    session.run("zoom.in"), session.run("zoom.in"), session.run("zoom.in")
    assert spoken(session.run("zoom.in")) == ["Closest zoom. Zoom 5 of 5, step half a degree."]
    for _ in range(4):
        session.run("zoom.out")
    assert spoken(session.run("zoom.out")) == ["Whole globe. Zoom 1 of 5, step 10 degrees."]


def test_turning_stops_at_the_poles(session):
    session.start()
    for _ in range(3):
        session.run("globe.north")       # 62, 72, 82
    r = session.run("globe.north")
    assert spoken(r) == ["North Pole. Sea"]
    assert session.state.lat == 90
    assert spoken(session.run("globe.north")) == ["North Pole. Sea"]
    assert session.state.lat == 90


def test_east_wraps_around_the_antimeridian(session):
    session.start()
    for _ in range(19):
        session.run("globe.east")
    assert session.state.lon == -171


def test_turning_is_marked_latest_only_and_redraws(session):
    session.start()
    r = session.run("globe.north")
    assert r.redraw and r.panel_stale and r.details_stale
    assert r.announcements[0]["priority"] == "assertive"


def test_rapid_moves_are_all_carried_out_but_only_the_last_is_spoken(session):
    # ANN-3: after 10 rapid moves, the final position is spoken.
    session.start()
    r = session.run_many([("globe.east", {})] * 10)
    assert session.state.lon == 99
    assert spoken(r) == [session._place_name()]
    assert r.redraw and r.panel_stale


def test_repeat_last(session):
    session.start()
    session.run("globe.south")
    assert spoken(session.run("speech.repeat")) == ["Spain"]


def test_braille_only_message_with_a_spoken_fallback(session):
    session.start()
    r = session.run("speech.braille_test")
    (a,) = r.announcements
    assert a["channel"] == "braille"
    assert a["text"] == "TobyMap Braille test: United Kingdom"
    assert a["fallback"] == "Braille-only messages need NVDA, and it was not found."


def test_panel_groups(session):
    session.start()
    groups = session.panel()
    assert [g["label"] for g in groups] == ["Within", "Nearby", "Crossed and passed"]
    within = groups[0]["items"]
    assert [i["label"] for i in within] == ["United Kingdom", "Earth"]
    nearby = groups[1]["items"]
    assert len(nearby) == 8
    # 425.6 km on the ellipsoid (P1-T1); the Phase 0 sphere gave 424.4, said as 420.
    assert nearby[0]["label"] == "Belgium, 430 kilometres east"
    assert groups[2]["items"] == [] and groups[2]["empty"] == "Nothing yet. This group is filled from Phase 2."


def test_details_of_the_current_country_and_of_a_selection(session):
    session.start()
    lines = session.details().splitlines()
    assert lines[0] == "United Kingdom"
    assert "Sovereign state: United Kingdom" in lines
    assert "Continent: Europe" in lines
    assert "Population estimate: 66,834,405" in lines
    r = session.run("panel.select", item="ne:FRA")
    assert r.redraw and r.details_stale and not r.announcements
    lines = session.details().splitlines()
    assert lines[0] == "France"
    assert lines[-2] == "From the centre of the map: 640 kilometres south-east"


def test_details_at_sea(session):
    session.start()
    session.run("globe.west")
    assert session.details().splitlines()[:2] == ["Sea", "No country here in the Natural Earth sample."]


def test_focus_commands(session):
    session.start()
    assert session.run("panel.within").focus == {"region": "panel", "group": "within"}
    assert session.run("panel.nearby").focus == {"region": "panel", "group": "nearby"}
    assert session.run("details.show").focus == {"region": "details"}


def test_click_centres_the_globe(session):
    session.start()
    r = session.run("map.click", x=400, y=300, width=800, height=600)
    assert spoken(r) == ["United Kingdom"]
    r = session.run("map.click", x=1, y=1, width=800, height=600)
    assert spoken(r) == ["Not on the globe."]


def test_help_keys_dialog_lists_commands_for_the_platform(session):
    session.start()
    r = session.run("help.keys", platform="web")
    assert r.dialog["title"] == "Keys"
    assert "Turn the globe north: Up" in r.dialog["text"]
    assert "Exit" not in r.dialog["text"]
    assert "Go to the menu bar: Ctrl+Alt+M" in r.dialog["text"]


def test_menu_bar_key_is_web_only_and_moves_focus_silently(session):
    # DP93: Tab no longer reaches the menu bar; the desktop uses Alt.
    from mapcore.commands import registry
    assert registry.keymap("web")["global"]["Ctrl+Alt+M"] == "focus.menu"
    assert "Ctrl+Alt+M" not in registry.keymap("desktop")["global"]
    session.start()
    r = session.run("focus.menu")
    assert r.focus == {"region": "menu"}
    assert r.announcements == []


def test_timing_report(session):
    session.start()
    session.scene(800, 600)
    session.frame_painted(3.2)
    session.startup_took(4321)
    text, startup = spoken(session.run("diagnostics.timing"))
    assert text.startswith("Last frame: worked out in ")
    assert "painted in 3 milliseconds" in text
    assert "points" in text
    assert startup == "Start-up took 4.3 seconds."


def test_map_label_is_the_place(session):
    session.start()
    assert session.map_label() == "United Kingdom"
    session.run("globe.west")
    assert session.map_label() == "Sea"


def test_window_words(session):
    words = session.words()
    assert words["map"] == "Map" and words["panel"] == "Information panel" and words["close"] == "Close"


def test_exit_is_an_action(session):
    assert session.run("app.exit").action == "exit"


def test_unknown_command_raises(session):
    with pytest.raises(KeyError):
        session.run("no.such.command")


def test_response_as_plain_dict(session):
    d = session.start().to_dict()
    assert set(d) == {"announcements", "redraw", "panel_stale", "details_stale", "focus", "dialog", "action"}


def test_v_says_the_size_of_the_visible_map(session):
    # PO feedback on spike S5: "Visible map: 182 by 92 km".
    session.start()
    session.scene(900, 700)
    assert spoken(session.run("where.visible")) == ["Visible map: the whole globe."]
    for _ in range(4):
        session.run("zoom.in")
    assert spoken(session.run("where.visible")) == ["Visible map: 1,140 by 890 kilometres."]
    session.scene(450, 700)  # the globe is sized to the narrower side, so more is visible
    assert spoken(session.run("where.visible")) == ["Visible map: 890 by 1,380 kilometres."]


def test_pack_messages():
    # Why a pack was not opened, or what is damaged (PCK-5, NFR-4, P1-T2).
    from mapcore.describe import say

    assert say("packs.not_a_pack", name="a.pack") == "a.pack is not a TobyMap pack, so it was not opened."
    assert say("packs.newer_format", name="a.pack") == (
        "a.pack needs a newer version of TobyMap, so it was not opened. Update TobyMap to use it.")
    assert say("packs.app_too_old", name="a.pack", need="0.2.0", have="0.1.0") == (
        "a.pack needs TobyMap 0.2.0 or later, and this is TobyMap 0.1.0, so it was not opened. "
        "Update TobyMap to use it.")
    assert say("packs.app_too_new", name="a.pack", before="0.2.0", have="0.2.1") == (
        "a.pack was made for versions of TobyMap before 0.2.0, and this is TobyMap 0.2.1, so it was not "
        "opened. Download the current pack instead.")
    assert say("packs.damaged_pack", name="a.pack", record="directory") == (
        "a.pack is damaged, so it was not opened. Download it again. The damage is in its directory.")
    assert say("packs.damaged_record", name="a.pack", record="tile/5/3/4") == (
        "Part of a.pack is damaged, and TobyMap is carrying on without it. Download the pack again. "
        "The damaged record is tile/5/3/4.")
    assert say("packs.checksum_wrong", name="a.pack") == (
        "a.pack does not match its checksum, so it may be damaged or incomplete. Download it again.")
