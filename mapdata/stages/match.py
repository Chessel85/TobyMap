"""Stage "match": a regional pack's features given the world pack's identifiers (P4-T1h, design
docs/plan/p4-t1-design.md 3.11, architecture 6.7; DAT-2, DMT-1).

The world pack is the identifier register: the stage reads it (the source world-pack) with mapcore.packs. For each
feature of the stage before in a layer the world pack also has (setting layers: countries, regions, counties, islands,
oceans, seas, lakes, rivers, roads and railways):

1. The same id in the same layer: matched. This is nearly every feature, as both packs read the same planet file with
   the same settings. A world id the world's writing stage gave the ending "#as-" and its layer, such as
   osm:r1814783#as-islands, is the same id.
2. Otherwise, the same Wikidata id in the same layer: the world's id. Where several regional features have it, the
   one with the most overlap takes it, and the others keep their own.
3. Otherwise, the same name made plain (mapcore.search.normalise), the same layer and type, and an overlap inside the
   coverage: for areas, each covers at least share (a half) of the other; for lines, at least share of the regional
   line lies within line_m (200 metres) of the world's; for unnamed islands the overlap alone, whatever the name.
   The world feature with the most overlap wins.
4. A matched feature takes the world's id, and its own goes into its aliases. Every record that names it (parent,
   named_from, sovereign_id, within) names the world's id.
5. A regional id that the world pack uses in another layer, in any layer of the regional pack, gets the ending "#as-"
   and its layer, as the writing stage does, so no id means two features once the packs are combined.
6. A world feature of those layers that lies in the coverage and has no match is listed in the log, as the combined
   packs will hide it in the covered pack tiles (P4-T3a).

Each world feature is matched once. The world's shapes are read from its pack tiles inside the coverage only.

matches.csv, in the stage's folder, lists every match made by Wikidata or by name, and every world feature left
unmatched, with both ids, both names and the overlap; match.json holds the counts. The quality report's section
"Matches with the world pack" is made from them (mapdata/pipeline/report.py). The shapes are not changed: shapes.wkb
is copied, and features.json written again with the ids changed, in the same order.
"""
from __future__ import annotations

import csv
import json
import math
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline.errors import BuildStopped

REPORT = "match.json"
MATCHES = "matches.csv"
COLUMNS = ["how", "layer", "world identifier", "world name", "regional identifier", "regional name", "overlap %"]
WORLD_LAYERS = ("countries", "regions", "counties", "islands", "oceans", "seas", "lakes", "rivers", "roads",
                "railways")
LINE_M = 200.0        # a regional line lies along a world line within this distance
SHARE = 0.5           # how much each must cover of the other
UNNAMED_ISLAND = "unnamed island"   # the type of the join's and small-islands' unnamed islands
ID_FIELDS = ("parent", "named_from", "sovereign_id")   # record fields that name another feature by its id
TREE = ("countries", "regions", "counties", "districts", "parishes")   # whose parent is in the layer above
METRES_PER_DEGREE = 111_320.0


@dataclass(frozen=True)
class Match:
    world_id: str
    how: str          # id, wikidata or name
    overlap: float | None   # 0 to 1: for areas the smaller of the two shares, for lines the share along


# Overlap ----------------------------------------------------------------------------------------------------------

def _polygonal(g) -> bool:
    return g is not None and not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon", "GeometryCollection") \
        and shapely.area(g) > 0


def _lineal(g) -> bool:
    return g is not None and not g.is_empty and shapely.length(g) > 0 and not _polygonal(g)


