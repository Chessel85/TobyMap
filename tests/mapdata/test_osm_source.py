"""One way to read OpenStreetMap for the regional stages (P4-T1a, design docs/plan/p4-t1-design.md 3.4): the query
matcher on the raw samples, reading boxes, the reading run for a stage, and cutting to the coverage."""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
import shapely

from mapdata.paths import CONFIG_DIR
from mapdata.stages import coverage, osm_source

RAW = CONFIG_DIR.parent.parent / "tests" / "samples" / "osm-raw"
WINCHESTER = [-1.31836, 51.05347, -1.29639, 51.06445]


@pytest.fixture(scope="module")
def samples():
    return osm_source.open_path(RAW, say=lambda _t: None)


def names(objs) -> set[str]:
    return {o.tags.get("name") for o in objs}


# The matcher ---------------------------------------------------------------------------------------------------

def test_kinds_and_a_tag_with_a_value(samples):
    stops = list(samples.query("n[highway=bus_stop]"))
    assert stops and all(o.kind == "node" and o.tags["highway"] == "bus_stop" for o in stops)
    assert all(o.id.startswith("osm:n") and o.shape.geom_type == "Point" for o in stops)
    assert not list(samples.query("w[highway=bus_stop]"))
    schools = list(samples.query("na[amenity=school]"))
    assert {o.kind for o in schools} <= {"node", "area"} and "Winchester College" in names(schools)


def test_has_and_has_not(samples):
    named = list(samples.query("a[leisure=park][name]"))
    assert "Abbey Gardens" in names(named) and None not in names(named)
    unnamed = list(samples.query("a[natural=water][!name]"))
    assert unnamed and all("name" not in o.tags for o in unnamed)


def test_one_of_several_values_and_none_of_them(samples):
    two = list(samples.query("n[amenity=post_box,bench]"))
    assert {o.tags["amenity"] for o in two} == {"post_box", "bench"}
    footways = list(samples.query("w[highway=footway]"))
    kept = list(samples.query("w[highway=footway][footway!=sidewalk,crossing]"))
    assert 0 < len(kept) < len(footways)
    assert not any(o.tags.get("footway") in ("sidewalk", "crossing") for o in kept)


def test_at_least_a_number(samples):
    tens = list(samples.query("a[boundary=administrative][admin_level>=9]"))
    assert tens and all(int(o.tags["admin_level"]) >= 9 for o in tens)
    assert "Brockenhurst" in names(tens) and "New Forest" not in names(tens)


def test_queries_joined_with_commas(samples):
    both = list(samples.query("n[amenity=post_box], n[amenity=bench]"))
    assert len(both) == len(list(samples.query("n[amenity=post_box,bench]")))


def test_quoted_values():
    sel = osm_source.parse_query('a[name="Abbey Gardens"]')
    assert osm_source.matches(sel, "area", {"name": "Abbey Gardens"})
    assert not osm_source.matches(sel, "way", {"name": "Abbey Gardens"})


def test_the_planet_is_given_values_quoted_where_geodesk_needs_it():
    """GeoDesk refuses an unquoted value with a hyphen, such as drive-through, which stopped the rehearsal's
    osm-streets stage (P4-T1j). The query given to GeoDesk quotes every value that is not a plain word or number."""
    q = osm_source.geodesk_query("w[highway=service][service!=driveway,parking_aisle,drive-through], "
                                 "na[name='Abbey Gardens'][!access][population>=1000], w[bridge]")
    assert q == ('w[highway=service][service!=driveway,parking_aisle,"drive-through"], '
                 'na[name="Abbey Gardens"][!access][population>=1000], w[bridge]')
    assert osm_source.parse_query(q) == osm_source.parse_query(q.replace('"drive-through"', "drive-through"))


def test_has_means_a_value_other_than_no():
    sel = osm_source.parse_query("w[bridge]")
    assert osm_source.matches(sel, "way", {"bridge": "yes"})
    assert not osm_source.matches(sel, "way", {"bridge": "no"})
    assert osm_source.matches(osm_source.parse_query("w[!bridge]"), "way", {"bridge": "no"})


@pytest.mark.parametrize("query", ["*", "r[type=route]", "a[name~Abbey]", "w[highway=*]", "a[ele<5]",
                                   "a[ele>=high]", "n[amenity=bench", "[amenity=bench]"])
def test_other_queries_are_refused(query, samples):
    with pytest.raises(osm_source.QueryRefused, match="cannot be used"):
        list(samples.query(query))


# Boxes ---------------------------------------------------------------------------------------------------------

def test_a_box_keeps_what_meets_it(samples):
    in_box = list(samples.query("n[highway=bus_stop]", WINCHESTER))
    every = list(samples.query("n[highway=bus_stop]"))
    assert 0 < len(in_box) < len(every)
    assert all(shapely.intersects(o.shape, shapely.box(*WINCHESTER)) for o in in_box)


