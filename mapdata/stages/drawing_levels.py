"""Drawing levels: simplified shapes for the zooms, and their drawing tiles (P1-T4, architecture 6.9, AD-16).

For each drawing level in the write stage's settings, every layer is
simplified as one coverage, so neighbours in the layer meet exactly at that
level, and parts of an area too small to see at the level are left out. The
largest part of every area is always kept, so no area vanishes. The
simplified shapes are then cut into drawing tiles of the level's tile level.
The exact shapes in the pack tiles are never changed (AD-5), and lookups and
distances never use drawing tiles.

Each level in the settings has:

* tolerance_m: how far the simplified outline may move, in metres.
* min_km2: parts smaller than this are left out (the largest part stays).
* tile_level: the tile level of its drawing tiles.
* view_km: the level serves views whose radius is at least this many
  kilometres; the core picks the finest level whose view_km is not more than
  the view radius, and the exact pack tiles when none is.

A frame should stay near 10,000 points (VIS-1); the build reports the points
of each level so the figure can be checked.
"""
from __future__ import annotations

import math

import numpy as np
import shapely

from mapcore.packs import coords, tiles

METRES_PER_DEGREE = 111_320.0
COVERED, SHAPE = tiles.COVERED, tiles.COMPACT


def simplify_layer(geoms: list, tolerance_m: float, min_km2: float, together: bool = True) -> list:
    """One layer's shapes simplified together as a coverage, with small parts left out.
    Lines are simplified one by one, and points are kept as they are (P2-T10a). With together
    false, as for a layer whose areas overlap, such as the mountain ranges and the ranges
    inside them, each area is simplified on its own (P3-T1e): a coverage must not overlap. That
    is done the plain way, then repaired: simplifying that keeps the shape valid as it goes took
    222 seconds for the trial's 0.9 million points of continents, and the plain way 0.1 seconds."""
    if not geoms:
        return []
    if not together:
        return [g if g is None or shapely.get_type_id(g) not in (3, 6) else
                drop_small(polygonal(shapely.simplify(g, tolerance_m / METRES_PER_DEGREE, preserve_topology=False)),
                           min_km2) for g in geoms]
    if not all(shapely.get_type_id(g) in (3, 6) for g in geoms if g is not None):
        return [g if g is None or shapely.get_type_id(g) not in (1, 2, 5)
                else shapely.simplify(g, tolerance_m / METRES_PER_DEGREE, preserve_topology=False) for g in geoms]
    arr = np.empty(len(geoms), dtype=object)
    arr[:] = geoms
    out = shapely.coverage_simplify(arr, tolerance_m / METRES_PER_DEGREE, simplify_boundary=True)
    return [drop_small(g, min_km2) for g in out]


def polygonal(g):
    """The areas of a shape made valid, as one Polygon or MultiPolygon: simplifying can leave lines behind."""
    g = shapely.make_valid(g)
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = [q for p in shapely.get_parts(g) for q in shapely.get_parts(p) if q.geom_type == "Polygon"]
    if not parts:
        return shapely.Polygon()
    return parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)


def drop_small(g, min_km2: float):
    """The parts of a shape of at least min_km2 (roughly, by area in degrees), and always the largest part.
    Holes smaller than min_km2 are filled too: in a sea, they are the islands left out, and they would keep
    millions of points that nothing could see."""
    if g is None or g.is_empty:
        return g
    parts = shapely.get_parts(g)
    areas = shapely.area(parts)
    lat = np.radians(shapely.get_coordinates(shapely.centroid(parts))[:, 1])
    scale = (METRES_PER_DEGREE / 1000) ** 2
    km2 = areas * scale * np.cos(lat)
    keep = km2 >= min_km2
    keep[int(np.argmax(areas))] = True
    kept = []
    for part in parts[keep]:
        if shapely.get_num_interior_rings(part):
            cos = math.cos(math.radians(part.centroid.y))
            holes = [h for h in part.interiors if shapely.Polygon(h).area * scale * cos >= min_km2]
            if len(holes) != shapely.get_num_interior_rings(part):
                part = shapely.Polygon(part.exterior, holes)
        kept.append(part)
    return kept[0] if len(kept) == 1 else shapely.MultiPolygon(kept)


def _clip(geom, bounds, kind=SHAPE, level=0, x=0, y=0):
    from mapdata.stages.pack_write import cut_to_rect, keep_kind, points_in_tile

    if kind == tiles.POINTS:
        return keep_kind(points_in_tile(geom, level, x, y), kind)
    return keep_kind(cut_to_rect(geom, bounds), kind)


def _cut(geom, level: int, x: int, y: int, target: int, out: dict, index: int) -> None:
    """Cut a shape (already clipped to tile level/x/y) down to the target tile level."""
    from mapdata.stages.pack_write import encode, entry_kind

    kind = entry_kind(geom)
    if kind != SHAPE:   # a line or points: no covered notes
        if level == target:
            out.setdefault((x, y), []).append((index, kind, encode(kind, geom)))
            return
        for dx in (0, 1):
            for dy in (0, 1):
                cx, cy = 2 * x + dx, 2 * y + dy
                inside = _clip(geom, tiles.tile_box(level + 1, cx, cy), kind, level + 1, cx, cy)
                if inside is not None:
                    _cut(inside, level + 1, cx, cy, target, out, index)
        return
    if level == target:
        box = shapely.box(*tiles.tile_box(level, x, y))
        if abs(geom.area - box.area) <= 1e-12 * box.area and shapely.equals(geom, box):
            out.setdefault((x, y), []).append((index, COVERED, b""))
        else:
            out.setdefault((x, y), []).append((index, SHAPE, coords.encode(coords.rings_of(geom))))
        return
    shapely.prepare(geom)
    for dx in (0, 1):
        for dy in (0, 1):
            cx, cy = 2 * x + dx, 2 * y + dy
            bounds = tiles.tile_box(level + 1, cx, cy)
            if shapely.contains_properly(geom, shapely.box(*bounds)):
                n = 2 ** (target - level - 1)
                for ix in range(n):
                    for iy in range(n):
                        out.setdefault((cx * n + ix, cy * n + iy), []).append((index, COVERED, b""))
                continue
            inside = _clip(geom, bounds)
            if inside is not None:
                _cut(inside, level + 1, cx, cy, target, out, index)


def cut_batch(args) -> dict:
    """A batch of shapes cut into drawing tiles, in a worker: {(x, y): [(index, kind, bytes)]}."""
    items, target = args
    out: dict = {}
    for index, wkb in items:
        geom = shapely.from_wkb(wkb)
        if geom is None or geom.is_empty:
            continue
        _cut(geom, 0, 0, 0, target, out, index)
    return out


def points(geoms: list) -> int:
    return int(sum(shapely.get_num_coordinates(g) for g in geoms if g is not None))