def overlap(regional, world, line_m: float = LINE_M) -> float:
    """How much the two shapes are one: for areas, the smaller of the two shares each covers of the other; for a
    line, the share of the regional line within line_m of the world's line. 0 when they cannot be compared."""
    if regional is None or world is None or regional.is_empty or world.is_empty:
        return 0.0
    if _polygonal(regional) and _polygonal(world):
        try:
            common = shapely.area(shapely.intersection(regional, world))
        except shapely.errors.GEOSException:
            common = shapely.area(shapely.intersection(shapely.make_valid(regional), shapely.make_valid(world)))
        return float(min(common / shapely.area(regional), common / shapely.area(world)))
    if _lineal(regional) and _lineal(world):
        lat = (regional.bounds[1] + regional.bounds[3]) / 2
        k = math.cos(math.radians(lat))

        def flat(g):   # east and north in degrees of latitude, near enough for 200 metres
            return shapely.transform(g, lambda xy: xy * np.array([k, 1.0]))

        r, w = flat(regional), flat(world)
        near = shapely.buffer(w, line_m / METRES_PER_DEGREE)
        return float(min(1.0, shapely.length(shapely.intersection(r, near)) / shapely.length(r)))
    return 0.0


# Matching -----------------------------------------------------------------------------------------------------------

def plain(name) -> str:
    from mapcore.search import normalise

    return normalise(name or "")


def find_matches(records: list[dict], shapes: dict, world: list[dict], world_shapes: dict, *,
                 layers=WORLD_LAYERS, line_m: float = LINE_M, share: float = SHARE
                 ) -> tuple[dict[int, Match], list[str]]:
    """Steps 1 to 3 and 6 of the module's notes. records are the regional records in order; shapes, the regional
    shapes by record index (only those that may be matched by Wikidata or name are needed); world, the world's
    records of these layers, each with id, layer, type, name and wikidata; world_shapes, each world feature's shape
    inside the coverage, by id (a world feature with none lies outside it). Returns the matches by record index,
    and the ids of the world features in the coverage left unmatched, sorted."""
    layers = set(layers)
    by_id = {w["id"]: w for w in world if w["layer"] in layers}
    taken: set[str] = set()
    found: dict[int, Match] = {}
    wanted = [i for i, r in enumerate(records) if r.get("layer") in layers]

    # 1 The same id in the same layer, or the id the world's writing stage gave it in this layer.
    for i in wanted:
        r = records[i]
        for wid in (r["id"], f"{r['id']}#as-{r['layer']}"):
            w = by_id.get(wid)
            if w is not None and w["layer"] == r["layer"] and wid not in taken:
                found[i] = Match(wid, "id", None)
                taken.add(wid)
                break

    def best(pairs) -> None:
        """Give each world feature to the regional feature with the most overlap, and each regional feature its best
        world feature, highest overlap first; ties by the ids, so the result is the same each build (DMT-1)."""
        for score, i, wid, how in sorted(pairs, key=lambda p: (-p[0], records[p[1]]["id"], p[1], p[2])):
            if i in found or wid in taken:
                continue
            found[i] = Match(wid, how, round(score, 4) if score is not None else None)
            taken.add(wid)

    # 2 The same Wikidata id in the same layer.
    by_wikidata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for w in world:
        if w["layer"] in layers and w.get("wikidata"):
            by_wikidata[(w["layer"], w["wikidata"])].append(w["id"])
    pairs = []
    for i in wanted:
        r = records[i]
        if i in found or not r.get("wikidata"):
            continue
        for wid in by_wikidata.get((r["layer"], r["wikidata"]), ()):
            if wid not in taken:
                pairs.append((overlap(shapes.get(i), world_shapes.get(wid), line_m), i, wid, "wikidata"))
    best(pairs)

    # 3 The same plain name and type, and an overlap; unnamed islands by their overlap alone.
    by_name: dict[tuple, list[str]] = defaultdict(list)
    for w in world:
        if w["layer"] not in layers or w["id"] in taken or w["id"] not in world_shapes:
            continue
        key = ((w["layer"], UNNAMED_ISLAND) if w.get("type") == UNNAMED_ISLAND
               else (w["layer"], w.get("type"), plain(w.get("name"))))
        by_name[key].append(w["id"])
    pairs = []
    for i in wanted:
        r = records[i]
        if i in found or shapes.get(i) is None:
            continue
        key = ((r["layer"], UNNAMED_ISLAND) if r.get("type") == UNNAMED_ISLAND
               else (r["layer"], r.get("type"), plain(r.get("name"))))
        if not key[-1]:
            continue   # no name to compare
        for wid in by_name.get(key, ()):
            score = overlap(shapes[i], world_shapes[wid], line_m)
            if score >= share:
                pairs.append((score, i, wid, "name"))
    best(pairs)

    # 6 World features in the coverage with no match.
    unmatched = sorted(w["id"] for w in world if w["layer"] in layers and w["id"] not in taken
                       and _in_cover(world_shapes.get(w["id"])))
    return found, unmatched


