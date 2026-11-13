"""The visible rule (P2-T4a; NAV-13, SCP-7, ANN-7, DP80, architecture 7.4).

A feature is visible when:

* its layer is on;
* the zoom is within its layer's zoom range;
* for an area, its stored width is at least its layer's minimum size, by
  default 2% of the zoom distance;
* at least part of it is within the view, the circle on the Earth's surface
  round the location whose radius is the zoom distance.

The first three tests use only the layer and the feature record, so they cost
almost nothing. The last is done in three steps, cheapest first:

1. Each feature's box is compared with the view. A box wholly outside it is
   out, and a box wholly inside it is in. This decides nearly every feature.
2. For the features left, the tiles the map is drawn from at this zoom (the
   drawing tiles, or the exact pack tiles when close in) are compared with the
   view in the same way. Every feature in a tile wholly inside the view is in.
3. Only in the tiles across the edge of the view are shapes looked at: a
   feature is in if the location is inside one of its shapes, or one of them
   comes within the zoom distance. The shapes are cut to round the view and
   put in an azimuthal equidistant projection centred on the location, where
   the distance from the centre is the true distance.

Distances here are on the mean sphere, which is within half a percent of the
ellipsoid: enough to decide what is in view, never used for what is said.

"Where am I" is never limited by this rule (ANN-7). Crossed and passed uses
only the layer and zoom tests, because a long step can reach beyond the view
(DP80, architecture 7.5): shown_layers() gives those.
"""
from __future__ import annotations

import math

import numpy as np

from mapcore.geo import geodesy
from mapcore.packs import tiles

HALF_PI = math.pi / 2
MARGIN = 1.02            # the shapes are cut a little wider than the view, so nothing at its edge is lost
SLACK = 1e-3             # degrees added to the cheap tests of the box edges kept in single precision


def _angles(lat1: float, lon1: float, lat2, lon2) -> np.ndarray:
    """The angle at the centre of the Earth between a point and arrays of points, in radians."""
    p1, p2 = math.radians(lat1), np.radians(lat2)
    half_dp = (p2 - p1) / 2
    half_dl = np.radians((np.asarray(lon2, dtype=np.float64) - lon1) % 360.0) / 2
    h = np.sin(half_dp) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(half_dl) ** 2
    return 2 * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def _within(lat: float, lon: float, lats: np.ndarray, lons: np.ndarray, rho: float) -> np.ndarray:
    """Whether each point is within the angle rho of a point: _angles, without its square
    root and arcsine, compared with the haversine of rho instead."""
    p1, p2 = math.radians(lat), np.radians(lats)
    h = np.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(np.radians(lons - lon) / 2) ** 2
    return h <= math.sin(min(rho, math.pi) / 2) ** 2


