"""Stage "continents": the seven continents, built from the countries' land (P3-T1e, DAT-12, DP174, DP88).

The settings file, mapdata/config/continents.yaml, gives each continent an
area that says roughly where it is, in order: a place in two areas belongs to
the first, and a place in none to the continent marked rest. Together they
cover the world once, so no land is in no continent and none in two.

* A country goes whole to one continent. Its parts are put in groups: parts
  within distant_km of each other are in one group. The group with the
  country's largest part is its main group, and goes to the continent whose
  area holds most of its land. Every other group goes to the continent whose
  area holds most of that group's land: "by where they are" (DP88), so the
  Canary Islands are in Africa and Hawaii in Oceania, but Corsica stays with
  France.
* A country named in "split", such as Russia, is cut along the edges of the
  areas, which for these countries are the dividing lines: the Urals, the Ural
  River and so on. A part cut off that is smaller than split_min_km2 stays with
  its part, so a dividing line drawn a little off a coast makes no sliver.

The stage keeps every feature of the stage before and adds a feature for each
continent, in the layer "continents". Its shape is the union of its countries'
land, so it follows the coast.
"""
from __future__ import annotations

import math
import shutil
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely
import yaml

from mapdata.paths import CONFIG_DIR
from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped

LAYER = "continents"
SETTINGS = "continents.yaml"
KM_PER_DEGREE = 111.32
CELL = 0.5            # degrees: the cells used to find which parts of a country are near each other
WORLD = shapely.box(-180.0, -90.0, 180.0, 90.0)


# The areas ---------------------------------------------------------------------------------------

def load_settings(path: Path | None = None) -> dict:
    path = path or CONFIG_DIR / SETTINGS
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    conts = data.get("continents") or []
    if not conts:
        raise BuildStopped(f"{path.name} lists no continents.")
    rest = [c for c in conts if c.get("rest")]
    if len(rest) != 1:
        raise BuildStopped(f"{path.name} must mark exactly one continent with rest: true, for the places no area "
                           f"holds. It marks {len(rest)}.")
    for c in conts:
        for needed in ("id", "name"):
            if not c.get(needed):
                raise BuildStopped(f"A continent in {path.name} has no {needed}.")
        if not c.get("rest") and not c.get("areas"):
            raise BuildStopped(f"The continent {c['name']} in {path.name} has no areas.")
    return data


def fold(ring: list) -> shapely.Geometry:
    """A polygon whose longitudes may run past 180 or -180, folded back into -180 to 180."""
    poly = shapely.make_valid(shapely.Polygon(ring))
    out = [shapely.intersection(poly, WORLD)]
    for shift in (360.0, -360.0):
        moved = shapely.intersection(shapely.transform(poly, lambda xy, s=shift: xy - [s, 0.0]), WORLD)
        if not moved.is_empty:
            out.append(moved)
    return shapely.union_all(out)


def expand(points: list, lines: dict) -> list:
    """An area's outline, with each named line, such as ural-river, put in its place."""
    out = []
    for p in points:
        if isinstance(p, str):
            if p not in lines:
                raise BuildStopped(f"A continent's area names the line {p}, which the continents settings do not "
                                   "give under lines.")
            out.extend(lines[p])
        else:
            out.append(p)
    return out


def zones(data: dict) -> list[tuple[dict, shapely.Geometry]]:
    """Each continent with the part of the world that is its: its areas, less those of the continents before
    it; and for the continent marked rest, all that no area holds. They cover the world once."""
    lines = data.get("lines") or {}
    out, taken = [], shapely.Polygon()
    rest = None
    for c in data["continents"]:
        if c.get("rest"):
            rest = c
            continue
        raw = shapely.union_all([fold(expand(a, lines)) for a in c["areas"]])
        out.append((c, shapely.difference(raw, taken)))
        taken = shapely.union(taken, raw)
    out.append((rest, shapely.difference(WORLD, taken)))
    return out


# Assigning land ------------------------------------------------------------------------------------

def km2(g) -> float:
    """A shape's area in km2, roughly: enough to compare shares and sizes."""
    if g is None or g.is_empty:
        return 0.0
    parts = shapely.get_parts(g)
    lat = np.radians(shapely.get_coordinates(shapely.centroid(parts))[:, 1])
    return float((shapely.area(parts) * np.cos(lat)).sum() * KM_PER_DEGREE ** 2)


