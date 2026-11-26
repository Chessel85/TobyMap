"""Stage "relationships": what each feature is inside, beside, overlapping and crossing (P3-T3, AD-8).

The application only looks these up (AD-8); they are worked out here, once, for every feature:

* Containment (P3-T3a, NAV-4): the areas that hold a feature fully, from every layer, so the parents
  of parents are there too; and, for a line or a place, the areas it is partly inside, with the
  share. Two areas that are the same land, each inside the other to within same_share, are "same
  as", not parent and child (DP71); so are two with the same name, each inside the other to within
  same_name_share, such as an island and a county (P3-T23, DP198). A land area's share inside another land area
  is measured on its land only (P3-T28n): Exmoor, whose outline runs a little into the sea beyond England's coast,
  is wholly inside England. So is a road's or railway's share inside a land area, on its length on land: Belfast's
  M3, which crosses the Lagan on a bridge over the sea, is wholly inside Northern Ireland. Water areas, rivers
  (whose estuaries truly lie in the sea) and places are measured on their whole shape.
* Neighbours and overlaps (P3-T3b, INF-2, INF-5): areas of one layer that share a border, with its
  length on the ellipsoid; areas of one layer that nearly touch, within near_km, with the distance;
  and areas of any layers that overlap, neither holding the other, with the share of each covered.
* Crossings (P3-T3c, INF-6): for each line, the areas it passes through in order from its start
  (for a river, its source, as OSM draws rivers the way they flow); for each area, the lines that
  cross it, and those along its border, within border_m.
* The water hierarchy (P3-T3d, DAT-4, LOC-6): for each area of a water layer, the area of a water
  layer of lower rank that holds the most of it, at least water_share: the Bay of Biscay's is the
  North Atlantic Ocean. Lakes are within the land areas round them by containment.
* Counts (P3-T3e): for each area, how many features of each layer are inside it, fully or partly.

How it is done: never a whole layer at once, which was spike S2's lesson. The world is cut into
boxes, each split in four while its parts hold more than leaf_points points, down to min_leaf_deg.
A shape that covers a box whole is noted as covering it and not cut further, as the pack tiles do.
In each box, only the parts there are compared, through a spatial index: the areas they share, the
borders they share, the length of each line inside each area, and the places inside each area.
These are summed over the boxes. A line's distance from its start rides along as its third
coordinate, which cutting keeps, so the order of the areas it passes through is its first distance
in each. The top boxes are jobs for the worker processes.

The results are kept in relationships.json in the stage's folder, by the index of each feature in
features.json, which this stage keeps unchanged; the writing stage puts them in the pack by id.

Settings: land_least (0.01), the least share of a land area, or of a line of the land_lines layers (roads and
railways), on land for it to be measured on land, so a line nearly all over the sea is measured whole; same_share (0.99), same_name_share (0.9), full_share (0.995), partly_share (0.005), cross_km (0.05), near_km (5), near_share
(0.25) and near_most (10), for nearly touching, border_m (100),
water_share (0.5), leaf_points (20000), min_leaf_deg (0.25), top_deg (45), along_lines and along_areas (the
layers looked at for a line along a border: rivers, against countries, regions and counties), and leave_out, the
layers with no relationships (the graticule and the special lines).

light_layers (P4-T1k, empty by default): street-scale layers whose features get only the areas they are in or partly
in and, for a line, the areas of the crossing_areas layers it passes through, in order. They get no neighbours,
nothing nearly touching, no overlaps and no outline; they hold nothing; no area lists or counts them; and two of them
are never compared, so Great Britain's streets, paths and fields do not each meet every other.
"""
from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.stages.geodesy import areas_km2

R_KM = 6371.0088
SETTINGS = {"coast_land": ["countries", "regions", "counties", "islands"], "shore_lakes": ["lakes"],
            "sea": [], "land": [], "land_least": 0.01, "land_lines": ("roads", "railways"),
            "crossing_areas": ["countries", "regions", "counties"],
            "shore_land": ["countries", "regions", "counties"], "water": [],
            "same_name_share": 0.9, "same_share": 0.99, "full_share": 0.995, "partly_share": 0.005, "cross_km": 0.05, "near_km": 5.0, "near_share": 0.25, "near_most": 10, "border_m": 100.0,
            "water_share": 0.5, "leaf_points": 20000, "min_leaf_deg": 0.25, "top_deg": 45.0,
            "along_lines": ("rivers",), "along_areas": ("countries", "regions", "counties"), "light_layers": []}
AREA, LINE, POINT = "area", "line", "point"
# Layers with no relationships: the graticule's lines would each cross hundreds of areas, and say nothing new.
LEAVE_OUT = ("graticule", "special-lines")


# Measuring ---------------------------------------------------------------------------------------------

def lengths_km(geoms) -> np.ndarray:
    """Each line's length over the Earth, in km, by the great circle between its points (within about 0.3% of
    the ellipsoid, well inside INF-2's 2%)."""
    geoms = np.asarray(geoms, dtype=object)
    out = np.zeros(len(geoms))
    if len(geoms) == 0:
        return out
    parts, which = shapely.get_parts(geoms, return_index=True)
    lines = []
    for p in parts:   # a polygon's boundary, a point nothing
        t = shapely.get_type_id(p)
        lines.append(p if t in (1, 2) else shapely.boundary(p) if t == 3 else shapely.LineString())
    sub, sub_which = shapely.get_parts(np.array(lines, dtype=object), return_index=True)
    coords, idx = shapely.get_coordinates(sub, return_index=True)
    if len(coords) < 2:
        return out
    same = idx[1:] == idx[:-1]
    lon, lat = np.radians(coords[:, 0]), np.radians(coords[:, 1])
    dlat, dlon = lat[1:] - lat[:-1], lon[1:] - lon[:-1]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[1:]) * np.cos(lat[:-1]) * np.sin(dlon / 2) ** 2
    seg = 2 * R_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1))) * same
    per_sub = np.bincount(idx[:-1], weights=seg, minlength=len(sub))
    per_part = np.bincount(sub_which, weights=per_sub, minlength=len(parts))
    np.add.at(out, which, per_part)
    return out


CHAIN_KM = 50.0      # a part of a line starting this near another part goes on from it (P3-T19j)
KM_PER_DEG = 111.32  # rough: only to compare a gap with CHAIN_KM
CHAIN_MOST = 500     # with more parts than this, a line is measured along its longest part only


def _along_km(c: np.ndarray) -> np.ndarray:
    """Each point's distance in km from the first, over the great circle between points."""
    lon, lat = np.radians(c[:, 0]), np.radians(c[:, 1])
    a = np.sin((lat[1:] - lat[:-1]) / 2) ** 2 + np.cos(lat[1:]) * np.cos(lat[:-1]) * np.sin((lon[1:] - lon[:-1]) / 2) ** 2
    return np.concatenate([[0.0], np.cumsum(2 * R_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1))))])


def with_distance(line, chain_km: float = CHAIN_KM):
    """A line with each point's distance from the line's start, in km, as its third coordinate.

    A river in several parts is measured by chaining them (P3-T19j, the Rhine's countries out of order): a part
    whose start is within chain_km of another part goes on from the nearest point of that part, plus the gap, as
    a delta branch leaves the main river and the river below a lake goes on from the river above it. A part whose
    start is near no other part is a source, at 0. The parts' own order does not matter. A part the chain does
    not reach, or a line of very many parts, is measured along the longest part, from that part's start, as
    before: each point's distance is where it falls on that part."""
    parts = [p for p in shapely.get_parts(line) if shapely.get_num_coordinates(p) >= 2]
    if not parts:
        return shapely.MultiLineString()
    km = lengths_km(np.array(parts, dtype=object))
    main = parts[int(np.argmax(km))]
    main_deg = max(shapely.length(main), 1e-12)
    coords = [shapely.get_coordinates(p) for p in parts]
    offset = [math.inf] * len(parts)
    if 1 < len(parts) <= CHAIN_MOST:
        links: list[list[tuple[int, float]]] = [[] for _ in parts]   # for each part: (part it goes on from, km)
        for b, c in enumerate(coords):
            start = shapely.Point(c[0])
            for a, pa in enumerate(parts):
                if a == b:
                    continue
                gap_deg = shapely.distance(pa, start)
                gap_km = gap_deg * KM_PER_DEG
                if gap_km <= chain_km:
                    pos = shapely.line_locate_point(pa, start) / max(shapely.length(pa), 1e-12) * float(km[a])
                    links[b].append((a, pos + gap_km))
        for b in range(len(parts)):
            if not links[b]:
                offset[b] = 0.0
        if not any(o == 0.0 for o in offset):   # every start near another part: the one farthest from the rest
            far = max(range(len(parts)), key=lambda b: min(add for _a, add in links[b]))
            offset[far], links[far] = 0.0, []
        for _ in range(len(parts)):   # the shortest way from a source to each part's start
            changed = False
            for b in range(len(parts)):
                for a, add in links[b]:
                    if offset[a] + add < offset[b] - 1e-9:
                        offset[b], changed = offset[a] + add, True
            if not changed:
                break
    elif len(parts) == 1:
        offset[0] = 0.0
    out = []
    for p, c, off in zip(parts, coords, offset):
        if math.isfinite(off):
            at = off + _along_km(c)
        else:
            at = shapely.line_locate_point(main, shapely.points(c)) / main_deg * float(km.max())
        out.append(shapely.LineString(np.column_stack([c, at])))
    return shapely.MultiLineString(out)