def test_seen_reads_an_object_once_across_reading_boxes(samples):
    seen: set = set()
    halves = [[-1.31836, 51.05347, -1.30, 51.06445], [-1.30, 51.05347, -1.29639, 51.06445]]
    got = [o.id for box in halves for o in samples.query("w[highway]", box, seen)]
    assert len(got) == len(set(got)) == len(list(samples.query("w[highway]", WINCHESTER)))


# The reading run -----------------------------------------------------------------------------------------------

class FakeProgress:
    def __init__(self):
        self.lines = []

    def line(self, text):
        self.lines.append(text)

    log = line


class FakeCtx:
    def __init__(self, folder: Path, cov_folder: Path):
        self.folder = folder
        self.folders = None
        self.settings = {"stage": "a-test", "source": "sample-osm-raw"}
        self.earlier = {"coverage": cov_folder}
        self.progress = FakeProgress()

    def source(self, key):
        return None, RAW

    def claim(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return Path(path)


def test_a_reading_box_keeps_only_what_is_near_the_coverage(tmp_path):
    """A reading box is a level 8 pack tile, far larger than the coverage at its edge: on the rehearsal, 590,000 of
    the 710,000 street features joined lay outside the coverage (P4-T1j). save_box keeps only the shapes within
    NEAR_DEG of the coverage, so joining across its edge still works."""
    tiles = [(14, 8132, 12839)]   # Winchester's pack tile
    cov_folder = tmp_path / "coverage"
    cov_folder.mkdir()
    shape = coverage.coverage_shape(tiles)
    coverage.save(cov_folder, coverage.Coverage("test", 14, tiles, shape, ["test"]))
    request = {"coverage": str(cov_folder / coverage.COVERAGE_FILE), "own": ""}
    west, south, east, north = shape.bounds
    geoms = [shapely.Point(west + 0.001, south + 0.001), shapely.Point(east + osm_source.NEAR_DEG / 2, south),
             shapely.Point(east + 0.5, north), shapely.LineString([(east + 0.5, south), (west, south + 0.001)])]
    records = [{"id": i} for i in ("in", "near", "far", "crossing")]
    folder = osm_source.save_box(request, tmp_path / "read", 0, records, geoms)
    from mapdata.pipeline import features

    kept, _g = features.load(folder)
    assert [r["id"] for r in kept] == ["in", "near", "crossing"]


def test_run_reading_runs_the_stages_read_job_a_box_at_a_time(tmp_path, monkeypatch):
    tiles = [(14, 8132, 12839)]   # Winchester's pack tile
    cov_folder = tmp_path / "coverage"
    cov_folder.mkdir()
    coverage.save(cov_folder, coverage.Coverage("test", 14, tiles, coverage.coverage_shape(tiles), ["test"]))

    def read_job(source, request, out):
        cov = osm_source.load_request_coverage(request)
        seen: set = set()
        for n, box in enumerate(request["reading_boxes"]):
            records, geoms = [], []
            for o in source.query(request["query"], box, seen):
                records.append({"id": o.id, "name": o.tags.get("name", ""), "layer": "stops"})
                geoms.append(o.shape)
            records, geoms, _counts = osm_source.clip_to_coverage(records, geoms, cov)
            osm_source.save_box(request, out, n, records, geoms)

    fake = types.ModuleType("mapdata.stages.fake_reader")
    fake.read_job = read_job
    monkeypatch.setitem(sys.modules, "mapdata.stages.fake_reader", fake)
    ctx = FakeCtx(tmp_path / "stage", cov_folder)
    out = osm_source.run_reading(ctx, "fake_reader", {"query": "n[highway=bus_stop]"})
    request = json.loads((ctx.folder / osm_source.REQUEST).read_text(encoding="utf-8"))
    assert request["module"] == "mapdata.stages.fake_reader" and len(request["reading_boxes"]) == 1
    assert (out / osm_source.FINISHED).is_file()
    records, geoms = osm_source.load_boxes(out)
    cov_shape = coverage.coverage_shape(tiles)
    assert records and all(shapely.covered_by(g, cov_shape) for g in geoms)
    assert "The Broadway (Stand 7)" in {r["name"] for r in records}


def test_read_osm_runs_only_the_stages_modules(tmp_path):
    (tmp_path / osm_source.REQUEST).write_text(json.dumps({"module": "os"}), encoding="utf-8")
    with pytest.raises(osm_source.BuildStopped, match="only the stages' own modules"):
        osm_source.main(tmp_path)


def test_clip_to_coverage_marks_partial():
    cov = coverage.Coverage("t", 14, [], shapely.box(0, 0, 1, 1), [])
    records, geoms, counts = osm_source.clip_to_coverage(
        [{"id": "a"}, {"id": "b"}], [shapely.LineString([(0.5, 0.5), (1.5, 0.5)]), shapely.Point(3, 3)], cov)
    assert [r["id"] for r in records] == ["a"] and records[0]["partial"] is True
    assert counts == {"kept": 1, "partial": 1, "dropped": 1}
