"""Write a spike S2 pack (architecture 8.2 stage 16, AD-5).

Each feature's exact shape is cut into tiles of the quadtree. A piece with
more than MAX_POINTS points is cut again into its four smaller tiles, so a
point test never decodes a large shape, however many islands a country has
(architecture 6.3, 6.12). A tile that lies wholly inside a feature stores only
a "covered" note.

The same features can be written with either shape encoding, so spike S2 can
compare WKB with compact coordinates (architecture 6.1).
"""
from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

import shapely

from mapcore.packs import archive

START_LEVEL = 3
MAX_LEVEL = 18
MAX_POINTS = 4000
# A pack tile is also split when all its tile entries together have more
# than this many points. Without it, spike S2 stage 2 put 332 of Norway's
# municipalities, 690,000 points and 2.9 MB, into one pack tile, and every
# lookup in southern Norway took 0.75 seconds.
TILE_POINTS = 20000


def _cut(geom, level: int, x: int, y: int, out: dict, index: int) -> None:
    """Cut one feature's shape into pack tiles. Tile entries keep the shape, encoded later."""
    box = shapely.box(*archive.tile_box(level, x, y))
    if shapely.contains_properly(geom, box):
        out[(level, x, y)].append((index, archive.COVERED, None))
        return
    piece = shapely.intersection(geom, box)
    piece = _areas(piece)
    if piece is None:
        return
    if shapely.equals(piece, box):
        out[(level, x, y)].append((index, archive.COVERED, None))
        return
    if shapely.get_num_coordinates(piece) > MAX_POINTS and level < MAX_LEVEL:
        for dx in (0, 1):
            for dy in (0, 1):
                _cut(piece, level + 1, 2 * x + dx, 2 * y + dy, out, index)
        return
    out[(level, x, y)].append((index, archive.WKB, piece))


def split_full_tiles(tiles: dict) -> None:
    """Split every pack tile whose tile entries together have more than TILE_POINTS points."""
    for level in range(START_LEVEL, MAX_LEVEL):
        for key in [k for k in tiles if k[0] == level]:
            entries = tiles[key]
            total = sum(shapely.get_num_coordinates(g) for _i, kind, g in entries if kind != archive.COVERED)
            if total <= TILE_POINTS:
                continue
            del tiles[key]
            _level, x, y = key
            for index, kind, g in entries:
                for dx in (0, 1):
                    for dy in (0, 1):
                        child = (level + 1, 2 * x + dx, 2 * y + dy)
                        if kind == archive.COVERED:
                            tiles[child].append((index, archive.COVERED, None))
                        else:
                            _cut(g, level + 1, child[1], child[2], tiles, index)


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


def encoder(name: str):
    if name == "wkb":
        return lambda g: (archive.WKB, shapely.to_wkb(g))
    if name == "compact":
        return lambda g: (archive.COMPACT, archive.encode_compact(g))
    raise ValueError(name)


def write(path: Path, manifest: dict, records: list[dict], geoms: list, encoding: str, say=print) -> dict:
    """Write the pack. Returns measurements: size, tiles, pieces, seconds."""
    start = time.perf_counter()
    tiles: dict = defaultdict(list)
    enc = encoder(encoding)
    for index, geom in enumerate(geoms):
        west, south, east, north = geom.bounds
        x0, y0 = archive.tile_of(west, south, START_LEVEL)
        x1, y1 = archive.tile_of(east, north, START_LEVEL)
        shapely.prepare(geom)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                _cut(geom, START_LEVEL, x, y, tiles, index)
    split_full_tiles(tiles)
    levels = sorted({level for level, _x, _y in tiles})
    writer = archive.Writer(path)
    writer.put_json("manifest", {**manifest, "encoding": encoding, "tile_levels": levels,
                                 "max_points_per_piece": MAX_POINTS})
    writer.put_json("features", records)
    pieces = 0
    for (level, x, y) in sorted(tiles):
        entries = sorted(((index, archive.COVERED, b"") if kind == archive.COVERED else (index, *enc(g)))
                         for index, kind, g in tiles[(level, x, y)])
        pieces += len(entries)
        writer.put(archive.tile_key(level, x, y), archive.encode_tile(entries))
    writer.close()
    stats = {"bytes": path.stat().st_size, "tiles": len(tiles), "pieces": pieces, "levels": levels,
             "seconds": time.perf_counter() - start}
    say(f"Wrote {path.name}: {stats['bytes'] / 1e6:.1f} MB, {stats['tiles']} pack tiles, {pieces} tile entries, "
        f"{stats['seconds']:.0f} seconds.")
    return stats


