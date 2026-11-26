"""The osm-streets stage: every road, street, track and footpath, named or not (P4-T1d, design
docs/plan/p4-t1-design.md 3.7; DAT-2, DAT-3).

Main roads (primary and secondary), streets and minor roads, and paths and tracks, each read from OpenStreetMap
within the coverage. A main road with a number is joined by its number, per country, as osm-lines joins the world's
roads. A street or path with a name is joined with the ways of the same name and layer that meet it, or come within
30 metres of it, so two High Streets that do not meet are two. Unnamed ways of one layer and type that meet are
joined within one parish. Every feature's OpenStreetMap way ids are kept in ways.json, for Phase 5's network graph.
Made-up ways test the rules; the regional test pack (the raw samples) tests the stage.
"""
import json
from pathlib import Path

import pytest
import shapely

from mapdata.pipeline import features
from mapdata.stages import osm_source, osm_streets

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "osm-raw"
# Winchester's High Street, where it is a pedestrian street: six ways end to end, from the Westgate's side to the
# Buttercross and on to the Broadway.
HIGH_STREET = [8186389, 38325309, 145127583, 199232139, 1165278378, 1165278379]

D = 1 / 111_320   # a metre northwards, in degrees
E = D / 0.63      # a metre eastwards at latitude 51, in degrees


def _way(wid, layer, kind, line, **tags):
    return osm_streets.Way(wid, layer, kind, {"highway": kind, **tags}, shapely.LineString(line))


def _east(x0, y, metres):
    """A line from (x0, y) going east for metres."""
    return [(x0, y), (x0 + metres * E, y)]


def _join(ways, parishes=(), countries=()):
    out = osm_streets.join_ways(ways, list(parishes), list(countries), gap_m=30, meet_m=3)
    return {r["id"]: (r, g, w) for r, g, w in out}


# Which ways are read, and into which layer ----------------------------------------------------------------------

@pytest.mark.parametrize("tags, layer, kind", [
    ({"highway": "primary"}, "main-roads", "primary"),
    ({"highway": "secondary_link"}, "main-roads", "secondary"),
    ({"highway": "tertiary"}, "streets", "tertiary"),
    ({"highway": "residential"}, "streets", "residential"),
    ({"highway": "pedestrian"}, "streets", "pedestrian"),
    ({"highway": "service"}, "streets", "service"),
    ({"highway": "service", "service": "alley"}, "streets", "service"),
    ({"highway": "footway"}, "paths", "footway"),
    ({"highway": "bridleway"}, "paths", "bridleway"),
    ({"highway": "track"}, "paths", "track"),
    ({"highway": "steps"}, "paths", "steps"),
])
def test_each_highway_value_has_its_layer_and_type(tags, layer, kind):
    assert osm_streets.classify(tags) == (layer, kind)


@pytest.mark.parametrize("tags", [
    {"highway": "service", "service": "driveway"},
    {"highway": "service", "service": "parking_aisle"},
    {"highway": "service", "service": "drive-through"},
    {"highway": "footway", "footway": "sidewalk"},
    {"highway": "footway", "footway": "crossing"},
    {"highway": "motorway"},
    {"highway": "trunk"},
    {"highway": "construction"},
])
def test_a_driveway_a_sidewalk_and_the_worlds_roads_are_left_out(tags):
    assert osm_streets.classify(tags) is None


def test_the_queries_are_ones_the_samples_understand():
    osm_source.parse_query(osm_streets.QUERY)


def test_the_type_words_come_from_the_templates():
    words = osm_streets.type_words()
    assert words["footway"] == "footpath" and words["service"] == "service road"
    assert words["primary"] == "primary road" and words["cycleway"] == "cycle path"
    assert {k for _layer, k in osm_streets.KINDS.values()} <= set(words)
    assert osm_streets.unnamed_name("service", words) == "Service road"
    assert osm_streets.fingerprint_extra({"stage": "osm-streets"}) == {"type_words": words}


# Joining by name ------------------------------------------------------------------------------------------------

def test_ways_of_one_name_that_meet_are_one_feature():
    ways = [_way(30, "streets", "pedestrian", _east(0, 51, 100), name="High Street"),
            _way(10, "streets", "pedestrian", _east(100 * E, 51, 100), name="High Street"),
            _way(20, "streets", "residential", _east(200 * E, 51, 50), name="High Street")]
    out = _join(ways)
    assert list(out) == ["osm:w10"]
    r, g, w = out["osm:w10"]
    assert r["name"] == "High Street" and r["layer"] == "streets" and r["type"] == "pedestrian street"
    assert w == [10, 20, 30]
    assert g.geom_type == "LineString"


