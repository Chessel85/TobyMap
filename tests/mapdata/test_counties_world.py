"""Counties for the whole world (P3-T1c, DP101, DP167, DP175): the county areas sorted a country at a time,
a county never the region itself, the counties record written for each country read whole, and the record in
the planet reading's fingerprint."""
import json
import pickle

import shapely
import yaml

from mapdata.pipeline import features
from mapdata.stages import counties, grid, join, osm_areas
from mapdata.stages.grid import Meta, Rules

DEG = 0.01   # about 1.1 km at the equator: a square of DEG is over 1 km2


def set_aside(path, rows):
    """A country's file of county areas, as the reading writes it: in two lots, as when it is flushed twice."""
    with open(path, "wb") as f:
        half = len(rows) // 2
        pickle.dump(rows[:half], f)
        pickle.dump(rows[half:], f)


def test_a_country_is_sorted_alone_and_areas_that_can_fill_no_gap_are_left_out(tmp_path):
    six_a = shapely.box(0, 0, 0.5, 1)            # level 6 covers the west half
    seven_inside = shapely.box(0, 0, 0.25, 1)    # inside level 6: can fill no gap
    seven_gap = shapely.box(0.5, 0, 1, 1)        # in the gap: kept
    eight_inside = shapely.box(0.6, 0.2, 0.7, 0.3)   # inside level 7's gap filler: can fill no gap
    eight_sliver = shapely.box(0.5 - DEG / 10, 0, 1, 1)   # all but a sliver inside 6 and 7
    rows = [("osm:r6", "Six", 6, {"name": "Six"}, shapely.to_wkb(six_a)),
            ("osm:r7a", "Seven A", 7, {"name": "Seven A"}, shapely.to_wkb(seven_inside)),
            ("osm:r7b", "Seven B", 7, {"name": "Seven B", "name:en": "Seven Bee"}, shapely.to_wkb(seven_gap)),
            ("osm:r8a", "Eight A", 8, {"name": "Eight A"}, shapely.to_wkb(eight_inside)),
            ("osm:r8b", "Eight B", 8, {"name": "Eight B"}, shapely.to_wkb(eight_sliver))]
    path = tmp_path / osm_areas.set_aside_name("osm:r1")
    set_aside(path, rows)
    cid, kept, lines, counts = osm_areas.sort_country(("osm:r1", "Land", "LD", [6, 7, 8], str(path), {}))
    assert cid == "osm:r1"
    assert [r["id"] for r, _b in kept] == ["osm:r6", "osm:r7b"]
    assert kept[1][0]["name"] == "Seven Bee" and kept[1][0]["country"] == "osm:r1" and kept[1][0]["level"] == 7
    assert counts == {6: [1, 0], 7: [2, 1], 8: [2, 2]}
    assert lines == []


def test_a_county_level_read_as_a_region_level_is_measured_against_but_not_added_again(tmp_path):
    # Argentina's departments are level 5, which the regions read too (P3-T1c): they are already among the
    # divisions, so only the later levels are sorted against them.
    five = shapely.box(0, 0, 1, 1)
    path = tmp_path / "a.pkl"
    set_aside(path, [("osm:r6", "Six", 6, {"name": "Six"}, shapely.to_wkb(shapely.box(0, 0, 0.5, 0.5))),
                     ("osm:r6b", "Six B", 6, {"name": "Six B"}, shapely.to_wkb(shapely.box(1, 0, 2, 1)))])
    _cid, kept, _lines, counts = osm_areas.sort_country(
        ("osm:r2", "Argentina", "AR", [5, 6], str(path), {"5": [shapely.to_wkb(five)]}))
    assert [r["id"] for r, _b in kept] == ["osm:r6b"]
    assert counts == {5: [1, 0], 6: [2, 1]}


def test_areas_held_twice_are_kept_once_when_sorted(tmp_path):
    # DP104, as for the regions: the copy with the country's own ISO 3166-2 code is kept.
    g = shapely.to_wkb(shapely.box(0, 0, 1, 1))
    path = tmp_path / "b.pkl"
    set_aside(path, [("osm:r10", "Ours", 6, {"name": "Ours", "ISO3166-2": "LD-1"}, g),
                     ("osm:r11", "Theirs", 6, {"name": "Theirs", "ISO3166-2": "XX-1"}, g)])
    _cid, kept, lines, _counts = osm_areas.sort_country(("osm:r1", "Land", "LD", [6], str(path), {}))
    assert [r["id"] for r, _b in kept] == ["osm:r10"]
    assert kept[0][0]["disputed"] is True and len(lines) == 1 and lines[0].startswith("Level 6. Land:")


