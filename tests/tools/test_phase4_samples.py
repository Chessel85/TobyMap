"""The Phase 4 street-level samples (P4-T0e): licence and box, every "must hold" counted by tag, the outline
as three boxes, and the size limit. No data folder and no network: the files are read as they are in the
repository. The byte-for-byte remake is checked by running tools/make_phase4_samples.py twice by hand."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "tests" / "samples" / "osm-raw"
NAMES = ("winchester", "brockenhurst", "lymington")


def _tool():
    spec = importlib.util.spec_from_file_location("make_phase4_samples", REPO / "tools" / "make_phase4_samples.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = _tool()


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tile_aligned(box) -> bool:
    """Whole pack tiles at tile level 14, to the 5 decimals the boxes are written in."""
    w, s, e, n = box
    width, height = 360 / 2 ** 14, 180 / 2 ** 14
    return all(abs(((v - o) / size) - round((v - o) / size)) * size < 1e-5
               for v, o, size in ((w, -180, width), (e, -180, width), (s, -90, height), (n, -90, height)))


@pytest.mark.parametrize("name", NAMES)
def test_raw_sample_has_licence_and_its_box(name):
    data = _read(RAW / f"{name}.geojson")
    assert data["type"] == "FeatureCollection"
    assert "OpenStreetMap" in data["licence"] and "ODbL" in data["licence"]
    assert data["about"]
    assert data["box"] == list(TOOL.BOXES[name])
    assert _tile_aligned(data["box"])


@pytest.mark.parametrize("name", NAMES)
def test_raw_features_have_osm_kind_tags_and_a_matching_shape(name):
    shapes = {"node": {"Point"}, "way": {"LineString"}, "area": {"Polygon", "MultiPolygon"}}
    last = None
    for f in _read(RAW / f"{name}.geojson")["features"]:
        p = f["properties"]
        assert set(p) == {"osm", "kind", "tags"}
        assert p["osm"][0] in "nwr" and p["osm"][1:].isdigit()
        assert p["tags"] and not any(k == "building" and not any(x in p["tags"] for x in TOOL.PLACE_KEYS)
                                     for k in p["tags"])
        assert f["geometry"]["type"] in shapes[p["kind"]]
        key = ("nwr".index(p["osm"][0]), int(p["osm"][1:]))
        assert last is None or key > last      # sorted by id, each object once
        last = key


@pytest.mark.parametrize("name", NAMES)
def test_every_must_hold_is_there(name):
    features = _read(RAW / f"{name}.geojson")["features"]
    for what, least, test in TOOL.MUST_HOLD[name]:
        found = sum(1 for f in features if test(f["properties"]["tags"], f["properties"]["kind"]))
        assert found >= least, f"{name}: {what}: found {found}, needs {least}"


def test_the_raw_samples_are_under_the_size_limit():
    assert sum((RAW / f"{n}.geojson").stat().st_size for n in NAMES) <= TOOL.SIZE_LIMIT


def test_the_cooked_sample_has_licence_box_and_the_areas():
    data = _read(REPO / "tests" / "samples" / "osm" / "lymington-coast.geojson")
    assert "ODbL" in data["licence"]
    assert data["box"] == [list(TOOL.LYMINGTON)]
    ids = {f["properties"]["id"]: f["properties"] for f in data["features"]}
    assert {"osm:r62149", "osm:r58447", "osm:r172799"} <= set(ids)
    assert ids["osm:r172799"]["layer"] == "counties" and ids["osm:r58447"]["layer"] == "regions"
    assert ids["osm:r62149"]["layer"] == "countries"


def test_the_outline_reads_as_three_boxes_inside_the_sample_boxes():
    sections, ring = [], None
    lines = (REPO / "tests" / "samples" / "outlines" / "test-region.poly").read_text(encoding="utf-8").split("\n")
    assert lines[0] == "test-region"
    for line in (x.strip() for x in lines[1:]):
        if line == "END":
            if ring is not None:
                sections.append(ring)
                ring = None
        elif line.isdigit():
            ring = []
        elif line:
            lon, lat = map(float, line.split())
            ring.append((lon, lat))
    assert len(sections) == 3
    for ring, box in zip(sections, TOOL.BOXES.values()):
        assert ring[0] == ring[-1] and len(set(ring)) == 4
        lons, lats = [p[0] for p in ring], [p[1] for p in ring]
        assert (min(lons), min(lats), max(lons), max(lats)) == pytest.approx(
            (box[0] + TOOL.SHRINK, box[1] + TOOL.SHRINK, box[2] - TOOL.SHRINK, box[3] - TOOL.SHRINK), abs=1e-9)
