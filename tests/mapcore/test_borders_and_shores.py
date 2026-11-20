"""Borders, shores and coast in the Information panel and Details (P3-T24e, P3-T24f; DP200, DP201, INF-2, INF-5).

The lengths are worked out by the build (relationships: next, coast, shores and outline_km).
"""
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


def _under_lines(session, label_start, *opened):
    """The items under an Overlapping heading for lines (P3-T29e), such as "Lines crossing its border 1"."""
    items = next(g for g in session.panel(open=["overlapping", *opened]) if g["id"] == "overlapping")["items"]
    return next(i for i in items if panel_table.is_heading(i["id"]) and i["label"].startswith(label_start))["children"]


def test_a_line_crossing_the_border_says_how_many_times_and_opens_to_each_crossing(test_pack):
    """P3-T24f, DP201: the River Itchen crosses Southampton's border twice, stored by the build; in Overlapping
    since P3-T29e."""
    s = _session(test_pack, SOUTHAMPTON)
    s.set_current_feature("osm:r127864")
    itchen = next(i for i in _under_lines(s, "Lines crossing its border ") if i["name"] == "River Itchen")
    assert itchen["label"].startswith("River Itchen, crosses twice, nearest ")
    points = next(i for i in _under_lines(s, "Lines crossing its border ", itchen["id"])
                  if i["id"] == itchen["id"])["children"]
    assert [p["label"].split(",")[0] for p in points] == ["Crossing 1 of River Itchen", "Crossing 2 of River Itchen"]
    assert all(p["level"] == 3 for p in points)   # under the line, under its heading
    s.store.close()


def test_a_line_along_the_border_is_said_as_along_not_crossing_it_hundreds_of_times(test_pack):
    s = _session(test_pack, SWITZERLAND)
    s.set_current_feature("osm:r51701")
    rhine = [i["label"] for i in _under_lines(s, "Lines along its border ") if i["name"] == "Rhine"]
    assert rhine and not any("crosses " in label and " times" in label for label in rhine)
    s.store.close()


def _with_near(s, entries):
    """The current feature's stored relationships with these nearly touching areas in place of its own."""
    rel = dict(s.store.relationships(s.current_feature.id), near=entries)
    s.store.relationships = lambda identifier, _rel=rel, _own=s.store.relationships: \
        _rel if identifier == s.current_feature.id else _own(identifier)


def test_an_area_under_5_metres_away_touches_at_a_point_not_0_metres_across(test_pack):
    """P3-T32b, checklist step 15.5: the build keeps a gap to 10 metres, so 0 is a gap under 5 metres, or two
    areas that meet with under 10 metres of border, as Belgium and the Moselle condominium on the river Our."""
    s = _session(test_pack, FRANCE)
    austria, poland = (s.store.search(n, limit=1)[0] for n in ("Austria", "Poland"))
    _with_near(s, [[austria.id, 0.0], [poland.id, 1.3]])
    items = {i["name"]: i["label"] for i in _group(s, "bordering")["items"]}
    assert items["Austria"].endswith(", touches at a point") and "0 metres" not in items["Austria"]
    assert items["Poland"].endswith(", nearly touches, 1.3 kilometres across")
    s.store.close()


def test_hierarchy_across_says_touches_at_a_point_too(test_pack):
    s = _session(test_pack, FRANCE)
    austria = s.store.search("Austria", limit=1)[0]
    _with_near(s, [[austria.id, 0.0]])
    texts = [t for a, t in s._across_cycle()["items"] if a.id == austria.id]
    assert texts == [texts[0]] and texts[0].endswith(", touches at a point") and "0 metres" not in texts[0]
    s.store.close()


# P3-T32c: a shared border stored in parts whose ends meet is one border, and an end is said once. Hampshire and
# West Sussex on the world pack: a 40 km line ending 0.86 m from the start of a 219 m line at Chichester Harbour,
# so three of the four ends were said with the same words.
_HANTS_MAIN = [(-0.7535003, 51.086461), (-0.85, 50.95), (-0.9324943, 50.8460621)]
_HANTS_PIECE = [(-0.9324906, 50.8460547), (-0.9321, 50.8450), (-0.9318987, 50.8441315)]


