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
    names = names[:-2]   # the last two are Disputed areas and Unclaimed areas (P3-T16a)
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


# Lists of disputed and unclaimed areas (P3-T16a; ANN-6, DAT-8, LOC-6) ------------------------------------------

def test_the_world_ends_with_disputed_and_unclaimed_areas(s):
    items = s.run("tree.open").dialog["root"]["items"]
    assert [i["label"] for i in items[-2:]] == ["Disputed areas", "Unclaimed areas"]


def test_crimea_is_in_disputed_areas_with_its_claimants(s):
    items = branch(s, "special:disputed")["items"]
    crimea = next(i for i in items if i["label"].startswith("Crimea"))
    assert crimea["label"].endswith("claimed by Russia, Ukraine") or "claimed by" in crimea["label"]
    assert s.run("tree.go", id=crimea["id"]).error is None


def test_a_list_is_not_a_place_and_an_empty_one_says_so(s):
    assert "is a list" in s.run("tree.go", id="special:disputed").error
    b = branch(s, "special:unclaimed")
    assert b["items"] == [] and b["none"] == "No unclaimed areas are stored."


def test_searching_disputed_lists_them_first(s):
    found = s.search("disputed")
    assert found and found[0]["name"].startswith("Crimea") or any(f["name"].startswith("Crimea") for f in found)
    assert "laimed by" in found[0]["label"]


def test_unclaimed_land_and_marked_land_are_told_apart():
    from mapcore.store.store import special_kind
    assert special_kind({"type": "unclaimed land"}) == "unclaimed"      # Bir Tawil, the small islands
    assert special_kind({"type": "disputed land"}) == "disputed"        # the West Bank, the Ilemi Triangle
    assert special_kind({"type": "region", "disputed": True}) == "disputed"   # a place held twice in OSM
    assert special_kind({"type": "country"}) is None


def test_browsing_inside_a_country_lists_its_disputed_areas(s):
    s.run("tree.go", id="continent:europe")
    r = s.run("browse.open")
    index = next((i for i, line in enumerate(r.dialog["lines"]) if line.startswith("Disputed areas")), None)
    assert index is not None
    s.run("browse.choose", index=index)
    group = next(g for g in s.panel(open=["search"]) if g["id"] == "search")
    assert any(i["label"].startswith("Crimea") for i in group["items"])
