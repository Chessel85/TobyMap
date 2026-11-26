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
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapcore.geo import geodesy
from mapcore.packs import coords, tiles
from mapcore.packs.pack import PackWriteError, PackWriter
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
    """Tile entries as the main process keeps them (P4-T1l): (index, kind, WKB or None, points), so a full pack
    tile is found without decoding its parts."""
    return [(i, k, None, 0) if g is None else (i, k, shapely.to_wkb(g), int(shapely.get_num_coordinates(g)))
            for i, k, g in entries]


def _shape_entries(entries) -> list:
    return [(i, k, None if b is None else shapely.from_wkb(b)) for i, k, b, *_n in entries]


def _split_batch(jobs: list) -> list:
    """Full pack tiles split, in a worker or here: [(key, entries)] gives [(pack tile, entries)]."""
    out: dict = defaultdict(list)
    for key, entries in jobs:
        _split_tile(key, _shape_entries(entries), out)
    return [(k, _wkb_entries(v)) for k, v in out.items()]


def split_full_tiles(cut: dict, executor=None, workers: int = 1) -> int:
    """Split every pack tile whose tile entries together have more than TILE_POINTS points, a tile level at a
    time. cut holds the entries as _wkb_entries makes them. With an executor, the full pack tiles of a level are
    split in the workers. The entries of each pack tile are put in feature order afterwards, so the order the
    workers finish in does not matter. Returns how many pack tiles were split."""
    split = 0
    for level in range(START_LEVEL, MAX_LEVEL):
        full = [k for k in sorted(k for k in cut if k[0] == level)
                if sum(e[3] for e in cut[k] if e[1] != COVERED) > TILE_POINTS]
        if not full:
            continue
        split += len(full)
        jobs = [(key, cut.pop(key)) for key in full]
        if executor is None:
            parts = [_split_batch(jobs)]
        else:
            # Each full pack tile's entries in runs, so a level with one or two full pack tiles, as a region's
            # first levels have, is still shared among the workers: two thirds of the rehearsal's writing was one
            # worker splitting (P4-T1m). Each entry is cut on its own, and the runs are joined in their order, so
            # each smaller pack tile gets its entries in the same order as before.
            per_tile = max(1, (workers * 4) // len(jobs))
            runs = []
            for key, entries in jobs:
                size = max(1, math.ceil(len(entries) / per_tile))
                runs += [[(key, entries[a:a + size])] for a in range(0, len(entries), size)]
            del jobs
            queue = list(enumerate(runs))
            del runs
            done: dict[int, list] = {}
            for at, part in executor_map(executor, _split_run, queue, workers, consume=True):
                done[at] = part
            parts = [done[at] for at in sorted(done)]
        for part in parts:
            for key, entries in part:
                cut[key].extend(entries)
    return split


def _split_run(job) -> tuple[int, list]:
    at, run = job
    return at, _split_batch(run)


def count_held(records: list[dict], relationships: dict[str, dict], layer_of=None) -> int:
    """Each area's "held": how many features of each layer are wholly inside it, by layer id, those whose "in"
    holds it (item 4a of the plan 2 ledger). Hierarchy mode's Down lists only these (P3-T29c), so its "in all" is
    made from them; "counts" keeps those partly inside too, the number Ctrl+Shift+F lists. "in" allows the build's
    full_share and measures land areas in land areas on land (P3-T28n), and takes in a condominium's owners, so
    this runs after share_condominiums. An island in a water by its shore (contents.waters_round) is in both the
    water's "held" and its "counts" (P3-T32g), as the manifest's islands_in_water says. Changes `relationships` in
    place; returns how many areas hold something. layer_of, if given, is each identifier's layer, in place of the
    records; relationships may be a spill.RelStore, whose items are read from disk (P4-T1m)."""
    from mapcore.store import contents

    if layer_of is None:
        layer_of = {r["id"]: r["layer"] for r in records}
    held: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for identifier, rel in relationships.items():
        layer = layer_of.get(identifier)
        if layer is None:
            continue
        for area in set(rel.get("in", ())):
            held[area][layer] += 1
        if layer in contents.ISLE_LAYERS:   # an island in the water round it, by its shore (P3-T32g)
            before = contents.holders(rel)   # what the relationships stage's "counts" took in
            for area in contents.waters_round(rel):
                if area not in rel.get("in", ()):
                    held[area][layer] += 1
                if area not in before:
                    counts = relationships.setdefault(area, {}).setdefault("counts", {})
                    counts[layer] = counts.get(layer, 0) + 1
                    relationships[area]["counts"] = dict(sorted(counts.items()))
    for area, by_layer in held.items():
        relationships.setdefault(area, {})["held"] = dict(sorted(by_layer.items()))
    # An area with counts but nothing wholly inside: an empty "held", not none, so the application knows the pack
    # has them. Found first, then changed, as a RelStore's items are copies.
    empty = [fid for fid, rel in relationships.items() if "counts" in rel and "held" not in rel]
    for fid in empty:
        relationships.setdefault(fid, {}).setdefault("held", {})
    return len(held)


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
    return ({key: _wkb_entries(entries) for key, entries in cut.items()},
            [("children", i, lv, x, y, shapely.to_wkb(g)) for i, lv, x, y, g in defer])


def start_tiles(geom) -> tuple[int, int, int, int]:
    """The first and last pack tile, x and y, at START_LEVEL, that a shape's bounds reach."""
    west, south, east, north = geom.bounds
    x0, y0 = tiles.tile_of(west, south, START_LEVEL)
    x1, y1 = tiles.tile_of(east, north, START_LEVEL)
    return x0, y0, x1, y1


def wkb_of(geoms, i: int, g=None) -> bytes:
    """Shape i's well-known binary: as stored, for shapes read from a stage's folder (features.DiskShapes), which
    is the same bytes as encoding the decoded shape again; else encoded."""
    if hasattr(geoms, "blob"):
        return geoms.blob(i)
    return shapely.to_wkb(geoms[i] if g is None else g)


def cut_jobs(geoms: list, workers: int) -> list[list]:
    """The first jobs of the cut, in batches: each feature over DEFER_POINTS points one job per start pack tile,
    alone in its batch, the largest first; the rest in batches of about the same number of points."""
    big, small = [], []
    for i, g in enumerate(geoms):
        n = shapely.get_num_coordinates(g)
        if n > DEFER_POINTS:
            wkb = wkb_of(geoms, i, g)
            x0, y0, x1, y1 = start_tiles(g)
            big += [(n, [("tile", i, x, y, wkb)]) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
        else:
            small.append((n, i))
    small.sort(key=lambda s: (-s[0], s[1]))
    n_batches = max(1, min(len(small), workers * 4))
    batches = [[(i, wkb_of(geoms, i)) for _n, i in small[k::n_batches]] for k in range(n_batches)]
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
                          for index, kind, blob, *_n in entries]))
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
    out.setdefault("source", sys.intern(record["id"].split(":")[0]))
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
          drawing_geoms: dict[int, list] | None = None, executor=None, before_records=None,
          relationships: dict[str, dict] | None = None, search: dict | None = None, in_place: bool = False,
          ids: list[str] | None = None, index_of: dict[str, int] | None = None, records_first: bool = True) -> dict:
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
    relationships, if given, are each feature's relationships by id (P3-T3e), written beside the feature records:
    a dictionary, or a spill.RelStore (P4-T1m).
    search, if given, makes the search index (P3-T8a, mapdata.stages.search_index): {"sites": {id: how many
    Wikimedia sites have it}, "settings": the index's settings}.
    in_place: each of records is let go (set to None) once its feature record is made, to save memory (P4-T1l).
    ids and index_of, if given, are the records' identifiers in order and each one's place, made once by the
    caller. records_first: the feature records are made before the cutting, so records are let go before it;
    otherwise after, so slow areas measured in the background have the cutting's time to finish.

    Kinder to memory (P4-T1m): the feature records, the relationships and the compressed pack tiles are set aside
    on disk, in a folder beside the pack that is deleted at the end, and written a group at a time. In memory are
    the identifiers, the records of the areas of the world tree and condominiums, and the search index's rows.

    A progress line is written after each step, so a long step is seen to move (DMT-2).

    Returns measurements: bytes, pack tiles, tile entries, tile levels, seconds.
    """
    import contextlib
    import tempfile

    from mapdata import parallel

    start = time.perf_counter()

    def step(text: str) -> None:
        say(f"{text}, {time.perf_counter() - start:.0f} seconds into writing the pack.")

    path = Path(path)
    manifest = full_manifest(manifest)
    if ids is None:
        ids = [r["id"] for r in records]
    if index_of is None:
        index_of = {fid: i for i, fid in enumerate(ids)}
    if len(index_of) != len(ids):
        seen: set[str] = set()
        twice = next(f for f in ids if f in seen or seen.add(f))
        raise PackWriteError(f"feature {twice} is given twice")
    numbering = Numbering(ids, index_of)
    n = len(ids)
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=f".{path.stem}-writing-") as tmp:
        made = _Made(n, Path(tmp))
        try:
            with (contextlib.nullcontext(executor) if executor is not None else parallel.pool(workers)) as executor:
                pool = None if workers == 1 else executor

                def records_step():
                    if before_records is not None:
                        before_records()
                    make_records(records, geoms, pool, workers, made.take, in_place)
                    step(f"Made {n:,} feature records")

                if records_first:
                    records_step()
                tiles_made = _pack_tiles(geoms, executor, workers, numbering, Path(tmp), step)
                drawn = _drawing_tiles(drawing_geoms, manifest, executor, workers, step)
                if not records_first:
                    records_step()
            return _finish(path, manifest, made, numbering, tiles_made, drawn, relationships, search, layers,
                           attribution, workers, say, step, start)
        finally:
            made.close()


class Numbering:
    """Each feature's number, as PackWriter.add_features gives them, from the identifiers alone (P4-T1m): in groups
    by feature_group, and by identifier in each group. Answers `in`, [] and len, as the writer's numbers."""

    def __init__(self, ids: list[str], index_of: dict[str, int]):
        from mapcore.packs.pack import GROUP_SIZE, feature_group

        n = len(ids)
        self.ids, self.index_of = ids, index_of
        self.groups = max(1, math.ceil(n / GROUP_SIZE))
        group = np.fromiter((feature_group(f, self.groups) for f in ids), dtype=np.int64, count=n)
        counts = np.bincount(group, minlength=self.groups)
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.int64)
        self.group_starts = [int(s) for s in starts]
        by_group = np.argsort(group, kind="stable")
        del group
        self.order = np.empty(n, dtype=np.int64)   # the feature at each number
        for g in range(self.groups):
            a, b = self.group_starts[g], self.group_starts[g] + int(counts[g])
            members = by_group[a:b].tolist()
            members.sort(key=ids.__getitem__)
            self.order[a:b] = members
        self.number_of = np.empty(n, dtype=np.int64)   # each feature's number, by its place in ids
        self.number_of[self.order] = np.arange(n, dtype=np.int64)
        self.counts = counts

    def members(self, g: int) -> list[int]:
        a = self.group_starts[g]
        return self.order[a:a + int(self.counts[g])].tolist()

    def __len__(self) -> int:
        return len(self.ids)

    def __contains__(self, fid) -> bool:
        return fid in self.index_of

    def __getitem__(self, fid) -> int:
        return int(self.number_of[self.index_of[fid]])