def _in_cover(g) -> bool:
    return g is not None and not g.is_empty and (shapely.area(g) > 0 or shapely.length(g) > 0)


def apply_matches(records: list[dict], found: dict[int, Match], world_layer_of: dict[str, str]) -> dict:
    """Steps 4 and 5 of the module's notes, on the records in place. world_layer_of gives the layer of every world
    id. Returns the counts: id, wikidata, name (the matches of each kind) and as_layer (ids given the ending)."""
    counts = {"id": 0, "wikidata": 0, "name": 0, "as_layer": 0}
    renamed: dict[tuple[str, str], str] = {}   # (old id, layer) to the new id
    for i, r in enumerate(records):
        m = found.get(i)
        old = r["id"]
        if m is not None:
            counts[m.how] += 1
            if m.world_id != old:
                r["id"] = m.world_id
                r["aliases"] = sorted(set(r.get("aliases") or []) | {old})
                renamed[(old, r["layer"])] = m.world_id
            continue
        other = world_layer_of.get(old)
        if other is not None and other != r["layer"]:
            new = f"{old}#as-{r['layer']}"
            r["id"] = new
            renamed[(old, r["layer"])] = new
            counts["as_layer"] += 1
    if not renamed:
        return counts
    # An old id, to the id it has now in each layer that had it: renamed, or kept by a record not renamed.
    now: dict[str, dict[str, str]] = defaultdict(dict)
    for (old, layer), new in renamed.items():
        now[old][layer] = new
    for r in records:
        if r["id"] in now:
            now[r["id"]].setdefault(r["layer"], r["id"])

    def new_id(old: str, child_layer: str) -> str:
        """The id an id field names now. An old id that several layers had is the one in the nearest layer above
        the child's, as a parish's parent is its district; failing that the one a record kept, then the first
        layer's in alphabetical order."""
        options = now.get(old)
        if not options:
            return old
        if len(options) > 1 and child_layer in TREE:
            above = [lay for lay in options if lay in TREE and TREE.index(lay) < TREE.index(child_layer)]
            if above:
                return options[max(above, key=TREE.index)]
        kept = [lay for lay, fid in options.items() if fid == old]
        return old if kept else options[sorted(options)[0]]

    for r in records:
        for field in ID_FIELDS:
            if isinstance(r.get(field), str):
                r[field] = new_id(r[field], r["layer"])
        if isinstance(r.get("within"), list):
            r["within"] = [{**w, "id": renamed.get((w.get("id"), w.get("layer")), w.get("id"))}
                           if isinstance(w, dict) else w for w in r["within"]]
    return counts


# Reading the world pack ---------------------------------------------------------------------------------------------

def world_records(pack, layers) -> tuple[list[dict], dict[str, str]]:
    """The world's records of the matched layers, each as id, layer, type, name and wikidata, and the layer of every
    world id, of every layer."""
    layer_of: dict[str, str] = {}
    out = []
    wanted = set(layers)
    for rec in pack.scan([lay["id"] for lay in pack.layers]):
        layer_of[rec["id"]] = rec["layer"]
        if rec["layer"] in wanted:
            names = rec.get("names") or {}
            out.append({"id": rec["id"], "layer": rec["layer"], "type": rec.get("type"),
                        "name": names.get("en") or names.get("local"), "wikidata": rec.get("wikidata"),
                        "bbox": rec.get("bbox")})
    out.sort(key=lambda w: w["id"])
    return out, layer_of


