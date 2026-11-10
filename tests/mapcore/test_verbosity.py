"""The verbosity presets and their switches (P2-T11a; ACC-5, ANN-1, DP144).

The presets' words on the Channel crossing are in tests/acceptance/scripts: channel.yaml is
normal, channel-terse.yaml and channel-detailed.yaml the other two.
"""
import pytest

from mapcore import settings as settings_mod
from mapcore.commands import registry
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


def test_normal_is_the_default_and_is_what_phase_1_said(session):
    v = session.settings
    assert v["verbosity"] == "normal" and v["say_area"] == "changed"
    assert v["say_zoom_step"] and v["say_heading"] and not v["say_heading_on_step"]


def test_choosing_a_preset_sets_its_switches(session):
    session.run("settings.set", field="verbosity", value="terse")
    v = session.settings
    assert v["say_area"] == "smallest" and not v["say_zoom_step"] and not v["say_heading"]
    session.run("settings.set", field="verbosity", value="detailed")
    assert v["say_area"] == "whole" and v["say_zoom_step"] and v["say_heading"] and v["say_heading_on_step"]


def test_changing_a_switch_makes_the_preset_custom_and_back(session):
    session.run("settings.set", field="say_heading", value=False)
    assert session.settings["verbosity"] == "custom"
    session.run("settings.set", field="say_heading", value=True)
    assert session.settings["verbosity"] == "normal"


def test_custom_sets_nothing(session):
    session.run("settings.set", field="say_zoom_step", value=False)
    session.run("settings.set", field="verbosity", value="custom")
    assert not session.settings["say_zoom_step"]


