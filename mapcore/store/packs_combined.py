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


# Features and relationships merged (P4-T3b) ------------------------------------------------------------------
#
# The match stage (P4-T1h) gives a regional feature the world pack's identifier where both packs hold it, keeping
# its own as an alias, and every record naming it names the world's identifier. So the packs hold one feature
# under one identifier, and the store merges its records and relationships:
#
# * The first record is the most detailed pack's that holds the whole feature (not partial); when every pack holds
#   only part of it, the world pack's, else the most detailed pack's. Its area, bounding box, point and its other
#   fields are the feature's; a field only another record has, such as the world's facts, is added.
# * The first record's pack answers alone for the layers it is the authority on: a regional pack holding the
#   whole feature, for its coverage's layers; the world pack, or a pack holding only part, for all its layers.
#   From the other packs only what concerns other layers is added, such as the parishes in the United Kingdom,
#   or the towns in Hampshire.
# * A record of only part of the feature says nothing about where the whole lies, how long its outline is, or its
#   coast's stretches: its "in", "same", "overlaps" and "partly", and its whole-feature members, are not taken.

PLACEMENT = ("in", "same", "overlaps", "partly")   # where the feature lies: an id is in at most one of them
NEIGHBOURS = ("next", "near")                      # an id is in at most one of them
ORDERED = ("crosses",)                             # in order from the line's start
COUNTED = ("counts", "held")                       # by layer
BY_ID = ("crossed_by", "along", "partly_by", "coast", "shores", "lake_shore", "crossed_at")
WHOLE = ("outline_km", "coast_stretches", "water_in")   # about the whole feature, taken only from a whole record


def _id_of(entry):
    return entry[0] if isinstance(entry, (list, tuple)) else entry


def merge_records(first: dict, others) -> dict:
    """The feature's record: the first record, with each field only another record has added, and the aliases of
    them all. Whether it is partial is the first record's."""
    out = dict(first)
    aliases = set(first.get("aliases") or ())
    for rec in others:
        aliases.update(rec.get("aliases") or ())
        for key, value in rec.items():
            if key not in out and key != "partial":
                out[key] = value
    if aliases:
        out["aliases"] = sorted(aliases)
    return out


def merge_relationships(first: dict, others, authority, layer_of) -> dict:
    """The feature's relationships, merged (docs/developer/pack-format.md, relations/G): the first record's, with
    what each of `others`, (relationships, partial) pairs in order, says about features of layers outside
    `authority`, the layers the first record's pack answers for alone. `layer_of(id)` gives a feature's layer."""
    out = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v) for k, v in first.items()}

    def takes(identifier) -> bool:
        return layer_of(identifier) not in authority

    def add_group(keys, rel):
        mentioned = {_id_of(e) for k in keys for e in out.get(k, ())}
        for k in keys:
            for entry in rel.get(k, ()):
                i = _id_of(entry)
                if i not in mentioned and takes(i):
                    out.setdefault(k, []).append(entry)
                    mentioned.add(i)

    for rel, partial in others:
        if not rel:
            continue
        if not partial:
            add_group(PLACEMENT, rel)
        add_group(NEIGHBOURS, rel)
        for k in BY_ID:
            if k in rel and (k in out or k != "partly_by"):   # no partly_by means a pack written before it
                add_group((k,), rel)
        for k in ORDERED:
            if k in rel:
                out[k] = _ordered_merge(out.get(k, []), [i for i in rel[k] if takes(i)])
        for k in COUNTED:
            if k in rel and (k in out or k == "counts"):
                mine = out.setdefault(k, {})
                for layer, n in rel[k].items():
                    if layer not in authority and layer not in mine:
                        mine[layer] = n
        if not partial:
            for k in WHOLE:
                if k in rel and k not in out:
                    out[k] = rel[k]
    return out


def _ordered_merge(first: list, other: list) -> list:
    """The ids of `first` in their order, with each id only `other` has put after the id before it in `other`,
    so a line's areas from its start stay in order: the River Itchen's parishes between its counties."""
    out = list(first)
    have = set(out)
    after = None
    for i in other:
        if i in have:
            after = i
            continue
        at = out.index(after) + 1 if after is not None else 0
        # after the ids already put after `after`, so two new ids keep their order
        while at < len(out) and out[at] not in first:
            at += 1
        out.insert(at, i)
        have.add(i)
        after = i
    return out
