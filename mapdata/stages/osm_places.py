"""Stage "osm-places": named places from the planet file, into a layer of places (P3-T1b, DP168, DAT-4).

For P3-T1b, the seas, bays and straits that OpenStreetMap has as a single
point, or as an area that Natural Earth's marine areas do not name, so they can
be found by search and Nearby. They are places: never said as where you are.

Each query in the settings gives the OSM features to read and the type their
places get. A node is a place where it is. An area becomes a place at a point
inside it, as the regional packs, not the base pack, hold OSM's bays as areas.
A place with the same name as a feature of the layer named in "same_as", such
as the North Sea in the Seas, bays and straits layer, is that feature, and is
left out.

GeoDesk gives its memory back only when the process ends (spike S2), so the
reading is done in its own short-lived process, "mapdata read-places", as the
osm-areas stage does. The features of the stage before are kept, and the places
added after them.

Settings:

* source: the planet file's source key, planet.
* layer: the layer of places, such as sea-places.
* queries: a list, each with query (GeoDesk's query language, such as
  "n[natural=bay][name]") and type (such as bay); with elevation: true, the
  place keeps its height in metres from OSM's ele tag, as for peaks (P3-T1f);
  with population: true, its population from OSM's population tag, as for
  towns and cities (P3-T1j), until Wikidata's replaces it (P3-T2).
* within: optional, a list of area layers, such as [countries, regions,
  counties]. Each place keeps the areas of those layers it is in, in that
  order, for search's descriptions (P3-T1j). In the stage's records each is
  its layer and id; the writing stage makes them ids, after any id is changed
  to keep every id different.
* same_as: optional, a layer whose names the places must not repeat.
* box: optional, [west, south, east, north].
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped

READ_VERSION = "osm-places-1"
REQUEST = "request.json"
READ_FOLDER = "read"


def place_record(osm_id: str, tags: dict, layer: str, kind: str) -> dict | None:
    """One place's record from its OSM tags: the English name where there is one, the local name beside it."""
    local = tags.get("name") or ""
    name = tags.get("name:en") or local
    if not name:
        return None
    r = {"id": osm_id, "layer": layer, "name": name, "type": kind}
    if local and local != name:
        r["local_name"] = local
    if tags.get("wikidata"):
        r["wikidata"] = tags["wikidata"]
    return r


def elevation_m(text) -> float | None:
    """A height from OSM's ele tag, such as "4808", "4808.7" or "4808 m"; None when it is not a number."""
    t = str(text or "").strip().lower().removesuffix("m").strip()
    if "," in t:   # "4,808": a decimal comma or a thousands comma, so not known
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return round(v, 1) if -500 < v < 9000 else None


def population(text) -> int | None:
    """A population from OSM's population tag, such as "12345", "12 345", "12,345" or "1.234.567"; None when it
    is not a whole number."""
    t = "".join(c for c in str(text or "").strip() if c not in " ,.'  ")
    return int(t) if t.isdigit() and 0 < int(t) < 100_000_000 else None


COAST_M = 1000   # a place no more than this off the land, such as a harbour town, has the areas nearest it


def areas_within(points: list, areas: list[tuple[str, str, object]], order: list[str]) -> list[list[dict]]:
    """For each point, the areas it is in, as layer and id, in the order of the layers given, then by id. Each
    area is tested once, prepared, against the points in its bounds. A place in none, such as a harbour town
    whose point is in the harbour (Looe, Porthleven), has the nearest area of each layer within COAST_M."""
    if not areas or not points:
        return [[] for _ in points]
    pts = np.array(points, dtype=object)
    xy = shapely.get_coordinates(pts)
    ptree = shapely.STRtree(pts)
    found: list[list[int]] = [[] for _ in points]
    for a, (_l, _i, g) in enumerate(areas):
        near = ptree.query(shapely.box(*g.bounds))
        if not len(near):
            continue
        shapely.prepare(g)
        for p in near[shapely.intersects_xy(g, xy[near, 0], xy[near, 1])].tolist():
            found[p].append(a)
    empty = [p for p, f in enumerate(found) if not f]
    if empty:
        atree = shapely.STRtree([g for _l, _i, g in areas])
        reach = COAST_M / 111_320.0
        for p in empty:
            best: dict[str, tuple[float, int]] = {}
            for a in sorted(atree.query(pts[p], predicate="dwithin", distance=reach).tolist()):
                d = shapely.distance(areas[a][2], pts[p])
                if areas[a][0] not in best or d < best[areas[a][0]][0]:
                    best[areas[a][0]] = (d, a)
            found[p] = [a for _d, a in best.values()]
    rank = {k: n for n, k in enumerate(order)}
    return [[{"layer": areas[a][0], "id": areas[a][1]}
             for a in sorted(set(f), key=lambda a: (rank.get(areas[a][0], 99), areas[a][1]))] for f in found]


def osm_id(f) -> str:
    return f"osm:{'n' if f.is_node else 'w' if f.is_way else 'r'}{f.id}"