def test_parts_of_a_shared_border_whose_ends_meet_are_joined_into_one():
    import shapely
    from mapcore.store.store import join_parts

    joined = join_parts([shapely.LineString(_HANTS_MAIN), shapely.LineString(_HANTS_PIECE)])
    assert len(joined) == 1
    coords = shapely.get_coordinates(joined[0])
    assert {tuple(coords[0]), tuple(coords[-1])} == {_HANTS_MAIN[0], _HANTS_PIECE[-1]}
    # the order of the parts and the way each runs make no difference
    again = join_parts([shapely.LineString(_HANTS_PIECE[::-1]), shapely.LineString(_HANTS_MAIN)])
    ends = shapely.get_coordinates(again[0])
    assert len(again) == 1 and {tuple(ends[0]), tuple(ends[-1])} == {_HANTS_MAIN[0], _HANTS_PIECE[-1]}


def test_parts_far_apart_stay_apart_and_a_line_whose_ends_meet_becomes_a_ring():
    import shapely
    from mapcore.store.store import join_parts

    far = join_parts([shapely.LineString(_HANTS_MAIN), shapely.LineString([(-0.90, 50.80), (-0.91, 50.79)])])
    assert len(far) == 2
    ring = join_parts([shapely.LineString([(8.0, 47.0), (8.1, 47.0), (8.1, 47.1), (8.0, 47.1), (8.0, 47.0000005)])])
    assert len(ring) == 1 and shapely.is_closed(ring[0])


def test_ends_where_two_parts_of_one_border_meet_are_not_listed(test_pack):
    """Germany's border with Switzerland, with one of its lines cut in two by a gap of about a metre: the same
    ends as before, none where the two parts meet."""
    import shapely

    s = _session(test_pack, SWITZERLAND)
    s.set_current_feature("osm:r51701")
    germany = next(i for i in _group(s, "bordering")["items"] if i["name"] == "Germany")
    before = sorted(c["label"] for c in _opened(s, "bordering", germany["id"])["children"])
    real = s.store.shared_border
    lines = real(s.store.feature("osm:r51701"), s.store.feature(germany["id"]))
    longest = max(range(len(lines)), key=lambda k: len(shapely.get_coordinates(lines[k])))
    coords = shapely.get_coordinates(lines[longest])
    assert not shapely.is_closed(lines[longest]) and len(coords) > 4
    half = len(coords) // 2
    cut = [shapely.LineString(coords[:half + 1]), shapely.LineString(coords[half:])]
    # a gap of about a metre between the two parts, as in the pack
    second = shapely.get_coordinates(cut[1])
    second[0] = second[0] + (0.00001, 0.0)
    cut[1] = shapely.LineString(second)
    s.store.shared_border = lambda a, b: lines[:longest] + cut + lines[longest + 1:]
    s._panel_cache = None
    after = sorted(c["label"] for c in _opened(s, "bordering", germany["id"])["children"])
    assert after == before
    s.store.close()


def test_an_end_at_the_same_place_as_another_is_said_once(test_pack):
    """Three parts meeting at one point, as where a border forks: that point is one end, not two."""
    import shapely

    s = _session(test_pack, SWITZERLAND)
    s.set_current_feature("osm:r51701")
    germany = next(i for i in _group(s, "bordering")["items"] if i["name"] == "Germany")
    fork = (8.6, 47.65)
    s.store.shared_border = lambda a, b: [shapely.LineString([fork, (8.7, 47.68)]),
                                          shapely.LineString([fork, (8.5, 47.68)]),
                                          shapely.LineString([fork, (8.6, 47.60)])]
    s._panel_cache = None
    kids = _opened(s, "bordering", germany["id"])["children"]
    spots = [s._spots[("bordering", c["id"])][1:3] for c in kids]
    assert len(kids) == 4 and sum(1 for p in spots if abs(p[0] - 47.65) < 1e-6 and abs(p[1] - 8.6) < 1e-6) == 1
    s.store.close()


