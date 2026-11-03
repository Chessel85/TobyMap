"""Areas and lengths on the Earth for the pipeline's reports.

Areas are worked out on the WGS 84 ellipsoid: each latitude is converted to
its authalic latitude, which maps the ellipsoid onto a sphere of the same
total area with every area kept, and the shape is then projected with the
Lambert azimuthal equal-area projection centred on the shape. Long straight
edges are first divided into short ones, so edges along a meridian, such as
the 180 degree line, follow the Earth (spike S2 stage 3, AD-17).

The sums are the core's own, in mapcore.geo.geodesy, so the pipeline and the
application measure the Earth the same way (P1-T1, AD-7). Distances are on
the ellipsoid with GeographicLib.
"""
from __future__ import annotations

import numpy as np
import shapely

from mapcore.geo import geodesy as _core

A_KM = _core.A_M / 1000
R_AUTHALIC_KM = _core.R_AUTHALIC_M / 1000
authalic_lat = _core.authalic_lat


def _laea(lon, lat, lon0, lat0, radius):
    return _core.laea(lon, lat, lon0, lat0, radius)


def area_km2(geom) -> float:
    """Area on the WGS 84 ellipsoid, in square kilometres."""
    if geom.is_empty:
        return 0.0
    geom = shapely.segmentize(geom, 0.25)
    c = geom.centroid
    lon0, lat0 = c.x, float(authalic_lat(np.array(c.y)))

    def project(coords):
        x, y = _laea(coords[:, 0], authalic_lat(coords[:, 1]), lon0, lat0, R_AUTHALIC_KM)
        return np.stack([x, y], axis=1)

    return float(shapely.transform(geom, project).area)


def areas_km2(geoms) -> np.ndarray:
    """The area of each shape in an array, on the WGS 84 ellipsoid, in one go.

    The same sums as area_km2, each shape projected about its own centre, but
    for all the shapes in a few array operations instead of one Python call
    each. Norway's land has 118,845 parts, so measuring them one at a time
    was slow (spike S2).
    """
    geoms = np.asarray(geoms, dtype=object)
    out = np.zeros(len(geoms))
    if len(geoms) == 0:
        return out
    empty = shapely.is_empty(geoms)
    live = np.nonzero(~empty)[0]
    if len(live) == 0:
        return out
    seg = shapely.segmentize(geoms[live], 0.25)
    centres = shapely.centroid(geoms[live])
    lon0 = shapely.get_x(centres)
    lat0 = authalic_lat(shapely.get_y(centres))
    coords, which = shapely.get_coordinates(seg, return_index=True)
    x, y = _laea(coords[:, 0], authalic_lat(coords[:, 1]), lon0[which], lat0[which], R_AUTHALIC_KM)
    projected = shapely.set_coordinates(seg, np.stack([x, y], axis=1))
    out[live] = shapely.area(projected)
    return out


def distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """The shortest distance over the ellipsoid, for reports. Longitude first,
    as in shapely."""
    return _core.distance_m(lat1, lon1, lat2, lon2) / 1000
