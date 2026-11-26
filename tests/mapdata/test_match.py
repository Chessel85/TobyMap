"""The match stage: a regional pack's features given the world pack's identifiers (P4-T1h, design
docs/plan/p4-t1-design.md 3.11, architecture 6.7; DAT-2, DMT-1).

The world pack is the identifier register. A regional feature in a layer the world pack also has is matched by the
same id in the same layer, otherwise by the same Wikidata id in the same layer, otherwise by the same plain name and
type and an overlap. A matched feature takes the world's id and keeps its own as an alias, and every record that names
it (parent, within) names the world's id. Made-up records and shapes test the rules; the regional test pack, matched
against the test pack, tests the stage.
"""
import csv
import json
from pathlib import Path

import shapely

from mapdata.pipeline import report
from mapdata.stages import match

COVER = shapely.box(0, 50, 1, 51)


def _rec(fid, layer, name, type_="lake", **more):
    return {"id": fid, "layer": layer, "name": name, "type": type_, **more}


def _world(fid, layer, name, type_="lake", wikidata=None):
    return {"id": fid, "layer": layer, "name": name, "type": type_, "wikidata": wikidata}


def _match(records, shapes, world, world_shapes):
    found, unmatched = match.find_matches(records, shapes, world, world_shapes)
    return found, unmatched


# The rules, on made-up records and shapes --------------------------------------------------------------------------

def test_the_same_id_in_the_same_layer_is_matched_and_keeps_its_id():
    county = _rec("osm:r172799", "counties", "Hampshire", "level 6")
    world = [_world("osm:r172799", "counties", "Hampshire", "level 6")]
    found, unmatched = _match([county], {0: COVER}, world, {"osm:r172799": COVER})
    assert found[0].world_id == "osm:r172799" and found[0].how == "id"
    records = [county]
    match.apply_matches(records, found, {"osm:r172799": "counties"})
    assert records[0]["id"] == "osm:r172799" and "aliases" not in records[0]
    assert unmatched == []


def test_a_different_id_with_the_same_wikidata_takes_the_worlds_id_and_keeps_its_own_as_an_alias():
    river = _rec("osm:w44911161", "rivers", "River Itchen", "river", wikidata="Q7337528")
    world = [_world("osm:r7703089", "rivers", "River Itchen", "river", "Q7337528")]
    line = shapely.LineString([(0.1, 50.1), (0.2, 50.2)])
    found, _ = _match([river], {0: line}, world, {"osm:r7703089": line})
    assert found[0].world_id == "osm:r7703089" and found[0].how == "wikidata"
    records = [river]
    match.apply_matches(records, found, {"osm:r7703089": "rivers"})
    assert records[0]["id"] == "osm:r7703089"
    assert records[0]["aliases"] == ["osm:w44911161"]


def test_a_parish_names_the_worlds_county_as_its_parent_through_its_district():
    county = _rec("osm:r1", "counties", "Hampshire", "level 6", wikidata="Q23204")
    district = _rec("osm:r2", "districts", "Winchester", "district", parent="osm:r1")
    parish = _rec("osm:r3", "parishes", "Twyford", "parish", parent="osm:r2")
    village = _rec("osm:n4", "villages", "Twyford", "village",
                   within=[{"id": "osm:r1", "layer": "counties"}, {"id": "osm:r2", "layer": "districts"}])
    world = [_world("osm:r172799", "counties", "Hampshire", "level 6", "Q23204")]
    records = [county, district, parish, village]
    found, _ = _match(records, {0: COVER}, world, {"osm:r172799": COVER})
    match.apply_matches(records, found, {"osm:r172799": "counties"})
    assert county["id"] == "osm:r172799" and county["aliases"] == ["osm:r1"]
    assert district["parent"] == "osm:r172799"
    assert parish["parent"] == "osm:r2"
    assert village["within"] == [{"id": "osm:r172799", "layer": "counties"}, {"id": "osm:r2", "layer": "districts"}]


def test_the_same_name_and_type_that_overlap_are_matched_by_name():
    lake = _rec("osm:w1", "lakes", "Mill Pond", "pond")
    world = [_world("osm:r9", "lakes", "Mill  pond", "pond")]
    here = shapely.box(0.1, 50.1, 0.11, 50.11)
    found, unmatched = _match([lake], {0: here}, world, {"osm:r9": here.buffer(0.0005)})
    assert found[0].world_id == "osm:r9" and found[0].how == "name"
    assert 0.5 <= found[0].overlap <= 1
    assert unmatched == []


def test_a_feature_with_the_same_name_far_away_is_not_matched():
    lake = _rec("osm:w1", "lakes", "Mill Pond", "pond")
    world = [_world("osm:r9", "lakes", "Mill Pond", "pond")]
    here = shapely.box(0.1, 50.1, 0.11, 50.11)
    far = shapely.box(0.8, 50.8, 0.81, 50.81)
    found, unmatched = _match([lake], {0: here}, world, {"osm:r9": far})
    assert 0 not in found
    assert unmatched == ["osm:r9"]


