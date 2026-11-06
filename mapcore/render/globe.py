"""The orthographic globe (VIS-5, AD-6, architecture 7.10).

The core projects every point with NumPy in one go and returns a plain shape
list in screen pixels. The shells only paint it: Qt on the desktop, a canvas
on the web.

Projection: the view is centred on (lat, lon). For each point on the unit
sphere, x is its component to the east of the centre, y to the north, and
depth towards the viewer. Depth below zero is the far side.

Horizon clipping, spike version: a ring that is partly on the far side has its
hidden points pushed out to the edge of the globe, in their own direction.
That keeps filled shapes closed and on the disc. Rings with no visible point
are dropped. Phase 1 may replace this with exact clipping along the horizon if
the spike shows visible faults (see docs/spikes/S5 findings).

The scene, all plain data:

* width, height, background
* globe: cx, cy, r, fill, edge
* coords: float32 x, y pairs for every kept ring, one after another
* seam: uint8 per point, 1 if the edge to the next point of the ring is
  artificial (the 180 degree line, AD-17): fill across it, never outline it
* rings: int32 point offsets, one more than the number of rings
* shapes: int32 ring offsets, one more than the number of shapes; a shape is
  one polygon with its holes, filled with the even-odd rule
* shape_style: index into styles for each shape
* shape_country: the country id of each shape
* styles: fill and stroke for each style
* current, highlight: shape indexes to outline and to highlight
* cross: the centre cross
* points, project_ms: for the timing report
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

GLOBE_FRACTION = 0.45  # radius at scale 1, as a share of the smaller side


@dataclass(frozen=True)
class View:
    lat: float
    lon: float
    scale: float = 1.0
    up: float = 0.0   # the bearing at the top of the map: 0 is north-up; the heading for heading-up (VIS-5)


def load_theme(name: str = "standard") -> dict:
    from mapcore.render import themes

    return themes.theme(name)


def _frame(view: View):
    """The screen's right, up and towards-the-viewer directions. With up, the map is turned
    so that bearing is at the top (heading-up, VIS-5)."""
    phi, lam = np.radians(view.lat), np.radians(view.lon)
    east = np.array([-np.sin(lam), np.cos(lam), 0.0])
    north = np.array([-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)])
    forward = np.array([np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)])
    if view.up:
        a = np.radians(view.up)
        east, north = np.cos(a) * east - np.sin(a) * north, np.cos(a) * north + np.sin(a) * east
    return east, north, forward


def unit_vectors(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    phi, lam = np.radians(lat_deg), np.radians(lon_deg)
    cp = np.cos(phi)
    return np.stack([cp * np.cos(lam), cp * np.sin(lam), np.sin(phi)], axis=1)


def project_points(view: View, lat_deg: np.ndarray, lon_deg: np.ndarray):
    """Unit-globe x (east), y (north) and depth for each point."""
    return _project_xyz(view, unit_vectors(np.asarray(lat_deg, float), np.asarray(lon_deg, float)))


def _project_xyz(view: View, xyz: np.ndarray):
    east, north, forward = _frame(view)
    return xyz @ east, xyz @ north, xyz @ forward


def _radius(view: View, width: float, height: float) -> float:
    return min(width, height) * GLOBE_FRACTION * view.scale


def visible_extent(view: View, width: float, height: float) -> tuple[float, float] | None:
    """The visible map across and up and down, through the centre, as angles in
    radians along the globe's surface. None when the whole globe fits."""
    r = _radius(view, width, height)
    if width / 2 >= r and height / 2 >= r:
        return None
    return (2 * math.asin(min(1.0, width / 2 / r)), 2 * math.asin(min(1.0, height / 2 / r)))


def to_screen(view: View, width: float, height: float, lat: float, lon: float) -> tuple[float, float]:
    x, y, _ = project_points(view, np.array([lat]), np.array([lon]))
    r = _radius(view, width, height)
    return width / 2 + r * float(x[0]), height / 2 - r * float(y[0])


def from_screen(view: View, width: float, height: float, sx: float, sy: float):
    """The (lat, lon) under a screen point, or None if it is off the globe."""
    r = _radius(view, width, height)
    x, y = (sx - width / 2) / r, (height / 2 - sy) / r
    rr = x * x + y * y
    if rr > 1:
        return None
    east, north, forward = _frame(view)
    p = x * east + y * north + np.sqrt(1 - rr) * forward
    lat = float(np.degrees(np.arcsin(np.clip(p[2], -1, 1))))
    lon = float(np.degrees(np.arctan2(p[1], p[0])))
    return lat, lon