def test_a_saved_custom_choice_comes_back(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.run("settings.set", field="say_area", value="off")
    saved = s.save()["settings"]
    again = MapSession(packs=[test_pack], settings=saved)
    assert again.settings["verbosity"] == "custom" and again.settings["say_area"] == "off"
    s.store.close()
    again.store.close()


def test_the_speech_tab_has_the_preset_first_then_its_switches():
    tab = next(t for t in settings_mod.schema()["tabs"] if t["id"] == "speech")
    assert [f["id"] for f in tab["fields"]] == ["verbosity", *settings_mod.PRESET_SWITCHES, "say_place_always"]
    assert set(settings_mod.presets()) == {"terse", "normal", "detailed"}
    for switches in settings_mod.presets().values():
        assert set(switches) == set(settings_mod.PRESET_SWITCHES)


def test_a_goes_to_the_next_preset_and_says_it(session):
    command = registry.by_name("verbosity.next")
    assert command.key == "A" and command.menu == "Speech"
    r = session.press("A")
    assert spoken(r) == ["Detailed. The whole place is said when an area changes, "
                         "and the heading after each step in free facing."]
    assert r.settings_changed and session.settings["verbosity"] == "detailed"
    assert spoken(session.press("A")) == ["Terse. Only the smallest area that changed is said."]
    assert spoken(session.press("A")) == ["Normal. Every area that changed is said, and the zoom, the step "
                                          "and the heading."]


def test_from_custom_a_goes_to_terse(session):
    session.run("settings.set", field="say_heading", value=False)
    session.press("A")
    assert session.settings["verbosity"] == "terse"


def test_without_the_zoom_switch_page_up_only_ticks_and_h_still_says_it(session):
    session.run("settings.set", field="say_zoom_step", value=False)
    r = session.press("Page Up")
    assert spoken(r) == [] and r.earcons == ["tick"] and r.redraw
    r = session.press("Shift+Page Up")
    assert spoken(r) == [] and r.earcons == ["tick"]
    assert "Zoom" in spoken(session.press("H"))[0]


def test_without_the_heading_switch_a_turn_only_ticks(session):
    session.run("settings.set", field="say_heading", value=False)
    session.world.orientation = "free"
    r = session.press("Right")
    assert spoken(r) == [] and r.earcons == ["tick"]
    session.world.orientation = "cardinal"
    r = session.press("Right")
    assert spoken(r) == [] and r.earcons == ["tick"]


def test_the_orientation_and_the_poles_are_always_said(session):
    session.run("settings.set", field="verbosity", value="terse")
    assert spoken(session.press("O")) == ["Cardinal facing, north."]


def test_area_off_says_nothing_after_a_step(session):
    session.run("settings.set", field="say_area", value="off")
    r = session.press("Down")   # into the sea, which normal says
    assert spoken(r) == [] and r.earcons == ["tick"]
    assert spoken(session.press("Space")) == ["North Atlantic Ocean"]   # Where am I is never limited


def test_detailed_says_the_heading_after_every_step_in_free_facing_only(session):
    session.run("settings.set", field="verbosity", value="detailed")
    session.world.orientation = "free"
    session.world.heading = 90.0
    r = session.press("Up")
    said = spoken(r)
    assert said and said[-1].startswith("Facing ") and said[-1].endswith(" degrees.")
    session.world.orientation = "north-fixed"
    session.world.heading = 0.0
    assert not any(s.startswith("Facing") for s in spoken(session.press("Up")))


def test_detailed_heading_after_a_held_run_in_free_facing(test_pack):
    clock = [0.0]
    s = MapSession(packs=[test_pack], saved_state=dict(KENT), clock=lambda: clock[0])
    s.start()
    s.run("settings.set", field="verbosity", value="detailed")
    s.world.orientation = "free"
    s.world.heading = 180.0
    s.press("Up")
    clock[0] = 0.6
    s.run("move.north", held=True, repeat=True)
    said = spoken(s.release())
    assert said[-1].startswith("Facing ")
    s.store.close()


# Always say the place (P2-T17q; ACC-5, ANN-1, ANN-3, DP162) ---------------------------------


@pytest.fixture
def in_kent(test_pack):
    """Kent with a 5 km step, so a step north stays in Kent (25 km leaves it)."""
    s = MapSession(packs=[test_pack], saved_state={**KENT, "step_m": 5000})
    s.start()
    yield s
    s.store.close()


def test_say_the_place_always_is_off_at_first_and_outside_the_presets(session):
    assert session.settings["say_place_always"] is False
    assert "say_place_always" not in settings_mod.PRESET_SWITCHES
    tab = next(t for t in settings_mod.schema()["tabs"] if t["id"] == "speech")
    field = next(f for f in tab["fields"] if f["id"] == "say_place_always")
    assert field["label"] == "Say the place after every step, even when it has not changed"
    assert field["kind"] == "yes_no"


@pytest.mark.parametrize("preset", ["terse", "normal", "detailed"])
def test_the_switch_never_makes_the_preset_custom(session, preset):
    session.run("settings.set", field="verbosity", value=preset)
    session.run("settings.set", field="say_place_always", value=True)
    assert session.settings["verbosity"] == preset
    session.run("settings.set", field="say_place_always", value=False)
    assert session.settings["verbosity"] == preset


@pytest.mark.parametrize("preset, said", [
    ("terse", "Kent"),
    ("normal", "Kent, United Kingdom"),
    ("detailed", "Kent, England, United Kingdom"),
])
def test_with_the_switch_on_a_step_inside_kent_says_the_place(in_kent, preset, said):
    session = in_kent
    session.run("settings.set", field="verbosity", value=preset)
    session.run("settings.set", field="say_place_always", value=True)
    r = session.press("Up")   # still in Kent: without the switch, only the tick
    assert spoken(r)[0] == said and "tick" not in r.earcons


def test_with_the_switch_off_a_step_inside_kent_is_still_only_a_tick(in_kent):
    session = in_kent
    r = session.press("Up")
    assert spoken(r) == [] and r.earcons == ["tick"]


def test_a_step_that_changes_an_area_is_said_as_before(session):
    session.run("settings.set", field="say_place_always", value=True)
    assert spoken(session.press("Down")) == ["North Atlantic Ocean"]


def test_area_off_says_nothing_even_with_the_switch_on(session):
    session.run("settings.set", field="say_area", value="off")
    session.run("settings.set", field="say_place_always", value=True)
    r = session.press("Up")
    assert spoken(r) == [] and r.earcons == ["tick"]


def test_a_held_key_still_clicks_and_says_one_place_on_the_release(test_pack):
    clock = [0.0]
    s = MapSession(packs=[test_pack], saved_state={**KENT, "step_m": 1000}, clock=lambda: clock[0])
    s.start()
    s.run("settings.set", field="say_place_always", value=True)
    first = s.press("Up")
    assert spoken(first) == ["Kent, United Kingdom"]
    for i in range(3):
        clock[0] = 0.6 + i * 0.2
        r = s.run("move.north", held=True, repeat=True)
        assert r.earcons == ["tick"] and not r.announcements
    done = s.release()
    assert spoken(done) == ["Kent, United Kingdom"] and "tick" not in done.earcons
    s.store.close()
