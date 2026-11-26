"""Stage "osm-land": land use, parks, school grounds and national parks (P4-T1e, design docs/plan/p4-t1-design.md 3.8;
DAT-2, DAT-3).

In a regional pack only, this stage reads the areas of OpenStreetMap within the coverage into four layers, by the
classes of mapdata/config/land_classes.yaml (the first class that matches an object wins, so no object is in two
layers):

* land-use: landuse and natural areas such as residential, farmland, forest, wood, heath and wetland.
* parks: leisure parks, commons, nature reserves, recreation grounds, pitches, golf courses and the like; a garden
  only if it has a name or access=yes or permissive (private gardens are left out).
* school-grounds: amenity school, college, university and kindergarten, as areas.
* national_parks: boundary=national_park, and boundary=protected_area with protect_class=5. These are cut to the land
  (the countries layer of the stage before), as every land area is.

An area's name is OpenStreetMap's (name:en first), or, with none, its type's words with a capital first letter:
"Woodland". Its type is the class's words, except for a protected area, whose type is its designation's words.

Joining: unnamed areas of one layer and type that touch (come within meet_m, 1 metre if not given) are joined, within
one parish (the parishes layer of the stage before; an area is in the parish its representative point is in), into
one area. Named areas stay separate. The joined area takes the id of the smallest of its areas. National parks are
never joined. Overlaps between areas are kept.

Each shape is simplified to tolerance_m (5 metres if not given), then cut to the coverage; one the coverage cuts is
partial. The stage logs each class whose layer or zoom differs from Shortbread's, a reference only (data sources.md),
and writes osm_land.json: the counts and those differences. The features of the stage before are kept, and the new
ones added after them, in id order.
"""
from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import osm_source
from mapdata.stages.clip import polygonal
from mapdata.stages.osm_lines import _connected, countries_of

REPORT = "osm_land.json"
RECORD = "land_classes.yaml"
LAYERS = ("land-use", "parks", "school-grounds", "national_parks")
NEVER_JOINED = ("national_parks",)
TOLERANCE_M = 5.0
MEET_M = 1.0
METRES_PER_DEGREE = 111_320.0
OPEN_ACCESS = ("yes", "permissive")


# The record -----------------------------------------------------------------------------------------------------

def record_path() -> Path:
    from mapdata.paths import CONFIG_DIR

    return CONFIG_DIR / RECORD


def load_record(path: Path | None = None) -> dict:
    """The land classes, checked: each is in one of the four layers and has its tag, words and zooms."""
    import yaml

    p = path or record_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    for c in data.get("classes") or []:
        for k in ("layer", "key", "value", "type", "zoom", "shortbread_layer"):
            if k not in c:
                raise BuildStopped(f"The land classes, {p.name}, give the class {c} no {k}.")
        if c["layer"] not in LAYERS:
            raise BuildStopped(f"The land classes, {p.name}, put {c['key']}={c['value']} in {c['layer']}, which is "
                               f"not one of {', '.join(LAYERS)}.")
    data.setdefault("classes", [])
    data.setdefault("designations", {})
    data.setdefault("default_designation", "protected landscape")
    data.setdefault("layer_equivalents", {})
    return data


def fingerprint_extra(stage: dict) -> dict:
    """The record is part of what the stage reads and writes, so changing it reads the areas again."""
    return {"land_classes": record_path().read_text(encoding="utf-8")}


def query_for(classes: list[dict]) -> str:
    """The query that reads every class: the values of one key together, a class with a second tag by itself."""
    plain: dict[str, list[str]] = defaultdict(list)
    extra: list[str] = []
    for c in classes:
        if c.get("also"):
            tail = "".join(f"[{k}={v}]" for k, v in c["also"].items())
            extra.append(f"a[{c['key']}={c['value']}]{tail}")
        elif c["value"] not in plain[c["key"]]:
            plain[c["key"]].append(c["value"])
    return ", ".join([f"a[{k}={','.join(v)}]" for k, v in plain.items()] + extra)


def differences(record: dict) -> list[str]:
    """Each class whose layer or first zoom differs from Shortbread's, as a plain line."""
    equiv = record.get("layer_equivalents") or {}
    out = []
    for c in record["classes"]:
        tag = f"{c['key']}={c['value']}"
        sb = str(c["shortbread_layer"])
        if sb == "none":
            out.append(f"{tag}: in our layer {c['layer']} from zoom {c['zoom']}; Shortbread does not hold it.")
        elif sb != equiv.get(c["layer"]):
            out.append(f"{tag}: our layer {c['layer']} differs from Shortbread's layer {sb} "
                       f"(zoom {c['zoom']} against {c.get('shortbread_zoom')}).")
        elif c.get("shortbread_zoom") is not None and int(c["shortbread_zoom"]) != int(c["zoom"]):
            out.append(f"{tag}: in {c['layer']} from zoom {c['zoom']}; Shortbread's layer {sb} has it from zoom "
                       f"{c['shortbread_zoom']}.")
    return out


# Classifying ----------------------------------------------------------------------------------------------------

