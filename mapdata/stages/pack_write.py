"""Write a pack in format 3 (architecture 8.2 stage 16, AD-5, docs/developer/pack-format.md).

Each feature's exact shape is cut into pack tiles. Areas, lines and points are
all cut the same way; only areas have covered notes (format 3, P2-T10a). A tile entry with more
than MAX_POINTS points is cut again into its four smaller pack tiles, so a
point test never decodes a large shape, however many islands a country has
(architecture 6.3, 6.12). A pack tile that lies wholly inside a feature
stores only a covered note. Shapes are stored in compact coordinates.

The spike S2 stages give feature records with a name, a local name, a layer,
a type and an area; feature_record() adds what the format asks for. The
colour number is left empty until the base pack lite works it out (P1-T4,
AD-19).
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapcore.geo import geodesy
from mapcore.packs import coords, tiles
from mapcore.packs.pack import PackWriter
from mapdata.stages import antimeridian

START_LEVEL = 3
MAX_LEVEL = tiles.MAX_TILE_LEVEL
MAX_POINTS = tiles.ENTRY_POINTS
# A pack tile is also split when all its tile entries together have more
# than this many points. Without it, spike S2 stage 2 put 332 of Norway's
# municipalities, 690,000 points and 2.9 MB, into one pack tile, and every
# lookup in southern Norway took 0.75 seconds.
TILE_POINTS = tiles.TILE_POINTS
SHAPE, COVERED = tiles.COMPACT, tiles.COVERED
RANKS = {"countries": 2, "regions": 4, "counties": 6}
LAYER_NAMES = {"countries": "Countries", "regions": "Regions", "counties": "Counties"}
OSM_CREDIT = "© OpenStreetMap contributors"


# Cutting into pack tiles ------------------------------------------------------

def cut_to_rect(geom, bounds):
    """The part of a shape inside a rectangle.

    GEOS's rectangle cut (clip_by_rect) is about three times faster than a
    general intersection: on the UK's 2.2 million points, cutting into pack
    tiles took 16 seconds instead of 52, with the same result (spike S2,
    2 November). It does not promise a valid result, so in the rare case it
    gives an invalid one, the general intersection is used instead.
    """
    part = shapely.clip_by_rect(geom, *bounds)
    if part.is_empty and shapely.get_type_id(geom) in (1, 2, 5):
        # A line along the edge of the rectangle, such as the equator or the prime meridian on a pack
        # tile edge, is dropped by clip_by_rect, but it is on the rectangle's edge (P2-T10b).
        return shapely.intersection(geom, shapely.box(*bounds))
    if part.is_empty or part.is_valid:
        return part
    return shapely.intersection(geom, shapely.box(*bounds))


def entry_kind(geom) -> int:
    """The tile entry kind for a shape: COMPACT for an area, LINES or POINTS."""
    kind = shapely.get_type_id(geom)
    if kind in (1, 2, 5):   # LineString, LinearRing, MultiLineString
        return tiles.LINES
    if kind in (0, 4):      # Point, MultiPoint
        return tiles.POINTS
    return SHAPE


def _cut(geom, level: int, x: int, y: int, out: dict, index: int, defer: list | None = None) -> None:
    """Cut one feature's shape into pack tiles. Tile entries keep the shape, encoded later. With defer, a part
    of more than DEFER_POINTS points to be cut further is not cut here: (index, level, x, y, part) is put in
    defer, so its four smaller pack tiles can be cut by other workers (P3-T1k)."""
    bounds = tiles.tile_box(level, x, y)
    kind = entry_kind(geom)
    if kind == tiles.POINTS and shapely.get_type_id(geom) == 0:
        # One place: it is in this pack tile or not, as tiles.tile_of says, with no shapes made to find out.
        # Splitting a pack tile of 73,821 peaks tried each peak in all four smaller pack tiles, level after level:
        # 2.1 million tries, a third of the writing stage's time on one core (P3-T1k).
        if tiles.tile_of(geom.x, geom.y, level) == (x, y):
            out[(level, x, y)].append((index, kind, geom))
        return
    if kind != SHAPE:
        inside = keep_kind(points_in_tile(geom, level, x, y) if kind == tiles.POINTS else cut_to_rect(geom, bounds),
                           kind)
        if inside is None:
            return
        if shapely.get_num_coordinates(inside) > MAX_POINTS and level < MAX_LEVEL:
            _cut_children(inside, level, x, y, out, index, defer)
            return
        out[(level, x, y)].append((index, kind, inside))
        return
    box = shapely.box(*bounds)
    if shapely.contains_properly(geom, box):
        out[(level, x, y)].append((index, COVERED, None))
        return
    inside = _areas(cut_to_rect(geom, bounds))
    if inside is None:
        return
    # Covered when the part left is the whole pack tile.
    if abs(inside.area - box.area) <= 1e-12 * box.area and shapely.equals(inside, box):
        out[(level, x, y)].append((index, COVERED, None))
        return
    if shapely.get_num_coordinates(inside) > MAX_POINTS and level < MAX_LEVEL:
        _cut_children(inside, level, x, y, out, index, defer)
        return
    out[(level, x, y)].append((index, SHAPE, inside))


DEFER_POINTS = 50_000   # a part this large to be cut further is handed back, to be shared among the workers


def _cut_children(inside, level: int, x: int, y: int, out: dict, index: int, defer: list | None) -> None:
    """A part cut into the four smaller pack tiles of level, x, y: here, or handed back in defer when large."""
    if defer is not None and shapely.get_num_coordinates(inside) > DEFER_POINTS:
        defer.append((index, level, x, y, inside))
        return
    for dx in (0, 1):
        for dy in (0, 1):
            _cut(inside, level + 1, 2 * x + dx, 2 * y + dy, out, index, defer)


def _split_tile(key: tuple, entries: list, out: dict) -> None:
    """One full pack tile's entries cut into its four smaller pack tiles, or further, into out."""
    level, x, y = key
    for index, kind, g in entries:
        if kind == tiles.POINTS and shapely.get_type_id(g) == 0:   # one place: straight to its pack tile
            out[(level + 1, *tiles.tile_of(g.x, g.y, level + 1))].append((index, kind, g))
            continue
        for dx in (0, 1):
            for dy in (0, 1):
                child = (level + 1, 2 * x + dx, 2 * y + dy)
                if kind == COVERED:
                    out[child].append((index, COVERED, None))
                else:
                    _cut(g, level + 1, child[1], child[2], out, index)


