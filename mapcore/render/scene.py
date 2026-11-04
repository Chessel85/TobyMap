"""The map scene from a pack (P1-T9; VIS-1, VIS-5, AD-6, AD-17, AD-19, DP76).

The shape list has the same form as the Phase 0 globe's (see globe.py): plain
arrays in screen pixels that the shells only paint. What changes is where the
shapes come from. They are read from the pack:

* a wide view uses a drawing level, the coarsest one whose view width is at
  least the zoom (so a frame stays near 10,000 points, VIS-1);
* a close view uses the exact pack tiles, at every tile level;
* shapes are cut to the part of the Earth in view with Shapely, so even a
  country's outline stays small;
* a point less than half a pixel from the one before is dropped.

The zoom is a distance across the smaller side of the map, so a smaller
window draws smaller but shows and hears the same area (DP76).

Artificial edges, the cuts along pack tile boundaries (which include the
180 degree line and the South Pole), are marked as seams: filled, never
outlined (AD-17), so Fiji and Russia draw whole across the line.
"""
from __future__ import annotations

import math
import time

import numpy as np

from mapcore.geo import geodesy
from mapcore.packs import tiles
from mapcore.render import globe

EXACT_BELOW_KM = 25.0     # a view this narrow or narrower uses the exact pack tiles
SEAM_TOLERANCE = 3e-7     # degrees: stored coordinates are whole ten-millionths
SNAP = 0.7               # pixel cells per pixel: points in the same 1.4 pixel cell are one point
LAYER_ORDER = {"oceans": 0, "countries": 1, "regions": 2, "counties": 3}
OCEAN_STYLE = 7
HIGHLIGHT_STYLE = 8
MIN_RING = 3


def view_for(world, width: float, height: float) -> globe.View:
    """The view for the world's location and zoom: the zoom is a distance
    across the smaller side of the map (DP76)."""
    side = min(width, height)
    theta = min(world.zoom_m / geodesy.R_MEAN_M, math.pi)
    radius = (side / 2) / math.sin(theta / 2)
    return globe.View(lat=world.lat, lon=world.lon, scale=radius / (side * globe.GLOBE_FRACTION))


def _cap(lat: float, lon: float, rho: float):
    """The longitude intervals and latitude range of the cap of angular radius rho (radians) round a point."""
    south = max(-90.0, lat - math.degrees(rho))
    north = min(90.0, lat + math.degrees(rho))
    if rho >= math.pi / 2 or north >= 90.0 or south <= -90.0 or math.cos(math.radians(max(abs(south), abs(north)))) <= math.sin(rho):
        return [(-180.0, 180.0)], south, north
    half = math.degrees(math.asin(math.sin(rho) / math.cos(math.radians(lat))))
    west, east = lon - half, lon + half
    if west < -180:
        return [(west + 360, 180.0), (-180.0, east)], south, north
    if east > 180:
        return [(west, 180.0), (-180.0, east - 360)], south, north
    return [(west, east)], south, north


