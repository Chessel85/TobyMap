"""The coast-stretches stage (P3-T30b, INF-2): each area's coast in stretches between its neighbours, with their ends.

Small shapes on the equator, where a degree is about 111 kilometres. Three counties side by side, A, B and C, west to
east, each 1 degree square, with the ocean to the south. B has an island in the sea, and C a sliver on B's shore.
"""
import json
import types

import numpy as np
import pytest
import shapely

from mapcore.packs import coords
from mapdata.pipeline import features
from mapdata.stages import coast_stretches as cs
from mapdata.stages.relationships import lengths_km

SLIVER = shapely.box(1.5, 0.0, 1.5005, 0.0005)     # about 55 metres square, on B's shore
ISLAND = shapely.box(1.4, -0.5, 1.45, -0.45)       # about 22 kilometres round


def _layers():
    def layer(i, kind, rank):
        return types.SimpleNamespace(id=i, name=i.capitalize(), kind=kind, geometry="area", rank=rank, shown=())
    return {"counties": layer("counties", "land", 5), "oceans": layer("oceans", "water", 1),
            "seas": layer("seas", "water", 2)}


def _world(tmp_path, with_sliver=True, two_seas=False):
    a = shapely.box(0, 0, 1, 1)
    b = shapely.box(1, 0, 2, 1)
    c = shapely.box(2, 0, 3, 1)
    if with_sliver:
        b = shapely.difference(b, SLIVER)
        c = shapely.MultiPolygon([c, SLIVER])
    b = shapely.MultiPolygon([b, ISLAND])
    ocean = shapely.difference(shapely.box(0, -1, 3, 0), ISLAND)
    sea = shapely.difference(shapely.box(1, -0.3, 1.5 if two_seas else 2, 0), ISLAND)
    records = [{"id": "A", "name": "A", "layer": "counties"}, {"id": "B", "name": "B", "layer": "counties"},
               {"id": "C", "name": "C", "layer": "counties"}, {"id": "O", "name": "Ocean", "layer": "oceans"},
               {"id": "S", "name": "Sea", "layer": "seas"}]
    geoms = [a, b, c, ocean, sea]
    if two_seas:   # B's coast on two seas, the west half on S, the east half on T
        records.append({"id": "T", "name": "Other sea", "layer": "seas"})
        geoms.append(shapely.box(1.5, -0.3, 2, 0))
    src = tmp_path / "relationships"
    src.mkdir()
    features.save(src, records, geoms)
    rel = {}
    for i in range(3):   # the coast as the relationships stage stores it: where the outline meets the ocean's
        km = float(lengths_km([shapely.intersection(shapely.boundary(geoms[i]), shapely.boundary(ocean))])[0])
        seas = ([[4, round(km / 2, 2)], [5, round(km / 2, 2)]] if two_seas else [[4, round(km, 2)]]) if i == 1 else []
        rel[str(i)] = {"coast": [[3, round(km, 2)]] + seas}
    (src / "relationships.json").write_text(json.dumps(rel), encoding="utf-8")
    return src


def _run(tmp_path, src, **settings):
    out = tmp_path / "out"
    out.mkdir()
    lines = []
    progress = types.SimpleNamespace(line=lines.append, log=lines.append)
    ctx = types.SimpleNamespace(pack=types.SimpleNamespace(layers=_layers()), settings=settings, previous=src,
                                folder=out, progress=progress, workers=1, claim=lambda p: p,
                                check_switch=lambda where: None)
    cs.run(ctx)
    rel = {int(k): v for k, v in json.loads((out / "relationships.json").read_text(encoding="utf-8")).items()}
    return rel, lines, out


def test_a_coast_between_two_neighbours_is_one_stretch_with_an_end_at_each(tmp_path):
    rel, lines, out = _run(tmp_path, _world(tmp_path))
    entry = rel[1]["coast_stretches"]
    [s] = entry["stretches"]   # the sliver of C on B's shore counts as sea, so it does not split B's coast
    assert s["km"] == pytest.approx(111.2, abs=0.5)
    (wlon, wlat, west), (elon, elat, east) = s["ends"]
    assert (west, east) == (0, 2)   # A at the west end, C at the east
    assert (wlon, wlat) == pytest.approx((1.0, 0.0), abs=1e-4) and (elon, elat) == pytest.approx((2.0, 0.0), abs=1e-4)
    assert s["half"] == pytest.approx([1.5, 0.0], abs=0.01)
    assert s["water"] == 4   # the sea, the most detailed water along it, not the ocean
    pts = coords.decode_stretch(s["line"])
    assert pts[0] == pytest.approx([1.0, 0.0], abs=1e-4) and pts[-1] == pytest.approx([2.0, 0.0], abs=1e-4)
    assert entry["islands_km"] == pytest.approx(22.2, abs=0.3)   # the island's coast, with no ends
    # The features are kept as they were; the relationships stored before are kept too.
    assert (out / "features.json").read_bytes() == (tmp_path / "relationships" / "features.json").read_bytes()
    assert rel[1]["coast"][0][0] == 3
    assert any("1 slivers on the shore counted as sea" in line for line in lines if line.startswith("Stretches"))
    assert any("0 differ by more than 1 percent" in line and "0 have no end of the neighbour's coast" in line
               for line in lines)