def _wkb_entries(entries) -> list:
    return [(i, k, None if g is None else shapely.to_wkb(g)) for i, k, g in entries]


def _shape_entries(entries) -> list:
    return [(i, k, None if b is None else shapely.from_wkb(b)) for i, k, b in entries]


def _split_batch(jobs: list) -> list:
    """Full pack tiles split in a worker: [(key, WKB entries)] gives {pack tile: WKB entries}."""
    out: dict = defaultdict(list)
    for key, entries in jobs:
        _split_tile(key, _shape_entries(entries), out)
    return [(k, _wkb_entries(v)) for k, v in out.items()]


def split_full_tiles(cut: dict, executor=None, workers: int = 1) -> int:
    """Split every pack tile whose tile entries together have more than TILE_POINTS points, a tile level at a
    time. With an executor, the full pack tiles of a level are split in the workers. The entries of each pack
    tile are put in feature order afterwards, so the order the workers finish in does not matter. Returns how
    many pack tiles were split."""
    split = 0
    for level in range(START_LEVEL, MAX_LEVEL):
        full = [k for k in sorted(k for k in cut if k[0] == level)
                if sum(shapely.get_num_coordinates(g) for _i, kind, g in cut[k] if kind != COVERED) > TILE_POINTS]
        if not full:
            continue
        split += len(full)
        if executor is None:
            for key in full:
                _split_tile(key, cut.pop(key), cut)
            continue
        jobs = [(key, _wkb_entries(cut.pop(key))) for key in full]
        jobs.sort(key=lambda j: -sum(len(b or b"") for _i, _k, b in j[1]))
        n = max(1, min(len(jobs), workers * 4))
        for part in executor_map(executor, _split_batch, [jobs[k::n] for k in range(n) if jobs[k::n]], workers):
            for key, entries in part:
                cut[key].extend(_shape_entries(entries))
    return split


