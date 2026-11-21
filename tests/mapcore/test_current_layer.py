"""The current layer, set with Shift+Enter (P3-T24b, DP202; LOC-4, INF-10).

Shift+Enter on an item makes its layer the current layer, and its feature the current feature. As you step,
the current feature stays in that layer. Where the layer has nothing, it goes back to the smallest area, and
the status line says so. Shift+Enter on the smallest area goes back to the usual rule.
"""
import pytest

from mapcore.commands import registry
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.0, "zoom_m": 25000, "step_m": 25000}


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


def _within(session, name):
    area = next(a for a in session.areas if a.name == name)
    session.panel()
    session.run("panel.select", item=area.id, group="within")
    return area


def test_shift_enter_in_the_panel_is_the_current_layer_command():
    command = registry.by_name("panel.current_layer")
    assert registry.default_key(command.name) == "Shift+Enter" and command.region == "panel"


def test_shift_enter_on_england_makes_regions_the_current_layer_and_it_follows_you(session):
    _within(session, "England")
    r = session.run("panel.current_layer")
    assert spoken(r) == ["Current layer: Regions and constituent countries. England is the current feature."]
    assert session.current_feature.name == "England" and r.panel_stale and r.details_stale
    # Step west, into other counties: the current feature stays England, not the county.
    for _ in range(4):
        session.run("move.west")
    assert session.areas and session.current_feature.name == "England"
    assert session.areas[0].name != "England"   # what is said does not change: the county first


def test_where_the_current_layer_has_nothing_the_smallest_area_is_current_and_the_status_line_says_so(session):
    _within(session, "England")
    session.run("panel.current_layer")
    for _ in range(3):
        session.run("move.east")   # out into the sea, where there is no region
    assert session.areas[0].layer in ("oceans", "seas")
    assert session.current_feature.id == session.areas[0].id
    assert session.controls()["status"].endswith("Regions and constituent countries: none here.")
    for _ in range(3):
        session.run("move.west")   # back onto the land: picked up again
    assert session.current_feature.name == "England"
    assert "none here" not in session.controls()["status"]


def test_shift_enter_on_the_smallest_area_goes_back_to_the_usual_rule(session):
    """P4-T14d, the PO's note on checklist step 6.3: the first time, even with another layer current."""
    _within(session, "England")
    session.run("panel.current_layer")
    _within(session, "Kent")
    r = session.run("panel.current_layer")
    assert spoken(r) == ["No current layer. The current feature is the smallest area here, Kent."]
    assert session.current_layer is None and session.current_feature.name == "Kent"
    r = session.run("panel.current_layer")   # Kent again: still the usual rule
    assert spoken(r) == ["No current layer. The current feature is the smallest area here, Kent."]
    assert session.current_layer is None


def test_shift_enter_on_a_larger_area_still_makes_its_layer_current(session):
    _within(session, "Kent")
    session.run("panel.current_layer")
    _within(session, "England")
    r = session.run("panel.current_layer")
    assert spoken(r) == ["Current layer: Regions and constituent countries. England is the current feature."]


def test_a_zoom_that_changes_what_space_says_moves_the_current_feature_with_it(session):
    """P4-T14d, the PO's note on checklist step 14.1: a feature made current here at 25 kilometres is let go when
    a zoom changes what Space says, so the current feature is the first area Space now says."""
    kent = session.areas[0]
    session.set_current_feature(kent.id)
    while session.world.zoom_m < 2500000:
        before = session._place_text()
        session.run("zoom.out")
        if session._place_text() == before:
            continue
        assert session.current_feature.id == session._first_said_here().id
    assert session.current_feature.id != kent.id
    heading = next(g for g in session.panel(open={"bordering"}) if g["id"] == "bordering")["label"]
    assert heading.startswith("Bordering " + session._first_said_here().name)


def test_a_zoom_that_leaves_what_space_says_alone_keeps_the_current_feature(session):
    england = next(a for a in session.areas if a.name == "England")
    session.set_current_feature(england.id)
    before = session._place_text()
    session.run("zoom.out")
    if session._place_text() == before:
        assert session.current_feature.id == england.id


def test_the_current_layer_is_followed_at_any_zoom(session):
    _within(session, "England")
    session.run("panel.current_layer")
    session.world.zoom_index = session.world.zoom_list.index(2500000)   # beyond the regions' zoom range
    session.areas = session._here()
    assert "England" not in [a.name for a in session.areas]
    assert session.current_feature.name == "England"


def test_shift_enter_on_nothing_says_to_choose_an_item(session):
    session.panel_on_item = False
    r = session.run("panel.current_layer")
    assert spoken(r) == ["Choose an item in the Information panel first."]
