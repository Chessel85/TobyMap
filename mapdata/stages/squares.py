"""Stage "squares": build the world one grid square at a time (P1-T4, AD-16, LOC-6, DMT-1).

The method is described in mapdata/stages/grid.py. This stage:

1. Reads the areas from the stage before (osm-areas) and the oceans from
   VLIZ, and cuts each into grid squares, once.
2. Finds the land tiles in each grid square from the land index.
3. Builds each grid square in a worker process, a few at a time (DP103),
   and keeps each finished grid square in the stage's folder at once. If the
   build is stopped, by the run switch or otherwise, the grid squares already
   built are kept and the stage carries on from there.

A grid square with no land and one ocean over all of it needs no work: it is
written as that ocean straight away.

Settings:

* sources: [land-polygons, vliz-oceans].
* square_degrees: the size of a grid square, 1 by default.
* tolerance_m: the base detail, in metres (DP112), 100 by default.
* box: optional, [west, south, east, north], as in osm-areas.
* condominiums: land that two countries hold together (DP117), each with
  countries (two identifiers), id and name.
* counties: true for a counties layer, by the rule of DP101 (P3-T1a): each
  piece of land is in the smallest level 6 area of its country, or where
  level 6 leaves a gap, the level 7 area, then the level 8 area, and where
  none covers it, the region itself. A country's levels come from the
  counties record, mapdata/config/county_levels.yaml, when it is there. The
  osm-areas stage before must have counties: true; it reads the county
  levels and leaves out the areas that can fill no gap (P3-T1c).
* seas: the source of the named seas, bays and straits, such as
  naturalearth-marine-areas, for a Seas layer below the oceans (P3-T1b,
  DP168). Each face of water is named with the smallest sea it is in, and
  water between a sea's rough coast and the real coast with the sea beside
  it (mapdata/stages/seas.py).
"""
from __future__ import annotations

import json
import pickle
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import grid
from mapdata.stages import land as landmod

SQUARES = "squares"
AREAS = "areas.json"
BATCH = 4  # grid squares per job


OCEAN_DETAIL_DEG = 0.01  # about 1 km: VLIZ's coasts are not used, only where one ocean meets another
OCEANS_VERSION = "oceans-2"


def _ocean_job(geometry_json: str) -> bytes:
    """One ocean simplified, in a worker. The quick simplifying, which does not keep the shape from
    crossing itself, is many times faster on VLIZ's millions of points; any fault it leaves is mended."""
    g = shapely.from_geojson(geometry_json)
    g = shapely.simplify(g, OCEAN_DETAIL_DEG, preserve_topology=False)
    if not g.is_valid:
        g = shapely.make_valid(g, method="structure")
    g = grid.polygonal(g)
    return shapely.to_wkb(g if g is not None else shapely.Polygon())


def ocean_areas(path: Path, working: Path, claim, say, workers: int = 1) -> tuple[list[dict], list]:
    """The VLIZ oceans, simplified to about 1 km, kept in the working folder after the first build.

    The coast comes from the land polygons, so VLIZ's own detailed coasts are not needed: only where one
    ocean meets another. Simplifying each ocean on its own can leave slivers of sea between two oceans,
    or covered by both; the first goes to an ocean beside it, as any water in no ocean does, and the
    second to the ocean with the lower number. Each ocean is its own job, so several cores share the work.
    """
    import hashlib

    from mapdata import parallel

    st = path.stat()
    key = hashlib.sha1(f"{OCEANS_VERSION}-{path.name}-{st.st_size}-{st.st_mtime_ns}".encode()).hexdigest()[:12]
    cache = working / f"vliz-oceans-{key}.pkl"
    if cache.is_file():
        records, blobs = pickle.loads(cache.read_bytes())
        return records, [shapely.from_wkb(b) for b in blobs]
    t = time.perf_counter()
    data = json.loads(path.read_text(encoding="utf-8"))
    feats = data["features"]
    say(f"Preparing the {len(feats)} VLIZ oceans, once for this download: simplifying them to about 1 km, "
        f"{min(workers, len(feats))} at a time.")
    records = [{"id": f"vliz:goas:{n}", "name": f["properties"]["name"], "kind": "ocean", "level": None,
                "country": None} for n, f in enumerate(feats, 1)]
    jobs = [json.dumps(f["geometry"]) for f in feats]
    del data, feats
    with parallel.pool(min(workers, len(jobs))) as ex:
        blobs = list(ex.map(_ocean_job, jobs)) if hasattr(ex, "map") else [_ocean_job(j) for j in jobs]
    claim(cache).write_bytes(pickle.dumps((records, blobs)))
    say(f"Prepared the VLIZ oceans in {time.perf_counter() - t:.0f} seconds.")
    return records, [shapely.from_wkb(b) for b in blobs]


