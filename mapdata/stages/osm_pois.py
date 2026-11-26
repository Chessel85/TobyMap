"""Stage "osm-pois": points of interest in four layers, and places for a pack read from the raw samples (P4-T1f,
design docs/plan/p4-t1-design.md 3.10; DAT-2, DAT-3).

In a regional pack only, this stage reads OpenStreetMap's points of interest within the coverage into four layers of
places, by the point of interest categories of mapdata/config/poi_categories.yaml:

* stops: bus stops, tram stops, railway stations, crossings and taxi ranks.
* shops-food: shops, cafes, restaurants, pubs, bars, fast food and ice cream.
* services: post offices, pharmacies, doctors, banks, libraries, toilets, places of worship, hotels, schools mapped as
  a point, car parks and the like.
* street-furniture: post boxes, benches, bins, recycling, drinking water and telephones.

The categories are tried in the table's order and the first that matches wins, so no object is in two categories. A
node is a place where it is; an area, such as a shop in a building or a car park, is a place at a point inside it, as
the osm-places stage makes one. A place's type is its category's words from mapcore/describe/templates.yaml, under
poi_categories, words ("bus stop"); its name is OpenStreetMap's (name:en first), or, with none, those words with a
capital first letter ("Bench"). An id already in the stage before is skipped. Each place is cut to the coverage.

With the setting places, the stage instead reads named places, as the osm-places stage does, through osm_source, so
a pack built from the raw samples (the test region) can have its villages: osm-places reads only the planet file.
places has layer, queries (each with query and type, and population: true to keep OpenStreetMap's population) and
within (the area layers each place keeps, as osm-places' within).

The features of the stage before are kept, and the new ones added after them, in id order. The stage writes
osm_pois.json: the counts by layer and by category.
"""
from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path

import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import osm_places, osm_source

REPORT = "osm_pois.json"
RECORD = "poi_categories.yaml"
LAYERS = ("stops", "shops-food", "services", "street-furniture")
KINDS = ("node", "area")
ANY = "*"


# The record -----------------------------------------------------------------------------------------------------

def record_path() -> Path:
    from mapdata.paths import CONFIG_DIR

    return CONFIG_DIR / RECORD


def category_words() -> dict[str, str]:
    """The words of each category, by its key, from the templates."""
    from mapcore.describe import templates

    return {str(k): str(v) for k, v in (templates().get("poi_categories") or {}).get("words", {}).items()}


def load_record(path: Path | None = None) -> dict:
    """The point of interest categories, checked: each has a key with words, one of the four layers, and tags."""
    import yaml

    p = path or record_path()
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    words = category_words()
    seen = set()
    for c in data.get("categories") or []:
        for k in ("key", "layer", "tags"):
            if k not in c:
                raise BuildStopped(f"The point of interest categories, {p.name}, give the category {c} no {k}.")
        if c["key"] in seen:
            raise BuildStopped(f"The point of interest categories, {p.name}, have the category {c['key']} twice.")
        seen.add(c["key"])
        if c["layer"] not in LAYERS:
            raise BuildStopped(f"The point of interest categories, {p.name}, put {c['key']} in {c['layer']}, which "
                               f"is not one of {', '.join(LAYERS)}.")
        if c["key"] not in words:
            raise BuildStopped(f"The category {c['key']} of {p.name} has no words in mapcore/describe/templates.yaml, "
                               "under poi_categories, words. Add them there.")
        if not c["tags"] or not all(isinstance(t, dict) and t for t in c["tags"]):
            raise BuildStopped(f"The category {c['key']} of {p.name} needs tags: a list of alternatives, each one "
                               "or more tags.")
        c["tags"] = [{str(k): str(v) for k, v in t.items()} for t in c["tags"]]
        c["kinds"] = list(c.get("kinds") or KINDS)
        if any(k not in KINDS for k in c["kinds"]):
            raise BuildStopped(f"The category {c['key']} of {p.name} has kinds {c['kinds']}; use node, area or both.")
        c["words"] = words[c["key"]]
    data.setdefault("categories", [])
    return data


def fingerprint_extra(stage: dict) -> dict:
    """The table and the words are part of what the stage reads and writes, so changing either reads the points of
    interest again."""
    return {"poi_categories": record_path().read_text(encoding="utf-8"), "words": category_words()}


def tag_text(alternative: dict) -> str:
    """One alternative's tags as plain text, such as "public_transport=platform and bus=yes"."""
    return " and ".join(f"{k}={'any value' if v == ANY else v}" for k, v in alternative.items())


def _filter(k: str, v: str) -> str:
    return f"[{k}]" if v == ANY else f"[{k}={v}]"


