"""Stage "local-areas": every administrative level below the counties (P4-T1b, design docs/plan/p4-t1-design.md 3.5).

A regional pack's districts and parishes, as OpenStreetMap holds them, by the local levels record
(mapdata/config/local_levels.yaml): for each country, the admin levels of its districts layer and of its parishes
layer, the name of land in no parish, and the plain words for OpenStreetMap's designation tags.

1. The areas at the record's levels are read within the coverage, one reading box at a time, through
   mapdata.stages.osm_source (the planet file in a short-lived process, or the raw samples for the test region).
2. Each is given to the county of the stage before that holds most of it, so a district is never outside its
   county, and only the county's land is kept: the counties are already cut to the land (AD-15).
3. Inside each county, the county's outline and every district's and parish's outline are joined into faces, the
   smallest shapes no outline crosses. Each face is in one district, or in none.
4. Slivers: a stretch of a county's land in no district, or of a district's land (or a county's land in no
   district) in no parish, that is under sliver_km2 or narrower on average than sliver_width_m, goes to the
   neighbour of that layer with the longest shared edge. Each is listed in the log and in local_areas.json.
5. Gaps: larger land in no parish becomes one area for each district (or each county with no districts), named
   by the record's gap name, such as "Unparished area", with id "unparished:" and the district's id. So every point
   of the land is in exactly one area of the parishes layer.
6. Shared edges (AD-16): every parish, and every gap, inside a county is simplified as one coverage, with the
   county's outline kept as it is (shapely.coverage_simplify at tolerance_m, 10 metres). A district is the join of
   its parishes and gaps, and its county's districts join to the county, so they meet exactly, with no gap and no
   overlap.
7. Records: layer districts or parishes; type and tier_name, the designation tag in plain words; parent, the area
   of the layer above that holds it; wikidata from the tag. A feature cut by the coverage is partial.

The features of the stage before are kept, and the new ones added after them.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely
from shapely.errors import GEOSException

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import osm_source
from mapdata.stages.clip import polygonal

RECORD = "local_levels.yaml"
REPORT = "local_areas.json"
LAYERS = ("districts", "parishes")
TIER_KEY = {"districts": "district_tier", "parishes": "parish_tier"}
METRES_PER_DEGREE = 111_320.0
GRID = 1e-7          # snapping for the faces, used only if joining the outlines exactly fails
TOLERANCE_M = 10.0
SLIVER_KM2 = 0.1
SLIVER_WIDTH_M = 200.0


# The record -----------------------------------------------------------------------------------------------------

def record_path() -> Path:
    from mapdata.paths import CONFIG_DIR

    return CONFIG_DIR / RECORD


def load_record(path: Path | None = None) -> dict:
    """The local levels record, checked: each country has its levels as lists of whole numbers, and a reason."""
    import yaml

    p = path or record_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    countries = data.get("countries") or {}
    for cid, entry in countries.items():
        for layer in LAYERS:
            levels = entry.get(layer) or []
            if not isinstance(levels, list) or not all(isinstance(v, int) and not isinstance(v, bool)
                                                       for v in levels):
                raise BuildStopped(f"The local levels record, {p.name}, gives {cid}'s {layer} as {levels}: it must "
                                   "be a list of admin levels, whole numbers, such as [8].")
        if not entry.get("why"):
            raise BuildStopped(f"The local levels record, {p.name}, gives no reason (why) for {cid}.")
    return {"countries": {str(k): v for k, v in countries.items()}}


def fingerprint_extra(stage: dict) -> dict:
    """The record is part of what the stage reads, so changing it reads the areas again."""
    return {"local_levels": record_path().read_text(encoding="utf-8")}


def type_words(designation: str | None, entry: dict, layer: str) -> str:
    """OpenStreetMap's designation in plain words: from the record's types, else with its underscores as spaces,
    else the record's word for the layer's tier."""
    if designation:
        return str((entry.get("types") or {}).get(designation) or designation.replace("_", " "))
    return str(entry.get(TIER_KEY[layer]) or layer[:-1])


# Reading --------------------------------------------------------------------------------------------------------

def query_for(levels: list[int]) -> str:
    return f"a[boundary=administrative][admin_level={','.join(str(v) for v in levels)}]"


def _level(text) -> int | None:
    try:
        return int(str(text).split(";")[0].strip())
    except ValueError:
        return None


def read_job(source, request: dict, out: Path) -> None:
    """The areas at the request's levels, one reading box at a time, each box saved before the next."""
    query = query_for(request["levels"])
    seen: set[str] = set()
    boxes = request["reading_boxes"]
    for n, box in enumerate(boxes):
        recs, geoms = [], []
        for o in source.query(query, box, seen):
            if o.kind != "area":
                continue
            g = polygonal(shapely.make_valid(o.shape))
            level = _level(o.tags.get("admin_level"))
            if g.is_empty or level is None:
                continue
            t = o.tags
            r = {"id": o.id, "level": level, "name": t.get("name:en") or t.get("name") or "",
                 "local_name": t.get("name") or ""}
            for key in ("designation", "wikidata"):
                if t.get(key):
                    r[key] = t[key]
            recs.append(r)
            geoms.append(g)
        osm_source.save_box(request, out, n, recs, geoms)
        source.say(f"Reading box {n + 1} of {len(boxes)}: {len(recs)} areas.")


