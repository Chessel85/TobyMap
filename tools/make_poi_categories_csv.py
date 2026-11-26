"""Make docs/plan/p4-t1f-poi-categories.csv, the point of interest categories for the product owner, from
mapdata/config/poi_categories.yaml (P4-T1f, design docs/plan/p4-t1-design.md 3.10).

One row per category, in the table's order: category (its key), words (its type, from mapcore/describe/templates.yaml),
layer, tags (its alternatives, separated by "; or "), count in the rehearsal, count in the United Kingdom.

The counts are not in the table, so the tool keeps those already in the CSV, by category, and the CSV can be made again
identical from the table. With --count <a GeoDesk library of the United Kingdom, such as uk.gol>, it counts them
afresh: each object is counted in the first category that matches it, as the osm-pois stage does, in the whole
library (the United Kingdom) and within the rehearsal's box (the box of hampshire-isle-of-wight.yaml's osm-areas
stage). Counting reads the library in this process, so run it with nothing else heavy running.

    .venv\\Scripts\\python.exe tools\\make_poi_categories_csv.py                 (keep the counts)
    .venv\\Scripts\\python.exe tools\\make_poi_categories_csv.py --count <uk.gol>
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from mapdata.stages import osm_pois  # noqa: E402

CSV_PATH = REPO / "docs" / "plan" / "p4-t1f-poi-categories.csv"
HEADER = ["category", "words", "layer", "tags", "count in the rehearsal", "count in the United Kingdom"]
REHEARSAL = REPO / "mapdata" / "config" / "packs" / "hampshire-isle-of-wight.yaml"


def read_counts(path: Path = CSV_PATH) -> dict[str, tuple[str, str]]:
    """The counts already in the CSV, {category: (rehearsal, United Kingdom)}; none if there is no CSV."""
    if not Path(path).is_file():
        return {}
    rows = list(csv.reader(io.StringIO(Path(path).read_bytes().decode("utf-8"))))
    return {r[0]: (r[4], r[5]) for r in rows[1:] if len(r) >= 6}


def make_csv(counts: dict[str, tuple[str, str]]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(HEADER)
    for c in osm_pois.load_record()["categories"]:
        tags = "; or ".join(osm_pois.tag_text(alt) for alt in c["tags"])
        if c["kinds"] == ["node"]:
            tags += " (mapped as a point only)"
        rehearsal, uk = counts.get(c["key"], ("", ""))
        w.writerow([c["key"], c["words"], c["layer"], tags, rehearsal, uk])
    return out.getvalue()


def rehearsal_box() -> list[float]:
    import yaml

    data = yaml.safe_load(REHEARSAL.read_text(encoding="utf-8"))
    return next(s["box"] for s in data["stages"] if s["stage"] == "osm-areas")


def count(gol: Path) -> dict[str, tuple[str, str]]:
    """Each category's count in the library and within the rehearsal's box, the first category that matches each
    object, as the stage counts them."""
    import geodesk

    categories = osm_pois.load_record()["categories"]
    keys = sorted({k for c in categories for alt in c["tags"] for k in alt})
    query = osm_pois.query_for(categories)
    world = geodesk.Features(str(gol))
    w, s, e, n = rehearsal_box()
    uk = {c["key"]: 0 for c in categories}
    box = {c["key"]: 0 for c in categories}
    started = time.perf_counter()
    seen = 0
    for f in world(query):
        if f.is_node:
            kind = "node"
        elif f.is_area:
            kind = "area"
        else:
            continue
        tags = {}
        for k in keys:
            v = f.tags[k]
            if v:
                tags[k] = str(v)
        c = osm_pois.classify(tags, kind, categories)
        if c is None:
            continue
        uk[c["key"]] += 1
        lon, lat = (f.lon, f.lat)
        if w <= lon <= e and s <= lat <= n:
            box[c["key"]] += 1
        seen += 1
        if seen % 250_000 == 0:
            print(f"Counted {seen:,} points of interest in {time.perf_counter() - started:.0f} seconds.", flush=True)
    print(f"Counted {seen:,} points of interest in {time.perf_counter() - started:.0f} seconds.", flush=True)
    return {k: (str(box[k]), str(uk[k])) for k in uk}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--count", type=Path, help="a GeoDesk library of the United Kingdom, such as uk.gol, to count "
                                                "each category in")
    args = ap.parse_args(argv)
    counts = count(args.count) if args.count else read_counts()
    CSV_PATH.write_bytes(make_csv(counts).encode("utf-8"))
    print(f"Wrote {CSV_PATH.relative_to(REPO)}: {len(osm_pois.load_record()['categories'])} categories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
