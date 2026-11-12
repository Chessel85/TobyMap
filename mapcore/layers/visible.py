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


def _angles(lat1: float, lon1: float, lat2, lon2) -> np.ndarray:
    """The angle at the centre of the Earth between a point and arrays of points, in radians."""
    p1, p2 = math.radians(lat1), np.radians(lat2)
    half_dp = (p2 - p1) / 2
    half_dl = np.radians((np.asarray(lon2, dtype=np.float64) - lon1) % 360.0) / 2
    h = np.sin(half_dp) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(half_dl) ** 2
    return 2 * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


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
    span = (east - west) % 360.0
    span = np.where((span == 0.0) & (east != west), 360.0, span)
    span = np.where((west <= -180.0) & (east >= 180.0), 360.0, span)

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
            ids, inverse = np.unique(np.asarray(layer_of), return_inverse=True)
            got = codes[p] = (layer_of, [str(i) for i in ids.tolist()], inverse.astype(np.intp).ravel())
        return got[1], got[2]

    def _candidates(self, p: int, zoom_m: float) -> np.ndarray:
        """The rows of the pack's feature table that pass the first three tests."""
        numbers, boxes, widths, layer_of = self._table(p)
        ids, code = self._layer_codes(p)
        shown = np.zeros(len(ids), bool)
        least = np.zeros(len(ids), float)   # the least width in metres, for an area layer
        for k, layer_id in enumerate(ids):
            layer = self.layers.get(layer_id)
            if layer is None:
                shown[k] = True
                continue
            if not (layer.on and layer.in_zoom(zoom_m)):
                continue
            shown[k] = True
            if layer.geometry == "area":
                least[k] = layer.min_size * zoom_m
        keep = shown[code] & (widths * 1000.0 >= least[code])
        return np.nonzero(keep)[0]

    # The view -----------------------------------------------------------------------

    def features(self, lat: float, lon: float, zoom_m: float) -> frozenset:
        """The ids of every visible feature with the location and zoom given."""
        return frozenset(self.store._area(p, n).id for p, n in self.numbers(lat, lon, zoom_m))

    def numbers(self, lat: float, lon: float, zoom_m: float) -> set:
        """Every visible feature as (pack, feature number)."""
        lon = geodesy.wrap_lon(lon)
        rho = zoom_m / geodesy.R_MEAN_M
        out: set = set()
        for p in self.store._covering(lat, lon)[:1]:
            numbers, boxes, _w, _l = self._table(p)
            rows = self._candidates(p, zoom_m)
            # The difference in latitude alone is never more than the distance.
            reach = math.degrees(rho)
            rows = rows[(boxes[rows, 1] - lat <= reach) & (lat - boxes[rows, 3] <= reach)]
            if not len(rows):
                continue
            near, far = box_reach(boxes[rows], lat, lon)
            out.update((p, int(n)) for n in numbers[rows[far <= rho]].tolist())
            edge = numbers[rows[(near <= rho) & (far > rho)]]
            if len(edge):
                out.update((p, n) for n in self._by_shape(p, set(edge.tolist()), lat, lon, rho, zoom_m))
        return out

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
        found = self._look(p, [("draw", d["id"], d["tile_level"])], undecided, lat, lon, rho)
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
            found |= self._look(p, tile_plan if key[0] == "tile" else [key], small, lat, lon, rho)
        return found

    def _look(self, p: int, plan, undecided: set, lat: float, lon: float, rho: float) -> set:
        """Which of the undecided features reach within rho of the point, in the tiles of the plan."""
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
            here = [n for n in data.by_feature if n in undecided and n not in found]
            if not here:
                continue
            if t_far <= rho:
                found.update(here)        # the whole tile is in view
                continue
            geoms, _numbers = data.drawing_shapes(tuple(box))
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