# The rules ------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Rules:
    sliver_km2: float = SLIVER_KM2
    sliver_width_m: float = SLIVER_WIDTH_M
    tolerance_m: float = TOLERANCE_M


@dataclass
class Read:
    """An area as read: its id, the layer it goes into, its names, its tags and its shape."""
    id: str
    layer: str
    name: str
    local_name: str
    tags: dict
    geom: object
    partial: bool = False
    extra: dict = field(default_factory=dict)


def km2(g) -> float:
    if g is None or g.is_empty:
        return 0.0
    lat = (g.bounds[1] + g.bounds[3]) / 2
    return g.area * (METRES_PER_DEGREE / 1000) ** 2 * math.cos(math.radians(lat))


def width_m(g) -> float:
    """Average width: twice the area over the outline's length, in metres, at the shape's latitude (the join's
    rule)."""
    k = math.cos(math.radians((g.bounds[1] + g.bounds[3]) / 2))
    h = shapely.transform(g, lambda xy: xy * np.array([k, 1.0]))
    return 2 * h.area / max(h.length, 1e-12) * METRES_PER_DEGREE


def faces_of(county, shapes: list) -> np.ndarray:
    """The county cut into faces by every outline: the smallest shapes no outline crosses, together exactly the
    county."""
    box = shapely.box(*county.bounds).buffer(1e-6, join_style="mitre")
    lines = [county.boundary] + [shapely.clip_by_rect(g.boundary, *box.bounds) for g in shapes]
    lines = [g for g in lines if g is not None and not g.is_empty]
    try:
        noded = shapely.union_all(lines)
    except GEOSException:
        noded = shapely.union_all(lines, grid_size=GRID)
    faces = np.array([f for f in shapely.get_parts(shapely.polygonize(list(shapely.get_parts(noded))))
                      if f.area > 0], dtype=object)
    if not len(faces):
        return faces
    shapely.prepare(county)
    inside = shapely.contains(county, shapely.point_on_surface(faces))
    return faces[inside]


def labels_of(faces: np.ndarray, shapes: list) -> list[int | None]:
    """For each face, the index of the shape that holds it (the first, by index, if several do), or None."""
    out: list[int | None] = [None] * len(faces)
    if not len(faces) or not shapes:
        return out
    points = shapely.point_on_surface(faces)
    tree = shapely.STRtree(np.array(shapes, dtype=object))
    f_idx, s_idx = tree.query(points, predicate="within")
    for f, s in sorted(zip(f_idx.tolist(), s_idx.tolist())):
        if out[f] is None or s < out[f]:
            out[f] = s
    return out