def read(gol: Path, queries: list[dict], layer: str, box, say=print) -> tuple[list[dict], list]:
    """Every place the queries find, as records and points, in id order. Runs in the short-lived process."""
    import geodesk

    world = geodesk.Features(str(gol))
    gbox = geodesk.Box(west=box[0], south=box[1], east=box[2], north=box[3]) if box else None
    found: dict[str, tuple[dict, object]] = {}
    for q in queries:
        t = time.perf_counter()
        sel = world(q["query"])
        if gbox is not None:
            sel = sel(gbox)
        n = 0
        for f in sel:
            fid = osm_id(f)
            if fid in found:
                continue
            tags = {k: str(f.tags[k] or "") for k in ("name", "name:en", "wikidata")}
            rec = place_record(fid, tags, layer, q["type"])
            if rec is None:
                continue
            if q.get("elevation"):
                ele = elevation_m(f.tags["ele"])
                if ele is not None:
                    rec["elevation_m"] = ele
            if q.get("population"):
                pop = population(f.tags["population"])
                if pop is not None:
                    rec["population"] = pop
                    rec["population_source"] = "OpenStreetMap"
            if f.is_node:
                point = shapely.Point(f.lon, f.lat)
            else:
                g = geodesk.from_mercator(f.shape)
                if g is None or g.is_empty:
                    continue
                point = shapely.point_on_surface(g)
            point = shapely.Point(round(point.x, 7), round(point.y, 7))
            found[fid] = (rec, point)
            n += 1
        say(f"Read {n:,} places for {q['query']} in {time.perf_counter() - t:.0f} seconds.")
    ids = sorted(found)
    return [found[i][0] for i in ids], [found[i][1] for i in ids]


def main(folder: Path) -> int:
    """The entry point of the short-lived process: "mapdata read-places <folder>"."""
    request = json.loads((folder / REQUEST).read_text(encoding="utf-8"))
    lines: list[str] = []

    def say(text):
        lines.append(text)
        print(text, flush=True)

    records, geoms = read(Path(request["gol"]), request["queries"], request["layer"], request.get("box"), say)
    out = folder / READ_FOLDER
    out.mkdir(exist_ok=True)
    features.save(out, records, geoms)
    (out / "read log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


def leave_out_repeats(records: list[dict], geoms: list, names: set[str]) -> tuple[list[dict], list, list[str]]:
    """The places whose name or local name is not already a feature's name in the same_as layer."""
    keep_r, keep_g, left = [], [], []
    for r, g in zip(records, geoms):
        if r["name"] in names or r.get("local_name") in names:
            left.append(r["name"])
            continue
        keep_r.append(r)
        keep_g.append(g)
    return keep_r, keep_g, left


def run(ctx) -> None:
    s = ctx.settings
    layer = s.get("layer")
    if layer not in ctx.pack.layers:
        raise BuildStopped(f"The osm-places stage writes to the layer {layer}, which the pack's layer groups do not "
                           "define. Add the layer, or correct the stage's settings.")
    if not s.get("queries"):
        raise BuildStopped("The osm-places stage needs queries, each with query and type.")
    _source, gol = ctx.source(s.get("source", "planet"))
    request = {"gol": str(gol), "queries": s["queries"], "layer": layer, "box": s.get("box"),
               "version": READ_VERSION}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(request, indent=1), encoding="utf-8", newline="\n")
    out = ctx.folder / READ_FOLDER
    for name in ("features.json", "shapes.wkb", "read log.txt"):
        ctx.claim(out / name)
    ctx.progress.line(f"Reading the places from the planet file {gol.name} in a separate process, which ends when it "
                      "has finished.")
    done = subprocess.run([sys.executable, "-m", "mapdata", "--data", str(ctx.folders.root), "read-places",
                           str(ctx.folder)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (done.stdout or "").splitlines():
        ctx.progress.log(line)
    if done.returncode != 0 or not (out / "features.json").is_file():
        raise BuildStopped("Reading the places from the planet file failed. The end of its output was: "
                           + " ".join((done.stderr or done.stdout or "").splitlines()[-5:]))
    p_records, p_geoms = features.load(out)
    records, geoms = features.load(ctx.previous) if ctx.previous else ([], [])
    same = s.get("same_as")
    left: list[str] = []
    if same:
        names = {v for r in records if r.get("layer") == same for v in (r.get("name"), r.get("local_name")) if v}
        p_records, p_geoms, left = leave_out_repeats(p_records, p_geoms, names)
    if s.get("within"):
        order = list(s["within"])
        areas = [(r["layer"], r["id"], g) for r, g in zip(records, geoms) if r.get("layer") in order]
        for r, w in zip(p_records, areas_within(p_geoms, areas, order)):
            r["within"] = w
        ctx.progress.line(f"Each place has the areas of {', '.join(order)} it is in: "
                          f"{sum(1 for r in p_records if not r['within']):,} places are in none of them.")
    features.save(ctx.folder, records + p_records, geoms + p_geoms, ctx.claim)
    kinds: dict[str, int] = {}
    for r in p_records:
        kinds[r["type"]] = kinds.get(r["type"], 0) + 1
    ctx.progress.line(f"Places in the layer {layer}: {len(p_records):,}: "
                      + ", ".join(f"{n:,} of type {k}" for k, n in sorted(kinds.items())) + ".")
    if left:
        ctx.progress.line(f"Places left out as they have the name of a feature in the layer {same}: {len(left)}. "
                          "The log lists them.")
        for name in left:
            ctx.progress.log(f"Left out, as the layer {same} has it: {name}.")