def _box_meets(bbox, bounds) -> bool:
    if not bbox:
        return False
    west, south, east, north = bbox
    x0, y0, x1, y1 = bounds
    if north < y0 or south > y1:
        return False
    if west <= east:
        return not (east < x0 or west > x1)
    return not (180 < x0 or west > x1) or not (east < x0 or -180 > x1)   # a box across the 180 degree line


def world_shapes(pack, world: list[dict], cover) -> dict[str, object]:
    """Each world feature's shape inside the coverage, from the pack tiles that meet it, by id. A feature with
    nothing inside the coverage is left out."""
    from mapcore.packs import coords, tiles

    bounds = cover.bounds
    numbers = {}
    for w in world:
        if _box_meets(w.get("bbox"), bounds):
            n = pack.feature_number(w["id"])
            if n is not None:
                numbers[n] = w["id"]
    if not numbers:
        return {}
    shapely.prepare(cover)
    parts_of: dict[str, list] = defaultdict(list)
    for key in pack.keys():
        if not key.startswith("tile/"):
            continue
        level, x, y = (int(v) for v in key.split("/")[1:])
        box = tiles.tile_box(level, x, y)
        if box[2] < bounds[0] or box[0] > bounds[2] or box[3] < bounds[1] or box[1] > bounds[3]:
            continue
        cell = shapely.box(*box)
        if not cover.intersects(cell):
            continue
        for e in pack.tile(level, x, y):
            fid = numbers.get(e.feature)
            if fid is None:
                continue
            if e.kind == tiles.COVERED:
                parts_of[fid].append(cell)
            elif e.kind == tiles.COMPACT:
                parts_of[fid].append(coords.to_shape(e.data))
            elif e.kind == tiles.LINES:
                parts_of[fid].append(coords.to_line_shapes([e.data])[0])
    out = {}
    for fid in sorted(parts_of):
        parts = parts_of[fid]
        g = parts[0] if len(parts) == 1 else shapely.union_all(parts)
        try:
            g = shapely.intersection(g, cover)
        except shapely.errors.GEOSException:
            g = shapely.intersection(shapely.make_valid(g), cover)
        if _in_cover(g):
            out[fid] = g
    return out


def open_world(path: Path):
    from mapcore.packs.pack import Pack, PackError

    try:
        pack = Pack(path, check_app=False)
    except PackError as exc:
        raise BuildStopped(f"The match stage reads the world pack, {path}, but it cannot be opened: "
                           f"{exc.message}") from None
    if (pack.manifest.get("coverage") or {}).get("kind") not in (None, "world"):
        pack.close()
        raise BuildStopped(f"The match stage's source, {path}, is a regional pack, not a world pack. Set the "
                           f"world-pack source in sources.yaml to the world pack.")
    return pack


# The stage ----------------------------------------------------------------------------------------------------------

def _shapes_of(folder: Path, data: dict, indexes) -> dict:
    out = {}
    with open(Path(folder) / "shapes.wkb", "rb") as f:
        for i in sorted(indexes):
            a, n = data["shapes"][i]
            f.seek(a)
            out[i] = shapely.from_wkb(f.read(n))
    return out


