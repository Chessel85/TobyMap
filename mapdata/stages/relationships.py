"""Stage "relationships": what each feature is inside, beside, overlapping and crossing (P3-T3, AD-8).

The application only looks these up (AD-8); they are worked out here, once, for every feature:

* Containment (P3-T3a, NAV-4): the areas that hold a feature fully, from every layer, so the parents
  of parents are there too; and, for a line or a place, the areas it is partly inside, with the
  share. Two areas that are the same land, each inside the other to within same_share, are "same
  as", not parent and child (DP71).
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

Settings: same_share (0.99), full_share (0.995), partly_share (0.005), cross_km (0.05), near_km (5), near_share
(0.25) and near_most (10), for nearly touching, border_m (100),
water_share (0.5), leaf_points (20000), min_leaf_deg (0.25), top_deg (45), along_lines and along_areas (the
layers looked at for a line along a border: rivers, against countries, regions and counties), and leave_out, the
layers with no relationships (the graticule and the special lines).
"""
from __future__ import annotations

import json
import math
import time
from collections import defaultdict

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.stages.geodesy import areas_km2

R_KM = 6371.0088
SETTINGS = {"same_share": 0.99, "full_share": 0.995, "partly_share": 0.005, "cross_km": 0.05, "near_km": 5.0, "near_share": 0.25, "near_most": 10, "border_m": 100.0,
            "water_share": 0.5, "leaf_points": 20000, "min_leaf_deg": 0.25, "top_deg": 45.0,
            "along_lines": ("rivers",), "along_areas": ("countries", "regions", "counties")}
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


def with_distance(line):
    """A line with each point's distance from the line's start, in km, as its third coordinate. A river in several
    parts, such as one split round islands or a delta, is measured along its longest part, from that part's start:
    each point's distance is where it falls on that part, so the parts' own order does not matter."""
    parts = [p for p in shapely.get_parts(line) if shapely.get_num_coordinates(p) >= 2]
    if not parts:
        return shapely.MultiLineString()
    km = lengths_km(np.array(parts, dtype=object))
    main = parts[int(np.argmax(km))]
    main_deg = max(shapely.length(main), 1e-12)
    out = []
    for p in parts:
        c = shapely.get_coordinates(p)
        at = shapely.line_locate_point(main, shapely.points(c)) / main_deg * float(km.max())
        out.append(shapely.LineString(np.column_stack([c, at])))
    return shapely.MultiLineString(out)


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
        # Stretches of an area's own outline lying on a cutting line, which no box sees both sides of:
        # (orientation "v" or "h", the line's longitude or latitude, from, to, feature, side 0 west or south, 1 east
        # or north). Matched across features afterwards (edge_borders).
        self.edges: list[tuple] = []

    def add(self, other: "Sums") -> None:
        for name in ("own", "shared", "border", "inside", "along"):
            mine = getattr(self, name)
            for k, v in getattr(other, name).items():
                mine[k] += v
        for k, v in other.first.items():
            self.first[k] = min(v, self.first.get(k, math.inf))
        self.edges.extend(other.edges)

    def plain(self) -> dict:
        def pairs(d):
            return [[int(a), int(b), float(v)] for (a, b), v in d.items()]
        return {"own": [[int(k), float(v)] for k, v in self.own.items()], "shared": pairs(self.shared),
                "border": pairs(self.border), "inside": pairs(self.inside), "first": pairs(self.first),
                "along": pairs(self.along), "edges": [list(e) for e in self.edges]}

    @classmethod
    def from_plain(cls, d: dict) -> "Sums":
        s = cls()
        for k, v in d["own"]:
            s.own[k] = v
        for name in ("shared", "border", "inside", "first", "along"):
            target = getattr(s, name)
            for a, b, v in d[name]:
                target[(a, b)] = v
        s.edges = [tuple(e) for e in d.get("edges", [])]
        return s


