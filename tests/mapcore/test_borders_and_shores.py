"""Borders, shores and coast in the Information panel and Details (P3-T24e, P3-T24f; DP200, DP201, INF-2, INF-5).

The lengths are worked out by the build (relationships: next, coast, shores and outline_km).
"""
import pytest

from mapcore.describe import words
from mapcore import panel as panel_table
from mapcore.session import MapSession

SWITZERLAND = {"lat": 46.8, "lon": 8.2, "zoom_m": 250000, "step_m": 25000}
FRANCE = {"lat": 46.5, "lon": 2.5, "zoom_m": 250000, "step_m": 25000}
LONGBRIDGE_LAKE = {"lat": 50.9566, "lon": -1.4882, "zoom_m": 1000, "step_m": 100}


def _session(test_pack, place):
    s = MapSession(packs=[test_pack], saved_state=dict(place))
    s.start()
    return s


def _group(session, gid):
    return next(g for g in session.panel(open=[gid]) if g["id"] == gid)


def test_each_neighbour_says_its_share_of_the_whole_border(test_pack):
    s = _session(test_pack, SWITZERLAND)
    items = _group(s, "bordering")["items"]
    italy = next(i for i in items if i["name"] == "Italy")
    assert italy["label"].startswith("Italy, ") and ", shared border " in italy["label"]
    assert italy["label"].endswith(" percent")
    shares = [int(i["label"].rsplit(", ", 1)[1].split()[0]) for i in items if i["label"].endswith(" percent")]
    assert 97 <= sum(shares) <= 103   # a landlocked country's borders are all of its outline
    s.store.close()


def test_a_country_on_the_sea_lists_its_coast_under_a_heading_after_its_neighbours(test_pack):
    s = _session(test_pack, FRANCE)
    items = _group(s, "bordering")["items"]
    coast = items[-1]
    assert panel_table.is_heading(coast["id"]) and coast["label"].startswith("Coast, ")
    names = [c["name"] for c in coast["children"]]
    assert "Bay of Biscay" in names
    assert "North Atlantic Ocean" not in names   # the wider water is left out (P3-T28b)
    assert coast["label"].startswith("Coast, ") and coast["label"].endswith(" kilometres")
    biscay = next(c for c in coast["children"] if c["name"] == "Bay of Biscay")
    assert biscay["label"].endswith(" of coast") and biscay["level"] == 2
    assert not any(panel_table.is_heading(i["id"]) for i in items[:-1])
    s.store.close()


def test_ctrl_s_sorts_the_neighbours_and_keeps_the_coast_heading_last(test_pack):
    s = _session(test_pack, FRANCE)
    _group(s, "bordering")
    s.panel_at_group = "bordering"
    s.run("panel.sort")   # by name
    items = _group(s, "bordering")["items"]
    plain = [i["name"] for i in items if not panel_table.is_heading(i["id"])]
    assert plain == sorted(plain, key=str.casefold)
    assert panel_table.is_heading(items[-1]["id"])
    s.store.close()


def test_a_lake_lists_the_land_round_it_as_shores_by_layer_and_not_in_overlapping(test_pack):
    s = _session(test_pack, LONGBRIDGE_LAKE)
    lake = next(a for a in s.areas if a.layer == "lakes")
    s.set_current_feature(lake.id)
    items = _group(s, "bordering")["items"]
    headings = [i["label"] for i in items if panel_table.is_heading(i["id"])]
    assert "Shores, Counties 1" in headings and "Shores, Countries 1" in headings
    counties = next(i for i in items if i["label"] == "Shores, Counties 1")
    assert counties["children"][0]["name"] == "Hampshire"
    assert counties["children"][0]["label"].endswith(" of shore")
    overlapping = _group(s, "overlapping")["items"]
    assert "Hampshire" not in [c["name"] for i in overlapping for c in panel_table.walk([i])]
    s.store.close()


def test_details_gives_the_whole_border_land_and_coast(test_pack):
    s = _session(test_pack, FRANCE)
    lines = s.details().split("\n")
    border = next(line for line in lines if line.startswith("Whole border: "))
    assert ", of which land is " in border and " and coastline is " in border
    s.store.close()


def test_the_border_line_counts_the_coast_as_the_coast_heading_does(test_pack):
    s = _session(test_pack, FRANCE)
    rel = s.store.relationships(s.areas[0].id)
    whole = s._coast_of(rel, visible_only=False)[2]
    if whole:
        assert f"coastline is {words.distance_text(whole * 1000.0, s.settings['units'])}" in s.details()
    s.store.close()


