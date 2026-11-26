"""Stage "osm-streets": every road, street, track and footpath, named or not (P4-T1d, design
docs/plan/p4-t1-design.md 3.7; DAT-2, DAT-3).

In a regional pack, the unchanged osm-lines stage reads the motorways and trunk roads into the world's layer roads,
with the world's ids. This stage reads every other road, street and path of OpenStreetMap within the coverage, into
three layers:

* main-roads: highway=primary, secondary and their _link ways (in Great Britain, the A roads that are not trunk
  roads, and the B roads).
* streets: highway=tertiary, tertiary_link, unclassified, residential, living_street, road, pedestrian (as a line),
  busway, and service, except service=driveway, parking_aisle and drive-through.
* paths: highway=footway, except footway=sidewalk and crossing; path, bridleway, cycleway, steps and track.

Each way's type is the plain words of its highway value, from the templates' details.street_types ("primary road",
"footpath"); a _link way has its road's type. The ways are joined into features:

* A main road with a number is joined by its number, per country, with osm-lines' rules for stretches far apart
  (road_parts), so "A33" is one feature and "B3335" another. An unnamed main-road way with no number that meets a
  numbered road end to end, such as a slip road, joins it (osm-lines' link_unnamed). The name is the number, with
  the name added where most of its ways carry it: "A33, Basingstoke Road".
* A street or path with a name (and a main road with a name but no number) is joined with the ways of the same name
  and the same layer that meet it, or come within join_gap_m (30 metres) of it, again and again. So a street broken
  by a roundabout, or a dual carriageway's two sides, is one feature, and the High Streets of two towns are two:
  a name joins only what is connected.
* Unnamed ways of one layer and type that meet (within meet_m, 3 metres, as each way is simplified to 2) are joined
  within one parish, the parishes layer of the stage before, a way being in the parish its middle is in. So the
  footpaths across a field are one "Footpath" in that parish, and footpaths that cross a parish boundary are two.
  The name is the type's words with a capital first letter: "Footpath", "Service road".

A feature takes the id of its smallest way, as in osm-lines. Every feature's OpenStreetMap way ids are kept in
ways.json beside features.json, for the network graph of Phase 5; the writing stage never reads it. Each line is
cut to the coverage, and one the coverage cuts is partial; its ways in ways.json are all its ways, inside the
coverage or not.

The reading is done one reading box at a time (osm_source), each way simplified to tolerance_m (2 metres) as it is
read; the joining is done after, on all the ways, so a street across two reading boxes is one feature. The stage
writes osm_streets.json: for each layer, the ways read, the features made, the km of line, and those the coverage
cut. The features of the stage before are kept, and the new ones added after them, in id order.
"""
from __future__ import annotations

import json
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.stages import osm_source
from mapdata.stages.osm_lines import _connected, first_ref, line_record, link_unnamed, most, road_parts, \
    simplify_line, countries_of
from mapdata.stages.osm_rivers import length_km

REPORT = "osm_streets.json"
WAYS = "ways.json"
LAYERS = ("main-roads", "streets", "paths")
TOLERANCE_M = 2.0
JOIN_GAP_M = 30.0
MEET_M = 3.0
METRES_PER_DEGREE = 111_320.0
TAG_KEYS = ("highway", "name", "name:en", "ref", "wikidata")
# Each highway value read: its layer and the type it gives (a _link way has its road's type).
KINDS = {
    "primary": ("main-roads", "primary"), "primary_link": ("main-roads", "primary"),
    "secondary": ("main-roads", "secondary"), "secondary_link": ("main-roads", "secondary"),
    "tertiary": ("streets", "tertiary"), "tertiary_link": ("streets", "tertiary"),
    "unclassified": ("streets", "unclassified"), "residential": ("streets", "residential"),
    "living_street": ("streets", "living_street"), "road": ("streets", "road"),
    "pedestrian": ("streets", "pedestrian"), "busway": ("streets", "busway"), "service": ("streets", "service"),
    "footway": ("paths", "footway"), "path": ("paths", "path"), "bridleway": ("paths", "bridleway"),
    "cycleway": ("paths", "cycleway"), "steps": ("paths", "steps"), "track": ("paths", "track"),
}
LEFT_OUT = {"service": ("driveway", "parking_aisle", "drive-through"), "footway": ("sidewalk", "crossing")}
QUERY = ("w[highway=primary,primary_link,secondary,secondary_link], "
         "w[highway=tertiary,tertiary_link,unclassified,residential,living_street,road,pedestrian,busway], "
         "w[highway=service][service!=driveway,parking_aisle,drive-through], "
         "w[highway=footway][footway!=sidewalk,crossing], "
         "w[highway=path,bridleway,cycleway,steps,track]")