def neighbours_of(faces: np.ndarray) -> list[list[tuple[int, float]]]:
    """For each face, the faces it shares an edge with, and the edge's length in degrees."""
    out: list[list[tuple[int, float]]] = [[] for _ in range(len(faces))]
    if len(faces) < 2:
        return out
    a, b = shapely.STRtree(faces).query(faces, predicate="intersects")
    keep = a < b
    a, b = a[keep], b[keep]
    edges = shapely.boundary(faces)
    lengths = shapely.length(shapely.intersection(edges[a], edges[b]))
    for i, j, length in zip(a.tolist(), b.tolist(), lengths.tolist()):
        if length > 0:
            out[i].append((j, length))
            out[j].append((i, length))
    return out


def settle(faces, labels: list, units: list, near: list, rules: Rules, give_all: bool = False):
    """Faces with no label, joined into stretches of land (faces of the same unit that share an edge): a sliver
    goes to the label, in its unit, with the longest shared edge; so does every stretch when give_all. Returns the
    new labels, the slivers as (faces, label, km2) and the stretches left, each a list of faces."""
    labels = list(labels)
    waiting = [i for i, lab in enumerate(labels) if lab is None]
    group = {i: i for i in waiting}

    def top(i):
        while group[i] != i:
            group[i] = group[group[i]]
            i = group[i]
        return i

    for i in waiting:
        for j, _length in near[i]:
            if j in group and units[j] == units[i]:
                a, b = top(i), top(j)
                if a != b:
                    group[max(a, b)] = min(a, b)
    stretches: dict[int, list[int]] = defaultdict(list)
    for i in waiting:
        stretches[top(i)].append(i)
    slivers, left = [], []
    for key in sorted(stretches):
        comp = stretches[key]
        held = set(comp)
        edges: dict = defaultdict(float)
        for i in comp:
            for j, length in near[i]:
                if j not in held and labels[j] is not None and units[j] == units[i]:
                    edges[labels[j]] += length
        shape = shapely.union_all(faces[comp])
        size = km2(shape)
        thin = give_all or size < rules.sliver_km2 or width_m(shape) < rules.sliver_width_m
        if thin and edges:
            best = max(sorted(edges, key=str), key=lambda k: edges[k])
            for i in comp:
                labels[i] = best
            slivers.append((comp, best, size))
        else:
            left.append(comp)
    return labels, slivers, left


def _record(a: Read, layer: str, parent: str, entry: dict) -> dict:
    words = type_words(a.tags.get("designation"), entry, layer)
    r = {"id": a.id, "layer": layer, "name": a.name, "local_name": a.local_name, "type": words,
         "tier_name": words, "parent": parent}
    if a.tags.get("wikidata"):
        r["wikidata"] = a.tags["wikidata"]
    if a.partial:
        r["partial"] = True
    r.update(a.extra)
    return r


def _at(g) -> list[float]:
    p = shapely.point_on_surface(g)
    return [round(p.y, 5), round(p.x, 5)]


