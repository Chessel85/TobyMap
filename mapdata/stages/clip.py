"""Clip: cut land areas to the land polygons (architecture 8.2 stage 5, AD-15, DAT-3).

Every administrative area is intersected with the OSM land polygons. Whatever
water a boundary includes, territorial waters, estuaries or bays, is removed,
and areas whose boundaries already follow the coast are unchanged. The same
cut is applied at every level, so countries, regions and counties line up
with each other and with the coast.

Land that is inside a country's original boundary but in none of the clipped
countries is a sliver. Slivers are measured and listed, for the quality report.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely

from mapdata.stages.geodesy import area_km2


class Land:
    """The land pieces with a spatial index."""

    def __init__(self, pieces: np.ndarray):
        self.pieces = pieces
        self.tree = shapely.STRtree(pieces)

    def clip(self, geom) -> object:
        """The land part of an area."""
        if geom.is_empty:
            return geom
        shapely.prepare(geom)
        idx = self.tree.query(geom, predicate="intersects")
        if len(idx) == 0:
            return shapely.Polygon()
        candidates = self.pieces[idx]
        inside = shapely.contains_properly(geom, candidates)
        whole = candidates[inside]
        cut = shapely.intersection(candidates[~inside], geom)
        cut = cut[~shapely.is_empty(cut)]
        parts = np.concatenate([whole, _polygons_only(cut)])
        if len(parts) == 0:
            return shapely.Polygon()
        # The land pieces never overlap, so a coverage union is safe and fast.
        try:
            out = shapely.coverage_union_all(parts)
        except shapely.errors.GEOSException:
            out = shapely.union_all(parts)
        return shapely.make_valid(out) if not out.is_valid else out


def _polygons_only(geoms: np.ndarray) -> np.ndarray:
    """Intersections can leave lines and points where shapes touch; keep areas."""
    out = []
    for g in geoms:
        if g.geom_type in ("Polygon", "MultiPolygon"):
            out.append(g)
        elif g.geom_type == "GeometryCollection":
            out.extend(p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon"))
    return np.array(out, dtype=object)


@dataclass
class Sliver:
    near: str          # the name of the country it touches most
    area_km2: float
    centre: tuple[float, float]  # lon, lat


def gaps(container, members: list, names: list[str], min_km2: float = 0.0001) -> list[Sliver]:
    """Land in the container that is in none of the members.

    Used two ways (architecture 6.12, "Slivers and gaps"):
    * the land near the countries, against all the clipped countries: land in no country;
    * a clipped country, against its clipped divisions: land in the country but in no division.
    Each piece is named after the member it shares the longest edge with,
    which is the one it would be given to.
    """
    members_union = shapely.union_all([m for m in members if not m.is_empty])
    gap = shapely.difference(container, members_union)
    found = []
    if gap.is_empty:
        return found
    tree = shapely.STRtree(np.array(members, dtype=object))
    for p in shapely.get_parts(gap):
        if p.geom_type != "Polygon":
            continue
        km2 = area_km2(p)
        if km2 < min_km2:
            continue
        best, best_len = "none", 0.0
        for i in tree.query(p.buffer(1e-6)):
            shared = shapely.intersection(p.buffer(1e-6), members[i].boundary).length
            if shared > best_len:
                best, best_len = names[i], shared
        c = p.representative_point()
        found.append(Sliver(best, km2, (c.x, c.y)))
    found.sort(key=lambda s: -s.area_km2)
    return found