class SceneBuilder:
    def __init__(self, store, theme: dict | None = None):
        self.store = store
        self.theme = theme or globe.load_theme()
        self._features: dict[tuple[int, int], tuple[str, int, int]] = {}  # -> (id, layer order, colour)

    def _feature(self, p: int, number: int):
        got = self._features.get((p, number))
        if got is None:
            area = self.store._area(p, number)
            got = ("?", 9, 1) if area is None else (area.id, LAYER_ORDER.get(area.layer, 4), int(area.record.get("colour") or 1))
            self._features[(p, number)] = got
        return got

    def _source(self, zoom_km: float, index):
        """("draw", level id, tile level) or ("tile", None, None) for this zoom."""
        levels = sorted(index.pack.drawing_levels.values(), key=lambda d: d.get("view_km", 0))
        if zoom_km <= EXACT_BELOW_KM or not levels:
            return "tile", None
        for d in levels:
            if d["view_km"] >= zoom_km:
                return "draw", d
        return "draw", levels[-1]

    def _collect(self, lat, lon, rho, zoom_km):
        """Shapes (Shapely) with their feature and tile box, for the cap in view."""
        import shapely

        geoms, feats, boxes = [], [], []
        intervals, south, north = _cap(lat, lon, rho * 1.15)
        for p in self.store._covering(lat, lon)[:1]:
            index = self.store._indexes[p]
            kind, d = self._source(zoom_km, index)
            if kind == "draw":
                plan = [("draw", d["id"], d["tile_level"])]
            else:
                plan = [("tile", level, level) for level in index.pack.tile_levels]
            for tkind, ident, level in plan:
                n = 2 ** level
                y0, y1 = tiles.tile_of(0.0, south, level)[1], tiles.tile_of(0.0, north, level)[1]
                spans = []
                for west, east in intervals:
                    spans.append((tiles.tile_of(west, 0.0, level)[0], tiles.tile_of(east, 0.0, level)[0]))
                for x0, x1 in spans:
                    for x, y in index.tiles_in("draw" if tkind == "draw" else "tile", ident if tkind == "draw" else level,
                                               x0, x1, y0, y1):
                        data = self.store._tile(p, "draw" if tkind == "draw" else "tile", ident if tkind == "draw" else level, x, y)
                        box = tiles.tile_box(level, x, y)
                        for i, entry in enumerate(data.entries):
                            geom = shapely.box(*box) if entry.kind == tiles.COVERED else data.shape(i)
                            geoms.append(geom)
                            feats.append(self._feature(p, entry.feature))
                            boxes.append(box)
        return geoms, feats, boxes, intervals, south, north

    def build(self, world, width: int, height: int, current: str | None = None, highlight: str | None = None,
              centre_cross: bool = True) -> dict:
        import shapely

        start = time.perf_counter()
        view = view_for(world, width, height)
        cx, cy, r = width / 2, height / 2, globe._radius(view, width, height)
        rho = math.asin(min(1.0, math.hypot(cx, cy) / r))
        geoms, feats, boxes, intervals, south, north = self._collect(world.lat, world.lon, rho, world.zoom_m / 1000.0)
        empty = np.zeros(0, np.intp)
        if geoms:
            arr = np.empty(len(geoms), object)
            arr[:] = geoms
            parts_all, idx_all = [], []
            for west, east in intervals:
                clipped = shapely.clip_by_rect(arr, west, south, east, north)
                parts, idx = shapely.get_parts(clipped, return_index=True)
                keep = (shapely.get_type_id(parts) == 3) & ~shapely.is_empty(parts)
                parts_all.append(parts[keep])
                idx_all.append(idx[keep])
            parts = np.concatenate(parts_all)
            idx = np.concatenate(idx_all).astype(np.intp)
        else:
            parts, idx = np.empty(0, object), empty
        if len(parts):
            order = np.argsort(np.array([feats[i][1] for i in idx], np.intp), kind="stable")  # oceans first
            parts, idx = parts[order], idx[order]
            _t, xy, (ring_off, poly_off) = shapely.to_ragged_array(parts)
            ring_off = np.asarray(ring_off, np.intp)
            poly_off = np.asarray(poly_off, np.intp)
        else:
            xy, ring_off, poly_off = np.zeros((0, 2)), np.zeros(1, np.intp), np.zeros(1, np.intp)
        frame = self._frame(view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes,
                            current, highlight)
        if centre_cross:
            frame["cross"] = {"x": cx, "y": cy, "size": 9, "colour": self.theme["cross"], "halo": self.theme["cross_halo"]}
        else:
            frame["cross"] = None
        frame["heading"] = {"x": cx, "y": cy, "degrees": float(world.heading), "colour": self.theme["cross"],
                            "halo": self.theme["cross_halo"], "length": 26}
        frame["project_ms"] = (time.perf_counter() - start) * 1000
        return frame

    def _frame(self, view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes, current, highlight):
        theme = self.theme
        n_pts = len(xy)
        lon, lat = (xy[:, 0], xy[:, 1]) if n_pts else (np.zeros(0), np.zeros(0))
        px, py, depth = globe.project_points(view, lat, lon) if n_pts else (np.zeros(0),) * 3
        hidden = depth < 0
        norm = np.hypot(px, py)
        safe = np.where(norm > 0, norm, 1.0)
        px = np.where(hidden, np.where(norm > 0, px / safe, 1.0), px)
        py = np.where(hidden, np.where(norm > 0, py / safe, 0.0), py)
        sx, sy = cx + r * px, cy - r * py

        n_rings = len(ring_off) - 1
        counts = np.diff(ring_off)
        ring_of_point = np.repeat(np.arange(n_rings, dtype=np.intp), counts)
        is_last = np.zeros(n_pts, bool)
        is_first = np.zeros(n_pts, bool)
        if n_rings:
            is_last[ring_off[1:] - 1] = True
            is_first[ring_off[:-1]] = True

        # Seams: an edge whose two ends are on the same edge of its pack tile (AD-17).
        tile_of_poly = np.asarray(idx, np.intp)
        ring_poly = np.repeat(np.arange(len(poly_off) - 1, dtype=np.intp), np.diff(poly_off))
        point_box = np.asarray([boxes[i] for i in tile_of_poly], float).reshape(-1, 4)[ring_poly][ring_of_point] \
            if n_pts else np.zeros((0, 4))
        nxt = np.minimum(np.arange(n_pts, dtype=np.intp) + 1, max(n_pts - 1, 0))
        seam = np.zeros(n_pts, bool)
        if n_pts:
            tol = SEAM_TOLERANCE
            w, s, e, n = point_box.T
            x0, y0, x1, y1 = lon, lat, lon[nxt], lat[nxt]
            seam = (((np.abs(x0 - w) < tol) & (np.abs(x1 - w) < tol)) | ((np.abs(x0 - e) < tol) & (np.abs(x1 - e) < tol))
                    | ((np.abs(y0 - s) < tol) & (np.abs(y1 - s) < tol)) | ((np.abs(y0 - n) < tol) & (np.abs(y1 - n) < tol)))
            seam &= ~is_last
            # Edges running along the pushed-out horizon are not real either.
            seam |= hidden & hidden[nxt] & ~is_last

        # Drop the closing point of every ring, then points in the same half pixel as the one before.
        keep = ~is_last
        if n_pts:
            qx, qy = np.round(sx * SNAP), np.round(sy * SNAP)
            same = np.zeros(n_pts, bool)
            same[1:] = (qx[1:] == qx[:-1]) & (qy[1:] == qy[:-1])
            keep &= is_first | ~same
        kept_counts = np.bincount(ring_of_point[keep], minlength=n_rings).astype(np.intp)

        # Cull rings that are off the map, and polygons whose outer ring is too small.
        on_screen = np.zeros(n_rings, bool)
        if n_rings:
            starts = ring_off[:-1]
            minx, maxx = np.minimum.reduceat(sx, starts), np.maximum.reduceat(sx, starts)
            miny, maxy = np.minimum.reduceat(sy, starts), np.maximum.reduceat(sy, starts)
            vis = np.add.reduceat((~hidden).astype(np.intp), starts) > 0
            on_screen = vis & (maxx >= 0) & (minx <= width) & (maxy >= 0) & (miny <= height)
        ring_ok = on_screen & (kept_counts >= MIN_RING)
        poly_first = poly_off[:-1]
        poly_ok = ring_ok[poly_first] if len(poly_first) else np.zeros(0, bool)
        ring_ok &= poly_ok[ring_poly] if n_rings else ring_ok
        point_ok = keep & ring_ok[ring_of_point] if n_pts else keep

        kept_rings = np.nonzero(ring_ok)[0]
        coords = np.empty(int(point_ok.sum()) * 2, np.float32)
        coords[0::2] = sx[point_ok]
        coords[1::2] = sy[point_ok]
        rings = np.concatenate([[0], np.cumsum(kept_counts[kept_rings])]).astype(np.int32)
        kept_polys = np.nonzero(poly_ok)[0]
        rings_per_poly = np.bincount(ring_poly[kept_rings], minlength=len(poly_ok))[kept_polys] if len(poly_ok) else np.zeros(0, np.intp)
        shapes = np.concatenate([[0], np.cumsum(rings_per_poly)]).astype(np.int32)

        land = theme["land"]
        styles = [{"fill": c, "stroke": theme["border"], "width": 1} for c in land]
        while len(styles) < OCEAN_STYLE:
            styles.append(styles[-1])
        styles.append({"fill": theme["ocean"], "stroke": "#00000000", "width": 0})   # OCEAN_STYLE
        styles.append({"fill": theme["highlight_fill"], "stroke": theme["highlight_outline"], "width": 2})
        shape_area, shape_style = [], []
        for j in kept_polys:
            ident, layer, colour = feats[tile_of_poly[j]]
            shape_area.append(ident)
            shape_style.append(OCEAN_STYLE if layer == 0 else (colour - 1) % len(land))
        hi = [i for i, a in enumerate(shape_area) if highlight and a == highlight]
        for i in hi:
            shape_style[i] = HIGHLIGHT_STYLE
        cur = [i for i, a in enumerate(shape_area) if current and a == current]
        return {
            "width": width, "height": height, "background": theme["background"],
            "globe": {"cx": cx, "cy": cy, "r": r, "fill": theme["ocean"], "edge": theme["globe_edge"]},
            "coords": coords, "seam": seam[point_ok].astype(np.uint8), "rings": rings, "shapes": shapes,
            "shape_style": np.asarray(shape_style, np.int32), "shape_area": shape_area, "styles": styles,
            "current": cur, "current_style": {"stroke": theme["current_outline"], "width": 3},
            "highlight": hi, "points": int(len(coords) // 2),
        }
