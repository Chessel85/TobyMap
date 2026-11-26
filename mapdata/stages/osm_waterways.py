"""Stage "osm-waterways": every other river and canal, and every stream, ditch and drain (P4-T1g, design
docs/plan/p4-t1-design.md 3.9; DAT-2, DAT-3).

In a regional pack, the unchanged osm-rivers stage makes the rivers the world pack has, joined by their Wikidata
link, with the world's ids. This stage reads every other waterway of OpenStreetMap within the coverage
(w[waterway=river,canal,stream,ditch,drain]), into two layers:

* rivers: waterway=river and canal, type river or canal.
* streams: waterway=stream, ditch and drain, type stream, ditch or drain.

A tidal channel, a weir, a dam and every other waterway value is not read.

A river way osm-rivers has already used is not read again: one whose Wikidata link is a river's of the stage
before, one whose id is a feature's id, or one that lies along a line of the stage before's rivers layer, within
used_within_m (5 metres) for used_share (nine tenths) of its length. (osm-rivers keeps no list of its ways, and its
code stays unchanged, so the line is the test.)

The ways are joined as osm-rivers joins a river's ways (its join_lines): ways of one name that meet, end to end or at
a shared point within meet_m (3 metres), again and again, each way kept in the direction it is drawn, which in
OpenStreetMap is the way the water flows. So each feature runs from source to mouth with its sections in order; a
water with branches is one feature of several lines. A named water of river and stream ways, such as Ober Water,
is one feature, in the layer and of the type of most of its length. Unnamed ways of one type that meet are joined
within one parish (the parishes layer of the stage before, a way being in the parish its middle is in), and named by
the type's words in the templates' details.unnamed_waterways: "Unnamed stream", "Ditch".

A feature takes the id of its smallest way, as in osm-lines. Every feature's way ids are kept in ways.json beside
features.json, as osm-streets keeps them; the writing stage never reads it. Each line is simplified to tolerance_m
(2 metres) as it is read, and cut to the coverage after joining; one the coverage cuts is partial. The stage writes
osm_waterways.json: for each layer, the ways read, the features made, the km of line, those named by their type and
those the coverage cut, and the river ways already used. The features of the stage before are kept, and the new
ones added after them, in id order.
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
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import osm_source
from mapdata.stages.osm_rivers import join_lines, length_km

REPORT = "osm_waterways.json"
WAYS = "ways.json"
LAYERS = ("rivers", "streams")
KINDS = {"river": "rivers", "canal": "rivers", "stream": "streams", "ditch": "streams", "drain": "streams"}
QUERY = "w[waterway=river,canal,stream,ditch,drain]"
TAG_KEYS = ("waterway", "name", "name:en", "wikidata")
TOLERANCE_M = 2.0
MEET_M = 3.0
USED_WITHIN_M = 5.0
USED_SHARE = 0.9
METRES_PER_DEGREE = 111_320.0


@dataclass
class Way:
    id: int          # the OpenStreetMap way's number
    layer: str       # rivers or streams
    kind: str        # river, canal, stream, ditch or drain
    tags: dict
    shape: object    # a line, in degrees, drawn the way the water flows


def unnamed_words() -> dict[str, str]:
    from mapcore.describe import templates

    return {k: str(v) for k, v in templates()["details"]["unnamed_waterways"].items()}


def fingerprint_extra(stage: dict) -> dict:
    """The names of unnamed waterways are written into the pack, so changing their words makes the stage run
    again."""
    return {"unnamed_words": unnamed_words()}


def name_of(tags: dict) -> str:
    return (tags.get("name:en") or tags.get("name") or "").strip()


# Reading --------------------------------------------------------------------------------------------------------

def read_job(source, request: dict, out: Path) -> None:
    """The waterways, one reading box at a time, each simplified and saved before the next box is read."""
    tol = float(request["tolerance_m"]) / METRES_PER_DEGREE
    seen: set[str] = set()
    boxes = request["reading_boxes"]
    for n, box in enumerate(boxes):
        recs, geoms = [], []
        for o in source.query(QUERY, box, seen):
            if o.kind != "way":   # a waterway drawn as an area is not a line
                continue
            kind = o.tags.get("waterway") or ""
            if kind not in KINDS:
                continue
            g = o.shape
            if g is None or g.is_empty or g.geom_type != "LineString":
                continue
            if tol:
                g = shapely.simplify(g, tol, preserve_topology=False)   # keeps the ends, so ways still meet
            if g.is_empty or len(g.coords) < 2:
                continue
            r = {"id": o.id, "layer": KINDS[kind], "kind": kind}
            r.update({k: o.tags[k] for k in TAG_KEYS if o.tags.get(k)})
            recs.append(r)
            geoms.append(g)
        osm_source.save_box(request, out, n, recs, geoms)
        source.say(f"Reading box {n + 1} of {len(boxes)}: {len(recs):,} rivers, canals, streams, ditches and "
                   "drains.")


# Ways already used by osm-rivers --------------------------------------------------------------------------------

def _flatten(xy):
    xy = xy.copy()
    xy[:, 0] *= np.cos(np.radians(xy[:, 1]))
    return xy


def _flat(geoms: list) -> np.ndarray:
    return shapely.transform(np.array(geoms, dtype=object), _flatten)


def already_used(ways: list[Way], before: list[tuple[dict, object]], within_m: float = USED_WITHIN_M,
                 share: float = USED_SHARE) -> set[int]:
    """The numbers of the river ways the stage before's rivers already hold: by a river's Wikidata link, by a
    feature's id, or by lying along a river's line, within within_m for share of the way's length."""
    rivers = [(r, g) for r, g in before if r.get("layer") == "rivers" and g is not None and not g.is_empty]
    links = {r["wikidata"] for r, _g in rivers if r.get("wikidata")}
    ids = {r["id"] for r, _g in before}
    used = set()
    rest = []
    for w in ways:
        if w.kind != "river":
            continue
        if (w.tags.get("wikidata") and w.tags["wikidata"] in links) or f"osm:w{w.id}" in ids:
            used.add(w.id)
        else:
            rest.append(w)
    if not rest or not rivers:
        return used
    zones = shapely.buffer(_flat([g for _r, g in rivers]), within_m / METRES_PER_DEGREE)
    tree = shapely.STRtree(zones)
    lines = _flat([w.shape for w in rest])
    near = defaultdict(list)
    for i, j in zip(*tree.query(lines, predicate="intersects").tolist()):
        near[i].append(j)
    for i, js in near.items():
        line = lines[i]
        zone = zones[js[0]] if len(js) == 1 else shapely.union_all(zones[js])
        if shapely.intersection(line, zone).length >= share * line.length:
            used.add(rest[i].id)
    return used