def retraced(geoms, chunk: int = 200_000) -> np.ndarray:
    """Which lines may go back over themselves: a part that turns straight back at a point, such as a small
    roundabout, a closed way, simplified to two points and back (A, B, A), or that has one stretch twice. Cutting
    such a line with an area keeps the stretch once, while its own length counts it twice, so a roundabout wholly
    in a county was half inside it (item 4b). Only a first test: once_over says whether a stretch is truly twice."""
    geoms = np.asarray(geoms, dtype=object)
    out = np.zeros(len(geoms), dtype=bool)
    for at in range(0, len(geoms), chunk):
        parts, which = shapely.get_parts(geoms[at:at + chunk], return_index=True)
        coords, idx = shapely.get_coordinates(parts, return_index=True)
        if len(coords) < 3:
            continue
        line = which[idx]
        same = idx[1:] == idx[:-1]
        v = coords[1:] - coords[:-1]
        # A turn straight back: two stretches in a row, one part, pointing opposite ways along one line.
        v1, v2 = v[:-1], v[1:]
        both = same[:-1] & same[1:]
        cross = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0]
        dot = (v1 * v2).sum(axis=1)
        size = np.hypot(v1[:, 0], v1[:, 1]) * np.hypot(v2[:, 0], v2[:, 1])
        back = both & (dot < 0) & (np.abs(cross) <= 1e-9 * size)
        out[at + line[:-2][back]] = True
        # The same stretch twice, anywhere in the line.
        seg = np.column_stack([coords[:-1], coords[1:]])[same]
        seg_line = line[:-1][same]
        flip = (seg[:, 0] > seg[:, 2]) | ((seg[:, 0] == seg[:, 2]) & (seg[:, 1] > seg[:, 3]))
        seg[flip] = seg[flip][:, [2, 3, 0, 1]]
        keep = (seg[:, 0] != seg[:, 2]) | (seg[:, 1] != seg[:, 3])
        rows = np.column_stack([seg_line[keep].astype(float), seg[keep]])
        if len(rows):
            _u, first, counts = np.unique(rows, axis=0, return_index=True, return_counts=True)
            out[at + rows[first[counts > 1], 0].astype(np.intp)] = True
    return out


def once_over(line):
    """A line with each stretch it goes over twice kept once, its parts joined where they meet end to end; the
    line itself if it has no stretch twice."""
    merged = shapely.line_merge(shapely.union_all(shapely.get_parts(line)))
    if shapely.length(merged) < shapely.length(line) * (1 - 1e-9):
        return merged
    return line


def first_distance(geoms) -> np.ndarray:
    """The least third coordinate of each shape, or infinity for an empty one."""
    out = np.full(len(geoms), np.inf)
    coords, idx = shapely.get_coordinates(np.asarray(geoms, dtype=object), include_z=True, return_index=True)
    if len(coords):
        z = np.where(np.isnan(coords[:, 2]), np.inf, coords[:, 2])
        np.minimum.at(out, idx, z)
    return out


# Cutting into boxes ------------------------------------------------------------------------------------

COVER = "cover"   # in place of a shape: the area covers the whole box

GRID_DEG = 1e-9   # the grid a pair is snapped to when GEOS cannot compare it as it is, well under a millimetre
REPAIRED = [0]    # how many pairs needed repairing, for the log


def robust(op, a, b):
    """op (shapely.intersection or shapely.difference) of two arrays of shapes, pair by pair. Cutting a shape to
    a box (clip_by_rect) can leave it slightly invalid along the box's edge, and GEOS then refuses the pair with
    a TopologyException, such as "Ring edge missing" on the world pack (P3-T3). Such a pair is done again with
    both shapes made valid, and failing that on a fine grid, so one bad pair does not stop the build."""
    try:
        return op(a, b)
    except shapely.errors.GEOSException:
        pass
    a = np.broadcast_to(np.asarray(a, dtype=object), np.broadcast_shapes(np.shape(a), np.shape(b)))
    b = np.broadcast_to(np.asarray(b, dtype=object), a.shape)
    out = np.empty(a.shape, dtype=object)
    for k, (x, y) in enumerate(zip(a.ravel(), b.ravel())):
        try:
            out.flat[k] = op(x, y)
            continue
        except shapely.errors.GEOSException:
            REPAIRED[0] += 1
        try:
            out.flat[k] = op(shapely.make_valid(x), shapely.make_valid(y))
        except shapely.errors.GEOSException:
            out.flat[k] = op(shapely.make_valid(x), shapely.make_valid(y), grid_size=GRID_DEG)
    return out


def cut(item, box) -> tuple | None:
    """An item (index, kind, shape or COVER) cut to a box (west, south, east, north), or None if nothing is in it.
    A place's points are in one box only: west and south edges in, east and north out, but for the world's edge."""
    i, kind, g = item
    if g is COVER:
        return item
    w, s, e, n = box
    if kind == POINT:
        c = shapely.get_coordinates(g)
        keep = (c[:, 0] >= w) & ((c[:, 0] < e) | (e >= 180)) & (c[:, 1] >= s) & ((c[:, 1] < n) | (n >= 90))
        return (i, kind, shapely.MultiPoint(c[keep])) if keep.any() else None
    gx0, gy0, gx1, gy1 = shapely.bounds(g)
    if gx0 >= w and gy0 >= s and gx1 <= e and gy1 <= n:
        return item
    if gx1 < w or gx0 > e or gy1 < s or gy0 > n:
        return None
    if kind == AREA:
        piece = shapely.clip_by_rect(g, w, s, e, n)
        if piece.is_empty or shapely.area(piece) <= 0:
            return None
        if shapely.area(piece) >= (e - w) * (n - s) * (1 - 1e-9):
            return (i, kind, COVER)
        return (i, kind, piece)
    piece = shapely.clip_by_rect(g, w, s, e, n)
    if piece.is_empty or shapely.length(piece) <= 0:
        return None
    return (i, kind, piece)


def points_of(items) -> int:
    return sum(int(shapely.get_num_coordinates(g)) for _i, _k, g in items if g is not COVER)


class Sums:
    """What the boxes add up: each feature's own measure, and each pair's."""

    def __init__(self):
        self.own = defaultdict(float)       # area km2, line km or number of points
        self.shared = defaultdict(float)    # (area, area): km2 of land in both
        self.border = defaultdict(float)    # (area, area) of one layer: km of shared border
        self.inside = defaultdict(float)    # (line or place, area): km or points inside
        self.first = {}                     # (line, area): the least distance from the line's start inside
        self.along = defaultdict(float)     # (line, area): km of the line within border_m of the area's border
        self.shore = defaultdict(float)     # (lake, land area): km of the lake's shore inside the land (P3-T24e)
        self.crossed_at = defaultdict(list)  # (line, area): [lon, lat] where the line crosses its border (P3-T24f)
        self.sea = defaultdict(float)       # land area: km2 of it in the sea (P3-T28n)
        self.sea_shared = defaultdict(float)  # (land area, land area): km2 of the land in both that is in the sea
        self.sea_inside = defaultdict(float)  # (road or railway, land area): km of it in the land area and the sea
        # Stretches of an area's own outline lying on a cutting line, which no box sees both sides of:
        # (orientation "v" or "h", the line's longitude or latitude, from, to, feature, side 0 west or south, 1 east
        # or north). Matched across features afterwards (edge_borders).
        self.edges: list[tuple] = []

    def add(self, other: "Sums") -> None:
        for name in ("own", "shared", "border", "inside", "along", "shore", "sea", "sea_shared", "sea_inside"):
            mine = getattr(self, name)
            for k, v in getattr(other, name).items():
                mine[k] += v
        for k, v in other.first.items():
            self.first[k] = min(v, self.first.get(k, math.inf))
        for k, v in other.crossed_at.items():
            self.crossed_at[k].extend(v)
        self.edges.extend(other.edges)

    def plain(self) -> dict:
        def pairs(d):
            return [[int(a), int(b), float(v)] for (a, b), v in d.items()]
        return {"own": [[int(k), float(v)] for k, v in self.own.items()], "shared": pairs(self.shared),
                "sea": [[int(k), float(v)] for k, v in self.sea.items()], "sea_shared": pairs(self.sea_shared),
                "sea_inside": pairs(self.sea_inside),
                "border": pairs(self.border), "inside": pairs(self.inside), "first": pairs(self.first),
                "along": pairs(self.along), "shore": pairs(self.shore), "edges": [list(e) for e in self.edges],
                "crossed_at": [[int(a), int(b), v] for (a, b), v in self.crossed_at.items()]}

    @classmethod
    def from_plain(cls, d: dict) -> "Sums":
        s = cls()
        for k, v in d["own"]:
            s.own[k] = v
        for k, v in d.get("sea", []):
            s.sea[k] = v
        for name in ("shared", "border", "inside", "first", "along", "shore", "sea_shared", "sea_inside"):
            target = getattr(s, name)
            for a, b, v in d.get(name, []):
                target[(a, b)] = v
        s.edges = [tuple(e) for e in d.get("edges", [])]
        for a, b, v in d.get("crossed_at", []):
            s.crossed_at[(a, b)] = [list(x) for x in v]
        return s


