"""The world in grid squares: every layer as one coverage, simplified once (P1-T4, AD-16, LOC-6).

The base pack lite is built one grid square at a time. In each grid square:

1. The outlines of everything in it, the land, the countries, the country
   units, the divisions and the oceans, are joined into one set of lines,
   with every crossing made a point.
2. The lines are made into faces. The faces cover the whole grid square,
   with no gaps and no overlaps, and each face is wholly inside or wholly
   outside each area.
3. Each face is named by testing one point inside it: land or water, which
   country, which region, which ocean. Faces with the same names are joined.
   A face of land in no country, or of water in no ocean, is named as
   waiting; the join stage gives it to a neighbour or names it.
4. The joined faces are simplified as one coverage, with the grid square's
   own edges held fixed, so each border and coast is simplified once and
   neighbouring grid squares still meet exactly.

Every point is on a grid of ten-millionths of a degree, the precision of the
pack's compact coordinates, so cuts made in neighbouring grid squares give
the same points.

Because the sea is part of each grid square's coverage, the coast is shared
by the land and the oceans, and the oceans meet the land exactly.

This module has no reading or writing of files, so it is tested on small
made-up shapes (tests/mapdata/test_grid.py).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
import shapely

GRID = 1e-7            # ten-millionths of a degree, as compact coordinates
METRES_PER_DEGREE = 111_320.0
LEVEL_ORDER = (4, 3, 5)  # the regions: level 4, gaps filled by level 3, then level 5 (DP114, DP116)

WAITING_LAND = ("land", None, None)
WAITING_WATER = ("water", None, None)


@dataclass(frozen=True)
class Meta:
    """What a square needs to know about one area: never its shape."""
    kind: str               # country (level 2), unit (a country unit), division, ocean
    id: str
    country: str | None     # the level 2 country a unit or division is in
    level: int | None
    size: float             # the area's whole size in square degrees, for "the smaller wins"


def square_key(w: float, s: float) -> str:
    return f"{w:+08.3f}_{s:+08.3f}"


def squares_in(bounds, size: float) -> list[tuple[float, float]]:
    """The south-west corners of the grid squares that a rectangle touches."""
    w, s, e, n = bounds
    i0, i1 = math.floor(w / size), math.ceil(e / size)
    j0, j1 = math.floor(s / size), math.ceil(n / size)
    out = []
    for i in range(i0, max(i1, i0 + 1)):
        for j in range(j0, max(j1, j0 + 1)):
            x, y = round(i * size, 7), round(j * size, 7)
            if -180 <= x < 180 and -90 <= y < 90:
                out.append((x, y))
    return out


def cut_to_squares(geom, size: float, within=None) -> dict[tuple[float, float], object]:
    """The parts of a shape in each grid square it touches, cut by halving, so a large shape is
    cut in time that grows with its points times the number of halvings, not the number of squares.

    within, a rectangle, limits the cut to the grid squares inside it.
    """
    out: dict[tuple[float, float], object] = {}
    if geom is None or geom.is_empty:
        return out
    w, s, e, n = geom.bounds
    if within is not None:
        w, s, e, n = max(w, within[0]), max(s, within[1]), min(e, within[2]), min(n, within[3])
        if w >= e or s >= n:
            return out
    i0, i1 = math.floor(w / size), max(math.ceil(e / size), math.floor(w / size) + 1)
    j0, j1 = math.floor(s / size), max(math.ceil(n / size), math.floor(s / size) + 1)

    def rect(a0, a1, b0, b1):
        return shapely.box(a0 * size, b0 * size, a1 * size, b1 * size)

    def go(g, a0, a1, b0, b1):
        if g.is_empty:
            return
        if a1 - a0 == 1 and b1 - b0 == 1:
            x, y = round(a0 * size, 7), round(b0 * size, 7)
            if -180 <= x < 180 and -90 <= y < 90:
                part = polygonal(g)
                if part is not None and not part.is_empty:
                    out[(x, y)] = part
            return
        if a1 - a0 >= b1 - b0:
            m = (a0 + a1) // 2
            halves = ((a0, m, b0, b1), (m, a1, b0, b1))
        else:
            m = (b0 + b1) // 2
            halves = ((a0, a1, b0, m), (a0, a1, m, b1))
        for h in halves:
            go(_cut(g, rect(*h)), *h)

    go(_cut(polygonal(geom), rect(i0, i1, j0, j1)), i0, i1, j0, j1)
    return out


def _cut(g, r):
    """The areas of g inside the rectangle r, on the grid. Lines and points, where g only touches r, are
    dropped, as the next cut refuses shapes that mix areas with lines."""
    if g is None or g.is_empty:
        return shapely.Polygon()
    out = polygonal(shapely.intersection(g, r, grid_size=GRID))
    return shapely.Polygon() if out is None else out


def polygonal(g):
    """Only the areas of a shape, as one Polygon or MultiPolygon, or None."""
    if g is None or g.is_empty:
        return None
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = [p for p in shapely.get_parts(g) if p.geom_type in ("Polygon", "MultiPolygon")]
    parts = [q for p in parts for q in shapely.get_parts(p)]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)


@dataclass
class Rules:
    """The settings that decide names where areas overlap."""
    condominiums: dict[frozenset, str] = field(default_factory=dict)  # pair of country ids: condominium id


@dataclass
class SquareResult:
    key: str
    labels: list[tuple]          # (kind, country, region) for land; (kind, ocean, None) for water
    shapes: list                 # the simplified shape for each label
    points_before: int = 0
    points_after: int = 0
    faces: int = 0
    overlaps: list[tuple] = field(default_factory=list)   # (layer, ids, km2)
    fills: list[tuple] = field(default_factory=list)      # (country, region, level, km2) regions from level 3 or 5
    pairs: list[tuple[int, int]] = field(default_factory=list)  # labels that share a border or coast here


def km2_of(face) -> float:
    """A quick area for reports, from square degrees at the face's latitude."""
    lat = (face.bounds[1] + face.bounds[3]) / 2
    return face.area * (METRES_PER_DEGREE / 1000) ** 2 * math.cos(math.radians(lat))


