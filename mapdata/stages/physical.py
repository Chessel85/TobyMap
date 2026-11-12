"""Stage "physical": mountain ranges and physical regions, cut to the land (P3-T1f, DAT-5, DP169).

Two layers, each from a source of its own:

* ranges: the GMBA Mountain Inventory, version 2. GMBA keeps its ranges in a
  hierarchy, such as the Alps, the Western Alps and the Bernese Alps, each
  range an area holding the ranges below it. The stage keeps the hierarchy:
  each range names the range above it as its parent, so "Within" lists the
  Bernese Alps, then the Western Alps, then the Alps. Its support polygons,
  islands, archipelagos and continents are left out, as are its grouped
  sub-ranges above sub_range_min_level, such as "Southeast Europe".
* regions: Natural Earth's physical regions, such as deserts, plateaus,
  plains and peninsulas. Its classes are given in the settings with the type
  each is called; its other classes, such as islands and mountain ranges, are
  left out, as other layers hold them.

Each area is simplified to tolerance_m, then cut to the land with the OSM land
polygons (AD-15), as both sources draw their edges loosely along the coast: so
at sea you never hear that you are in a mountain range. A range left with no
land is left out. The layers' areas overlap each other, so they are not painted
on the map, and their drawing levels are made one area at a time.

The features of the stage before are kept, and the new ones added after them.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import land as landmod

METRES_PER_DEGREE = 111_320.0
GMBA_INNER = "GMBA_Inventory_v2.0_standard.shp"
# GMBA's kinds of feature that are mountains, and the type each is called.
GMBA_KINDS = {
    "Mountain range with well-recognized name": "mountain range",
    "Geographically-defined sub-range": "mountain range",
    "Highland or plateau": "highland",
    "Area dominated by a single large peak": "mountain",
    "Point Defined Range": "mountain range",
    "Escarpment / Canyon": "escarpment",
}
SUB_RANGE = "Geographically-defined sub-range"


def polygonal(g):
    if g is None or g.is_empty:
        return None
    g = shapely.make_valid(g) if not g.is_valid else g
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = [q for p in shapely.get_parts(g) for q in shapely.get_parts(p) if q.geom_type == "Polygon"]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)


def wikidata_of(url) -> str:
    """Q1286 from https://www.wikidata.org/wiki/Q1286."""
    text = str(url or "").strip().rstrip("/")
    q = text.rsplit("/", 1)[-1]
    return q if q.startswith("Q") and q[1:].isdigit() else ""


def gmba_ranges(zip_path: Path, box, min_level: int, sub_range_min_level: int,
                max_level: int = 99) -> tuple[list[dict], list]:
    """GMBA's ranges from min_level to max_level of its hierarchy, as records with their parent, and their
    shapes. Parents are the nearest range above in GMBA's hierarchy that is kept."""
    import pyogrio

    vsi = f"/vsizip/{zip_path.as_posix()}/{GMBA_INNER}"
    meta, _fids, wkb, fields = pyogrio.raw.read(vsi, return_fids=True, bbox=tuple(box) if box else None)
    col = {n: fields[i] for i, n in enumerate(meta["fields"])}
    shapes = shapely.from_wkb(wkb)
    keep: dict[str, tuple[dict, object]] = {}
    path_of: dict[str, list[str]] = {}
    for i in range(len(shapes)):
        kind = col["Feature"][i]
        level = int(col["Hier_Lvl"][i])
        if kind not in GMBA_KINDS or level < min_level or level > max_level:
            continue
        if kind == SUB_RANGE and level < sub_range_min_level:
            continue
        name = col["Name_EN"][i] or col["MapName"][i] or col["AsciiName"][i]
        if not name:
            continue
        gid = f"gmba:{int(col['GMBA_V2_ID'][i])}"
        rec = {"id": gid, "name": str(name), "type": GMBA_KINDS[kind], "level": level}
        q = wikidata_of(col["WikiDataUR"][i])
        if q:
            rec["wikidata"] = q
        keep[gid] = (rec, shapes[i])
        path_of[gid] = [f"gmba:{p.strip()}" for p in str(col["Path_ID"][i] or "").split(">") if p.strip()]
    for gid, (rec, _g) in keep.items():
        above = [p for p in path_of[gid] if p != gid and p in keep]
        if above:
            rec["parent"] = above[-1]
    ids = sorted(keep, key=lambda k: int(k.split(":")[1]))
    return [keep[k][0] for k in ids], [keep[k][1] for k in ids]


