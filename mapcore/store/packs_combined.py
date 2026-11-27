"""Several packs open together: which pack answers where (P4-T3a; PLT-4, PCK-2, AD-14, architecture 6.8).

A regional pack's manifest names its coverage (docs/developer/pack-format.md): the covered pack tiles, as
"level/x/y", and the layers it answers for in them. Inside a covered pack tile, a regional pack answers for
those layers, and the world pack's features of those layers are left out there; for every other layer, such as
the continents, and everywhere outside the coverage, the world pack answers. Nothing is said about missing
detail (PLT-4): where no regional pack covers a point, the world pack simply answers.

The most detailed pack wins: regional packs are put before the world pack, the finest coverage (the highest
tile level) first, and a pack hides the features of a layer where an earlier pack covers the point and holds
that layer.

For a point, each coverage looks up the pack tile holding it at each tile level its tiles use: a few set
lookups, made from the tiles at start-up, so it costs nothing against NFR-1. For the drawing, the coverage's
shape within a tile, the union of its covered pack tiles there, is cut out of the world pack's shapes of the
covered layers, made once a tile and kept.
"""
from __future__ import annotations

import threading

from mapcore.packs import tiles


class Coverage:
    """A regional pack's coverage, from its manifest's coverage member."""

    def __init__(self, member: dict):
        self.region = member.get("region", "")
        self.tile_level = int(member.get("tile_level", 0))
        self.layers = frozenset(member.get("layers") or ())
        self.draw_below_km = float(member.get("draw_below_km") or 0.0)
        by_level: dict[int, set] = {}
        for text in member.get("tiles") or ():
            level, x, y = (int(v) for v in str(text).split("/"))
            by_level.setdefault(level, set()).add((x, y))
        self.by_level = by_level
        self.levels = sorted(by_level)
        boxes = [tiles.tile_box(level, x, y) for level in self.levels for x, y in by_level[level]]
        if boxes:
            self.bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                         max(b[2] for b in boxes), max(b[3] for b in boxes))
        else:
            self.bbox = None
        self._shape = None
        self._parts: dict[tuple, object] = {}
        self._lock = threading.RLock()   # a prepared shape is not safe from two threads at once

    def covers(self, lat: float, lon: float) -> bool:
        """Whether the point is in a covered pack tile."""
        if self.bbox is None:
            return False
        west, south, east, north = self.bbox
        if not (south <= lat <= north and west <= lon <= east):
            return False
        for level in self.levels:
            if tiles.tile_of(lon, lat, level) in self.by_level[level]:
                return True
        return False

    def meets_box(self, box) -> bool:
        """Whether the coverage's bounding box meets a box (west, south, east, north)."""
        if self.bbox is None:
            return False
        west, south, east, north = self.bbox
        return box[0] <= east and box[2] >= west and box[1] <= north and box[3] >= south

    @property
    def shape(self):
        """The union of the covered pack tiles (Shapely), made once."""
        with self._lock:
            if self._shape is None:
                import shapely

                boxes = [shapely.box(*tiles.tile_box(level, x, y)) for level in self.levels
                         for x, y in sorted(self.by_level[level])]
                self._shape = shapely.union_all(boxes) if boxes else shapely.GeometryCollection()
                shapely.prepare(self._shape)
            return self._shape

    def part_in(self, box):
        """The coverage within a box: None when they do not meet, True when it fills the box, else its shape
        there. Made once a box and kept."""
        key = tuple(round(v, 9) for v in box)
        with self._lock:
            if key in self._parts:
                return self._parts[key]
            got = None
            if self.meets_box(box):
                import shapely

                cell = shapely.box(*box)
                shape = self.shape
                if shape.contains(cell):
                    got = True
                elif shape.intersects(cell):
                    part = shapely.intersection(shape, cell)
                    got = None if part.is_empty or part.area == 0 else part
            self._parts[key] = got
            return got

    def contains_boxes(self, boxes):
        """For each box (an array of west, south, east, north), whether it lies wholly in the coverage."""
        import numpy as np
        import shapely

        out = np.zeros(len(boxes), bool)
        if self.bbox is None or not len(boxes):
            return out
        west, south, east, north = self.bbox
        maybe = (boxes[:, 0] >= west) & (boxes[:, 2] <= east) & (boxes[:, 1] >= south) & (boxes[:, 3] <= north)
        rows = np.nonzero(maybe)[0]
        if len(rows):
            b = boxes[rows]
            with self._lock:
                out[rows] = shapely.contains(self.shape, shapely.box(b[:, 0], b[:, 1], b[:, 2], b[:, 3]))
        return out


def coverage_of(pack) -> Coverage | None:
    """A pack's coverage, or None for a world pack (or a pack whose coverage has no tiles listed)."""
    member = (getattr(pack, "manifest", None) or {}).get("coverage") or {}
    # A coverage with no tiles is the form left "to be settled in Phase 4", which packs written by tests and
    # spike S2 still carry as {"kind": "region"}: such a pack answers everywhere, as before.
    if member.get("kind") != "region" or "tiles" not in member:
        return None
    return Coverage(member)


def detail_order(packs) -> list[int]:
    """The packs' positions, most detailed first: regional packs by their coverage's tile level, finest first,
    then the world packs, each group keeping the order given (which on the desktop is by file name)."""
    def key(k: int):
        cov = coverage_of(packs[k])
        return (0, -cov.tile_level, k) if cov is not None else (1, 0, k)

    return sorted(range(len(packs)), key=key)