def leaf(box, items, layer_of: list[str], settings: dict, sums: Sums) -> None:
    """Compare the parts in one box."""
    w, s, e, n = box
    box_shape = shapely.box(w, s, e, n)
    box_km2 = float(areas_km2([box_shape])[0])
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
    # Land two areas share: a covering area shares all of the other's land here.
    for a in whole:
        for b in range(len(areas)):
            if b != a and areas[b][0] != areas[a][0] and (areas[b][2] is not COVER or a < b):
                key = tuple(sorted((areas[a][0], areas[b][0])))
                sums.shared[key] += own[b]
    if len(parts) > 1:
        arr = np.array([areas[k][2] for k in parts], dtype=object)
        tree = shapely.STRtree(arr)
        left, right = tree.query(arr, predicate="intersects")
        keep = left < right
        left, right = left[keep], right[keep]
        if len(left):
            inter = shapely.intersection(arr[left], arr[right])
            got = areas_km2(inter)
            for a, b, km2 in zip(left, right, got):
                ia, ib = areas[parts[a]][0], areas[parts[b]][0]
                if km2 > 0 and ia != ib:
                    sums.shared[tuple(sorted((ia, ib)))] += float(km2)
            # Borders shared by two areas of one layer, but not along the box's own edges.
            same = np.array([layer_of[areas[parts[a]][0]] == layer_of[areas[parts[b]][0]] for a, b in zip(left, right)],
                            dtype=bool)
            if same.any():
                la, rb = left[same], right[same]
                edge = shapely.boundary(box_shape)
                shared = shapely.intersection(shapely.boundary(arr[la]), shapely.boundary(arr[rb]))
                shared = shapely.difference(shared, shapely.buffer(edge, 1e-9))
                for a, b, km in zip(la, rb, lengths_km(shared)):
                    if km > 0:
                        sums.border[tuple(sorted((areas[parts[a]][0], areas[parts[b]][0])))] += float(km)
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
        if parts:
            arr = np.array([areas[k][2] for k in parts], dtype=object)
            tree = shapely.STRtree(arr)
            li_idx, ar_idx = tree.query(larr, predicate="intersects")
            if len(li_idx):
                inter = shapely.intersection(larr[li_idx], arr[ar_idx])
                kms, firsts = lengths_km(inter), first_distance(inter)
                for l_, a_, km, d in zip(li_idx, ar_idx, kms, firsts):
                    if km > 0:
                        key = (lines[l_][0], areas[parts[a_]][0])
                        sums.inside[key] += float(km)
                        sums.first[key] = min(sums.first.get(key, math.inf), float(d))
            # Along a border: within border_m of an area's edge, that is not the box's edge. Only for the lines and
            # areas of the layers named, such as a river forming a border, as buffering every outline is slow.
            tol = settings["border_m"] / 1000 / 111.32
            li_idx, ar_idx = tree.query(larr, predicate="dwithin", distance=tol)
            keep = np.array([layer_of[lines[l_][0]] in settings["along_lines"]
                             and layer_of[areas[parts[a_]][0]] in settings["along_areas"]
                             for l_, a_ in zip(li_idx, ar_idx)], dtype=bool)
            li_idx, ar_idx = (li_idx[keep], ar_idx[keep]) if len(li_idx) else (li_idx, ar_idx)
            if len(li_idx):
                edges = shapely.difference(shapely.boundary(arr[ar_idx]),
                                           shapely.buffer(shapely.boundary(box_shape), tol))
                near = shapely.intersection(larr[li_idx], shapely.buffer(edges, tol))
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
        got = shapely.intersection(edge, line)
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


def edge_borders(edges: list[tuple], layer_of: list[str]) -> dict[tuple, float]:
    """Shared borders along cutting lines: a stretch of one feature's outline on a line, with the feature on one
    side, against another feature of the same layer on the other side. {(a, b): km}."""
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
                if a != b and layer_of[a] == layer_of[b]:
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
    for it in items:
        on_lines(it, [("v", mx, s, n), ("h", my, w, e)], sums)
    for sub in ((w, s, mx, my), (mx, s, e, my), (w, my, mx, n), (mx, my, e, n)):
        inside = [c for c in (cut(it, sub) for it in items) if c is not None]
        relate(sub, inside, layer_of, settings, sums, depth + 1)


