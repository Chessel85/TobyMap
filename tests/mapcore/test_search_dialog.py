"""P3-T8c and P3-T8d: the search dialog's commands and narrowing choice (SRB-1, SRB-2, NAV-8, ACC-7)."""
import pytest

from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}
PARIS, PARIS_TEXAS = "osm:n17807753", "osm:n105715620"
SAO_PAULO_CITY = "osm:n30674098"


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


def test_ctrl_f_opens_the_search_dialog_from_anywhere(s):
    for region in ("map", "panel", "details"):
        r = s.press("Ctrl+F", region)
        assert r.dialog["kind"] == "search" and r.dialog["cancel"] == "Cancel"
        assert r.dialog["query"] == "search.query" and r.dialog["go"] == "search.go"


def test_the_choice_beside_the_field_has_everywhere_inside_near_and_each_layer(s):
    scopes = s.run("search.open").dialog["scopes"]
    ids = [x["id"] for x in scopes]
    assert ids[:3] == ["all", "inside", "near"]
    assert scopes[0]["label"] == "Everywhere"
    assert scopes[1]["label"] == f"Inside {s.current_feature.name}"
    assert scopes[2]["label"].startswith("Near here, within ")
    assert any(i.startswith("layer:") for i in ids)
    assert any(x["label"].startswith("Only ") for x in scopes)


def test_typing_gives_lines_and_identifiers_and_fills_the_search_group(s):
    found = s.run("search.query", text="Sao Paulo", scope="all").found
    assert SAO_PAULO_CITY in found["ids"] and len(found["lines"]) == len(found["ids"]) and found["none"] == ""
    group = next(g for g in s.panel(open=["search"]) if g["id"] == "search")
    assert len(group["items"]) == len(found["ids"]) and group["items"][0]["label"].startswith("São Paulo")
    s.run("search.query", text="", scope="all")   # a new search replaces the group's items
    assert next(g for g in s.panel() if g["id"] == "search")["items"] == []


def test_nothing_found_says_so_from_the_templates(s):
    found = s.run("search.query", text="qqzzxx", scope="all").found
    assert found["ids"] == [] and found["none"] == "Nothing found for qqzzxx."


def test_an_empty_field_gives_nothing_and_no_words(s):
    s.run("search.query", text="Paris", scope="all")
    found = s.run("search.query", text="  ", scope="all").found
    assert found == {"lines": [], "ids": [], "none": ""} and s.search_found == {}


def test_one_layer_narrows_the_results(s):
    everywhere = s.run("search.query", text="Paris", scope="all").found["ids"]
    layer = s.search_found[PARIS].layer
    only = s.run("search.query", text="Paris", scope=f"layer:{layer}").found["ids"]
    assert PARIS in only and set(only) <= set(everywhere)
    other = next(l.id for l in s.layers.layers() if l.id != layer)
    assert PARIS not in s.run("search.query", text="Paris", scope=f"layer:{other}").found["ids"]


def test_near_leaves_out_places_far_away(s):
    found = s.run("search.query", text="Paris", scope="near").found
    assert PARIS not in found["ids"] and PARIS_TEXAS not in found["ids"]


def test_inside_the_current_feature_is_passed_on(s):
    r = s.run("search.query", text="Southampton", scope="inside")
    assert r.found is not None   # the narrowing itself is Store.search's, tested in test_search.py


def test_enter_goes_to_the_result_and_alt_comma_comes_back(s):
    found = s.run("search.query", text="Sao Paulo", scope="all").found
    r = s.run("search.go", id=SAO_PAULO_CITY)
    assert not r.error and s.current_feature.id == SAO_PAULO_CITY
    s.press("Alt+,", "map")
    assert abs(s.world.lat - HAMPSHIRE["lat"]) < 1e-6
    assert found["ids"]


def test_going_to_something_not_found_is_refused(s):
    s.run("search.query", text="Paris", scope="all")
    assert s.run("search.go", id="osm:n1").error


def test_run_many_keeps_the_found_results(s):
    r = s.run_many([("search.query", {"text": "Paris", "scope": "all"})])
    assert r.found and PARIS in r.found["ids"]
