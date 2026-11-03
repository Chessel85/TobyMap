"""Spike S4 timing code (P0-T7): its timed lookup must answer exactly as the core's does. No browser."""
import sys
from pathlib import Path

import pytest
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "spikes" / "s4"))

import s4_bench  # noqa: E402

pytest.importorskip("mapdata")
from mapdata.stages import lookup, pack_write  # noqa: E402


@pytest.fixture
def pack(tmp_path):
    land = shapely.segmentize(shapely.box(5, 58, 15, 70), 0.01).difference(shapely.box(9, 63, 10, 64))
    fjord_town = shapely.box(9.2, 63.2, 9.8, 63.8)
    records = [{"id": "t:land", "name": "Land", "layer": "countries", "type": "country", "area_km2": 2.0},
               {"id": "t:town", "name": "Town", "local_name": "By", "layer": "regions", "type": "town",
                "area_km2": 1.0}]
    path = tmp_path / "t.pack"
    manifest = {"name": "test", "sources": [{"name": "Test", "licence": "ODbL 1.0", "date": "2026-10-26"}]}
    pack_write.write(path, manifest, records, [land, fjord_town], say=lambda s: None)
    p = lookup.open_pack(path)
    yield p
    p.close()


def test_timed_lookup_answers_as_the_core_does(pack):
    points = s4_bench.walk_points(63.5, 6.0, 90, 20.0, 30) + [(63.1, 9.1), (63.5, 9.5), (75.0, 10.0)]
    for cache in (False, True):
        lk = s4_bench.Lookup(pack, cache=cache)
        for lat, lon in points:
            assert lk.at(lon, lat) == lookup.at(pack, lon, lat)
    assert lk.decode_ms > 0 and lk.tiles_read > 0


def test_cache_means_fewer_pack_tiles_read(pack):
    pts = s4_bench.walk_points(63.5, 6.0, 90, 1.0, 20)
    no, yes = s4_bench.Lookup(pack, cache=False), s4_bench.Lookup(pack, cache=True)
    for lat, lon in pts:
        no.at(lon, lat)
        yes.at(lon, lat)
    assert yes.tiles_read < no.tiles_read


def test_walk_points_are_the_step_apart():
    pts = s4_bench.walk_points(60.0, 10.0, 90, 2.0, 5)
    assert len(pts) == 6
    lat0, lon0 = pts[0]
    lat1, lon1 = pts[1]
    assert lat1 == pytest.approx(lat0)
    assert (lon1 - lon0) * 111.32 * 0.5 == pytest.approx(2.0, rel=1e-3)  # cos 60 degrees is 0.5


def test_run_and_report(pack):
    places = [{"name": "Town", "lat": 63.5, "lon": 9.5, "includes": ["Town"]},  # in the land's hole
              {"name": "Out at sea", "lat": 75.0, "lon": 10.0, "sea": True},
              {"name": "Wrong on purpose", "lat": 63.1, "lon": 9.1, "includes": ["Town"]}]
    walks = [{"name": "East", "lat": 63.5, "lon": 6.0, "bearing": 90, "step_km": 5.0, "steps": 5}]
    result = s4_bench.run(pack, places, walks)
    assert result["places_passed"] == 2
    assert [r["ok"] for r in result["places"]] == [True, True, False]
    assert result["walks"][0]["no_cache"]["count"] == 5 and result["walks"][0]["tile_cache"]["count"] == 5
    text = "\n".join(s4_bench.report_lines(result, "Here"))
    assert "FAIL Wrong on purpose" in text and "pack tile cache" in text
    assert "\t" not in text and "|" not in text  # plain lines, no tables