def settle_county(county_id: str, county, districts: list[Read], parishes: list[Read], entry: dict,
                  rules: Rules) -> tuple[list[tuple[dict, object]], dict]:
    """A county's districts and parishes, settled as the module's notes say: each sliver given to its neighbour,
    land in no parish as one gap area for each district, all simplified as one coverage with the county's outline
    kept. entry is the country's record merged with its part's. Returns (record, shape) pairs, districts first,
    and a report: slivers, gaps and what was left out."""
    report: dict = {"slivers": [], "gaps": [], "left_out": []}
    county = polygonal(shapely.make_valid(county))
    if county.is_empty:
        return [], report
    d_shapes = [polygonal(shapely.make_valid(d.geom)) for d in districts]
    p_shapes = [polygonal(shapely.make_valid(p.geom)) for p in parishes]
    faces = faces_of(county, d_shapes + p_shapes)
    if not len(faces):
        return [], report
    near = neighbours_of(faces)
    n = len(faces)

    # Districts: each face in one district or none; slivers to the neighbouring district.
    d_label = labels_of(faces, d_shapes) if districts else [None] * n
    d_label, slivers, _left = settle(faces, d_label, [0] * n, near, rules)
    for comp, best, size in slivers:
        report["slivers"].append({"layer": "districts", "km2": round(size, 4), "given_to": districts[best].id,
                                  "at": _at(shapely.union_all(faces[comp])), "county": county_id})

    # Parishes: each parish belongs to the unit (a district, or the county's land in no district) holding most of
    # it, and is kept only there.
    COUNTY = -1
    units = [COUNTY if d is None else d for d in d_label]
    p_raw = labels_of(faces, p_shapes) if parishes else [None] * n
    share: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for i, p in enumerate(p_raw):
        if p is not None:
            share[p][units[i]] += faces[i].area
    home = {p: max(sorted(s), key=lambda u: s[u]) for p, s in share.items()}
    p_label = [p if p is not None and home[p] == units[i] else None for i, p in enumerate(p_raw)]
    gap_name = entry.get("gap_name")
    p_label, slivers, left = settle(faces, p_label, units, near, rules, give_all=not gap_name)
    for comp, best, size in slivers:
        if gap_name or size < rules.sliver_km2:
            report["slivers"].append({"layer": "parishes", "km2": round(size, 4), "given_to": parishes[best].id,
                                      "at": _at(shapely.union_all(faces[comp])), "county": county_id})
        else:
            report["gaps"].append({"km2": round(size, 4), "given_to": parishes[best].id,
                                   "at": _at(shapely.union_all(faces[comp])), "county": county_id})

    def unit_id(u):
        return county_id if u == COUNTY else districts[u].id

    # The pieces of the coverage: each parish, each unit's gap, and land with no area (a part wholly in parishes
    # where OpenStreetMap leaves a whole district in none), so the districts' edges are simplified with the rest.
    pieces: dict[tuple, list[int]] = defaultdict(list)
    for i in range(n):
        if p_label[i] is not None:
            pieces[("parish", p_label[i])].append(i)
    for comp in left:
        u = units[comp[0]]
        pieces[("gap" if gap_name else "none", u)].extend(comp)
    keys = sorted(pieces, key=lambda k: (k[0], k[1]))
    joined = [shapely.coverage_union_all(faces[sorted(pieces[k])]) for k in keys]
    tol = rules.tolerance_m / METRES_PER_DEGREE
    simple = list(shapely.coverage_simplify(np.array(joined, dtype=object), tol, simplify_boundary=False))

    out_d: list[tuple[dict, object]] = []
    out_p: list[tuple[dict, object]] = []
    by_unit: dict[int, list] = defaultdict(list)
    for k, g in zip(keys, simple):
        g = polygonal(g)
        if g.is_empty:
            continue
        kind, which = k
        if kind == "parish":
            u = home[which]
            by_unit[u].append(g)
            out_p.append((_record(parishes[which], "parishes", unit_id(u), entry), g))
        elif kind == "gap":
            by_unit[which].append(g)
            gap_type = entry.get("gap_type") or gap_name.lower()
            r = {"id": f"unparished:{unit_id(which)}", "layer": "parishes", "name": gap_name, "type": gap_type,
                 "tier_name": gap_type, "parent": unit_id(which)}
            if which != COUNTY and districts[which].partial:
                r["partial"] = True
            out_p.append((r, g))
            report["gaps"].append({"id": r["id"], "km2": round(km2(g), 4), "parent": unit_id(which)})
        else:
            by_unit[which].append(g)
            report["left_out"].append({"why": "land in no parish, in a part wholly in parishes",
                                       "km2": round(km2(g), 4), "parent": unit_id(which), "at": _at(g)})
    for u in sorted(k for k in by_unit if k != COUNTY):
        g = polygonal(shapely.coverage_union_all(by_unit[u]))
        out_d.append((_record(districts[u], "districts", county_id, entry), g))
    for d, a in enumerate(districts):
        if d not in by_unit:
            report["left_out"].append({"id": a.id, "why": "a district with no land of its own in its county",
                                       "parent": county_id})
    for p, a in enumerate(parishes):
        if p not in home or not any(lab == p for lab in p_label):
            report["left_out"].append({"id": a.id, "why": "a parish with no land of its own in its district",
                                       "parent": county_id})
    out_d.sort(key=lambda rg: rg[0]["id"])
    out_p.sort(key=lambda rg: (rg[0]["parent"], rg[0]["id"]))
    return out_d + out_p, report