def classify(tags: dict, record: dict) -> tuple[str, str] | None:
    """The layer and type of an area with these tags: the first class that matches. None for an area left out, such
    as a private garden."""
    for c in record["classes"]:
        if tags.get(c["key"]) != c["value"]:
            continue
        if any(tags.get(k) != str(v) for k, v in (c.get("also") or {}).items()):
            continue
        if c.get("when") == "named_or_open":
            if not (tags.get("name") or tags.get("name:en") or tags.get("access") in OPEN_ACCESS):
                continue
        kind = c["type"]
        if c["layer"] == "national_parks":
            kind = record["designations"].get(tags.get("designation") or "", None) \
                or (kind if c["key"] == "boundary" and c["value"] == "national_park"
                    else record["default_designation"])
        return c["layer"], kind
    return None


# Reading --------------------------------------------------------------------------------------------------------

def read_job(source, request: dict, out: Path) -> None:
    """The areas, one reading box at a time, each classified, simplified and saved before the next box is read."""
    tol = float(request["tolerance_m"]) / METRES_PER_DEGREE
    record = request["record"]
    seen: set[str] = set()
    boxes = request["reading_boxes"]
    for n, box in enumerate(boxes):
        recs, geoms = [], []
        left_out = 0
        for o in source.query(request["query"], box, seen):
            if o.kind != "area":
                continue
            found = classify(o.tags, record)
            if found is None:
                left_out += 1
                continue
            g = o.shape
            if tol:
                g = shapely.simplify(g, tol, preserve_topology=True)
            g = polygonal(shapely.make_valid(g))
            if g.is_empty:
                continue
            t = o.tags
            r = {"id": o.id, "layer": found[0], "type": found[1], "name": t.get("name:en") or t.get("name") or "",
                 "local_name": t.get("name") or ""}
            if t.get("wikidata"):
                r["wikidata"] = t["wikidata"]
            recs.append(r)
            geoms.append(shapely.set_precision(g, 1e-7))
        recs.append({"id": f"count:left_out:{n}", "left_out": left_out})
        geoms.append(shapely.Polygon())
        osm_source.save_box(request, out, n, recs, geoms)
        source.say(f"Reading box {n + 1} of {len(boxes)}: {len(recs) - 1:,} land areas, and {left_out:,} left out.")


# Joining --------------------------------------------------------------------------------------------------------

def _number(oid: str) -> tuple[int, str]:
    return int(oid[5:]), oid[4]


def join_areas(recs: list[dict], geoms: list, parishes: list[tuple[str, object]], meet_m: float = MEET_M) \
        -> tuple[list[dict], list, list[int]]:
    """The areas with unnamed ones of one layer and type that touch, in one parish, joined into one. Returns the
    records, the shapes, and for each how many areas it is made of."""
    n = len(recs)
    if not n:
        return [], [], []
    reps = [shapely.point_on_surface(g) for g in geoms]
    parish = countries_of(reps, parishes) if parishes else [""] * n
    codes: dict[tuple, int] = {}
    key = np.zeros(n, dtype=np.intp)
    joinable = np.zeros(n, dtype=bool)
    for i, r in enumerate(recs):
        if not r.get("name") and r["layer"] not in NEVER_JOINED:
            joinable[i] = True
            key[i] = codes.setdefault((r["layer"], r["type"], parish[i]), len(codes))
    left = right = np.empty(0, dtype=np.intp)
    idx = np.flatnonzero(joinable)
    if len(idx) > 1:
        sub = np.array([geoms[i] for i in idx], dtype=object)
        a, b = shapely.STRtree(sub).query(sub, predicate="dwithin", distance=meet_m / METRES_PER_DEGREE)
        keep = (a < b) & (key[idx[a]] == key[idx[b]])
        left, right = idx[a[keep]].astype(np.intp), idx[b[keep]].astype(np.intp)
    sets = _connected(np.concatenate([left, right]).astype(np.intp),
                      np.concatenate([right, left]).astype(np.intp), n)
    out_r, out_g, sizes = [], [], []
    for members in sets:
        if len(members) == 1:
            out_r.append(recs[members[0]])
            out_g.append(geoms[members[0]])
            sizes.append(1)
            continue
        first = min(members, key=lambda i: _number(recs[i]["id"]))
        rec = dict(recs[first])
        for i in members:   # the smallest area's wikidata, else the first any has
            if not rec.get("wikidata") and recs[i].get("wikidata"):
                rec["wikidata"] = recs[i]["wikidata"]
        merged = polygonal(shapely.make_valid(shapely.union_all([geoms[i] for i in members])))
        out_r.append(rec)
        out_g.append(shapely.set_precision(merged, 1e-7))
        sizes.append(len(members))
    return out_r, out_g, sizes


# The stage ------------------------------------------------------------------------------------------------------

