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


SEAM_TOLERANCE = 1e-9  # degrees, about 0.1 mm


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
        # The OSM land pieces overlap by a thin band, about 0.0005 degrees, at
        # each split line (found in spike S2), so a full union is needed, not a
        # coverage union.
        out = shapely.union_all(parts)
        # Where a border crosses a piece's edge, the cut adds a point on the
        # border that its neighbour does not get, so the two no longer meet
        # exactly (AD-16 needs them to). Those points lie on the border's line,
        # so removing points within SEAM_TOLERANCE of the line drops them and
        # moves nothing by more than about a tenth of a millimetre.
        out = shapely.simplify(out, SEAM_TOLERANCE, preserve_topology=True)
        return polygonal(shapely.make_valid(out) if not out.is_valid else out)


def polygonal(geom):
    """The areas of a shape, as one Polygon or MultiPolygon.

    make_valid and intersection can return a GeometryCollection holding stray
    lines and points as well as areas. Coverage tools accept only areas.
    """
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    parts = [p for p in shapely.get_parts(geom) if p.geom_type in ("Polygon", "MultiPolygon")]
    if not parts:
        return shapely.Polygon()
    polys = [q for p in parts for q in shapely.get_parts(p)]
    return polys[0] if len(polys) == 1 else shapely.MultiPolygon(polys)


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


def gaps(container, members: list, names: list[str], min_km2: float = 0.0001,
         name_from_km2: float = 0.01) -> list[Sliver]:
    """Land in the container that is in none of the members.

    Used two ways (architecture 6.12, "Slivers and gaps"):
    * the land near the countries, against all the clipped countries: land in no country;
    * a clipped country, against its clipped divisions: land in the country but in no division.
    Each piece is named after the member it shares the longest edge with,
    which is the one it would be given to. Pieces under name_from_km2
    (1 hectare) are listed without a name.
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
        c = p.representative_point()
        if km2 < name_from_km2:
            # Naming every sliver took most of a 30 minute run; small ones
            # are counted and measured, but not named.
            found.append(Sliver("not named, too small", km2, (c.x, c.y)))
            continue
        best, best_len = "none", 0.0
        # The overlap with a thin band round the piece measures the shared edge.
        # (A boundary is not used: make_valid can return a GeometryCollection,
        # which has none.)
        band = p.buffer(1e-6)
        for i in tree.query(band):
            if members[i].is_empty:
                continue
            shared = shapely.intersection(band, members[i]).area
            if shared > best_len:
                best, best_len = names[i], shared
        found.append(Sliver(best, km2, (c.x, c.y)))
    found.sort(key=lambda s: -s.area_km2)
    return found
