"""The local-areas stage: every administrative level below the counties (P4-T1b, design docs/plan/p4-t1-design.md 3.5;
LOC-2, LOC-3, AD-15, AD-16).

Districts (level 8) and parishes (level 10) from OpenStreetMap, cut to the land, slivers given to the neighbour with
the longest shared edge, land in no parish said as "Unparished area", and every shared edge simplified once, so a
parish meets its district and a district its county exactly. Made-up shapes test the rules; the regional test pack
(the raw samples of Winchester, Brockenhurst and Lymington) tests the stage.
"""
from pathlib import Path

import pytest
import shapely
import yaml

from mapdata.paths import CONFIG_DIR
from mapdata.pipeline import features
from mapdata.stages import local_areas

HAMPSHIRE, WINCHESTER, NEW_FOREST = "osm:r172799", "osm:r127238", "osm:r129306"
BROCKENHURST, DENNY_LODGE, BOLDRE, LYMINGTON = "osm:r3946276", "osm:r3943911", "osm:r3948992", "osm:r3949115"
WINCHESTER_CENTRE = (-1.3135, 51.0615)    # the High Street, unparished
BOXES = {"winchester": [-1.31836, 51.05347, -1.29639, 51.06445],
         "brockenhurst": [-1.62598, 50.81177, -1.56006, 50.83374],
         "lymington": [-1.56006, 50.73486, -1.51611, 50.75684]}
SQUARE_DEGREES = 1e-12    # "within floating point" for shapes about a kilometre across


# The rules, on made-up shapes ----------------------------------------------------------------------------------

RULES = local_areas.Rules(sliver_km2=0.1, sliver_width_m=200, tolerance_m=10)
PART = {"gap_name": "Unparished area", "gap_type": "unparished area", "parish_tier": "civil parish",
        "district_tier": "district"}


def _area(oid, layer, geom, name=None, designation=None):
    return local_areas.Read(oid, layer, name or oid, name or oid, {"designation": designation} if designation else {},
                            geom)


def test_a_sliver_goes_to_the_neighbour_with_the_longest_shared_edge():
    """A thin strip of the county in no district, 0.02 km wide, between a district along its whole length and one
    that meets only its end, goes to the first."""
    county = shapely.box(0, 50, 0.1, 50.1)
    long_side = _area("osm:r1", "districts", shapely.box(0, 50, 0.0997, 50.05))
    short_side = _area("osm:r2", "districts", shapely.box(0, 50.05, 0.1, 50.1))
    out, report = local_areas.settle_county("osm:r9", county, [long_side, short_side], [], PART, RULES)
    got = {r["id"]: g for r, g in out if r["layer"] == "districts"}
    assert set(got) == {"osm:r1", "osm:r2"}
    assert got["osm:r1"].area == pytest.approx(0.1 * 0.05, rel=1e-9)     # the strip is in it
    assert got["osm:r2"].area == pytest.approx(0.1 * 0.05, rel=1e-9)
    assert [(s["layer"], s["given_to"]) for s in report["slivers"]] == [("districts", "osm:r1")]


def test_a_parish_sliver_goes_to_the_parish_with_the_longest_shared_edge_and_larger_land_is_unparished():
    county = shapely.box(0, 50, 0.1, 50.1)
    district = _area("osm:r1", "districts", county)
    # A strip 0.0001 degrees high along the county's north edge, above the left parish, meets the right parish only
    # at its end; a block of about 2 by 3 km in the right parish's east is in no parish.
    left = _area("osm:r11", "parishes", shapely.box(0, 50, 0.05, 50.0999), designation="civil_parish")
    right = _area("osm:r12", "parishes", shapely.box(0.05, 50, 0.1, 50.1).difference(
        shapely.box(0.07, 50.03, 0.1, 50.06)), designation="civil_parish")
    out, report = local_areas.settle_county("osm:r9", county, [district], [left, right], PART, RULES)
    parishes = {r["id"]: (r, g) for r, g in out if r["layer"] == "parishes"}
    assert set(parishes) == {"osm:r11", "osm:r12", "unparished:osm:r1"}
    assert parishes["osm:r11"][1].area == pytest.approx(0.05 * 0.1, rel=1e-9)
    gap, shape = parishes["unparished:osm:r1"]
    assert gap["name"] == "Unparished area" and gap["type"] == "unparished area" and gap["parent"] == "osm:r1"
    assert shape.area == pytest.approx(0.03 * 0.03, rel=1e-9)
    assert [(s["layer"], s["given_to"]) for s in report["slivers"]] == [("parishes", "osm:r11")]
    assert parishes["osm:r11"][0]["type"] == "civil parish" and parishes["osm:r11"][0]["parent"] == "osm:r1"