def test_a_county_is_never_the_region_itself():
    # A country with nothing at level 4 has its regions from level 5; if its counties are level 5 too, the
    # county is the next level down, or the region used as county, never the region a second time.
    meta = [Meta("country", "A", None, 2, 9.0), Meta("division", "five", "A", 5, 4.0),
            Meta("division", "six", "A", 6, 1.0)]
    rules = Rules(county_levels={"A": (5, 6)})
    label = grid.label_land([0, 1, 2], meta, rules, [], [], 1.0)
    assert label == ("land", "A", "five", "six")
    label = grid.label_land([0, 1], meta, rules, [], [], 1.0)
    assert label == ("land", "A", "five", "five" + grid.COUNTY_SUFFIX)
    # With level 4 present, level 5 is the county.
    meta.append(Meta("division", "four", "A", 4, 8.0))
    assert grid.label_land([0, 1, 2, 3], meta, rules, [], [], 1.0) == ("land", "A", "four", "five")


def test_the_record_is_written_but_a_corrected_entry_never_is(tmp_path):
    path = tmp_path / "record.yaml"
    path.write_text(yaml.safe_dump({"countries": {
        "osm:r1": {"name": "Argentina", "levels": [5, 6], "regions_used": [], "how": "corrected: departments"},
        "osm:r2": {"name": "France", "levels": [6], "regions_used": [], "how": "worked out by x on 1 May 2026"},
    }}), encoding="utf-8")
    done = counties.write_record(path, {"osm:r1": ("Argentina", [6], []), "osm:r2": ("France", [6], []),
                                        "osm:r3": ("Chile", [6, 8], ["Magallanes"])}, "the build of trial",
                                 today="11 November 2026")
    assert done == {"written": ["Chile"], "corrected": ["Argentina"], "unchanged": ["France"]}
    record = counties.load_record(path)
    assert record["osm:r1"]["levels"] == [5, 6] and record["osm:r1"]["how"] == "corrected: departments"
    assert record["osm:r2"]["how"] == "worked out by x on 1 May 2026"   # unchanged, so its date is kept
    assert record["osm:r3"] == {"name": "Chile", "levels": [6, 8], "regions_used": ["Magallanes"],
                                "how": "worked out by the build of trial on 11 November 2026"}
    assert path.read_text(encoding="utf-8").startswith("# The counties record")
    assert counties.how_of(record["osm:r1"]) == "corrected" and counties.how_of(record["osm:r3"]) == "worked out"
    assert counties.how_of(None) == "the rule"


def test_the_record_is_in_the_reading_fingerprint_only_with_counties(tmp_path, monkeypatch):
    path = tmp_path / "record.yaml"
    path.write_text(yaml.safe_dump({"countries": {"osm:r1": {"name": "A", "levels": [6], "how": "x"}}}),
                    encoding="utf-8")
    assert osm_areas.fingerprint_extra({"stage": "osm-areas"}) is None
    stage = {"stage": "osm-areas", "counties": True, "counties_record": str(path)}
    first = osm_areas.fingerprint_extra(stage)
    assert first == {"county_levels": {"osm:r1": [6]}}
    # A new date alone changes nothing; new levels read the planet file again.
    path.write_text(yaml.safe_dump({"countries": {"osm:r1": {"name": "A", "levels": [6], "how": "y"}}}),
                    encoding="utf-8")
    assert osm_areas.fingerprint_extra(stage) == first
    path.write_text(yaml.safe_dump({"countries": {"osm:r1": {"name": "A", "levels": [5, 6], "how": "y"}}}),
                    encoding="utf-8")
    assert osm_areas.fingerprint_extra(stage) != first


def test_features_append_adds_shapes_without_reading_them(tmp_path):
    features.save(tmp_path, [{"id": "a"}], [shapely.box(0, 0, 1, 1)])
    features.append(tmp_path, [{"id": "b"}, {"id": "c"}],
                    [shapely.to_wkb(shapely.box(1, 1, 2, 2)), shapely.to_wkb(shapely.box(2, 2, 3, 3))])
    records, geoms = features.load(tmp_path)
    assert [r["id"] for r in records] == ["a", "b", "c"]
    assert [g.bounds for g in geoms] == [(0, 0, 1, 1), (1, 1, 2, 2), (2, 2, 3, 3)]