def county_index(previous: Path) -> dict:
    """Each country's county levels and how they were chosen, from the reading stage (P3-T1c)."""
    from mapdata.stages import osm_areas

    path = Path(previous) / osm_areas.SET_ASIDE / osm_areas.SET_ASIDE_INDEX
    if not path.is_file():
        raise BuildStopped("The setting counties: true needs the stage before to read the county areas: give the "
                           "osm-areas stage counties: true as well.")
    return json.loads(path.read_text(encoding="utf-8"))


def county_record(previous: Path) -> str:
    """The counties record the reading stage used, for the join stage to write what it finds."""
    from mapdata.stages import osm_areas

    return json.loads((Path(previous) / osm_areas.REQUEST).read_text(encoding="utf-8"))["counties"]["record"]


def unused_levels(records, levels_by_country, ctx) -> set[int]:
    """Divisions at a level that neither the regions nor the country's counties use, such as the United
    States' level 8 when the counties record gives it level 6 only: they could name no land."""
    regions = set(grid.LEVEL_ORDER)
    out = {i for i, r in enumerate(records)
           if r.get("kind") == "division" and r.get("level") not in regions
           and r.get("level") not in levels_by_country.get(r.get("country"), grid.COUNTY_LEVELS)}
    if out:
        ctx.progress.line(f"County levels: {len(out):,} areas are at a level their country's counties do not use, "
                          "so they are left out.")
    return out


def _cut_job(args):
    index, wkb, size, box = args
    parts = grid.cut_to_squares(shapely.from_wkb(wkb), size, box)
    return index, {k: shapely.to_wkb(g) for k, g in parts.items()}


def _square_job(job):
    """A batch of grid squares, in a worker: [(key, result as plain values, seconds)]."""
    index_folder, land_south, size, tol, meta, rules, squares = job
    index = landmod.LandIndex(Path(index_folder))
    out = []
    for (w, s), positions, pieces in squares:
        t = time.perf_counter()
        bounds = (w, s, w + size, s + size)
        q = shapely.box(*bounds)
        land = None
        if len(positions):
            tiles = index.read(np.array(positions, dtype=np.intp))
            land = shapely.intersection(shapely.union_all(tiles, grid_size=grid.GRID), q, grid_size=grid.GRID)
        cap = grid.polar_cap(bounds, land_south)
        if cap is not None:
            land = cap if land is None else shapely.union(land, cap, grid_size=grid.GRID)
        r = grid.build_square(bounds, land, [(i, shapely.from_wkb(b)) for i, b in pieces], meta, rules, tol)
        out.append((grid.square_key(w, s), plain(r), time.perf_counter() - t))
    return out


def plain(r: grid.SquareResult) -> dict:
    return {"key": r.key, "labels": [list(k) for k in r.labels], "shapes": [shapely.to_wkb(g) for g in r.shapes],
            "points_before": r.points_before, "points_after": r.points_after, "faces": r.faces,
            "overlaps": [list(o) for o in r.overlaps], "fills": [list(f) for f in r.fills],
            "counties": [list(c) for c in r.counties],
            "pairs": [list(x) for x in r.pairs]}


def load_square(path: Path) -> dict:
    return pickle.loads(path.read_bytes())


