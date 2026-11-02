"""Compare stage 1 built again with the faster methods against the build of 1 November.

Spike S2 (P0-T5), the PO's request of 2 November: the algorithms were made
faster, and stage 1 (the UK, France and Spain) was built again with them,
as s2-stage1-again. This reads both builds and writes a report of every
difference, in plain lines (DMT-2):

* time: the whole run and each step, against the 1 November run;
* the cut shapes: every area's land must be the same shape as the one
  cached on 1 November, apart from differences under a square metre;
* the coastline places: the same areas found at each, in the same order;
* the UK's islands: the same number of parts, named and unnamed, at each size;
* land in no country: still none; land in no region: the same slivers;
* neighbours: every layer still meets exactly after cleaning and simplifying;
* the packs: the same areas found at a grid of test points.

Two differences are expected and are not faults (the S2 findings, "Next:
faster algorithms, proved on stage 1"): areas are now measured on the
ellipsoid, so area figures move by a fraction of a percent; and the
counties layer follows discussion point 101, so it gains areas that level 6
left out. Shapes are compared by the area of their difference, measured the
new way for both.

It only reads the two builds, and writes comparison.txt and
comparison.json in the new build's output folder.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import time
from pathlib import Path

import numpy as np
import shapely
import yaml

from mapdata.paths import DataFolders
from mapdata.stages.geodesy import area_km2
from mapdata.stages.s2_stage1 import Log

OLD_NAME, NEW_NAME = "s2-stage1", "s2-stage1-again"
OLD_VERSION = "s2-stage1-v2"   # s2_stage1.VERSION on 1 November
SAME_M2 = 1.0                  # shapes differing by less than a square metre are the same
UK = "osm:r62149"
COUNTRIES = {"osm:r62149": "United Kingdom", "osm:r2202162": "France", "osm:r1311341": "Spain"}
ISLAND_KEYS = [("parts", "parts"), ("named_parts", "parts with a name"), ("unnamed_parts", "parts without a name"),
               ("at_least_1_hectare", "parts of 1 hectare or more"),
               ("unnamed_at_least_1_hectare", "unnamed parts of 1 hectare or more"),
               ("at_least_1_km2", "parts of 1 km2 or more"), ("at_least_20_km2", "parts of 20 km2 or more")]
# Test points for the packs: every GRID_STEP degrees in these boxes, and
# every SMALL_STEP in the small overseas ones.
GRID_STEP, SMALL_STEP = 0.3, 0.05
GRID_BOXES = {"the United Kingdom": (-8.7, 49.8, 2.0, 61.0), "France": (-5.3, 41.2, 9.8, 51.2),
              "Spain": (-9.5, 35.8, 4.5, 44.0), "the Canary Islands": (-18.3, 27.5, -13.3, 29.5)}
SMALL_BOXES = {"French Guiana": (-54.7, 2.0, -51.5, 6.0), "Guadeloupe": (-61.9, 15.8, -61.0, 16.6),
               "Martinique": (-61.3, 14.3, -60.8, 14.9), "Réunion": (55.2, -21.4, 55.9, -20.8),
               "Mayotte": (44.9, -13.1, 45.4, -12.6), "Gibraltar and Ceuta": (-5.45, 35.85, -5.25, 36.2)}


# Pure comparisons, each giving report lines and whether all matched -----------

def compare_islands(old: dict, new: dict) -> tuple[list[str], bool]:
    lines, same = [], True
    for key, words in ISLAND_KEYS:
        a, b = old.get(key), new.get(key)
        ok = a == b
        same &= ok
        lines.append(f"{'Same' if ok else 'DIFFERENT'}: {words}: {a:,} on 1 November, {b:,} now."
                     if isinstance(a, int) and isinstance(b, int) else
                     f"{'Same' if ok else 'DIFFERENT'}: {words}: {a} on 1 November, {b} now.")
    return lines, same


def match_slivers(old: list[dict], new: list[dict], near_deg: float = 0.0005, area_share: float = 0.02):
    """Pairs of slivers at the same place with about the same area: (matched, old only, new only).

    Areas were measured on a sphere on 1 November and on the ellipsoid now, so
    they may differ by a fraction of a percent.
    """
    if not old or not new:
        return 0, list(old), list(new)
    tree = shapely.STRtree(np.array([shapely.Point(*s["centre"]) for s in new], dtype=object))
    used: set[int] = set()
    old_only = []
    for s in old:
        hits = tree.query(shapely.Point(*s["centre"]).buffer(near_deg))
        best = None
        for h in hits.tolist():
            if h in used:
                continue
            a, b = s["area_km2"], new[h]["area_km2"]
            if abs(a - b) <= area_share * max(a, b, 1e-9):
                best = h
                break
        if best is None:
            old_only.append(s)
        else:
            used.add(best)
    new_only = [s for i, s in enumerate(new) if i not in used]
    return len(used), old_only, new_only


def compare_found(old: list[dict], new: list[dict], old_ids: set[str]) -> tuple[str, list[str]]:
    """Compare what a lookup found in each pack, in order.

    Returns "same", "added" (the same apart from counties that are not in
    the old pack at all, which discussion point 101 adds), or "different",
    and the names of any counties added.
    """
    old_names = [f["id"] for f in old]
    new_names = [f["id"] for f in new]
    if old_names == new_names:
        return "same", []
    added = [f for f in new if f["layer"] == "counties" and f["id"] not in old_ids]
    kept = [f["id"] for f in new if f not in added]
    if kept == old_names:
        return "added", [f["name"] for f in added]
    return "different", []


def grid_points() -> list[tuple[str, float, float]]:
    out = []
    for boxes, step in ((GRID_BOXES, GRID_STEP), (SMALL_BOXES, SMALL_STEP)):
        for where, (w, s, e, n) in boxes.items():
            for lon in np.arange(w, e + 1e-9, step):
                for lat in np.arange(s, n + 1e-9, step):
                    out.append((where, round(float(lon), 4), round(float(lat), 4)))
    return out


# Jobs for worker processes -----------------------------------------------------

def _shape_job(pairs: list[tuple[str, str, str]]) -> list[tuple[str, float, float, float]]:
    """(id, km2 of the difference, old km2, new km2) for each pair of cached shapes."""
    from mapdata.stages import clip

    out = []
    for key_id, old_path, new_path in pairs:
        a = clip.polygonal(pickle.loads(Path(old_path).read_bytes()))
        b = clip.polygonal(pickle.loads(Path(new_path).read_bytes()))
        diff = shapely.symmetric_difference(a, b)
        out.append((key_id, area_km2(diff) if not diff.is_empty else 0.0, area_km2(a), area_km2(b)))
    return out


def _lookup_job(old_pack: str, new_pack: str, points: list) -> list:
    from mapcore.packs.archive import Pack

    old, new = Pack(Path(old_pack)), Pack(Path(new_pack))
    try:
        return [(where, lon, lat, old.at(lon, lat), new.at(lon, lat)) for where, lon, lat in points]
    finally:
        old.close()
        new.close()


def _lookup_batch(args: tuple) -> list:
    return _lookup_job(*args)


# The run -------------------------------------------------------------------

def _old_cut_path(working: Path, area) -> Path:
    key = hashlib.sha1(shapely.to_wkb(area.geom) + OLD_VERSION.encode()).hexdigest()[:16]
    path = working / "clipped" / f"{area.id.replace(':', '_')}-{key}.pkl"
    if path.is_file():
        return path
    found = sorted((working / "clipped").glob(f"{area.id.replace(':', '_')}-*.pkl"))
    return found[-1] if found else path


def shape_pairs(folders: DataFolders) -> tuple[list, list[str]]:
    """Each area cut on 1 November, with the same area cut now: (id, name, old file, new file)."""
    from mapdata.stages import s2_stage

    old_work, new_work = folders.working / OLD_NAME, folders.working / NEW_NAME
    old_ex = sorted(old_work.glob("extract-*.pkl"))
    if not old_ex:
        raise SystemExit(f"The 1 November extract is missing from {old_work}.")
    countries, units, divisions, *_rest = pickle.loads(old_ex[-1].read_bytes())
    config = s2_stage.load_config(1)
    gol = folders.root / config["source_gol"]
    new_ex = s2_stage.extract_cache_path(config, folders, gol)
    if not new_ex.is_file():
        raise SystemExit(f"Stage 1 again has not been built: {new_ex} is missing.")
    ex = pickle.loads(new_ex.read_bytes())
    settings = {c["id"]: c for c in config["countries"]}
    new_by_id = {a.id: a for a in ex["countries"]}
    new_units = {u.id: u for u in ex["units"]}
    new_divs = {d.id: d for divs in ex["divisions"].values() for d in divs}
    region_level = config.get("region_level", 4)
    pairs, missing = [], []
    old_all = [(a, "country") for a in countries] + [(u, "unit") for u in units] + \
              [(d, f"level {lv}") for (_cid, lv), divs in divisions.items() for d in divs]
    seen = set()
    for area, kind in old_all:
        if area.id in seen:
            continue
        seen.add(area.id)
        old_path = _old_cut_path(old_work, area)
        if area.id in new_by_id:
            geom = s2_stage.limited(new_by_id[area.id].geom, settings[area.id].get("land_within"))
            new_path = s2_stage.cut_cache_path(new_work, area.id, geom)
        elif area.id in new_units:
            new_path = s2_stage.cut_cache_path(new_work, area.id, new_units[area.id].geom)
        elif area.id in new_divs:
            d = new_divs[area.id]
            prefix = d.id if d.level == region_level else "county"
            new_path = s2_stage.cut_cache_path(new_work, prefix, d.geom)
        else:
            missing.append(f"{area.name} ({area.id}, {kind}): not in the new build at all.")
            continue
        if not old_path.is_file() or not new_path.is_file():
            missing.append(f"{area.name} ({area.id}, {kind}): its cut shape is missing from the "
                           f"{'1 November' if not old_path.is_file() else 'new'} build.")
            continue
        pairs.append((area.id, area.tags.get("name:en") or area.name, str(old_path), str(new_path)))
    return pairs, missing


def run(folders: DataFolders, workers: int = 3) -> int:
    from mapdata import parallel
    from mapdata.stages import pack_write, s2_stage

    log = Log()
    old_out, new_out = folders.output / OLD_NAME, folders.output / NEW_NAME
    for path in (old_out / "summary.json", new_out / "summary.json"):
        if not path.is_file():
            log(f"{path} is missing, so there is nothing to compare.")
            return 2
    old = json.loads((old_out / "summary.json").read_text(encoding="utf-8"))
    new = json.loads((new_out / "summary.json").read_text(encoding="utf-8"))
    log("Spike S2: stage 1 built again with the faster methods, compared with the build of 1 November.")
    log("A line starting DIFFERENT is a difference that needs looking at. Expected differences are said to be so.")
    result: dict = {}
    faults = 0

    log.heading("Time")
    log(f"Whole run: {old['total_seconds'] / 60:.1f} minutes on 1 November, {new['total_seconds'] / 60:.1f} "
        f"minutes now. Peak memory: {old['peak_memory_mb']:,.0f} MB then, {new['peak_memory_mb']:,.0f} MB now "
        f"(the main process; workers are separate).")
    for step in sorted(set(old["timings"]) | set(new["timings"])):
        a, b = old["timings"].get(step), new["timings"].get(step)
        log(f"  {step}: " + (f"{a:.0f} seconds then" if a is not None else "not timed then")
            + ", " + (f"{b:.0f} seconds now." if b is not None else "not timed now."))
    result["time"] = {"old_seconds": old["total_seconds"], "new_seconds": new["total_seconds"]}

    log.heading("Cut shapes")
    t = time.perf_counter()
    pairs, missing = shape_pairs(folders)
    for line in missing:
        log(f"DIFFERENT: {line}")
    faults += len(missing)
    names = {p[0]: p[1] for p in pairs}
    pairs.sort(key=lambda p: -Path(p[2]).stat().st_size)
    batches = [pairs[k::max(1, workers * 3)] for k in range(max(1, workers * 3))]
    rows = []
    with parallel.pool(workers) as executor:
        for part in pack_write.executor_map(executor, _shape_job, [b for b in batches if b], workers):
            rows.extend(part)
    differ = [r for r in rows if r[1] * 1e6 >= SAME_M2]
    log(f"{len(rows)} areas compared in {time.perf_counter() - t:.0f} seconds. The same shape, to within a square "
        f"metre: {len(rows) - len(differ)}. Different: {len(differ)}.")
    for key_id, diff, a, b in sorted(differ, key=lambda r: -r[1]):
        log(f"DIFFERENT: {names[key_id]} ({key_id}): {diff * 1e6:,.1f} m2 differ; {a:,.3f} km2 then, {b:,.3f} km2 now.")
    biggest = max(rows, key=lambda r: r[1]) if rows else None
    if biggest and not differ:
        log(f"The largest difference is {biggest[1] * 1e6:.4f} m2, for {names[biggest[0]]}.")
    faults += len(differ)
    result["shapes"] = {"compared": len(rows), "different": [r[0] for r in differ], "missing": missing}

    log.heading("Coastline places")
    places = yaml.safe_load((s2_stage.ACCEPTANCE / "coastline_places.yaml").read_text(encoding="utf-8"))["places"]
    old_pack, new_pack = old_out / f"{OLD_NAME}-compact.pack", new_out / f"{NEW_NAME}-compact.pack"
    found = _lookup_job(str(old_pack), str(new_pack), [(p["name"], p["lon"], p["lat"]) for p in places])
    from mapcore.packs.archive import Pack
    op = Pack(old_pack)
    old_ids = {f["id"] for f in op.features}
    op.close()
    place_rows = []
    for name, _lon, _lat, a, b in found:
        verdict, added = compare_found(a, b, old_ids)
        heard = ", ".join(f["name"] for f in b) or "sea"
        if verdict == "same":
            log(f"Same: {name}: {heard}.")
        elif verdict == "added":
            log(f"Same, with a county added by discussion point 101 ({', '.join(added)}): {name}: {heard}.")
        else:
            faults += 1
            log(f"DIFFERENT: {name}: {', '.join(f['name'] for f in a) or 'sea'} then, {heard} now.")
        place_rows.append({"place": name, "verdict": verdict})
    log(f"Places passed: {old['places_passed']} of {old['places']} then, {new['places_passed']} of {new['places']} now.")
    result["places"] = place_rows

    log.heading("The UK's islands")
    lines, same = compare_islands(old["islands"], new["islands"].get(UK, {}))
    for line in lines:
        log(line)
    faults += 0 if same else 1
    log(f"Named islands and islets read from OSM: {old['islands'].get('named_features')} then, "
        f"{new['islands'].get(UK, {}).get('named_features')} now. Expected to differ: the new program keeps only "
        f"those inside the UK's own shape, not its whole bounding box, and uses English names where OSM has them.")
    result["islands_same"] = same

    log.heading("Land in no country")
    a, b = old["no_country"], new["no_country"]
    ok = len(a) == len(b) == 0 or (len(a) == len(b) and match_slivers(a, b)[0] == len(a))
    log(f"{'Same' if ok else 'DIFFERENT'}: parts of land within about 1 km of the three countries in no country: "
        f"{len(a)} then, {len(b)} now.")
    faults += 0 if ok else 1

    log.heading("Land in no region")
    region_rows = {}
    for cid, name in COUNTRIES.items():
        a = old["level_gaps"].get(f"{cid} level 4", [])
        b = new["region_gaps"].get(cid, [])
        matched, old_only, new_only = match_slivers(a, b)
        ok = not old_only and not new_only
        faults += 0 if ok else 1
        log(f"{'Same' if ok else 'DIFFERENT'}: {name}: {len(a)} slivers, {sum(s['area_km2'] for s in a):,.3f} km2 "
            f"then; {len(b)} slivers, {sum(s['area_km2'] for s in b):,.3f} km2 now; {matched} at the same place "
            f"with about the same area.")
        for s in (old_only[:5]):
            log(f"  Only then: {s['area_km2'] * 1e6:,.0f} m2 at {s['centre'][1]:.5f} north, {s['centre'][0]:.5f} east.")
        for s in (new_only[:5]):
            log(f"  Only now: {s['area_km2'] * 1e6:,.0f} m2 at {s['centre'][1]:.5f} north, {s['centre'][0]:.5f} east.")
        region_rows[cid] = {"then": len(a), "now": len(b), "matched": matched}
    result["region_gaps"] = region_rows

    log.heading("Neighbours after cleaning and simplifying (AD-16)")
    for c in new["coverage"]:
        ok = c["valid_cleaned"] and c["valid_after"] and c["overlap_km2"] < 1e-9
        faults += 0 if ok else 1
        log(f"{'Same' if ok else 'DIFFERENT'}: {c['layer']}: meets exactly after cleaning: "
            f"{'yes' if c['valid_cleaned'] else 'no'}; after simplifying: {'yes' if c['valid_after'] else 'no'}; "
            f"overlap {c['overlap_km2']:.3f} km2.")
    log("On 1 November every layer met exactly after cleaning and after simplifying, checked along every coast. "
        "Now each layer is checked within 5 km of its land borders, where neighbours meet.")

    log.heading("Counties (discussion point 101), an expected difference")
    for cid, c in new.get("counties", {}).items():
        log(f"{COUNTRIES.get(cid, cid)}: {c['count']} counties now, from levels "
            f"{', '.join(map(str, c['levels_used'])) or 'none'}"
            + (f", and {len(c['regions_used'])} regions used as their own county" if c["regions_used"] else "") + ".")
        for line in c["filled"][:15]:
            log(f"  {line}")
        if len(c["filled"]) > 15:
            log(f"  and {len(c['filled']) - 15} more.")

    log.heading("The packs at a grid of test points")
    t = time.perf_counter()
    points = grid_points()
    chunks = [points[k::max(1, workers * 4)] for k in range(max(1, workers * 4))]
    counts = {"same": 0, "added": 0, "different": 0}
    examples = []
    with parallel.pool(workers) as executor:
        for part in pack_write.executor_map(executor, _lookup_batch,
                                            [(str(old_pack), str(new_pack), c) for c in chunks if c], workers):
            for where, lon, lat, a, b in part:
                verdict, _added = compare_found(a, b, old_ids)
                counts[verdict] += 1
                if verdict == "different" and len(examples) < 20:
                    examples.append(f"{where}, {lat:.4f} north, {lon:.4f} east: "
                                    f"{', '.join(f['name'] for f in a) or 'sea'} then, "
                                    f"{', '.join(f['name'] for f in b) or 'sea'} now.")
    log(f"{len(points):,} test points, every {GRID_STEP} degrees across the three countries and every "
        f"{SMALL_STEP} degrees in the overseas regions, Gibraltar and Ceuta, in {time.perf_counter() - t:.0f} seconds.")
    log(f"The same areas found: {counts['same']:,}. The same apart from a county added by discussion point 101: "
        f"{counts['added']:,}. Different: {counts['different']:,}.")
    for line in examples:
        log(f"DIFFERENT: {line}")
    faults += counts["different"]
    result["grid"] = counts

    log.heading("Result")
    if faults:
        log(f"{faults} differences need looking at; each is on a line starting DIFFERENT.")
    else:
        log("No differences, apart from the expected ones: the results are the same as on 1 November.")
    result["faults"] = faults
    (new_out / "comparison.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    (new_out / "comparison.txt").write_text("\n".join(log.lines) + "\n", encoding="utf-8")
    log(f"Report: {new_out / 'comparison.txt'}")
    return 0 if not faults else 1
