"""The status line and the move and zoom buttons (P3-T18, VIS-1, SCP-2, ACC-2)."""
import pytest

from mapcore.commands import registry
from mapcore.session import MapSession


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": -1.0})
    s.start()
    return s


def test_the_status_line_says_what_c_and_h_say(session):
    session.run("move.north")
    c = session.run("where.coordinates").announcements[0]["text"]
    h = session.run("where.heading").announcements[0]["text"]
    assert session.controls()["status"] == f"{c}. {h}"


def test_the_status_line_follows_a_step(session):
    before = session.controls()["status"]
    session.run("move.north")
    assert session.controls()["status"] != before


def test_each_button_is_a_command_in_the_registry(session):
    names = [b["name"] for b in session.controls()["buttons"]]
    assert names == ["move.north", "move.south", "move.west", "move.east", "zoom.in", "zoom.out",
                     "step.larger", "step.smaller"]
    for n in names:
        assert registry.by_name(n) and session.handles(n)
    assert all(b["label"] for b in session.controls()["buttons"])


def test_a_button_sends_the_same_command_as_its_key(session):
    session.run("zoom.in")
    after_button = session.controls()["status"]
    session.run("zoom.out")
    session.run("zoom.in")
    assert session.controls()["status"] == after_button


def test_a_setting_hides_both(session):
    assert session.controls()["show"] is True
    session.run("settings.set", field="show_controls", value=False)
    assert session.controls()["show"] is False


def labels(session):
    return {b["name"]: b["label"] for b in session.controls()["buttons"]}


def test_the_move_buttons_are_named_for_what_the_keys_do_now(session):
    assert [labels(session)[n] for n in ("move.north", "move.south", "move.west", "move.east")] == \
        ["North", "South", "West", "East"]
    session.run("orientation.cycle")   # cardinal facing
    assert [labels(session)[n] for n in ("move.north", "move.south", "move.west", "move.east")] == \
        ["Forward", "Back", "Turn left", "Turn right"]
    session.run("orientation.cycle")   # free facing
    assert labels(session)["move.north"] == "Forward"
    session.run("orientation.cycle")   # north-fixed again
    assert labels(session)["move.north"] == "North"
    session.run("mode.toggle")
    assert [labels(session)[n] for n in ("move.north", "move.south", "move.west", "move.east")] == \
        ["Up", "Down", "Previous neighbour", "Next neighbour"]
