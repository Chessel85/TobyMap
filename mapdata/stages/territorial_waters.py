"""Stage "territorial-waters": each country's territorial waters, a layer of their own (P4-T12a, DAT-15, DAT-3).

OpenStreetMap draws a country's area out to sea, to the edge of its territorial waters, 12 nautical miles from
its coast. The build cuts the countries to the coast (AD-15), so that sea part is not in the Countries layer. This
stage keeps it as a layer of its own: a country's territorial waters are its area as OpenStreetMap has it, the
outline as read by the osm-areas stage, simplified to tolerance_m, less all the land as the pack draws it, the
areas of the land layer (the countries) as the join stage made them (DP220, physical.DrawnLand). So the inner edge
of the territorial waters is exactly the drawn coast, and at sea you are never in a country.

* The countries are those of the land layer of the stage before. Each that has an outline in the outlines stage,
  by its id, gets territorial waters, named by the name setting: "Territorial waters of France". The country's
  name is put as the application says a name after "of" (mapcore.describe.words.name_after_of), so "Territorial
  waters of the United Kingdom", with "the" before a name that has one of the words in templates.yaml, details,
  the_words; those words are in the stage's fingerprint. OpenStreetMap gives no adjective for a country, such as
  French, so the name says "of" the country. A country with
  no sea part has none, nor has land the build named itself, such as a condominium or unclaimed land, which has
  no outline.
* A country OpenStreetMap has whole, split into country units (DP86), such as the whole French state, is no
  longer in the land layer. Its outline, less the outlines of its units, gives the waters of what is left, such as
  New Caledonia's, named after the whole country: "Territorial waters of France".
* Two countries' outlines can overlap at sea, where their claims overlap. Each keeps its own waters, so the
  areas of the layer overlap there; the log lists each pair. The layer is therefore not simplified as one
  coverage when the pack is written (its fill is none in the layer file).
* Parts smaller than min_km2 are left out: slivers where an outline and the drawn coast differ a little.

The sea is cut from the outline a box at a time: a box holding more than most_points points of land is halved,
again and again, so a long coast such as Norway's is never cut in one step.

Settings: outlines (the stage whose outlines are used, osm-areas), land_layer (countries), layer
(territorial-waters), name ("Territorial waters of {country}"), tolerance_m (100, the squares' own), min_km2
(0.1), most_points (20000), box. The features of the stage before are kept, and the new ones added after them.
"""
from __future__ import annotations

import json
import math
import shutil
import time

import numpy as np
import shapely

from mapcore.describe import templates
from mapcore.describe.words import name_after_of
from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages.physical import DrawnLand, polygonal, union_land

METRES_PER_DEGREE = 111_320.0
KM_PER_DEGREE = 111.32
TYPE = "territorial waters"
ID_PREFIX = "territorial-waters:"
NAME = "Territorial waters of {country}"
OUTLINE_KINDS = ("country", "unit")   # the osm-areas records that are countries or country units (DP86)
SMALLEST_DEG = 0.05   # a box is never halved below this, in degrees


def fingerprint_extra(stage: dict) -> dict:
    """The words that put "the" before a country's name, as the names are made with them."""
    return {"the_words": sorted(templates()["details"]["the_words"])}


def name_of(pattern: str, country: str) -> str:
    """The waters' name: "Territorial waters of France", "Territorial waters of the United Kingdom"."""
    return pattern.format(country=name_after_of(country))


def load_outlines(folder, wanted) -> tuple[dict[str, dict], dict[str, object]]:
    """The records and outlines, by id, of the records in a stage's folder for which wanted(record) is true,
    reading only their shapes."""
    data = json.loads((folder / "features.json").read_text(encoding="utf-8"))
    records, shapes = {}, {}
    with open(folder / "shapes.wkb", "rb") as f:
        for r, (a, n) in zip(data["records"], data["shapes"]):
            if wanted(r):
                f.seek(a)
                records[r["id"]] = r
                shapes[r["id"]] = shapely.from_wkb(f.read(n))
    return records, shapes


def rough_km2(g) -> float:
    """An area's size in square kilometres, near enough to tell a sliver from the sea."""
    if g is None or g.is_empty:
        return 0.0
    lat = shapely.centroid(g).y
    return float(g.area) * KM_PER_DEGREE ** 2 * math.cos(math.radians(lat))


def drop_small(g, min_km2: float):
    """The parts of a shape of at least min_km2; None when none is."""
    if g is None:
        return None
    parts = [p for p in shapely.get_parts(g) if rough_km2(p) >= min_km2]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)


def sea_of(shape, land: DrawnLand, most_points: int = 20000):
    """The shape less the land: the land near it is taken out a box at a time, each box halved while it holds
    more than most_points points of land. The boxes meet exactly along the lines they were cut on, so the parts
    join up again exactly. None when no sea is left."""
    out = []
    stack = [shape]
    while stack:
        g = stack.pop()
        if g is None or g.is_empty:
            continue
        near = land.within(g)
        if not len(near):
            out.extend(shapely.get_parts(g))
            continue
        x0, y0, x1, y1 = g.bounds
        if int(shapely.get_num_coordinates(near).sum()) > most_points and max(x1 - x0, y1 - y0) > SMALLEST_DEG:
            if x1 - x0 >= y1 - y0:
                m = (x0 + x1) / 2
                halves = ((x0, y0, m, y1), (m, y0, x1, y1))
            else:
                m = (y0 + y1) / 2
                halves = ((x0, y0, x1, m), (x0, m, x1, y1))
            stack.extend(polygonal(shapely.clip_by_rect(g, *h)) for h in halves)
            continue
        ground = union_land(list(near))
        left = polygonal(shapely.difference(g, ground)) if ground is not None else g
        if left is not None:
            out.extend(p for p in shapely.get_parts(left) if not p.is_empty)
    if not out:
        return None
    arr = np.array(out, dtype=object)
    try:
        joined = shapely.coverage_union_all(arr)
        if not joined.is_valid:
            raise ValueError("not a coverage")
    except (shapely.errors.GEOSException, ValueError):
        joined = shapely.union_all(arr)
    return polygonal(joined)