def test_two_high_streets_that_do_not_meet_are_two():
    """The High Street of Winchester and the High Street of Twyford, 5 km apart."""
    ways = [_way(1, "streets", "residential", _east(0, 51, 300), name="High Street"),
            _way(2, "streets", "residential", _east(0, 51 - 5000 * D, 300), name="High Street")]
    out = _join(ways)
    assert sorted(out) == ["osm:w1", "osm:w2"]
    assert all(r["name"] == "High Street" for r, _g, _w in out.values())


def test_a_roundabouts_gap_joins():
    """A street broken by a roundabout 20 metres across is one; the same name 100 metres on is another."""
    ways = [_way(1, "streets", "residential", _east(0, 51, 200), name="Station Road"),
            _way(2, "streets", "residential", _east(220 * E, 51, 200), name="Station Road"),
            _way(3, "streets", "residential", _east(520 * E, 51, 200), name="Station Road")]
    out = _join(ways)
    assert sorted(out) == ["osm:w1", "osm:w3"]
    assert out["osm:w1"][2] == [1, 2]


def test_a_name_joins_only_within_its_layer():
    ways = [_way(1, "streets", "residential", _east(0, 51, 100), name="Mill Lane"),
            _way(2, "paths", "footway", _east(100 * E, 51, 100), name="Mill Lane")]
    out = _join(ways)
    assert sorted(out) == ["osm:w1", "osm:w2"]
    assert out["osm:w2"][0]["layer"] == "paths"


# Unnamed ways, within a parish ----------------------------------------------------------------------------------

PARISH_A = ("osm:r1", shapely.box(0, 50.99, 0.01, 51.01))
PARISH_B = ("osm:r2", shapely.box(0.01, 50.99, 0.02, 51.01))


def test_unnamed_footpaths_meeting_in_one_parish_are_one_feature():
    ways = [_way(5, "paths", "footway", [(0.001, 51), (0.003, 51)]),
            _way(6, "paths", "footway", [(0.003, 51), (0.003, 51.002)]),
            _way(7, "paths", "footway", [(0.003, 51.002), (0.005, 51.004)])]
    out = _join(ways, [PARISH_A, PARISH_B])
    assert list(out) == ["osm:w5"]
    r, _g, w = out["osm:w5"]
    assert r["name"] == "Footpath" and r["type"] == "footpath" and w == [5, 6, 7]


def test_unnamed_footpaths_crossing_a_parish_boundary_are_two():
    ways = [_way(5, "paths", "footway", [(0.006, 51), (0.0099, 51)]),
            _way(6, "paths", "footway", [(0.0099, 51), (0.014, 51)])]
    out = _join(ways, [PARISH_A, PARISH_B])
    assert sorted(out) == ["osm:w5", "osm:w6"]


def test_unnamed_ways_of_two_types_are_two():
    ways = [_way(5, "paths", "footway", [(0.001, 51), (0.003, 51)]),
            _way(6, "paths", "track", [(0.003, 51), (0.005, 51)])]
    out = _join(ways, [PARISH_A])
    assert sorted(out) == ["osm:w5", "osm:w6"]
    assert out["osm:w6"][0]["name"] == "Track"


def test_unnamed_ways_that_do_not_meet_are_two():
    ways = [_way(5, "paths", "footway", [(0.001, 51), (0.003, 51)]),
            _way(6, "paths", "footway", [(0.001, 51.001), (0.003, 51.001)])]
    assert sorted(_join(ways, [PARISH_A])) == ["osm:w5", "osm:w6"]


# Main roads, by number ------------------------------------------------------------------------------------------

def test_a_road_numbered_a33_has_the_number_in_its_name():
    ways = [_way(11, "main-roads", "primary", _east(0, 51, 500), ref="A33", name="Basingstoke Road"),
            _way(12, "main-roads", "primary", _east(500 * E, 51, 500), ref="A33", name="Basingstoke Road"),
            _way(13, "main-roads", "primary", _east(1000 * E, 51, 500), ref="A33")]
    out = _join(ways)
    assert list(out) == ["osm:w11"]
    r, _g, w = out["osm:w11"]
    assert r["name"] == "A33, Basingstoke Road" and r["ref"] == "A33" and r["type"] == "primary road"
    assert w == [11, 12, 13]