def bordering(layer_a: str, layer_b: str, settings: dict) -> bool:
    """Whether the shared border of two areas is measured: areas of one layer, which are neighbours (INF-2); and a
    land area of the coast_land layers with a sea of the water layers, which is coast (P3-T24e, DP200)."""
    if layer_a == layer_b:
        return True
    water, land = settings.get("water", ()), settings.get("coast_land", ())
    return (layer_a in water and layer_b in land) or (layer_b in water and layer_a in land)


def leaf(box, items, layer_of: list[str], settings: dict, sums: Sums) -> None:
    """Compare the parts in one box."""
    w, s, e, n = box
    box_shape = shapely.box(w, s, e, n)
    box_km2 = float(areas_km2([box_shape])[0])
    light = set(settings.get("light_layers", ()))

    def lit(i):   # a feature of a light layer (P4-T1k): only the areas it is in, and it holds nothing
        return layer_of[i] in light
    areas = [it for it in items if it[1] == AREA]
    lines = [it for it in items if it[1] == LINE]
    places = [it for it in items if it[1] == POINT]
    # Each area's own land here.
    shapes = [it[2] for it in areas if it[2] is not COVER]
    sized = iter(areas_km2(shapes)) if shapes else iter(())
    own = []
    for it in areas:
        km2 = box_km2 if it[2] is COVER else float(next(sized))
        own.append(km2)
        sums.own[it[0]] += km2
    whole = [k for k, it in enumerate(areas) if it[2] is COVER]
    parts = [k for k, it in enumerate(areas) if it[2] is not COVER]
    land_layers, sea_layers = settings.get("land", ()), settings.get("sea", ())
    in_sea: dict[int, list] = defaultdict(list)   # a land area's parts in the sea here: [(shape, km2)]
    # Land two areas share: a covering area shares all of the other's land here.
    for a in whole:
        for b in range(len(areas)):
            if b != a and areas[b][0] != areas[a][0] and (areas[b][2] is not COVER or a < b):
                if light and lit(areas[a][0]) and lit(areas[b][0]):
                    continue
                key = tuple(sorted((areas[a][0], areas[b][0])))
                sums.shared[key] += own[b]
    if len(parts) > 1:
        arr = np.array([areas[k][2] for k in parts], dtype=object)
        tree = shapely.STRtree(arr)
        left, right = tree.query(arr, predicate="intersects")
        keep = left < right
        if light and len(left):   # two areas of light layers are never compared
            keep &= ~np.array([lit(areas[parts[a]][0]) and lit(areas[parts[b]][0]) for a, b in zip(left, right)],
                              dtype=bool)
        left, right = left[keep], right[keep]
        if len(left):
            inter = robust(shapely.intersection, arr[left], arr[right])
            got = areas_km2(inter)
            for n, (a, b, km2) in enumerate(zip(left, right, got)):
                ia, ib = areas[parts[a]][0], areas[parts[b]][0]
                if km2 > 0 and ia != ib:
                    sums.shared[tuple(sorted((ia, ib)))] += float(km2)
                    # A land area's part in the sea (P3-T28n), kept to measure its share inside another on land.
                    for x, y in ((a, b), (b, a)):
                        if layer_of[areas[parts[x]][0]] in land_layers and layer_of[areas[parts[y]][0]] in sea_layers:
                            in_sea[parts[x]].append((inter[n], float(km2)))
            # Borders shared by two areas of one layer, and coast between land and sea (P3-T24e), but not along
            # the box's own edges.
            same = np.array([bordering(layer_of[areas[parts[a]][0]], layer_of[areas[parts[b]][0]], settings)
                             and not (light and (lit(areas[parts[a]][0]) or lit(areas[parts[b]][0])))
                             for a, b in zip(left, right)], dtype=bool)
            if same.any():
                la, rb = left[same], right[same]
                edge = shapely.boundary(box_shape)
                shared = robust(shapely.intersection, shapely.boundary(arr[la]), shapely.boundary(arr[rb]))
                shared = robust(shapely.difference, shared, shapely.buffer(edge, 1e-9))
                for a, b, km in zip(la, rb, lengths_km(shared)):
                    if km > 0:
                        sums.border[tuple(sorted((areas[parts[a]][0], areas[parts[b]][0])))] += float(km)
    land_sea = {}   # a land area's part in the sea here, by its index here, where it reaches the sea
    if land_layers and sea_layers:
        land_sea = land_in_sea(areas, own, in_sea, layer_of, land_layers, sea_layers, sums, light)
    # A lake's shore inside each land area round it (P3-T24e, DP200): a lake lies on the land, so its outline is
    # inside the countries, regions and counties, not along their borders.
    lakes = [k for k in parts if layer_of[areas[k][0]] in settings.get("shore_lakes", ())]
    land = [k for k, it in enumerate(areas) if layer_of[it[0]] in settings.get("shore_land", ())]
    if lakes and land:
        edge = shapely.buffer(shapely.boundary(box_shape), 1e-9)
        shores = robust(shapely.difference, shapely.boundary(np.array([areas[k][2] for k in lakes], dtype=object)),
                        np.array([edge] * len(lakes), dtype=object))
        shore_km = lengths_km(shores)
        land_parts = [k for k in land if areas[k][2] is not COVER]
        for n, k in enumerate(lakes):
            for a in land:
                if areas[a][2] is COVER and shore_km[n] > 0:
                    sums.shore[(areas[k][0], areas[a][0])] += float(shore_km[n])
        if land_parts:
            larr = np.array([areas[k][2] for k in land_parts], dtype=object)
            tree = shapely.STRtree(larr)
            s_idx, l_idx = tree.query(shores, predicate="intersects")
            if len(s_idx):
                inside = robust(shapely.intersection, shores[s_idx], larr[l_idx])
                for s_, l_, km in zip(s_idx, l_idx, lengths_km(inside)):
                    if km > 0:
                        sums.shore[(areas[lakes[s_]][0], areas[land_parts[l_]][0])] += float(km)
    # Lines and places are measured only inside the areas that are not light: a light area holds nothing (P4-T1k).
    if light:
        whole = [a for a in whole if not lit(areas[a][0])]
        parts = [k for k in parts if not lit(areas[k][0])]
    # Lines: their length here, inside each area, and along each area's border.
    if lines:
        larr = np.array([it[2] for it in lines], dtype=object)
        line_km, line_first = lengths_km(larr), first_distance(larr)
        for it, km in zip(lines, line_km):
            sums.own[it[0]] += float(km)
        for li, it in enumerate(lines):
            for a in whole:
                key = (it[0], areas[a][0])
                sums.inside[key] += float(line_km[li])
                sums.first[key] = min(sums.first.get(key, math.inf), float(line_first[li]))
        # Roads and railways over the sea (P3-T28n's rule, for lines): the length of each in a land area and in the
        # sea, so its share inside the land area is measured on land.
        wet = ({li for li, it in enumerate(lines) if layer_of[it[0]] in settings.get("land_lines", ())}
               if land_layers and sea_layers else set())
        sea_covers = any(layer_of[areas[a][0]] in sea_layers for a in whole)
        land_whole = [a for a in whole if layer_of[areas[a][0]] in land_layers]
        if wet and sea_covers:
            for li in wet:
                for a in land_whole:
                    sums.sea_inside[(lines[li][0], areas[a][0])] += float(line_km[li])
        if parts:
            arr = np.array([areas[k][2] for k in parts], dtype=object)
            tree = shapely.STRtree(arr)
            li_idx, ar_idx = tree.query(larr, predicate="intersects")
            if len(li_idx):
                inter = robust(shapely.intersection, larr[li_idx], arr[ar_idx])
                kms, firsts = lengths_km(inter), first_distance(inter)
                for l_, a_, km, d in zip(li_idx, ar_idx, kms, firsts):
                    if km > 0:
                        key = (lines[l_][0], areas[parts[a_]][0])
                        sums.inside[key] += float(km)
                        sums.first[key] = min(sums.first.get(key, math.inf), float(d))
                if wet:
                    lines_in_sea(lines, areas, parts, li_idx, ar_idx, inter, kms, wet, sea_covers, land_whole,
                                 land_sea, layer_of, land_layers, sea_layers, sums)
                # Where each line crosses the border of a country, region or county, but not the box's own edges
                # (P3-T24f, DP201): Crossing says how many times, and the nearest.
                wanted = np.array([layer_of[areas[parts[a_]][0]] in settings.get("crossing_areas", ())
                                   and not (light and lit(lines[l_][0])) for l_, a_ in zip(li_idx, ar_idx)],
                                  dtype=bool)
                if wanted.any():
                    cl, ca = li_idx[wanted], ar_idx[wanted]
                    rim = shapely.buffer(shapely.boundary(box_shape), 1e-9)
                    edges = robust(shapely.difference, shapely.boundary(arr[ca]), np.array([rim] * len(ca), dtype=object))
                    met = robust(shapely.intersection, shapely.force_2d(larr[cl]), edges)
                    for l_, a_, g in zip(cl, ca, met):
                        if g is None or shapely.is_empty(g):
                            continue
                        pts = [q for q in shapely.get_parts(g)]
                        coords = [shapely.get_coordinates(q)[0] for q in pts if shapely.get_num_coordinates(q)]
                        if coords:
                            sums.crossed_at[(lines[l_][0], areas[parts[a_]][0])].extend(
                                [round(float(x), 5), round(float(y), 5)] for x, y in coords)
            # Along a border: within border_m of an area's edge, that is not the box's edge. Only for the lines and
            # areas of the layers named, such as a river forming a border, as buffering every outline is slow.
            tol = settings["border_m"] / 1000 / 111.32
            li_idx, ar_idx = tree.query(larr, predicate="dwithin", distance=tol)
            keep = np.array([layer_of[lines[l_][0]] in settings["along_lines"] and not (light and lit(lines[l_][0]))
                             and layer_of[areas[parts[a_]][0]] in settings["along_areas"]
                             for l_, a_ in zip(li_idx, ar_idx)], dtype=bool)
            li_idx, ar_idx = (li_idx[keep], ar_idx[keep]) if len(li_idx) else (li_idx, ar_idx)
            if len(li_idx):
                edges = robust(shapely.difference, shapely.boundary(arr[ar_idx]),
                                           shapely.buffer(shapely.boundary(box_shape), tol))
                near = robust(shapely.intersection, larr[li_idx], shapely.buffer(edges, tol))
                for l_, a_, km in zip(li_idx, ar_idx, lengths_km(near)):
                    if km > 0:
                        sums.along[(lines[l_][0], areas[parts[a_]][0])] += float(km)
    # Places: how many of each one's points are inside each area.
    if places:
        coords, which = shapely.get_coordinates(np.array([it[2] for it in places], dtype=object), return_index=True)
        per_place = np.bincount(which, minlength=len(places))
        for k, it in enumerate(places):
            count = float(per_place[k])
            sums.own[it[0]] += count
            for a in whole:
                sums.inside[(it[0], areas[a][0])] += count
        if parts and len(coords):
            arr = np.array([areas[k][2] for k in parts], dtype=object)
            tree = shapely.STRtree(arr)
            pts = shapely.points(coords)
            p_idx, a_idx = tree.query(pts, predicate="intersects")
            for p_, a_ in zip(p_idx, a_idx):
                sums.inside[(places[which[p_]][0], areas[parts[a_]][0])] += 1.0


