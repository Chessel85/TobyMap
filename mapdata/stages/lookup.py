"""What is at a point in a pack, for the pipeline's checks (DMT-2).

The application's own lookup comes with the store (P1-T5). This one is for
checking builds: mapdata inspect, the spike S2 stages' check places and the
comparison program. It reads pack tiles through the core's pack reader, at
most one at each tile level, and can keep decoded pack tiles in a cache.
"""
from __future__ import annotations

from pathlib import Path

import shapely

from mapcore.packs import coords, tiles
from mapcore.packs.pack import Pack


def open_pack(path) -> Pack:
    """A pack opened for checking: the application version is not checked."""
    return Pack(Path(path), check_app=False)


class Lookup:
    def __init__(self, pack: Pack, cache: bool = False):
        self.pack = pack
        self.cache: dict | None = {} if cache else None

    def _entries(self, level: int, x: int, y: int) -> list:
        key = (level, x, y)
        if self.cache is not None and key in self.cache:
            return self.cache[key]
        # Only areas are "at" a point; lines and points (pack format 3) are left out, as in the store.
        entries = [(e.feature, None if e.kind == tiles.COVERED else coords.to_shape(e.data))
                   for e in self.pack.tile(level, x, y) if e.kind not in (tiles.LINES, tiles.POINTS)]
        if self.cache is not None:
            self.cache[key] = entries
        return entries

    def at(self, lon: float, lat: float) -> list[dict]:
        """Every feature at the point, smallest first (LOC-2)."""
        point = shapely.Point(lon, lat)
        found = []
        for level in self.pack.tile_levels:
            for number, geom in self._entries(level, *tiles.tile_of(lon, lat, level)):
                if geom is None or shapely.intersects(geom, point):
                    found.append(self.pack.feature(number))
        found.sort(key=lambda f: (f["area_km2"], f["id"]))
        return found


def at(pack: Pack, lon: float, lat: float) -> list[dict]:
    return Lookup(pack).at(lon, lat)
