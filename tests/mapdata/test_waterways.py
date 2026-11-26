"""The osm-waterways stage: every other river and canal, and every stream, ditch and drain (P4-T1g, design
docs/plan/p4-t1-design.md 3.9; DAT-2, DAT-3).

osm-rivers makes the rivers the world pack has, with the world's ids. osm-waterways reads every other river and
canal way into the layer rivers, and every stream, ditch and drain into the layer streams. Ways of one name that
meet are joined end to end, each kept in the direction it is drawn, which in OpenStreetMap is the way the water
flows, so a feature runs from source to mouth with its sections in order. Unnamed ways of one type that meet are
joined within one parish. A river way osm-rivers has already used is not read again. Made-up ways test the rules;
the regional test pack (the raw samples) tests the stage.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import shapely

from mapdata.pipeline import features
from mapdata.stages import osm_source, osm_waterways

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "osm-raw"
# Winchester: the River Itchen's ways, and the unnamed side streams of its water meadows south of the city.
ITCHEN = [888703372, 888703373, 97475945, 784951706, 784951709]
SIDE_STREAMS = [1334306818, 1334306824, 1334306826, 1334306830, 1334306840, 1334306844, 1334306850, 48149733]
# Brockenhurst: The Weir, five stream ways and one river way, end to end, from its source to the Lymington River.
THE_WEIR = [552362438, 80050155, 80050136, 552362440, 552362439, 80877785]
LYMINGTON_RIVER = [79776098, 552362461]   # Brockenhurst, each with the Wikidata link Q6708191

D = 1 / 111_320   # a metre northwards, in degrees
E = D / 0.63      # a metre eastwards at latitude 51, in degrees


def _way(wid, kind, line, **tags):
    return osm_waterways.Way(wid, osm_waterways.KINDS[kind], kind, {"waterway": kind, **tags},
                             shapely.LineString(line))


def _join(ways, parishes=()):
    out = osm_waterways.join_ways(ways, list(parishes), meet_m=3)
    return {r["id"]: (r, g, w) for r, g, w in out}


def _runs_forward(line, way) -> bool:
    """True when way runs the same way as the part of line it lies on: its start comes before its end."""
    parts = list(shapely.get_parts(line))
    mid = shapely.line_interpolate_point(way, 0.5, normalized=True)
    part = min(parts, key=lambda p: p.distance(mid))
    start, end = shapely.Point(way.coords[0]), shapely.Point(way.coords[-1])
    return part.project(start) < part.project(end)


# Which ways are read, and into which layer ----------------------------------------------------------------------

@pytest.mark.parametrize("kind, layer", [
    ("river", "rivers"), ("canal", "rivers"), ("stream", "streams"), ("ditch", "streams"), ("drain", "streams"),
])
def test_each_waterway_value_has_its_layer(kind, layer):
    assert osm_waterways.KINDS[kind] == layer


def test_the_query_is_one_the_samples_understand():
    osm_source.parse_query(osm_waterways.QUERY)


def test_the_words_for_unnamed_waterways_come_from_the_templates():
    words = osm_waterways.unnamed_words()
    assert set(words) >= set(osm_waterways.KINDS)
    assert words["stream"] == "Unnamed stream" and words["ditch"] == "Ditch"
    assert osm_waterways.fingerprint_extra({"stage": "osm-waterways"}) == {"unnamed_words": words}


# Joining --------------------------------------------------------------------------------------------------------

def test_a_stream_in_several_ways_is_one_feature_with_its_sections_in_order():
    """Three ways of Test Brook, end to end, given out of order: one feature, from source to mouth."""
    a, b, c, d = (0, 51), (300 * E, 51), (300 * E, 51 - 300 * D), (600 * E, 51 - 300 * D)
    ways = [_way(30, "stream", [c, d], name="Test Brook"),
            _way(10, "stream", [a, b], name="Test Brook"),
            _way(20, "stream", [b, c], name="Test Brook")]
    out = _join(ways)
    assert list(out) == ["osm:w10"]
    r, g, w = out["osm:w10"]
    assert r["name"] == "Test Brook" and r["layer"] == "streams" and r["type"] == "stream"
    assert w == [10, 20, 30]
    assert g.geom_type == "LineString"
    assert [tuple(round(v, 6) for v in p) for p in g.coords] == [tuple(round(v, 6) for v in p) for p in (a, b, c, d)]


def test_a_way_drawn_against_the_others_keeps_its_own_direction():
    """The line is never turned round to make one line: each way keeps the direction it is drawn in."""
    ways = [_way(1, "stream", [(0, 51), (100 * E, 51)], name="Mill Stream"),
            _way(2, "stream", [(200 * E, 51), (100 * E, 51)], name="Mill Stream")]
    r, g, _w = _join(ways)["osm:w1"]
    assert all(_runs_forward(g, w.shape) for w in ways)


def test_a_named_water_of_river_and_stream_ways_takes_the_layer_of_most_of_its_length():
    ways = [_way(1, "stream", [(0, 51), (100 * E, 51)], name="Ober Water"),
            _way(2, "river", [(100 * E, 51), (900 * E, 51)], name="Ober Water")]
    r, _g, w = _join(ways)["osm:w1"]
    assert r["layer"] == "rivers" and r["type"] == "river" and w == [1, 2]


def test_two_waters_of_one_name_that_do_not_meet_are_two():
    ways = [_way(1, "stream", [(0, 51), (100 * E, 51)], name="Black Ditch"),
            _way(2, "stream", [(0, 51 - 2000 * D), (100 * E, 51 - 2000 * D)], name="Black Ditch")]
    assert sorted(_join(ways)) == ["osm:w1", "osm:w2"]


PARISH_A = ("osm:r1", shapely.box(0, 50.99, 0.01, 51.01))
PARISH_B = ("osm:r2", shapely.box(0.01, 50.99, 0.02, 51.01))


def test_unnamed_streams_meeting_in_one_parish_are_one_and_across_a_boundary_two():
    ways = [_way(5, "stream", [(0.001, 51), (0.003, 51)]),
            _way(6, "stream", [(0.003, 51), (0.003, 51.002)]),
            _way(7, "stream", [(0.003, 51.002), (0.0099, 51.002)]),
            _way(8, "stream", [(0.0099, 51.002), (0.015, 51.002)])]
    out = _join(ways, [PARISH_A, PARISH_B])
    assert sorted(out) == ["osm:w5", "osm:w8"]
    r, _g, w = out["osm:w5"]
    assert r["name"] == "Unnamed stream" and r["type"] == "stream" and w == [5, 6, 7]


def test_unnamed_ways_of_two_types_are_two():
    ways = [_way(5, "stream", [(0.001, 51), (0.003, 51)]),
            _way(6, "ditch", [(0.003, 51), (0.005, 51)])]
    out = _join(ways, [PARISH_A])
    assert sorted(out) == ["osm:w5", "osm:w6"]
    assert out["osm:w6"][0]["name"] == "Ditch" and out["osm:w6"][0]["layer"] == "streams"


def test_a_river_way_already_used_is_found_by_its_link_or_its_line():
    river = shapely.LineString([(0, 51), (1000 * E, 51)])
    before = [({"id": "osm:r9", "layer": "rivers", "name": "River Test", "wikidata": "Q1"}, river)]
    ways = [_way(1, "river", [(100 * E, 51 + 1 * D), (400 * E, 51 + 1 * D)], name="River Test"),
            _way(2, "river", [(0, 52), (100 * E, 52)], name="River Test", wikidata="Q1"),
            _way(3, "river", [(0, 51 + 200 * D), (300 * E, 51 + 200 * D)], name="Other River"),
            _way(4, "stream", [(100 * E, 51), (400 * E, 51)], name="A stream on the river's line")]
    used = osm_waterways.already_used(ways, before, within_m=5)
    assert used == {1, 2}


# The stage, on the regional test pack ---------------------------------------------------------------------------

def _stage_folder(test_region_pack, kind):
    work = Path(test_region_pack).parents[2] / "working" / "test-region"
    return next(f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith(f"{kind}-"))


def _sample_ways() -> dict[int, shapely.LineString]:
    out = {}
    for p in sorted(SAMPLES.glob("*.geojson")):
        for f in json.loads(p.read_text(encoding="utf-8"))["features"]:
            props = f["properties"]
            if props["osm"].startswith("w") and props["tags"].get("waterway"):
                out[int(props["osm"][1:])] = shapely.from_geojson(json.dumps(f["geometry"]))
    return out


@pytest.fixture(scope="module")
def stage(test_region_pack):
    folder = _stage_folder(test_region_pack, "osm-waterways")
    records, geoms = features.load(folder)
    ways = json.loads((folder / osm_waterways.WAYS).read_text(encoding="utf-8"))["ways"]
    mine = {r["id"]: (r, g) for r, g in zip(records, geoms) if r["id"] in ways}
    owner = {w: fid for fid, ids in ways.items() for w in ids}
    return mine, ways, owner, folder


def test_the_river_itchens_side_streams_in_winchester_are_streams_running_the_way_the_water_flows(stage):
    mine, _ways, owner, _folder = stage
    sample = _sample_ways()
    for wid in SIDE_STREAMS:
        r, g = mine[owner[wid]]
        assert r["layer"] == "streams" and r["type"] == "stream", wid
        assert _runs_forward(g, sample[wid]), wid
    for wid in ITCHEN:
        r, g = mine[owner[wid]]
        assert r["layer"] == "rivers" and r["name"] == "River Itchen"
        assert _runs_forward(g, sample[wid]), wid


def test_the_weir_in_several_ways_is_one_feature_from_source_to_mouth(stage):
    mine, ways, owner, _folder = stage
    fid = f"osm:w{min(THE_WEIR)}"
    assert {owner[w] for w in THE_WEIR} == {fid}
    assert sorted(ways[fid]) == ways[fid] and set(THE_WEIR) <= set(ways[fid])
    r, g = mine[fid]
    assert r["name"] == "The Weir" and r["layer"] == "streams"
    assert g.geom_type == "LineString"
    sample = _sample_ways()
    assert shapely.Point(g.coords[0]).distance(shapely.Point(sample[THE_WEIR[0]].coords[0])) < 1e-6
    assert shapely.Point(g.coords[-1]).distance(shapely.Point(sample[THE_WEIR[-1]].coords[-1])) < 1e-6
    steps = [g.project(shapely.Point(sample[w].coords[0])) for w in THE_WEIR]
    assert steps == sorted(steps)


def test_ways_json_holds_every_way_of_every_feature_once(stage):
    mine, ways, _owner, _folder = stage
    assert set(ways) == set(mine)
    every = [w for ids in ways.values() for w in ids]
    assert len(every) == len(set(every))
    assert all(fid == f"osm:w{min(ids)}" for fid, ids in ways.items())


def test_tidal_channels_are_not_read(stage):
    _mine, _ways, owner, _folder = stage
    assert 948386972 not in owner   # Lymington: waterway=tidal_channel


def test_the_stage_writes_its_counts(stage):
    _mine, _ways, _owner, folder = stage
    counts = json.loads((folder / osm_waterways.REPORT).read_text(encoding="utf-8"))["counts"]
    assert set(counts["layers"]) == {"rivers", "streams"}
    assert counts["layers"]["streams"]["ways"] > counts["layers"]["streams"]["features"] > 0
    assert counts["already_used"] == 0


def test_the_streams_are_in_the_pack(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        records = {p.feature(n)["id"]: p.feature(n) for n in range(p.manifest["features"]["count"])}
    r = records[f"osm:w{min(THE_WEIR)}"]
    assert r["name"] == "The Weir" and r["layer"] == "streams"


# A river the osm-rivers stage made ------------------------------------------------------------------------------

def test_a_river_the_osm_rivers_stage_made_is_not_read_twice(test_region_pack, tmp_path):
    """As osm-rivers runs before osm-waterways in the real packs: the River Itchen, made from its relation with no
    Wikidata link of its own (found by its line), and the Lymington River, with its link Q6708191 (found by the
    link), stay as they were, and none of their ways is read again."""
    before = _stage_folder(test_region_pack, "osm-water")
    records, geoms = features.load(before)
    sample = _sample_ways()
    itchen = {"id": "osm:r1000001", "layer": "rivers", "name": "River Itchen", "type": "river"}
    lymington = {"id": "osm:r1000002", "layer": "rivers", "name": "Lymington River", "type": "river",
                 "wikidata": "Q6708191"}
    previous = tmp_path / "before"
    previous.mkdir()
    features.save(previous, records + [itchen, lymington],
                  geoms + [shapely.line_merge(shapely.MultiLineString([sample[w] for w in ITCHEN]), directed=True),
                           shapely.LineString([(-1.4, 50.9), (-1.39, 50.9)])])
    folder = tmp_path / "osm-waterways"
    folder.mkdir()
    lines = []
    ctx = SimpleNamespace(settings={"stage": "osm-waterways", "source": "sample-osm-raw", "tolerance_m": 2},
                          previous=previous, folder=folder, folders=None,
                          earlier={"coverage": _stage_folder(test_region_pack, "coverage")}, claim=lambda p: p,
                          source=lambda key: (None, SAMPLES),
                          progress=SimpleNamespace(line=lines.append, log=lines.append))
    osm_waterways.run(ctx)
    out, _g = features.load(folder)
    assert [r for r in out if r["id"] in (itchen["id"], lymington["id"])] == [itchen, lymington]
    assert len({r["id"] for r in out}) == len(out)
    ways = json.loads((folder / osm_waterways.WAYS).read_text(encoding="utf-8"))["ways"]
    read = {w for ids in ways.values() for w in ids}
    assert not read & set(ITCHEN) and not read & set(LYMINGTON_RIVER)
    assert read & set(SIDE_STREAMS)
    report = json.loads((folder / osm_waterways.REPORT).read_text(encoding="utf-8"))
    assert report["counts"]["already_used"] == len(ITCHEN) + len(LYMINGTON_RIVER)
