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


def _cut(geom, level: int, x: int, y: int, out: dict, index: int, encode) -> None:
    box = shapely.box(*archive.tile_box(level, x, y))
    if shapely.contains_properly(geom, box):
        out[(level, x, y)].append((index, archive.COVERED, b""))
        return
    piece = shapely.intersection(geom, box)
    piece = _areas(piece)
    if piece is None:
        return
    if shapely.equals(piece, box):
        out[(level, x, y)].append((index, archive.COVERED, b""))
        return
    if shapely.get_num_coordinates(piece) > MAX_POINTS and level < MAX_LEVEL:
        for dx in (0, 1):
            for dy in (0, 1):
                _cut(piece, level + 1, 2 * x + dx, 2 * y + dy, out, index, encode)
        return
    kind, data = encode(piece)
    out[(level, x, y)].append((index, kind, data))


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
                _cut(geom, START_LEVEL, x, y, tiles, index, enc)
    levels = sorted({level for level, _x, _y in tiles})
    writer = archive.Writer(path)
    writer.put_json("manifest", {**manifest, "encoding": encoding, "tile_levels": levels,
                                 "max_points_per_piece": MAX_POINTS})
    writer.put_json("features", records)
    pieces = 0
    for (level, x, y) in sorted(tiles):
        entries = sorted(tiles[(level, x, y)])
        pieces += len(entries)
        writer.put(archive.tile_key(level, x, y), archive.encode_tile(entries))
    writer.close()
    stats = {"bytes": path.stat().st_size, "tiles": len(tiles), "pieces": pieces, "levels": levels,
             "seconds": time.perf_counter() - start}
    say(f"Wrote {path.name}: {stats['bytes'] / 1e6:.1f} MB, {stats['tiles']} tiles, {pieces} pieces, "
        f"{stats['seconds']:.0f} seconds.")
    return stats