# P3-T32m, the PO's decision of 20 November 2026: Bordering measures each neighbour, nearly touching area, shore and
# coast to its nearest point from where you stand, as Overlapping and Nearby do, not to its own point. From Winchester,
# West Sussex was said "61 kilometres east", to its own point near Horsham.
WINCHESTER = {"lat": 51.06, "lon": -1.31, "zoom_m": 25000, "step_m": 5000}
IN_WEST_SUSSEX = {"lat": 50.95, "lon": -0.45, "zoom_m": 25000, "step_m": 5000}
HAMPSHIRE_ID, WEST_SUSSEX_ID = "osm:r172799", "osm:r113757"


def _measured(s, identifier):
    return s.store.measure(s.store.feature(identifier), s.world.lat, s.world.lon)


def test_a_neighbour_is_said_at_its_nearest_point_not_its_own_point(test_pack):
    s = _session(test_pack, WINCHESTER)
    items = {i["id"]: i for i in _group(s, "bordering")["items"]}
    sussex, near = items[WEST_SUSSEX_ID], _measured(s, WEST_SUSSEX_ID)
    assert near.distance_m < 45000   # its nearest edge, not its own point 61 kilometres away
    assert abs(sussex["distance_m"] - near.distance_m) < 1000
    distance = words.distance_text(sussex["distance_m"], s._units())
    assert sussex["label"].startswith(f"West Sussex, {distance} ") and ", shared border " in sussex["label"]
    spot = s._spots[("bordering", WEST_SUSSEX_ID)]   # Space hears it from there
    assert abs(spot[1] - near.lat) < 0.02 and abs(spot[2] - near.lon) < 0.02
    assert s.run("panel.hear", item=WEST_SUSSEX_ID, group="bordering").label == f"West Sussex, {distance}"
    s.store.close()


def test_every_bordering_item_is_measured_to_its_nearest_point_and_sorted_by_that_bearing(test_pack):
    s = _session(test_pack, WINCHESTER)
    items = _group(s, "bordering")["items"]
    plain = [i for i in items if not panel_table.is_heading(i["id"])]
    for i in plain + [c for h in items if panel_table.is_heading(h["id"]) for c in h["children"]]:
        near = _measured(s, i["id"])
        assert abs(i["distance_m"] - near.distance_m) < max(1000.0, 0.02 * near.distance_m), i["label"]
    coast = items[-1]["children"]
    assert coast and all(c["distance_m"] < 50000 for c in coast)   # the sea off Hampshire, not 3,880 km away
    bearings = [i["bearing_deg"] for i in plain]
    assert bearings == sorted(bearings)
    s.store.close()


def test_enter_on_a_neighbour_still_goes_to_its_own_point(test_pack):
    """As Enter on an Overlapping item does: the nearest point is for the words and Space only."""
    s = _session(test_pack, WINCHESTER)
    _group(s, "bordering")
    lat, lon = s._point_of(s.store.feature(WEST_SUSSEX_ID))
    s.run("panel.go", item=WEST_SUSSEX_ID, group="bordering")
    assert abs(s.world.lat - lat) < 1e-6 and abs(s.world.lon - lon) < 1e-6
    assert s.current_feature.id == WEST_SUSSEX_ID
    s.store.close()


def test_a_neighbour_you_are_inside_says_so(test_pack):
    s = _session(test_pack, IN_WEST_SUSSEX)
    s.set_current_feature(HAMPSHIRE_ID)
    sussex = next(i for i in _group(s, "bordering")["items"] if i["id"] == WEST_SUSSEX_ID)
    assert sussex["label"].startswith("West Sussex, you are inside, shared border ")
    texts = [t for a, t in s._across_cycle()["items"] if a.id == WEST_SUSSEX_ID]
    assert texts and texts[0].startswith("West Sussex, you are inside, shared border ")
    s.store.close()


def test_hierarchy_across_says_the_direction_of_the_nearest_point_in_bordering_order(test_pack):
    s = _session(test_pack, WINCHESTER)
    items = [i for i in _group(s, "bordering")["items"] if not panel_table.is_heading(i["id"])]
    cycle = s._across_cycle()["items"]
    assert [a.id for a, _t in cycle] == [i["id"] for i in items]
    near = _measured(s, WEST_SUSSEX_ID)
    text = next(t for a, t in cycle if a.id == WEST_SUSSEX_ID)
    assert text.startswith(f"West Sussex, {words.direction_text(near.bearing_deg, s.settings['bearing'], None)}, ")
    s.store.close()