def label_land(hits: list[int], meta: list[Meta], rules: Rules, overlaps: list, fills: list, km2: float):
    """The names of a face of land, from the areas it is inside."""
    countries = sorted((i for i in hits if meta[i].kind == "country"), key=lambda i: (meta[i].size, meta[i].id))
    base = None
    country = None
    if len(countries) > 1:
        ids = frozenset(meta[i].id for i in countries)
        condo = next((c for pair, c in rules.condominiums.items() if pair <= ids), None)
        if condo is not None:
            country = condo
        else:
            overlaps.append(("countries", tuple(sorted(ids)), km2))
    if countries:
        base = meta[countries[0]].id
        if country is None:
            country = base
            units = sorted((i for i in hits if meta[i].kind == "unit" and meta[i].country == base),
                           key=lambda i: (meta[i].size, meta[i].id))
            if units:
                country = meta[units[0]].id
    region = None
    if base is not None and country is not None and not country.startswith("condominium:"):
        own = [i for i in hits if meta[i].kind == "division" and meta[i].country == base]
        for level in LEVEL_ORDER:
            at = sorted((i for i in own if meta[i].level == level), key=lambda i: (meta[i].size, meta[i].id))
            if at:
                region = meta[at[0]].id
                if len(at) > 1:
                    overlaps.append(("regions", tuple(sorted(meta[i].id for i in at)), km2))
                if level != LEVEL_ORDER[0]:
                    fills.append((base, region, level, km2))
                break
    return ("land", country, region)


def label_water(hits: list[int], meta: list[Meta]):
    oceans = sorted(meta[i].id for i in hits if meta[i].kind == "ocean")
    return ("water", oceans[0] if oceans else None, None)


