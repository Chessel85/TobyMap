"""The build speed trials for the counties step (P1-T16, DP107).

Runs the counties step of one country with each method in
mapdata/stages/counties.py, times each part of it, and checks that every
method chooses the same counties, with the same land to within a square
metre. It reads only caches made by a stage's earlier run or its extract
(mapdata spike-s2 or spike-s2-extract), so it never opens the planet file.

Each method cuts areas to the land afresh, not from the cache, so the times
can be compared. The results go into the stage's output folder, as
counties-trials-<date and time>.txt, with the same in JSON.
"""
from __future__ import annotations

import json
import pickle
import time

import shapely

from mapdata.paths import DataFolders
from mapdata.stages import clip, counties as countiesmod, land as landmod, s2_stage
from mapdata.stages.geodesy import area_km2
from mapdata.stages.s2_stage1 import Log, english

SAME_KM2 = 1e-6   # one square metre


class GaveUp(Exception):
    pass


def run(stage: str, folders: DataFolders, methods: list[str], country_id: str | None = None,
        within: list[float] | None = None, give_up_minutes: float | None = None, workers: int = 3) -> int:
    log = Log()
    config = s2_stage.load_config(stage)
    name = config["name"]
    working = folders.working / name
    out_dir = folders.output / name
    out_dir.mkdir(parents=True, exist_ok=True)
    gol = folders.root / config["source_gol"]
    cache = s2_stage.extract_cache_path(config, folders, gol)
    if not cache.is_file():
        log(f"Stage {stage} has not been read from the planet file yet. Run: python -m mapdata spike-s2-extract {stage}")
        return 2
    log(f"Counties trials on stage {stage}, {config['title']}")
    ex = pickle.loads(cache.read_bytes())
    countries = ex["countries"]
    divisions = ex["divisions"]
    settings = {c["id"]: c for c in config["countries"]}
    region_level = config.get("region_level", 4)
    wanted = [c for c in config["countries"] if c.get("divisions") and (country_id is None or c["id"] == country_id)]
    if not wanted:
        log(f"No country with divisions called {country_id} in stage {stage}.")
        return 2
    box = shapely.box(*within) if within else None
    if within:
        log(f"Only the land within {within} (west, south, east, north) is used.")

    # The land tiles, as the stage reads them, from its cache.
    shapes_for_land, boxes = {}, []
    for a in countries:
        g, _stopped = s2_stage.outline_to_the_pole(s2_stage.limited(a.geom, settings[a.id].get("land_within")))
        shapes_for_land[a.id] = g
        boxes.extend(s2_stage.part_boxes(g, join=0.5))
    boxes = s2_stage.part_boxes(s2_stage._box_union(boxes), pad=0.0, join=0.0)
    tiles = landmod.load_boxes(folders.downloads, working, name, boxes, say=log)
    tiles, _cap = s2_stage.with_polar_cap(tiles)
    land = clip.Land(tiles)

    results, report = {}, {}
    saved_dir = working / "counties-trials"

    def saved(cid: str, method: str):
        return saved_dir / f"{cid.replace(':', '_')}-{method}{'-within-' + '_'.join(f'{v:g}' for v in within) if within else ''}.pkl"

    for c in wanted:
        country = next(a for a in countries if a.id == c["id"])
        levels, _ = countiesmod.levels_for({}, country.id)   # the general rule, not the record
        cboxes = c.get("county_boxes") or ([within] if within else None)
        country_raw = s2_stage.limited(shapes_for_land[country.id], cboxes)

        def keep(d):
            return box is None or shapely.intersects(box, shapely.point_on_surface(d.geom))

        divs = [d for d in divisions[(country.id, region_level)] if keep(d)]
        clipped = s2_stage.clip_all(land, [(d.id, d.geom) for d in divs], working, log, workers)
        regions = [(d, s2_stage.limited(clipped[d.id], cboxes)) for d in divs]
        regions = [(d, g) for d, g in regions if not g.is_empty]
        cands = {lv: [d for d in divisions.get((country.id, lv), []) if keep(d)] for lv in levels}
        log.heading(f"{english(country)}")
        log(f"Regions: {len(regions)}. Areas at each level: "
            + ", ".join(f"level {lv}, {len(v)}" for lv, v in cands.items()) + ".")
        report[country.id] = {}
        for method in methods:
            timer = countiesmod.Timer()
            start = time.perf_counter()

            def clip_one(g):
                if give_up_minutes and time.perf_counter() - start > give_up_minutes * 60:
                    raise GaveUp
                return clip.polygonal(land.clip(g))

            try:
                res = countiesmod.build(country_raw, regions, cands, clip_one, levels, english=english,
                                        method=method, timer=timer)
            except GaveUp:
                took = time.perf_counter() - start
                log(f"Method {method}: stopped after {took / 60:.1f} minutes, as asked. Time so far: "
                    + "; ".join(f"{k}, {v:.1f} seconds" for k, v in timer.seconds.items()) + ".")
                report[country.id][method] = {"gave_up_seconds": took, "parts": timer.seconds}
                continue
            took = time.perf_counter() - start
            results[(country.id, method)] = res
            saved_dir.mkdir(parents=True, exist_ok=True)
            saved(country.id, method).write_bytes(pickle.dumps(res, protocol=pickle.HIGHEST_PROTOCOL))
            log(f"Method {method}: {took:.1f} seconds. {len(res.counties)} counties from levels "
                f"{', '.join(map(str, res.levels_used)) or 'none'}"
                + (f", and {len(res.regions_used)} regions used as their own county" if res.regions_used else "")
                + f". Land in no county: {res.left_km2:,.3f} km2.")
            for part, secs in sorted(timer.seconds.items(), key=lambda kv: -kv[1]):
                n = timer.calls.get(part, 1)
                log(f"  {part}: {secs:.1f} seconds" + (f", {n:,} times" if n > 1 else "") + ".")
            report[country.id][method] = {
                "seconds": took, "parts": timer.seconds, "calls": timer.calls, "levels_used": res.levels_used,
                "regions_used": res.regions_used, "left_km2": res.left_km2, "filled": res.filled,
                "counties": [{"id": k.area.id, "level": k.level, "region_fill": k.region_fill,
                              "km2": area_km2(k.geom)} for k in res.counties]}
        ran = [m for m in methods if (country.id, m) in results]
        for n, method in enumerate(ran):
            # Compared with an earlier method of this run, or else with the
            # result kept from an earlier run of spike S2's method or nearby-gap.
            if n:
                base, other = ran[0], results[(country.id, ran[0])]
            else:
                base = next((m for m in ("whole-gap", "nearby-gap") if m != method
                             and saved(country.id, m).is_file()), None)
                if base is None:
                    continue
                other = pickle.loads(saved(country.id, base).read_bytes())
                base = f"{base}, kept from an earlier run"
            lines = compare(other, results[(country.id, method)])
            if lines:
                log(f"Method {method} differs from {base}:")
                for line in lines[:30]:
                    log(f"  {line}")
            else:
                log(f"Method {method} chooses the same counties as {base}, with the same land to within a "
                    f"square metre, and the same land left in no county.")
            report[country.id][method]["differences"] = lines

    stamp = time.strftime("%Y-%m-%d-%H%M")
    (out_dir / f"counties-trials-{stamp}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (out_dir / f"counties-trials-{stamp}.txt").write_text("\n".join(log.lines) + "\n", encoding="utf-8")
    log(f"Report: {out_dir / f'counties-trials-{stamp}.txt'}")
    return 0


def compare(a: countiesmod.Result, b: countiesmod.Result) -> list[str]:
    """Every difference between two results, in plain lines; none if they are the same."""
    out = []
    ka = {(k.area.id, k.region_fill): k for k in a.counties}
    kb = {(k.area.id, k.region_fill): k for k in b.counties}
    for key in sorted(set(ka) - set(kb)):
        out.append(f"Only in the first: {key[0]}{' as a region' if key[1] else ''}.")
    for key in sorted(set(kb) - set(ka)):
        out.append(f"Only in the second: {key[0]}{' as a region' if key[1] else ''}.")
    if [k for k in a.counties] and [(k.area.id, k.region_fill) for k in a.counties] != \
            [(k.area.id, k.region_fill) for k in b.counties] and set(ka) == set(kb):
        out.append("The same counties, in a different order.")
    for key in sorted(set(ka) & set(kb)):
        ga, gb = ka[key].geom, kb[key].geom
        if ga.equals_exact(gb, 0):
            continue
        diff = area_km2(shapely.symmetric_difference(ga, gb))
        if diff > SAME_KM2:
            out.append(f"{key[0]}: its land differs by {diff * 1e6:,.1f} square metres.")
    if a.levels_used != b.levels_used:
        out.append(f"Levels used: {a.levels_used} against {b.levels_used}.")
    # Land left in no county is the whole gap less what regions filled, so it
    # carries the rounding of figures up to millions of km2: Argentina's
    # differed by 0.016 km2 in 1.2 million, about one part in 100 million.
    filled = sum(area_km2(k.geom) for k in a.counties if k.region_fill)
    if abs(a.left_km2 - b.left_km2) > 0.001 + 1e-7 * filled:
        out.append(f"Land in no county: {a.left_km2:,.3f} km2 against {b.left_km2:,.3f} km2.")
    return out