def waters(outline, land: DrawnLand, box, tolerance_m: float, min_km2: float, most_points: int = 20000):
    """A country's territorial waters: its outline simplified to tolerance_m, cut to the box if any, less the
    land. The land is not simplified again, so the inner edge is the drawn coast. None when there is no sea."""
    tol = tolerance_m / METRES_PER_DEGREE
    g = polygonal(shapely.simplify(outline, tol, preserve_topology=True)) if tol else polygonal(outline)
    if g is not None and box:
        g = polygonal(shapely.clip_by_rect(g, *box))
    if g is None:
        return None
    sea = sea_of(g, land, most_points)
    if sea is None:
        return None
    sea = polygonal(shapely.set_precision(sea, 1e-7))
    return drop_small(sea, min_km2)


def overlapping(records: list[dict], geoms: list, min_km2: float) -> list[tuple[str, str, float]]:
    """Each pair of areas that overlap by min_km2 or more: (name, name, square kilometres)."""
    if len(geoms) < 2:
        return []
    arr = np.array(geoms, dtype=object)
    tree = shapely.STRtree(arr)
    left, right = tree.query(arr, predicate="intersects")
    out = []
    for a, b in zip(left, right):
        if a < b:
            km2 = rough_km2(polygonal(shapely.intersection(arr[a], arr[b])))
            if km2 >= min_km2:
                out.append((records[a]["name"], records[b]["name"], km2))
    return out


def run(ctx) -> None:
    s = ctx.settings
    t0 = time.perf_counter()
    land_layer = s.get("land_layer", "countries")
    layer = s.get("layer", "territorial-waters")
    if layer not in ctx.pack.layers:
        raise BuildStopped(f"The territorial-waters stage writes to the layer {layer}, which the pack's layer "
                           "groups do not define. Add the layer, or correct the stage's settings.")
    outlines_stage = s.get("outlines", "osm-areas")
    folder = (getattr(ctx, "earlier", None) or {}).get(outlines_stage)
    if folder is None or not (folder / "features.json").is_file():
        raise BuildStopped(f"The territorial-waters stage needs the countries as read, from the {outlines_stage} "
                           "stage, which this pack has not run before it. Put the stage after it, or correct "
                           "its outlines setting.")
    countries, geoms = features.load_layers(ctx.previous, {land_layer})
    if not countries:
        raise BuildStopped(f"The territorial-waters stage takes the land of the layer {land_layer} out of the "
                           "countries, which the stage before has none of. Put the stage after the join stage, "
                           "or correct its land_layer setting.")
    land = DrawnLand(geoms)
    del geoms
    held = [r["id"] for r in countries]
    known = set(held)
    read, outlines = load_outlines(folder, lambda r: r.get("kind") in OUTLINE_KINDS)
    ctx.progress.line(f"The land of the layer {land_layer} made ready, and {len(outlines):,} outlines read from "
                      f"the {outlines_stage} stage, in {time.perf_counter() - t0:.0f} seconds.")
    # Each country of the layer, in its order, by its own outline; then each whole country no longer in it, by
    # what is left of its outline once its units' are taken out, in the order of the ids.
    jobs = [(cid, r["name"], outlines.get(cid)) for cid, r in zip(held, countries)]
    for cid in sorted(i for i, r in read.items() if r.get("kind") == "country" and i not in known):
        units = [outlines[u] for u, r in read.items() if r.get("country") == cid and u in outlines]
        rest = outlines[cid]
        if units:
            rest = polygonal(shapely.difference(rest, shapely.union_all(units)))
        jobs.append((cid, read[cid]["name"], rest))
    box = s.get("box")
    tol = float(s.get("tolerance_m", 100))
    min_km2 = float(s.get("min_km2", 0.1))
    most = int(s.get("most_points", 20000))
    pattern = s.get("name", NAME)
    new_records, new_geoms = [], []
    none = 0
    for cid, name, outline in jobs:
        g = waters(outline, land, box, tol, min_km2, most) if outline is not None else None
        if g is None:
            none += 1
            continue
        new_records.append({"id": f"{ID_PREFIX}{cid}", "layer": layer, "name": name_of(pattern, name),
                            "type": TYPE, "country": cid})
        new_geoms.append(g)
        ctx.progress.log(f"{new_records[-1]['name']}: {rough_km2(g):,.0f} square kilometres, "
                         f"{len(shapely.get_parts(g)):,} parts, {shapely.get_num_coordinates(g):,} points.")
    pairs = overlapping(new_records, new_geoms, min_km2)
    for a, b, km2 in pairs:
        ctx.progress.log(f"Overlapping territorial waters: {a} and {b}, {km2:,.1f} square kilometres.")
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(ctx.previous / name, ctx.claim(ctx.folder / name))
    features.append(ctx.folder, new_records, [shapely.to_wkb(g) for g in new_geoms])
    points = sum(int(shapely.get_num_coordinates(g)) for g in new_geoms)
    ctx.progress.line(f"Territorial waters: {len(new_records):,} areas, {points:,} points, of {len(jobs):,} "
                      f"countries looked at; {none:,} had no sea part. {len(pairs):,} pairs overlap at sea. "
                      f"In {time.perf_counter() - t0:.0f} seconds.")