def feature_records(records: list[dict], geoms: list, executor=None, workers: int = 1) -> list[dict]:
    """feature_record for each feature, in the workers when there is an executor, in batches of about the same
    number of points."""
    if executor is None:
        return [feature_record(r, g) for r, g in zip(records, geoms)]
    n = max(1, min(len(records), workers * 4))
    order = sorted(range(len(records)), key=lambda i: -shapely.get_num_coordinates(geoms[i]))
    jobs = [order[k::n] for k in range(n) if order[k::n]]
    out: list = [None] * len(records)
    for part in run_within_budget(executor, _records_batch, jobs,
                                  lambda job: [(i, records[i], shapely.to_wkb(geoms[i])) for i in job],
                                  [0] * len(jobs), 0, workers):
        for i, rec in part:
            out[i] = rec
    return out


def _records_batch(items: list) -> list:
    return [(i, feature_record(r, shapely.from_wkb(b))) for i, r, b in items]


def points_in_tile(geom, level: int, x: int, y: int):
    """The points of a shape that belong to a pack tile: each point to exactly one
    pack tile, the one tiles.tile_of gives, so a point on an edge is stored once. Worked out for all the points
    at once, with the same sums as tiles.tile_of. None when no point is in the pack tile."""
    c = shapely.get_coordinates(geom)
    n = 2 ** level
    tx = np.clip(((c[:, 0] + 180) / 360 * n).astype(np.int64), 0, n - 1)
    ty = np.clip(((c[:, 1] + 90) / 180 * n).astype(np.int64), 0, n - 1)
    c = c[(tx == x) & (ty == y)]
    return shapely.multipoints(c) if len(c) else None


def keep_kind(geom, kind: int):
    """Keep only the parts of a cut that are the shape's own kind: polygons for an
    area, lines for a line, points for a point. None when nothing is left."""
    if kind == SHAPE:
        return _areas(geom)
    if geom is None or geom.is_empty:
        return None
    wanted = (1, 2) if kind == tiles.LINES else (0,)
    parts = [g for g in shapely.get_parts(geom) if shapely.get_type_id(g) in wanted and not g.is_empty]
    if kind == tiles.LINES:
        parts = [g for g in parts if len(g.coords) >= 2]
        merged = shapely.line_merge(shapely.MultiLineString(parts)) if len(parts) > 1 else None
        if merged is not None:
            parts = list(shapely.get_parts(merged))
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return shapely.MultiLineString(parts) if kind == tiles.LINES else shapely.MultiPoint(parts)


def _areas(geom):
    """Keep only the polygon parts of an intersection."""
    if geom.is_empty:
        return None
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    polys = [g for g in shapely.get_parts(geom) if g.geom_type in ("Polygon", "MultiPolygon")]
    if not polys:
        return None
    parts = []
    for p in polys:
        parts.extend(shapely.get_parts(p))
    return shapely.MultiPolygon(parts) if len(parts) > 1 else parts[0]


def _cut_batch(items: list) -> tuple[dict, list]:
    """Cut a batch of jobs into pack tiles, in a worker. A job is a feature, (index, WKB); one start pack tile of
    a feature, ("tile", index, x, y, WKB); or a large part handed back to be cut into its four smaller pack
    tiles, ("children", index, level, x, y, WKB). Returns {tile: [(index, kind, WKB or None)]}, and the large
    parts handed back, as "children" jobs. However the work is shared, each pack tile of a feature is cut by
    the same steps from the same shape, so the pack is the same (DMT-1)."""
    cut: dict = defaultdict(list)
    defer: list = []
    for item in items:
        if item[0] == "children":
            _w, index, level, x, y, wkb = item
            inside = shapely.from_wkb(wkb)
            for dx in (0, 1):
                for dy in (0, 1):
                    _cut(inside, level + 1, 2 * x + dx, 2 * y + dy, cut, index, defer)
            continue
        if item[0] == "tile":
            _w, index, x0, y0, wkb = item
            x1, y1 = x0, y0
            geom = shapely.from_wkb(wkb)
        else:
            index, wkb = item
            geom = shapely.from_wkb(wkb)
            x0, y0, x1, y1 = start_tiles(geom)
        if entry_kind(geom) == SHAPE:
            shapely.prepare(geom)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                _cut(geom, START_LEVEL, x, y, cut, index, defer)
    return ({key: [(i, k, None if g is None else shapely.to_wkb(g)) for i, k, g in entries]
             for key, entries in cut.items()},
            [("children", i, lv, x, y, shapely.to_wkb(g)) for i, lv, x, y, g in defer])