def test_the_same_name_but_another_type_is_not_matched():
    lake = _rec("osm:w1", "lakes", "Mill Pond", "pond")
    world = [_world("osm:r9", "lakes", "Mill Pond", "reservoir")]
    here = shapely.box(0.1, 50.1, 0.11, 50.11)
    found, _ = _match([lake], {0: here}, world, {"osm:r9": here})
    assert 0 not in found


def test_a_line_is_matched_by_name_when_half_of_it_lies_within_200_metres():
    road = _rec("osm:w5", "roads", "A33", "trunk road")
    world = [_world("osm:w7", "roads", "A33", "trunk road")]
    near = shapely.LineString([(0.1, 50.5), (0.2, 50.5)])
    found, _ = _match([road], {0: near}, world, {"osm:w7": shapely.LineString([(0.1, 50.5015), (0.2, 50.5015)])})
    assert found[0].how == "name" and found[0].overlap == 1.0
    found, _ = _match([road], {0: near}, world, {"osm:w7": shapely.LineString([(0.1, 50.51), (0.2, 50.51)])})
    assert 0 not in found   # about 1.1 kilometres apart


def test_unnamed_islands_are_matched_by_their_overlap_alone():
    islet = _rec("island:unnamed:50.10000:0.10000", "islands", "Unnamed island", "unnamed island")
    world = [_world("island:unnamed:50.10010:0.10010", "islands", "Unnamed island", "unnamed island")]
    here = shapely.box(0.09, 50.09, 0.11, 50.11)
    found, _ = _match([islet], {0: here}, world, {"island:unnamed:50.10010:0.10010": here.buffer(0.001)})
    assert found[0].how == "name" and found[0].world_id == "island:unnamed:50.10010:0.10010"
    found, _ = _match([islet], {0: here}, world,
                      {"island:unnamed:50.10010:0.10010": shapely.box(0.5, 50.5, 0.52, 50.52)})
    assert 0 not in found


def test_a_world_feature_is_matched_once():
    a = _rec("osm:w1", "rivers", "River Test", "river", wikidata="Q1")
    b = _rec("osm:w2", "rivers", "River Test", "river", wikidata="Q1")
    world = [_world("osm:r9", "rivers", "River Test", "river", "Q1")]
    line = shapely.LineString([(0.1, 50.1), (0.2, 50.2)])
    found, _ = _match([a, b], {0: line, 1: shapely.LineString([(0.1, 50.1), (0.11, 50.11)])}, world,
                      {"osm:r9": line})
    assert [i for i in found] == [0]   # the one that lies along more of the world's line


def test_an_id_the_world_uses_in_another_layer_gets_the_as_ending():
    district = _rec("osm:r127864", "districts", "Southampton", "district")
    parish = _rec("osm:r8", "parishes", "Bitterne", "parish", parent="osm:r127864")
    records = [district, parish]
    found, _ = _match(records, {}, [], {})
    counts = match.apply_matches(records, found, {"osm:r127864": "counties"})
    assert district["id"] == "osm:r127864#as-districts"
    assert parish["parent"] == "osm:r127864#as-districts"
    assert counts["as_layer"] == 1


def test_the_world_ids_ending_as_the_layer_is_matched_by_id():
    island = _rec("osm:r1814783", "islands", "Somewhere", "island")
    world = [_world("osm:r1814783#as-islands", "islands", "Somewhere", "island")]
    found, _ = _match([island], {0: COVER}, world, {"osm:r1814783#as-islands": COVER})
    assert found[0].how == "id" and found[0].world_id == "osm:r1814783#as-islands"


def test_the_matches_are_the_same_whatever_the_order_of_the_world():
    lakes = [_rec(f"osm:w{i}", "lakes", "Pond", "pond") for i in range(3)]
    shapes = {i: shapely.box(0.1 + i / 10, 50.1, 0.12 + i / 10, 50.12) for i in range(3)}
    world = [_world(f"osm:r{i}", "lakes", "Pond", "pond") for i in range(3)]
    wshapes = {f"osm:r{i}": shapes[i] for i in range(3)}
    a, _ = _match(lakes, shapes, world, wshapes)
    b, _ = _match(lakes, shapes, list(reversed(world)), dict(reversed(list(wshapes.items()))))
    assert {i: m.world_id for i, m in a.items()} == {i: m.world_id for i, m in b.items()} == \
        {0: "osm:r0", 1: "osm:r1", 2: "osm:r2"}


# The report section ----------------------------------------------------------------------------------------------