def _job(job):
    box, blobs, layer_of, settings = job
    items = [(i, k, COVER if b is None else shapely.from_wkb(b)) for i, k, b in blobs]
    sums = Sums()
    relate(tuple(box), items, layer_of, settings, sums)
    return sums.plain()


def top_boxes(deg: float) -> list[tuple]:
    out = []
    for s in np.arange(-90, 90, deg):
        for w in np.arange(-180, 180, deg):
            out.append((float(w), float(s), float(min(w + deg, 180)), float(min(s + deg, 90))))
    return out


def measure(records, geoms, kinds, settings, executor=None, workers: int = 1, say=print) -> Sums:
    """The sums for every feature, the top boxes run in the workers when there are workers."""
    layer_of = [r["layer"] for r in records]
    items = []
    for i, (g, k) in enumerate(zip(geoms, kinds)):
        if g is None or g.is_empty:
            continue
        items.append((i, k, with_distance(g) if k == LINE else g))
    top = total = Sums()
    deg = settings["top_deg"]
    lines = [("v", float(x), -90.0, 90.0) for x in np.arange(-180 + deg, 180, deg)] +             [("h", float(y), -180.0, 180.0) for y in np.arange(-90 + deg, 90, deg)]
    for it in items:
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
    for n, plain in enumerate(results, 1):
        total.add(Sums.from_plain(plain))
        if n % 4 == 0 or n == len(jobs):
            say(f"Compared the features in {n} of {len(jobs)} boxes of {settings['top_deg']:g} degrees, "
                f"{time.perf_counter() - started:.0f} seconds.")
    for key, km in edge_borders(total.edges, layer_of).items():
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
    for i, k in enumerate(kinds):
        if k == AREA and geoms[i] is not None and not geoms[i].is_empty:
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


def relationships(records, geoms, kinds, sums: Sums, ranks: dict, water: set, settings) -> dict[int, dict]:
    """Each feature's relationships, by index, with the others also by index."""
    full, same_s, partly = settings["full_share"], settings["same_share"], settings["partly_share"]
    out: dict[int, dict] = defaultdict(dict)

    def put(i, key, value):
        out[i].setdefault(key, []).append(value)

    own = sums.own
    for (a, b), km2 in sums.shared.items():
        if own.get(a, 0) <= 0 or own.get(b, 0) <= 0:
            continue
        sa, sb = km2 / own[a], km2 / own[b]
        if sa >= same_s and sb >= same_s:
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
    for (a, b), km in sums.border.items():
        if km >= 0.01:
            neighbours.add((min(a, b), max(a, b)))
            put(a, "next", [b, round(km, 2)])
            put(b, "next", [a, round(km, 2)])
    for (a, b), km in nearly_touching(records, geoms, kinds, neighbours, settings, own).items():
        put(a, "near", [b, km])
        put(b, "near", [a, km])
    for (i, a), amount in sums.inside.items():
        whole = own.get(i, 0)
        if whole <= 0:
            continue
        share = amount / whole
        if share >= full:
            put(i, "in", a)
        elif share >= partly:
            put(i, "partly", [a, round(share, 4)])
        if kinds[i] == LINE and amount >= settings["cross_km"]:   # by length, so a long river's short pass counts
            put(i, "crosses", [a, sums.first.get((i, a), math.inf)])
            put(a, "crossed_by", i)
    for (i, a), km in sums.along.items():
        if km >= 1.0:   # at least a kilometre within border_m of the area's border
            put(a, "along", i)
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
    size = {i: own.get(i, 0) for i in range(len(records))}
    for i, rel in out.items():
        for key in ("in", "same", "crossed_by", "along"):
            if key in rel:
                rel[key] = sorted(set(rel[key]), key=lambda j: (size[j], records[j]["id"]))
        for key in ("overlaps", "partly"):
            if key in rel:
                rel[key] = sorted(rel[key], key=lambda v: (-v[1], records[v[0]]["id"]))
        for key in ("next", "near"):
            if key in rel:
                rel[key] = sorted(rel[key], key=lambda v: (-v[1] if key == "next" else v[1], records[v[0]]["id"]))
        if "crosses" in rel:
            rel["crosses"] = [a for a, _d in sorted(rel["crosses"], key=lambda v: (v[1], ranks[records[v[0]]["layer"]],
                                                                                     records[v[0]]["id"]))]
        if "water_in" in rel:
            rel["water_in"] = rel["water_in"][0]
    # Counts by layer of what is inside each area, fully or partly.
    for i, rel in list(out.items()):
        for a in rel.get("in", []) + [v[0] for v in rel.get("partly", [])]:
            counts = out[a].setdefault("counts", {})
            counts[records[i]["layer"]] = counts.get(records[i]["layer"], 0) + 1
    for rel in out.values():
        if "counts" in rel:
            rel["counts"] = dict(sorted(rel["counts"].items()))
    return dict(out)