KEPT_LAYERS = ("continents", "countries", "regions", "counties")   # contents.TREE_LAYERS, held in memory


class _Made:
    """The feature records as they are made, set aside on disk (P4-T1m), with each one's layer, and the records of
    the world tree's layers and the condominiums held, which the tree and share_condominiums read."""

    def __init__(self, n: int, folder: Path):
        from mapdata.pipeline.spill import Spill

        self.spill = Spill(n, folder, "features")
        self.layer: list[str | None] = [None] * n
        self.kept: dict[int, dict] = {}

    def take(self, i: int, layer: str, keep: bool, data: bytes) -> None:
        import pickle

        self.spill.put_bytes(i, data)
        self.layer[i] = sys.intern(layer)
        if keep:
            self.kept[i] = pickle.loads(data)

    def record(self, i: int) -> dict:
        got = self.kept.get(i)
        return got if got is not None else self.spill.get(i)

    def kept_records(self) -> list[dict]:
        return [self.kept[i] for i in sorted(self.kept)]

    def close(self) -> None:
        self.spill.close()


def _keep(rec: dict) -> bool:
    return rec["layer"] in KEPT_LAYERS or rec.get("type") == "condominium"


def _made(i: int, rec: dict) -> tuple:
    import pickle

    from mapdata.pipeline.spill import PROTOCOL

    return i, rec["layer"], _keep(rec), pickle.dumps(rec, PROTOCOL)


