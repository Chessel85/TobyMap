"""Stage "small-islands": every island under 1 km2 (P4-T1c, design docs/plan/p4-t1-design.md 3.6; DAT-1, DAT-3,
LOC-3, DP87).

The join makes the named islands, from OpenStreetMap's place=island and place=islet, and the unnamed ones of 1 km2
or more (its UNNAMED_ISLAND_KM2, which stays, as changing join.py would make the world's join run again). In a
regional pack this stage adds every other island, of any size:

1. The land is the countries layer of the stage before. Its parts that touch, across borders, are one landmass, as
   in the join.
2. A landmass is left as it is when it holds an area of the islands layer (the join named it), when it is 1 km2 or
   more (the join's business: an unnamed island it made, or a mainland), or when it reaches the coverage's edge
   (land the coverage cuts, such as a stretch of mainland at the edge, is not known to be an island).
3. Every other landmass is an island. Where an islet that OpenStreetMap has only as a point (the "island point"
   records of the osm-areas stage, which the join did not use) is on it, it takes that islet's name and id.
   Otherwise it is "Unnamed island" (the templates' details.unnamed.island), type "unnamed island" as the join's,
   with id "island:unnamed:" and its point (shapely's point on surface) rounded to 5 decimals, about a metre, so
   the id is the same each build (DMT-1).

The drawing's size rule leaves the small ones out at wide zooms, as for every area. The stage reads the stage before
only, and the osm-areas stage's records (not its shapes) for the island points. It writes small_islands.json: the
counts, and each island added with its size. The features of the stage before are kept, and the new ones added
after them.
"""
from __future__ import annotations

import json
import math
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import coverage as coveragemod

REPORT = "small_islands.json"
LARGEST_KM2 = 1.0           # the join's UNNAMED_ISLAND_KM2: a landmass this size or more is the join's
METRES_PER_DEGREE = 111_320.0
EDGE_DEG = 1e-7             # land this near the coverage's edge reaches it
TYPE = "unnamed island"


def unnamed_name() -> str:
    from mapcore.describe import templates

    return str(templates()["details"]["unnamed"]["island"])


def fingerprint_extra(stage: dict) -> dict:
    """The name of an unnamed island is written into the pack, so changing its words makes the stage run again."""
    return {"unnamed_island": unnamed_name()}


def km2_of(g) -> float:
    if g is None or g.is_empty:
        return 0.0
    lat = (g.bounds[1] + g.bounds[3]) / 2
    return float(g.area) * (METRES_PER_DEGREE / 1000) ** 2 * math.cos(math.radians(lat))