def test_overlapping_is_under_a_heading_for_each_kind(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.87, "lon": -1.6, "zoom_m": 25000, "step_m": 5000})
    s.start()
    park = next(a for a in s.store.at(50.87, -1.6) if a.layer == "national_parks")
    s.set_current_feature(park.id)
    items = _group(s, "overlapping")["items"]
    assert items and all(panel_table.is_heading(i["id"]) for i in items)
    assert any(i["label"].startswith("Counties ") for i in items)
    s.store.close()


SOUTHAMPTON = {"lat": 50.91, "lon": -1.40, "zoom_m": 25000, "step_m": 5000}


def _opened(session, gid, item_id):
    return next(i for i in next(g for g in session.panel(open=[gid, item_id]) if g["id"] == gid)["items"]
                if i["id"] == item_id)


def test_a_neighbour_opens_to_the_ends_of_the_shared_border_and_what_is_there(test_pack):
    """P3-T24f, DP201: Switzerland and Germany: an end where France meets them, one where Austria does, and
    Buesingen, a German exclave inside Switzerland, a stretch with no ends."""
    s = _session(test_pack, SWITZERLAND)
    s.set_current_feature("osm:r51701")
    germany = next(i for i in _group(s, "bordering")["items"] if i["name"] == "Germany")
    assert germany["expandable"] and "children" not in germany   # worked out only when opened
    ends = [c["label"] for c in _opened(s, "bordering", germany["id"])["children"]]
    assert any(e.startswith("End of the border with Germany, where France meets it, ") for e in ends)
    assert any(e.startswith("End of the border with Germany, where Austria meets it, ") for e in ends)
    assert any(e.startswith("A stretch with no ends, ") and " round, nearest point " in e for e in ends)
    s.store.close()


def _end_bearings(s, children):
    from mapcore.geo import geodesy

    out = []
    for c in children:
        spot = s._spots[("bordering", c["id"])]
        out.append(geodesy.inverse(s.world.lat, s.world.lon, spot[1], spot[2])[1] % 360.0)
    return out


def test_the_ends_are_in_order_clockwise_from_north_or_from_ahead(test_pack):
    """P3-T28i: by the bearing the words are made from."""
    s = _session(test_pack, SWITZERLAND)
    s.set_current_feature("osm:r51701")
    germany = next(i for i in _group(s, "bordering")["items"] if i["name"] == "Germany")
    kids = _opened(s, "bordering", germany["id"])["children"]
    assert len(kids) >= 3
    b = _end_bearings(s, kids)
    assert b == sorted(b)   # compass: north first, round to north-west
    s.world.orientation, s.world.heading = "free", 200.0
    s.run("settings.set", field="relative_directions", value=True)
    kids = _opened(s, "bordering", germany["id"])["children"]
    rel = [(x - 200.0) % 360.0 for x in _end_bearings(s, kids)]
    assert rel == sorted(rel)   # clockwise from ahead
    s.store.close()


def test_enter_on_an_end_goes_to_that_point(test_pack):
    s = _session(test_pack, SWITZERLAND)
    s.set_current_feature("osm:r51701")
    germany = next(i for i in _group(s, "bordering")["items"] if i["name"] == "Germany")
    end = next(c for c in _opened(s, "bordering", germany["id"])["children"] if "Austria" in c["label"])
    r = s.run("panel.go", item=end["id"], group="bordering")
    assert abs(s.world.lat - 47.54) < 0.05 and abs(s.world.lon - 9.56) < 0.05
    assert r.announcements
    s.store.close()


@pytest.mark.skip(reason="The Crossing group went in P3-T29a; its content comes back in Overlapping in P3-T29e")
def test_a_line_crossing_the_border_says_how_many_times_and_opens_to_each_crossing(test_pack):
    """P3-T24f, DP201: the River Itchen crosses Southampton's border twice, stored by the build."""
    s = _session(test_pack, SOUTHAMPTON)
    s.set_current_feature("osm:r127864")
    itchen = next(i for i in _group(s, "crossing")["items"] if i["name"] == "River Itchen")
    assert itchen["label"].startswith("River Itchen, crosses twice, nearest ")
    points = _opened(s, "crossing", itchen["id"])["children"]
    assert [p["label"].split(",")[0] for p in points] == ["Crossing 1 of River Itchen", "Crossing 2 of River Itchen"]
    assert all(p["level"] == 2 for p in points)
    s.store.close()


@pytest.mark.skip(reason="The Crossing group went in P3-T29a; its content comes back in Overlapping in P3-T29e")
def test_a_line_along_the_border_is_said_as_along_not_crossing_it_hundreds_of_times(test_pack):
    s = _session(test_pack, SWITZERLAND)
    s.set_current_feature("osm:r51701")
    rhine = [i["label"] for i in _group(s, "crossing")["items"] if i["name"] == "Rhine"]
    assert rhine and not any("crosses " in label and " times" in label for label in rhine)
    s.store.close()