def make_records(records: list[dict], geoms: list, executor=None, workers: int = 1, take=None,
                 in_place: bool = False) -> None:
    """feature_record for each feature, in the workers when there is an executor, in batches of about the same
    number of points: take(index, layer, whether it is kept in memory, the record pickled) for each, in the order
    they are made. With in_place, each of records is let go once its record is made (P4-T1m)."""
    if executor is None:
        for i, g in enumerate(geoms):
            take(*_made(i, feature_record(records[i], g)))
            if in_place:
                records[i] = None
        return
    n = max(1, min(len(records), workers * 4))
    points = [int(shapely.get_num_coordinates(g)) for g in geoms]
    order = sorted(range(len(records)), key=lambda i: -points[i])
    del points
    jobs = [order[k::n] for k in range(n) if order[k::n]]
    del order
    for part in run_within_budget(executor, _records_batch, jobs,
                                  lambda job: [(i, records[i], wkb_of(geoms, i)) for i in job],
                                  [0] * len(jobs), 0, workers):
        for item in part:
            take(*item)
            if in_place:
                records[item[0]] = None


def feature_records(records: list[dict], geoms: list, executor=None, workers: int = 1,
                    in_place: bool = False) -> list[dict]:
    """feature_record for each feature, as make_records makes them, as a list; with in_place, in records."""
    import pickle

    out: list = records if in_place else [None] * len(records)

    def take(i, _layer, _keep, data):
        out[i] = pickle.loads(data)
    make_records(records, geoms, executor, workers, take)
    return out