def write_matches(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        out = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        out.writeheader()
        out.writerows(rows)


def run(ctx) -> None:
    from mapdata.stages import coverage as coveragemod

    s = ctx.settings
    key = s.get("source")
    if not key:
        raise BuildStopped("The match stage needs the setting source: the world pack, world-pack.")
    cov_folder = ctx.earlier.get("coverage")
    if cov_folder is None:
        raise BuildStopped("The match stage matches the features inside the coverage, but no coverage stage ran "
                           "before it. Put the coverage stage before it.")
    layers = tuple(s.get("layers") or WORLD_LAYERS)
    line_m = float(s.get("line_m", LINE_M))
    share = float(s.get("share", SHARE))
    cover = coveragemod.load(cov_folder).shape
    _src, path = ctx.source(key)

    data = json.loads((Path(ctx.previous) / "features.json").read_text(encoding="utf-8"))
    records = data["records"]
    pack = open_world(path)
    try:
        world, layer_of = world_records(pack, layers)
        wshapes = world_shapes(pack, world, cover)
    finally:
        pack.close()
    world_ids = {w["id"] for w in world}
    # Only the shapes that may be matched by Wikidata or by name are read.
    maybe = [i for i, r in enumerate(records) if r.get("layer") in layers
             and r["id"] not in world_ids and f"{r['id']}#as-{r['layer']}" not in world_ids]
    shapes = _shapes_of(ctx.previous, data, maybe)
    found, unmatched = find_matches(records, shapes, world, wshapes, layers=layers, line_m=line_m, share=share)

    names = {i: records[i].get("name") or "" for i in found}
    old_ids = {i: records[i]["id"] for i in found}
    counts = apply_matches(records, found, layer_of)
    counts["world_unmatched"] = len(unmatched)

    by_world = {w["id"]: w for w in world}
    rows = []
    for i, m in sorted(found.items(), key=lambda im: (im[1].how, records[im[0]]["layer"], im[1].world_id)):
        if m.how == "id":
            continue
        rows.append({"how": m.how, "layer": records[i]["layer"], "world identifier": m.world_id,
                     "world name": by_world[m.world_id].get("name") or "", "regional identifier": old_ids[i],
                     "regional name": names[i],
                     "overlap %": "" if m.overlap is None else f"{100 * m.overlap:.1f}"})
    for wid in unmatched:
        w = by_world[wid]
        rows.append({"how": "unmatched", "layer": w["layer"], "world identifier": wid, "world name": w.get("name") or "",
                     "regional identifier": "", "regional name": "", "overlap %": ""})

    shutil.copyfile(Path(ctx.previous) / "shapes.wkb", ctx.claim(Path(ctx.folder) / "shapes.wkb"))
    ctx.claim(Path(ctx.folder) / "features.json").write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=0), encoding="utf-8", newline="\n")
    write_matches(ctx.claim(Path(ctx.folder) / MATCHES), rows)
    ctx.claim(Path(ctx.folder) / REPORT).write_text(
        json.dumps({"counts": counts, "layers": list(layers)}, indent=1, sort_keys=True), encoding="utf-8",
        newline="\n")

    ctx.progress.line(f"Matched with the world pack: {counts['id']:,} features by their id, {counts['wikidata']:,} "
                      f"by Wikidata and {counts['name']:,} by name, each of those taking the world's id and keeping "
                      f"its own as an alias. {counts['as_layer']:,} ids the world uses in another layer were given "
                      f"the ending of their layer. {len(unmatched):,} world features in the coverage have no match. "
                      f"Each match by Wikidata or name, and each world feature with none, is listed in {MATCHES}.")
    for row in rows:
        if row["how"] == "unmatched":
            ctx.progress.log(f"World feature with no match in the coverage, to be hidden there when the packs are "
                             f"combined: {row['world name'] or 'no name'} ({row['world identifier']}), "
                             f"{row['layer']}.")
        else:
            ctx.progress.log(f"Matched by {row['how']}: {row['regional name'] or 'no name'} "
                             f"({row['regional identifier']}) is the world's {row['world name'] or 'no name'} "
                             f"({row['world identifier']}), {row['layer']}, overlap {row['overlap %'] or 'not measured'}"
                             f"{'%' if row['overlap %'] else ''}.")