def make_records(recs: list[dict], geoms: list, have: set, words: dict | None, source_key: str):
    """The new features: an id in have is skipped; an unnamed area has its type's words with a capital first
    letter. Returns the records and shapes in id order, and the number skipped."""
    out = []
    skipped = 0
    for r, g in zip(recs, geoms):
        if r["id"] in have:
            skipped += 1
            continue
        name = r.get("name") or (r["type"][:1].upper() + r["type"][1:])
        rec = {"id": r["id"], "layer": r["layer"], "name": name, "type": r["type"], "source_key": source_key}
        if r.get("local_name") and r["local_name"] != name:
            rec["local_name"] = r["local_name"]
        for k in ("wikidata", "partial"):
            if r.get(k):
                rec[k] = r[k]
        out.append((rec, g))
    out.sort(key=lambda rg: rg[0]["id"])
    return [r for r, _g in out], [g for _r, g in out], skipped


def run(ctx) -> None:
    s = ctx.settings
    record = load_record()
    request = {"tolerance_m": float(s.get("tolerance_m", TOLERANCE_M)), "record": record,
               "query": query_for(record["classes"])}
    meet_m = float(s.get("meet_m", MEET_M))
    ctx.progress.line(f"Reading land use, parks, school grounds and national parks within the coverage: "
                      f"{request['query']}.")
    diffs = differences(record)
    ctx.progress.line(f"{len(diffs)} classes differ from Shortbread's layer or zoom, which is a reference only:")
    for line in diffs:
        ctx.progress.line("  " + line)
    out = osm_source.run_reading(ctx, "osm_land", request)
    raw_r, raw_g = osm_source.load_boxes(out)
    left_out = sum(int(r.get("left_out", 0)) for r in raw_r if r["id"].startswith("count:"))
    pairs = [(r, g) for r, g in zip(raw_r, raw_g) if not r["id"].startswith("count:")]
    del raw_r, raw_g

    p_r, p_g = features.load_layers(Path(ctx.previous), {"parishes", "countries"})
    parishes = [(r["id"], g) for r, g in zip(p_r, p_g) if r["layer"] == "parishes"]
    land = [g for r, g in zip(p_r, p_g) if r["layer"] == "countries"]
    recs = [r for r, _g in pairs]
    geoms = [g for _r, g in pairs]
    by_read: dict[str, int] = defaultdict(int)
    for r in recs:
        by_read[r["layer"]] += 1
    ctx.progress.line(f"Read {len(recs):,} areas: " + ", ".join(f"{by_read[k]:,} in {k}" for k in LAYERS)
                      + f"; {left_out:,} left out (such as private gardens). Joining unnamed ones that touch, "
                        "within each parish.")
    recs, geoms, sizes = join_areas(recs, geoms, parishes, meet_m)

    if land:   # a protected area is cut to the land, as every land area is
        land_shape = shapely.union_all(land)
        shapely.prepare(land_shape)
        for i, r in enumerate(recs):
            if r["layer"] == "national_parks" and not shapely.contains(land_shape, geoms[i]):
                geoms[i] = polygonal(shapely.make_valid(shapely.intersection(geoms[i], land_shape)))
        keep = [i for i, g in enumerate(geoms) if not g.is_empty]
        recs, geoms, sizes = [recs[i] for i in keep], [geoms[i] for i in keep], [sizes[i] for i in keep]

    cov = osm_source.coverage_of(ctx)
    cut_r, cut_g, cut_counts = osm_source.clip_to_coverage(recs, geoms, cov)
    data = json.loads((Path(ctx.previous) / "features.json").read_text(encoding="utf-8"))
    have = {r["id"] for r in data["records"]}
    del data
    new_r, new_g, skipped = make_records(cut_r, cut_g, have, None, s.get("source") or "planet")

    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(Path(ctx.previous) / name, ctx.claim(Path(ctx.folder) / name))
    features.append(ctx.folder, new_r, [shapely.to_wkb(g) for g in new_g])

    layers = {}
    for layer in LAYERS:
        mine = [r for r in new_r if r["layer"] == layer]
        kinds: dict[str, int] = defaultdict(int)
        for r in mine:
            kinds[r["type"]] += 1
        layers[layer] = {"read": by_read[layer], "features": len(mine),
                         "partial": sum(1 for r in mine if r.get("partial")),
                         "by_type": dict(sorted(kinds.items()))}
    counts = {"layers": layers, "left_out": left_out, "joined_areas": sum(v - 1 for v in sizes),
              "outside_coverage": cut_counts["dropped"], "already_in_pack": skipped}
    ctx.claim(Path(ctx.folder) / REPORT).write_text(
        json.dumps({"counts": counts, "shortbread_differences": diffs}, indent=1, ensure_ascii=False,
                   sort_keys=True), encoding="utf-8", newline="\n")
    for layer, c in layers.items():
        ctx.progress.line(f"The layer {layer}: {c['read']:,} areas read, {c['features']:,} features after joining, "
                          f"{c['partial']:,} cut by the coverage.")
    ctx.progress.line(f"{counts['joined_areas']:,} areas were joined into others; {cut_counts['dropped']:,} were "
                      f"outside the coverage; {skipped:,} were already in the pack. The counts and the differences "
                      f"from Shortbread are in {REPORT}.")
