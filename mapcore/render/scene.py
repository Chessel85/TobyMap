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
CLEAR_STYLE = 9   # an area in a layer not painted, drawn only for the current area's outline (P3-T17)
CLEAR = "clear"   # its fill
LINE_STYLE, HIGHLIGHT_LINE_STYLE, SPECIAL_LINE_STYLE = 0, 1, 2   # the line styles (P2-T17v)
LINE_DRAW_ORDER = {LINE_STYLE: 0, SPECIAL_LINE_STYLE: 1, HIGHLIGHT_LINE_STYLE: 2}
MIN_RING = 3
WATER_LAST = 100   # added to a land layer's order, so all water is painted first


def fill_of(feature: tuple, fills: dict | None) -> str:
    """How a feature's area is painted: its layer's fill, or water for the oceans and land for the rest."""
    got = (fills or {}).get(feature[3])
    if got in ("land", "water", "none"):
        return got
    return "water" if feature[1] == 0 else "land"


# How far from the centre the zoom distance is drawn, in Qt's scaled pixels (DP138).
# The map has a fixed scale for each zoom, as on paper, so a bigger window shows more
# map round the edges. What is heard (the hearing range) is the zoom distance itself,
# so the window size never changes it (DP76).
ZOOM_RADIUS_PX = 300


FOCUS_HALF_PX = 4   # half the side of the square that tells a magnifier where the map centre is (ACC-8)


def focus_rect(width: float, height: float) -> dict:
    """The small square round the map centre that the shells report to a magnifier, as a
    text caret or a focused element, so it keeps the location in view (ACC-8, DP146). The
    location is always at the centre of the map."""
    return {"x": width / 2 - FOCUS_HALF_PX, "y": height / 2 - FOCUS_HALF_PX,
            "width": 2 * FOCUS_HALF_PX, "height": 2 * FOCUS_HALF_PX}


def view_for(world, width: float, height: float, heading_up: bool = False) -> globe.View:
    """The view for the world's location and zoom: the zoom distance is drawn
    ZOOM_RADIUS_PX from the centre (DP138, NAV-13). At the largest zoom the whole
    hemisphere is a disc of that radius. With heading_up, in cardinal and free facing
    the map is turned so the way you face is at the top (VIS-5)."""
    side = min(width, height)
    theta = min(world.zoom_m / geodesy.R_MEAN_M, math.pi / 2)
    radius = ZOOM_RADIUS_PX / math.sin(theta)
    up = float(world.heading) % 360.0 if heading_up and world.orientation != "north-fixed" else 0.0
    return globe.View(lat=world.lat, lon=world.lon, scale=radius / (side * globe.GLOBE_FRACTION), up=up)


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


def drawing_source(index, zoom_km: float):
    """("draw", drawing level) or ("tile", None): where a pack's shapes come from at
    this zoom. The map and the visible rule both use it, so they read the same tiles."""
    levels = sorted(index.pack.drawing_levels.values(), key=lambda d: d.get("view_km", 0))
    if zoom_km <= EXACT_BELOW_KM or not levels:
        return "tile", None
    for d in levels:
        if d["view_km"] >= zoom_km:
            return "draw", d
    return "draw", levels[-1]


def holds(level: dict, layer_id: str) -> bool:
    """Whether a drawing level holds a layer's shapes. A pack written since P3-T1e lists the layers each level
    holds, leaving out those that cannot be seen at its zooms; an older pack's levels hold every layer."""
    return "layers" not in level or layer_id in level["layers"]


def finest_holding(index, layer_id: str) -> dict | None:
    """The finest drawing level that holds a layer, or None for the exact pack tiles. Used for a layer whose
    zoom range the user has widened beyond the zooms the chosen level serves (SCP-7)."""
    for d in sorted(index.pack.drawing_levels.values(), key=lambda d: d.get("view_km", 0)):
        if holds(d, layer_id):
            return d
    return None