# The stage ------------------------------------------------------------------------------------------------------

def _country_and_part(county: dict, by_id: dict, countries: dict) -> tuple[str | None, str | None]:
    """The country of a county (its id in the record) and the id of the part above it, such as England."""
    seen = []
    r = county
    for _ in range(6):
        if r is None:
            break
        seen.append(r["id"])
        if r["layer"] == "countries":
            break
        r = by_id.get(r.get("parent"))
    country = next((i for i in seen if i in countries), None)
    if country is None:
        return None, None
    parts = countries[country].get("parts") or {}
    return country, next((i for i in seen if i in parts), None)


def entry_for(countries: dict, country: str, part: str | None) -> dict:
    """A country's record merged with its part's: the part's words win."""
    entry = {k: v for k, v in countries[country].items() if k != "parts"}
    if part:
        entry.update((countries[country].get("parts") or {}).get(part) or {})
    if "gap_name" not in entry:
        entry["gap_name"] = None
    return entry


def assign(areas: list[Read], counties: list[tuple[dict, object]]) -> dict[int, list[Read]]:
    """Each area given to the county (by index) that holds most of it; an area in no county is not given."""
    out: dict[int, list[Read]] = defaultdict(list)
    if not counties or not areas:
        return out
    shapes = np.array([g for _r, g in counties], dtype=object)
    tree = shapely.STRtree(shapes)
    for a in areas:
        idx = tree.query(a.geom, predicate="intersects").tolist()
        if not idx:
            continue
        if len(idx) == 1:
            out[idx[0]].append(a)
            continue
        sizes = shapely.area(shapely.intersection(shapes[idx], a.geom))
        best = max(sorted(idx), key=lambda i: sizes[idx.index(i)])
        if sizes[idx.index(best)] > 0:
            out[best].append(a)
    return out