# Joining --------------------------------------------------------------------------------------------------------

def _parishes_of(ways: list[Way], parishes: list[tuple[str, object]]) -> list[int]:
    """The index of the parish each way's middle is in, or of the nearest; -1 with no parishes."""
    if not parishes:
        return [-1] * len(ways)
    mids = shapely.line_interpolate_point(np.array([w.shape for w in ways], dtype=object), 0.5, normalized=True)
    tree = shapely.STRtree([g for _id, g in parishes])
    out = [-1] * len(ways)
    pts, areas = tree.query(mids, predicate="intersects")
    for p, a in sorted(zip(pts.tolist(), areas.tolist())):
        if out[p] == -1:
            out[p] = a
    missing = [i for i, v in enumerate(out) if v == -1]
    if missing:
        nearest = tree.query_nearest(mids[missing], all_matches=False)
        for p, a in zip(nearest[0].tolist(), nearest[1].tolist()):
            out[missing[p]] = a
    return out


def _groups(ways: list[Way], parish: list[int], meet_m: float) -> list[list[int]]:
    """The indexes of ways joined: ways of one name, and unnamed ways of one type and parish, that come within
    meet_m of each other, connected again and again."""
    n = len(ways)
    if not n:
        return []
    keys = [("name", name_of(w.tags)) if name_of(w.tags) else ("unnamed", w.kind, parish[i])
            for i, w in enumerate(ways)]
    flat = _flat([w.shape for w in ways])
    left, right = shapely.STRtree(flat).query(flat, predicate="dwithin", distance=meet_m / METRES_PER_DEGREE)
    up = list(range(n))

    def top(i):
        while up[i] != i:
            up[i] = up[up[i]]
            i = up[i]
        return i

    for a, b in zip(left.tolist(), right.tolist()):
        if a < b and keys[a] == keys[b]:
            ta, tb = top(a), top(b)
            if ta != tb:
                up[max(ta, tb)] = min(ta, tb)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[top(i)].append(i)
    return list(groups.values())


def _most(values: list, weights: list[float]):
    totals: dict = defaultdict(float)
    for v, w in zip(values, weights):
        if v:
            totals[v] += w
    if not totals:
        return None
    return max(sorted(totals), key=lambda k: totals[k])


