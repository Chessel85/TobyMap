"""Tiers, and constituent countries (P3-T17, DP165; NAV-4, LOC-2, LOC-3, VIS-1).

England, Scotland, Wales and Northern Ireland are constituent countries of the United
Kingdom, a tier between country and county, though OSM gives them level 4 as it does the
French regions. Each area's tier is in its record, from the tiers record of the writing
stage. Details says it; the order of the areas at a point uses it; and the regions are
not painted on the map unless "Draw the borders of regions" is on.
"""
import pytest

from mapcore.session import MapSession
from mapcore.store.store import Area, most_specific_first

BASINGSTOKE = {"lat": 51.27, "lon": -1.09, "zoom_m": 25000, "step_m": 25000}   # Hampshire, England
ENGLAND, BRITTANY, HAMPSHIRE, UK = "osm:r58447", "osm:r102740", "osm:r172799", "osm:r62149"


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(BASINGSTOKE))
    s.start()
    yield s
    s.store.close()


def details_type(session, item):
    session.run("panel.select", item=item)
    return next(line for line in session.details().splitlines() if line.startswith("Type: "))


def test_each_area_has_its_tier_and_the_pack_lists_the_tiers(session):
    assert session.store.tiers == ["country", "constituent_country", "region", "county"]
    tier = {i: session.store.feature(i).record["tier"] for i in (UK, ENGLAND, BRITTANY, HAMPSHIRE)}
    assert tier == {UK: "country", ENGLAND: "constituent_country", BRITTANY: "region", HAMPSHIRE: "county"}


def test_in_hampshire_within_lists_hampshire_england_and_the_united_kingdom_in_order(session):
    # The test pack has no continents layer; on the world pack Europe follows (mapdata inspect).
    within = [i["label"].split(",")[0] for g in session.panel() if g["id"] == "within" for i in g["items"]]
    assert within == ["Hampshire", "England", "United Kingdom"]
    assert spoken(session.press("Space")) == ["Hampshire, England, United Kingdom"]


def test_englands_details_say_constituent_country_of_the_united_kingdom(session):
    assert details_type(session, ENGLAND) == "Type: constituent country of the United Kingdom"


def test_brittanys_details_say_region_of_france(session):
    assert details_type(session, BRITTANY) == "Type: region of France"


def test_hampshires_details_say_county_of_england(session):
    assert details_type(session, HAMPSHIRE) == "Type: county of England"


def test_a_countrys_details_say_country(session):
    assert details_type(session, UK) == "Type: country"


def test_a_pack_without_tiers_says_the_layers_word(session):
    rec = dict(session.store.feature(ENGLAND).record)
    rec.pop("tier")
    assert session._type_text(Area(0, 0, rec)) == "first-level division"


@pytest.mark.parametrize("name, said", [
    ("United Kingdom", "the United Kingdom"), ("United States", "the United States"), ("France", "France"),
    ("Isle of Wight", "the Isle of Wight"), ("The Gambia", "the Gambia"), ("Solomon Islands", "the Solomon Islands"),
    ("England", "England"), ("Netherlands", "the Netherlands"),
])
def test_a_name_after_of_takes_the_where_it_should(name, said):
    from mapcore.describe import words

    assert words.name_after_of(name) == said


def test_where_two_tiers_share_a_rank_the_lower_tier_comes_first():
    tiers = ["country", "constituent_country", "region", "county"]

    def area(i, tier, km2):
        return Area(0, 0, {"id": i, "layer": "regions", "rank": 4, "area_km2": km2, "tier": tier,
                           "names": {"en": i}})
    big_region = area("a region", "region", 200_000.0)
    small_cc = area("a constituent country", "constituent_country", 10_000.0)
    no_tier = area("an old area", None, 1.0)
    assert [a.id for a in most_specific_first([small_cc, no_tier, big_region], tiers)] == [
        "a region", "a constituent country", "an old area"]
    # With no tiers, the smallest first, as before.
    assert [a.id for a in most_specific_first([small_cc, no_tier, big_region])] == [
        "an old area", "a constituent country", "a region"]


# Draw the borders of regions (VIS-1, DP165) --------------------------------------------------

def _at(session, zoom_m):
    session.world.zoom_index = session.world.zoom_list.index(zoom_m)
    session.areas = session._here()   # as a zoom command does


def test_draw_the_borders_of_regions_is_off_at_first(session):
    assert session.settings["map_region_borders"] is False


def test_with_region_borders_off_the_map_draws_no_region_but_where_am_i_still_says_it(session):
    _at(session, 500000)   # England is the current area here, as the counties' zoom range is passed
    assert session.areas[0].id == ENGLAND
    frame = session.scene(800, 600)
    drawn = [a for a in frame["shape_area"] if session.store.feature(a).layer == "regions"]
    assert set(drawn) == {ENGLAND}, "only the current region, for its outline"
    from mapcore.render.scene import CLEAR_STYLE

    styles = {frame["shape_style"][i] for i, a in enumerate(frame["shape_area"]) if a == ENGLAND}
    assert styles == {CLEAR_STYLE}, "not painted: no fill and no border"
    assert frame["styles"][CLEAR_STYLE]["fill"] == "#00000000" and frame["styles"][CLEAR_STYLE]["width"] == 0
    assert frame["current"] and all(frame["shape_area"][i] == ENGLAND for i in frame["current"])
    assert spoken(session.press("Space")) == ["England, United Kingdom"]


def test_with_region_borders_on_the_regions_are_painted(session):
    _at(session, 500000)
    session.run("settings.set", field="map_region_borders", value=True)
    frame = session.scene(800, 600)
    regions = {a for a in frame["shape_area"] if session.store.feature(a).layer == "regions"}
    assert ENGLAND in regions and len(regions) > 1
    from mapcore.render.scene import CLEAR_STYLE

    assert CLEAR_STYLE not in set(frame["shape_style"].tolist())


def test_with_region_borders_off_an_isolated_region_is_still_painted(session):
    _at(session, 500000)
    session.run("panel.select", item=BRITTANY)
    session.isolated = BRITTANY
    frame = session.scene(800, 600)
    from mapcore.render.scene import CLEAR_STYLE

    assert BRITTANY in frame["shape_area"]
    assert {frame["shape_style"][i] for i, a in enumerate(frame["shape_area"]) if a == BRITTANY} != {CLEAR_STYLE}


def test_the_setting_is_in_the_display_tab(session):
    display = next(t for t in session.settings_schema()["tabs"] if t["id"] == "display")
    field = next(f for f in display["fields"] if f["id"] == "map_region_borders")
    assert field["label"] == "Draw the borders of regions" and field["kind"] == "yes_no"


def test_the_regions_layer_is_called_regions_and_constituent_countries(session):
    assert session.layers.get("regions").name == "Regions and constituent countries"