def lines_in_sea(lines, areas, parts, li_idx, ar_idx, inter, kms, wet, sea_covers, land_whole, land_sea, layer_of,
                 land_layers, sea_layers, sums: Sums) -> None:
    """The length of each road or railway here that is both in a land area and in the sea, from its parts in each
    area already cut, so its share inside the land area is measured on land: Belfast's M3, which crosses the Lagan
    on a bridge over the sea, is wholly inside Northern Ireland. Only a line that reaches the sea here costs
    anything more: its parts in the land areas that reach the sea too are cut again by those areas' small parts in
    the sea (land_sea, from land_in_sea), not by the sea's large areas. A land area cut to the coast has next to
    none."""
    in_sea: dict[int, list] = defaultdict(list)    # line here: [(index of the pair, index of a sea area's part)]
    in_land: dict[int, list] = defaultdict(list)   # line here: [(index of the pair, index of a land area's part)]
    for n, (l_, a_) in enumerate(zip(li_idx, ar_idx)):
        if l_ not in wet or kms[n] <= 0:
            continue
        layer = layer_of[areas[parts[a_]][0]]
        if layer in sea_layers:
            in_sea[l_].append((n, a_))
        elif layer in land_layers:
            in_land[l_].append((n, a_))
    if sea_covers:   # the sea covers the box: all of each line here is in the sea
        for l_, pairs_ in in_land.items():
            for n, a_ in pairs_:
                sums.sea_inside[(lines[l_][0], areas[parts[a_]][0])] += float(kms[n])
        return
    cut_line, cut_by, keys = [], [], []
    for l_, seas in in_sea.items():
        sea_km = sum(float(kms[n]) for n, _s in seas)
        for a in land_whole:
            sums.sea_inside[(lines[l_][0], areas[a][0])] += sea_km
        for n, a_ in in_land.get(l_, ()):
            wet_part = land_sea.get(parts[a_])
            if wet_part is not None:
                cut_line.append(inter[n])
                cut_by.append(wet_part)
                keys.append((lines[l_][0], areas[parts[a_]][0]))
    if keys:
        both = robust(shapely.intersection, np.array(cut_line, dtype=object), np.array(cut_by, dtype=object))
        for key, km in zip(keys, lengths_km(both)):
            if km > 0:
                sums.sea_inside[key] += float(km)


SEA_KM2_MIN = 1e-4   # a land area with less sea than this in a box (100 square metres) shares none with another


def _one(shapes):
    """Shapes that do not overlap, as one."""
    if len(shapes) == 1:
        return shapes[0]
    try:
        return shapely.union_all(shapes)
    except shapely.errors.GEOSException:
        REPAIRED[0] += 1
        return shapely.union_all([shapely.make_valid(g) for g in shapes], grid_size=GRID_DEG)


def land_in_sea(areas, own, in_sea, layer_of, land_layers, sea_layers, sums: Sums, light=frozenset()) -> dict:
    """How much of each land area is in the sea here, and how much of each two land areas' shared land is (P3-T28n),
    so a land area's share inside another is measured on its land: Exmoor, whose outline runs a little into the sea
    beyond England's coast, is wholly inside England. The sea is the layer that holds all the water (the oceans),
    whose areas never overlap, so the sea in an area is the sum of its parts in each. Those parts were found when
    the areas here were compared, so only the few land areas that reach into the sea cost anything more. Returns
    each land area's part in the sea here, by its index here, for those cut here that reach it, for the lines."""
    seas = [k for k, it in enumerate(areas) if layer_of[it[0]] in sea_layers]
    land = [k for k, it in enumerate(areas) if layer_of[it[0]] in land_layers]
    if not seas or not land:
        return {}
    sea_covers = any(areas[k][2] is COVER for k in seas)
    sea_km2 = own[next(k for k in seas if areas[k][2] is COVER)] if sea_covers else sum(own[k] for k in seas)
    wet = []   # (index here, its sea here or COVER for the whole sea here, km2)
    for k in land:
        if areas[k][2] is COVER:
            g, km2 = COVER, sea_km2
        elif sea_covers:
            g, km2 = areas[k][2], own[k]
        elif in_sea.get(k):
            g, km2 = _one([p for p, _km2 in in_sea[k]]), sum(km2 for _p, km2 in in_sea[k])
        else:
            continue
        if km2 > 0:
            sums.sea[areas[k][0]] += km2
        if km2 >= SEA_KM2_MIN:
            wet.append((k, g, km2))
    shapes = {k: g for k, g, _km2 in wet if g is not COVER}
    if len(wet) < 2:
        return shapes
    for x in range(len(wet)):   # each two: the sea both are in
        for y in range(x + 1, len(wet)):
            (ka, ga, kma), (kb, gb, kmb) = wet[x], wet[y]
            ia, ib = areas[ka][0], areas[kb][0]
            if ia == ib or (light and layer_of[ia] in light and layer_of[ib] in light):
                continue
            if ga is COVER or gb is COVER:
                km2 = kmb if ga is COVER else kma
            elif not shapely.intersects(ga, gb):
                continue
            else:
                km2 = float(areas_km2(robust(shapely.intersection, [ga], [gb]))[0])
            if km2 > 0:
                sums.sea_shared[tuple(sorted((ia, ib)))] += km2
    return shapes


