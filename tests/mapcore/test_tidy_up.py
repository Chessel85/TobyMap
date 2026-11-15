"""P3-T19 and P3-T20: fixes and speed from the PO's first pass of the Phase 3 desktop checklist."""
import numpy as np
import pytest

from mapcore.geo import geodesy
from mapcore.session import MapSession

STATION = (50.9074977, -1.4142289)


def test_many_distances_at_once_agree_with_one_at_a_time():
    """P3-T20b: Contains for Europe made 80,000 items one distance at a time."""
    rng = np.random.default_rng(7)
    lats, lons = rng.uniform(-90, 90, 500), rng.uniform(-180, 180, 500)
    lats[:3], lons[:3] = [46.8, -46.8, 0.0], [8.2, -171.8, 98.2]   # here, nearly opposite, and a quarter round
    dist, bear = geodesy.inverse_many(46.8, 8.2, lats, lons)
    for i in range(len(lats)):
        d, b, _ = geodesy.inverse(46.8, 8.2, lats[i], lons[i])
        assert dist[i] == pytest.approx(d, abs=0.001)
        if d > 1:
            assert min(abs(b - bear[i]), 360 - abs(b - bear[i])) < 1e-6


def test_the_world_tree_opens_where_it_last_had_the_focus(continents_pack):
    """P3-T19e, checklist 11.5: until TobyMap closes."""
    s = MapSession(packs=[continents_pack], saved_state={"lat": 46.8, "lon": 8.2, "zoom_m": 250000, "step_m": 25000})
    s.start()
    first = s.run("tree.open").dialog
    assert first["open"] == [] and first["focus"] is None
    europe = s.run("tree.children", id="continent:europe").branch["items"]
    swiss = next(i for i in europe if i["label"].startswith("Switzerland"))
    s.run("tree.at", path=["world", "continent:europe", swiss["id"]])
    again = s.run("tree.open").dialog
    assert [b["id"] for b in again["open"]] == ["continent:europe"] and again["open"][0]["items"] == europe
    assert again["focus"] == swiss["id"]
    s.store.close()


@pytest.mark.parametrize("on", [True, False])
def test_look_around_says_the_direction_only_with_its_setting(test_pack, on):
    """P3-T19f: "A34, north-east, 1.7 kilometres", while in development."""
    s = MapSession(packs=[test_pack], settings={"values": {"look_direction": on}},
                   saved_state={"lat": STATION[0], "lon": STATION[1] - 0.03, "zoom_m": 50000, "step_m": 1000})
    s.start()
    texts = [i["voice"]["text"] for i in s.press("L", "map").scan["items"]]
    s.store.close()
    assert texts and all(t.count(",") == (2 if on else 1) for t in texts)
