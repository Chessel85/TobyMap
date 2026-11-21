"""Stage "coverage": a regional pack's coverage, its covered pack tiles, and every feature cut to them (P4-T1a).

A regional pack (design docs/plan/p4-t1-design.md, section 2.3) answers, inside its coverage, instead of the world
pack. Its coverage is worked out once, after the join (or the samples, for the test region):

1. The land inside the region outline: the land of the countries layer of the stage before, as the countries draw
   it, inside the outline. The outline is Geofabrik's .poly file (or several, joined into one), read here with the
   standard library and Shapely. It only chooses the pack tiles; no shape of it goes into the pack.
2. A pack tile at the coverage's tile level (setting tile_level) is covered if it holds any of that land, of any
   size. Pack tiles of open sea are not covered: the world pack answers there.
3. Four covered pack tiles that make one pack tile at the level above are written as that one, up to tile level
   merge_from_level, so Great Britain's coverage is a few thousand entries.
4. The coverage shape is the union of the covered pack tiles. Every feature of the stage before is cut to it, and
   one left with less than 99.9 percent of its area or length is marked partial. One left with nothing is dropped.

coverage.json, in the stage's folder, holds the tiles, the tile level, the coverage shape in well-known binary, and
the outline's names. The writing stage puts the coverage into the manifest (pack-format.md), and every later
stage that reads OpenStreetMap cuts its shapes to it (mapdata.stages.osm_source).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely

from mapcore.packs.tiles import MAX_TILE_LEVEL, in_grid, tile_box
from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages.clip import polygonal

COVERAGE_FILE = "coverage.json"
TILE_LEVEL = 12          # about 6 by 5 kilometres in Great Britain
MERGE_FROM_LEVEL = 6     # four covered pack tiles are written as one, up to this level
PARTIAL_SHARE = 0.999    # a feature cut to less than this share of its area or length is partial
READING_LEVEL = 8        # the reading boxes of osm_source: pack tiles at tile level 8, about 1.4 by 0.7 degrees
DRAW_BELOW_KM = 250      # the manifest's draw_below_km when the pack's coverage does not give one


# The .poly file -------------------------------------------------------------------------------------------------

def read_poly(text: str, where: str = "the outline") -> tuple[str, object]:
    """The name and shape of a .poly file (Osmosis's polygon format, as Geofabrik writes it): a name line, then
    sections, each a name line, "lon lat" lines and END, a section whose name starts with "!" being a hole; then
    END. Returns (name, Polygon or MultiPolygon in degrees)."""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        raise BuildStopped(f"{where} is empty: a .poly file starts with a name line.")
    name = lines[0]
    outers, holes = [], []
    i = 1
    while i < len(lines):
        head = lines[i]
        if head == "END":
            break
        hole = head.startswith("!")
        i += 1
        ring = []
        while i < len(lines) and lines[i] != "END":
            parts = lines[i].split()
            try:
                ring.append((float(parts[0]), float(parts[1])))
            except (ValueError, IndexError):
                raise BuildStopped(f"{where} has a line that is not a longitude and latitude, in its section "
                                   f"{head}: {lines[i]}") from None
            i += 1
        if i >= len(lines):
            raise BuildStopped(f"{where} has a section, {head}, with no END line.")
        i += 1   # the section's END
        if len(ring) < 3:
            raise BuildStopped(f"{where} has a section, {head}, with fewer than three corners.")
        poly = shapely.make_valid(shapely.Polygon(ring))
        (holes if hole else outers).append(poly)
    if not outers:
        raise BuildStopped(f"{where} has no section that is not a hole, so it outlines nothing.")
    shape = shapely.union_all(outers)
    if holes:
        shape = shapely.difference(shape, shapely.union_all(holes))
    shape = polygonal(shape)
    if shape.is_empty:
        raise BuildStopped(f"{where} outlines no area.")
    return name, shape


def read_outlines(paths: list[Path]) -> tuple[list[str], object]:
    """The names, and one shape joining every outline."""
    names, shapes = [], []
    for p in paths:
        name, shape = read_poly(Path(p).read_text(encoding="utf-8", errors="replace"), f"The outline {Path(p).name}")
        names.append(name)
        shapes.append(shape)
    return names, polygonal(shapely.union_all(shapes))


# Pack tiles -----------------------------------------------------------------------------------------------------

def tile_text(level: int, x: int, y: int) -> str:
    return f"{level}/{x}/{y}"


def parse_tile(text: str) -> tuple[int, int, int]:
    """"level/x/y" as three whole numbers; ValueError if it is not one."""
    parts = str(text).split("/")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"{text} is not a pack tile written as level/x/y")
    return int(parts[0]), int(parts[1]), int(parts[2])


def tiles_in_box(box, level: int) -> list[tuple[int, int]]:
    """The pack tiles at a level that a box in degrees [west, south, east, north] meets."""
    n = 2 ** level
    w, s, e, nn = box
    x0 = max(0, int((w + 180) / 360 * n))
    x1 = min(n - 1, int((e + 180) / 360 * n))
    y0 = max(0, int((s + 90) / 180 * n))
    y1 = min(n - 1, int((nn + 90) / 180 * n))
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def covered_tiles(land: list, outline, level: int) -> set[tuple[int, int]]:
    """The pack tiles at `level` that hold land inside the outline, of any size. `land` is a list of land shapes
    (the countries); a pack tile that only touches land along an edge or at a corner is not covered."""
    cells = tiles_in_box(outline.bounds, level)
    boxes = np.array([shapely.box(*tile_box(level, x, y)) for x, y in cells], dtype=object)
    if not len(boxes):
        return set()
    shapely.prepare(outline)
    near = shapely.intersects(outline, boxes) & ~shapely.touches(outline, boxes)
    cells = [c for c, k in zip(cells, near) if k]
    inside = shapely.intersection(boxes[near], outline)   # each pack tile's part inside the outline
    if not len(inside):
        return set()
    tree = shapely.STRtree(inside)
    out: set[tuple[int, int]] = set()
    for g in land:
        if g is None or g.is_empty:
            continue
        for part in shapely.get_parts(g):
            if not part.geom_type.endswith("Polygon"):
                continue
            idx = [i for i in tree.query(part).tolist() if cells[i] not in out]
            if not idx:
                continue
            shapely.prepare(part)
            hit = shapely.intersects(part, inside[idx]) & ~shapely.touches(part, inside[idx])
            out.update(cells[i] for i, h in zip(idx, hit) if h)
            shapely.destroy_prepared(part)
    return out


def merge_tiles(cells: set[tuple[int, int]], level: int, merge_from_level: int) -> list[tuple[int, int, int]]:
    """Covered pack tiles as (level, x, y), four that make one at the level above written as that one, up to
    merge_from_level. Sorted by level, then x, then y."""
    out: list[tuple[int, int, int]] = []
    current = set(cells)
    for lv in range(level, merge_from_level, -1):
        parents: dict[tuple[int, int], int] = {}
        for x, y in current:
            parents[(x // 2, y // 2)] = parents.get((x // 2, y // 2), 0) + 1
        whole = {p for p, k in parents.items() if k == 4}
        out += [(lv, x, y) for x, y in current if (x // 2, y // 2) not in whole]
        current = whole
    out += [(min(level, merge_from_level), x, y) for x, y in current]
    return sorted(out)


def coverage_shape(tiles: list[tuple[int, int, int]]):
    """The union of the covered pack tiles. Shared edges are exact: tile_box divides by powers of two."""
    return polygonal(shapely.union_all([shapely.box(*tile_box(*t)) for t in tiles]))


def reading_boxes(tiles: list[tuple[int, int, int]], level: int = READING_LEVEL) -> list[list[float]]:
    """The pack tiles at `level` that hold any covered pack tile, as boxes [west, south, east, north], in order:
    the reading boxes of osm_source, read one at a time."""
    cells: set[tuple[int, int]] = set()
    for lv, x, y in tiles:
        if lv >= level:
            cells.add((x >> (lv - level), y >> (lv - level)))
        else:
            k = 2 ** (level - lv)
            cells.update((x * k + i, y * k + j) for i in range(k) for j in range(k))
    return [list(tile_box(level, x, y)) for x, y in sorted(cells)]


# Cutting features to the coverage -------------------------------------------------------------------------------

def _size(g) -> float:
    if g is None or g.is_empty:
        return 0.0
    if g.geom_type.endswith("Polygon") or g.geom_type == "GeometryCollection":
        return float(shapely.area(g))
    if g.geom_type.endswith("LineString"):
        return float(shapely.length(g))
    return float(shapely.get_num_geometries(g))


def cut_one(g, shape):
    """A shape cut to the coverage shape (prepared is best), as the same kind of shape: (the cut shape or None if
    nothing is left, whether it is partial)."""
    if g is None or g.is_empty:
        return None, False
    if shapely.contains_properly(shape, g):
        return g, False
    kind = g.geom_type
    cut = shapely.intersection(g, shape)
    if kind.endswith("Polygon"):
        cut = polygonal(cut)
    elif kind.endswith("LineString"):
        lines = [p for p in shapely.get_parts(cut) if p.geom_type.endswith("LineString")]
        lines = [q for p in lines for q in shapely.get_parts(p)]
        cut = shapely.line_merge(shapely.MultiLineString(lines)) if lines else shapely.LineString()
        if kind == "MultiLineString" and cut.geom_type == "LineString":
            cut = shapely.MultiLineString([cut])
    elif kind.endswith("Point"):
        pts = [q for p in shapely.get_parts(cut) if p.geom_type.endswith("Point") for q in shapely.get_parts(p)]
        cut = shapely.MultiPoint(pts) if kind == "MultiPoint" or len(pts) > 1 else (pts[0] if pts else shapely.Point())
    if cut is None or cut.is_empty or _size(cut) == 0:
        return None, False
    before = _size(g)
    return cut, bool(before > 0 and _size(cut) < PARTIAL_SHARE * before)


def cut_to_coverage(records: list[dict], geoms: list, shape) -> tuple[list[dict], list, dict]:
    """Every feature cut to the coverage shape: one left with nothing is dropped, and one left with less than 99.9
    percent of its area, or of its length, gets partial: true (a point layer's feature: of its points). A feature
    already partial stays partial. Returns the records, the shapes, and counts: kept, partial, dropped."""
    shapely.prepare(shape)
    out_r, out_g = [], []
    counts = {"kept": 0, "partial": 0, "dropped": 0}
    for r, g in zip(records, geoms):
        cut, partial = cut_one(g, shape)
        if cut is None:
            counts["dropped"] += 1
            continue
        r = dict(r)
        if partial or r.get("partial"):
            r["partial"] = True
            counts["partial"] += 1
        out_r.append(r)
        out_g.append(cut)
        counts["kept"] += 1
    return out_r, out_g, counts


# The coverage record --------------------------------------------------------------------------------------------

@dataclass
class Coverage:
    region: str
    tile_level: int
    tiles: list[tuple[int, int, int]]
    shape: object
    outline_names: list[str]

    @property
    def tile_texts(self) -> list[str]:
        return [tile_text(*t) for t in self.tiles]


def save(folder: Path, cov: Coverage, claim=lambda p: p, extra: dict | None = None) -> Path:
    data = {"region": cov.region, "tile_level": cov.tile_level, "tiles": cov.tile_texts,
            "outline_names": cov.outline_names, "shape_wkb": shapely.to_wkb(cov.shape, hex=True), **(extra or {})}
    path = claim(Path(folder) / COVERAGE_FILE)
    path.write_text(json.dumps(data, indent=0, sort_keys=True), encoding="utf-8", newline="\n")
    return path


def load(where: Path) -> Coverage:
    """The coverage from a coverage stage's folder, or from its coverage.json."""
    path = Path(where)
    if path.is_dir():
        path = path / COVERAGE_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    return Coverage(data["region"], int(data["tile_level"]), [parse_tile(t) for t in data["tiles"]],
                    shapely.from_wkb(data["shape_wkb"]), list(data.get("outline_names") or []))


def check_manifest_coverage(cov: dict, layers: list[str]) -> list[str]:
    """What is wrong with a manifest's coverage member, in plain words; an empty list when nothing is. A world
    pack's is {"kind": "world"}; a regional pack's has region, tile_level, tiles (each "level/x/y" in the grid, at
    or above the tile level, sorted by level, x and y, none inside another), layers (each a layer the pack holds)
    and draw_below_km (pack-format.md)."""
    if not isinstance(cov, dict):
        return ["the coverage is not a set of settings"]
    if cov.get("kind") == "world":
        return []
    if cov.get("kind") != "region":
        return [f"the coverage's kind is {cov.get('kind')}; it must be world or region"]
    problems = []
    level = cov.get("tile_level")
    if not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= MAX_TILE_LEVEL:
        problems.append(f"the tile level, {level}, is not a whole number from 0 to {MAX_TILE_LEVEL}")
        level = MAX_TILE_LEVEL
    if not str(cov.get("region") or "").strip():
        problems.append("it has no region name")
    tiles = cov.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        problems.append("it has no covered pack tiles")
        tiles = []
    parsed = []
    for t in tiles:
        try:
            lv, x, y = parse_tile(t)
        except ValueError as e:
            problems.append(str(e))
            continue
        if not in_grid(lv, x, y) or lv > level:
            problems.append(f"the pack tile {t} is not in the grid at or above tile level {level}")
            continue
        parsed.append((lv, x, y))
    if parsed != sorted(parsed):
        problems.append("the pack tiles are not sorted by level, then x, then y")
    held = set(parsed)
    if len(held) != len(parsed):
        problems.append("a pack tile is given twice")
    for lv, x, y in parsed:
        for up in range(1, lv + 1):
            if (lv - up, x >> up, y >> up) in held:
                problems.append(f"the pack tile {tile_text(lv, x, y)} is inside {tile_text(lv - up, x >> up, y >> up)}, "
                                "which is also given")
                break
    named = cov.get("layers")
    if not isinstance(named, list):
        problems.append("it has no list of layers")
    else:
        unknown = [k for k in named if k not in layers]
        if unknown:
            problems.append(f"it names layers the pack does not hold: {', '.join(map(str, unknown))}")
    below = cov.get("draw_below_km")
    if isinstance(below, bool) or not isinstance(below, (int, float)) or below <= 0:
        problems.append(f"draw_below_km, {below}, is not a number above 0")
    return problems


def manifest_coverage(pack_coverage: dict, cov: Coverage | None, layers: list[str]) -> dict:
    """The manifest's coverage member (pack-format.md): a world pack's as its settings give it; a regional pack's
    from the coverage stage (cov), with the layers it holds features of. Stops the build if it is not right."""
    if (pack_coverage or {}).get("kind") != "region" or cov is None:
        # A world pack; or a trial with no coverage stage, such as trial-western-europe, whose {kind: region} is
        # written as before (it is not a regional pack: it has no covered pack tiles).
        return pack_coverage
    out = {"kind": "region", "region": pack_coverage.get("region") or cov.region, "tile_level": cov.tile_level,
           "tiles": cov.tile_texts, "layers": list(layers),
           "draw_below_km": pack_coverage.get("draw_below_km", DRAW_BELOW_KM)}
    problems = check_manifest_coverage(out, list(layers))
    if problems:
        raise BuildStopped("The pack's coverage cannot be written: " + "; ".join(problems) + ".")
    return out


# The stage ------------------------------------------------------------------------------------------------------

def outline_keys(settings: dict) -> list[str]:
    keys = ([settings["source"]] if settings.get("source") else []) + list(settings.get("sources") or [])
    if not keys:
        raise BuildStopped("The coverage stage needs the region outline: source, a .poly file's source key, or "
                           "sources, a list of them, joined into one outline.")
    return keys


def run(ctx) -> None:
    s = ctx.settings
    if (ctx.pack.data.get("coverage") or {}).get("kind") != "region":
        raise BuildStopped(f"The coverage stage is for a regional pack, but {ctx.pack.path.name} gives coverage "
                           "kind world. Give it coverage: {kind: region}, or take the coverage stage out.")
    level = int(s.get("tile_level", TILE_LEVEL))
    merge_from = int(s.get("merge_from_level", MERGE_FROM_LEVEL))
    land_layer = s.get("land_layer", "countries")
    if not 0 <= merge_from <= level <= MAX_TILE_LEVEL:
        raise BuildStopped(f"The coverage stage's tile_level ({level}) and merge_from_level ({merge_from}) must be "
                           f"whole numbers with merge_from_level no more than tile_level, and both {MAX_TILE_LEVEL} "
                           "or less.")
    paths = [ctx.source(k)[1] for k in outline_keys(s)]
    names, outline = read_outlines(paths)
    ctx.progress.line(f"Read the region outline: {', '.join(names)}, from {', '.join(p.name for p in paths)}.")
    records, geoms = features.load(ctx.previous)
    land = [g for r, g in zip(records, geoms) if r["layer"] == land_layer
            and shapely.intersects(g, shapely.box(*outline.bounds))]
    cells = covered_tiles(land, outline, level)
    if not cells:
        raise BuildStopped(f"No pack tile at tile level {level} holds land of the layer {land_layer} inside the "
                           "region outline. Check the outline, and that the stages before read the region.")
    tiles = merge_tiles(cells, level, merge_from)
    shape = coverage_shape(tiles)
    cov = Coverage(ctx.pack.data["coverage"].get("region") or ctx.pack.name, level, tiles, shape, names)
    km2 = float(shapely.area(shape))   # in square degrees, for the log only
    save(ctx.folder, cov, ctx.claim, {"merge_from_level": merge_from, "covered_at_tile_level": len(cells)})
    ctx.progress.line(f"Covered pack tiles: {len(cells):,} at tile level {level}, written as {len(tiles):,} "
                      f"(four that make one at the level above written as that one, up to tile level {merge_from}).")
    ctx.progress.log(f"The coverage spans {km2:.4f} square degrees; its reading boxes, at tile level {READING_LEVEL}: "
                     f"{len(reading_boxes(tiles))}.")
    out_r, out_g, counts = cut_to_coverage(records, geoms, shape)
    features.save(ctx.folder, out_r, out_g, ctx.claim)
    dropped = sorted({r["layer"] for r in records} - {r["layer"] for r in out_r})
    ctx.progress.line(f"Cut the features to the coverage: {counts['kept']:,} kept, of which {counts['partial']:,} "
                      f"partial, and {counts['dropped']:,} outside it left out."
                      + (f" Layers left with nothing: {', '.join(dropped)}." if dropped else ""))
    for r in out_r:
        if r.get("partial") and r["layer"] in ("countries", "regions", "oceans", "seas"):
            ctx.progress.log(f"Partial: {r.get('name')} ({r['id']}), layer {r['layer']}.")