def natural_earth_regions(path: Path, box, classes: dict[str, str]) -> tuple[list[dict], list]:
    """Natural Earth's physical regions of the classes given, with the type each class is called."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    clip = shapely.box(*box) if box else None
    records, geoms = [], []
    for f in data["features"]:
        p = {k.lower(): v for k, v in f["properties"].items()}
        kind = classes.get(p.get("featurecla"))
        name = p.get("name_en") or p.get("name")
        if not kind or not name or not f.get("geometry"):
            continue
        g = shapely.geometry.shape(f["geometry"])
        if clip is not None and not g.intersects(clip):
            continue
        rec = {"id": f"ne:region:{p.get('ne_id')}", "name": str(name), "type": kind}
        if p.get("name") and p["name"] != name:
            rec["local_name"] = str(p["name"])
        if p.get("wikidataid"):
            rec["wikidata"] = str(p["wikidataid"])
        records.append(rec)
        geoms.append(g)
    order = sorted(range(len(records)), key=lambda i: records[i]["id"])
    return [records[i] for i in order], [geoms[i] for i in order]


class SimpleLand:
    """The land index's land tiles, each read once and simplified once to tolerance_m, then kept: ranges sit
    inside ranges, so the same land tiles are asked for many times, and their full detail is far finer than
    the base pack keeps. Cutting the North European Plain at full detail read 1,441 land tiles of 773,000
    points and took 11 seconds."""

    def __init__(self, index, tolerance_m: float):
        self.index = index
        self.tol = tolerance_m / METRES_PER_DEGREE
        self.kept: dict[int, object] = {}

    def within(self, mask) -> np.ndarray:
        parts = shapely.get_parts(mask)
        positions = self.index.touching([p.bounds for p in parts])
        new = np.array([p for p in positions.tolist() if p not in self.kept], dtype=np.intp)
        if len(new):
            read = self.index.read(new)
            if self.tol:
                read = shapely.simplify(read, self.tol, preserve_topology=True)
            for pos, g in zip(new.tolist(), read):
                self.kept[pos] = g
        tiles = np.array([self.kept[p] for p in positions.tolist()], dtype=object)
        if not len(tiles):
            return tiles
        tiles = tiles[~shapely.is_empty(tiles)]
        shapely.prepare(mask)
        return tiles[shapely.intersects(mask, tiles)]


def union_land(pieces: list):
    """The union of land tiles cut to an area. The land tiles never overlap, so the quick union made for that
    is used, and checked; the general union, about ten times slower, when its result is not valid."""
    arr = np.array([q for p in pieces for q in shapely.get_parts(p) if q.geom_type == "Polygon"], dtype=object)
    if not len(arr):
        return None
    try:
        g = shapely.coverage_union_all(arr)
        if g.is_valid:
            return polygonal(g)
    except shapely.errors.GEOSException:
        pass
    return polygonal(shapely.union_all(arr))


def cut_to_land(geoms: list, index, box, tolerance_m: float) -> list:
    """Each shape simplified, cut to the box, if any, then to the land. None where no land is left."""
    clip = shapely.box(*box) if box else None
    tol = tolerance_m / METRES_PER_DEGREE
    out = []
    for g in geoms:
        g = polygonal(shapely.simplify(g, tol, preserve_topology=False)) if tol else polygonal(g)
        if g is not None and clip is not None:
            g = polygonal(shapely.intersection(g, clip))
        if g is None:
            out.append(None)
            continue
        tiles = index.within(g)
        if not len(tiles):
            out.append(None)
            continue
        shapely.prepare(g)
        inside = shapely.contains_properly(g, tiles)
        pieces = list(tiles[inside]) + [p for p in shapely.intersection(tiles[~inside], g) if not p.is_empty]
        land = union_land(pieces) if pieces else None
        if land is not None and tol:   # the coast's own detail is far finer than the base pack needs
            land = polygonal(shapely.simplify(land, tol, preserve_topology=False))
        if land is not None:
            land = polygonal(shapely.set_precision(land, 1e-7))
        out.append(land)
    return out


def run(ctx) -> None:
    s = ctx.settings
    box = s.get("box")
    t0 = time.perf_counter()
    index = landmod.open_index(ctx.folders.downloads, ctx.folders.working, ctx.progress.log)
    lands: dict[float, SimpleLand] = {}
    new_records, new_geoms = [], []
    for part, reader in (("ranges", "gmba"), ("regions", "ne")):
        c = s.get(part)
        if not c:
            continue
        layer = c["layer"]
        if layer not in ctx.pack.layers:
            raise BuildStopped(f"The physical stage writes to the layer {layer}, which the pack's layer groups do "
                               "not define. Add the layer, or correct the stage's settings.")
        source, path = ctx.source(c["source"])
        t = time.perf_counter()
        if reader == "gmba":
            recs, geoms = gmba_ranges(path, box, int(c.get("min_level", 3)), int(c.get("sub_range_min_level", 4)),
                                      int(c.get("max_level", 99)))
        else:
            recs, geoms = natural_earth_regions(path, box, c.get("classes") or {})
        read_n = len(recs)
        tol = float(c.get("tolerance_m", 0))
        cut = cut_to_land(geoms, lands.setdefault(tol, SimpleLand(index, tol)), box, tol)
        kept = {r["id"] for r, g in zip(recs, cut) if g is not None}
        n = 0
        for r, g in zip(recs, cut):
            if g is None:
                continue
            if r.get("parent") and r["parent"] not in kept:
                r.pop("parent")
            r["layer"] = layer
            new_records.append(r)
            new_geoms.append(g)
            n += 1
        ctx.progress.line(f"The layer {layer}: {n:,} areas from {source.name}, of {read_n:,} read; {read_n - n:,} "
                          f"had no land, in {time.perf_counter() - t:.0f} seconds.")
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(ctx.previous / name, ctx.claim(ctx.folder / name))
    features.append(ctx.folder, new_records, [shapely.to_wkb(g) for g in new_geoms])
    ctx.progress.line(f"Physical features: {len(new_records):,} areas in {time.perf_counter() - t0:.0f} seconds.")