def tiles_by_square(bounds: np.ndarray, size: float, box) -> dict[tuple[float, float], list[int]]:
    """The land tiles touching each grid square, from the land index's bounds."""
    out: dict[tuple[float, float], list[int]] = defaultdict(list)
    if box is not None:
        keep = np.flatnonzero((bounds[:, 0] <= box[2]) & (bounds[:, 2] >= box[0]) &
                              (bounds[:, 1] <= box[3]) & (bounds[:, 3] >= box[1]))
    else:
        keep = np.arange(len(bounds))
    i0 = np.floor(bounds[keep, 0] / size).astype(np.intp)
    i1 = np.floor(np.nextafter(bounds[keep, 2], -np.inf) / size).astype(np.intp)
    j0 = np.floor(bounds[keep, 1] / size).astype(np.intp)
    j1 = np.floor(np.nextafter(bounds[keep, 3], -np.inf) / size).astype(np.intp)
    for pos, a0, a1, b0, b1 in zip(keep.tolist(), i0.tolist(), i1.tolist(), j0.tolist(), j1.tolist()):
        for a in range(a0, max(a1, a0) + 1):
            for b in range(b0, max(b1, b0) + 1):
                x, y = round(a * size, 7), round(b * size, 7)
                if -180 <= x < 180 and -90 <= y < 90:
                    out[(x, y)].append(pos)
    return out


def all_squares(size: float, box) -> list[tuple[float, float]]:
    return grid.squares_in(box or (-180, -90, 180, 90), size)


