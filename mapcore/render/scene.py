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

The zoom distance is drawn at a fixed scale (ZOOM_RADIUS_PX), so a smaller
window shows less map round the edges but hears the same area (DP76, DP138).

Line features are drawn as lines and point features as markers (P2-T10a):
"line_coords" holds the screen points of every run of a line on the near side
of the globe, "line_runs" where each run starts, and "line_style" and
"line_area" its style and feature; "marker_coords", "marker_style" and
"marker_area" the same for points. Lines are never filled.

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


# How far from the centre the zoom distance is drawn, in Qt's scaled pixels (DP138).
# The map has a fixed scale for each zoom, as on paper, so a bigger window shows more
# map round the edges. What is heard (the hearing range) is the zoom distance itself,
# so the window size never changes it (DP76).
ZOOM_RADIUS_PX = 300


def view_for(world, width: float, height: float) -> globe.View:
    """The view for the world's location and zoom: the zoom distance is drawn
    ZOOM_RADIUS_PX from the centre (DP138, NAV-13). At the largest zoom the whole
    hemisphere is a disc of that radius."""
    side = min(width, height)
    theta = min(world.zoom_m / geodesy.R_MEAN_M, math.pi / 2)
    radius = ZOOM_RADIUS_PX / math.sin(theta)
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
        self._features: dict[tuple[int, int], tuple[str, int, int, str]] = {}  # -> (id, layer order, colour, layer)

    def _feature(self, p: int, number: int):
        got = self._features.get((p, number))
        if got is None:
            area = self.store._area(p, number)
            got = ("?", 9, 1, "") if area is None else (area.id, LAYER_ORDER.get(area.layer, 4),
                                                        int(area.record.get("colour") or 1), area.layer)
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

    def _collect(self, lat, lon, rho, zoom_km, layers=None):
        """The shapes (Shapely) for the cap in view, with the feature of each and
        the box of its tile. Each tile's shapes are decoded together, once, and
        kept with the tile (P2-T14c). `layers`, when given, is the set of layer ids
        that are on: the shapes of every other layer are left out (SCP-6)."""
        geoms, feats, boxes, tile_of = [], [], [], []
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
                        if not data.entries:
                            continue
                        box = tiles.tile_box(level, x, y)
                        shapes, numbers = data.drawing_shapes(box)
                        found = [self._feature(p, n) for n in numbers.tolist()]
                        if layers is not None:
                            keep = np.fromiter((f[3] in layers for f in found), bool, len(found))
                            if not keep.all():
                                shapes = shapes[keep]
                                found = [f for f, k in zip(found, keep) if k]
                            if not len(shapes):
                                continue
                        geoms.append(shapes)
                        feats.extend(found)
                        tile_of.append(np.full(len(shapes), len(boxes), np.intp))
                        boxes.append(box)
        if not geoms:
            return np.empty(0, object), [], np.zeros((0, 4)), intervals, south, north
        box_of_shape = np.asarray(boxes, float).reshape(-1, 4)[np.concatenate(tile_of)]
        return np.concatenate(geoms), feats, box_of_shape, intervals, south, north

    def build(self, world, width: int, height: int, current: str | None = None, highlight: str | None = None,
              centre_cross: bool = True, layers=None) -> dict:
        import shapely

        start = time.perf_counter()
        view = view_for(world, width, height)
        cx, cy, r = width / 2, height / 2, globe._radius(view, width, height)
        rho = math.asin(min(1.0, math.hypot(cx, cy) / r))
        geoms, feats, boxes, intervals, south, north = self._collect(world.lat, world.lon, rho, world.zoom_m / 1000.0,
                                                                     layers)
        empty = np.zeros(0, np.intp)
        lines, line_idx, dots, dot_idx = np.empty(0, object), empty, np.empty(0, object), empty
        if len(geoms):
            parts_all, idx_all = [], []
            other_all, other_idx_all = [], []
            for west, east in intervals:
                clipped = shapely.clip_by_rect(geoms, west, south, east, north)
                parts, idx = shapely.get_parts(clipped, return_index=True)
                kinds = shapely.get_type_id(parts)
                live = ~shapely.is_empty(parts)
                keep = (kinds == 3) & live
                parts_all.append(parts[keep])
                idx_all.append(idx[keep])
                other = ((kinds == 1) | (kinds == 0)) & live   # lines and points (P2-T10a)
                other_all.append(parts[other])
                other_idx_all.append(idx[other])
            parts = np.concatenate(parts_all)
            idx = np.concatenate(idx_all).astype(np.intp)
            others = np.concatenate(other_all)
            other_idx = np.concatenate(other_idx_all).astype(np.intp)
            if len(others):
                is_line = shapely.get_type_id(others) == 1
                lines, line_idx = others[is_line], other_idx[is_line]
                dots, dot_idx = others[~is_line], other_idx[~is_line]
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
        chosen = time.perf_counter()
        frame = self._frame(view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes,
                            current, highlight)
        frame.update(self._lines(view, cx, cy, r, lines, line_idx, feats, highlight))
        frame.update(self._markers(view, width, height, cx, cy, r, dots, dot_idx, feats, highlight))
        frame["points"] += int(len(frame["line_coords"]) // 2)
        frame["choose_ms"] = (chosen - start) * 1000            # finding and cutting the shapes in view (P2-T14b)
        frame["projecting_ms"] = (time.perf_counter() - chosen) * 1000   # turning them into screen pixels
        if centre_cross:
            frame["cross"] = {"x": cx, "y": cy, "size": 9, "colour": self.theme["cross"], "halo": self.theme["cross_halo"]}
        else:
            frame["cross"] = None
        frame["heading"] = {"x": cx, "y": cy, "degrees": float(world.heading), "colour": self.theme["cross"],
                            "halo": self.theme["cross_halo"], "length": 26}
        frame["project_ms"] = (time.perf_counter() - start) * 1000   # the whole of the core's part
        return frame

    def _lines(self, view, cx, cy, r, lines, idx, feats, highlight) -> dict:
        """Each line cut into runs of points on the near side of the globe, in screen pixels."""
        import shapely

        theme = self.theme
        styles = [{"stroke": theme["line"], "width": theme["line_width"]},
                  {"stroke": theme["highlight_outline"], "width": theme["line_width"] + 2}]
        if not len(lines):
            return {"line_coords": np.zeros(0, np.float32), "line_runs": np.zeros(1, np.int32),
                    "line_style": np.zeros(0, np.int32), "line_area": [], "line_styles": styles}
        xy, which = shapely.get_coordinates(lines, return_index=True)
        px, py, depth = globe.project_points(view, xy[:, 1], xy[:, 0])
        seen = depth >= 0
        which = np.asarray(which, np.intp)
        # A run starts at a point on the near side whose point before is hidden or on another line.
        starts = seen.copy()
        starts[1:] &= ~(seen[:-1] & (which[1:] == which[:-1]))
        run_of = np.cumsum(starts) - 1
        keep_runs = np.bincount(run_of[seen], minlength=int(starts.sum())) >= 2
        keep = seen & keep_runs[run_of]
        run_ids, counts = np.unique(run_of[keep], return_counts=True)
        coords = np.empty(int(keep.sum()) * 2, np.float32)
        coords[0::2] = cx + r * px[keep]
        coords[1::2] = cy - r * py[keep]
        first_point = np.searchsorted(run_of[keep], run_ids)
        line_of_run = which[keep][first_point]
        area = [feats[idx[k]][0] for k in line_of_run.tolist()]
        return {"line_coords": coords, "line_runs": np.concatenate([[0], np.cumsum(counts)]).astype(np.int32),
                "line_style": np.array([1 if highlight and a == highlight else 0 for a in area], np.int32),
                "line_area": area, "line_styles": styles}

    def _markers(self, view, width, height, cx, cy, r, dots, idx, feats, highlight) -> dict:
        """Each point feature's points on the near side of the globe and on the map, in screen pixels."""
        import shapely

        theme = self.theme
        styles = [{"fill": theme["marker"], "stroke": theme["marker_outline"], "radius": theme["marker_radius"]},
                  {"fill": theme["highlight_fill"], "stroke": theme["highlight_outline"],
                   "radius": theme["marker_radius"] + 2}]
        if not len(dots):
            return {"marker_coords": np.zeros(0, np.float32), "marker_style": np.zeros(0, np.int32),
                    "marker_area": [], "marker_styles": styles}
        xy, which = shapely.get_coordinates(dots, return_index=True)
        px, py, depth = globe.project_points(view, xy[:, 1], xy[:, 0])
        sx, sy = cx + r * px, cy - r * py
        keep = (depth >= 0) & (sx >= 0) & (sx <= width) & (sy >= 0) & (sy <= height)
        coords = np.empty(int(keep.sum()) * 2, np.float32)
        coords[0::2], coords[1::2] = sx[keep], sy[keep]
        area = [feats[idx[k]][0] for k in np.asarray(which, np.intp)[keep].tolist()]
        return {"marker_coords": coords, "marker_area": area, "marker_styles": styles,
                "marker_style": np.array([1 if highlight and a == highlight else 0 for a in area], np.int32)}

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
        point_box = boxes[tile_of_poly][ring_poly][ring_of_point] if n_pts else np.zeros((0, 4))
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
            ident, layer, colour, _layer_id = feats[tile_of_poly[j]]
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
