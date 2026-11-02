"""Areas and lengths on the Earth for the pipeline's reports.

Areas are worked out on the WGS 84 ellipsoid: each latitude is converted to
its authalic latitude, which maps the ellipsoid onto a sphere of the same
total area with every area kept, and the shape is then projected with the
Lambert azimuthal equal-area projection centred on the shape. Long straight
edges are first divided into short ones, so edges along a meridian, such as
the 180 degree line, follow the Earth (spike S2 stage 3, AD-17).

Spike version: the full pipeline uses GeographicLib (AD-7).
"""
from __future__ import annotations

import math

import numpy as np
import shapely

A_KM = 6378.137
F = 1 / 298.257223563
E2 = F * (2 - F)
E = math.sqrt(E2)
R_KM = 6371.0088  # mean radius, for distances in reports


def _q(sin_phi: np.ndarray) -> np.ndarray:
    return (1 - E2) * (sin_phi / (1 - E2 * sin_phi ** 2)
                       - (1 / (2 * E)) * np.log((1 - E * sin_phi) / (1 + E * sin_phi)))


Q_POLE = float(_q(np.array(1.0)))
R_AUTHALIC_KM = A_KM * math.sqrt(Q_POLE / 2)


def authalic_lat(lat_deg: np.ndarray) -> np.ndarray:
    """Authalic latitude in degrees."""
    ratio = np.clip(_q(np.sin(np.radians(lat_deg))) / Q_POLE, -1.0, 1.0)
    return np.degrees(np.arcsin(ratio))


def _laea(lon: np.ndarray, lat: np.ndarray, lon0: float, lat0: float, radius: float):
    lam, phi = np.radians(lon - lon0), np.radians(lat)
    phi0 = np.radians(lat0)
    denom = 1 + np.sin(phi0) * np.sin(phi) + np.cos(phi0) * np.cos(phi) * np.cos(lam)
    k = np.sqrt(2 / np.maximum(denom, 1e-12))
    x = radius * k * np.cos(phi) * np.sin(lam)
    y = radius * k * (np.cos(phi0) * np.sin(phi) - np.sin(phi0) * np.cos(phi) * np.cos(lam))
    return x, y


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


def distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great circle distance on the mean sphere, for reports."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_KM * math.asin(min(1.0, math.sqrt(h)))
