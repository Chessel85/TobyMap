"""The pack tile cache (architecture 10.1, spike S4, NFR-1).

It keeps the tile entries of the pack tiles and drawing tiles already read,
and the Shapely shapes already decoded from them, up to a size limit. The
least recently used pack tile goes first. Decoded shapes are never changed
once made, so background threads may read them while the main thread works.

The size is an estimate: the stored bytes of each tile entry, times a factor
for the decoded shape (about 16 bytes a point, and about 2 points a byte).
"""
from __future__ import annotations

import threading
from collections import OrderedDict

from mapcore.packs import coords, tiles

DECODED_FACTOR = 24  # estimated bytes in memory per stored byte, once decoded
TILE_OVERHEAD = 256  # estimated bytes for the tile's own bookkeeping
DEFAULT_LIMIT = 96 * 1024 * 1024


class TileData:
    """The tile entries of one pack tile or drawing tile, with their shapes
    decoded when first asked for."""

    __slots__ = ("entries", "by_feature", "shapes", "cost", "owner", "drawing", "some")

    def __init__(self, entries: list[tiles.TileEntry]):
        self.entries = entries
        self.by_feature: dict[int, list[int]] = {}
        for i, e in enumerate(entries):
            self.by_feature.setdefault(e.feature, []).append(i)
        self.shapes: dict[int, object] = {}
        self.cost = TILE_OVERHEAD + sum(len(e.data) + 16 for e in entries)
        self.owner = None  # the cache that holds this tile, told when shapes are decoded
        self.drawing = None  # every shape of the tile, decoded at once, for the map scene (P2-T14c)
        self.some = None  # shapes of single entries decoded by shapes_of, unprepared

    def shapes_of(self, indices, box) -> dict:
        """The shapes of some entries, by entry index, unprepared, as drawing_shapes
        would give them. A tile the map has not drawn decodes only these: the visible
        rule needs a few small areas from a tile that may also hold every road."""
        if self.drawing is not None:
            geoms = self.drawing[0]
            return {i: geoms[i] for i in indices}
        import shapely

        some = self.some
        if some is None:
            some = self.some = {}
        missing = [i for i in indices if i not in some and i not in self.shapes]
        for kind, decode in ((tiles.COMPACT, coords.to_shapes), (tiles.LINES, coords.to_line_shapes),
                             (tiles.POINTS, coords.to_point_shapes)):
            these = [i for i in missing if self.entries[i].kind == kind]
            if these:
                for i, shape in zip(these, decode([self.entries[i].data for i in these])):
                    some[i] = shape
        for i in missing:
            if self.entries[i].kind == tiles.COVERED:
                some[i] = shapely.box(*box)
        grown = sum(len(self.entries[i].data) for i in missing) * DECODED_FACTOR
        if grown:
            self.cost += grown
            if self.owner is not None:
                self.owner.grew(grown)
        return {i: self.shapes[i] if i in self.shapes else some[i] for i in indices}

    def drawing_shapes(self, box) -> tuple:
        """Every entry as a Shapely shape, decoded in one go, in entry order: an
        array of shapes, and the feature number of each. A covered note is the
        tile's box. Kept with the tile, so a drawing decodes a tile only once."""
        got = self.drawing
        if got is None:
            import numpy as np
            import shapely

            geoms = np.empty(len(self.entries), object)
            # Shapes a lookup has already decoded, such as for "where am I", are used as they are.
            # So are those the visible rule decoded on their own.
            done = dict(self.some or {})
            done.update(self.shapes)
            for i, shape in done.items():
                geoms[i] = shape
            compact = [i for i, e in enumerate(self.entries) if e.kind != tiles.COVERED and i not in done]
            for kind, decode in ((tiles.COMPACT, coords.to_shapes), (tiles.LINES, coords.to_line_shapes),
                                 (tiles.POINTS, coords.to_point_shapes)):
                these = [i for i in compact if self.entries[i].kind == kind]
                if these:
                    geoms[these] = decode([self.entries[i].data for i in these])
            for i, e in enumerate(self.entries):
                if e.kind == tiles.COVERED:
                    geoms[i] = shapely.box(*box)
            numbers = np.fromiter((e.feature for e in self.entries), np.int64, len(self.entries))
            got = self.drawing = (geoms, numbers)
            grown = sum(len(self.entries[i].data) for i in compact) * DECODED_FACTOR
            self.cost += grown
            if self.owner is not None:
                self.owner.grew(grown)
        return got

    def shape(self, i: int):
        """The decoded, prepared Shapely shape of entry i; None for a covered note."""
        entry = self.entries[i]
        if entry.kind == tiles.COVERED:
            return None
        shape = self.shapes.get(i)
        if shape is None:
            import shapely

            if entry.kind == tiles.LINES:
                shape = coords.to_line_shapes([entry.data])[0]
            elif entry.kind == tiles.POINTS:
                shape = coords.to_point_shapes([entry.data])[0]
            else:
                shape = coords.to_shape(entry.data)
            shapely.prepare(shape)
            self.shapes[i] = shape
            grown = len(entry.data) * DECODED_FACTOR
            self.cost += grown
            if self.owner is not None:
                self.owner.grew(grown)
        return shape


class TileCache:
    def __init__(self, limit_bytes: int = DEFAULT_LIMIT):
        self.limit = limit_bytes
        self._items: OrderedDict[tuple, TileData] = OrderedDict()
        self._lock = threading.RLock()
        self._total = 0
        self.hits = 0
        self.misses = 0

    @property
    def size(self) -> int:
        return self._total

    def grew(self, nbytes: int) -> None:
        """A tile in the cache has decoded a shape. The tile is trimmed later, at the next get."""
        with self._lock:
            self._total += nbytes

    def __len__(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._total = 0

    def get(self, key: tuple, load) -> TileData:
        """The cached tile for key, or load() stored in the cache. load
        returns a TileData; it runs under the lock, so a tile is read once."""
        with self._lock:
            found = self._items.get(key)
            if found is not None:
                self._items.move_to_end(key)
                self.hits += 1
                self._trim(keep=key)
                return found
            self.misses += 1
            data = load()
            data.owner = self
            self._items[key] = data
            self._total += data.cost
            self._trim(keep=key)
            return data

    def _trim(self, keep) -> None:
        # The tile just asked for stays, even if it alone is over the limit.
        while self._total > self.limit and len(self._items) > 1:
            key = next(iter(self._items))
            if key == keep:
                self._items.move_to_end(key)
                continue
            gone = self._items.pop(key)
            gone.owner = None  # a shape decoded later in a tile that was let go is not counted
            self._total -= gone.cost