def run(ctx) -> None:
    s = ctx.settings
    rules = Rules(float(s.get("sliver_km2", SLIVER_KM2)), float(s.get("sliver_width_m", SLIVER_WIDTH_M)),
                  float(s.get("tolerance_m", TOLERANCE_M)))
    record = load_record()
    countries = record["countries"]
    levels = sorted({lv for e in countries.values() for layer in LAYERS for lv in e.get(layer) or []})
    if not levels:
        raise BuildStopped("The local levels record gives no levels for any country, so the local-areas stage has "
                           "nothing to read.")
    ctx.progress.line(f"Reading the administrative areas at levels {', '.join(map(str, levels))}, within the "
                      "coverage.")
    out = osm_source.run_reading(ctx, "local_areas", {"levels": levels})
    raw_r, raw_g = osm_source.load_boxes(out)
    cov = osm_source.coverage_of(ctx)
    cut_r, _cut_g, _counts = osm_source.clip_to_coverage(raw_r, raw_g, cov)
    partial = {r["id"] for r in cut_r if r.get("partial")}
    inside = {r["id"] for r in cut_r}

    records, geoms = features.load(ctx.previous)
    by_id = {r["id"]: r for r in records}
    counties = [(r, g) for r, g in zip(records, geoms) if r["layer"] == "counties"]
    county_entry: dict[int, dict] = {}
    for k, (r, _g) in enumerate(counties):
        country, part = _country_and_part(r, by_id, countries)
        if country is not None:
            county_entry[k] = entry_for(countries, country, part)
    in_record = [counties[k] for k in sorted(county_entry)]
    keys = sorted(county_entry)

    report: dict = {"counts": {}, "slivers": [], "gaps": [], "left_out": []}
    areas: list[Read] = []
    level_layers = {lv: layer for e in countries.values() for layer in LAYERS for lv in e.get(layer) or []}
    for r, g in zip(raw_r, raw_g):
        if r["id"] not in inside:
            continue
        if not r.get("name"):
            report["left_out"].append({"id": r["id"], "why": "no name", "level": r["level"]})
            continue
        tags = {k: r[k] for k in ("designation", "wikidata") if r.get(k)}
        areas.append(Read(r["id"], level_layers.get(r["level"], ""), r["name"], r.get("local_name") or r["name"],
                          {**tags, "admin_level": r["level"]}, g, r["id"] in partial))
    given = assign(areas, in_record)
    new: list[tuple[dict, object]] = []
    gone = {a.id for a in areas} - {a.id for k in given for a in given[k]}
    for oid in sorted(gone):
        report["left_out"].append({"id": oid, "why": "in no county of the pack"})
    for n, (k, (crec, cgeom)) in enumerate(zip(keys, in_record)):
        entry = county_entry[k]
        mine = given.get(n) or []
        ds = sorted((a for a in mine if a.tags["admin_level"] in (entry.get("districts") or [])), key=lambda a: a.id)
        ps = sorted((a for a in mine if a.tags["admin_level"] in (entry.get("parishes") or [])), key=lambda a: a.id)
        out_c, rep = settle_county(crec["id"], cgeom, ds, ps, entry, rules)
        for key in ("slivers", "gaps", "left_out"):
            report[key] += rep[key]
        for r, g in out_c:
            r["source_key"] = s.get("source") or "planet"
        new += out_c
        if ds or ps:
            ctx.progress.log(f"{crec['name']} ({crec['id']}): {len(ds)} districts and {len(ps)} parishes read; "
                             f"{sum(1 for r, _g in out_c if r['layer'] == 'districts')} districts and "
                             f"{sum(1 for r, _g in out_c if r['layer'] == 'parishes')} parish-layer areas made.")
    new_d = [x for x in new if x[0]["layer"] == "districts"]
    new_p = [x for x in new if x[0]["layer"] == "parishes"]
    report["counts"] = {"districts": len(new_d), "parishes": len(new_p),
                        "gap_areas": sum(1 for r, _g in new_p if r["id"].startswith("unparished:")),
                        "read": len(raw_r), "slivers": len(report["slivers"])}
    features.save(ctx.folder, records + [r for r, _g in new_d + new_p], geoms + [g for _r, g in new_d + new_p],
                  ctx.claim)
    ctx.claim(ctx.folder / REPORT).write_text(json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True),
                                              encoding="utf-8", newline="\n")
    c = report["counts"]
    ctx.progress.line(f"Local areas, from {c['read']:,} administrative areas read: districts, {c['districts']:,}; "
                      f"areas in the parishes layer, {c['parishes']:,}, of them land in no parish, {c['gap_areas']:,}; "
                      f"slivers given to the neighbour with the longest shared edge, {c['slivers']:,}; areas left "
                      f"out, {len(report['left_out']):,}. Each is listed in {REPORT}.")
    for sl in report["slivers"]:
        ctx.progress.log(f"Sliver of the {sl['layer']} layer, {sl['km2']} km2 at {sl['at'][0]} north, "
                         f"{sl['at'][1]} east, given to {sl['given_to']}.")
    for lo in report["left_out"]:
        ctx.progress.log(f"Left out: {lo.get('id', '')} {lo['why']}.")
