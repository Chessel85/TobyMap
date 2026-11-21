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

Bookmarks are drawn on top of everything (P4-T8f, DP219 point 5): "bookmarks" holds, for each bookmark
on the near side of the globe and on the map, its point in screen pixels, the half-width of its diamond, a
fixed size on screen scaled by the Label size setting, whether it is the item selected, and its name, to
be drawn left-aligned beside it; "bookmark_style" the theme's colours for them.

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
PLAIN_STYLE = 10   # one plain land colour, as the physical view paints the countries (P3-T23)
KIND_STYLE = 11    # the first of the physical colours, one for each kind of layer (P3-T23)
# After the physical colours: the lighter blue of the territorial waters (P4-T12b), at KIND_STYLE + their number.
THIN_OUTLINE, THICK_OUTLINE = 0, 1   # the outline styles: every area's, and the country borders (P3-T23)
LINE_STYLE, HIGHLIGHT_LINE_STYLE, SPECIAL_LINE_STYLE = 0, 1, 2   # the line styles (P2-T17v)
LINE_DRAW_ORDER = {LINE_STYLE: 0, SPECIAL_LINE_STYLE: 1, HIGHLIGHT_LINE_STYLE: 2}
MIN_RING = 3
WATER_LAST = 100   # added to a land layer's order, so all water is painted first
BOOKMARK_PX = 12.0        # a bookmark's diamond, corner to corner, at a Label size of 100% (DP219 point 5)
BOOKMARK_NAME_PX = 12.0   # its name's size at 100%
BOOKMARK_GAP_PX = 4.0     # between the diamond and its name
CLIP_CHUNK = 2000   # shapes cut to the view in one step of a drawing (P3-T24a)
NAMES_PER_STEP = 15   # names placed in one step
LINE_CHUNK = 3000   # lines turned into screen points in one step
FRAME_CHUNK_POINTS = 150_000   # area points turned into screen pixels in one step


DECODE_CHUNK_BYTES = 30_000   # stored bytes of a tile decoded in one step of a drawing (P3-T24a)


def _decode_in_chunks(data, indices, box):
    """Decode a tile's entries a chunk at a time, yielding between chunks. The shapes are kept with the
    tile (TileData.shapes_of), where drawing_shapes then finds them. A small tile is left to be decoded at once."""
    entries = data.entries
    todo = [i for i in indices if entries[i].kind != tiles.COVERED]
    if sum(len(entries[i].data) for i in todo) <= DECODE_CHUNK_BYTES:
        return
    chunk, size = [], 0
    for i in todo:
        chunk.append(i)
        size += len(entries[i].data)
        if size >= DECODE_CHUNK_BYTES:
            data.shapes_of(chunk, box)
            chunk, size = [], 0
            yield
    if chunk:
        data.shapes_of(chunk, box)
        yield


def _outline_order(frame: dict, shapes, styles) -> None:
    """The outlines, in the order drawn: every area's first, then the country borders on top (P3-T23)."""
    order = np.argsort(np.asarray(styles, np.intp), kind="stable")
    frame["outline_shapes"] = np.asarray(shapes, np.int32)[order] if len(order) else np.zeros(0, np.int32)
    frame["outline_style"] = np.asarray(styles, np.int32)[order] if len(order) else np.zeros(0, np.int32)


def _drain(steps):
    """Run a generator of steps to its end, and return what it returns."""
    while True:
        try:
            next(steps)
        except StopIteration as done:
            return done.value