@dataclass
class Way:
    id: int          # the OpenStreetMap way's number
    layer: str       # main-roads, streets or paths
    kind: str        # the key of its type in the templates' street_types, such as footway
    tags: dict
    shape: object    # a line, in degrees


def classify(tags: dict) -> tuple[str, str] | None:
    """The layer and type of a way with these tags, or None for a way left out: a driveway, parking aisle or
    drive-through, a sidewalk or crossing, and every highway value not read here (motorways and trunk roads are the
    osm-lines stage's)."""
    highway = tags.get("highway") or ""
    found = KINDS.get(highway)
    if found is None:
        return None
    if highway == "service" and (tags.get("service") or "") in LEFT_OUT["service"]:
        return None
    if highway == "footway" and (tags.get("footway") or "") in LEFT_OUT["footway"]:
        return None
    return found


def type_words() -> dict[str, str]:
    from mapcore.describe import templates

    return {k: str(v) for k, v in templates()["details"]["street_types"].items()}


def fingerprint_extra(stage: dict) -> dict:
    """The type words are written into the pack, so changing them makes the stage run again."""
    return {"type_words": type_words()}


def unnamed_name(kind: str, words: dict) -> str:
    text = words.get(kind) or kind
    return text[:1].upper() + text[1:]


# Reading --------------------------------------------------------------------------------------------------------

def read_job(source, request: dict, out: Path) -> None:
    """The ways, one reading box at a time, each simplified and saved before the next box is read."""
    tol = float(request["tolerance_m"]) / METRES_PER_DEGREE
    seen: set[str] = set()
    boxes = request["reading_boxes"]
    for n, box in enumerate(boxes):
        recs, geoms = [], []
        for o in source.query(QUERY, box, seen):
            if o.kind != "way":   # a pedestrian or service area is not a line
                continue
            found = classify(o.tags)
            if found is None:
                continue
            g = o.shape
            if g is None or g.is_empty or g.geom_type not in ("LineString", "MultiLineString"):
                continue
            g = simplify_line(g, tol)
            if g.is_empty:
                continue
            r = {"id": o.id, "layer": found[0], "kind": found[1]}
            r.update({k: o.tags[k] for k in TAG_KEYS if o.tags.get(k)})
            recs.append(r)
            geoms.append(g)
        osm_source.save_box(request, out, n, recs, geoms)
        source.say(f"Reading box {n + 1} of {len(boxes)}: {len(recs):,} roads, streets and paths.")


# Joining --------------------------------------------------------------------------------------------------------

def _flatten(xy):
    xy = xy.copy()
    xy[:, 0] *= np.cos(np.radians(xy[:, 1]))
    return xy


def _places_of(points: list, areas: list[tuple[str, object]]) -> list[int]:
    """The index of the area each point is in, or of the nearest; -1 with no areas."""
    if not areas:
        return [-1] * len(points)
    ids = countries_of(points, [(str(i), g) for i, (_a, g) in enumerate(areas)])
    return [int(i) for i in ids]


def _merge(lines: list):
    parts = [p for p in shapely.get_parts(np.array(lines, dtype=object)).tolist()
             if p.geom_type == "LineString" and len(p.coords) >= 2]
    if not parts:
        return None
    return shapely.set_precision(shapely.line_merge(shapely.MultiLineString(parts)), 1e-7)


def _groups_by_meeting(ways: list[Way], parish: list[int], gap_m: float, meet_m: float) -> list[list[int]]:
    """The indexes of ways joined by name or, unnamed, by type and parish: named ways of one name that come within
    gap_m of each other, and unnamed ways of one type and parish within meet_m, connected again and again."""
    n = len(ways)
    if not n:
        return []
    flat = shapely.transform(np.array([w.shape for w in ways], dtype=object), _flatten)
    left, right = shapely.STRtree(flat).query(flat, predicate="dwithin", distance=gap_m / METRES_PER_DEGREE)
    keep = left < right
    left, right = left[keep], right[keep]
    names = [(w.tags.get("name") or "").strip() for w in ways]
    codes: dict[tuple, int] = {}
    key = np.array([codes.setdefault(("name", names[i]) if names[i] else ("unnamed", ways[i].kind, parish[i]),
                                     len(codes)) for i in range(n)], dtype=np.intp)
    named = np.array([bool(v) for v in names], dtype=bool)
    same = key[left] == key[right]
    left, right = left[same], right[same]
    unnamed_pair = ~named[left]
    if unnamed_pair.any():
        near = shapely.distance(flat[left[unnamed_pair]], flat[right[unnamed_pair]]) <= meet_m / METRES_PER_DEGREE
        ok = np.ones(len(left), dtype=bool)
        ok[np.flatnonzero(unnamed_pair)[~near]] = False
        left, right = left[ok], right[ok]
    both_l = np.concatenate([left, right]).astype(np.intp)
    both_r = np.concatenate([right, left]).astype(np.intp)
    return _connected(both_l, both_r, n)