def test_the_join_lists_every_gap_and_writes_the_record_for_countries_read_whole(tmp_path):
    lines, logged = [], []
    ctx = type("C", (), {"progress": type("P", (), {"line": staticmethod(lines.append),
                                                     "log": staticmethod(logged.append)})(),
                         "pack": type("K", (), {"data": {"name": "trial"}})()})()
    path = tmp_path / "record.yaml"
    by_id = {"A": {"name": "Aland"}, "B": {"name": "Bland"}, "RA": {"name": "Ra", "country": "A"},
             "RB": {"name": "Rb", "country": "B"}, "six": {"name": "Six", "level": 6, "country": "A"},
             "eight": {"name": "Eight", "level": 8, "country": "A"}, "sixb": {"name": "Six B", "level": 6, "country": "B"}}
    # The land of a country unit is labelled with the unit, but its counties count for the country.
    shapes = {("land", "U", "RA", "six"): [shapely.box(0, 0, 1, 1)],
              ("land", "A", "RA", "eight"): [shapely.box(1, 0, 1.1, 1)],
              ("land", "A", "RA", "RA" + grid.COUNTY_SUFFIX): [shapely.box(2, 0, 2.5, 1)],
              ("land", "B", "RB", "sixb"): [shapely.box(5, 0, 6, 1)]}
    rows = {("A", 6): 12000.0, ("A", 8): 1200.0, ("A", grid.REGION_AS_COUNTY): 6000.0, ("B", 6): 12000.0}
    areas = {"counties": {"A": {"levels": [6, 7, 8], "how": "the rule", "whole": True},
                          "B": {"levels": [6, 7, 8], "how": "the rule", "whole": False}},
             "counties_record": str(path)}
    report = []
    join.county_report(ctx, rows, by_id, report, shapes, areas)
    assert report[0].startswith("Counties in Aland: level 6, 1 areas, 12,000 km2; gaps filled by level 8, 1 areas")
    assert "the region itself, Ra " in report[0] and report[0].endswith("Levels by the rule, as the counties record does not have this country yet.")
    assert any(r.startswith("No county covers") and "of Ra, Aland" in r for r in report)
    assert any(line.startswith("Gap in the counties of Aland filled by level 8: Eight,") for line in logged)
    record = counties.load_record(path)
    assert list(record) == ["A"]   # B is cut by the reading box, so it is not written
    assert record["A"]["levels"] == [6, 8] and record["A"]["regions_used"] == ["Ra"]
    assert any("1 not written, as the build has only part of them" in line for line in lines)


def test_squares_need_the_reading_to_have_read_the_counties(tmp_path):
    import pytest

    from mapdata.pipeline.errors import BuildStopped
    from mapdata.stages import squares

    with pytest.raises(BuildStopped, match="counties: true as well"):
        squares.county_index(tmp_path)
    (tmp_path / osm_areas.SET_ASIDE).mkdir()
    (tmp_path / osm_areas.SET_ASIDE / osm_areas.SET_ASIDE_INDEX).write_text(json.dumps({"A": {"levels": [6]}}))
    assert squares.county_index(tmp_path) == {"A": {"levels": [6]}}


def test_a_country_with_nothing_at_its_first_level_has_its_counties_at_the_next():
    lines, logged, report = [], [], []
    ctx = type("C", (), {"progress": type("P", (), {"line": staticmethod(lines.append),
                                                     "log": staticmethod(logged.append)})(),
                         "pack": type("K", (), {"data": {"name": "trial"}})()})()
    by_id = {"HR": {"name": "Croatia"}, "m": {"name": "M", "level": 7, "country": "HR"}}
    join.county_report(ctx, {("HR", 7): 5000.0}, by_id, report, {("land", "HR", "R", "m"): [shapely.box(0, 0, 1, 1)]},
                       {"counties": {"HR": {"levels": [6, 7, 8], "how": "the rule", "whole": False}}})
    assert report[0].startswith("Counties in Croatia: level 7, 1 areas")


def test_a_county_with_the_id_of_a_region_gets_an_ending_so_every_id_is_different():
    records = [
        {"id": "osm:r1", "layer": "regions"},
        {"id": "osm:r1", "layer": "counties"},
        {"id": "osm:r2", "layer": "counties"},
        {"id": "osm:r3#county", "layer": "counties"},
    ]
    join.keep_ids_unique(records)
    ids = [r["id"] for r in records]
    assert ids == ["osm:r1", "osm:r1" + grid.COUNTY_ALSO_REGION_SUFFIX, "osm:r2", "osm:r3#county"]
    assert len(set(ids)) == len(ids)