def plan_for(index, kind: str, d: dict | None, wanted) -> list[tuple]:
    """The tiles to read, as (kind, level id, tile level, the layers to take from them or None for all): the
    chosen drawing level's, then, for each wanted layer it does not hold, the finest level that holds it."""
    if kind != "draw":
        return [("tile", level, level, None) for level in index.pack.tile_levels]
    plan = [("draw", d["id"], d["tile_level"], None)]
    if "layers" not in d:
        return plan
    extra: dict = {}
    for layer_id in sorted(set(wanted) - set(d["layers"])):
        alt = finest_holding(index, layer_id)
        key = ("tile", None) if alt is None else ("draw", alt["id"])
        extra.setdefault(key, (alt, set()))[1].add(layer_id)
    for (k, _ident), (alt, ids) in sorted(extra.items(), key=lambda kv: str(kv[0])):
        if k == "draw":
            plan.append(("draw", alt["id"], alt["tile_level"], frozenset(ids)))
        else:
            plan += [("tile", level, level, frozenset(ids)) for level in index.pack.tile_levels]
    return plan


class SceneBuilder:
    def __init__(self, store, theme: dict | None = None):
        self.store = store
        self.theme = theme or globe.load_theme()
        # -> (id, layer order, colour, layer, width in km or None, intervals or None, name)
        self._features: dict[tuple[int, int], tuple] = {}

    def _feature(self, p: int, number: int):
        got = self._features.get((p, number))
        if got is None:
            area = self.store._area(p, number)
            got = ("?", 9, 1, "", None, None, "") if area is None else (
                area.id, LAYER_ORDER.get(area.layer, 4), int(area.record.get("colour") or 1), area.layer,
                area.record.get("width_km"), area.record.get("intervals"), area.name)
            self._features[(p, number)] = got
        return got

    def _source(self, zoom_km: float, index):
        return drawing_source(index, zoom_km)

    def _collect(self, lat, lon, rho, zoom_km, layers=None, min_widths=None, interval=None, isolate=None):
        """The shapes (Shapely) for the cap in view, with the feature of each and
        the box of its tile. Each tile's shapes are decoded together, once, and
        kept with the tile (P2-T14c). `layers`, when given, is the set of layer ids
        that are shown: the shapes of every other layer are left out (SCP-6). `min_widths`,
        when given, is {layer id: the least width in km} for an area layer, and an area
        narrower than that is left out (the size rule, NAV-13, DP80). `interval`, when given, leaves out
        a line that is not in the set of intervals its record names (DAT-13). `isolate`, when given,
        is the one feature to keep (VIS-2)."""
        geoms, feats, boxes, tile_of = [], [], [], []
        intervals, south, north = _cap(lat, lon, rho * 1.15)
        for p in self.store._covering(lat, lon)[:1]:
            index = self.store._indexes[p]
            kind, d = self._source(zoom_km, index)
            # The layers asked for; isolating a feature may need any layer (VIS-2).
            every = [x["id"] for x in index.pack.layers]
            wanted = every if layers is None or isolate is not None else [x for x in every if x in layers]
            for tkind, ident, level, allowed in plan_for(index, kind, d, wanted):
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
                        if allowed is not None:   # a level read only for layers the chosen level leaves out
                            keep = np.fromiter((f[3] in allowed for f in found), bool, len(found))
                            if not keep.any():
                                continue
                            shapes = shapes[keep]
                            found = [f for f, k in zip(found, keep) if k]
                        if isolate is not None:
                            keep = np.fromiter((f[0] == isolate for f in found), bool, len(found))
                            shapes = shapes[keep]
                            found = [f for f, k in zip(found, keep) if k]
                            if not len(shapes):
                                continue
                        elif layers is not None:
                            keep = np.fromiter((f[3] in layers and (not min_widths or f[4] is None
                                                                    or f[4] >= min_widths.get(f[3], 0.0))
                                                and (interval is None or f[5] is None or interval in f[5])
                                                for f in found), bool, len(found))
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
              centre_cross: bool = True, layers=None, min_widths=None, interval=None, theme: dict | None = None,
              isolate: str | None = None, names: bool = False, label_scale: float = 1.0,
              heading_up: bool = False, special_layers=frozenset(), fills: dict | None = None) -> dict:
        """One frame. theme is the theme to draw with (themes.effective), the builder's own when
        None. isolate keeps only that feature (VIS-2). names places the areas' names, at
        label_scale times their size (VIS-3, P2-T12d). heading_up turns the map (VIS-5).
        special_layers are the line layers drawn in the special line style (P2-T17v, DAT-13).
        fills is {layer id: land, water or none}, from the layers' definitions: water is painted in
        the ocean's colour, under the land; none is not painted, for a layer whose areas lie over
        the others, such as continents or mountain ranges (P3-T1e). A layer it leaves out is land,
        except the oceans."""
        import shapely

        if theme is not None:
            self.theme = theme
        start = time.perf_counter()
        view = view_for(world, width, height, heading_up)
        cx, cy, r = width / 2, height / 2, globe._radius(view, width, height)
        rho = math.asin(min(1.0, math.hypot(cx, cy) / r))
        geoms, feats, boxes, intervals, south, north = self._collect(world.lat, world.lon, rho, world.zoom_m / 1000.0,
                                                                     layers, min_widths, interval, isolate)
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
            fill = [fill_of(feats[i], fills) for i in idx.tolist()]
            # A layer that is not painted still has the current area's outline (VIS-1), as for a region with
            # "Draw the borders of regions" off (P3-T17); and an area isolated is painted, as it is all there is.
            if current or isolate:
                fill = [("land" if feats[i][0] == isolate else CLEAR if feats[i][0] == current else f) if f == "none"
                        else f for f, i in zip(fill, idx.tolist())]
            painted = np.array([f != "none" for f in fill], bool)
            if not painted.all():
                parts, idx = parts[painted], idx[painted]
                fill = [f for f, k in zip(fill, painted) if k]
            clear = {feats[i][0] for i, f in zip(idx.tolist(), fill) if f == CLEAR}
            # Water first, the oceans before the seas and lakes, then the land, each in its layer order.
            order = np.argsort(np.array([(0 if f == "water" else WATER_LAST) + feats[i][1]
                                         for f, i in zip(fill, idx.tolist())], np.intp), kind="stable")
            parts, idx = parts[order], idx[order]
            _t, xy, (ring_off, poly_off) = shapely.to_ragged_array(parts)
            ring_off = np.asarray(ring_off, np.intp)
            poly_off = np.asarray(poly_off, np.intp)
        else:
            xy, ring_off, poly_off = np.zeros((0, 2)), np.zeros(1, np.intp), np.zeros(1, np.intp)
            clear = set()
        chosen = time.perf_counter()
        frame = self._frame(view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes,
                            current, highlight, fills, clear)
        frame.update(self._lines(view, cx, cy, r, lines, line_idx, feats, highlight, special_layers))
        frame.update(self._markers(view, width, height, cx, cy, r, dots, dot_idx, feats, highlight))
        frame["points"] += int(len(frame["line_coords"]) // 2)
        frame.update(place_names(frame, self.theme, label_scale) if names else no_names(self.theme))
        frame["choose_ms"] = (chosen - start) * 1000            # finding and cutting the shapes in view (P2-T14b)
        frame["projecting_ms"] = (time.perf_counter() - chosen) * 1000   # turning them into screen pixels
        if centre_cross:
            frame["cross"] = {"x": cx, "y": cy, "size": 9, "colour": self.theme["cross"], "halo": self.theme["cross_halo"]}
        else:
            frame["cross"] = None
        frame["heading"] = {"x": cx, "y": cy, "degrees": (float(world.heading) - view.up) % 360.0,
                            "colour": self.theme["cross"],
                            "halo": self.theme["cross_halo"], "length": 26}
        frame["focus"] = focus_rect(width, height)
        frame["project_ms"] = (time.perf_counter() - start) * 1000   # the whole of the core's part
        return frame

    def _lines(self, view, cx, cy, r, lines, idx, feats, highlight, special_layers=frozenset()) -> dict:
        """Each line cut into runs of points on the near side of the globe, in screen pixels.
        A run's style is LINE_STYLE, HIGHLIGHT_LINE_STYLE for the item selected in the
        Information panel, or SPECIAL_LINE_STYLE for a line of a layer whose line_style is
        special, such as the equator (P2-T17v). The special lines are drawn last, on top."""
        import shapely

        theme = self.theme
        styles = [{"stroke": theme["line"], "width": theme["line_width"]},
                  {"stroke": theme["highlight_outline"], "width": theme["special_line_width"] + 2},
                  {"stroke": theme["special_line"], "width": theme["special_line_width"]}]
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
        found = [feats[idx[k]] for k in line_of_run.tolist()]
        area = [f[0] for f in found]
        style = np.array([HIGHLIGHT_LINE_STYLE if highlight and f[0] == highlight
                          else SPECIAL_LINE_STYLE if f[3] in special_layers else LINE_STYLE for f in found], np.int32)
        runs = np.concatenate([[0], np.cumsum(counts)]).astype(np.int32)
        # Plain lines first, then the special lines, then the highlighted line, so each is on top.
        order = np.argsort(np.array([LINE_DRAW_ORDER[s] for s in style.tolist()], np.intp), kind="stable")
        if len(order) and (order != np.arange(len(order))).any():
            pieces = [coords[2 * runs[k]:2 * runs[k + 1]] for k in order.tolist()]
            coords = np.concatenate(pieces).astype(np.float32)
            runs = np.concatenate([[0], np.cumsum(counts[order])]).astype(np.int32)
            style = style[order]
            area = [area[k] for k in order.tolist()]
        return {"line_coords": coords, "line_runs": runs, "line_style": style,
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

    def _frame(self, view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes, current, highlight,
               fills=None, clear=frozenset()):
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
        # A point where a seam starts or ends is always kept: dropped, the long edge along a pack
        # tile edge would take the mark of the short real edge before it and be outlined, as the
        # straight line along 45 degrees north across France was (P2-T17v, AD-17).
        keep = ~is_last
        if n_pts:
            qx, qy = np.round(sx * SNAP), np.round(sy * SNAP)
            same = np.zeros(n_pts, bool)
            same[1:] = (qx[1:] == qx[:-1]) & (qy[1:] == qy[:-1])
            turn = np.zeros(n_pts, bool)
            turn[1:] = seam[1:] != seam[:-1]
            keep &= is_first | ~same | turn
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
        styles = [{"fill": c, "stroke": theme["border"], "width": theme.get("border_width", 1)} for c in land]
        while len(styles) < OCEAN_STYLE:
            styles.append(styles[-1])
        styles.append({"fill": theme["ocean"], "stroke": "#00000000", "width": 0})   # OCEAN_STYLE
        styles.append({"fill": theme["highlight_fill"], "stroke": theme["highlight_outline"], "width": 2})
        styles.append({"fill": "#00000000", "stroke": "#00000000", "width": 0})   # CLEAR_STYLE
        shape_area, shape_style, shape_name = [], [], []
        for j in kept_polys:
            ident, layer, colour = feats[tile_of_poly[j]][:3]
            shape_area.append(ident)
            shape_name.append(feats[tile_of_poly[j]][6])
            water = fill_of(feats[tile_of_poly[j]], fills) == "water"
            shape_style.append(CLEAR_STYLE if ident in clear else OCEAN_STYLE if water else (colour - 1) % len(land))
        hi = [i for i, a in enumerate(shape_area) if highlight and a == highlight]
        for i in hi:
            shape_style[i] = HIGHLIGHT_STYLE
        cur = [i for i, a in enumerate(shape_area) if current and a == current]
        return {
            "width": width, "height": height, "background": theme["background"],
            "globe": {"cx": cx, "cy": cy, "r": r, "fill": theme["ocean"], "edge": theme["globe_edge"]},
            "coords": coords, "seam": seam[point_ok].astype(np.uint8), "rings": rings, "shapes": shapes,
            "shape_style": np.asarray(shape_style, np.int32), "shape_area": shape_area, "styles": styles,
            "shape_name": shape_name,
            "current": cur, "current_style": {"stroke": theme["current_outline"], "width": theme.get("current_width", 3)},
            "highlight": hi, "points": int(len(coords) // 2),
        }


# Names on the map (P2-T12d; VIS-3, SCP-2) ------------------------------------------------

NAME_MIN_PX = 11.0        # the smallest name, at 100%
NAME_MAX_PX = 22.0        # the largest name, at 100%
NAME_PER_SIDE = 0.06      # a name's size grows with the square root of its area on the map
CHAR_WIDTH = 0.6          # the width of an average letter, as a share of the size, for a plain sans-serif font
LINE_HEIGHT = 1.25
NAME_GAP_PX = 3.0         # the least space between two names
NAME_CANDIDATES = 150     # at most this many areas, the largest, are tried
CENTRE_CLEAR_PX = 30      # no name over the centre cross and the heading arrow


def no_names(theme: dict) -> dict:
    return {"names": [], "name_style": {"colour": theme["name_text"], "halo": theme["name_halo"]}}


def name_size(area_px: float, scale: float = 1.0) -> float:
    """The size of a name in pixels, for an area of area_px square pixels on the map: larger
    for a larger area, so names grow as you zoom in (VIS-3), times the label size setting."""
    base = min(NAME_MAX_PX, max(NAME_MIN_PX, NAME_PER_SIDE * math.sqrt(max(area_px, 0.0))))
    return round(base * 2) / 2 * scale


def name_box(x: float, y: float, text: str, size: float) -> tuple[float, float, float, float]:
    """The box a name centred on (x, y) takes: left, top, right, bottom."""
    half_w = (CHAR_WIDTH * size * len(text)) / 2 + 1
    half_h = LINE_HEIGHT * size / 2
    return x - half_w, y - half_h, x + half_w, y + half_h


def place_names(frame: dict, theme: dict, scale: float = 1.0) -> dict:
    """Where to put each visible area's name, as plain data for the shells: {"text", "x",
    "y", "size"}, centred on (x, y), in pixels. Larger areas first. A name goes inside its
    area, at the point furthest from its edges, only where the whole name fits; it never
    overlaps another name or the centre cross. Only areas on the map have names, so every
    name is one Where am I can say (SCP-2)."""
    import shapely

    out = no_names(theme)
    names = frame.pop("shape_name", None) or []
    shapes, rings = frame["shapes"], frame["rings"]
    if len(shapes) < 2:
        return out
    xy = np.asarray(frame["coords"], np.float64).reshape(-1, 2)
    try:
        polys = shapely.from_ragged_array(shapely.GeometryType.POLYGON, xy,
                                          (np.asarray(rings, np.intp), np.asarray(shapes, np.intp)))
    except Exception:   # a ring too short to be a polygon: no names this frame rather than no map
        return out
    width, height = frame["width"], frame["height"]
    area = shapely.area(polys)
    # The largest piece of each area, among the largest areas.
    best: dict[str, int] = {}
    for i in np.argsort(-area, kind="stable").tolist():
        ident = frame["shape_area"][i]
        if ident not in best and names[i]:
            best[ident] = i
            if len(best) >= NAME_CANDIDATES:
                break
    if not best:
        return out
    idx = np.fromiter(best.values(), np.intp, len(best))
    # A pixel of simplification is invisible in where a name goes, and makes the rest quick.
    pieces = shapely.clip_by_rect(shapely.simplify(polys[idx], 1.0, preserve_topology=False), 0, 0, width, height)
    bad = ~shapely.is_valid(pieces)
    if bad.any():   # a ring folded over the horizon
        pieces[bad] = shapely.make_valid(pieces[bad])
    pieces = np.array([_largest_polygon(g) for g in pieces], dtype=object)
    sizes = shapely.area(pieces)
    order = np.argsort(-sizes, kind="stable")
    cx, cy = width / 2, height / 2
    taken = [(cx - CENTRE_CLEAR_PX, cy - CENTRE_CLEAR_PX, cx + CENTRE_CLEAR_PX, cy + CENTRE_CLEAR_PX)]
    placed = []
    for k in order.tolist():
        piece = pieces[k]
        if piece is None or sizes[k] <= 0:
            continue
        text = names[idx[k]]
        size = name_size(sizes[k], scale)
        x0, y0, x1, y1 = shapely.bounds(piece)
        if (x1 - x0) < CHAR_WIDTH * size * len(text) or (y1 - y0) < LINE_HEIGHT * size:
            continue   # it cannot fit, so no need to look further
        try:
            centre = shapely.get_point(shapely.maximum_inscribed_circle(piece, max(0.5, math.sqrt(sizes[k]) / 100)), 0)
            x, y = shapely.get_x(centre), shapely.get_y(centre)
        except Exception:
            point = shapely.point_on_surface(piece)
            x, y = shapely.get_x(point), shapely.get_y(point)
        box = name_box(x, y, text, size)
        if box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height:
            continue
        if not shapely.contains(piece, shapely.box(*box)):
            continue
        g = NAME_GAP_PX
        if any(box[0] < b[2] + g and b[0] < box[2] + g and box[1] < b[3] + g and b[1] < box[3] + g for b in taken):
            continue
        taken.append(box)
        placed.append({"text": text, "x": round(float(x), 1), "y": round(float(y), 1), "size": size})
    out["names"] = placed
    return out


def _largest_polygon(geom):
    """The largest polygon in a geometry, or None."""
    import shapely

    if geom is None or shapely.is_empty(geom):
        return None
    parts = shapely.get_parts(geom)
    parts = parts[shapely.get_type_id(parts) == 3]
    if not len(parts):
        return None
    return parts[int(np.argmax(shapely.area(parts)))]
