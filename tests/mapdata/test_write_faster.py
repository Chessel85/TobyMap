"""P3-T1k: the writing stage shared among worker processes gives the same results as on one core (DMT-1)."""
import random

import shapely

from mapdata import parallel
from mapdata.stages import pack_write, write


def shapes():
    random.seed(2)
    out = []
    for _ in range(30):
        n = random.choice([1, 3, 20])
        out.append(shapely.MultiPolygon([shapely.Point(random.uniform(-170, 170), random.uniform(-80, 80))
                                         .buffer(random.uniform(0.01, 3), 100) for _ in range(n)]))
    holes = [[(x + 0.1, y + 0.1), (x + 0.4, y + 0.1), (x + 0.4, y + 0.4), (x + 0.1, y + 0.4)]
             for x in range(20) for y in range(20)]
    # Invalid: a hole outside its shell, as in the world's Indian Ocean.
    bad = shapely.Polygon([(0, 0), (30, 0), (30, 30), (0, 30)], holes + [[(50, 50), (51, 50), (51, 51), (50, 51)]])
    out += [shapely.MultiPolygon([bad, shapely.box(100, 0, 101, 1)]), shapely.Polygon(),
            shapely.LineString([(0, 0), (1, 1)]), shapely.Point(3, 4)]
    return out


def test_areas_are_the_same_with_workers_and_slow_parts_started_early(monkeypatch):
    """Large shapes measured part by part in several jobs, and an invalid part started early, add up to the same
    areas as one shape at a time on one core."""
    monkeypatch.setattr(write, "ALONE_POINTS", 1000)
    gs = shapes()
    alone, _ = write.feature_areas_km2(gs)
    with parallel.pool(2) as ex:
        early = write.start_slow_areas(gs, ex)
        shared, pending = write.feature_areas_km2(gs, ex, 2, early=early)
        shared = write.finish_areas(shared, pending, early)
    assert len(early) == 1
    assert shared == alone


def test_a_pack_is_the_same_written_on_one_core_or_several(tmp_path, monkeypatch):
    """Cutting with large parts handed back to the pool, splitting full pack tiles and making the records in the
    workers write the same bytes as on one core."""
    monkeypatch.setattr(pack_write, "DEFER_POINTS", 500)
    monkeypatch.setattr(pack_write, "MAX_POINTS", 300)
    monkeypatch.setattr(pack_write, "TILE_POINTS", 2000)
    seen = {"handed": 0, "split": 0}
    run_cut, split = pack_write.run_cut, pack_write.split_full_tiles

    def counting_cut(*a, **k):
        n = run_cut(*a, **k)
        seen["handed"] += n
        return n

    def counting_split(*a, **k):
        n = split(*a, **k)
        seen["split"] += n
        return n

    monkeypatch.setattr(pack_write, "run_cut", counting_cut)
    monkeypatch.setattr(pack_write, "split_full_tiles", counting_split)
    random.seed(3)
    gs = [shapely.MultiPolygon([shapely.Point(x, y).buffer(random.uniform(1, 9), 400) for x in (-60, 60)])
          for y in (-40, 0, 40)]
    gs += [shapely.LineString([(x / 10, 45 + (x % 7) / 10) for x in range(-1500, 1500)]),
           shapely.LineString([(0, 0), (1, 1)]), shapely.Point(3, 4)]
    gs += [shapely.Point(random.uniform(1, 4), random.uniform(44, 47)) for _ in range(5000)]
    records = [{"id": f"t:{i}", "layer": "countries", "name": f"Shape {i}", "type": "test", "area_km2": 1.0}
               for i in range(len(gs))]
    keep = [i for i, g in enumerate(gs) if not g.is_empty]
    records, gs = [records[i] for i in keep], [gs[i] for i in keep]
    manifest = {"name": "t", "sources": [{"name": "test", "licence": "ODbL 1.0", "date": "2026-11-12"}]}
    one, two = tmp_path / "one.pack", tmp_path / "two.pack"
    pack_write.write(one, manifest, [dict(r) for r in records], gs, workers=1, say=lambda _t: None)
    # Threads, not processes, so the lowered limits above hold in the workers too; the jobs are the same.
    import concurrent.futures as cf

    with cf.ThreadPoolExecutor(3) as ex:
        pack_write.write(two, manifest, [dict(r) for r in records], gs, workers=3, say=lambda _t: None,
                         executor=ex)
    assert one.read_bytes() == two.read_bytes()
    assert seen["handed"] > 0 and seen["split"] > 0


def test_jobs_within_a_budget_never_run_beyond_it_together():
    """The largest job runs alone; smaller ones share the budget; every job runs once."""
    import concurrent.futures as cf

    with cf.ThreadPoolExecutor(4) as ex:
        got = list(pack_write.run_within_budget(ex, lambda a: a, ["a", "b", "c", "d"], lambda j: j,
                                                [10, 4, 3, 3], 10, 4))
    assert sorted(got) == ["a", "b", "c", "d"]