def test_without_the_sliver_counted_as_sea_or_the_break_joined_the_coast_would_split(tmp_path):
    rel, _lines, _out = _run(tmp_path, _world(tmp_path), sliver_km2=0.0, gap_m=0.0)
    ends = [[e[2] for e in s["ends"]] for s in rel[1]["coast_stretches"]["stretches"]]
    assert ends == [[0, 2], [2, 2]]   # A to C, then C at both ends, west to east


def test_an_area_with_a_coast_at_one_end_only_and_one_with_no_listed_stretch(tmp_path):
    rel, _lines, _out = _run(tmp_path, _world(tmp_path))
    [s] = rel[0]["coast_stretches"]["stretches"]
    assert [e[2] for e in s["ends"]] == [None, 1]   # nothing west of A
    assert rel[0]["coast_stretches"]["islands_km"] == 0
    assert "coast_stretches" not in rel.get(3, {})   # the ocean has shores, not coast


def test_stretches_under_the_least_length_are_not_kept(tmp_path):
    rel, _lines, _out = _run(tmp_path, _world(tmp_path), least_km=200.0)
    assert not any("coast_stretches" in r for r in rel.values())


def test_a_break_under_100_metres_is_joined_over_and_a_longer_one_is_not():
    west = np.array([[0.0, 0.0], [0.01, 0.0]])
    east = np.array([[0.0108, 0.0], [0.02, 0.0]])     # 89 metres on
    far = np.array([[0.0213, 0.0], [0.03, 0.0]])      # 145 metres on
    got = cs.join_gaps([east, west, far], 100.0)
    assert sorted((len(c), closed) for c, closed, _km in got) == [(2, False), (4, False)]
    joined = next(c for c, _closed, _km in got if len(c) == 4)
    assert {tuple(joined[0]), tuple(joined[-1])} == {(0.0, 0.0), (0.02, 0.0)}
    km = next(km for c, _closed, km in got if len(c) == 4)
    assert km == pytest.approx(2.13, abs=0.01)   # the coast's own length, not the break's


def test_lines_whose_ends_join_are_an_islands_coast():
    a = np.array([[0.0, 0.0], [0.01, 0.0], [0.01, 0.01]])
    b = np.array([[0.0102, 0.0102], [0.0, 0.01], [0.0, 0.0002]])
    [(c, closed, km)] = cs.join_gaps([a, b], 100.0)
    assert closed and km == pytest.approx(4.4, abs=0.1)
    assert tuple(c[0]) == tuple(c[-1])


def test_a_stored_line_is_simplified_and_reads_back():
    pts = np.array([[1.0, 50.0], [1.0001, 50.00001], [1.5, 50.2], [2.0, 50.0]])
    values = cs.encode_line(pts, 200.0)
    back = coords.decode_stretch(values)
    assert len(back) == 3   # the point 7 metres off the line is gone
    assert back == pytest.approx(np.array([[1.0, 50.0], [1.5, 50.2], [2.0, 50.0]]), abs=1e-4)
    assert all(isinstance(v, int) for v in values)


def test_with_ids_names_the_neighbours_and_the_water_by_identifier():
    rel = {"B": {"coast_stretches": {"stretches": [{"ends": [[1, 0, 0], [2, 0, None]], "water": 4, "km": 5}],
                                     "islands_km": 0}}}
    cs.with_ids(rel, ["A", "B", "C", "O", "S"])
    s = rel["B"]["coast_stretches"]["stretches"][0]
    assert s["ends"] == [[1, 0, "A"], [2, 0, None]] and s["water"] == "S"


def test_the_sliver_counted_as_sea_keeps_the_coast_whole_with_no_break_joined(tmp_path):
    rel, _lines, _out = _run(tmp_path, _world(tmp_path), gap_m=0.0)
    assert [[e[2] for e in s["ends"]] for s in rel[1]["coast_stretches"]["stretches"]] == [[0, 2]]


# P4-T14i: a stretch split where its sea changes, and a short one with one neighbour at both ends joined ---------------

def _stretch(points, km, west, east):
    c = np.array(points, dtype=float)
    return {"c": c, "km": km, "ends": [[c[0][0], c[0][1], west], [c[-1][0], c[-1][1], east]]}


