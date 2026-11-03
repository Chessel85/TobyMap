"""Geodesy on the WGS 84 ellipsoid (AD-7, architecture 5.2 and 7.1).

Every distance, bearing and step is worked out on the ellipsoid with
GeographicLib, which is pure Python, so the same code runs on the desktop and
in Pyodide. NumPy is used for the sums done over many points at once: areas,
the local projection and the rough distances used to rank candidates.

Longitudes: positions are given and returned in the range above -180 up to
180, except the points of a move's path, which carry on past the 180 degree
line so that neighbouring points are never 360 degrees apart (AD-17).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from geographiclib.geodesic import Geodesic

WGS84 = Geodesic.WGS84
A_M = Geodesic.WGS84.a            # equatorial radius, metres
F = Geodesic.WGS84.f              # flattening
E2 = F * (2 - F)                  # first eccentricity squared
E = math.sqrt(E2)
R_MEAN_M = 6371008.8              # mean radius, for rough work only

# The most a path point may be from the next, so a path follows the Earth.
PATH_SPACING_M = 10_000.0
PATH_MAX_POINTS = 257


# Longitudes and distances ------------------------------------------------------------

def wrap_lon(lon: float) -> float:
    """Longitude in the range above -180 up to 180."""
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    return 180.0 if wrapped == -180.0 else wrapped


def inverse(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float, float]:
    """Distance in metres, the bearing at the start and the bearing on arrival.

    Bearings are degrees clockwise from north, from 0 up to 360.
    """
    g = WGS84.Inverse(lat1, lon1, lat2, lon2)
    return g["s12"], g["azi1"] % 360.0, g["azi2"] % 360.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The shortest distance over the ellipsoid, in metres (INF-3)."""
    return WGS84.Inverse(lat1, lon1, lat2, lon2, Geodesic.DISTANCE)["s12"]


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The bearing from point 1 to point 2 at point 1, clockwise from north."""
    return WGS84.Inverse(lat1, lon1, lat2, lon2, Geodesic.AZIMUTH)["azi1"] % 360.0


def rough_distances_m(lat: float, lon: float, lats, lons) -> np.ndarray:
    """Distances from one point to many, on the mean sphere, to within about
    half a percent. For ranking candidates quickly; the exact distance of the
    ones kept comes from distance_m."""
    p1 = math.radians(lat)
    p2 = np.radians(np.asarray(lats, dtype=np.float64))
    dl = np.radians(np.asarray(lons, dtype=np.float64) - lon)
    h = np.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R_MEAN_M * np.arcsin(np.minimum(1.0, np.sqrt(h)))


def meridian_to_pole_m(lat: float, north: bool) -> float:
    """The distance along the meridian from a latitude to the North or South Pole."""
    return WGS84.Inverse(lat, 0.0, 90.0 if north else -90.0, 0.0, Geodesic.DISTANCE)["s12"]


def parallel_radius_m(lat: float) -> float:
    """The radius of the line of latitude through lat, in metres."""
    phi = math.radians(lat)
    return A_M * math.cos(phi) / math.sqrt(1 - E2 * math.sin(phi) ** 2)


# Moving ------------------------------------------------------------------------------

@dataclass(frozen=True)
class Move:
    """Where a move went, the path it followed, and the heading on arrival.

    path holds (lat, lon) points from the start to the end, no more than
    PATH_SPACING_M apart, so it follows the curve of the Earth. Its
    longitudes carry on past the 180 degree line (see the module notes).
    """
    lat: float
    lon: float
    heading: float
    path: tuple[tuple[float, float], ...]


def _path_count(metres: float) -> int:
    # 1% spare: equal steps of latitude differ in length by up to about 1%.
    return min(PATH_MAX_POINTS, max(2, math.ceil(abs(metres) / (PATH_SPACING_M * 0.99)) + 1))


def step_meridian(lat: float, lon: float, metres: float) -> Move | None:
    """Move north (metres above 0) or south (below 0) along the meridian.

    A move that would reach or pass a pole is refused with None, so the caller
    can play the blocked sound (NAV-1).
    """
    north = metres > 0
    if metres == 0:
        return Move(lat, wrap_lon(lon), 0.0, ((lat, lon), (lat, lon)))
    if abs(metres) >= meridian_to_pole_m(lat, north):
        return None
    end = WGS84.Direct(lat, 0.0, 0.0 if north else 180.0, abs(metres), Geodesic.LATITUDE)["lat2"]
    # Every point on the meridian has its longitude, so evenly spaced latitudes
    # follow it exactly; only the end needs the ellipsoid's sums. This keeps a
    # long step well inside the 1 ms budget (architecture 10.1).
    n = _path_count(metres)
    path = tuple((lat + (end - lat) * i / (n - 1), lon) for i in range(n))
    return Move(end, wrap_lon(lon), 0.0 if north else 180.0, path)


def step_parallel(lat: float, lon: float, metres: float) -> Move | None:
    """Move east (metres above 0) or west (below 0) along the line of latitude.

    The change in longitude is the distance divided by the radius of that line
    of latitude (architecture 7.1). At a pole there is no line of latitude, so
    the move is refused with None.
    """
    radius = parallel_radius_m(lat)
    if radius < 1.0:
        return None
    dlon = math.degrees(metres / radius)
    n = _path_count(metres)
    path = tuple((lat, lon + dlon * i / (n - 1)) for i in range(n))
    return Move(lat, wrap_lon(lon + dlon), 90.0 if metres >= 0 else 270.0, path)


def step_geodesic(lat: float, lon: float, heading: float, metres: float) -> Move:
    """Move along the shortest line on the ellipsoid in a heading (free facing).

    The heading on arrival is the direction of travel at the end (NAV-3).
    The line may pass over a pole.
    """
    line = WGS84.DirectLine(lat, lon, heading, metres, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
    n = _path_count(metres)
    path = []
    for i in range(n):
        p = line.Position(metres * i / (n - 1), Geodesic.STANDARD | Geodesic.LONG_UNROLL)
        path.append((p["lat2"], p["lon2"]))
    end = line.Position(metres, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
    return Move(end["lat2"], wrap_lon(end["lon2"]), end["azi2"] % 360.0, tuple(path))


# Boxes and centres across the 180 degree line ----------------------------------------

LINE_TOLERANCE = 1e-7  # degrees


@dataclass(frozen=True)
class WrapBox:
    """A bounding box whose west edge may be east of its east edge, when the
    box crosses the 180 degree line (AD-17)."""
    west: float
    south: float
    east: float
    north: float
    width: float  # degrees of longitude covered; 360 for a shape round a pole

    @property
    def crosses(self) -> bool:
        return self.west > self.east

    @property
    def round_the_world(self) -> bool:
        return self.width >= 359.999

    def contains_lon(self, lon: float) -> bool:
        lon = wrap_lon(lon)
        if self.round_the_world:
            return True
        if self.crosses:
            return lon >= self.west - LINE_TOLERANCE or lon <= self.east + LINE_TOLERANCE
        return self.west - LINE_TOLERANCE <= lon <= self.east + LINE_TOLERANCE


def wrap_box(spans, south: float, north: float) -> WrapBox:
    """The smallest box covering some spans of longitude, each (west, east)
    with west no greater than east, allowed to cross the 180 degree line.

    The spans are merged and the widest stretch of longitude with no span is
    left outside the box. Shapes that cross the line are stored split at it,
    so their parts give spans on both sides.
    """
    merged: list[list[float]] = []
    for w, e in sorted(spans):
        if merged and w <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([w, e])
    if not merged:
        return WrapBox(0.0, 0.0, 0.0, 0.0, 0.0)
    gaps = [(merged[i + 1][0] - merged[i][1], merged[i][1], merged[i + 1][0]) for i in range(len(merged) - 1)]
    gaps.append((merged[0][0] + 360.0 - merged[-1][1], merged[-1][1], merged[0][0]))
    size, gap_start, gap_end = max(gaps)
    if size <= LINE_TOLERANCE:
        return WrapBox(-180.0, south, 180.0, north, 360.0)
    return WrapBox(gap_end, south, gap_start, north, 360.0 - size)


def box_centre(box: WrapBox) -> tuple[float, float]:
    """The middle of a box as (lat, lon), across the 180 degree line.

    A box round the world is a shape round a pole, such as Antarctica, so its
    centre is that pole (architecture 6.13).
    """
    if box.round_the_world:
        if box.south <= -89.0:
            return -90.0, 0.0
        if box.north >= 89.0:
            return 90.0, 0.0
        return (box.south + box.north) / 2, 0.0
    east = box.east + 360.0 if box.crosses else box.east
    return (box.south + box.north) / 2, wrap_lon((box.west + east) / 2)


# Areas on the ellipsoid --------------------------------------------------------------

def _q(sin_phi):
    return (1 - E2) * (sin_phi / (1 - E2 * sin_phi ** 2)
                       - (1 / (2 * E)) * np.log((1 - E * sin_phi) / (1 + E * sin_phi)))


Q_POLE = float(_q(np.float64(1.0)))
R_AUTHALIC_M = A_M * math.sqrt(Q_POLE / 2)


def authalic_lat(lat_deg):
    """The authalic latitude in degrees: it maps the ellipsoid onto a sphere of
    radius R_AUTHALIC_M with every area kept."""
    ratio = np.clip(_q(np.sin(np.radians(lat_deg))) / Q_POLE, -1.0, 1.0)
    return np.degrees(np.arcsin(ratio))


def laea(lon, lat, lon0, lat0, radius: float = R_AUTHALIC_M):
    """Lambert azimuthal equal-area projection on a sphere, centred on
    (lat0, lon0). Give authalic latitudes to keep areas on the ellipsoid."""
    lam, phi = np.radians(np.asarray(lon) - lon0), np.radians(lat)
    phi0 = np.radians(lat0)
    denom = 1 + np.sin(phi0) * np.sin(phi) + np.cos(phi0) * np.cos(phi) * np.cos(lam)
    k = np.sqrt(2 / np.maximum(denom, 1e-12))
    x = radius * k * np.cos(phi) * np.sin(lam)
    y = radius * k * (np.cos(phi0) * np.sin(phi) - np.sin(phi0) * np.cos(phi) * np.cos(lam))
    return x, y


def densify(lon, lat, max_deg: float = 0.25):
    """A closed or open line with extra points, so no edge is longer than
    max_deg degrees. Long edges along a meridian or a line of latitude then
    follow the Earth."""
    lon = np.asarray(lon, dtype=np.float64)
    lat = np.asarray(lat, dtype=np.float64)
    if len(lon) < 2:
        return lon, lat
    span = np.maximum(np.abs(np.diff(lon)), np.abs(np.diff(lat)))
    pieces = np.maximum(1, np.ceil(span / max_deg)).astype(np.intp)
    start = np.repeat(np.arange(len(pieces), dtype=np.intp), pieces)
    first = np.repeat(np.cumsum(pieces) - pieces, pieces)
    t = (np.arange(len(start), dtype=np.intp) - first) / np.repeat(pieces, pieces)
    out_lon = np.append(lon[start] + (lon[start + 1] - lon[start]) * t, lon[-1])
    out_lat = np.append(lat[start] + (lat[start + 1] - lat[start]) * t, lat[-1])
    return out_lon, out_lat


def ring_area_m2(lon, lat, centre: tuple[float, float] | None = None) -> float:
    """The area inside one ring, in square metres, on the ellipsoid.

    The ring is densified, its latitudes made authalic, and it is projected
    with the equal-area projection centred on the ring (or on centre, given
    as (lat, lon)). Holes are measured as rings of their own and taken away
    by the caller. The ring must not cross the 180 degree line, which is how
    packs store shapes (AD-17).
    """
    lon, lat = densify(lon, lat)
    if len(lon) < 3:
        return 0.0
    if centre is None:
        lat0, lon0 = float(np.mean(lat)), float((np.min(lon) + np.max(lon)) / 2)
    else:
        lat0, lon0 = centre
    x, y = laea(lon, authalic_lat(lat), lon0, float(authalic_lat(np.float64(lat0))))
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


# A local projection for quick nearest-point work ---------------------------------------

class LocalProjection:
    """Metres east and north of a centre point, for quick work near it (P1-T5).

    It scales longitude and latitude by the ellipsoid's radii of curvature at
    the centre, so it is within about 0.1% for a few tens of kilometres and
    good enough for choosing the nearest of nearby things. Longitudes are
    taken the short way round, across the 180 degree line. Exact distances
    still come from distance_m.
    """

    def __init__(self, lat: float, lon: float):
        self.lat0 = lat
        self.lon0 = lon
        phi = math.radians(lat)
        w = math.sqrt(1 - E2 * math.sin(phi) ** 2)
        self.m_per_deg_lat = math.radians(1) * A_M * (1 - E2) / w ** 3
        self.m_per_deg_lon = math.radians(1) * A_M * math.cos(phi) / w

    def forward(self, lat, lon):
        """(x, y) in metres east and north of the centre, for arrays or numbers."""
        dlon = (np.asarray(lon, dtype=np.float64) - self.lon0 + 180.0) % 360.0 - 180.0
        dlat = np.asarray(lat, dtype=np.float64) - self.lat0
        return dlon * self.m_per_deg_lon, dlat * self.m_per_deg_lat

    def inverse(self, x, y):
        """(lat, lon) for metres east and north of the centre."""
        lat = self.lat0 + np.asarray(y, dtype=np.float64) / self.m_per_deg_lat
        lon = self.lon0 + np.asarray(x, dtype=np.float64) / self.m_per_deg_lon
        return lat, (lon + 180.0) % 360.0 - 180.0
