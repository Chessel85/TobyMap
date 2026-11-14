"""P3-T10a: the query builder in the core (INF-9). Find a layer, a relation, and of what; the answer goes into the
Search group under a heading such as "Rivers crossing Germany, 1 item", from the stored relationships.

The test pack's rivers are the Rhine from Basel to Schaffhausen and the River Itchen, so "rivers crossing Germany"
finds the Rhine; the Danube is checked by hand on the world pack."""
import pytest

from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}
GERMANY, SWITZERLAND, RHINE = "osm:r51477", "osm:r51701", "osm:r123924"
HAMPSHIRE_ID, ISLE_OF_WIGHT, SOUTHAMPTON = "osm:r172799", "osm:r154350", "osm:r127864"


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


def search_group(s):
    return next(g for g in s.panel(open={"search"}) if g["id"] == "search")


def ask(s, layer, relation, of, distance=""):
    return s.run("query.run", layer=layer, relation=relation, of=of, distance=distance)


def names(s):
    return [i["name"] for i in search_group(s)["items"]]


def test_rivers_crossing_germany_include_the_rhine_and_go_into_the_search_group(s):
    r = ask(s, "rivers", "crossing", GERMANY)
    assert r.error is None and r.panel_stale
    assert r.announcements[-1]["text"] == "Rivers crossing Germany: 1, in the Search group."
    group = search_group(s)
    assert group["label"] == "Rivers crossing Germany, 1 item"
    assert names(s) == ["Rhine"]
    # Enter on an answer goes there, as on a search result.
    assert s.run("search.go", id=RHINE).error is None and s.current_feature.id == RHINE


def test_a_query_with_nothing_found_says_so_and_keeps_the_form_open(s):
    ask(s, "rivers", "crossing", GERMANY)
    r = ask(s, "lakes", "crossing", GERMANY)
    assert r.error == "No lakes crossing Germany."
    assert names(s) == ["Rhine"]   # the Search group keeps the last answer


def test_towns_within_a_distance_of_the_current_feature(s):
    # Newport on the Isle of Wight is about 10 km across the Solent from Hampshire's coast.
    assert ask(s, "towns", "near", HAMPSHIRE_ID, "10").error == "No cities and towns within 10 kilometres of Hampshire."
    r = ask(s, "towns", "near", HAMPSHIRE_ID, "20")
    assert r.error is None
    assert search_group(s)["label"] == "Cities and towns within 20 kilometres of Hampshire, 1 item"
    [item] = search_group(s)["items"]
    assert item["label"].startswith("Newport, 10 kilometres from Hampshire, ")
    # Inside counts as no distance: the Isle of Wight's Newport, not the one in Wales.
    s.run("search.query", text="Isle of Wight")
    assert s.run("search.go", id=ISLE_OF_WIGHT).error is None
    d = s.run("query.open").dialog
    assert d["of"][0] == {"id": ISLE_OF_WIGHT, "label": "Isle of Wight, the current feature"}
    assert ask(s, "towns", "near", ISLE_OF_WIGHT, "10").error is None
    [item] = search_group(s)["items"]
    assert item["id"] == "osm:n2386521" and item["label"].startswith("Newport, ")
    assert "kilometres from" not in item["label"]


def test_within_a_distance_is_nearest_first_with_each_distance(s):
    ask(s, "counties", "near", ISLE_OF_WIGHT, "20")
    labels = [i["label"] for i in search_group(s)["items"]]
    assert labels[0].startswith("Hampshire, 1.3 kilometres from the Isle of Wight")
    assert [x.split(",")[0] for x in labels] == ["Hampshire", "Portsmouth", "Bournemouth", "West Sussex", "Southampton"]


def test_stations_within_a_distance_of_a_county(s):
    ask(s, "stations", "near", SOUTHAMPTON, "10")
    assert names(s) == ["Southampton Central"]
    ask(s, "stations", "near", SOUTHAMPTON, "20")
    assert names(s) == ["Southampton Central", "Brockenhurst"]


def test_countries_bordering_switzerland(s):
    ask(s, "countries", "bordering", SWITZERLAND)
    assert search_group(s)["label"] == "Countries bordering Switzerland, 5 items"
    assert sorted(names(s)) == ["Austria", "France", "Germany", "Italy", "Liechtenstein"]


def test_inside_uses_the_stored_relationships(s):
    ask(s, "stations", "inside", HAMPSHIRE_ID)
    assert names(s) == ["Brockenhurst"]   # Southampton Central is in Southampton, not the county of Hampshire
    assert search_group(s)["label"] == "Railway stations inside Hampshire, 1 item"


def test_the_areas_a_line_crosses_are_in_order_from_its_start(s):
    r = ask(s, "countries", "crossing", RHINE)
    assert r.announcements[-1]["text"] == "Countries crossed by Rhine: 3, in the Search group."
    assert names(s) == ["Switzerland", "Germany", "France"]


def test_the_form_has_three_lists_with_no_field_names(s):
    d = s.run("query.open").dialog
    assert d["kind"] == "query" and d["ok"] == "OK" and d["cancel"] == "Cancel" and d["run"] == "query.run"
    assert [r["label"] for r in d["relations"]] == ["inside", "crossing", "bordering", "within a distance of"]
    assert [r["distance"] for r in d["relations"]] == [False, False, False, True]
    assert {"id": "rivers", "label": "Rivers"} in d["layers"]
    assert d["distance_label"] == "Distance in kilometres"
    # A feature in the Search group can be asked about too.
    s.run("search.query", text="Switzerland")
    of = s.run("query.open").dialog["of"]
    assert of[0]["label"] == "Hampshire, the current feature"
    assert any(o["id"] == SWITZERLAND and o["label"].endswith(", from the Search group") for o in of)
    # Every word shown is the core's, with no identifier or field name.
    for line in [o["label"] for o in of] + [x["label"] for x in d["layers"]]:
        assert "osm:" not in line and "_" not in line


def test_a_distance_must_be_a_number_above_nothing(s):
    for bad in ("", "0", "-3", "ten"):
        assert ask(s, "towns", "near", HAMPSHIRE_ID, bad).error == "Type a distance greater than 0, such as 10."
    assert ask(s, "nowhere", "inside", HAMPSHIRE_ID).error == "Choose what to find, the relation and the feature."
    assert ask(s, "towns", "inside", "osm:nothing").error == "Choose what to find, the relation and the feature."


def test_imperial_units_ask_in_miles(s):
    s.run("settings.set", field="units", value="imperial")
    assert s.run("query.open").dialog["distance_label"] == "Distance in miles"
    ask(s, "stations", "near", SOUTHAMPTON, "10")   # 16 km
    assert names(s) == ["Southampton Central", "Brockenhurst"]


def test_a_search_afterwards_takes_back_the_search_group_heading(s):
    ask(s, "rivers", "crossing", GERMANY)
    s.run("search.query", text="Switzerland")
    assert search_group(s)["label"].startswith("Search, ")


def test_with_no_feature_to_ask_about_the_form_does_not_open(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 0.0, "lon": -160.0, "zoom_m": 1000, "step_m": 100})
    s.start()
    try:
        assert s.current_feature is None   # the test pack has no ocean in the Pacific
        r = s.run("query.open")
        assert r.dialog is None
        assert r.announcements[-1]["text"] == "No feature to ask about. Go to one, or search for one first."
    finally:
        s.store.close()