def _match_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "16-match-0123"
    folder.mkdir()
    rows = [{"how": "name", "layer": "lakes", "world identifier": "osm:r9", "world name": "Mill Pond",
             "regional identifier": "osm:w1", "regional name": "Mill Pond", "overlap %": "87.5"},
            {"how": "wikidata", "layer": "rivers", "world identifier": "osm:r7703089", "world name": "River Itchen",
             "regional identifier": "osm:w44911161", "regional name": "River Itchen", "overlap %": "100.0"},
            {"how": "unmatched", "layer": "lakes", "world identifier": "osm:r10", "world name": "Lake Far",
             "regional identifier": "", "regional name": "", "overlap %": ""}]
    with open(folder / match.MATCHES, "w", encoding="utf-8", newline="") as f:
        out = csv.DictWriter(f, fieldnames=match.COLUMNS, lineterminator="\n")
        out.writeheader()
        out.writerows(rows)
    (folder / match.REPORT).write_text(json.dumps({"counts": {"id": 40, "wikidata": 1, "name": 1, "as_layer": 0,
                                                               "world_unmatched": 1}}), encoding="utf-8")
    return folder


def test_the_report_lists_each_match_made_by_name(tmp_path):
    got = report.gather_world_matches([(16, "match", _match_folder(tmp_path))])
    short, lines = report.world_matches_section(got, "the matches.csv")
    text = "\n".join([short, *lines])
    assert "Mill Pond" in text and "osm:w1" in text and "osm:r9" in text
    assert "by name" in text and "87.5" in text
    assert "River Itchen" in text and "Lake Far" in text
    assert lines.index(next(x for x in lines if "Mill Pond" in x)) < \
        lines.index(next(x for x in lines if "River Itchen" in x))   # matches by name first, to be checked


def test_features_of_stages_that_read_a_box_are_cut_to_the_coverage(tmp_path):
    """The unchanged stages osm-layer, osm-rivers, osm-lines and osm-places read the outline's box, not the coverage:
    on the rehearsal, 710 villages and many lakes, rivers and roads lay outside the coverage, and a long river was not
    partial (P4-T1j). The match stage cuts every feature to the coverage, one shape at a time, keeping a shape already
    inside byte for byte."""
    from mapdata.pipeline import features

    cover = shapely.box(0, 0, 10, 10)
    records = [{"id": "in", "layer": "lakes"}, {"id": "river", "layer": "rivers"}, {"id": "out", "layer": "villages"},
               {"id": "was", "layer": "streets", "partial": True}]
    geoms = [shapely.box(1, 1, 2, 2), shapely.LineString([(5, 5), (25, 5)]), shapely.Point(20, 20),
             shapely.LineString([(1, 1), (3, 3)])]
    src = tmp_path / "before"
    src.mkdir()
    features.save(src, records, geoms)
    data = json.loads((src / "features.json").read_text(encoding="utf-8"))
    counts = match.cut_to_coverage(src, data, cover, tmp_path / "shapes.wkb")
    assert [r["id"] for r in data["records"]] == ["in", "river", "was"]
    assert [r.get("partial", False) for r in data["records"]] == [False, True, True]
    raw = (tmp_path / "shapes.wkb").read_bytes()
    got = [shapely.from_wkb(raw[a:a + n]) for a, n in data["shapes"]]
    assert got[0].equals(geoms[0]) and got[1].length == 5
    assert raw[:data["shapes"][0][1]] == shapely.to_wkb(geoms[0])
    assert counts == {"kept": 3, "partial": 2, "dropped": 1, "cut": 1}


def test_a_pack_with_no_match_stage_says_so():
    short, lines = report.world_matches_section(None, "x.csv")
    assert "no match stage" in " ".join(lines)


# The stage, on the regional test pack against the test pack ------------------------------------------------------

def _stage_folder(pack: Path, kind: str) -> Path:
    work = pack.parents[2] / "working" / "test-region"
    return next(work.glob(f"*-{kind}-*"))


def test_hampshire_has_the_test_packs_id(test_region_pack, test_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_pack, check_app=False) as world, Pack(test_region_pack, check_app=False) as region:
        w = world.feature_by_id("osm:r172799")
        r = region.feature_by_id("osm:r172799")
        assert w["layer"] == r["layer"] == "counties" and r["names"]["en"] == "Hampshire"
        assert "aliases" not in r


def test_the_river_itchen_takes_the_test_packs_id_by_wikidata(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as region:
        r = region.feature_by_id("osm:r7703089")
        assert r is not None and r["layer"] == "rivers"
        assert r["aliases"] == ["osm:w44911161"]
        assert region.feature_by_id("osm:w44911161") is None
    rows = list(csv.DictReader(open(_stage_folder(test_region_pack, "match") / match.MATCHES, encoding="utf-8")))
    assert any(r["how"] == "wikidata" and r["world identifier"] == "osm:r7703089" for r in rows)


def test_a_parish_is_under_the_worlds_hampshire(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as region:
        parishes = list(region.scan(["parishes"]))
        assert parishes
        for parish in parishes:
            district = region.feature_by_id(parish["parents"][0])
            assert district["layer"] == "districts"
            assert "osm:r172799" in district["parents"]


def test_the_quality_report_has_the_matches_section(test_region_pack):
    text = (test_region_pack.parent / "test-region quality report.txt").read_text(encoding="utf-8")
    assert "\nMatches with the world pack\n" in text
    assert "River Itchen" in text