def on_lines(item, lines, sums: Sums) -> None:
    """Record the stretches of an area's own outline that lie on cutting lines, with the side the area is on."""
    i, kind, g = item
    if kind != AREA or g is COVER:
        return
    x0, y0, x1, y1 = shapely.bounds(g)
    near = [ln for ln in lines if (ln[0] == "v" and x0 <= ln[1] <= x1) or (ln[0] == "h" and y0 <= ln[1] <= y1)]
    if not near:
        return
    edge = shapely.boundary(g)
    for orient, at, lo, hi in near:
        line = shapely.LineString([(at, lo), (at, hi)] if orient == "v" else [(lo, at), (hi, at)])
        got = robust(shapely.intersection, edge, line)
        for part in shapely.get_parts(got):
            if shapely.get_type_id(part) not in (1, 5) or shapely.length(part) <= 0:
                continue
            for seg in shapely.get_parts(shapely.line_merge(part)) if shapely.get_type_id(part) == 5 else [part]:
                c = shapely.get_coordinates(seg)
                k = 1 if orient == "v" else 0
                a, b = float(c[:, k].min()), float(c[:, k].max())
                mid = (a + b) / 2
                eps = 1e-7
                probe = (at + eps, mid) if orient == "v" else (mid, at + eps)
                side = 1 if shapely.intersects(g, shapely.Point(probe)) else 0
                sums.edges.append((orient, at, a, b, i, side))


def edge_borders(edges: list[tuple], layer_of: list[str], settings: dict | None = None) -> dict[tuple, float]:
    """Shared borders along cutting lines: a stretch of one feature's outline on a line, with the feature on one
    side, against another feature of the same layer, or land against sea, on the other side. {(a, b): km}."""
    out: dict[tuple, float] = defaultdict(float)
    groups: dict[tuple, list] = defaultdict(list)
    for orient, at, lo, hi, i, side in edges:
        groups[(orient, round(at, 9))].append((lo, hi, i, side))
    for (orient, at), items in groups.items():
        km_per_deg = math.pi / 180 * R_KM * (1.0 if orient == "v" else math.cos(math.radians(at)))
        west = [x for x in items if x[3] == 0]
        east = [x for x in items if x[3] == 1]
        for lo1, hi1, a, _s in west:
            for lo2, hi2, b, _t in east:
                if a != b and bordering(layer_of[a], layer_of[b], settings or {}):
                    overlap = min(hi1, hi2) - max(lo1, lo2)
                    if overlap > 0:
                        out[tuple(sorted((a, b)))] += overlap * km_per_deg
    return out


def relate(box, items, layer_of, settings, sums: Sums, depth: int = 0) -> None:
    """Split the box in four while its parts hold too many points, then compare the parts in each."""
    w, s, e, n = box
    if not items:
        return
    small = (e - w) <= settings["min_leaf_deg"] or (n - s) <= settings["min_leaf_deg"]
    if small or depth > 30 or points_of(items) <= settings["leaf_points"] or len(items) < 2:
        leaf(box, items, layer_of, settings, sums)
        return
    mx, my = (w + e) / 2, (s + n) / 2
    light = set(settings.get("light_layers", ()))
    for it in items:
        if not light or layer_of[it[0]] not in light:   # a light area has no neighbours (P4-T1k)
            on_lines(it, [("v", mx, s, n), ("h", my, w, e)], sums)
    for sub in ((w, s, mx, my), (mx, s, e, my), (w, my, mx, n), (mx, my, e, n)):
        inside = [c for c in (cut(it, sub) for it in items) if c is not None]
        relate(sub, inside, layer_of, settings, sums, depth + 1)


def _job(job):
    box, blobs, layer_of, settings = job
    items = [(i, k, COVER if b is None else shapely.from_wkb(b)) for i, k, b in blobs]
    sums = Sums()
    REPAIRED[0] = 0
    relate(tuple(box), items, layer_of, settings, sums)
    return dict(sums.plain(), repaired=REPAIRED[0])


def top_boxes(deg: float) -> list[tuple]:
    out = []
    for s in np.arange(-90, 90, deg):
        for w in np.arange(-180, 180, deg):
            out.append((float(w), float(s), float(min(w + deg, 180)), float(min(s + deg, 90))))
    return out


def measure(records, geoms, kinds, settings, executor=None, workers: int = 1, say=print) -> Sums:
    """The sums for every feature, the top boxes run in the workers when there are workers."""
    layer_of = [r["layer"] for r in records]
    # A line that goes back over itself, such as a roundabout simplified to there and back, is measured with each
    # stretch once, so its length and its length inside an area agree (item 4b).
    line_at = [i for i, (g, k) in enumerate(zip(geoms, kinds)) if k == LINE and g is not None and not g.is_empty]
    twice = retraced([geoms[i] for i in line_at]) if line_at else np.zeros(0, dtype=bool)
    fixed = {i: once_over(geoms[i]) for i, t in zip(line_at, twice) if t}
    items = []
    for i, (g, k) in enumerate(zip(geoms, kinds)):
        if g is None or g.is_empty:
            continue
        items.append((i, k, with_distance(fixed.get(i, g)) if k == LINE else g))
    top = total = Sums()
    deg = settings["top_deg"]
    lines = [("v", float(x), -90.0, 90.0) for x in np.arange(-180 + deg, 180, deg)] +             [("h", float(y), -180.0, 180.0) for y in np.arange(-90 + deg, 90, deg)]
    light = set(settings.get("light_layers", ()))
    for it in items:
        if not light or layer_of[it[0]] not in light:
            on_lines(it, lines, top)
    jobs = []
    for box in top_boxes(settings["top_deg"]):
        inside = [c for c in (cut(it, box) for it in items) if c is not None]
        if inside:
            jobs.append((box, [(i, k, None if g is COVER else shapely.to_wkb(g, include_srid=False, output_dimension=3))
                               for i, k, g in inside], layer_of, settings))
    jobs.sort(key=lambda j: -sum(len(b[2]) for b in j[1] if b[2] is not None))
    started = time.perf_counter()
    if executor is None or workers == 1:
        results = (_job(j) for j in jobs)
    else:
        results = executor.map(_job, jobs)
    repaired = 0
    for n, plain in enumerate(results, 1):
        total.add(Sums.from_plain(plain))
        repaired += plain.get("repaired", 0)
        if n % 4 == 0 or n == len(jobs):
            say(f"Compared the features in {n} of {len(jobs)} boxes of {settings['top_deg']:g} degrees, "
                f"{time.perf_counter() - started:.0f} seconds.")
    if repaired:
        say(f"Pairs of shapes the geometry library could not compare as they were, so made valid first: {repaired}.")
    for key, km in edge_borders(total.edges, layer_of, settings).items():
        total.border[key] += km
    return total


# From sums to relationships ---------------------------------------------------------------------------

def nearly_touching(records, geoms, kinds, neighbours: set, settings, own: dict | None = None) -> dict:
    """Areas of one layer that share no border but nearly touch: {(a, b): km}. How near is near depends on the
    smaller area's size: at most near_share of its width (the square root of its area), and never more than
    near_km, so Hampshire is near the Isle of Wight, 1.3 km across the Solent, but two islets 3 km apart are not.
    Each area keeps at most near_most of the nearest. On the Western Europe trial, a flat 5 km gave 1.25 million
    pairs, nearly all islets of archipelagos."""
    near_deg = settings["near_km"] / 111.32
    found: dict[tuple, float] = {}
    by_layer = defaultdict(list)
    light = set(settings.get("light_layers", ()))
    for i, k in enumerate(kinds):
        if k == AREA and geoms[i] is not None and not geoms[i].is_empty and records[i]["layer"] not in light:
            by_layer[records[i]["layer"]].append(i)
    own = own or {}

    def width(i):
        return math.sqrt(max(own.get(i, 0.0), 0.0))

    for layer, idx in by_layer.items():
        if len(idx) < 2:
            continue
        arr = np.array([geoms[i] for i in idx], dtype=object)
        tree = shapely.STRtree(arr)
        left, right = tree.query(arr, predicate="dwithin", distance=near_deg)
        for a, b in zip(left, right):
            ia, ib = idx[a], idx[b]
            if ia >= ib or (ia, ib) in neighbours:
                continue
            limit = min(settings["near_km"], settings["near_share"] * min(width(ia), width(ib)))
            if limit <= 0 or shapely.distance(arr[a], arr[b]) > limit / 111.32 * 2:   # quick, generous in degrees
                continue
            km = float(lengths_km([shapely.shortest_line(arr[a], arr[b])])[0])
            if km <= limit:
                found[(ia, ib)] = round(km, 2)
    # At most near_most for each area, the nearest first.
    each: dict[int, list] = defaultdict(list)
    for (a, b), km in found.items():
        each[a].append((km, records[b]["id"], b))
        each[b].append((km, records[a]["id"], a))
    keep = {i: {j for _km, _id, j in sorted(v)[:int(settings["near_most"])]} for i, v in each.items()}
    return {(a, b): km for (a, b), km in found.items() if b in keep[a] and a in keep[b]}