# Both encodings at once, in worker processes (DP103) ---------------------------

def _cut_batch(items: list) -> dict:
    """Cut a batch of features into pack tiles, in a worker: {tile: [(index, kind, WKB or None)]}."""
    tiles: dict = defaultdict(list)
    for index, wkb in items:
        geom = shapely.from_wkb(wkb)
        west, south, east, north = geom.bounds
        x0, y0 = archive.tile_of(west, south, START_LEVEL)
        x1, y1 = archive.tile_of(east, north, START_LEVEL)
        shapely.prepare(geom)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                _cut(geom, START_LEVEL, x, y, tiles, index)
    return {key: [(i, k, None if g is None else shapely.to_wkb(g)) for i, k, g in entries]
            for key, entries in tiles.items()}


def _encode_batch(batch: list) -> list:
    """Encode a batch of pack tiles both ways, in a worker: [(tile, WKB record, compact record, entries)]."""
    wkb_enc, compact_enc = encoder("wkb"), encoder("compact")
    out = []
    for key, entries in batch:
        a, b = [], []
        for index, kind, blob in entries:
            if kind == archive.COVERED:
                a.append((index, archive.COVERED, b""))
                b.append((index, archive.COVERED, b""))
            else:
                g = shapely.from_wkb(blob)
                a.append((index, *wkb_enc(g)))
                b.append((index, *compact_enc(g)))
        out.append((key, archive.encode_tile(sorted(a)), archive.encode_tile(sorted(b)), len(entries)))
    return out


def write_both(paths: dict, manifest: dict, records: list[dict], geoms: list, workers: int = 1, say=print) -> dict:
    """Write the pack with WKB and with compact coordinates, cutting the shapes only once.

    paths: {"wkb": path, "compact": path}. The cutting into pack tiles and
    the encoding are each split into batches run by worker processes; the
    main process joins the results, splits full pack tiles, and writes both
    files. Returns measurements for each encoding.
    """
    from mapdata import parallel

    start = time.perf_counter()
    order = sorted(range(len(geoms)), key=lambda i: -shapely.get_num_coordinates(geoms[i]))
    n_batches = max(1, min(len(order), workers * 4))
    batches = [[(i, shapely.to_wkb(geoms[i])) for i in order[k::n_batches]] for k in range(n_batches)]
    tiles: dict = defaultdict(list)
    with parallel.pool(workers) as executor:
        for part in executor_map(executor, _cut_batch, batches, workers):
            for key, entries in part.items():
                tiles[key].extend((i, k, None if b is None else shapely.from_wkb(b)) for i, k, b in entries)
        split_full_tiles(tiles)
        levels = sorted({level for level, _x, _y in tiles})
        keys = sorted(tiles)
        n_enc = max(1, min(len(keys), workers * 8))
        enc_batches = [[(key, [(i, k, None if g is None else shapely.to_wkb(g)) for i, k, g in tiles[key]])
                        for key in keys[j::n_enc]] for j in range(n_enc)]
        tiles.clear()
        encoded = {}
        for result in executor_map(executor, _encode_batch, enc_batches, workers):
            for key, rec_wkb, rec_compact, count in result:
                encoded[key] = (rec_wkb, rec_compact, count)
    stats = {}
    for slot, encoding in ((0, "wkb"), (1, "compact")):
        path = paths[encoding]
        writer = archive.Writer(path)
        writer.put_json("manifest", {**manifest, "encoding": encoding, "tile_levels": levels,
                                     "max_points_per_piece": MAX_POINTS, "max_points_per_tile": TILE_POINTS})
        writer.put_json("features", records)
        pieces = 0
        for (level, x, y) in sorted(encoded):
            rec = encoded[(level, x, y)]
            pieces += rec[2]
            writer.put(archive.tile_key(level, x, y), rec[slot])
        writer.close()
        stats[encoding] = {"bytes": path.stat().st_size, "tiles": len(encoded), "pieces": pieces, "levels": levels,
                           "seconds": time.perf_counter() - start}
        say(f"Wrote {path.name}: {stats[encoding]['bytes'] / 1e6:.1f} MB, {len(encoded)} pack tiles, "
            f"{pieces} tile entries.")
    say(f"Both packs written in {time.perf_counter() - start:.0f} seconds, with {workers} worker "
        f"process{'es' if workers != 1 else ''}, cutting each shape once.")
    return stats


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