def box_reach(boxes: np.ndarray, lat: float, lon: float) -> tuple[np.ndarray, np.ndarray]:
    """The nearest and farthest that each box (west, south, east, north, in degrees)
    comes to a point, as angles at the centre of the Earth, in radians.

    A box whose west is greater than its east crosses the 180 degree line; one from
    -180 to 180 goes round the world. The answers are exact on the sphere:

    * nearest: 0 inside the box; else the nearest of the corners, the feet of the
      perpendiculars to the two meridian edges, and, where the point's longitude is
      within the box, straight north or south to the box;
    * farthest: the farthest corner, or the point on a parallel edge directly
      opposite the point's longitude where the box reaches it, or half way round
      the world where the box holds the point's antipode. Along a meridian or a
      parallel the distance never peaks between the ends otherwise.
    """
    boxes = np.asarray(boxes, dtype=np.float64).reshape(-1, 4)
    west, south, east, north = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    point = (west == east) & (south == north)
    if point.all():
        # A place's box is a single point: nearest and farthest are its distance.
        d = _angles(lat, lon, south, west)
        return d, d.copy()
    if point.any():
        near, far = np.empty(len(boxes)), np.empty(len(boxes))
        near[point] = far[point] = _angles(lat, lon, south[point], west[point])
        near[~point], far[~point] = box_reach(boxes[~point], lat, lon)
        return near, far
    span = _spans(west, east)

    def within(lons) -> np.ndarray:
        return ((lons - west) % 360.0) <= span

    phi = math.radians(lat)
    lon_in = within(lon)
    corners = np.stack([_angles(lat, lon, south, west), _angles(lat, lon, south, east),
                        _angles(lat, lon, north, west), _angles(lat, lon, north, east)])
    s, n = np.radians(south), np.radians(north)

    near = corners.min(axis=0)
    straight = np.maximum(np.maximum(s - phi, phi - n), 0.0)
    near = np.where(lon_in, np.minimum(near, straight), near)
    for edge in (west, east):
        dl = np.radians((lon - edge + 180.0) % 360.0 - 180.0)
        foot = np.arctan2(math.sin(phi), math.cos(phi) * np.cos(dl))
        to_foot = np.arcsin(np.clip(math.cos(phi) * np.abs(np.sin(dl)), 0.0, 1.0))
        ok = (np.abs(dl) <= HALF_PI) & (foot >= s) & (foot <= n)
        near = np.where(ok, np.minimum(near, to_foot), near)

    far = corners.max(axis=0)
    for edge in (west, east):
        # More than a quarter of the way round, a meridian edge is farthest at the
        # point opposite its nearest point on the other half of the same circle.
        dl = np.radians((lon - edge + 180.0) % 360.0 - 180.0)
        peak = np.arctan2(-math.sin(phi), -math.cos(phi) * np.cos(dl))
        to_peak = math.pi - np.arcsin(np.clip(math.cos(phi) * np.abs(np.sin(dl)), 0.0, 1.0))
        ok = (np.abs(dl) > HALF_PI) & (peak >= s) & (peak <= n)
        far = np.where(ok, np.maximum(far, to_peak), far)
    opposite = lon + 180.0
    across = within(opposite)
    to_edge = np.maximum(math.pi - np.abs(phi + s), math.pi - np.abs(phi + n))
    far = np.where(across, np.maximum(far, to_edge), far)
    antipode = across & (-phi >= s) & (-phi <= n)
    far = np.where(antipode, math.pi, far)
    return near, far


def _cap_boxes(lat: float, lon: float, rho: float) -> list[tuple[float, float, float, float]]:
    """Boxes (west, south, east, north), none across the 180 degree line, that together
    hold the cap of angular radius rho round a point."""
    south = max(-90.0, lat - math.degrees(rho))
    north = min(90.0, lat + math.degrees(rho))
    c = math.cos(math.radians(lat))
    if rho >= HALF_PI or north >= 90.0 or south <= -90.0 or c <= math.sin(rho):
        return [(-180.0, south, 180.0, north)]
    half = math.degrees(math.asin(math.sin(rho) / c))
    west, east = lon - half, lon + half
    if west < -180.0:
        return [(west + 360.0, south, 180.0, north), (-180.0, south, east, north)]
    if east > 180.0:
        return [(west, south, 180.0, north), (-180.0, south, east - 360.0, north)]
    return [(west, south, east, north)]


def _spans(west: np.ndarray, east: np.ndarray) -> np.ndarray:
    """The degrees of longitude each box spans eastward from its west edge, as box_reach reads them."""
    span = (east - west) % 360.0
    span = np.where((span == 0.0) & (east != west), 360.0, span)
    return np.where((west <= -180.0) & (east >= 180.0), 360.0, span)


def _meets_longitudes(west: np.ndarray, east: np.ndarray, cut) -> np.ndarray:
    """Whether each box shares any longitude with the boxes of _cap_boxes, none of which
    crosses the 180 degree line: a cheap test before box_reach, which costs far more. The
    box's west edge is from -180 to 180 and its east edge is west plus its span, so up to
    540; the part beyond 180 is the same longitudes less 360."""
    meets = np.zeros(len(west), bool)
    for c_west, _s, c_east, _n in cut:
        c_west, c_east = c_west - SLACK, c_east + SLACK
        meets |= ((west <= c_east) & (east >= c_west)) | (east - 360.0 >= c_west)
    return meets


