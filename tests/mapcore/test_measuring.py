"""P3-T7a: measuring from where you are to a feature (INF-3). Nothing moves you."""
import pytest

from mapcore.commands import registry
from mapcore.geo import geodesy
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


def test_shift_m_is_the_key():
    assert registry.command_for_key("web", "Shift+M", "map").name == "measure.to"
    assert registry.command_for_key("desktop", "Shift+M", "panel").name == "measure.to"
    assert registry.command_for_key("web", "M", "map").name == "mode.toggle"


def test_inside_an_area_it_is_the_distance_to_its_border(s):
    here = (s.world.lat, s.world.lon)
    hampshire = next(a for a in s.areas if a.name == "Hampshire")
    near = s.store.measure(hampshire, *here, border=True)
    assert near.inside and near.distance_m > 100
    # the point found is on the border: nothing of Hampshire's border is nearer than it
    r = s.press("Shift+M", "map")
    assert (s.world.lat, s.world.lon) == here
    assert "its border" in said(s.run("measure.to", item=hampshire.id, group="within"))
    assert geodesy.distance_m(*here, near.lat, near.lon) == pytest.approx(near.distance_m, abs=1)


def test_to_a_feature_you_are_not_in_it_is_the_nearest_point(s):
    near = s.store.nearby(s.world.lat, s.world.lon, 200_000, limit=30, exclude={a.id for a in s.areas})
    assert near, "something lies within 200 km of Hampshire in the test pack"
    r = s.measure_to(near[0].area)
    assert "nearest point" in said(r) and near[0].area.name in said(r)


def test_the_centre_can_be_chosen_in_the_units_tab(s):
    s.settings.set("measure_to", "centre")
    hampshire = next(a for a in s.areas if a.name == "Hampshire")
    assert said(s.run("measure.to", item=hampshire.id, group="within")).startswith("Hampshire, centre ")


def test_with_no_item_it_measures_to_the_current_feature(s):
    assert s.current_feature.name in said(s.run("measure.to"))


def test_london_to_paris_is_344_km_at_148_degrees():
    d, b, _ = geodesy.inverse(51.507, -0.128, 48.857, 2.352)
    assert d / 1000 == pytest.approx(344, abs=1) and b == pytest.approx(148, abs=1)