def build_square(bounds, land, pieces: list[tuple[int, object]], meta: list[Meta], rules: Rules,
                 tolerance_m: float) -> SquareResult:
    """One grid square: faces, names, and the simplified coverage (see the module's notes).

    land is the land inside the grid square; pieces are (index into meta, the area's part in the grid
    square). tolerance_m is the base detail, in metres (DP112).
    """
    q = shapely.box(*bounds)
    key = square_key(bounds[0], bounds[1])
    land = polygonal(land) if land is not None else None
    lines = [q.boundary]
    if land is not None:
        lines.append(land.boundary)
    lines += [g.boundary for _i, g in pieces]
    noded = shapely.union_all([g for g in lines if g is not None and not g.is_empty], grid_size=GRID)
    faces = np.array([f for f in shapely.get_parts(shapely.polygonize(list(shapely.get_parts(noded))))
                      if f.area > 0], dtype=object)
    result = SquareResult(key, [], [], faces=len(faces))
    if len(faces) == 0:
        return result
    points = shapely.point_on_surface(faces)
    xy = shapely.get_coordinates(points)
    on_land = (shapely.contains_xy(land, xy[:, 0], xy[:, 1]) if land is not None
               else np.zeros(len(faces), bool))
    hits: dict[int, list[int]] = defaultdict(list)
    if pieces:
        shapes = np.array([g for _i, g in pieces], dtype=object)
        tree = shapely.STRtree(shapes)
        f_idx, p_idx = tree.query(points, predicate="within")
        for f, p in zip(f_idx.tolist(), p_idx.tolist()):
            hits[f].append(pieces[p][0])
    groups: dict[tuple, list] = defaultdict(list)
    for f, face in enumerate(faces):
        if on_land[f]:
            lab = label_land(hits[f], meta, rules, result.overlaps, result.fills, km2_of(face))
            if lab[1] is None:
                lab = WAITING_LAND
        else:
            lab = label_water(hits[f], meta)
        groups[lab].append(face)
    labels = sorted(groups, key=lambda k: tuple("" if v is None else str(v) for v in k))
    joined = [shapely.coverage_union_all(groups[k]) for k in labels]
    result.points_before = int(sum(shapely.get_num_coordinates(joined)))
    simplified = shapely.coverage_simplify(np.array(joined, dtype=object), tolerance_m / METRES_PER_DEGREE,
                                           simplify_boundary=False)
    result.labels = labels
    result.shapes = list(simplified)
    result.points_after = int(sum(shapely.get_num_coordinates(simplified)))
    result.pairs = sharing(result.shapes)
    result.overlaps = merge_rows(result.overlaps)
    result.fills = merge_rows(result.fills)
    return result


def sharing(shapes: list) -> list[tuple[int, int]]:
    """The pairs of shapes that share a line, not only a point: neighbours, for the colour numbers (AD-19)."""
    if len(shapes) < 2:
        return []
    arr = np.array(shapes, dtype=object)
    a, b = shapely.STRtree(arr).query(arr, predicate="intersects")
    keep = a < b
    out = []
    for i, j in zip(a[keep].tolist(), b[keep].tolist()):
        if shapely.intersection(arr[i].boundary, arr[j].boundary).length > 0:
            out.append((i, j))
    return out


def merge_rows(rows: list[tuple]) -> list[tuple]:
    """Rows whose last value is km2, added together where the rest is the same."""
    out: dict[tuple, float] = defaultdict(float)
    for r in rows:
        out[r[:-1]] += r[-1]
    return [(*k, v) for k, v in sorted(out.items(), key=lambda kv: str(kv[0]))]


def polar_cap(bounds, land_south: float):
    """The land south of where the land polygons stop, inside a grid square (AD-15): Antarctica's
    ice sheet is land all the way to the South Pole."""
    w, s, e, n = bounds
    if s >= land_south:
        return None
    return shapely.box(w, s, e, min(n, land_south))
