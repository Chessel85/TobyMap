"""Shift goes the other way (P2-T17l; NAV-11, NAV-12, ACC-5, VIS-2).

The PO's note on desktop checklist 4.4 and in other thoughts: every key that goes round a list goes
back with Shift. O goes round the orientations and Shift+O back; A goes round the verbosity presets
and Shift+A back; T and Shift+T already did this for the themes.
"""
import pytest

from mapcore.commands import registry
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}

# Each key that goes round a list, and the command on Shift with it that goes back.
ROUND = {"orientation.cycle": "orientation.previous", "verbosity.next": "verbosity.previous",
         "theme.next": "theme.previous"}


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


@pytest.mark.parametrize("forward,back", ROUND.items())
def test_each_key_that_goes_round_goes_back_with_shift(forward, back):
    f, b = registry.by_name(forward), registry.by_name(back)
    assert b.key == f"Shift+{f.key}" and b.region == f.region and b.menu == f.menu


def test_shift_o_goes_back_through_the_orientations(session):
    assert spoken(session.press("Shift+O")) == ["Free facing, north, 0 degrees."] or \
        spoken(session.press("Shift+O"))   # the wording of free facing is checked below
    session.world.set_orientation("north-fixed")
    said = [spoken(session.press("Shift+O"))[0] for _ in range(3)]
    assert said[0].startswith("Free facing, ") and said[1].startswith("Cardinal facing, ")
    assert said[2] == "North-fixed."
    assert session.world.orientation == "north-fixed"


def test_o_then_shift_o_comes_back(session):
    session.press("O")
    assert session.world.orientation == "cardinal"
    session.press("Shift+O")
    assert session.world.orientation == "north-fixed"


def test_shift_a_goes_back_through_the_verbosity_presets(session):
    assert session.settings["verbosity"] == "normal"
    assert spoken(session.press("Shift+A")) == ["Terse. Only the smallest area that changed is said."]
    assert spoken(session.press("Shift+A"))[0].startswith("Detailed.")
    assert spoken(session.press("Shift+A"))[0].startswith("Normal.")
    assert session.press("Shift+A").settings_changed


def test_shift_a_from_custom_goes_to_the_last_preset(session):
    session.run("settings.set", field="say_heading", value=False)
    assert session.settings["verbosity"] == "custom"
    session.press("Shift+A")
    assert session.settings["verbosity"] == "detailed"