def relationships(records, geoms, kinds, sums: Sums, ranks: dict, water: set, settings,
                  near: bool = True) -> dict[int, dict]:
    """Each feature's relationships, by index, with the others also by index. records and kinds may be lists or
    dicts by index. near=False leaves out the areas nearly touching, for a batch of light features (P4-T1l)."""
    full, same_s, partly = settings["full_share"], settings["same_share"], settings["partly_share"]
    out: dict[int, dict] = defaultdict(dict)

    def put(i, key, value):
        out[i].setdefault(key, []).append(value)

    own = sums.own
    land_layers = set(settings.get("land", ()))
    light = set(settings.get("light_layers", ()))
    crossing = set(settings.get("crossing_areas", ()))

    def share(i, km2, key):
        """The share of area i that km2 is: of its land, for a land area with at least land_least of it on land,
        against another land area (P3-T28n, NAV-4); otherwise of its whole shape."""
        sea = sums.sea.get(i, 0.0) if key is not None else 0.0
        if sea <= 0 or own[i] - sea < own[i] * settings["land_least"]:
            return km2 / own[i]
        return max(km2 - sums.sea_shared.get(key, 0.0), 0.0) / (own[i] - sea)

    for (a, b), km2 in sums.shared.items():
        if own.get(a, 0) <= 0 or own.get(b, 0) <= 0:
            continue
        key = (a, b) if records[a]["layer"] in land_layers and records[b]["layer"] in land_layers else None
        sa, sb = share(a, km2, key), share(b, km2, key)
        same_name = settings["same_name_share"]
        if light and (records[a]["layer"] in light or records[b]["layer"] in light):
            # An area of a light layer (P4-T1k) is in, or partly in, the other; never the same, overlapping or
            # holding anything. Two light areas are not compared at all.
            if records[a]["layer"] in light and records[b]["layer"] in light:
                continue
            x, y, sx = (a, b, sa) if records[a]["layer"] in light else (b, a, sb)
            if sx >= full or (sa >= same_s and sb >= same_s):
                put(x, "in", y)
            elif sx >= partly:
                put(x, "partly", [y, round(min(sx, 1.0), 4)])
            continue
        if (sa >= same_s and sb >= same_s) or (sa >= same_name and sb >= same_name and records[a].get("name")
                                                and records[a].get("name") == records[b].get("name")):
            # The same land, or an island and an area of one name over nearly the same land, as the Isle of Wight
            # the island and the county, each cut to the coast a little differently (P3-T23, DP198).
            put(a, "same", b)
            put(b, "same", a)
        elif sa >= full and sb < full:
            put(a, "in", b)
        elif sb >= full and sa < full:
            put(b, "in", a)
        elif sa >= full and sb >= full:   # each nearly all inside the other, but not within same_share
            put(a, "in", b) if own[a] <= own[b] else put(b, "in", a)
        elif sa >= partly or sb >= partly:
            put(a, "overlaps", [b, round(min(sa, 1.0), 4), round(min(sb, 1.0), 4)])
            put(b, "overlaps", [a, round(min(sb, 1.0), 4), round(min(sa, 1.0), 4)])
    neighbours = set()
    sea = set(settings.get("water", ()))
    for (a, b), km in sums.border.items():
        if km < 0.01:
            continue
        la, lb = records[a]["layer"], records[b]["layer"]
        if la == lb:
            neighbours.add((min(a, b), max(a, b)))
            put(a, "next", [b, round(km, 2)])
            put(b, "next", [a, round(km, 2)])
        else:   # land and sea: the land's coast, and the sea's shores (P3-T24e, DP200)
            land, water_area = (b, a) if la in sea else (a, b)
            put(land, "coast", [water_area, round(km, 2)])
            put(water_area, "shores", [land, round(km, 2)])
    for (lake, land), km in sums.shore.items():
        if km >= 0.01:
            put(lake, "shores", [land, round(km, 2)])
    for (a, b), km in (nearly_touching(records, geoms, kinds, neighbours, settings, own) if near else {}).items():
        put(a, "near", [b, km])
        put(b, "near", [a, km])
    # A road's or railway's share inside a land area is measured on its length on land, when at least land_least of
    # it is on land: its length in the sea is its length in the sea's areas, which never overlap. A sea bridge such as
    # the Tay Bridge, 86 percent over the water, is wholly inside Scotland; the roads and railways are split at each
    # country's border (osm-lines), so its land is all in one country.
    land_lines, sea_layers = set(settings.get("land_lines", ())), set(settings.get("sea", ()))
    line_sea: dict[int, float] = defaultdict(float)
    for (i, a), amount in sums.inside.items():
        if kinds[i] == LINE and records[i]["layer"] in land_lines and records[a]["layer"] in sea_layers:
            line_sea[i] += amount
    for (i, a), amount in sums.inside.items():
        whole = own.get(i, 0)
        if whole <= 0:
            continue
        share = amount / whole
        sea_km = line_sea.get(i, 0.0)
        if sea_km > 0 and records[a]["layer"] in land_layers and whole - sea_km >= whole * settings["land_least"]:
            share = min(max(amount - sums.sea_inside.get((i, a), 0.0), 0.0) / (whole - sea_km), 1.0)
        if share >= full:
            put(i, "in", a)
        elif share >= partly:
            put(i, "partly", [a, round(share, 4)])
        if kinds[i] == LINE and amount >= settings["cross_km"]:   # by length, so a long river's short pass counts
            if light and records[i]["layer"] in light:
                # A light line (P4-T1k) lists only the crossing_areas it passes through, and no area lists it.
                if records[a]["layer"] in crossing:
                    put(i, "crosses", [a, sums.first.get((i, a), math.inf)])
                continue
            put(i, "crosses", [a, sums.first.get((i, a), math.inf)])
            put(a, "crossed_by", i)
    for (i, a), km in sums.along.items():
        if km >= 1.0:   # at least a kilometre within border_m of the area's border
            put(a, "along", i)
    for (i, a), points in sums.crossed_at.items():   # each line's crossings of the area's border (P3-T24f)
        unique = sorted({(lat, lon) for lon, lat in points})
        if unique:
            put(a, "crossed_at", [i, [[lat, lon] for lat, lon in unique]])
    # The water hierarchy: the water area of a lower rank that holds the most of each water area.
    for (a, b), km2 in sums.shared.items():
        for x, y in ((a, b), (b, a)):
            if records[x]["layer"] in water and records[y]["layer"] in water and ranks[records[y]["layer"]] < \
                    ranks[records[x]["layer"]] and own.get(x, 0) > 0:
                share = km2 / own[x]
                best = out[x].get("water_in")
                if share >= settings["water_share"] and (best is None or share > best[1]):
                    out[x]["water_in"] = [y, round(share, 4)]
    # Tidy: each list in a fixed order, so the pack is the same each time (DMT-1).
    size = _Size(own)
    for i, rel in out.items():
        for key in ("in", "same", "crossed_by", "along"):
            if key in rel:
                rel[key] = sorted(set(rel[key]), key=lambda j: (size[j], records[j]["id"]))
        for key in ("overlaps", "partly"):
            if key in rel:
                rel[key] = sorted(rel[key], key=lambda v: (-v[1], records[v[0]]["id"]))
        if "crossed_at" in rel:
            rel["crossed_at"] = sorted(rel["crossed_at"], key=lambda v: records[v[0]]["id"])
        for key in ("next", "near", "coast", "shores"):
            if key in rel:
                rel[key] = sorted(rel[key], key=lambda v: (v[1] if key == "near" else -v[1], records[v[0]]["id"]))
        if "crosses" in rel:
            rel["crosses"] = [a for a, _d in sorted(rel["crosses"], key=lambda v: (v[1], ranks[records[v[0]]["layer"]],
                                                                                     records[v[0]]["id"]))]
        if "water_in" in rel:
            rel["water_in"] = rel["water_in"][0]
    # The lines partly inside each area: those crossing it or with a crossing of its border, less those it holds
    # wholly (item 4b), so Overlapping's "Lines crossing its border" reads them at once, not each line's own
    # relationships. Empty for an area crossed only by lines wholly inside it, so the application knows it is kept.
    for a, rel in list(out.items()):
        if "crossed_by" in rel or "crossed_at" in rel:
            lines = set(rel.get("crossed_by", ())) | {v[0] for v in rel.get("crossed_at", ())}
            rel["partly_by"] = sorted((i for i in lines if a not in out.get(i, {}).get("in", ())),
                                      key=lambda j: (size[j], records[j]["id"]))
    # Counts by layer of what is inside each area, fully or partly, by the same test as listing them with
    # Ctrl+Shift+F (Store.browse), so the count said is the number listed: an area overlapping it, such as Lake
    # Geneva for Switzerland, and a line crossing it, count too (P3-T19j, checklist 12.3).
    for i, rel in list(out.items()):
        if light and records[i]["layer"] in light:   # not counted in any area's counts (P4-T1k)
            continue
        holders = set(rel.get("in", [])) | set(rel.get("same", [])) | set(rel.get("crosses", []))             | {v[0] for v in rel.get("partly", [])} | {v[0] for v in rel.get("overlaps", [])}
        for a in sorted(holders):
            counts = out[a].setdefault("counts", {})
            counts[records[i]["layer"]] = counts.get(records[i]["layer"], 0) + 1
    for rel in out.values():
        if "counts" in rel:
            rel["counts"] = dict(sorted(rel["counts"].items()))
    return dict(out)