def shares(parts: np.ndarray, zone_geoms: list, tree) -> list[dict[int, float]]:
    """For each part, the km2 of it in each continent's zone. A part inside one zone is measured once."""
    out = [dict() for _ in range(len(parts))]
    pi, zi = tree.query(parts, predicate="intersects")
    by_part: dict[int, list[int]] = defaultdict(list)
    for p, z in zip(pi.tolist(), zi.tolist()):
        by_part[p].append(z)
    for p in range(len(parts)):
        zs = by_part.get(p)
        if not zs:   # outside every zone: cannot happen, as they cover the world, but measured the safe way
            zs = list(range(len(zone_geoms)))
        if len(zs) == 1:
            out[p][zs[0]] = km2(parts[p])
            continue
        for z in zs:
            a = km2(shapely.intersection(parts[p], zone_geoms[z]))
            if a > 0:
                out[p][z] = a
        if not out[p]:   # a part on an edge, with no area either side: by its point
            pt = shapely.point_on_surface(parts[p])
            z = next((z for z in zs if zone_geoms[z].covers(pt)), zs[0])
            out[p][z] = km2(parts[p])
    return out


def groups(parts: np.ndarray, distant_km: float) -> list:
    """The group of each part: parts within about distant_km of each other, through the parts between, are in
    one group. The land is marked on cells of CELL degrees, and occupied cells near each other are joined."""
    cells_of: list[set[tuple[int, int]]] = []
    ncol = int(round(360 / CELL))
    for g in parts:
        x0, y0, x1, y1 = g.bounds
        c0, c1 = int((x0 + 180) // CELL), int((x1 + 180) // CELL)
        r0, r1 = int((y0 + 90) // CELL), int((y1 + 90) // CELL)
        if c0 == c1 and r0 == r1:
            cells_of.append({(r0, c0 % ncol)})
            continue
        shapely.prepare(g)
        boxes = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
        hit = g.intersects(np.array([shapely.box(c * CELL - 180, r * CELL - 90, (c + 1) * CELL - 180,
                                                 (r + 1) * CELL - 90) for r, c in boxes]))
        found = {(r, c % ncol) for (r, c), h in zip(boxes, np.atleast_1d(hit)) if h}
        cells_of.append(found or {(r0, c0 % ncol)})
    parent: dict = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    occupied = set().union(*cells_of) if cells_of else set()
    for cells in cells_of:   # the cells of one part are one group
        first = next(iter(cells))
        for c in cells:
            parent[find(c)] = find(first)
    dr = int(math.ceil(distant_km / (CELL * KM_PER_DEGREE)))
    for (r, c) in occupied:
        lat = (r + 0.5) * CELL - 90
        cos = max(math.cos(math.radians(lat)), 1e-3)
        dc = min(ncol // 2, int(math.ceil(distant_km / (CELL * KM_PER_DEGREE * cos))))
        for rr in range(max(0, r - dr), r + dr + 1):
            for cc in range(c - dc, c + dc + 1):
                other = (rr, cc % ncol)
                if other in occupied and other != (r, c):
                    parent[find(other)] = find((r, c))
    return [find(next(iter(cells))) for cells in cells_of]


def assign_country(record: dict, geom, zone_geoms: list, tree, split: bool, distant_km: float,
                   split_min_km2: float) -> list[tuple[int, object]]:
    """The country's land, as (zone, shape) pairs."""
    parts = shapely.get_parts(geom)
    parts = parts[~shapely.is_empty(parts)]
    if not len(parts):
        return []
    sh = shares(parts, zone_geoms, tree)
    out = []
    if split:
        for p, s in zip(parts, sh):
            if len(s) == 1:
                out.append((next(iter(s)), p))
                continue
            main = max(s, key=lambda z: (s[z], -z))
            others = [z for z, a in s.items() if z != main and a >= split_min_km2]
            if not others:
                out.append((main, p))
                continue
            cut = []
            for z in sorted(others):
                piece = shapely.intersection(p, zone_geoms[z])
                cut.append(piece)
                out.append((z, piece))
            out.append((main, shapely.difference(p, shapely.union_all(cut))))
        return out
    gid = groups(parts, distant_km) if len(parts) > 1 else [0]
    by_group: dict = defaultdict(lambda: defaultdict(float))
    for g, s in zip(gid, sh):
        for z, a in s.items():
            by_group[g][z] += a
    zone_of_group = {g: max(t, key=lambda z: (t[z], -z)) for g, t in by_group.items()}
    for g, p in zip(gid, parts):
        out.append((zone_of_group[g], p))
    return out


def continent_shapes(records: list[dict], geoms: list, data: dict, say=print, log=print):
    """Each continent's land, from the countries layer. Returns [(continent, shape)] in the settings' order,
    the continents with no land left out, and the report's lines."""
    zs = zones(data)
    zone_geoms = [g for _c, g in zs]
    tree = shapely.STRtree(zone_geoms)
    split_ids = {s["wikidata"] for s in data.get("split") or []}
    distant = float(data.get("distant_km", 300))
    split_min = float(data.get("split_min_km2", 100))
    pieces: dict[int, list] = defaultdict(list)
    for r, g in zip(records, geoms):
        if r.get("layer") != "countries" or g is None or g.is_empty:
            continue
        got = assign_country(r, g, zone_geoms, tree, r.get("wikidata") in split_ids, distant, split_min)
        held: dict[int, float] = defaultdict(float)
        for z, piece in got:
            if piece is not None and not piece.is_empty:
                pieces[z].append(piece)
                held[z] += km2(piece)
        if len(held) > 1:
            total = sum(held.values())
            log(f"{r['name']}: " + "; ".join(f"{zs[z][0]['name']} {a:,.0f} km2 ({100 * a / total:.1f}%)"
                                            for z, a in sorted(held.items(), key=lambda kv: -kv[1])) + ".")
    out = []
    for z, (c, _zone) in enumerate(zs):
        if not pieces.get(z):
            continue
        t = time.perf_counter()
        shape = union_land(pieces[z])
        say(f"{c['name']}: {km2(shape):,.0f} km2, from {len(pieces[z]):,} parts of countries, joined in "
            f"{time.perf_counter() - t:.0f} seconds.")
        out.append((c, shape))
    return out


def union_land(pieces: list):
    """The union of countries' land, which meet edge to edge: the quick union made for that, checked, and
    the general union when its result is not valid."""
    polys = shapely.get_parts(np.array(pieces, dtype=object))
    polys = polys[shapely.get_type_id(polys) == 3]
    try:
        g = shapely.coverage_union_all(polys)
        if g.is_valid:
            return g
    except shapely.errors.GEOSException:
        pass
    return shapely.make_valid(shapely.union_all(polys))


# The stage ---------------------------------------------------------------------------------------

def fingerprint_extra(stage: dict) -> dict:
    """The continents settings are part of what the stage reads, as the counties record is for osm-areas."""
    return {"continents": (CONFIG_DIR / SETTINGS).read_text(encoding="utf-8")}


def run(ctx) -> None:
    if LAYER not in ctx.pack.layers:
        raise BuildStopped("The continents stage writes the layer continents, which the pack's layer groups do not "
                           "define. Add the layer, or take the stage out.")
    if ctx.previous is None:
        raise BuildStopped("The continents stage needs the countries from the stages before it.")
    data = load_settings()
    t = time.perf_counter()
    records, geoms = features.load_layers(ctx.previous, {"countries"})
    ctx.progress.line(f"Read {len(records):,} countries and other land in {time.perf_counter() - t:.0f} seconds.")
    made = continent_shapes(records, geoms, data, ctx.progress.line, ctx.progress.log)
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(ctx.previous / name, ctx.claim(ctx.folder / name))
    new_records = []
    for c, shape in made:
        rec = {"id": c["id"], "layer": LAYER, "name": c["name"], "type": "continent"}
        if c.get("wikidata"):
            rec["wikidata"] = c["wikidata"]
        new_records.append(rec)
    features.append(ctx.folder, new_records, [shapely.to_wkb(s) for _c, s in made])
    ctx.progress.line(f"Continents: {len(made)}, in {time.perf_counter() - t:.0f} seconds. The log lists each "
                      "country with land in more than one.")