def start_tiles(geom) -> tuple[int, int, int, int]:
    """The first and last pack tile, x and y, at START_LEVEL, that a shape's bounds reach."""
    west, south, east, north = geom.bounds
    x0, y0 = tiles.tile_of(west, south, START_LEVEL)
    x1, y1 = tiles.tile_of(east, north, START_LEVEL)
    return x0, y0, x1, y1


def cut_jobs(geoms: list, workers: int) -> list[list]:
    """The first jobs of the cut, in batches: each feature over DEFER_POINTS points one job per start pack tile,
    alone in its batch, the largest first; the rest in batches of about the same number of points."""
    big, small = [], []
    for i, g in enumerate(geoms):
        n = shapely.get_num_coordinates(g)
        if n > DEFER_POINTS:
            wkb = shapely.to_wkb(g)
            x0, y0, x1, y1 = start_tiles(g)
            big += [(n, [("tile", i, x, y, wkb)]) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
        else:
            small.append((n, i))
    small.sort(key=lambda s: (-s[0], s[1]))
    n_batches = max(1, min(len(small), workers * 4))
    batches = [[(i, shapely.to_wkb(geoms[i])) for _n, i in small[k::n_batches]] for k in range(n_batches)]
    return [b for _n, b in sorted(big, key=lambda b: -b[0])] + [b for b in batches if b]


def run_cut(executor, jobs: list[list], workers: int, merge) -> int:
    """Run the cut's jobs, and the large parts each hands back, as soon as a worker is free, the parts handed
    back first. merge is given each finished job's pack tiles. Returns how many parts were handed back."""
    import concurrent.futures as cf

    from mapdata import parallel

    queue, running, handed = list(jobs), set(), 0
    while queue or running:
        while queue and len(running) < workers + 1 and parallel.room_for_another(len(running)):
            running.add(executor.submit(_cut_batch, queue.pop(0)))
        done, running = cf.wait(running, return_when=cf.FIRST_COMPLETED)
        for future in done:
            part, deferred = future.result()
            merge(part)
            handed += len(deferred)
            queue[:0] = [[d] for d in deferred]
    return handed


def _encode_batch(batch: list) -> list:
    """Encode a batch of pack tiles in compact coordinates, in a worker: [(tile, entries)]."""
    out = []
    for key, entries in batch:
        out.append((key, [(index, COVERED, b"") if kind == COVERED else (index, kind, encode(kind, shapely.from_wkb(blob)))
                          for index, kind, blob in entries]))
    return out


def encode(kind: int, geom) -> bytes:
    """A shape's bytes for a tile entry of its kind, in compact coordinates."""
    if kind == tiles.LINES:
        return coords.encode_lines(coords.lines_of(geom))
    if kind == tiles.POINTS:
        return coords.encode_points(coords.points_of(geom))
    return coords.encode(coords.rings_of(geom))


# Feature records and the manifest ---------------------------------------------

def feature_record(record: dict, geom) -> dict:
    """A spike S2 feature record with the fields the format asks for (architecture 6.4).

    The record's own fields are kept, so the S2 checks still find "name" and
    "local_name". The names are English, and "local" for the name in the
    area's own language where it differs.
    """
    out = dict(record)
    layer = record["layer"]
    out.setdefault("source", record["id"].split(":")[0])
    names = {"en": record["name"]}
    if record.get("local_name") and record["local_name"] != record["name"]:
        names["local"] = record["local_name"]
    out.setdefault("names", names)
    out.setdefault("rank", RANKS.get(layer, 8))
    box = antimeridian.wrap_box(geom)
    out.setdefault("bbox", [round(v, 7) for v in (box.west, box.south, box.east, box.north)])
    mid = (box.south + box.north) / 2
    across = geodesy.parallel_radius_m(mid) * math.radians(box.width)
    up = geodesy.distance_m(box.south, 0.0, box.north, 0.0)
    out.setdefault("width_km", round(max(across, up) / 1000, 3))
    out.setdefault("colour", None)  # worked out from P1-T4 (AD-19)
    point = shapely.point_on_surface(geom)
    out.setdefault("point", [round(point.x, 7), round(point.y, 7)])
    out.setdefault("parents", [record["parent"]] if record.get("parent") else [])
    return out


def full_manifest(manifest: dict) -> dict:
    """The stage's manifest with the defaults for a spike S2 build."""
    out = {"version": "spike-s2", "coverage": {"kind": "region"}, "app_versions": {"from": "0.0.1"},
           "drawing_levels": [], **manifest}
    if not out.get("sources"):
        raise ValueError("a pack's manifest lists its sources, each with a name, licence and date")
    return out


def spike_attribution(manifest: dict) -> str:
    lines = [f"{OSM_CREDIT}."]
    lines += [f"{s['name']}: {s['licence']}, {s['date']}." for s in manifest["sources"]]
    return "\n".join(lines) + "\n"


def source_date(path: Path) -> str:
    """A source file's date, as YYYY-MM-DD, from when it was last changed."""
    import datetime as dt

    return dt.datetime.fromtimestamp(Path(path).stat().st_mtime, dt.timezone.utc).date().isoformat()


def spike_sources(gol: Path, land_polygons: Path) -> list[dict]:
    """The sources of a spike S2 build: the GeoDesk library and the land polygons."""
    return [{"name": f"OpenStreetMap, GeoDesk library {Path(gol).name}", "licence": "ODbL 1.0",
             "date": source_date(gol)},
            {"name": f"OSM land polygons, {Path(land_polygons).name}", "licence": "ODbL 1.0",
             "date": source_date(land_polygons)}]


# Writing -------------------------------------------------------------------

def write(path: Path, manifest: dict, records: list[dict], geoms: list, workers: int = 1, say=print,
          layers: list[dict] | None = None, attribution: str | None = None,
          drawing_geoms: dict[int, list] | None = None, executor=None, before_records=None) -> dict:
    """Write the pack. The cutting into pack tiles and the encoding are split
    into batches run by worker processes (DP103); the main process joins the
    results, splits full pack tiles, and writes the file. The tile entries
    in each pack tile are put in feature order, whatever order the workers
    finish in, so the same areas always give the same bytes (DMT-1).

    layers and attribution come from the pipeline's settings; without them,
    the spike S2 defaults are used.

    drawing_geoms, if given, has the simplified shape of every feature (in
    the order of geoms) for each drawing level in the manifest, by level id;
    they are cut into drawing tiles (mapdata.stages.drawing_levels).

    executor, if given, is a pool already open, as the writing stage's; otherwise one is opened here.
    before_records, if given, is called before the feature records are made, such as to put in their areas.

    A progress line is written after each step, so a long step is seen to move (DMT-2).

    Returns measurements: bytes, pack tiles, tile entries, tile levels, seconds.
    """
    import contextlib

    from mapdata import parallel

    start = time.perf_counter()

    def step(text: str) -> None:
        say(f"{text}, {time.perf_counter() - start:.0f} seconds into writing the pack.")

    path = Path(path)
    manifest = full_manifest(manifest)
    cut: dict = defaultdict(list)
    with (contextlib.nullcontext(executor) if executor is not None else parallel.pool(workers)) as executor:
        def merge(part):
            for key, entries in part.items():
                cut[key].extend((i, k, None if b is None else shapely.from_wkb(b)) for i, k, b in entries)

        handed = run_cut(executor, cut_jobs(geoms, workers), workers, merge)
        step(f"Cut {len(geoms):,} features into {len(cut):,} pack tiles, with {handed:,} large parts shared "
             "among the workers")
        n_split = split_full_tiles(cut, None if workers == 1 else executor, workers)
        step(f"Split {n_split:,} full pack tiles")
        for entries in cut.values():
            entries.sort(key=lambda e: e[0])
        keys = sorted(cut)
        n_enc = max(1, min(len(keys), workers * 8))
        enc_batches = [[(key, [(i, k, None if g is None else shapely.to_wkb(g)) for i, k, g in cut[key]])
                        for key in keys[j::n_enc]] for j in range(n_enc)]
        cut.clear()
        encoded = {}
        for result in executor_map(executor, _encode_batch, [b for b in enc_batches if b], workers):
            for key, entries in result:
                encoded[key] = entries
        step(f"Encoded {len(encoded):,} pack tiles")
        drawn = {}
        if drawing_geoms:
            from mapdata.stages import drawing_levels

            tile_levels = {d["id"]: d["tile_level"] for d in manifest["drawing_levels"]}
            for level_id, shapes in sorted(drawing_geoms.items()):
                items = [(i, shapely.to_wkb(g)) for i, g in enumerate(shapes) if g is not None and not g.is_empty]
                items.sort(key=lambda it: -len(it[1]))
                nb = max(1, min(len(items), workers * 8))
                jobs = [(items[k::nb], tile_levels[level_id]) for k in range(nb) if items[k::nb]]
                level_tiles: dict = defaultdict(list)
                for part in executor_map(executor, drawing_levels.cut_batch, jobs, workers):
                    for key, entries in part.items():
                        level_tiles[key].extend(entries)
                drawn[level_id] = level_tiles
                step(f"Cut drawing level {level_id} into {len(level_tiles):,} drawing tiles")
        if before_records is not None:
            before_records()
        made = feature_records(records, geoms, None if workers == 1 else executor, workers)
        step(f"Made {len(made):,} feature records")
    writer = PackWriter(path)
    numbers = writer.add_features(made)
    number_of = [numbers[r["id"]] for r in records]
    entries_written = 0
    for (level, x, y) in sorted(encoded):
        entries = [(number_of[i], kind, data) for i, kind, data in encoded[(level, x, y)]]
        entries_written += len(entries)
        writer.add_tile(level, x, y, entries)
    drawing_entries = 0
    for level_id in sorted(drawn):
        for (x, y) in sorted(drawn[level_id]):
            entries = sorted(drawn[level_id][(x, y)], key=lambda e: e[0])
            drawing_entries += len(entries)
            writer.add_drawing_tile(level_id, x, y, [(number_of[i], kind, data) for i, kind, data in entries])
    if layers is None:
        layer_ids = list(dict.fromkeys(r["layer"] for r in records))
        layers = [{"id": layer, "name": LAYER_NAMES.get(layer, layer.title())} for layer in layer_ids]
    writer.finish(manifest, attribution if attribution is not None else spike_attribution(manifest), layers)
    levels = sorted({level for level, _x, _y in encoded})
    stats = {"bytes": path.stat().st_size, "tiles": len(encoded), "drawing_entries": drawing_entries, "entries": entries_written, "levels": levels,
             "seconds": time.perf_counter() - start}
    say(f"Wrote {path.name}: {stats['bytes'] / 1e6:.1f} MB, {stats['tiles']} pack tiles, {entries_written} tile "
        f"entries, in {stats['seconds']:.0f} seconds with {workers} worker process{'es' if workers != 1 else ''}.")
    return stats


def run_within_budget(executor, function, jobs: list, make, costs: list, budget: float, workers: int):
    """Results of function over jobs, as they finish, in jobs' order of starting: a job starts when a worker is
    free, memory allows, and the costs of the jobs running, its own added, are within budget; a job is always
    started when none is running. make(job) gives the job's arguments, only when it starts."""
    import concurrent.futures as cf

    from mapdata import parallel

    waiting = list(zip(costs, jobs))
    running: dict = {}
    while waiting or running:
        while waiting and len(running) < workers and parallel.room_for_another(len(running)):
            pick = next((k for k, (c, _j) in enumerate(waiting) if not running
                         or sum(running.values()) + c <= budget), None)
            if pick is None:
                break
            cost, job = waiting.pop(pick)
            running[executor.submit(function, make(job))] = cost
        done, _rest = cf.wait(list(running), return_when=cf.FIRST_COMPLETED)
        for future in done:
            running.pop(future)
            yield future.result()


def executor_map(executor, function, batches: list, workers: int):
    """Results of function over batches, a few at a time, holding back when memory is short (DP103)."""
    import concurrent.futures as cf

    from mapdata import parallel

    queue, running = list(batches), set()
    while queue or running:
        while queue and len(running) < workers + 1 and parallel.room_for_another(len(running)):
            running.add(executor.submit(function, queue.pop(0)))
        done, running = cf.wait(running, return_when=cf.FIRST_COMPLETED)
        for future in done:
            yield future.result()