class _Size:
    """Each feature's own measure by index, 0 for one with none, without a dict of every feature (P4-T1l)."""

    def __init__(self, own):
        self.own = own

    def __getitem__(self, i):
        return self.own.get(i, 0)


def sea_and_land(layers) -> tuple[list[str], list[str]]:
    """The layer that holds all the sea, and the land layers, whose areas' shares inside each other are measured on
    land (P3-T28n). The sea is the water layer of areas of the lowest rank, the oceans: the join stage gives all
    the water to an ocean, and the oceans never overlap. The seas, bays and straits are in the oceans, so they add
    nothing. The land layers are the area layers of kind land but those painted as water, the lakes, which lie on
    the land but are water: the countries, regions, counties, islands, continents, mountain ranges, physical regions
    and the like."""
    water = [v for v in layers.values() if v.kind == "water" and v.geometry == AREA]
    least = min((v.rank for v in water), default=None)
    sea = sorted(v.id for v in water if v.rank == least)
    land = sorted(k for k, v in layers.items() if v.kind != "water" and v.geometry == AREA
                  and dict(v.shown).get("fill") != "water")
    return sea, land


def run(ctx) -> None:
    # The records alone, slimmed to what is used: the stage passes features.json and shapes.wkb on unchanged, so
    # they are kept as they are, not saved again (P4-T1l).
    index = features.read_index(ctx.previous)
    offsets = index["shapes"]
    records = [{"id": r["id"], "layer": r["layer"], **({"name": r["name"]} if "name" in r else {})}
               for r in index["records"]]
    del index
    settings = {**SETTINGS, **{k: v for k, v in ctx.settings.items() if k in SETTINGS}}
    layers = ctx.pack.layers
    settings["water"] = sorted(k for k, v in layers.items() if v.kind == "water" and v.geometry == AREA)
    settings["sea"], settings["land"] = sea_and_land(layers)
    kinds = [layers[r["layer"]].geometry if r["layer"] in layers else AREA for r in records]
    left_out = set(ctx.settings.get("leave_out", LEAVE_OUT))
    light = set(settings.get("light_layers", ()))
    # With light layers, only the other features' shapes are held; the light ones are read batch by batch.
    held = [i for i, r in enumerate(records) if r["layer"] not in left_out and r["layer"] not in light]
    shapes = features.read_shapes(ctx.previous, offsets, held)
    geoms_used = [shapes.get(i) for i in range(len(records))]
    del shapes
    ranks = {k: v.rank for k, v in layers.items()}
    water = {k for k, v in layers.items() if v.kind == "water" and v.geometry == AREA}
    t = time.perf_counter()
    from mapdata import parallel

    texts: dict[int, str] = {}
    with parallel.pool(ctx.workers) as executor:
        pool = None if ctx.workers == 1 else executor
        sums = measure(records, geoms_used, kinds, settings, pool, ctx.workers, ctx.progress.line)
        rel = relationships(records, geoms_used, kinds, sums, ranks, water, settings)
        for i, km in outlines(geoms_used, kinds).items():   # each area's whole border, land and coast (P3-T24f)
            rel.setdefault(i, {})["outline_km"] = km
        counts = defaultdict(int)
        for r in rel.values():
            for k, v in r.items():
                counts[k] += len(v) if isinstance(v, (list, dict)) else 1
        if light:
            lit = [i for i, r in enumerate(records) if r["layer"] in light]
            texts, light_counts = light_relationships(ctx.previous, offsets, lit, records, kinds, geoms_used, sums,
                                                      ranks, water, settings, pool, ctx.workers, ctx.progress.line)
            for k, n in light_counts.items():
                counts[k] += n
    ctx.progress.line(f"Relationships of {len(rel) + len(texts):,} features worked out in "
                      f"{time.perf_counter() - t:.0f} seconds: "
                      + ", ".join(f"{WORDS[k]} {counts[k]:,}" for k in WORDS if counts.get(k)) + ".")
    for name in ("features.json", "shapes.wkb"):
        features.keep_file(ctx.previous / name, ctx.claim(ctx.folder / name))
    write_file(ctx.claim(ctx.folder / FILE), rel, texts)


def write_file(path, rel: dict[int, dict], texts: dict[int, str] | None = None) -> None:
    """relationships.json, written as it is made: the same bytes as json.dumps of {str(index): relationships} with
    sorted keys, where texts holds some features' relationships already as that text (P4-T1l)."""
    texts = texts or {}
    with open(path, "w", encoding="utf-8", newline="\n") as out:
        out.write("{")
        for n, i in enumerate(sorted(set(rel) | set(texts), key=str)):
            text = texts[i] if i in texts else json.dumps(rel[i], sort_keys=True, separators=(",", ":"))
            out.write(("," if n else "") + json.dumps(str(i)) + ":" + text)
        out.write("}")


# The light layers in batches (P4-T1l) ------------------------------------------------------------------------------
#
# A feature of a light layer is compared only with the areas that are not light, and nothing else depends on it. So
# the other features are related first, as before but without the light ones; then the light features are related in
# batches of features near each other, each batch in a worker with the areas that are not light cut to the batch's
# box, and each area's own measure and sea from the first pass. Only each light feature's relationships come back, as
# text. So no process holds every light feature's shape, or the sums for all of them: England has millions.

BATCH_POINTS = 400_000   # about this many points of light features in one batch
CELL_DEG = 0.05          # light features are put in order by the cell their box's centre is in, the cells in Z order
BATCH_MARGIN_DEG = 1e-4  # a batch's box reaches this far beyond its features, so no point lies on its edge
READ_CHUNK = 100_000     # light features' shapes read at once, for their boxes