def test_a_county_with_no_districts_has_its_parishes_under_it():
    county = shapely.box(0, 50, 0.1, 50.1)
    parish = _area("osm:r11", "parishes", shapely.box(0, 50, 0.1, 50.1))
    out, _report = local_areas.settle_county("osm:r9", county, [], [parish], PART, RULES)
    assert [(r["id"], r["parent"]) for r, _g in out] == [("osm:r11", "osm:r9")]


def test_parishes_join_to_their_district_and_districts_to_their_county_after_simplifying():
    """Wiggly made-up borders, simplified once as shared edges: no gap and no overlap anywhere."""
    county = shapely.Polygon([(0, 50), (0.1, 50), (0.1, 50.1), (0.05, 50.1003), (0, 50.1)])
    wiggle = [(0.05 + 0.00003 * ((i % 3) - 1), 50 + i * 0.001) for i in range(101)]
    west = shapely.Polygon([(0, 50), *wiggle, (0, 50.1)]).intersection(county)
    east = county.difference(west)
    districts = [_area("osm:r1", "districts", west), _area("osm:r2", "districts", east)]
    p1 = _area("osm:r11", "parishes", shapely.box(0, 50, 0.06, 50.05).intersection(west.buffer(0.0002)))
    p2 = _area("osm:r12", "parishes", west.difference(shapely.box(0, 50, 0.06, 50.05)))
    out, _report = local_areas.settle_county("osm:r9", county, districts, [p1, p2], PART, RULES)
    _assert_joins(out, {"osm:r9": county})


def _assert_joins(out, counties: dict):
    by_parent: dict[str, list] = {}
    for r, g in out:
        by_parent.setdefault(r["parent"], []).append((r, g))
    shapes = {r["id"]: g for r, g in out}
    for parent, children in by_parent.items():
        whole = shapes.get(parent, counties.get(parent))
        if whole is None:
            continue
        if parent in counties:   # the county: its districts, and its land in no district's parishes
            children = [(r, g) for r, g in children if r["layer"] == "districts"] + [
                (r, g) for r, g in children if r["layer"] == "parishes"]
        joined = shapely.union_all([g for _r, g in children])
        assert shapely.symmetric_difference(joined, whole).area < SQUARE_DEGREES, parent
        assert sum(g.area for _r, g in children) == pytest.approx(joined.area, abs=SQUARE_DEGREES), parent


def test_the_types_are_plain_words():
    levels = local_areas.load_record()
    uk = levels["countries"]["osm:r62149"]
    assert local_areas.type_words("non_metropolitan_district", uk, "districts") == "district"
    assert local_areas.type_words("civil_parish", uk, "parishes") == "civil parish"
    assert local_areas.type_words("outer_london_borough", uk, "districts") == "London borough"
    assert local_areas.type_words("something_new", uk, "parishes") == "something new"


def test_the_record_gives_the_united_kingdoms_levels_and_gap_names():
    data = yaml.safe_load((CONFIG_DIR / "local_levels.yaml").read_text(encoding="utf-8"))
    uk = data["countries"]["osm:r62149"]
    assert uk["districts"] == [8] and uk["parishes"] == [10]
    parts = uk["parts"]
    assert parts["osm:r58447"]["gap_name"] == "Unparished area"                   # England
    assert parts["osm:r58446"]["gap_name"] == "Area with no community council"    # Scotland
    assert parts["osm:r58437"].get("gap_name") is None                           # Wales, wholly in communities
    assert all(e.get("why") for e in data["countries"].values())


def test_the_tiers_record_has_district_and_parish_after_county():
    data = yaml.safe_load((CONFIG_DIR / "tiers.yaml").read_text(encoding="utf-8"))
    assert data["tiers"][-3:] == ["county", "district", "parish"]
    assert data["layers"]["districts"] == "district" and data["layers"]["parishes"] == "parish"


def test_the_stage_reads_the_record_in_its_fingerprint():
    assert "local_levels" in local_areas.fingerprint_extra({"stage": "local-areas"})


# The stage, on the regional test pack ---------------------------------------------------------------------------

def _stage(test_region_pack, kind: str):
    work = Path(test_region_pack).parents[2] / "working" / "test-region"
    folder = next(f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith(f"{kind}-"))
    return folder, *features.load(folder)