def paint_plan(feats: list, paint: dict | None, fills: dict | None, theme: dict, current=None, isolate=None) -> dict:
    """How each feature is painted (P3-T23, DP198): arrays, one entry for each of feats, of its fill style
    (an index into the frame's styles, or -1 for not painted), its outline style (-1 for none), whether
    its name is drawn, and its place in the drawing order. paint is {layer id: {fill, outline, names, order,
    thick}} from the map view in use (MapSession._paint); without it, the layers' fills are used, as before
    the views. The current feature is always kept, so it can be outlined and tinted, and an isolated one is
    always filled (VIS-2)."""
    kinds = sorted((theme.get("physical") or {}).keys())
    n = len(feats)
    style = np.full(n, -1, np.intp)
    outline = np.full(n, -1, np.intp)
    named = np.zeros(n, bool)
    order = np.zeros(n, float)
    land_count = len(theme["land"])
    for k, f in enumerate(feats):
        ident, rank, colour, layer = f[0], f[1], f[2], f[3]
        if paint is not None and layer in paint:
            spec = paint[layer]
            fill = spec.get("fill", "colours")
            line = (THICK_OUTLINE if spec.get("thick") else THIN_OUTLINE) if spec.get("outline", True) else -1
            name = spec.get("names")
            order[k] = spec.get("order", 0.0)
        else:
            fill = fill_of(f, fills)
            fill = "colours" if fill == "land" else fill
            line = -1 if fill in ("water", "none") else THIN_OUTLINE
            name = None
            order[k] = (0 if fill == "water" else WATER_LAST) + rank
        if ident == isolate and fill == "none":
            fill = "colours"
        if fill == "water":
            style[k] = OCEAN_STYLE
        elif fill == "light_water":
            style[k] = KIND_STYLE + len(kinds)
        elif fill == "plain":
            style[k] = PLAIN_STYLE
        elif fill == "kind":
            style[k] = KIND_STYLE + kinds.index(layer) if layer in kinds else (
                KIND_STYLE + kinds.index("default") if "default" in kinds else PLAIN_STYLE)
        elif fill in ("colours", "land"):
            style[k] = (int(colour) - 1) % land_count
        elif line >= 0 or ident == current:
            style[k] = CLEAR_STYLE   # not filled, but outlined or the current feature
        named[k] = (fill != "none") if name is None else bool(name)
        outline[k] = line
    return {"style": style, "outline": outline, "names": named, "order": order}


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

    def _collect(self, lat, lon, rho, zoom_km, layers=None, min_widths=None, interval=None, isolate=None, limit=None):
        """The shapes for the cap in view (see _collect_steps), all at once."""
        return _drain(self._collect_steps(lat, lon, rho, zoom_km, layers, min_widths, interval, isolate, limit))

    def _collect_steps(self, lat, lon, rho, zoom_km, layers=None, min_widths=None, interval=None, isolate=None,
                       limit=None):
        """A generator that yields between pack tiles, so a drawing can give way to a key (P3-T24a, DP202),
        and returns the shapes (Shapely) for the cap in view, with the feature of each and
        the box of its tile. Each tile's shapes are decoded together, once, and
        kept with the tile (P2-T14c). `layers`, when given, is the set of layer ids
        that are shown: the shapes of every other layer are left out (SCP-6). `min_widths`,
        when given, is {layer id: the least width in km} for an area layer, and an area
        narrower than that is left out (the size rule, NAV-13, DP80). `interval`, when given, leaves out
        a line that is not in the set of intervals its record names (DAT-13). `isolate`, when given,
        is the one feature to keep (VIS-2). `limit`, when given, is {pack: the set of feature numbers to
        draw}, the drawing's limit (P3-T24a): only those entries of a tile are decoded."""
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
                        yield
                        data = self.store._tile(p, "draw" if tkind == "draw" else "tile", ident if tkind == "draw" else level, x, y)
                        if not data.entries:
                            continue
                        box = tiles.tile_box(level, x, y)
                        wanted_here = None if limit is None or isolate is not None else limit.get(p, set())
                        drawn_here = None if wanted_here is None else wanted_here.intersection(data.by_feature)
                        partial = drawn_here is not None and data.drawing is None and len(drawn_here) < len(data.by_feature)
                        if data.drawing is None:
                            # A large tile, such as the roads round a city, is decoded in chunks, a step each.
                            todo = (sorted(i for n in drawn_here for i in data.by_feature[n]) if partial
                                    else range(len(data.entries)))
                            yield from _decode_in_chunks(data, todo, box)
                        if partial:
                            # The drawing's limit: decode only the entries of the features drawn.
                            entries = sorted(i for n in drawn_here for i in data.by_feature[n])
                            if not entries:
                                continue
                            got = data.shapes_of(entries, box)
                            shapes = np.empty(len(entries), object)
                            shapes[:] = [got[i] for i in entries]
                            numbers = np.fromiter((data.entries[i].feature for i in entries), np.int64, len(entries))
                        else:
                            shapes, numbers = data.drawing_shapes(box)
                            if wanted_here is not None:
                                mask = np.fromiter((n in wanted_here for n in numbers.tolist()), bool, len(numbers))
                                if not mask.all():
                                    shapes, numbers = shapes[mask], numbers[mask]
                                if not len(numbers):
                                    continue
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

    def build(self, world, width: int, height: int, **options) -> dict:
        """One frame, made at once (see steps)."""
        return _drain(self.steps(world, width, height, **options))

    def steps(self, world, width: int, height: int, current: str | None = None, highlight: str | None = None,
              centre_cross: bool = True, layers=None, min_widths=None, interval=None, theme: dict | None = None,
              isolate: str | None = None, names: bool = False, label_scale: float = 1.0,
              heading_up: bool = False, special_layers=frozenset(), fills: dict | None = None, limit=None,
              paint: dict | None = None, bookmarks=()):
        """One frame, made in steps: a generator that yields between them, so that the drawing never holds
        up what is said (P3-T24a, DP202), and returns the frame. limit is the drawing's limit, the features
        to draw by pack (see _collect_steps). theme is the theme to draw with (themes.effective), the builder's own when
        None. isolate keeps only that feature (VIS-2). names places the areas' names, at
        label_scale times their size (VIS-3, P2-T12d). heading_up turns the map (VIS-5).
        special_layers are the line layers drawn in the special line style (P2-T17v, DAT-13).
        fills is {layer id: land, water or none}, from the layers' definitions: water is painted in
        the ocean's colour, under the land; none is not painted, for a layer whose areas lie over
        the others, such as continents or mountain ranges (P3-T1e). A layer it leaves out is land,
        except the oceans. paint, when given, is the map view's plan for each layer, which replaces fills
        (P3-T23, see paint_plan): the drawing order, the fill, the outline and the names.
        bookmarks are the bookmarks shown, (id, name, lat, lon) each, drawn as marks on top (P4-T8f)."""
        import shapely

        if theme is not None:
            self.theme = theme
        start = time.perf_counter()
        view = view_for(world, width, height, heading_up)
        cx, cy, r = width / 2, height / 2, globe._radius(view, width, height)
        rho = math.asin(min(1.0, math.hypot(cx, cy) / r))
        geoms, feats, boxes, intervals, south, north = yield from self._collect_steps(
            world.lat, world.lon, rho, world.zoom_m / 1000.0, layers, min_widths, interval, isolate, limit)
        yield
        empty = np.zeros(0, np.intp)
        lines, line_idx, dots, dot_idx = np.empty(0, object), empty, np.empty(0, object), empty
        if len(geoms):
            parts_all, idx_all = [], []
            other_all, other_idx_all = [], []
            for west, east in intervals:
                for at in range(0, len(geoms), CLIP_CHUNK):   # in chunks, a step each
                    clipped = shapely.clip_by_rect(geoms[at:at + CLIP_CHUNK], west, south, east, north)
                    parts, idx = shapely.get_parts(clipped, return_index=True)
                    idx = np.asarray(idx, np.intp) + at
                    kinds = shapely.get_type_id(parts)
                    live = ~shapely.is_empty(parts)
                    keep = (kinds == 3) & live
                    parts_all.append(parts[keep])
                    idx_all.append(idx[keep])
                    other = ((kinds == 1) | (kinds == 0)) & live   # lines and points (P2-T10a)
                    other_all.append(parts[other])
                    other_idx_all.append(idx[other])
                    yield
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
        plan = paint_plan(feats, paint, fills, self.theme, current, isolate)
        if len(parts):
            # A shape neither filled nor outlined is left out, unless it is the current feature's, which is
            # always outlined and tinted (VIS-1, P3-T23).
            drawn = plan["style"][idx] >= 0
            if not drawn.all():
                parts, idx = parts[drawn], idx[drawn]
            # In the drawing order of the views file, and within a layer the larger under the smaller.
            size_km = np.fromiter(((f[4] or 0.0) for f in feats), float, len(feats))
            order = np.lexsort((-size_km[idx], plan["order"][idx]))
            parts, idx = parts[order], idx[order]
            yield
            _t, xy, (ring_off, poly_off) = shapely.to_ragged_array(parts)
            ring_off = np.asarray(ring_off, np.intp)
            poly_off = np.asarray(poly_off, np.intp)
        else:
            xy, ring_off, poly_off = np.zeros((0, 2)), np.zeros(1, np.intp), np.zeros(1, np.intp)
        chosen = time.perf_counter()
        yield
        frame = yield from self._frame_steps(view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats,
                                             boxes, current, highlight, plan)
        yield
        under = frozenset(k for k, v in (paint or {}).items() if v.get("under"))
        frame.update((yield from self._lines_steps(view, cx, cy, r, lines, line_idx, feats, highlight, special_layers,
                                                   under)))
        yield
        frame.update(self._markers(view, width, height, cx, cy, r, dots, dot_idx, feats, highlight))
        frame["points"] += int(len(frame["line_coords"]) // 2)
        if names:
            yield
            frame.update((yield from place_names_steps(frame, self.theme, label_scale)))
        else:
            frame.update(no_names(self.theme))
        frame.update(self._bookmarks(view, width, height, cx, cy, r, bookmarks, highlight, names, label_scale))
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

    def _lines(self, view, cx, cy, r, lines, idx, feats, highlight, special_layers=frozenset(), under=frozenset()) -> dict:
        """The lines' runs (see _lines_steps), all at once."""
        return _drain(self._lines_steps(view, cx, cy, r, lines, idx, feats, highlight, special_layers, under))

    def _lines_steps(self, view, cx, cy, r, lines, idx, feats, highlight, special_layers=frozenset(),
                     under=frozenset()):
        """Each line cut into runs of points on the near side of the globe, in screen pixels.
        A run's style is LINE_STYLE, HIGHLIGHT_LINE_STYLE for the item selected in the
        Information panel, or SPECIAL_LINE_STYLE for a line of a layer whose line_style is
        special, such as the equator (P2-T17v). The special lines are drawn last, on top.
        A generator, a step for each chunk of lines (P3-T24a), that returns them. The lines of the layers in
        under, such as rivers, come first, and lines_under says how many runs they are: the shells draw them
        before the areas' outlines, the rest after (P3-T23, the drawing order)."""
        import shapely

        theme = self.theme
        styles = [{"stroke": theme["line"], "width": theme["line_width"]},
                  {"stroke": theme["highlight_outline"], "width": theme["special_line_width"] + 2},
                  {"stroke": theme["special_line"], "width": theme["special_line_width"]}]
        if not len(lines):
            return {"line_coords": np.zeros(0, np.float32), "line_runs": np.zeros(1, np.int32),
                    "line_style": np.zeros(0, np.int32), "line_area": [], "line_styles": styles, "lines_under": 0}
        idx = np.asarray(idx, np.intp)
        coords_all, counts_all, feat_all = [], [], []
        for at in range(0, len(lines), LINE_CHUNK):
            xy, which = shapely.get_coordinates(lines[at:at + LINE_CHUNK], return_index=True)
            px, py, depth = globe.project_points(view, xy[:, 1], xy[:, 0])
            seen = depth >= 0
            if not seen.any():   # every line of the chunk is on the far side of the globe
                yield
                continue
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
            coords_all.append(coords)
            counts_all.append(counts)
            feat_all.append(idx[at + which[keep][first_point]])
            yield
        if not coords_all:
            return {"line_coords": np.zeros(0, np.float32), "line_runs": np.zeros(1, np.int32),
                    "line_style": np.zeros(0, np.int32), "line_area": [], "line_styles": styles, "lines_under": 0}
        coords = np.concatenate(coords_all).astype(np.float32)
        counts = np.concatenate(counts_all).astype(np.intp)
        feat_of_run = np.concatenate(feat_all).astype(np.intp)
        # Each run's feature, layer and style, worked out once for each feature, not for each run.
        used, inverse = np.unique(feat_of_run, return_inverse=True)
        used_ids = [feats[k][0] for k in used.tolist()]
        special = np.fromiter((feats[k][3] in special_layers for k in used.tolist()), bool, len(used))
        high = np.fromiter((bool(highlight) and i == highlight for i in used_ids), bool, len(used))
        below = np.fromiter((feats[k][3] in under for k in used.tolist()), bool, len(used))[inverse]
        style_of_used = np.where(high, HIGHLIGHT_LINE_STYLE, np.where(special, SPECIAL_LINE_STYLE, LINE_STYLE))
        style = style_of_used[inverse].astype(np.int32)
        run_feature = inverse
        # Plain lines first, then the special lines, then the highlighted line, so each is on top.
        rank = np.array([LINE_DRAW_ORDER[k] for k in range(len(LINE_DRAW_ORDER))], np.intp)[style] \
            + np.where(below, 0, len(LINE_DRAW_ORDER))
        order = np.argsort(rank, kind="stable")
        if len(order) and (order != np.arange(len(order))).any():
            point_run = np.repeat(np.arange(len(counts), dtype=np.intp), counts)
            position = np.empty(len(order), np.intp)
            position[order] = np.arange(len(order), dtype=np.intp)
            moved = np.argsort(position[point_run], kind="stable")
            coords = coords.reshape(-1, 2)[moved].ravel()
            counts, style, run_feature = counts[order], style[order], run_feature[order]
        runs = np.concatenate([[0], np.cumsum(counts)]).astype(np.int32)
        area = np.asarray(used_ids, object)[run_feature].tolist() if len(run_feature) else []
        return {"line_coords": coords, "line_runs": runs, "line_style": style,
                "line_area": area, "line_styles": styles, "lines_under": int(below.sum())}

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

    def _bookmarks(self, view, width, height, cx, cy, r, bookmarks, highlight, names, scale) -> dict:
        """The bookmarks' marks (P4-T8f, DP219 point 5): a diamond the same size on screen at every zoom, so it
        never covers the map at a wide zoom or vanishes at a close one, scaled by the Label size setting, with
        the bookmark's name to its right, when names are drawn. A mark is left out on the far side of the globe
        or off the map. No name is moved for another: they are drawn where they fall, as the places' markers."""
        theme = self.theme
        style = {"fill": theme.get("bookmark", theme["marker"]),
                 "stroke": theme.get("bookmark_outline", theme["marker_outline"]),
                 "selected_fill": theme["highlight_fill"], "selected_stroke": theme["highlight_outline"],
                 "colour": theme["name_text"], "halo": theme["name_halo"]}
        out = []
        if bookmarks:
            lats = np.array([b[2] for b in bookmarks], float)
            lons = np.array([b[3] for b in bookmarks], float)
            px, py, depth = globe.project_points(view, lats, lons)
            sx, sy = cx + r * px, cy - r * py
            half = BOOKMARK_PX / 2 * scale
            size = BOOKMARK_NAME_PX * scale
            for k, (ident, name, _lat, _lon) in enumerate(bookmarks):
                x, y = float(sx[k]), float(sy[k])
                if depth[k] < 0 or not (-half <= x <= width + half and -half <= y <= height + half):
                    continue
                out.append({"x": round(x, 1), "y": round(y, 1), "half": half, "selected": bool(highlight and ident == highlight),
                            "text": name if names else "", "text_x": round(x + half + BOOKMARK_GAP_PX * scale, 1),
                            "text_y": round(y, 1), "text_size": size})
        return {"bookmarks": out, "bookmark_style": style}

    def _frame(self, view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes, current, highlight,
               plan=None):
        """The areas in screen pixels (see _frame_steps), all at once."""
        return _drain(self._frame_steps(view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes,
                                        current, highlight, plan))

    def _frame_steps(self, view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes, current,
                     highlight, plan=None):
        """The areas in screen pixels, made a chunk of polygons at a time, a step each (P3-T24a), and joined.
        Each chunk is independent: its rings and shapes are counted from its own start, then moved on."""
        n_polys = len(poly_off) - 1
        if n_polys <= 0:
            return self._frame_part(view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes,
                                    current, highlight, plan)
        point_at_poly = ring_off[poly_off]   # the first point of each polygon, and the end
        cuts = [0]
        while cuts[-1] < n_polys:
            target = point_at_poly[cuts[-1]] + FRAME_CHUNK_POINTS
            nxt = int(np.searchsorted(point_at_poly, target, side="right")) - 1
            cuts.append(min(n_polys, max(nxt, cuts[-1] + 1)))
        if len(cuts) == 2:
            return self._frame_part(view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes,
                                    current, highlight, plan)
        pieces = []
        for p0, p1 in zip(cuts, cuts[1:]):
            r0, r1 = int(poly_off[p0]), int(poly_off[p1])
            q0, q1 = int(ring_off[r0]), int(ring_off[r1])
            pieces.append(self._frame_part(view, width, height, cx, cy, r, xy[q0:q1], ring_off[r0:r1 + 1] - q0,
                                           poly_off[p0:p1 + 1] - r0, idx[p0:p1], feats, boxes, current, highlight,
                                           plan))
            yield
        frame = pieces[0]
        points, rings_so_far, shapes_so_far = len(frame["coords"]) // 2, len(frame["rings"]) - 1, len(frame["shapes"]) - 1
        coords, seam, rings, shapes, styles_of = [frame["coords"]], [frame["seam"]], [frame["rings"]], [frame["shapes"]], [frame["shape_style"]]
        outlined, outline_style = [frame["outline_shapes"]], [frame["outline_style"]]
        for part in pieces[1:]:
            outlined.append(part["outline_shapes"] + shapes_so_far)
            outline_style.append(part["outline_style"])
            coords.append(part["coords"])
            seam.append(part["seam"])
            rings.append(part["rings"][1:] + points)
            shapes.append(part["shapes"][1:] + rings_so_far)
            styles_of.append(part["shape_style"])
            frame["shape_area"] += part["shape_area"]
            frame["shape_name"] += part["shape_name"]
            frame["current"] += [i + shapes_so_far for i in part["current"]]
            frame["highlight"] += [i + shapes_so_far for i in part["highlight"]]
            points += len(part["coords"]) // 2
            rings_so_far += len(part["rings"]) - 1
            shapes_so_far += len(part["shapes"]) - 1
        frame["coords"] = np.concatenate(coords).astype(np.float32)
        frame["seam"] = np.concatenate(seam).astype(np.uint8)
        frame["rings"] = np.concatenate(rings).astype(np.int32)
        frame["shapes"] = np.concatenate(shapes).astype(np.int32)
        frame["shape_style"] = np.concatenate(styles_of).astype(np.int32)
        frame["points"] = int(points)
        _outline_order(frame, np.concatenate(outlined), np.concatenate(outline_style))
        return frame

    def _frame_part(self, view, width, height, cx, cy, r, xy, ring_off, poly_off, idx, feats, boxes, current,
                    highlight, plan=None):
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

        if plan is None:
            plan = paint_plan(feats, None, None, theme, current)
        none = "#00000000"
        # The fills: the outlines are drawn after, as lines over everything painted (P3-T23), so a fill has none.
        styles = [{"fill": c, "stroke": none, "width": 0} for c in theme["land"]]
        while len(styles) < OCEAN_STYLE:
            styles.append(styles[-1])
        styles.append({"fill": theme["ocean"], "stroke": none, "width": 0})   # OCEAN_STYLE
        styles.append({"fill": theme["highlight_fill"], "stroke": theme["highlight_outline"], "width": 2})
        styles.append({"fill": none, "stroke": none, "width": 0})   # CLEAR_STYLE
        physical = theme.get("physical") or {}
        styles.append({"fill": theme.get("plain_land", theme["land"][0]), "stroke": none, "width": 0})   # PLAIN_STYLE
        styles += [{"fill": physical[k], "stroke": none, "width": 0} for k in sorted(physical)]   # KIND_STYLE on
        styles.append({"fill": theme.get("light_water", theme["ocean"]), "stroke": none, "width": 0})   # light water
        shape_area, shape_style, shape_name, line_style = [], [], [], []
        for j in kept_polys:
            k = tile_of_poly[j]
            ident = feats[k][0]
            shape_area.append(ident)
            shape_name.append(feats[k][6] if plan["names"][k] else "")
            shape_style.append(int(plan["style"][k]))
            line_style.append(int(plan["outline"][k]))
        hi = [i for i, a in enumerate(shape_area) if highlight and a == highlight]
        for i in hi:
            shape_style[i] = HIGHLIGHT_STYLE
        cur = [i for i, a in enumerate(shape_area) if current and a == current]
        line_style = np.asarray(line_style, np.intp)
        frame = {
            "width": width, "height": height, "background": theme["background"],
            "globe": {"cx": cx, "cy": cy, "r": r, "fill": theme["ocean"], "edge": theme["globe_edge"]},
            "coords": coords, "seam": seam[point_ok].astype(np.uint8), "rings": rings, "shapes": shapes,
            "shape_style": np.asarray(shape_style, np.int32), "shape_area": shape_area, "styles": styles,
            "shape_name": shape_name,
            # The current feature: outlined and filled with a translucent tint, on top of everything (P3-T23).
            "current": cur, "current_style": {"stroke": theme["current_outline"], "width": theme.get("current_width", 3),
                                              "tint": theme.get("current_tint", theme["current_outline"]),
                                              "tint_alpha": float(theme.get("current_tint_alpha", 0.2))},
            "highlight": hi, "points": int(len(coords) // 2),
            "outline_styles": [{"stroke": theme["border"], "width": theme.get("border_width", 1)},
                               {"stroke": theme["border"], "width": theme.get("country_border_width",
                                                                             2 * theme.get("border_width", 1))}],
        }
        keep = np.nonzero(line_style >= 0)[0]
        _outline_order(frame, keep.astype(np.intp), line_style[keep])
        return frame


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
    """The names' places (see place_names_steps), all at once."""
    return _drain(place_names_steps(frame, theme, scale))


def place_names_steps(frame: dict, theme: dict, scale: float = 1.0):
    """A generator, yielding every few names (P3-T24a), that returns where to put each visible area's name, as plain data for the shells: {"text", "x",
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
    for n, k in enumerate(order.tolist()):
        if n % NAMES_PER_STEP == NAMES_PER_STEP - 1:
            yield
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