def _numbered(ways: list[Way], countries: list[tuple[str, object]]) -> tuple[list[tuple[tuple, list[int]]], set]:
    """The main-road ways joined by number: each numbered way's key is its first number, an unnamed way with no
    number takes the number of the road it meets end to end, then the ways of one number and country are split
    where their stretches are far apart (osm-lines' rules). Returns the groups, each (key, indexes), and the indexes
    used."""
    keys: dict[int, tuple | None] = {}
    for i, w in enumerate(ways):
        if w.layer != "main-roads":
            continue
        ref = first_ref(w.tags.get("ref"))
        if ref:
            keys[i] = ("ref", ref)
        elif not (w.tags.get("name") or "").strip():
            keys[i] = None
    if not any(k is not None for k in keys.values()):
        return [], set()
    link_unnamed(keys, {i: ways[i].shape for i in keys})
    used = sorted(i for i, k in keys.items() if k is not None)
    mids = [shapely.line_interpolate_point(ways[i].shape, 0.5, normalized=True) for i in used]
    country = dict(zip(used, countries_of(mids, countries)))
    by_key: dict[tuple, list[int]] = defaultdict(list)
    for i in used:
        by_key[(country[i], keys[i])].append(i)
    groups = []
    for (c, k), idx in by_key.items():
        for part in road_parts([ways[i].shape for i in idx]):
            groups.append(((c, k), [idx[j] for j in part]))
    return groups, set(used)


def join_ways(ways: list[Way], parishes: list[tuple[str, object]], countries: list[tuple[str, object]],
              gap_m: float = JOIN_GAP_M, meet_m: float = MEET_M, words: dict | None = None) \
        -> list[tuple[dict, object, list[int]]]:
    """The ways joined into features: each (record, line, its way numbers in order), in id order."""
    words = words or type_words()
    out = []
    numbered, used = _numbered(ways, countries)
    for (c, key), idx in numbered:
        g = _merge([ways[i].shape for i in idx])
        if g is None:
            continue
        wids = sorted(ways[i].id for i in idx)
        rec = line_record(f"osm:w{wids[0]}", {"layer": "main-roads", "key": "ref"}, key,
                          [ways[i].tags for i in idx], [words.get(ways[i].kind, ways[i].kind) for i in idx])
        if c:
            rec["country"] = c
        out.append((rec, g, wids))
    rest = [i for i in range(len(ways)) if i not in used]
    mids = [shapely.line_interpolate_point(ways[i].shape, 0.5, normalized=True) for i in rest]
    parish_of = _places_of(mids, parishes)
    for layer in LAYERS:
        idx = [k for k, i in enumerate(rest) if ways[i].layer == layer]
        if not idx:
            continue
        mine = [ways[rest[k]] for k in idx]
        for group in _groups_by_meeting(mine, [parish_of[k] for k in idx], gap_m, meet_m):
            members = [mine[j] for j in group]
            g = _merge([w.shape for w in members])
            if g is None:
                continue
            wids = sorted(w.id for w in members)
            name = (members[0].tags.get("name") or "").strip()
            kinds = [words.get(w.kind, w.kind) for w in members]
            if name:
                rec = line_record(f"osm:w{wids[0]}", {"layer": layer, "key": "name"}, ("name", name),
                                  [w.tags for w in members], kinds)
                ref, _n = most([first_ref(w.tags.get("ref")) for w in members])
                if ref:
                    rec["ref"] = ref
            else:
                kind, _n = most([w.kind for w in members])
                rec = {"id": f"osm:w{wids[0]}", "layer": layer, "name": unnamed_name(kind, words),
                       "type": words.get(kind, kind)}
            out.append((rec, g, wids))
    out.sort(key=lambda rgw: rgw[2][0])
    return out


# The stage ------------------------------------------------------------------------------------------------------

def _ways_from(raw_r: list[dict], raw_g: list) -> list[Way]:
    out = []
    for r, g in zip(raw_r, raw_g):
        tags = {k: r[k] for k in TAG_KEYS if r.get(k)}
        out.append(Way(int(r["id"].split(":w", 1)[1]), r["layer"], r["kind"], tags, g))
    return out