def run(ctx) -> None:
    records, geoms = features.load(ctx.previous)
    settings = {**SETTINGS, **{k: v for k, v in ctx.settings.items() if k in SETTINGS}}
    layers = ctx.pack.layers
    kinds = [layers[r["layer"]].geometry if r["layer"] in layers else AREA for r in records]
    left_out = set(ctx.settings.get("leave_out", LEAVE_OUT))
    geoms_used = [None if r["layer"] in left_out else g for r, g in zip(records, geoms)]
    ranks = {k: v.rank for k, v in layers.items()}
    water = {k for k, v in layers.items() if v.kind == "water" and v.geometry == AREA}
    t = time.perf_counter()
    from mapdata import parallel

    with parallel.pool(ctx.workers) as executor:
        sums = measure(records, geoms_used, kinds, settings, None if ctx.workers == 1 else executor, ctx.workers,
                       ctx.progress.line)
    rel = relationships(records, geoms_used, kinds, sums, ranks, water, settings)
    counts = defaultdict(int)
    for r in rel.values():
        for k, v in r.items():
            counts[k] += len(v) if isinstance(v, (list, dict)) else 1
    ctx.progress.line(f"Relationships of {len(rel):,} features worked out in {time.perf_counter() - t:.0f} seconds: "
                      + ", ".join(f"{WORDS[k]} {counts[k]:,}" for k in WORDS if counts.get(k)) + ".")
    features.save(ctx.folder, records, geoms, ctx.claim)
    text = json.dumps({str(i): r for i, r in sorted(rel.items())}, sort_keys=True, separators=(",", ":"))
    ctx.claim(ctx.folder / FILE).write_text(text, encoding="utf-8", newline="\n")


FILE = "relationships.json"
WORDS = {"in": "inside", "same": "the same land", "overlaps": "overlapping", "partly": "partly inside",
         "next": "neighbours", "near": "nearly touching", "crosses": "areas crossed", "crossed_by": "crossed by",
         "along": "along a border", "water_in": "in a larger water area", "counts": "areas with counts"}


def load(folder) -> dict[int, dict] | None:
    path = folder / FILE
    if not path.is_file():
        return None
    return {int(k): v for k, v in json.loads(path.read_text(encoding="utf-8")).items()}


def by_id(rel: dict[int, dict], ids: list[str]) -> dict[str, dict]:
    """The relationships with every index made the id the feature is written with."""
    def fix(key, v):
        if key in ("in", "same", "crossed_by", "along", "crosses"):
            return [ids[j] for j in v]
        if key in ("overlaps", "partly", "next", "near"):
            return [[ids[x[0]], *x[1:]] for x in v]
        if key == "water_in":
            return ids[v]
        return v
    return {ids[i]: {k: fix(k, v) for k, v in r.items()} for i, r in rel.items()}
