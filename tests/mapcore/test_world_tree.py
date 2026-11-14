"""P3-T9: the world tree and browsing by category (SRB-3, SRB-4), on the test pack, which has continents."""
import pytest

from mapcore.session import MapSession

SWITZERLAND = {"lat": 46.95, "lon": 7.45, "zoom_m": 100000, "step_m": 10000}
HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}


@pytest.fixture
def s(continents_pack):
    s = MapSession(packs=[continents_pack], saved_state=dict(SWITZERLAND))
    s.start()
    yield s
    s.store.close()


def labels(items):
    return [i["label"] for i in items]


def branch(s, identifier):
    return s.run("tree.children", id=identifier).branch


def find(items, name):
    return next(i for i in items if i["label"].startswith(name + ","))


def test_w_opens_the_world_tree_from_the_map(s):
    r = s.press("W", "map")
    d = r.dialog
    assert d["kind"] == "tree" and d["title"] == "World tree" and d["cancel"] == "Cancel"
    assert d["root"]["label"] == "World" and d["children"] == "tree.children" and d["go"] == "tree.go"


def test_the_world_holds_the_continents_by_name_with_their_position_as_nvda_says_it(s):
    root = s.run("tree.open").dialog["root"]
    names = labels(root["items"])
    assert names == sorted(names) and "Europe, continent" in names and len(names) == 7
    # World is level 1, the continents level 2: Europe is "level 2, 4 of 7", as the shells' trees count.
    assert names.index("Europe, continent") + 1 == 4


def test_europe_lists_its_countries(s):
    europe = branch(s, "continent:europe")["items"]
    names = [i["label"].split(",")[0] for i in europe]
    assert {"France", "Switzerland", "Germany"} <= set(names) and names == sorted(names, key=str.casefold)
    assert find(europe, "Switzerland")["label"] == "Switzerland, country"


def test_a_country_lists_its_regions_and_distant_parts(s):
    france = find(branch(s, "continent:europe")["items"], "France")
    under = labels(branch(s, france["id"])["items"])
    assert any(x.startswith("Brittany") for x in under)
    assert any(x.startswith("French Guiana") for x in under)   # a distant part is under its sovereign (DP191)


def test_a_constituent_country_is_under_its_country_and_has_its_own_counties(s):
    europe = branch(s, "continent:europe")["items"]
    uk = find(europe, "United Kingdom")
    england = find(branch(s, uk["id"])["items"], "England")
    counties = labels(branch(s, england["id"])["items"])
    assert any(x.startswith("Hampshire") for x in counties) and len(counties) > 20
    assert all(not x.startswith("England,") for x in labels(europe))   # England is not beside the United Kingdom


def test_a_branch_with_nothing_below_says_so(s):
    swiss = find(branch(s, "continent:europe")["items"], "Switzerland")
    b = branch(s, swiss["id"])
    assert b["items"] == [] and b["none"] == "Switzerland has no areas below it in the tree."


def test_enter_on_an_item_goes_there_and_the_world_is_not_a_place(s):
    swiss = find(branch(s, "continent:europe")["items"], "Switzerland")
    r = s.run("tree.go", id=swiss["id"])
    assert r.error is None and s.current_feature.name == "Switzerland"
    assert r.announcements[-1]["text"].startswith("Switzerland")
    assert s.run("tree.go", id="world").error == "The World is the top of the tree. Choose a continent, country or area to go there."
    assert s.run("tree.go", id="osm:nothing").error


@pytest.fixture
def hampshire(continents_pack):
    s = MapSession(packs=[continents_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    hants = s.store.search("Hampshire", 5)
    s.run("tree.go", id=next(f.id for f in hants if f.layer == "counties"))
    yield s
    s.store.close()


def test_browsing_lists_the_kinds_inside_the_current_feature_with_counts(hampshire):
    r = hampshire.press("Ctrl+Shift+F", "map")
    assert r.dialog["kind"] == "choose" and r.dialog["go"] == "browse.choose"
    assert r.dialog["title"] == "Inside Hampshire"
    assert any(line.startswith("Lakes ") for line in r.dialog["lines"])


def test_choosing_lakes_puts_every_lake_in_hampshire_in_the_search_group_whatever_the_zoom(hampshire):
    while hampshire.world.zoom_m > 1000:   # zoomed in, far from the lake, which the zoom does not limit (SRB-4)
        hampshire.run("zoom.in")
    r = hampshire.run("browse.open")
    index = next(i for i, line in enumerate(r.dialog["lines"]) if line.startswith("Lakes "))
    assert hampshire.current_feature.name == "Hampshire"
    said = hampshire.run("browse.choose", index=index)
    assert said.announcements[-1]["text"] == "Lakes: 1 inside Hampshire, in the Search group."
    group = next(g for g in hampshire.panel(open=["search"]) if g["id"] == "search")
    assert [i["label"].split(",")[0] for i in group["items"]] == ["Longbridge Lake"]