def z_order(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """The Z-order (Morton) number of each cell (x, y), so cells near each other mostly come close in order."""
    def spread(v):
        v = v.astype(np.uint64) & np.uint64(0xFFFFFFFF)
        for shift, mask in ((16, 0x0000FFFF0000FFFF), (8, 0x00FF00FF00FF00FF), (4, 0x0F0F0F0F0F0F0F0F),
                            (2, 0x3333333333333333), (1, 0x5555555555555555)):
            v = (v | (v << np.uint64(shift))) & np.uint64(mask)
        return v
    return spread(x) | (spread(y) << np.uint64(1))


def light_batches(idx: np.ndarray, bounds: np.ndarray, points: np.ndarray, most: int,
                  cell_deg: float = CELL_DEG) -> list[np.ndarray]:
    """The light features (their indexes idx, boxes and points) put into batches of about most points, near each
    other: in Z order of the cell holding each box's centre, then by index. Each batch's indexes in order."""
    if not len(idx):
        return []
    cx = np.floor(((bounds[:, 0] + bounds[:, 2]) / 2 + 180) / cell_deg)
    cy = np.floor(((bounds[:, 1] + bounds[:, 3]) / 2 + 90) / cell_deg)
    order = np.lexsort((idx, z_order(cx, cy)))
    group = (np.cumsum(points[order]) - 1) // max(int(most), 1)
    cuts = np.nonzero(np.diff(group))[0] + 1
    return [np.sort(idx[part]) for part in np.split(order, cuts)]


def _read_blobs(folder, offsets, which) -> list[bytes]:
    out = []
    with open(Path(folder) / "shapes.wkb", "rb") as f:
        for i in which:
            a, n = offsets[i]
            f.seek(a)
            out.append(f.read(n))
    return out


def _light_job(job):
    """One batch of light features, related in a worker: their relationships as text by index, the counts by kind,
    and how many pairs needed repairing."""
    box, light_items, area_items, meta, own, sea, settings, ranks, water = job
    records = {i: m[0] for i, m in meta.items()}
    kinds = {i: m[1] for i, m in meta.items()}
    layer_of = {i: m[0]["layer"] for i, m in meta.items()}
    lit = [(i, k, shapely.from_wkb(b)) for i, k, b in light_items]
    # As measure does: a line that goes back over itself is measured with each stretch once, and carries its
    # distance from its start.
    lines = [n for n, (_i, k, g) in enumerate(lit) if k == LINE and not g.is_empty]
    twice = retraced([lit[n][2] for n in lines]) if lines else np.zeros(0, dtype=bool)
    back = {n for n, t in zip(lines, twice) if t}
    items = []
    for n, (i, k, g) in enumerate(lit):
        if g.is_empty:
            continue
        items.append((i, k, with_distance(once_over(g) if n in back else g) if k == LINE else g))
    items += [(i, AREA, shapely.from_wkb(b)) for i, b in area_items]
    items.sort(key=lambda it: it[0])
    sums = Sums()
    REPAIRED[0] = 0
    relate(tuple(box), items, layer_of, settings, sums)
    light_ids = {i for i, _k, _b in light_items}
    # Only what concerns a light feature is kept; each area's own measure and sea are its whole, from the first pass.
    for name in ("shared", "border", "inside", "along", "shore", "sea_shared", "sea_inside"):
        d = getattr(sums, name)
        for key in [key for key in d if key[0] not in light_ids and key[1] not in light_ids]:
            del d[key]
    sums.first = {k: v for k, v in sums.first.items() if k[0] in light_ids or k[1] in light_ids}
    sums.crossed_at.clear()
    sums.edges = []
    for i, km in own.items():
        sums.own[i] = km
    for i in [i for i in sums.sea if i not in light_ids]:
        del sums.sea[i]
    for i, km2 in sea.items():
        sums.sea[i] = km2
    out = relationships(records, None, kinds, sums, ranks, water, settings, near=False)
    texts, counts = {}, defaultdict(int)
    for i in sorted(light_ids):
        r = out.get(i)
        if r:
            texts[i] = json.dumps(r, sort_keys=True, separators=(",", ":"))
            for k, v in r.items():
                counts[k] += len(v) if isinstance(v, (list, dict)) else 1
    return texts, dict(counts), REPAIRED[0]


def light_relationships(folder, offsets, lit: list[int], records, kinds, geoms, sums: Sums, ranks, water, settings,
                        executor, workers: int, say=print) -> tuple[dict[int, str], dict[str, int]]:
    """The light features' relationships, batch by batch (see above): {index: text}, and the counts by kind. geoms
    holds the shapes of the features that are not light, and sums their first pass."""
    from mapdata.stages.pack_write import run_within_budget

    started = time.perf_counter()
    idx = np.array(lit, dtype=np.intp)
    bounds = np.zeros((len(idx), 4))
    points = np.zeros(len(idx), dtype=np.int64)
    for at in range(0, len(idx), READ_CHUNK):
        part = idx[at:at + READ_CHUNK]
        g = shapely.from_wkb(np.array(_read_blobs(folder, offsets, part), dtype=object))
        bounds[at:at + len(part)] = shapely.bounds(g)
        points[at:at + len(part)] = shapely.get_num_coordinates(g)
    keep = ~np.isnan(bounds).any(axis=1)   # an empty shape has no box, and no relationships
    most = int(settings.get("batch_points", BATCH_POINTS))
    batches = light_batches(idx[keep], bounds[keep], points[keep], most)
    where = {int(i): k for k, i in enumerate(idx)}
    areas = [i for i, g in enumerate(geoms) if g is not None and kinds[i] == AREA and not g.is_empty]
    tree = shapely.STRtree(np.array([geoms[i] for i in areas], dtype=object))
    say(f"Relating {int(keep.sum()):,} features of the light layers to the {len(areas):,} areas of the other layers, "
        f"in {len(batches):,} batches of about {most:,} points.")

    def make(batch):
        b = bounds[[where[int(i)] for i in batch]]
        m = BATCH_MARGIN_DEG
        box = (float(b[:, 0].min()) - m, float(b[:, 1].min()) - m, float(b[:, 2].max()) + m,
               float(b[:, 3].max()) + m)
        area_items = []
        for i in sorted(int(areas[k]) for k in tree.query(shapely.box(*box))):
            g = geoms[i]
            gx0, gy0, gx1, gy1 = shapely.bounds(g)
            if not (gx0 >= box[0] and gy0 >= box[1] and gx1 <= box[2] and gy1 <= box[3]):
                g = shapely.clip_by_rect(g, *box)
                if g.is_empty or shapely.area(g) <= 0:
                    continue
            area_items.append((i, shapely.to_wkb(g)))
        ids = [int(i) for i in batch]
        meta = {i: (records[i], kinds[i]) for i in ids}
        meta.update({i: (records[i], kinds[i]) for i, _b in area_items})
        own = {i: sums.own.get(i, 0.0) for i, _b in area_items}
        sea = {i: sums.sea[i] for i, _b in area_items if i in sums.sea}
        light_items = list(zip(ids, [kinds[i] for i in ids], _read_blobs(folder, offsets, ids)))
        return (box, light_items, area_items, meta, own, sea, settings, ranks, water)

    texts: dict[int, str] = {}
    counts: dict[str, int] = defaultdict(int)
    repaired = 0
    if executor is None or workers == 1:
        results = (_light_job(make(b)) for b in batches)
    else:
        costs = [int(points[[where[int(i)] for i in b]].sum()) for b in batches]
        results = run_within_budget(executor, _light_job, batches, make, costs, math.inf, workers)
    for n, (got, c, rep) in enumerate(results, 1):
        texts.update(got)
        for k, v in c.items():
            counts[k] += v
        repaired += rep
        if n % 10 == 0 or n == len(batches):
            say(f"Related the light features of {n:,} of {len(batches):,} batches, "
                f"{time.perf_counter() - started:.0f} seconds.")
    if repaired:
        say(f"Pairs of shapes the geometry library could not compare as they were, so made valid first, in the light "
            f"layers' batches: {repaired}.")
    return texts, dict(counts)


def outlines(geoms, kinds, chunk: int = 2000) -> dict[int, float]:
    """Each area's whole outline, its border with land and coast together, in km over the Earth, rounded to
    0.01 km (P3-T24f, DP201). The cut along the 180 degree line is not a border, so it is left out."""
    out: dict[int, float] = {}
    areas = [i for i, (g, k) in enumerate(zip(geoms, kinds)) if k == AREA and g is not None and not g.is_empty]
    seam = shapely.union(shapely.LineString([(180, -90), (180, 90)]), shapely.LineString([(-180, -90), (-180, 90)]))
    near_seam = shapely.buffer(seam, 1e-7)
    for at in range(0, len(areas), chunk):
        these = areas[at:at + chunk]
        edges = shapely.boundary(np.array([geoms[i] for i in these], dtype=object))
        bounds = shapely.bounds(edges)
        on_seam = (bounds[:, 0] <= -180 + 1e-7) | (bounds[:, 2] >= 180 - 1e-7)
        if on_seam.any():
            edges[on_seam] = robust(shapely.difference, edges[on_seam], np.array([near_seam] * int(on_seam.sum()), dtype=object))
        for i, km in zip(these, lengths_km(edges)):
            out[i] = round(float(km), 2)
    return out


FILE = "relationships.json"
WORDS = {"in": "inside", "same": "the same land", "overlaps": "overlapping", "partly": "partly inside",
         "next": "neighbours", "near": "nearly touching", "crosses": "areas crossed", "crossed_by": "crossed by",
         "along": "along a border", "water_in": "in a larger water area", "counts": "areas with counts",
         "coast": "with a coast", "shores": "with shores", "outline_km": "outlines measured",
         "crossed_at": "with border crossings", "partly_by": "with lines partly inside"}


def load(folder) -> dict[int, dict] | None:
    path = folder / FILE
    if not path.is_file():
        return None
    return {int(k): v for k, v in json.loads(path.read_text(encoding="utf-8")).items()}


def _with_ids(r: dict, ids: list[str]) -> dict:
    def fix(key, v):
        if key in ("in", "same", "crossed_by", "along", "crosses", "partly_by"):
            return [ids[j] for j in v]
        if key in ("overlaps", "partly", "next", "near", "coast", "shores", "crossed_at"):
            return [[ids[x[0]], *x[1:]] for x in v]
        if key == "water_in":
            return ids[v]
        return v
    return {k: fix(k, v) for k, v in r.items()}


def by_id(rel: dict[int, dict], ids: list[str]) -> dict[str, dict]:
    """The relationships with every index made the id the feature is written with."""
    return {ids[i]: _with_ids(r, ids) for i, r in rel.items()}


def load_by_id(folder, ids: list[str]) -> dict[str, dict] | None:
    """by_id(load(folder), ids), but each feature's relationships read from the file and given their ids one at a
    time, so the relationships by index are never all held beside those by id (P4-T1l). The same order."""
    out: dict[str, dict] = {}
    if not _each_by_id(folder, ids, lambda i, rel: out.__setitem__(ids[i], rel)):
        return None
    return out


def load_store(folder, ids: list[str], index_of: dict[str, int], spill_folder=None, change=None):
    """The relationships as load_by_id gives them, but set aside on disk in a RelStore (P4-T1m), each changed by
    change(rel) first if given. None when the stage before has no relationships file."""
    from mapdata.pipeline.spill import RelStore

    store = RelStore(ids, index_of, spill_folder)

    def put(i, rel):
        if change is not None:
            change(rel)
        store.put(i, rel)

    try:
        found = _each_by_id(folder, ids, put)
    except BaseException:
        store.close()
        raise
    if not found:
        store.close()
        return None
    return store


def _each_by_id(folder, ids: list[str], take) -> bool:
    """take(index, relationships with ids) for each feature in the relationships file, in its order; False when
    there is no file."""
    path = Path(folder) / FILE
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    space = " \t\r\n"

    def skip(at):
        while text[at] in space:
            at += 1
        return at

    at = skip(skip(0) + 1)   # past "{"
    while text[at] != "}":
        key, at = decoder.raw_decode(text, at)
        at = skip(at)
        value, at = decoder.raw_decode(text, skip(at + 1))   # past ":"
        take(int(key), _with_ids(value, ids))
        at = skip(at)
        if text[at] == ",":
            at = skip(at + 1)
    return True