@pytest.fixture(scope="module")
def stage(test_region_pack):
    folder, records, geoms = _stage(test_region_pack, "local-areas")
    return folder, records, geoms


def _layer(stage, layer):
    _f, records, geoms = stage
    return [(r, g) for r, g in zip(records, geoms) if r["layer"] == layer]


def test_every_point_of_the_samples_land_has_exactly_one_parish_layer_area(stage):
    land = shapely.union_all([g for _r, g in _layer(stage, "countries")])
    parishes = _layer(stage, "parishes")
    joined = shapely.union_all([g for _r, g in parishes])
    for name, box in BOXES.items():
        b = shapely.box(*box)
        here = shapely.intersection(land, b)
        assert here.area > 0, name
        assert shapely.symmetric_difference(shapely.intersection(joined, b), here).area < SQUARE_DEGREES, name
        cut = [shapely.intersection(g, b) for _r, g in parishes]
        assert sum(c.area for c in cut) == pytest.approx(here.area, abs=SQUARE_DEGREES), name


def test_a_districts_parishes_join_to_it_and_a_countys_districts_to_the_county(stage):
    counties = {r["id"]: g for r, g in _layer(stage, "counties")}
    out = _layer(stage, "districts") + _layer(stage, "parishes")
    _assert_joins(out, counties)
    districts = {r["id"] for r, _g in _layer(stage, "districts")}
    assert districts == {WINCHESTER, NEW_FOREST}
    joined = shapely.union_all([g for r, g in _layer(stage, "districts")])
    assert shapely.symmetric_difference(joined, counties[HAMPSHIRE]).area < SQUARE_DEGREES


def test_the_samples_parishes_are_under_their_districts(stage):
    parents = {r["id"]: r["parent"] for r, _g in _layer(stage, "parishes")}
    for parish in (BROCKENHURST, DENNY_LODGE, BOLDRE, LYMINGTON):
        assert parents[parish] == NEW_FOREST
    assert {r["parent"] for r, _g in _layer(stage, "districts")} == {HAMPSHIRE}


def test_winchesters_centre_is_unparished_area_in_the_city_of_winchester(stage):
    at = shapely.Point(*WINCHESTER_CENTRE)
    here = [r for r, g in _layer(stage, "parishes") if g.contains(at)]
    assert len(here) == 1
    assert here[0]["name"] == "Unparished area" and here[0]["type"] == "unparished area"
    assert here[0]["id"] == f"unparished:{WINCHESTER}" and here[0]["parent"] == WINCHESTER
    district = [r for r, g in _layer(stage, "districts") if g.contains(at)]
    assert [r["id"] for r in district] == [WINCHESTER]


def test_the_stage_writes_its_counts_for_the_quality_report(stage):
    import json

    folder, _r, _g = stage
    report = json.loads((folder / local_areas.REPORT).read_text(encoding="utf-8"))
    assert report["counts"]["districts"] == 2 and report["counts"]["parishes"] >= 5
    assert {"slivers", "gaps", "left_out"} <= set(report)


def test_the_districts_and_parishes_are_in_the_pack_with_their_tiers(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        records = {p.feature(n)["id"]: p.feature(n) for n in range(p.manifest["features"]["count"])}
        assert p.manifest["tiers"][-2:] == ["district", "parish"]
    assert records[NEW_FOREST]["tier"] == "district" and records[NEW_FOREST]["layer"] == "districts"
    assert records[BROCKENHURST]["tier"] == "parish" and records[BROCKENHURST]["tier_name"] == "civil parish"
    assert records[BROCKENHURST]["wikidata"] == "Q1612283"


# Details --------------------------------------------------------------------------------------------------------

@pytest.fixture
def session(test_region_pack):
    from mapcore.session import MapSession

    s = MapSession(packs=[test_region_pack], saved_state={"lat": 50.817, "lon": -1.575, "zoom_m": 2500,
                                                          "step_m": 250})
    s.start()
    yield s
    s.store.close()


def _details_type(session, item):
    session.run("panel.select", item=item)
    return next(line for line in session.details().splitlines() if line.startswith("Type: "))


def test_details_say_the_tier_of_a_district_and_a_parish(session):
    assert _details_type(session, NEW_FOREST) == "Type: district of Hampshire"
    assert _details_type(session, BROCKENHURST) == "Type: civil parish of New Forest"


def test_details_say_an_unparished_area_of_its_district(session):
    assert _details_type(session, f"unparished:{WINCHESTER}") == "Type: unparished area of Winchester"
