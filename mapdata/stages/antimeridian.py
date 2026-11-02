"""Checks for shapes that cross the 180 degree line (architecture 6.13, AD-17).

OSM stores such shapes split at the line, so a country like Fiji is a
collection of parts, some with longitudes near +180 and some near -180. These
helpers work out a bounding box and centre across the line, move the parts
together for an isolated drawing, and measure the artificial edges along the
line, which must never be announced as a border or coast.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely

from mapdata.stages.geodesy import distance_km

LINE_TOLERANCE = 1e-7  # degrees


@dataclass
class WrapBox:
    west: float    # may be greater than east when the box crosses the line
    south: float
    east: float
    north: float
    width: float   # degrees of longitude covered, 360 for a shape round the pole

    @property
    def crosses(self) -> bool:
        return self.west > self.east

    @property
    def round_the_world(self) -> bool:
        return self.width >= 359.999


def _intervals(geom) -> list[tuple[float, float]]:
    out = []
    for p in shapely.get_parts(geom):
        w, _s, e, _n = p.bounds
        out.append((w, e))
    return sorted(out)


def wrap_box(geom) -> WrapBox:
    """The smallest box in longitude, allowed to cross the 180 degree line.

    The longitudes covered by the parts are merged; the largest stretch of
    longitude with no part is left outside the box.
    """
    _w, south, _e, north = geom.bounds
    merged: list[list[float]] = []
    for w, e in _intervals(geom):
        if merged and w <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([w, e])
    if not merged:
        return WrapBox(0, 0, 0, 0, 0)
    # Gaps between merged stretches, including the one round the back across the line.
    gaps = [(merged[i + 1][0] - merged[i][1], merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1)]
    gaps.append((merged[0][0] + 360 - merged[-1][1], merged[-1][1], merged[0][0]))
    size, gap_start, gap_end = max(gaps)
    if size <= LINE_TOLERANCE:
        return WrapBox(-180.0, south, 180.0, north, 360.0)
    return WrapBox(gap_end, south, gap_start, north, 360.0 - size)


def shifted(geom, box: WrapBox | None = None):
    """The shape with parts west of the line moved by 360 degrees, so a shape
    that crosses the line is one compact group (for isolated drawing, VIS-2)."""
    box = box or wrap_box(geom)
    if not box.crosses:
        return geom
    parts = []
    for p in shapely.get_parts(geom):
        if p.bounds[2] <= box.east + LINE_TOLERANCE:
            p = shapely.transform(p, lambda c: c + np.array([360.0, 0.0]))
        parts.append(p)
    return shapely.union_all(parts) if len(parts) > 1 else parts[0]


def normalise_lon(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


@dataclass
class Centre:
    lon: float
    lat: float
    in_shape: bool
    snapped_lon: float  # the nearest point of the shape, if the centre is not in it
    snapped_lat: float
    snap_km: float


def centre(geom, box: WrapBox | None = None) -> Centre:
    """The centre of the wrap-aware box, and whether it is on the shape.

    A shape round the pole (Antarctica) has the pole as its centre. If the
    centre is in the sea, the nearest point of the shape is given too, which
    is what hierarchy mode or a search would jump to.
    """
    box = box or wrap_box(geom)
    if box.round_the_world:
        lat = -89.999 if box.south < -89 else (89.999 if box.north > 89 else (box.south + box.north) / 2)
        lon = 0.0
    else:
        east = box.east + 360 if box.crosses else box.east
        lon = normalise_lon((box.west + east) / 2)
        lat = (box.south + box.north) / 2
    pt = shapely.Point(lon, lat)
    if shapely.intersects(geom, pt):
        return Centre(lon, lat, True, lon, lat, 0.0)
    near = shapely.shortest_line(geom, pt).coords[0]
    return Centre(lon, lat, False, near[0], near[1], distance_km(lon, lat, near[0], near[1]))


@dataclass
class LineEdges:
    east_km: float     # length of edges lying on +180
    west_km: float     # length of edges lying on -180
    pole_edges: int    # edges lying along the South Pole's latitude, which have no length
    unmatched_km: float  # edges on one side with no matching edge on the other


def _edges_on(geom, test) -> list[tuple[float, float]]:
    """Latitude ranges of edges whose two ends both pass test(lon, lat)."""
    out = []
    for p in shapely.get_parts(geom):
        for ring in [p.exterior, *p.interiors]:
            c = np.asarray(ring.coords)
            a, b = c[:-1], c[1:]
            hit = test(a) & test(b)
            for (lo_a, la_a), (lo_b, la_b) in zip(a[hit], b[hit]):
                out.append((min(la_a, la_b), max(la_a, la_b)))
    return out


def _merge(ranges):
    merged = []
    for lo, hi in sorted(ranges):
        if merged and lo <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return merged


def _km_of(ranges) -> float:
    return sum(hi - lo for lo, hi in ranges) * 111.2


def line_edges(geom) -> LineEdges:
    """Edges along the 180 degree line, and along the South Pole, which are artificial.

    Every edge on +180 should be matched by one on -180 over the same
    latitudes, because the line only splits the shape; unmatched lengths show
    a fault.
    """
    east = _merge(_edges_on(geom, lambda c: np.abs(c[:, 0] - 180) < LINE_TOLERANCE))
    west = _merge(_edges_on(geom, lambda c: np.abs(c[:, 0] + 180) < LINE_TOLERANCE))
    pole_edges = len(_edges_on(geom, lambda c: c[:, 1] < -90 + LINE_TOLERANCE))
    e_union = shapely.union_all([shapely.LineString([(0, lo), (0, hi)]) for lo, hi in east]) if east else None
    w_union = shapely.union_all([shapely.LineString([(0, lo), (0, hi)]) for lo, hi in west]) if west else None
    if e_union is None and w_union is None:
        unmatched = 0.0
    elif e_union is None or w_union is None:
        unmatched = ((e_union or w_union).length) * 111.2
    else:
        unmatched = shapely.symmetric_difference(e_union, w_union).length * 111.2
    return LineEdges(_km_of(east), _km_of(west), pole_edges, unmatched)
