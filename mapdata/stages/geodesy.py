"""Areas and lengths on the Earth for the pipeline's reports.

Spike version: areas are worked out on an equal-area projection centred on
each shape (Lambert azimuthal equal-area on the mean-radius sphere), which is
within a fraction of a percent of the ellipsoid for country-sized shapes. The
ellipsoid with GeographicLib comes with the full pipeline (AD-7).
"""
from __future__ import annotations

import numpy as np
import shapely

R_KM = 6371.0088


def _laea(lon: np.ndarray, lat: np.ndarray, lon0: float, lat0: float):
    lam, phi = np.radians(lon - lon0), np.radians(lat)
    phi0 = np.radians(lat0)
    k = np.sqrt(2 / (1 + np.sin(phi0) * np.sin(phi) + np.cos(phi0) * np.cos(phi) * np.cos(lam)))
    x = R_KM * k * np.cos(phi) * np.sin(lam)
    y = R_KM * k * (np.cos(phi0) * np.sin(phi) - np.sin(phi0) * np.cos(phi) * np.cos(lam))
    return x, y


def area_km2(geom) -> float:
    if geom.is_empty:
        return 0.0
    c = geom.centroid
    lon0, lat0 = c.x, c.y

    def project(coords):
        x, y = _laea(coords[:, 0], coords[:, 1], lon0, lat0)
        return np.stack([x, y], axis=1)

    return float(shapely.transform(geom, project).area)
