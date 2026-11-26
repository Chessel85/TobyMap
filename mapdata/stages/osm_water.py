"""Stage "osm-water": every other lake, pond, reservoir and basin (P4-T1c, design docs/plan/p4-t1-design.md 3.6;
DAT-1, DAT-3, DP87).

In a regional pack, the osm-layer stage reads the named lakes, reservoirs and lagoons with the world's queries and
ids, of any size. This stage reads every other water area of OpenStreetMap within the coverage, of any size, into
the layer lakes:

* Read: a[natural=water], a[landuse=reservoir,basin] and a[water=pond], through mapdata.stages.osm_source (the
  planet file in a short-lived process, or the raw samples for the test region), one reading box at a time.
* Left out: an area whose water tag is in the setting leave_out (river, if not given): a river's area belongs to
  the river's line, and at the coast it is the land polygons' business.
* Skipped: an id already in the stage before, such as a lake osm-layer read with the world's id, so no lake is read
  twice.
* Type, from the tags: lake, pond, reservoir, basin or lagoon (TYPES; any other water value is a lake).
* Name: OpenStreetMap's (name:en first, as osm-areas does), or where it has none, the type's words from the
  templates' details.unnamed: "Pond", "Unnamed lake".
* Shape: simplified to tolerance_m (5 metres if not given), keeping every pond however small, then cut to the
  coverage; a feature the coverage cuts is partial.

The drawing's size rule leaves small ones out at wide zooms, as for every area. The stage writes osm_water.json: the
counts (added, by type, already read, rivers left out, cut by the coverage). The features of the stage before are
kept, and the new ones added after them, in id order.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import osm_source
from mapdata.stages.clip import polygonal

REPORT = "osm_water.json"
LAYER = "lakes"
QUERY = "a[natural=water], a[landuse=reservoir,basin], a[water=pond]"
LEAVE_OUT = ("river",)
TOLERANCE_M = 5.0
METRES_PER_DEGREE = 111_320.0
# OpenStreetMap's water values, and the type each gives; any other is a lake.
TYPES = {"lake": "lake", "oxbow": "lake", "lagoon": "lagoon",
         "pond": "pond", "fishpond": "pond", "reflecting_pool": "pond", "stream_pool": "pond", "moat": "pond",
         "reservoir": "reservoir",
         "basin": "basin", "wastewater": "basin", "settling_basin": "basin"}
LANDUSE_TYPES = {"reservoir": "reservoir", "basin": "basin"}


def unnamed_words() -> dict[str, str]:
    from mapcore.describe import templates

    return {k: str(v) for k, v in templates()["details"]["unnamed"].items() if k != "island"}


def fingerprint_extra(stage: dict) -> dict:
    """The names of unnamed water are written into the pack, so changing their words makes the stage run again."""
    return {"unnamed_words": unnamed_words()}


def type_of(tags: dict) -> str:
    water = tags.get("water")
    if water:
        return TYPES.get(water, "lake")
    return LANDUSE_TYPES.get(tags.get("landuse") or "", "lake")


def left_out(tags: dict, leave_out) -> bool:
    return (tags.get("water") or "") in set(leave_out)


# Reading --------------------------------------------------------------------------------------------------------

def read_job(source, request: dict, out: Path) -> None:
    """The water areas, one reading box at a time, each box saved before the next. A river's area is counted, not
    kept."""
    tol = float(request["tolerance_m"]) / METRES_PER_DEGREE
    leave = tuple(request["leave_out"])
    seen: set[str] = set()
    boxes = request["reading_boxes"]
    for n, box in enumerate(boxes):
        recs, geoms = [], []
        rivers = 0
        for o in source.query(QUERY, box, seen):
            if o.kind != "area":
                continue
            t = o.tags
            if left_out(t, leave):
                rivers += 1
                continue
            g = o.shape
            if tol:
                g = shapely.simplify(g, tol, preserve_topology=True)
            g = polygonal(shapely.make_valid(g))
            if g.is_empty:
                continue
            r = {"id": o.id, "type": type_of(t), "name": t.get("name:en") or t.get("name") or "",
                 "local_name": t.get("name") or ""}
            if t.get("wikidata"):
                r["wikidata"] = t["wikidata"]
            recs.append(r)
            geoms.append(shapely.set_precision(g, 1e-7))
        recs.append({"id": f"count:rivers:{n}", "rivers_left_out": rivers})
        geoms.append(shapely.Polygon())
        osm_source.save_box(request, out, n, recs, geoms)
        source.say(f"Reading box {n + 1} of {len(boxes)}: {len(recs) - 1} water areas, and {rivers} river areas "
                   "left out.")


# The stage ------------------------------------------------------------------------------------------------------

def make_records(raw_r: list[dict], raw_g: list, have: set, words: dict, source_key: str):
    """The new features from the water areas read: an id in have is skipped; a name is OSM's or the type's
    words. Returns the records and shapes, in id order, the number skipped and the number with no name."""
    out = []
    skipped = unnamed = 0
    for r, g in zip(raw_r, raw_g):
        if r["id"] in have:
            skipped += 1
            continue
        kind = r["type"]
        name = r.get("name") or words.get(kind) or words["lake"]
        rec = {"id": r["id"], "layer": LAYER, "name": name, "type": kind, "source_key": source_key}
        if r.get("local_name") and r["local_name"] != name:
            rec["local_name"] = r["local_name"]
        unnamed += not r.get("name")
        for k in ("wikidata", "partial"):
            if r.get(k):
                rec[k] = r[k]
        out.append((rec, g))
    out.sort(key=lambda rg: rg[0]["id"])
    return [r for r, _g in out], [g for _r, g in out], skipped, unnamed


def run(ctx) -> None:
    s = ctx.settings
    leave = s.get("leave_out", list(LEAVE_OUT))
    request = {"tolerance_m": float(s.get("tolerance_m", TOLERANCE_M)), "leave_out": list(leave or [])}
    ctx.progress.line(f"Reading every other lake, pond, reservoir and basin, within the coverage: {QUERY}.")
    out = osm_source.run_reading(ctx, "osm_water", request)
    raw_r, raw_g = osm_source.load_boxes(out)
    rivers = sum(int(r.get("rivers_left_out", 0)) for r in raw_r if r["id"].startswith("count:"))
    pairs = [(r, g) for r, g in zip(raw_r, raw_g) if not r["id"].startswith("count:")]
    cov = osm_source.coverage_of(ctx)
    cut_r, cut_g, cut_counts = osm_source.clip_to_coverage([r for r, _g in pairs], [g for _r, g in pairs], cov)

    data = json.loads((Path(ctx.previous) / "features.json").read_text(encoding="utf-8"))
    have = {r["id"] for r in data["records"]}
    words = unnamed_words()
    if "lake" not in words:
        raise BuildStopped("The templates (mapcore/describe/templates.yaml) give no words for an unnamed lake, "
                           "details.unnamed.lake, so the osm-water stage cannot name the water it reads.")
    records, geoms, skipped, unnamed = make_records(cut_r, cut_g, have, words, s.get("source") or "planet")

    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(Path(ctx.previous) / name, ctx.claim(Path(ctx.folder) / name))
    features.append(ctx.folder, records, [shapely.to_wkb(g) for g in geoms])
    by_type: dict[str, int] = {}
    for r in records:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    counts = {"read": len(pairs), "added": len(records), "by_type": by_type, "already_read": skipped,
              "left_out_river": rivers, "outside_coverage": cut_counts["dropped"],
              "partial": sum(1 for r in records if r.get("partial")),
              "unnamed": unnamed}
    ctx.claim(Path(ctx.folder) / REPORT).write_text(
        json.dumps({"counts": counts}, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8", newline="\n")
    ctx.progress.line(f"Water areas, from {counts['read']:,} read: {counts['added']:,} added to the layer {LAYER} ("
                      + ", ".join(f"{n:,} of type {k}" for k, n in sorted(by_type.items()))
                      + f"), of them {counts['unnamed']:,} with no name in OpenStreetMap; {skipped:,} already in the "
                      f"pack, so not read twice; {rivers:,} river areas left out; {counts['outside_coverage']:,} "
                      f"outside the coverage. The counts are in {REPORT}.")