def test_numbered_roads_join_by_number_and_an_unnamed_link_joins_its_road():
    """Ways of the A33 a kilometre apart are still one road, as in osm-lines; an unnamed slip road at its end joins
    it; the B3335 is another road."""
    ways = [_way(11, "main-roads", "primary", _east(0, 51, 500), ref="A33"),
            _way(12, "main-roads", "primary", _east(1500 * E, 51, 500), ref="A33"),
            _way(14, "main-roads", "primary", [(2000 * E, 51), (2000 * E, 51 + 100 * D)]),
            _way(15, "main-roads", "secondary", _east(0, 51 - 3000 * D, 500), ref="B3335")]
    out = _join(ways)
    assert sorted(out) == ["osm:w11", "osm:w15"]
    assert out["osm:w11"][2] == [11, 12, 14]
    assert out["osm:w15"][0]["name"] == "B3335" and out["osm:w15"][0]["type"] == "secondary road"


# The stage, on the regional test pack ---------------------------------------------------------------------------

def _stage_folder(test_region_pack, kind):
    work = Path(test_region_pack).parents[2] / "working" / "test-region"
    return next(f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith(f"{kind}-"))


@pytest.fixture(scope="module")
def stage(test_region_pack):
    folder = _stage_folder(test_region_pack, "osm-streets")
    records, geoms = features.load(folder)
    ways = json.loads((folder / osm_streets.WAYS).read_text(encoding="utf-8"))["ways"]
    mine = {r["id"]: (r, g) for r, g in zip(records, geoms) if r["layer"] in osm_streets.LAYERS}
    return mine, ways, folder


def test_winchesters_high_street_is_one_feature(stage):
    mine, ways, _folder = stage
    fid = f"osm:w{min(HIGH_STREET)}"
    r, g = mine[fid]
    assert r["name"] == "High Street" and r["layer"] == "streets"
    assert set(HIGH_STREET) <= set(ways[fid])
    assert all(f"osm:w{w}" not in mine for w in HIGH_STREET if w != min(HIGH_STREET))
    assert g.geom_type == "LineString"


def test_ways_json_holds_every_way_id_of_every_feature(stage):
    mine, ways, _folder = stage
    assert set(ways) == set(mine)
    every = [w for ids in ways.values() for w in ids]
    assert len(every) == len(set(every))
    assert all(fid == f"osm:w{min(ids)}" for fid, ids in ways.items())


def test_driveways_and_sidewalks_are_left_out(stage):
    _mine, ways, _folder = stage
    kept = {w for ids in ways.values() for w in ids}
    data = json.loads((SAMPLES / "winchester.geojson").read_text(encoding="utf-8"))
    left = [int(f["properties"]["osm"][1:]) for f in data["features"]
            if f["properties"]["tags"].get("service") == "driveway"
            or (f["properties"]["tags"].get("highway") == "footway"
                and f["properties"]["tags"].get("footway") == "sidewalk")]
    assert left and not kept & set(left)


def test_the_numbered_roads_and_unnamed_ways_of_the_samples(stage):
    mine, _ways, _folder = stage
    names = [r["name"] for r, _g in mine.values() if r["layer"] == "main-roads"]
    assert any(n.startswith("A337") for n in names)
    assert any(n.startswith("B3330") for n in names)
    assert any(r["name"] == "Footpath" and r["layer"] == "paths" for r, _g in mine.values())


def test_the_stage_writes_its_counts(stage):
    _mine, _ways, folder = stage
    report = json.loads((folder / osm_streets.REPORT).read_text(encoding="utf-8"))
    counts = report["counts"]
    assert set(counts["layers"]) == set(osm_streets.LAYERS)
    assert counts["layers"]["paths"]["ways"] > counts["layers"]["paths"]["features"] > 0


def test_the_streets_are_in_the_pack(test_region_pack):
    from mapcore.packs.pack import Pack

    with Pack(test_region_pack, check_app=False) as p:
        records = {p.feature(n)["id"]: p.feature(n) for n in range(p.manifest["features"]["count"])}
    r = records[f"osm:w{min(HIGH_STREET)}"]
    assert r["name"] == "High Street" and r["layer"] == "streets"