def landmasses(land: list) -> list[list]:
    """The land's parts, grouped: parts that touch are one landmass, a list of its parts. find_islands sorts what
    it makes by id, so the order here does not matter."""
    parts = [q for g in land if g is not None and not g.is_empty
             for q in shapely.get_parts(g) if q.geom_type == "Polygon" and not q.is_empty]
    if not parts:
        return []
    arr = np.empty(len(parts), dtype=object)
    arr[:] = parts
    ia, ib = shapely.STRtree(arr).query(arr, predicate="intersects")
    parent = list(range(len(parts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in zip(ia.tolist(), ib.tolist()):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)
    groups: dict[int, list] = defaultdict(list)
    for i, q in enumerate(parts):
        groups[find(i)].append(q)
    return list(groups.values())


def find_islands(land: list, islands: list, cover, points: list[dict], name: str,
                 used: set | None = None) -> tuple[list[tuple[dict, object]], dict]:
    """The islands the join did not make, as the module's notes say: (record, shape) pairs in id order, and the
    counts: unnamed, point, holds_island, large, cut. cover is the coverage shape; points the island point records
    (with "point": [lon, lat]); used, the ids already in the pack, so a point the join used is not used again."""
    used = used or set()
    counts = {"unnamed": 0, "point": 0, "holds_island": 0, "large": 0, "cut": 0}
    masses = landmasses(land)
    if not masses:
        return [], counts
    named = [g for g in islands if g is not None and not g.is_empty]
    tree = shapely.STRtree(np.array(named, dtype=object)) if named else None
    edge = cover.boundary
    shapely.prepare(edge)
    free_points = sorted((p for p in points if p.get("id") not in used and p.get("point")),
                         key=lambda p: (p.get("type") != "island", p.get("name") or "", p["id"]))
    taken: set = set()
    out: list[tuple[dict, object]] = []
    for mass in masses:
        if sum(km2_of(q) for q in mass) >= LARGEST_KM2:   # first, so a mainland is never joined or cut again
            counts["large"] += 1
            continue
        g = mass[0] if len(mass) == 1 else shapely.union_all(mass)
        if tree is not None and any(shapely.area(shapely.intersection(named[i], g)) > 0
                                    for i in tree.query(g, predicate="intersects").tolist()):
            counts["holds_island"] += 1
            continue
        if shapely.dwithin(g, edge, EDGE_DEG):
            counts["cut"] += 1
            continue
        here = [p for p in free_points if p["id"] not in taken and g.contains(shapely.Point(*p["point"]))]
        if here:
            p = here[0]
            taken.add(p["id"])
            r = {"id": p["id"], "layer": "islands", "name": p.get("name") or name,
                 "local_name": p.get("local_name") or p.get("name") or name, "type": p.get("type") or "island"}
            if p.get("wikidata"):
                r["wikidata"] = p["wikidata"]
            counts["point"] += 1
        else:
            at = shapely.point_on_surface(g)
            iid = f"island:unnamed:{at.y:.5f}:{at.x:.5f}"
            n = 2
            while iid in used or any(iid == o["id"] for o, _g in out):
                iid = f"island:unnamed:{at.y:.5f}:{at.x:.5f}:{n}"
                n += 1
            r = {"id": iid, "layer": "islands", "name": name, "type": TYPE}
            counts["unnamed"] += 1
        out.append((r, g))
    out.sort(key=lambda rg: rg[0]["id"])
    return out, counts


def island_points(folder: Path | None) -> list[dict]:
    """The osm-areas stage's island point records, read without their (empty) shapes."""
    if folder is None or not (Path(folder) / "features.json").is_file():
        return []
    data = json.loads((Path(folder) / "features.json").read_text(encoding="utf-8"))
    return [r for r in data["records"] if r.get("kind") == "island point" and r.get("point")]


def run(ctx) -> None:
    cov_folder = ctx.earlier.get("coverage")
    if cov_folder is None:
        raise BuildStopped("The small-islands stage finds islands within the coverage, but no coverage stage ran "
                           "before it. Put the coverage stage before it.")
    cov = coveragemod.load(cov_folder)
    land_r, land_g = features.load_layers(ctx.previous, {"countries", "islands"})
    data = json.loads((Path(ctx.previous) / "features.json").read_text(encoding="utf-8"))
    used = {r["id"] for r in data["records"]}
    land = [g for r, g in zip(land_r, land_g) if r["layer"] == "countries"]
    islands = [g for r, g in zip(land_r, land_g) if r["layer"] == "islands"]
    points = island_points(ctx.earlier.get("osm-areas"))
    found, counts = find_islands(land, islands, cov.shape, points, unnamed_name(), used)

    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(Path(ctx.previous) / name, ctx.claim(Path(ctx.folder) / name))
    features.append(ctx.folder, [r for r, _g in found], [shapely.to_wkb(g) for _r, g in found])
    report = {"counts": counts, "added": [{"id": r["id"], "name": r["name"], "km2": round(km2_of(g), 6)}
                                          for r, g in found]}
    ctx.claim(Path(ctx.folder) / REPORT).write_text(json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True),
                                                    encoding="utf-8", newline="\n")
    ctx.progress.line(f"Small islands, each under {LARGEST_KM2:g} km2: {counts['unnamed']:,} added as "
                      f"{unnamed_name()}, and {counts['point']:,} named from OpenStreetMap's island points. Left as "
                      f"they were: {counts['holds_island']:,} landmasses with an island already, "
                      f"{counts['large']:,} of {LARGEST_KM2:g} km2 or more, and {counts['cut']:,} that reach the "
                      f"coverage's edge. Each island added is listed in {REPORT}.")
    for r, g in found:
        at = shapely.point_on_surface(g)
        ctx.progress.log(f"Island added: {r['name']} ({r['id']}), {km2_of(g):.4f} km2 at {at.y:.5f} north, "
                         f"{at.x:.5f} east.")