def run(ctx) -> None:
    from mapdata import parallel
    from mapdata.stages.pack_write import executor_map

    s = ctx.settings
    size = float(s.get("square_degrees", 1.0))
    tol = float(s.get("tolerance_m", 100.0))
    box = s.get("box")
    records, geoms = features.load(ctx.previous)
    _src, ocean_path = ctx.source("vliz-oceans")
    o_records, o_geoms = ocean_areas(ocean_path, ctx.folders.working, ctx.claim, ctx.progress.line, ctx.workers)
    c_index = county_index(ctx.previous) if s.get("counties") else None
    levels_by_country = {cid: tuple(e["levels"]) for cid, e in c_index.items()} if c_index is not None else None
    records, geoms = records + o_records, geoms + o_geoms
    if s.get("seas"):
        from mapdata.stages import seas as seasmod

        _src, seas_path = ctx.source(s["seas"])
        s_records, s_geoms = seasmod.marine_areas(json.loads(seas_path.read_text(encoding="utf-8"))["features"])
        ctx.progress.line(f"Seas: {sum(r['kind'] == 'sea' for r in s_records)} named seas, bays and straits, and "
                          f"{sum(r['kind'] == 'nosea' for r in s_records)} areas of water that name no sea, from "
                          f"{_src.name}.")
        records, geoms = records + s_records, geoms + s_geoms
    meta = [grid.Meta(r["kind"], r["id"], r.get("country"), r.get("level"), float(g.area))
            for r, g in zip(records, geoms)]
    ids = {r["id"] for r in records}
    condos = {}
    for c in s.get("condominiums") or []:
        missing = [i for i in c["countries"] if i not in ids]
        if missing and box is None:
            raise BuildStopped(f"The condominium {c['name']} names {', '.join(missing)}, which the planet file does "
                               "not have as a country. Correct the pack's settings.")
        condos[frozenset(c["countries"])] = c["id"]
    rules = grid.Rules(condominiums=condos, county_levels=levels_by_country, seas=bool(s.get("seas")))
    ctx.claim(ctx.folder / AREAS).write_text(
        json.dumps({"records": records, "condominiums": s.get("condominiums") or [], "counties": c_index,
                    "counties_record": county_record(ctx.previous) if c_index is not None else None},
                   ensure_ascii=False,
                   indent=0, sort_keys=True), encoding="utf-8", newline="\n")

    folder = ctx.folder / SQUARES
    folder.mkdir(exist_ok=True)
    wanted = all_squares(size, box)
    done = {p.stem for p in folder.glob("*.pkl")}
    todo = [sq for sq in wanted if grid.square_key(*sq) not in done]
    ctx.progress.line(f"Grid squares of {size:g} degrees: {len(wanted)}, of which {len(wanted) - len(todo)} are kept "
                      f"from an earlier run. Base detail: {tol:g} metres. Workers: {ctx.workers}.")
    if not todo:
        return

    ctx.source("land-polygons")
    index = landmod.open_index(ctx.folders.downloads, ctx.folders.working, ctx.progress.log)
    land_south = float(index.bounds[:, 1].min())
    by_square = tiles_by_square(index.bounds, size, box)

    t = time.perf_counter()
    pieces: dict[tuple[float, float], list] = defaultdict(list)
    todo_set = set(todo)
    left_out = set()
    if levels_by_country:
        left_out = unused_levels(records, levels_by_country, ctx)
    jobs = [(i, shapely.to_wkb(g), size, box) for i, g in enumerate(geoms)
            if g is not None and not g.is_empty and i not in left_out]
    jobs.sort(key=lambda j: -len(j[1]))  # the largest first, so the workers finish together
    with parallel.pool(ctx.workers) as ex:
        for n, (i, parts) in enumerate(executor_map(ex, _cut_job, jobs, ctx.workers), 1):
            for k, b in parts.items():
                if k in todo_set:
                    pieces[k].append((i, b))
            if n % max(1, len(jobs) // 10) == 0:
                ctx.progress.line(f"Cutting the areas into grid squares: {n} of {len(jobs)} done.")
    for k in pieces:
        pieces[k].sort()
    ctx.progress.line(f"Cut {len(jobs)} areas into grid squares in {time.perf_counter() - t:.0f} seconds.")

    # Grid squares with no land and one ocean over all of them, and with seas one marine area over all of them,
    # are written straight away.
    quick = 0
    work = []
    for sq in todo:
        ps = pieces.get(sq, [])
        if not by_square.get(sq) and grid.polar_cap((sq[0], sq[1], sq[0] + size, sq[1] + size), land_south) is None:
            whole = [i for i, b in ps if abs(shapely.from_wkb(b).area - size * size) < 1e-9]
            oceans = [i for i in whole if meta[i].kind == "ocean"]
            marine = [i for i in whole if meta[i].kind in ("sea", "nosea")]
            if len(whole) == len(ps) and len(oceans) == 1 and len(marine) <= int(rules.seas):
                label = ["water", meta[oceans[0]].id, None]
                if rules.seas:
                    label.append(grid.label_water(marine, meta, rules)[3] if marine else grid.SEA_WAITING)
                q = shapely.box(sq[0], sq[1], sq[0] + size, sq[1] + size)
                save_square(ctx, folder, {"key": grid.square_key(*sq), "labels": [label],
                                          "shapes": [shapely.to_wkb(q)], "points_before": 5, "points_after": 5,
                                          "faces": 1, "overlaps": [], "fills": [], "counties": [],
                                          "pairs": []})
                quick += 1
                continue
        work.append(sq)
    ctx.progress.line(f"Grid squares of open sea, written at once: {quick}. Grid squares to build: {len(work)}.")

    work.sort(key=lambda sq: -sum(len(b) for _i, b in pieces.get(sq, [])) - 200 * len(by_square.get(sq, [])))
    batches = []
    for n in range(0, len(work), BATCH):
        chunk = work[n:n + BATCH]
        used = {i for sq in chunk for i, _b in pieces.get(sq, [])}
        batches.append((str(index.folder), land_south, size, tol, {i: meta[i] for i in used}, rules,
                        [(sq, by_square.get(sq, []), pieces.get(sq, [])) for sq in chunk]))
    t = time.perf_counter()
    built = 0
    slowest = (0.0, "")
    with parallel.pool(ctx.workers) as ex:
        for results in executor_map(ex, _square_job, batches, ctx.workers):
            for key, result, took in results:
                save_square(ctx, folder, result)
                built += 1
                if took > slowest[0]:
                    slowest = (took, key)
            if built % max(1, len(work) // 50) < BATCH:
                ctx.progress.line(f"Grid squares built: {built} of {len(work)}.")
            ctx.check_switch(f"after {built} of {len(work)} grid squares")
    ctx.progress.line(f"Built {built} grid squares in {time.perf_counter() - t:.0f} seconds. The slowest, "
                      f"{slowest[1]}, took {slowest[0]:.0f} seconds.")


def save_square(ctx, folder: Path, result: dict) -> None:
    path = ctx.claim(folder / f"{result['key']}.pkl")
    tmp = path.with_suffix(".tmp")
    ctx.claim(tmp).write_bytes(pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL))
    tmp.replace(path)
