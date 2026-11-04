"""A flat view around the location, in metres, for choosing the nearest point.

Near the equator and the middle latitudes it is geodesy.LocalProjection. Within
HIGH_LAT degrees of a pole, where a degree of longitude shrinks to nothing, it
is an azimuthal equidistant projection on the mean sphere, which has no
trouble at the pole. Either way the nearest point is only chosen here; the
distance and bearing that are announced are measured on the ellipsoid.
"""
from __future__ import annotations

import math

import numpy as np

from mapcore.geo import geodesy

HIGH_LAT = 80.0


class Flat:
    """Metres east and north of a centre, for arrays of latitude and longitude."""

    def __init__(self, lat: float, lon: float):
        self.lat0, self.lon0 = lat, lon
        self.polar = abs(lat) >= HIGH_LAT
        self._local = None if self.polar else geodesy.LocalProjection(lat, lon)
        self._p0 = math.radians(lat)

    def forward(self, lat, lon):
        if not self.polar:
            return self._local.forward(lat, lon)
        p = np.radians(np.asarray(lat, dtype=np.float64))
        dl = np.radians((np.asarray(lon, dtype=np.float64) - self.lon0 + 180.0) % 360.0 - 180.0)
        cos_c = np.clip(math.sin(self._p0) * np.sin(p) + math.cos(self._p0) * np.cos(p) * np.cos(dl), -1.0, 1.0)
        c = np.arccos(cos_c)
        az = np.arctan2(np.sin(dl) * np.cos(p),
                        math.cos(self._p0) * np.sin(p) - math.sin(self._p0) * np.cos(p) * np.cos(dl))
        r = geodesy.R_MEAN_M * c
        return r * np.sin(az), r * np.cos(az)

    def inverse(self, x, y):
        """(lat, lon) in degrees."""
        if not self.polar:
            return self._local.inverse(x, y)
        x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        c = np.hypot(x, y) / geodesy.R_MEAN_M
        az = np.arctan2(x, y)
        sin_p = np.clip(math.sin(self._p0) * np.cos(c) + math.cos(self._p0) * np.sin(c) * np.cos(az), -1.0, 1.0)
        p = np.arcsin(sin_p)
        dl = np.arctan2(np.sin(az) * np.sin(c) * math.cos(self._p0),
                        np.cos(c) - math.sin(self._p0) * sin_p)
        return np.degrees(p), (self.lon0 + np.degrees(dl) + 180.0) % 360.0 - 180.0

    def transform(self, geom):
        """A Shapely shape given in longitude and latitude, in metres."""
        import shapely

        def move(c):
            x, y = self.forward(c[:, 1], c[:, 0])
            return np.column_stack([x, y])

        return shapely.transform(geom, move)