def join_ways(ways: list[Way], parishes: list[tuple[str, object]], meet_m: float = MEET_M,
              words: dict | None = None) -> list[tuple[dict, object, list[int]]]:
    """The ways joined into features: each (record, line, its way numbers in order), in id order."""
    words = words or unnamed_words()
    parish = _parishes_of(ways, parishes)
    out = []
    for group in _groups(ways, parish, meet_m):
        members = sorted((ways[i] for i in group), key=lambda w: w.id)
        g = join_lines([w.shape for w in members])
        if g is None:
            continue
        g = shapely.set_precision(g, 1e-7)
        lengths = [w.shape.length for w in members]
        layer = _most([w.layer for w in members], lengths)
        kind = _most([w.kind for w in members if w.layer == layer],
                     [n for w, n in zip(members, lengths) if w.layer == layer])
        wids = [w.id for w in members]
        name = name_of(members[0].tags)
        rec = {"id": f"osm:w{wids[0]}", "layer": layer, "name": name or words.get(kind, kind), "type": kind}
        if name:
            local = _most([(w.tags.get("name") or "").strip() for w in members], lengths)
            if local and local != name:
                rec["local_name"] = local
        q = _most([w.tags.get("wikidata") for w in members], lengths)
        if q:
            rec["wikidata"] = q
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
    meet_m = float(s.get("meet_m", MEET_M))
    words = unnamed_words()
    if set(KINDS) - set(words):
        raise BuildStopped("The templates (mapcore/describe/templates.yaml) give no words for some unnamed "
                           "waterways, under details.unnamed_waterways: " + ", ".join(sorted(set(KINDS) - set(words)))
                           + ". The osm-waterways stage cannot name the waterways it reads.")
    ctx.progress.line("Reading every river, canal, stream, ditch and drain within the coverage.")
    out = osm_source.run_reading(ctx, "osm_waterways", request)
    raw_r, raw_g = osm_source.load_boxes(out)
    ways = _ways_from(raw_r, raw_g)
    del raw_r, raw_g

    previous = Path(ctx.previous)
    b_r, b_g = features.load_layers(previous, {"rivers", "parishes"})
    data = json.loads((previous / "features.json").read_text(encoding="utf-8"))
    have = {r["id"] for r in data["records"]}
    del data
    before_rivers = [(r, g) for r, g in zip(b_r, b_g) if r["layer"] == "rivers"]
    before_rivers += [({"id": i}, None) for i in have]   # every id, so a way that is a feature already is used
    used = already_used(ways, before_rivers, float(s.get("used_within_m", USED_WITHIN_M)),
                        float(s.get("used_share", USED_SHARE)))
    by_layer_ways: dict[str, int] = defaultdict(int)
    for w in ways:
        by_layer_ways[w.layer] += 1
    ways = [w for w in ways if w.id not in used]
    ctx.progress.line(f"Read {sum(by_layer_ways.values()):,} ways: "
                      + ", ".join(f"{by_layer_ways[k]:,} in {k}" for k in LAYERS)
                      + f". {len(used):,} river ways are already in the rivers the stage before made, so are not "
                        "read again. Joining the rest by name, and unnamed ones within each parish.")
    parishes = [(r["id"], g) for r, g in zip(b_r, b_g) if r["layer"] == "parishes"]
    if not parishes:
        ctx.progress.line("The stage before has no parishes, so unnamed waterways that meet are joined however far "
                          "they reach.")
    joined = join_ways(ways, parishes, meet_m, words)
    del ways, b_r, b_g

    cov = osm_source.coverage_of(ctx)
    recs = [r for r, _g, _w in joined]
    cut_r, cut_g, cut_counts = osm_source.clip_to_coverage(recs, [g for _r, g, _w in joined], cov)
    way_ids = {r["id"]: w for r, _g, w in joined}
    for r in cut_r:
        r["source_key"] = s.get("source") or "planet"
    clash = [r["id"] for r in cut_r if r["id"] in have]
    if clash:
        ctx.progress.line(f"{len(clash):,} features already in the stage before, such as {clash[0]}, are not added "
                          "again.")
        keep = [i for i, r in enumerate(cut_r) if r["id"] not in have]
        cut_r, cut_g = [cut_r[i] for i in keep], [cut_g[i] for i in keep]

    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(previous / name, ctx.claim(Path(ctx.folder) / name))
    features.append(ctx.folder, cut_r, [shapely.to_wkb(g) for g in cut_g])
    kept_ways = {r["id"]: way_ids[r["id"]] for r in cut_r}
    ctx.claim(Path(ctx.folder) / WAYS).write_text(
        json.dumps({"about": "Each feature's OpenStreetMap way numbers, for the network graph (P4-T1g). The writing "
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
                         "unnamed": sum(1 for r, _g in mine if r["name"] == words.get(r["type"])),
                         "by_type": dict(sorted(kinds.items()))}
    counts = {"layers": layers, "already_used": len(used), "outside_coverage": cut_counts["dropped"],
              "already_in_pack": len(clash)}
    ctx.claim(Path(ctx.folder) / REPORT).write_text(
        json.dumps({"counts": counts}, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8", newline="\n")
    for layer, c in layers.items():
        ctx.progress.line(f"The layer {layer}: {c['ways']:,} ways joined into {c['features']:,} features, "
                          f"{c['km']:,.0f} km of line, {c['unnamed']:,} named by their type, {c['partial']:,} cut "
                          "by the coverage.")
    ctx.progress.line(f"{cut_counts['dropped']:,} features were outside the coverage. Every feature's way numbers "
                      f"are in {WAYS}, and the counts in {REPORT}.")