def query_for(categories: list[dict]) -> str:
    """The query that reads every category: the values of one key together, an alternative of several tags by
    itself, nodes and areas."""
    plain: dict[str, list[str]] = defaultdict(list)
    whole: set[str] = set()
    rest: list[tuple[str, dict]] = []
    for c in categories:
        letters = "".join(k[0] for k in KINDS if k in c["kinds"])
        for alt in c["tags"]:
            if len(alt) == 1 and letters == "na":
                (k, v), = alt.items()
                if v == ANY:
                    whole.add(k)
                elif v not in plain[k]:
                    plain[k].append(v)
            else:
                rest.append((letters, alt))
    extra: list[str] = []
    for letters, alt in rest:   # one already read by a single tag of its own, such as a church, is not asked again
        if any(k in whole or v in plain.get(k, ()) for k, v in alt.items()):
            continue
        q = letters + "".join(_filter(k, v) for k, v in alt.items())
        if q not in extra:
            extra.append(q)
    parts = [f"na[{k}]" for k in sorted(whole)]
    parts += [f"na[{k}={','.join(v)}]" for k, v in plain.items() if k not in whole]
    return ", ".join(parts + extra)


# Classifying ----------------------------------------------------------------------------------------------------

def _has(tags: dict, k: str, v: str) -> bool:
    value = tags.get(k)
    if v == ANY:
        return value is not None and value != "no"
    return value == v


def classify(tags: dict, kind: str, categories: list[dict]) -> dict | None:
    """The category of an object with these tags, a node or an area: the first that matches, or None."""
    for c in categories:
        if kind not in c.get("kinds", KINDS):
            continue
        if any(all(_has(tags, k, v) for k, v in alt.items()) for alt in c["tags"]):
            return c
    return None


# Reading --------------------------------------------------------------------------------------------------------

def _point(o) -> shapely.Point | None:
    g = o.shape
    if g is None or g.is_empty:
        return None
    p = g if g.geom_type == "Point" else shapely.point_on_surface(shapely.make_valid(g))
    if p.is_empty:
        return None
    return shapely.Point(round(p.x, 7), round(p.y, 7))


def _read_places(source, request: dict, out: Path) -> None:
    """Named places, as the osm-places stage reads them, one reading box at a time."""
    places = request["places"]
    seen: set[str] = set()
    boxes = request["reading_boxes"]
    for n, box in enumerate(boxes):
        recs, geoms = [], []
        for q in places["queries"]:
            for o in source.query(q["query"], box, seen):
                if o.kind == "way":
                    continue
                rec = osm_places.place_record(o.id, o.tags, places["layer"], q["type"])
                p = _point(o)
                if rec is None or p is None:
                    continue
                if q.get("population"):
                    pop = osm_places.population(o.tags.get("population"))
                    if pop is not None:
                        rec["population"] = pop
                        rec["population_source"] = "OpenStreetMap"
                recs.append(rec)
                geoms.append(p)
        osm_source.save_box(request, out, n, recs, geoms)
        source.say(f"Reading box {n + 1} of {len(boxes)}: {len(recs):,} places.")


def read_job(source, request: dict, out: Path) -> None:
    """The points of interest, one reading box at a time, each classified and saved before the next box is read."""
    if request.get("places"):
        _read_places(source, request, out)
        return
    categories = request["record"]["categories"]
    seen: set[str] = set()
    boxes = request["reading_boxes"]
    for n, box in enumerate(boxes):
        recs, geoms = [], []
        for o in source.query(request["query"], box, seen):
            if o.kind not in KINDS:
                continue
            c = classify(o.tags, o.kind, categories)
            p = _point(o) if c is not None else None
            if p is None:
                continue
            t = o.tags
            r = {"id": o.id, "layer": c["layer"], "type": c["words"], "category": c["key"],
                 "name": t.get("name:en") or t.get("name") or "", "local_name": t.get("name") or ""}
            if t.get("wikidata"):
                r["wikidata"] = t["wikidata"]
            recs.append(r)
            geoms.append(p)
        osm_source.save_box(request, out, n, recs, geoms)
        source.say(f"Reading box {n + 1} of {len(boxes)}: {len(recs):,} points of interest.")


# The stage ------------------------------------------------------------------------------------------------------

def make_records(recs: list[dict], geoms: list, have: set, source_key: str):
    """The new features: an id in have is skipped; an unnamed place has its type's words with a capital first
    letter. Returns the records and points in id order, and the number skipped."""
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
        for k in ("wikidata", "partial", "population", "population_source", "within"):
            if r.get(k):
                rec[k] = r[k]
        out.append((rec, g))
    out.sort(key=lambda rg: rg[0]["id"])
    return [r for r, _g in out], [g for _r, g in out], skipped


def _keep(ctx, new_r: list[dict], new_g: list) -> None:
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(Path(ctx.previous) / name, ctx.claim(Path(ctx.folder) / name))
    features.append(ctx.folder, new_r, [shapely.to_wkb(g) for g in new_g])