def run(ctx) -> None:
    s = ctx.settings
    request = {"tolerance_m": float(s.get("tolerance_m", TOLERANCE_M))}
    gap_m = float(s.get("join_gap_m", JOIN_GAP_M))
    meet_m = float(s.get("meet_m", MEET_M))
    ctx.progress.line("Reading every main road, street, track and path within the coverage.")
    out = osm_source.run_reading(ctx, "osm_streets", request)
    raw_r, raw_g = osm_source.load_boxes(out)
    ways = _ways_from(raw_r, raw_g)
    by_layer_ways: dict[str, int] = defaultdict(int)
    for w in ways:
        by_layer_ways[w.layer] += 1
    ctx.progress.line(f"Read {len(ways):,} ways: " + ", ".join(f"{by_layer_ways[k]:,} in {k}" for k in LAYERS)
                      + ". Joining them by number, by name, and unnamed ones within each parish.")

    p_r, p_g = features.load_layers(Path(ctx.previous), {"parishes", "countries"})
    parishes = [(r["id"], g) for r, g in zip(p_r, p_g) if r["layer"] == "parishes"]
    countries = [(r["id"], g) for r, g in zip(p_r, p_g) if r["layer"] == "countries"]
    if not parishes:
        ctx.progress.line("The stage before has no parishes, so unnamed ways that meet are joined however far "
                          "they reach.")
    joined = join_ways(ways, parishes, countries, gap_m, meet_m)
    del ways, raw_r, raw_g

    cov = osm_source.coverage_of(ctx)
    recs = [r for r, _g, _w in joined]
    cut_r, cut_g, cut_counts = osm_source.clip_to_coverage(recs, [g for _r, g, _w in joined], cov)
    way_ids = {r["id"]: w for r, _g, w in joined}
    for r in cut_r:
        r["source_key"] = s.get("source") or "planet"

    data = json.loads((Path(ctx.previous) / "features.json").read_text(encoding="utf-8"))
    have = {r["id"] for r in data["records"]}
    clash = [r["id"] for r in cut_r if r["id"] in have]
    if clash:
        ctx.progress.line(f"{len(clash):,} features already in the stage before, such as {clash[0]}, are not added "
                          "again.")
        keep = [i for i, r in enumerate(cut_r) if r["id"] not in have]
        cut_r, cut_g = [cut_r[i] for i in keep], [cut_g[i] for i in keep]
    del data

    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(Path(ctx.previous) / name, ctx.claim(Path(ctx.folder) / name))
    features.append(ctx.folder, cut_r, [shapely.to_wkb(g) for g in cut_g])
    kept_ways = {r["id"]: way_ids[r["id"]] for r in cut_r}
    ctx.claim(Path(ctx.folder) / WAYS).write_text(
        json.dumps({"about": "Each feature's OpenStreetMap way numbers, for the network graph (P4-T1d). The writing "
                             "stage does not read this file.", "ways": kept_ways}, sort_keys=True),
        encoding="utf-8", newline="\n")

    layers = {}
    for layer in LAYERS:
        mine = [(r, g) for r, g in zip(cut_r, cut_g) if r["layer"] == layer]
        kinds: dict[str, int] = defaultdict(int)
        for r, _g in mine:
            kinds[r["type"]] += 1
        layers[layer] = {"ways": by_layer_ways[layer], "features": len(mine),
                         "km": round(sum(length_km(g) for _r, g in mine), 1),
                         "partial": sum(1 for r, _g in mine if r.get("partial")),
                         "unnamed": sum(1 for r, _g in mine if r["name"] == unnamed_name_of(r)),
                         "by_type": dict(sorted(kinds.items()))}
    counts = {"layers": layers, "outside_coverage": cut_counts["dropped"], "already_in_pack": len(clash)}
    ctx.claim(Path(ctx.folder) / REPORT).write_text(
        json.dumps({"counts": counts}, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8", newline="\n")
    for layer, c in layers.items():
        ctx.progress.line(f"The layer {layer}: {c['ways']:,} ways joined into {c['features']:,} features, "
                          f"{c['km']:,.0f} km of line, {c['unnamed']:,} named by their type, {c['partial']:,} cut "
                          "by the coverage.")
    ctx.progress.line(f"{cut_counts['dropped']:,} features were outside the coverage. Every feature's way numbers "
                      f"are in {WAYS}, and the counts in {REPORT}.")


def unnamed_name_of(rec: dict) -> str:
    """The name an unnamed feature of rec's type has, to count the features named by their type."""
    text = rec.get("type") or ""
    return text[:1].upper() + text[1:]