def _records_batch(items: list) -> list:
    return [_made(i, feature_record(r, shapely.from_wkb(b))) for i, r, b in items]


def _stored_batch(args) -> list:
    """Pack tiles encoded and made into their records, compressed, in a worker (P4-T1m): [(place, key, stored, check,
    entries)] for [(place, key, [(feature number, kind, WKB or None, points)])]."""
    from mapcore.packs.pack import stored_tile

    batch, count = args
    out = []
    for place, key, entries in batch:
        coded = [(number, COVERED, b"") if kind == COVERED else (number, kind, encode(kind, shapely.from_wkb(blob)))
                 for number, kind, blob, *_n in entries]
        stored, check = stored_tile(coded, key[0], count)
        out.append((place, key, stored, check, len(coded)))
    return out


def _pack_tiles(geoms, executor, workers: int, numbering: Numbering, folder: Path, step) -> dict:
    """Cut every feature into pack tiles, split the full ones, and make each pack tile's record in the workers, set
    aside on disk (P4-T1m). Returns {"keys": the pack tiles in order, "spill": their records, "checks", "entries"}."""
    from mapdata.pipeline.spill import Spill

    cut: dict = defaultdict(list)

    def merge(part):   # kept as the workers give them, never decoded here (P4-T1l)
        for key, entries in part.items():
            cut[key].extend(entries)

    handed = run_cut(executor, cut_jobs(geoms, workers), workers, merge)
    step(f"Cut {len(geoms):,} features into {len(cut):,} pack tiles, with {handed:,} large parts shared "
         "among the workers")
    n_split = split_full_tiles(cut, None if workers == 1 else executor, workers)
    step(f"Split {n_split:,} full pack tiles")
    keys = sorted(cut)
    number_of = numbering.number_of
    count = len(numbering)
    jobs = []
    for place, key in enumerate(keys):
        entries = cut.pop(key)
        entries.sort(key=lambda e: e[0])   # feature order, as before, then each given its feature number
        jobs.append((place, key, [(int(number_of[e[0]]), *e[1:]) for e in entries]))
    n_enc = max(1, min(len(jobs), workers * 8))
    batches = [b for b in ((jobs[j::n_enc], count) for j in range(n_enc)) if b[0]]
    del jobs
    spill = Spill(len(keys), folder, "tiles")
    checks = [0] * len(keys)
    entries_made = 0
    try:
        for result in executor_map(executor, _stored_batch, batches, workers, consume=True):
            for place, _key, stored, check, n_entries in result:
                spill.put_bytes(place, stored)
                checks[place] = check
                entries_made += n_entries
    except BaseException:
        spill.close()
        raise
    step(f"Encoded {len(keys):,} pack tiles")
    return {"keys": keys, "spill": spill, "checks": checks, "entries": entries_made}