class GlobeGeometry:
    """Every ring of every country as unit vectors, built once."""

    def __init__(self, xyz, ring_offsets, shape_ring_offsets, shape_country, shape_colour, seam=None):
        self.xyz = xyz
        # seam[i] is True when the edge from point i to the next point of its
        # ring is artificial: along the 180 degree line, or Antarctica's
        # closing edge at the South Pole. It is filled but never outlined (AD-17).
        self.seam = seam if seam is not None else np.zeros(len(xyz), bool)
        self.ring_offsets = ring_offsets
        self.shape_ring_offsets = shape_ring_offsets
        self.shape_country = shape_country
        self.shape_colour = shape_colour
        # Offsets use np.intp: it is 32 bits in Pyodide (wasm32) and 64 on the desktop.
        self.ring_shape = np.repeat(np.arange(len(shape_country), dtype=np.intp),
                                    np.diff(shape_ring_offsets).astype(np.intp))

    @classmethod
    def from_world(cls, world) -> "GlobeGeometry":
        lats, lons, ring_offsets, shape_offsets, shape_country, shape_colour = [], [], [0], [0], [], []
        for c in world.countries:
            for poly in c.polygons:
                for ring in poly:
                    lats.append(ring.lat)
                    lons.append(ring.lon)
                    ring_offsets.append(ring_offsets[-1] + len(ring.lat))
                shape_offsets.append(shape_offsets[-1] + len(poly))
                shape_country.append(c.id)
                shape_colour.append(c.colour)
        lat_all, lon_all = np.concatenate(lats), np.concatenate(lons)
        xyz = unit_vectors(lat_all, lon_all)
        offs = np.asarray(ring_offsets, np.intp)
        # The next point of each point's ring, the last wrapping to the first,
        # for every ring at once (a loop over rings was slow for countries
        # with thousands of islands).
        nxt = np.arange(len(lat_all), dtype=np.intp) + 1
        full = np.diff(offs) > 0
        nxt[offs[1:][full] - 1] = offs[:-1][full]
        lo, la = lon_all, lat_all
        lo_next, la_next = lon_all[nxt], lat_all[nxt]
        on_line = (np.abs(np.abs(lo) - 180) < 1e-6) & (np.abs(np.abs(lo_next) - 180) < 1e-6)
        at_pole = (la < -89.99) & (la_next < -89.99)
        seam = on_line | at_pole
        return cls(xyz, offs, np.asarray(shape_offsets, np.intp),
                   shape_country, np.asarray(shape_colour, np.int64), seam)

    @property
    def point_count(self) -> int:
        return len(self.xyz)


def build_scene(geometry: GlobeGeometry, view: View, width: int, height: int,
                current: str | None = None, highlight: str | None = None, theme: dict | None = None) -> dict:
    start = time.perf_counter()
    theme = theme or load_theme()
    cx, cy, r = width / 2, height / 2, _radius(view, width, height)

    x, y, depth = _project_xyz(view, geometry.xyz)
    hidden = depth < 0
    # Push hidden points out to the edge, in their own direction.
    norm = np.hypot(x, y)
    safe = np.where(norm > 0, norm, 1.0)
    x = np.where(hidden, np.where(norm > 0, x / safe, 1.0), x)
    y = np.where(hidden, np.where(norm > 0, y / safe, 0.0), y)
    sx = cx + r * x
    sy = cy - r * y

    offs = geometry.ring_offsets
    n_rings = len(offs) - 1
    visible_counts = np.add.reduceat((~hidden).astype(np.intp), offs[:-1]) if n_rings else np.zeros(0, np.intp)
    min_x, max_x = np.minimum.reduceat(sx, offs[:-1]), np.maximum.reduceat(sx, offs[:-1])
    min_y, max_y = np.minimum.reduceat(sy, offs[:-1]), np.maximum.reduceat(sy, offs[:-1])
    on_screen = (max_x >= 0) & (min_x <= width) & (max_y >= 0) & (min_y <= height)
    keep_ring = (visible_counts > 0) & on_screen

    # A shape is kept if its outer ring (its first ring) is kept.
    outer = geometry.shape_ring_offsets[:-1]
    keep_shape = keep_ring[outer]
    # Keep holes only of kept shapes.
    keep_ring = keep_ring & keep_shape[geometry.ring_shape]

    kept_rings = np.nonzero(keep_ring)[0]
    lengths = offs[kept_rings + 1] - offs[kept_rings]
    point_index = np.nonzero(np.repeat(keep_ring, np.diff(offs)))[0]
    coords = np.empty(len(point_index) * 2, np.float32)
    coords[0::2] = sx[point_index]
    coords[1::2] = sy[point_index]
    rings = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int32)
    kept_shapes = np.nonzero(keep_shape)[0]
    rings_per_shape = np.bincount(geometry.ring_shape[kept_rings], minlength=len(keep_shape))[kept_shapes]
    shapes = np.concatenate([[0], np.cumsum(rings_per_shape)]).astype(np.int32)

    land = theme["land"]
    styles = [{"fill": colour, "stroke": theme["border"], "width": 1} for colour in land]
    shape_country = [geometry.shape_country[i] for i in kept_shapes]
    shape_style = np.asarray([(int(geometry.shape_colour[i]) - 1) % len(land) for i in kept_shapes], np.int32)
    highlight_style = len(styles)
    styles.append({"fill": theme["highlight_fill"], "stroke": theme["highlight_outline"], "width": 2})
    hi = [i for i, c in enumerate(shape_country) if highlight and c == highlight]
    for i in hi:
        shape_style[i] = highlight_style
    cur = [i for i, c in enumerate(shape_country) if current and c == current]

    return {
        "width": width,
        "height": height,
        "background": theme["background"],
        "globe": {"cx": cx, "cy": cy, "r": r, "fill": theme["ocean"], "edge": theme["globe_edge"]},
        "coords": coords,
        "seam": geometry.seam[point_index].astype(np.uint8),
        "rings": rings,
        "shapes": shapes,
        "shape_style": shape_style,
        "shape_country": shape_country,
        "styles": styles,
        "current": cur,
        "current_style": {"stroke": theme["current_outline"], "width": 3},
        "highlight": hi,
        "cross": {"x": cx, "y": cy, "size": 9, "colour": theme["cross"], "halo": theme["cross_halo"]},
        "points": int(len(point_index)),
        "project_ms": (time.perf_counter() - start) * 1000,
    }