def _have(ctx) -> set:
    data = json.loads((Path(ctx.previous) / "features.json").read_text(encoding="utf-8"))
    return {r["id"] for r in data["records"]}


def _run_places(ctx, places: dict) -> None:
    layer = places.get("layer")
    if layer not in ctx.pack.layers:
        raise BuildStopped(f"The osm-pois stage's places setting writes to the layer {layer}, which the pack's layer "
                           "groups do not define. Add the layer, or correct the stage's settings.")
    if not places.get("queries"):
        raise BuildStopped("The osm-pois stage's places setting needs queries, each with query and type.")
    request = {"places": {"layer": layer, "queries": list(places["queries"])}}
    ctx.progress.line(f"Reading the places of the layer {layer} within the coverage: "
                      + ", ".join(q["query"] for q in places["queries"]) + ".")
    out = osm_source.run_reading(ctx, "osm_pois", request)
    recs, geoms = osm_source.load_boxes(out)
    cut_r, cut_g, cut_counts = osm_source.clip_to_coverage(recs, geoms, osm_source.coverage_of(ctx))
    order = list(places.get("within") or [])
    if order:
        p_r, p_g = features.load_layers(Path(ctx.previous), set(order))
        areas = [(r["layer"], r["id"], g) for r, g in zip(p_r, p_g) if r["layer"] in order]
        for r, w in zip(cut_r, osm_places.areas_within(cut_g, areas, order)):
            r["within"] = w
    new_r, new_g, skipped = make_records(cut_r, cut_g, _have(ctx), ctx.settings.get("source") or "planet")
    _keep(ctx, new_r, new_g)
    kinds: dict[str, int] = defaultdict(int)
    for r in new_r:
        kinds[r["type"]] += 1
    counts = {"layer": layer, "places": len(new_r), "by_type": dict(sorted(kinds.items())),
              "in_no_area": sum(1 for r in new_r if order and not r.get("within")),
              "outside_coverage": cut_counts["dropped"], "already_in_pack": skipped}
    ctx.claim(Path(ctx.folder) / REPORT).write_text(json.dumps({"counts": counts}, indent=1, ensure_ascii=False,
                                                               sort_keys=True), encoding="utf-8", newline="\n")
    ctx.progress.line(f"Places in the layer {layer}: {len(new_r):,}: "
                      + ", ".join(f"{n:,} of type {k}" for k, n in sorted(kinds.items())) + ".")
    if order:
        ctx.progress.line(f"Each place has the areas of {', '.join(order)} it is in: {counts['in_no_area']:,} places "
                          "are in none of them.")
    ctx.progress.line(f"{cut_counts['dropped']:,} were outside the coverage; {skipped:,} were already in the pack.")


def run(ctx) -> None:
    s = ctx.settings
    if s.get("places"):
        _run_places(ctx, s["places"])
        return
    record = load_record()
    request = {"record": record, "query": query_for(record["categories"])}
    ctx.progress.line(f"Reading the points of interest within the coverage, {len(record['categories'])} categories: "
                      f"{request['query']}.")
    out = osm_source.run_reading(ctx, "osm_pois", request)
    recs, geoms = osm_source.load_boxes(out)
    by_category: dict[str, int] = defaultdict(int)
    for r in recs:
        by_category[r.pop("category")] += 1
    cut_r, cut_g, cut_counts = osm_source.clip_to_coverage(recs, geoms, osm_source.coverage_of(ctx))
    new_r, new_g, skipped = make_records(cut_r, cut_g, _have(ctx), s.get("source") or "planet")
    _keep(ctx, new_r, new_g)

    layers = {}
    for layer in LAYERS:
        mine = [r for r in new_r if r["layer"] == layer]
        layers[layer] = {"places": len(mine), "named_by_type": sum(1 for r in mine if not r.get("local_name")
                                                                   and r["name"].casefold() == r["type"].casefold())}
    counts = {"layers": layers, "by_category": {c["key"]: by_category.get(c["key"], 0) for c in record["categories"]},
              "outside_coverage": cut_counts["dropped"], "already_in_pack": skipped}
    ctx.claim(Path(ctx.folder) / REPORT).write_text(json.dumps({"counts": counts}, indent=1, ensure_ascii=False,
                                                               sort_keys=True), encoding="utf-8", newline="\n")
    for layer, c in layers.items():
        ctx.progress.line(f"The layer {layer}: {c['places']:,} places, {c['named_by_type']:,} of them named by their "
                          "type.")
    ctx.progress.line(f"{cut_counts['dropped']:,} were outside the coverage; {skipped:,} were already in the pack. "
                      f"The counts by category are in {REPORT}.")