class _Azimuthal:
    """An azimuthal equidistant projection on the mean sphere, centred on a point, in
    radians of the sphere: a point's distance from (0, 0) is its true angle from the centre."""

    def __init__(self, lat: float, lon: float):
        self.lon0 = lon
        self.sin0, self.cos0 = math.sin(math.radians(lat)), math.cos(math.radians(lat))

    def __call__(self, xy: np.ndarray) -> np.ndarray:
        p = np.radians(xy[:, 1])
        dl = np.radians((xy[:, 0] - self.lon0 + 180.0) % 360.0 - 180.0)
        cos_c = np.clip(self.sin0 * np.sin(p) + self.cos0 * np.cos(p) * np.cos(dl), -1.0, 1.0)
        c = np.arccos(cos_c)
        az = np.arctan2(np.sin(dl) * np.cos(p), self.cos0 * np.sin(p) - self.sin0 * np.cos(p) * np.cos(dl))
        return np.column_stack([c * np.sin(az), c * np.cos(az)])


class VisibleRule:
    """Which features are visible, from the store and the layer catalogue."""

    def __init__(self, store, layers):
        self.store = store
        self.layers = layers

    # The first three tests --------------------------------------------------------

    def shown_layers(self, zoom_m: float) -> frozenset:
        """The ids of the layers that are on and whose zoom range holds the zoom."""
        return frozenset(layer.id for layer in self.layers.layers() if layer.on and layer.in_zoom(zoom_m))

    def min_widths(self, zoom_m: float) -> dict:
        """For each area layer that is shown, the least width in km an area must have (DP80)."""
        return {layer.id: layer.min_size * zoom_m / 1000.0 for layer in self.layers.layers()
                if layer.on and layer.in_zoom(zoom_m) and layer.geometry == "area"}

    @staticmethod
    def big_enough(layer, record: dict, zoom_m: float) -> bool:
        """The size rule: an area at least its layer's minimum size across, as a share of
        the zoom distance (DP80). Lines and points, and records with no width, pass."""
        width = record.get("width_km")
        if layer is None or layer.geometry != "area" or width is None:
            return True
        return width * 1000.0 >= layer.min_size * zoom_m

    def passes(self, record: dict, zoom_m: float) -> bool:
        """The first three tests: its layer is on, in its zoom range, and big enough."""
        layer = self.layers.get(record["layer"])
        if layer is not None and not (layer.on and layer.in_zoom(zoom_m)):
            return False
        return self.big_enough(layer, record, zoom_m)

    def _table(self, p: int):
        """The pack's features: numbers, boxes, widths and layers, read once with the store's boxes."""
        index = self.store._indexes[p]
        numbers, boxes = index.boxes
        widths, layer_of = index.sizes
        return numbers, boxes, widths, layer_of

    def _layer_codes(self, p: int):
        """Each feature's layer as a number, and the layer ids in that order, worked out once a pack: comparing
        the layer id of every feature as text, for each layer, took about 100 ms a frame on the world pack."""
        codes = getattr(self, "_codes", None)
        if codes is None:
            codes = self._codes = {}
        layer_of = self._table(p)[3]
        got = codes.get(p)
        if got is None or got[0] is not layer_of:
            # A dictionary, not np.unique: sorting the text of every layer id took about 0.7 s.
            seen: dict = {}
            inverse = np.fromiter((seen.setdefault(i, len(seen)) for i in layer_of), np.intp, len(layer_of))
            got = codes[p] = (layer_of, [str(i) for i in seen], inverse)
        return got[1], got[2]

    def _by_layer(self, p: int) -> list:
        """For each layer, in the order of _layer_codes, its rows of the feature table in order
        of each box's south edge, with their south and north edges in that order; worked out
        once a pack. A view then takes the features of the layers shown, in its band of
        latitude, without testing every row of the table: that cost about 12 ms a frame."""
        layers = getattr(self, "_layer_rows", None)
        if layers is None:
            layers = self._layer_rows = {}
        boxes = self._table(p)[1]
        got = layers.get(p)
        if got is None or got[0] is not boxes:
            ids, code = self._layer_codes(p)
            order = np.argsort(boxes[:, 1], kind="stable").astype(np.intp)
            by_code = code[order]
            # The edges are kept in single precision, rounded outward, to save about 10 MB on the
            # world pack: they only choose the rows box_reach then tests exactly.
            def outward(values, way):
                return np.nextafter(values.astype(np.float32), np.float32(way))

            per_layer = []
            for k in range(len(ids)):
                rows = np.ascontiguousarray(order[by_code == k])
                west = boxes[rows, 0]
                per_layer.append((rows, outward(boxes[rows, 1], -np.inf), outward(boxes[rows, 3], np.inf),
                                  outward(west, -np.inf), outward(west + _spans(west, boxes[rows, 2]), np.inf)))
            got = layers[p] = (boxes, per_layer)
        return got[1]

    def _candidates(self, p: int, zoom_m: float, lat: float | None = None, reach: float = 180.0,
                    lon: float | None = None, rho: float = math.pi) -> np.ndarray:
        """The rows of the pack's feature table that pass the first three tests and, when lat
        is given, whose box reaches within `reach` degrees of latitude of it and, when lon is
        given too, shares a longitude with the cap of angular radius rho round the point."""
        numbers, boxes, widths, layer_of = self._table(p)
        ids, _code = self._layer_codes(p)
        cut = None
        if lat is not None and lon is not None:
            cut = _cap_boxes(lat, lon, min(math.pi, rho))
            if len(cut) == 1 and cut[0][0] <= -180.0 and cut[0][2] >= 180.0:
                cut = None    # every longitude
        found = []
        for k, (rows, south, north, west, east) in enumerate(self._by_layer(p)):
            layer = self.layers.get(ids[k])
            if layer is not None and not (layer.on and layer.in_zoom(zoom_m)):
                continue
            if lat is not None:
                end = int(np.searchsorted(south, lat + reach + SLACK, side="right"))
                keep = np.nonzero(north[:end] >= lat - reach - SLACK)[0]
                if cut is not None:
                    keep = keep[_meets_longitudes(west[keep], east[keep], cut)]
                rows = rows[keep]
            if layer is not None and layer.geometry == "area":
                rows = rows[widths[rows] * 1000.0 >= layer.min_size * zoom_m]
            found.append(rows)
        return np.concatenate(found) if found else np.zeros(0, np.intp)

    # The view -----------------------------------------------------------------------

    def features(self, lat: float, lon: float, zoom_m: float) -> frozenset:
        """The ids of every visible feature with the location and zoom given."""
        out: set = set()
        for p, rows, by_shape in self._visible(lat, lon, zoom_m):
            out.update(self.store._indexes[p].ids[rows].tolist())
            out.update(self.store._area(p, n).id for n in by_shape)
        return frozenset(out)

    def numbers(self, lat: float, lon: float, zoom_m: float) -> set:
        """Every visible feature as (pack, feature number)."""
        out: set = set()
        for p, rows, by_shape in self._visible(lat, lon, zoom_m):
            out.update((p, n) for n in self._table(p)[0][rows].tolist())
            out.update((p, n) for n in by_shape)
        return out

    def _visible(self, lat: float, lon: float, zoom_m: float) -> list:
        """For each pack, the rows of its feature table decided visible by their boxes, and the
        feature numbers decided visible by their shapes."""
        lon = geodesy.wrap_lon(lon)
        rho = zoom_m / geodesy.R_MEAN_M
        out = []
        for p in self.store._covering(lat, lon)[:1]:
            numbers, boxes, _w, _l = self._table(p)
            # The difference in latitude alone is never more than the distance.
            rows = self._candidates(p, zoom_m, lat, math.degrees(rho), lon, rho * MARGIN)
            if not len(rows):
                continue
            near, far = box_reach(boxes[rows], lat, lon)
            across = (near <= rho) & (far > rho)
            # A box across the edge of the view that is no deeper than the drawing's own
            # tolerance is in: looking at its shapes could not be more exact than the map.
            shallow = across & (far - near <= self._tolerance(p, zoom_m))
            edge = numbers[rows[across & ~shallow]]
            by_shape = self._by_shape(p, set(edge.tolist()), lat, lon, rho, zoom_m) if len(edge) else set()
            out.append((p, rows[(far <= rho) | shallow], by_shape))
        return out

    def _tolerance(self, p: int, zoom_m: float) -> float:
        """How far, as an angle in radians, the drawing level for this zoom may put an edge
        from its exact place; 0 where the map is drawn from the exact pack tiles."""
        from mapcore.render.scene import drawing_source

        kind, d = drawing_source(self.store._indexes[p], zoom_m / 1000.0)
        if kind != "draw":
            return 0.0
        return float(d.get("tolerance_m", 0.0)) / geodesy.R_MEAN_M

    def _by_shape(self, p: int, undecided: set, lat: float, lon: float, rho: float, zoom_m: float) -> set:
        """Which of the undecided features have part of a shape within rho of the point.

        The tiles are the map's own at this zoom (P1-T9), so they are usually read
        already. A feature that drawing level leaves out as small is looked for in
        the coarsest drawing level that holds it, or the exact pack tiles."""
        from mapcore.render.scene import drawing_source, holds

        index = self.store._indexes[p]
        kind, d = drawing_source(index, zoom_m / 1000.0)
        tile_plan = [("tile", level, level) for level in index.pack.tile_levels]
        if kind != "draw":
            return self._look(p, tile_plan, undecided, lat, lon, rho)
        tolerance = float(d.get("tolerance_m", 0.0)) / geodesy.R_MEAN_M
        found = self._look(p, [("draw", d["id"], d["tile_level"])], undecided, lat, lon, rho, tolerance)
        levels = sorted(index.pack.drawing_levels.values(), key=lambda level: -level.get("view_km", 0))
        by_plan: dict = {}
        for n in undecided - found:
            area = self.store._area(p, n)
            if area is None:
                continue
            size = area.area_km2
            layer = self.layers.get(area.layer)
            # A drawing level keeps every line and place of the layers it holds, and an area's largest part.
            whole = layer is not None and layer.geometry != "area"
            if holds(d, area.layer) and (whole or size >= d.get("min_km2", 0.0)):
                continue   # it is in this drawing level, so it was looked for
            holder = next((level for level in levels if holds(level, area.layer)
                           and (whole or level.get("min_km2", 0.0) <= size)), None)
            key = ("tile", None, None) if holder is None else ("draw", holder["id"], holder["tile_level"])
            by_plan.setdefault(key, set()).add(n)
        for key, small in by_plan.items():
            found |= self._look(p, tile_plan if key[0] == "tile" else [key], small, lat, lon, rho, tolerance)
        return found

    def _look(self, p: int, plan, undecided: set, lat: float, lon: float, rho: float,
              tolerance: float = 0.0) -> set:
        """Which of the undecided features reach within rho of the point, in the tiles of the plan.
        A shape across the edge of the view no deeper than the tolerance, an angle, counts as in."""
        import shapely

        index = self.store._indexes[p]
        cut = _cap_boxes(lat, lon, min(math.pi, rho * MARGIN))
        spots = []
        for kind, ident, level in plan:
            for c, (west, south, east, north) in enumerate(cut):
                x0, y0 = tiles.tile_of(west, south, level)
                x1, y1 = tiles.tile_of(east, north, level)
                spots.extend((kind, ident, level, x, y, c) for x, y in index.tiles_in(kind, ident, x0, x1, y0, y1))
        if not spots:
            return set()
        boxes = np.array([tiles.tile_box(s[2], s[3], s[4]) for s in spots], np.float64)
        near, far = box_reach(boxes, lat, lon)
        found: set = set()
        shapes, owners, is_area, cut_of = [], [], [], []
        for (kind, ident, level, x, y, c), box, t_near, t_far in zip(spots, boxes, near.tolist(), far.tolist()):
            if t_near > rho:
                continue
            data = self.store._tile(p, kind, ident, x, y)
            # Whichever is fewer is gone through: a tile may hold thousands of roads.
            if len(undecided) < len(data.by_feature):
                here = [n for n in undecided if n in data.by_feature and n not in found]
            else:
                here = [n for n in data.by_feature if n in undecided and n not in found]
            if not here:
                continue
            if t_far <= rho:
                found.update(here)        # the whole tile is in view
                continue
            wanted = [i for n in here for i in data.by_feature[n]]
            geoms = data.shapes_of(wanted, tuple(box))
            for n in here:
                for i in data.by_feature[n]:
                    shapes.append(geoms[i])
                    owners.append(n)
                    is_area.append(data.entries[i].kind in tiles.AREA_KINDS)
                    cut_of.append(c)
        if not shapes:
            return found
        shapes = np.array(shapes, dtype=object)
        owners = np.array(owners, dtype=np.intp)
        is_area = np.array(is_area, dtype=bool)
        cut_of = np.array(cut_of, dtype=np.intp)
        open_ = ~np.isin(owners, np.fromiter(found, np.intp, len(found)))
        # Each shape's own box first, as for the features' boxes: wholly in view, or across its
        # edge but no deeper than the drawing's tolerance, it is in; wholly outside, that shape is.
        bounds = shapely.bounds(shapes)
        known = open_ & ~np.isnan(bounds).any(axis=1)
        s_near, s_far = np.zeros(len(shapes)), np.full(len(shapes), np.inf)   # a shape with no box is undecided
        if known.any():
            s_near[known], s_far[known] = box_reach(bounds[known], lat, lon)
        shown = known & ((s_far <= rho) | ((s_near <= rho) & (s_far - s_near <= tolerance)))
        found.update(owners[shown].tolist())
        open_ &= ~np.isin(owners, owners[shown]) & ~(known & (s_near > rho))
        # A shape with a point within the view is in: this settles most roads, railways and
        # rivers across its edge without cutting and projecting them.
        rows = np.nonzero(open_)[0]
        if len(rows):
            xy, which = shapely.get_coordinates(shapes[rows], return_index=True)
            if len(xy):
                hit = rows[np.unique(which[_within(lat, lon, xy[:, 1], xy[:, 0], rho)])]
                found.update(owners[hit].tolist())
                open_ &= ~np.isin(owners, owners[hit])
        # The location inside an area.
        inside = open_ & is_area & shapely.intersects_xy(shapes, lon, lat)
        found.update(owners[inside].tolist())
        open_ &= ~np.isin(owners, owners[inside])
        # Any part within rho, each shape cut to round the view first.
        reach = np.zeros(len(shapes), bool)
        for c, box in enumerate(cut):
            rows = np.nonzero(open_ & (cut_of == c))[0]
            if not len(rows):
                continue
            parts = shapely.clip_by_rect(shapes[rows], *box)
            if rho >= HALF_PI:
                # A view this wide holds a vertex of any shape it meets.
                xy, which = shapely.get_coordinates(parts, return_index=True)
                if len(xy):
                    close = _angles(lat, lon, xy[:, 1], xy[:, 0]) <= rho
                    reach[rows[np.unique(which[close])]] = True
                continue
            projected = shapely.transform(parts, _Azimuthal(lat, lon))
            polygonal = np.isin(shapely.get_type_id(projected), (3, 6))
            edges = np.where(polygonal, shapely.boundary(projected), projected)
            gap = shapely.distance(shapely.Point(0.0, 0.0), edges)
            reach[rows] = np.nan_to_num(gap, nan=np.inf) <= rho
        found.update(owners[reach].tolist())
        return found
