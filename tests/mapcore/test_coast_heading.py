"""Bordering's Coast heading from the stored stretches of coast (P3-T30b, INF-2; the PO's answers to P3-T30a).

Each stretch is said like a neighbour, at its nearest point from where you are (P3-T32m), with its length and share of
the coast, and opens to its two ends. Then "Coast of islands", which opens to the islands. A pack without stretches
says the Coast heading as before, its waters.
"""
import shapely

from mapcore import panel as panel_table
from mapcore.geo import geodesy
from mapcore.packs import coords
from mapcore.session import MapSession

WINCHESTER = {"lat": 51.06, "lon": -1.31, "zoom_m": 25000, "step_m": 5000}
HAMPSHIRE_ID = "osm:r172799"
MANCHE_ID = "osm:r7404"


def _session(test_pack, place=WINCHESTER):
    s = MapSession(packs=[test_pack], saved_state=dict(place))
    s.start()
    return s


def _coast(s, *opened):
    g = next(g for g in s.panel(open=["bordering", *opened]) if g["id"] == "bordering")
    return next(i for i in g["items"] if panel_table.is_heading(i["id"]) and i["label"].startswith("Coast, "))


def _stored(s, identifier=HAMPSHIRE_ID):
    return s.store.relationships(identifier)["coast_stretches"]


def test_the_coast_heading_lists_the_stretches_west_to_east_then_the_coast_of_islands(test_pack):
    s = _session(test_pack)
    assert s.current_feature.id == HAMPSHIRE_ID
    stored = _stored(s)
    kids = _coast(s)["children"]
    stretches = [k for k in kids if k["id"].startswith("stretch:")]
    assert len(stretches) == len(stored["stretches"]) >= 2
    assert all(k["label"].startswith("Coast") and k["label"].endswith(" percent") and k["level"] == 2
               for k in stretches)
    wests = [st["ends"][0][0] for st in stored["stretches"]]
    assert wests == sorted(wests)   # west to east
    assert kids[-1]["id"].startswith("coast-islands:") and kids[-1]["label"].startswith("Coast of islands, ")
    assert all(k["expandable"] and "children" not in k for k in kids)   # the ends and islands only when opened
    s.store.close()


def test_a_stretch_names_its_neighbours_and_its_sea(test_pack):
    s = _session(test_pack)
    stored = _stored(s)
    k = next(n for n, st in enumerate(stored["stretches"]) if st["ends"][0][2] and st["ends"][1][2])
    other = s.store.feature(stored["stretches"][k]["ends"][0][2]).name
    item = next(c for c in _coast(s)["children"] if c["id"] == f"stretch:{HAMPSHIRE_ID}:{k}")
    sea = s.store.feature(stored["stretches"][k]["water"]).name
    east = s.store.feature(stored["stretches"][k]["ends"][1][2]).name
    words = f"Coast with {other} at both ends" if other == east else f"Coast from {other} to {east}"
    assert item["label"].startswith(f"{words}, {sea}, ")
    s.store.close()


def test_a_stretch_is_said_at_its_nearest_point_heard_from_there_and_enter_goes_half_way(test_pack):
    s = _session(test_pack)
    stored = _stored(s)
    item = _coast(s)["children"][0]
    st = stored["stretches"][0]
    pts = coords.decode_stretch(st["line"])
    dist, _b = geodesy.inverse_many(s.world.lat, s.world.lon, pts[:, 1], pts[:, 0])
    assert item["distance_m"] <= float(min(dist)) + 1.0   # no further than its nearest stored point
    spot = s._spots[("bordering", item["id"])]
    d, _b2, _ = geodesy.inverse(s.world.lat, s.world.lon, spot[1], spot[2])
    assert abs(d - item["distance_m"]) < 1.0   # Space hears it from that point
    r = s.run("measure.to", item=item["id"], group="bordering")
    assert r.announcements   # Shift+M measures to that point
    half_lon, half_lat = st["half"]
    s.run("panel.go", item=item["id"], group="bordering")
    assert abs(s.world.lat - half_lat) < 1e-6 and abs(s.world.lon - half_lon) < 1e-6
    s.store.close()


def test_a_stretch_opens_to_its_two_ends_west_then_east(test_pack):
    s = _session(test_pack)
    stored = _stored(s)
    k = next(n for n, st in enumerate(stored["stretches"]) if st["ends"][1][2])
    item_id = f"stretch:{HAMPSHIRE_ID}:{k}"
    item = next(c for c in _coast(s, item_id)["children"] if c["id"] == item_id)
    ends = item["children"]
    assert len(ends) == 2 and all(e["level"] == 3 for e in ends)
    east = s.store.feature(stored["stretches"][k]["ends"][1][2]).name
    assert ends[1]["label"].startswith(f"End of the coast, where {east} meets it, ")
    assert all(e["label"].startswith("End of the coast, ") for e in ends)
    lon, lat, _o = stored["stretches"][k]["ends"][1]
    s.run("panel.go", item=ends[1]["id"], group="bordering")   # Enter on an end goes to that end
    assert abs(s.world.lat - lat) < 1e-6 and abs(s.world.lon - lon) < 1e-6
    s.store.close()


def test_coast_of_islands_opens_to_the_islands_with_1_kilometre_of_coast_or_more(test_pack):
    s = _session(test_pack, {"lat": 49.1, "lon": -1.3, "zoom_m": 25000, "step_m": 5000})
    s.set_current_feature(MANCHE_ID)
    item_id = f"coast-islands:{MANCHE_ID}"
    item = next(c for c in _coast(s, item_id)["children"] if c["id"] == item_id)
    islands = item["children"]
    assert islands and all(i["level"] == 3 for i in islands)
    if islands[0]["id"].startswith("heading:"):
        assert islands[0]["label"] == "No island here with 1 kilometre of coast or more."
    else:
        assert all(i["label"].endswith(" round") for i in islands)
        lengths = [i["label"].rsplit(", ", 1)[1] for i in islands]
        assert lengths
    s.store.close()


def test_a_pack_without_stretches_says_the_coast_heading_as_before(test_pack, monkeypatch):
    s = _session(test_pack)
    plain = s.store.relationships

    def without(identifier):
        rel = dict(plain(identifier))
        rel.pop("coast_stretches", None)
        return rel

    monkeypatch.setattr(s.store, "relationships", without)
    kids = _coast(s)["children"]
    assert kids and all(k["label"].endswith(" of coast") for k in kids)   # the waters, as before
    s.store.close()


def test_the_stored_line_reads_back_as_a_line():
    from mapcore.session import stored_line

    line = stored_line(coords.encode_stretch([[-1.5, 50.8], [-1.4, 50.85], [-1.3, 50.8]]))
    assert isinstance(line, shapely.LineString)
    assert shapely.get_coordinates(line).tolist() == [[-1.5, 50.8], [-1.4, 50.85], [-1.3, 50.8]]