def test_a_short_stretch_with_one_neighbour_at_both_ends_is_joined_to_the_stretch_beside_it():
    # As England's shore of the Dee: a long stretch from Wales, then 600 metres of Wales's shore, then 3 km of England's
    # with Wales at both ends.
    long_ = _stretch([[-3.10, 53.27], [-3.0, 54.0], [-3.05, 55.0]], 757.0, 7, 9)
    short = _stretch([[-3.095, 53.262], [-3.074, 53.254]], 3.3, 7, 7)
    far = _stretch([[-2.7, 51.6], [-1.0, 50.7]], 4000.0, 7, 9)   # Wales at its west end too, but 180 km away
    got = cs.join_short([far, long_, short], 20.0)
    assert len(got) == 2 and got[0] is not far and got[0]["c"] is far["c"]
    joined = got[1]
    assert joined["km"] == pytest.approx(760.3)
    assert [e[2] for e in joined["ends"]] == [7, 9]
    assert joined["ends"][0][:2] == pytest.approx([-3.074, 53.254])   # the short one's far end is the new west end
    assert len(joined["c"]) == 5 and joined["c"][-1] == pytest.approx([-3.05, 55.0])


def test_a_short_stretch_is_left_alone_with_no_stretch_beside_it_with_that_neighbour():
    monaco = _stretch([[7.41, 43.72], [7.44, 43.75]], 6.9, 3, 3)   # France at both ends, its only stretch
    other = _stretch([[7.5, 43.8], [7.6, 43.9]], 15.0, 4, 3)       # France at one end, but 8 km away
    lone = cs.join_short([monaco], 20.0)
    assert len(lone) == 1 and lone[0]["km"] == 6.9
    assert len(cs.join_short([monaco, other], 5.0)) == 2   # further than join_km


def test_a_stretch_of_20_km_or_more_with_one_neighbour_at_both_ends_is_kept():
    a = _stretch([[0.0, 0.0], [0.3, 0.0]], 33.0, 1, 1)
    b = _stretch([[0.301, 0.0], [0.5, 0.0]], 22.0, 1, 2)
    assert len(cs.join_short([a, b], 20.0)) == 2


def test_parts_on_one_water_and_a_short_bay_goes_to_the_longer_part_beside_it():
    labels = np.array([5, 5, 5, 3, 5, 5, -1, 6, 6, 6])   # a 5 km bay of the ocean (3), a step on no water (-1)
    step_km = np.array([10.0, 10, 10, 5, 10, 10, 1, 10, 10, 10])
    assert cs.sea_runs(labels, step_km, 20.0) == [(0, 6, 5), (6, 10, 6)]   # the step on no water goes east, the longer
    assert cs.sea_runs(labels, step_km, 4.0) == [(0, 3, 5), (3, 4, 3), (4, 6, 5), (6, 10, 6)]
    assert cs.sea_runs(labels, step_km, 100.0) == [(0, 10, 5)]   # the longest takes all
    assert cs.sea_runs(np.array([-1, -1]), np.array([1.0, 1.0]), 20.0) == [(0, 2, -1)]


def test_a_stretch_on_two_seas_is_split_where_the_sea_changes(tmp_path):
    rel, lines, _out = _run(tmp_path, _world(tmp_path, two_seas=True))
    got = rel[1]["coast_stretches"]["stretches"]
    assert [[e[2] for e in s["ends"]] for s in got] == [[0, None], [None, 2]]   # the new ends have no neighbour
    assert [s["water"] for s in got] == [4, 5]
    assert sum(s["km"] for s in got) == pytest.approx(111.2, abs=0.5)
    assert got[0]["ends"][1][:2] == pytest.approx([1.5, 0.0], abs=0.001)
    assert got[0]["half"] == pytest.approx([1.25, 0.0], abs=0.01)
    assert coords.decode_stretch(got[1]["line"])[-1] == pytest.approx([2.0, 0.0], abs=1e-4)
    assert [s["water"] for s in rel[0]["coast_stretches"]["stretches"]] == [3]   # A's, on the ocean alone, as before
    assert any("0 differ by more than 1 percent" in line for line in lines)


def test_in_the_stage_a_short_stretch_with_one_neighbour_at_both_ends_is_joined(tmp_path):
    # Without the sliver counted as sea, B's coast east of the sliver, 55 km, has C at both ends.
    rel, _lines, _out = _run(tmp_path, _world(tmp_path), sliver_km2=0.0, gap_m=0.0, join_km=60.0)
    [s] = rel[1]["coast_stretches"]["stretches"]
    assert [e[2] for e in s["ends"]] == [0, 2]
    assert s["km"] == pytest.approx(111.2, abs=0.5)