def _drawing_tiles(drawing_geoms, manifest: dict, executor, workers: int, step) -> dict:
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
    return drawn


class _Slim:
    """Each feature's identifier and layer, as small records, for contents.contents, read as often as asked."""

    def __init__(self, ids: list[str], layers: list[str]):
        self.ids, self.layers = ids, layers

    def __iter__(self):
        for fid, layer in zip(self.ids, self.layers):
            yield {"id": fid, "layer": layer}


def _finish(path, manifest, made: _Made, numbering: Numbering, tiles_made: dict, drawn: dict, relationships, search,
            layers, attribution, workers, say, step, start) -> dict:
    """The relationships, contents and search index, then the pack written a group at a time."""
    from mapcore.store import contents

    ids, index_of = numbering.ids, numbering.index_of

    class _LayerOf:   # each identifier's layer, for count_held
        @staticmethod
        def get(fid):
            i = index_of.get(fid)
            return None if i is None else made.layer[i]

    if relationships:   # a condominium inside each of its owners, by the core's rule, before anything reads them (P3-T28f)
        kept = made.kept_records()
        owners = {o for r in kept if r.get("type") == "condominium" for o in r.get("owners") or ()}
        have = {r["id"] for r in kept}
        kept += [made.record(index_of[o]) for o in sorted(owners) if o in index_of and o not in have]
        if contents.share_condominiums(kept, relationships):
            step("Put each condominium inside its owners")
        held = count_held(None, relationships, _LayerOf())
        step(f"Counted what is wholly inside each of {held:,} areas")
    index = None
    if search is not None:   # P3-T8a: from the feature records, with their final ids, points and areas
        from mapdata.stages import search_index

        index_rows = search_index.rows(
            (made.record(i) for i in range(len(ids))), relationships, search.get("sites") or {},
            search.get("settings"), lookup=lambda fid: made.record(index_of[fid]) if fid in index_of else None)
        n_buckets, filed = search_index.buckets(
            index_rows, search_index.settings_of(search.get("settings"))["bucket_rows"])
        index = (n_buckets, filed, len(index_rows))
        n_rows, n_named = len(index_rows), len({r[2] for r in index_rows})
        del index_rows   # filed holds them; only the counts are said (P4-T1l)
        step(f"Made the search index: {n_rows:,} names of {n_named:,} features, in {n_buckets:,} search records")
    writer = PackWriter(path)
    writer.add_feature_groups(
        numbering.group_starts,
        ((g, [made.record(i) for i in numbering.members(g)]) for g in range(numbering.groups)
         if numbering.counts[g]),
        numbering)
    if relationships:   # P3-T3e: by id, beside the feature records, a group at a time (P4-T1m)
        extra = getattr(relationships, "extra", None)
        unknown = sorted(extra if extra is not None else (f for f in relationships if f not in index_of))
        if unknown:
            raise PackWriteError(f"relationships of features not in the pack: {', '.join(unknown[:5])}")

        def per_group():
            for g in range(numbering.groups):
                by_id = {}
                for i in numbering.members(g):
                    rel = relationships.get(ids[i])
                    if rel:
                        by_id[ids[i]] = rel
                yield g, by_id
        writer.add_relationship_groups(per_group())
        # P3-T20c, DP194: the world tree and what each area of its layers holds, by the core's own rules.
        rel_of = lambda fid: relationships.get(fid) or {}   # noqa: E731
        rows = {r["id"]: r for r in made.kept_records() if r["layer"] in contents.TREE_LAYERS}
        tree = contents.build_tree(rows, rel_of)
        holds = contents.contents(_Slim(ids, made.layer), rel_of, numbering)
        writer.add_contents({k: sorted(v) for k, v in sorted(tree.items())}, contents.tree_names(rows, tree), holds)
        step(f"Stored the world tree, {sum(len(v) for v in tree.values()):,} items, and what {len(holds):,} areas "
             f"hold, {sum(len(n) for h in holds.values() for n, _p in h.values()):,} features in all")
    if index is not None:
        writer.add_search(*index)
        del index
    keys, spill, checks = tiles_made["keys"], tiles_made["spill"], tiles_made["checks"]
    try:
        for place, (level, x, y) in enumerate(keys):
            writer.add_stored_tile(level, x, y, spill.get_bytes(place), checks[place])
    finally:
        spill.close()
    number_of = numbering.number_of
    drawing_entries = 0
    for level_id in sorted(drawn):
        for (x, y) in sorted(drawn[level_id]):
            entries = sorted(drawn[level_id][(x, y)], key=lambda e: e[0])
            drawing_entries += len(entries)
            writer.add_drawing_tile(level_id, x, y, [(int(number_of[i]), kind, data) for i, kind, data in entries])
    if layers is None:
        layer_ids = list(dict.fromkeys(made.layer))
        layers = [{"id": layer, "name": LAYER_NAMES.get(layer, layer.title())} for layer in layer_ids]
    writer.finish(manifest, attribution if attribution is not None else spike_attribution(manifest), layers)
    levels = sorted({level for level, _x, _y in keys})
    entries_written = tiles_made["entries"]
    stats = {"bytes": path.stat().st_size, "tiles": len(keys), "drawing_entries": drawing_entries,
             "entries": entries_written, "levels": levels, "seconds": time.perf_counter() - start}
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


def executor_map(executor, function, batches: list, workers: int, consume: bool = False):
    """Results of function over batches, a few at a time, holding back when memory is short (DP103). With consume,
    batches is emptied as each is sent, so what each holds is let go once it is done (P4-T1l)."""
    import concurrent.futures as cf

    from mapdata import parallel

    queue, running = (batches if consume else list(batches)), set()
    while queue or running:
        while queue and len(running) < workers + 1 and parallel.room_for_another(len(running)):
            running.add(executor.submit(function, queue.pop(0)))
        done, running = cf.wait(running, return_when=cf.FIRST_COMPLETED)
        for future in done:
            yield future.result()
