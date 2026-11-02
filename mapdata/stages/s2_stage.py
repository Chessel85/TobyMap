"""Spike S2, stages 2 and 3 (architecture 12.3, P0-T5).

Stage 2 is Sweden and Norway: shared islands and a very complex coast.
Stage 3 is Fiji, Russia, the USA, Kiribati and Antarctica: the 180 degree
line and the South Pole (architecture 6.13, AD-17).

Each stage is described by a settings file, mapdata/config/s2_stage<N>.yaml.
The run follows stage 1's method (mapdata/stages/s2_stage1.py), with what
stage 1 taught:

* The planet file is read in its own short-lived process (spike-s2-extract),
  because GeoDesk gives its memory back only when the process ends.
* The reading boxes for the land polygons are worked out from the shapes
  being built, and read in one pass of the file.
* The counties layer follows discussion point 101: level 6, gaps filled by
  level 7 then 8, then the region itself, with a record of the levels used
  for each country (mapdata/config/county_levels.yaml).
* Each layer is cleaned, then simplified as one coverage.

Everything it writes is inside the data folder's tobymap folder, except the
counties record, which is part of the pipeline's settings.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import shapely
import yaml

from mapdata.parallel import memory_mb
from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.stages import antimeridian, boundaries, clip, counties as countiesmod, land as landmod, pack_write
from mapdata.stages.geodesy import area_km2, areas_km2, distance_km
from mapdata.stages.s2_stage1 import Log, cached, coverage_report, english, peak_memory_mb, pictures

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE = ROOT / "tests" / "acceptance"
RECORD = CONFIG_DIR / "county_levels.yaml"
VERSION = "s2-stage-v1"          # change to discard the clipped caches
EXTRACT_VERSION = "s2-extract-v2"  # change to read the planet file again
FAR_KM = 1000


LOW_MEMORY_MB = 3000


# The guard pauses while the planet file is read in its own process. GeoDesk
# maps the file into memory, which Windows counts as in use although it can
# take it back at any time; on 2 November that stopped stage 4 wrongly. The
# reading process gives everything back when it ends.
GUARD = {"paused": False}


def start_memory_guard(log: Log, report: Path) -> None:
    """Stop the build cleanly if the laptop runs short of memory.

    On 2 November two builds running together ran the laptop short of memory
    and were stopped from outside, with nothing in their reports. This checks
    every two seconds and, below LOW_MEMORY_MB available, writes the report
    so far with the reason, and ends the build.
    """
    import os
    import threading

    def watch():
        while True:
            time.sleep(2)
            if GUARD["paused"]:
                continue
            mine, free = memory_mb()
            if free and free < LOW_MEMORY_MB:
                log(f"Stopped: the computer has only {free:,.0f} MB of memory free, and this build is using "
                    f"{mine:,.0f} MB. Nothing is lost; cached steps are kept for the next run.")
                report.write_text("\n".join(log.lines) + "\n", encoding="utf-8")
                # Where the build was, for whoever looks into it next.
                import faulthandler
                with open(report.with_name("stopped-at.txt"), "w", encoding="utf-8") as f:
                    faulthandler.dump_traceback(file=f, all_threads=True)
                os._exit(3)

    threading.Thread(target=watch, daemon=True).start()


def with_polar_cap(tiles: np.ndarray):
    """The land tiles, with the South Pole's cap added if they stop short of it.

    Spike S2 stage 3 found that the OSM land polygons stop at 86 degrees
    south, so the South Pole was in the sea and Antarctica was short by
    about 620,000 km2. Returns the tiles and the latitude they stopped at,
    or None if no cap was needed.
    """
    if len(tiles) == 0:
        return tiles, None
    south = float(shapely.bounds(tiles)[:, 1].min())
    if south <= -89.999 or south > -80:
        return tiles, None
    cap = shapely.box(-180.0, -90.0, 180.0, south + 0.0005)  # overlaps slightly, as land tiles do
    return np.concatenate([tiles, np.array([cap], dtype=object)]), south


# Stage 1 has its own program (s2_stage1.py) and settings (s2_stage1.yaml),
# kept as they were for the 1 November baseline. Built by this program, it
# uses s2_stage1_again.yaml.
CONFIG_FILES = {1: "s2_stage1_again.yaml"}


def load_config(stage: int) -> dict:
    path = CONFIG_DIR / CONFIG_FILES.get(stage, f"s2_stage{stage}.yaml")
    if not path.is_file():
        raise SystemExit(f"No settings for stage {stage}: {path} is missing.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def part_boxes(geom, pad: float = 0.05, join: float = 1.0) -> list[list[float]]:
    """Boxes round the parts of a shape, with boxes near each other joined."""
    if geom is None or geom.is_empty:
        return []
    boxes = [shapely.box(*p.bounds).buffer(join, join_style="mitre") for p in shapely.get_parts(geom)]
    out = []
    for g in shapely.get_parts(shapely.union_all(boxes)):
        w, s, e, n = g.bounds
        w, s, e, n = w + join - pad, s + join - pad, e - join + pad, n - join + pad
        out.append([max(-180.0, w), max(-90.0, s), min(180.0, e), min(90.0, n)])
    return out


def _box_union(boxes):
    return shapely.union_all([shapely.box(*b) for b in boxes]) if boxes else None


def limited(geom, boxes):
    """The part of a shape inside some boxes, or the whole shape if there are none."""
    if not boxes:
        return geom
    return clip.polygonal(shapely.intersection(geom, _box_union(boxes)))


# Extract: runs in its own process ------------------------------------------

def extract(config: dict, gol: Path) -> dict:
    import geodesk

    record = countiesmod.load_record(RECORD)
    lines: list[str] = []
    repairs: list[str] = []
    world = geodesk.Features(str(gol))
    countries = []
    for c in config["countries"]:
        countries.append(boundaries.relation(world, c["id"], c["name"], 2, repairs))
    lines.append(f"Countries: {', '.join(english(a) for a in countries)}.")
    divisions: dict = {}
    named: dict = {}
    region_level = config.get("region_level", 4)
    for c in config["countries"]:
        if not c.get("divisions"):
            continue
        country = next(a for a in countries if a.id == c["id"])
        whole = part_boxes(country.geom)
        region_boxes = c.get("region_boxes") or whole
        county_boxes = c.get("county_boxes") or region_boxes
        found = boundaries.divisions(world, country, region_level, repairs, boxes=region_boxes)
        divisions[(country.id, region_level)] = found
        lines.append(f"{english(country)}, level {region_level}: {len(found)} areas.")
        levels, _ = countiesmod.levels_for(record, country.id)
        for level in sorted(set(levels) | set(countiesmod.DEFAULT_LEVELS)):
            found = boundaries.divisions(world, country, level, repairs, boxes=county_boxes)
            divisions[(country.id, level)] = found
            lines.append(f"{english(country)}, level {level}: {len(found)} areas"
                         + (" in the area checked for counties." if c.get("county_boxes") else "."))
        if c.get("islands"):
            prepared = country.geom
            shapely.prepare(prepared)
            points, seen = [], set()
            for w, s, e, n in whole:
                box = geodesk.Box(west=w, south=s, east=e, north=n)
                for f in world("na[place=island],na[place=islet]")(box):
                    name = str(f.tags["name:en"] or f.tags["name"])
                    if not name or f.id in seen:
                        continue
                    seen.add(f.id)
                    pt = (shapely.Point(f.lon, f.lat) if f.is_node
                          else shapely.point_on_surface(geodesk.from_mercator(f.shape)))
                    if shapely.contains(prepared, pt):
                        points.append((name, pt))
            named[country.id] = points
            lines.append(f"{english(country)}: {len(points)} named islands and islets in OSM.")
    units = read_units(world, config, repairs) if config.get("units") else []
    if units:
        lines.append(f"Country units: {', '.join(u.tags['unit_name'] for u in units)}.")
    return {"countries": countries, "divisions": divisions, "named": named, "repairs": repairs, "lines": lines,
            "units": units}


def read_units(world, config: dict, repairs: list[str]) -> list:
    """The country units (country_units.yaml) of the stage's countries, which
    replace them in the Countries layer (architecture 6.12, DP86)."""
    data = yaml.safe_load((CONFIG_DIR / "country_units.yaml").read_text(encoding="utf-8"))
    ids = {c["id"] for c in config["countries"]}
    out = []
    for u in data["units"]:
        if u["replaces"] not in ids:
            continue
        for part in u["parts"]:
            feature = world.relation(int(part["id"].removeprefix("osm:r")))
            if feature is None:
                raise SystemExit(f"{part['id']} ({part['name']}) is not in the GOL file.")
            area = boundaries._to_area(feature, int(str(feature.tags["admin_level"]) or 3), u["replaces"], repairs)
            area.tags["unit_name"] = part["name"]
            area.tags["unit_type"] = part["type"]
            area.tags["sovereign"] = u["sovereign"]
            out.append(area)
    return out


def sovereigns() -> dict:
    """Sovereign states recorded for level 2 areas that are not their own, such as Gibraltar."""
    data = yaml.safe_load((CONFIG_DIR / "country_units.yaml").read_text(encoding="utf-8"))
    return data.get("sovereigns") or {}


def run_extract(stage: int, folders: DataFolders) -> int:
    """The entry point of the short-lived extract process."""
    config = load_config(stage)
    gol = folders.root / config["source_gol"]
    path = extract_cache_path(config, folders, gol)
    result = extract(config, gol)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL))
    tmp.replace(path)
    print(f"Extract finished: {len(result['countries'])} countries, "
          f"{sum(len(v) for v in result['divisions'].values())} divisions.", flush=True)
    return 0


def extract_cache_path(config: dict, folders: DataFolders, gol: Path) -> Path:
    stamp = f"{gol.stat().st_size}-{gol.stat().st_mtime_ns}"
    record = countiesmod.load_record(RECORD)
    ids = [c["id"] for c in config["countries"] if c.get("divisions")]
    rec = {i: record.get(i, {}).get("levels") for i in ids}
    parts = [config["countries"], config.get("region_level", 4), rec, stamp, EXTRACT_VERSION]
    if config.get("units"):
        parts.append({"units": (CONFIG_DIR / "country_units.yaml").read_text(encoding="utf-8")})
    key = hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return folders.working / config["name"] / f"extract-{key}.pkl"


# Checks ------------------------------------------------------------------

def _clip_job(geom, candidates):
    """One area cut to the land, in a worker process: (land, seconds)."""
    start = time.perf_counter()
    return clip.clip_to(geom, candidates), time.perf_counter() - start


def clip_all(land: clip.Land, items: list[tuple[str, object]], working: Path, log: Log, workers: int = 1) -> dict:
    """Every area cut to the land, cached by a fingerprint of its shape.

    Areas not in the cache are cut in worker processes (mapdata.parallel),
    largest first, with only a few waiting at a time, so the land tiles
    sent to the workers do not all sit in memory at once.
    """
    from mapdata import parallel

    out, slow, todo, seen = {}, [], [], set()
    for key_id, geom in items:
        if key_id in seen:
            continue  # an area in two lists, such as a region that is also a country unit
        seen.add(key_id)
        path = cut_cache_path(working, key_id, geom)
        if path.is_file():
            out[key_id] = clip.polygonal(pickle.loads(path.read_bytes()))
        else:
            todo.append((key_id, geom, path))
    if not todo:
        return out
    todo.sort(key=lambda t: -shapely.get_num_coordinates(t[1]))
    log(f"Cutting {len(todo)} areas to the land with {workers} worker process{'es' if workers != 1 else ''}; "
        f"{len(items) - len(todo)} were already in the cache.")
    (working / "clipped").mkdir(parents=True, exist_ok=True)
    with parallel.pool(workers) as executor:
        running = {}
        queue = list(todo)
        while queue or running:
            while queue and len(running) < workers + 1 and parallel.room_for_another(len(running)):
                key_id, geom, path = queue.pop(0)
                running[executor.submit(_clip_job, geom, land.candidates(geom))] = (key_id, path)
            done, _ = cf_wait(running)
            for future in done:
                key_id, path = running.pop(future)
                result, took = future.result()
                result = clip.polygonal(result)
                path.write_bytes(pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL))
                out[key_id] = result
                if took > 30:
                    slow.append(f"{key_id} {took:.0f} s")
    if slow:
        log("Slowest to cut to the land: " + ", ".join(slow) + ".")
    return out


def cut_cache_path(working: Path, key_id: str, geom) -> Path:
    """Where an area's land is cached: by its id and a fingerprint of the shape it was cut from."""
    key = hashlib.sha1(shapely.to_wkb(geom) + VERSION.encode()).hexdigest()[:16]
    return working / "clipped" / f"{key_id.replace(':', '_')}-{key}.pkl"


def cf_wait(running: dict):
    import concurrent.futures as cf

    return cf.wait(running, return_when=cf.FIRST_COMPLETED)


def island_report(name: str, named_points: list, land_geom, log: Log) -> dict:
    parts = shapely.get_parts(land_geom)
    areas = areas_km2(parts)
    order = np.argsort(-areas)
    # Each part is prepared once and tested against the named points near it.
    # Testing each point against an unprepared mainland with millions of
    # points took over 25 minutes for Norway.
    named_parts = set()
    if named_points:
        pts_tree = shapely.STRtree(np.array([pt for _n, pt in named_points], dtype=object))
        part_idx, _pt_idx = pts_tree.query(parts, predicate="intersects")
        named_parts = {int(i) for i in part_idx}
    biggest = int(order[0])
    named_parts.discard(biggest)
    total = len(parts)
    unnamed_ha = int(sum(1 for i in range(total) if i != biggest and i not in named_parts and areas[i] >= 0.01))
    rep = {"parts": total, "named_features": len(named_points), "named_parts": len(named_parts),
           "unnamed_parts": total - 1 - len(named_parts), "at_least_1_hectare": int((areas >= 0.01).sum()),
           "unnamed_at_least_1_hectare": unnamed_ha, "at_least_1_km2": int((areas >= 1).sum()),
           "at_least_20_km2": int((areas >= 20).sum()), "points": int(shapely.get_num_coordinates(land_geom))}
    log(f"{name}: land in {total:,} separate parts, with {rep['points']:,} points. Named islands and islets in OSM: "
        f"{len(named_points):,}. Parts with a name: {len(named_parts):,}. Without a name: {rep['unnamed_parts']:,}.")
    log(f"  Parts of 1 hectare or more: {rep['at_least_1_hectare']:,}, of which unnamed: {unnamed_ha:,}. "
        f"Of 1 km2 or more: {rep['at_least_1_km2']:,}. Of 20 km2 or more: {rep['at_least_20_km2']:,}.")
    return rep


def shared_islands(members: list[tuple[str, object, object]], named: list, log: Log) -> list[dict]:
    """Islands whose land is in more than one country.

    members: (name, land, shape as read). A part of one country's land that
    touches a part of another's, other than where two mainlands meet, is an
    island shared between them. Its border must be a shared edge: the two
    sides meet exactly, with no gap or overlap.

    Only parts near the border between each two countries are tested, found
    from the shapes as read, whose borders have far fewer points than the coast.
    """
    rows = []
    parts, owner, areas = [], [], []
    names_tree = shapely.STRtree(np.array([pt for _n, pt in named], dtype=object)) if named else None
    pairs = []
    for a in range(len(members)):
        for b in range(a + 1, len(members)):
            (na, la, ra), (nb, lb, rb) = members[a], members[b]
            zone = shapely.intersection(ra.boundary, rb.boundary)
            if zone.is_empty:
                continue
            zone = zone.buffer(1e-4)
            found = []
            for name, land in ((na, la), (nb, lb)):
                ps = shapely.get_parts(land)
                hits = shapely.STRtree(ps).query(zone, predicate="intersects")
                found.append([ps[k] for k in hits])
            for pa in found[0]:
                for pb in found[1]:
                    if not shapely.intersects(shapely.box(*pa.bounds), shapely.box(*pb.bounds)):
                        continue
                    ka, kb = area_km2(pa), area_km2(pb)
                    if ka > 50000 and kb > 50000:
                        continue  # two mainlands meeting at a land border
                    if shapely.intersects(pa, pb):
                        pairs.append((na, pa, ka, nb, pb, kb))
    for na, pa, ka, nb, pb, kb in pairs:
        i, j = len(parts), len(parts) + 1
        parts.extend([pa, pb])
        owner.extend([na, nb])
        areas.extend([ka, kb])
        island = shapely.union_all([parts[i], parts[j]])
        overlap = area_km2(shapely.intersection(parts[i], parts[j]))
        border = shapely.intersection(parts[i].boundary, parts[j].boundary)
        border_m = border.length * 111_200 * np.cos(np.radians(island.centroid.y))
        island_name = "no name in OSM"
        if names_tree is not None:
            hits = names_tree.query(island, predicate="intersects")
            if len(hits):
                island_name = ", ".join(sorted({named[k][0] for k in hits})[:3])
        rows.append({"countries": f"{owner[i]} and {owner[j]}", "name": island_name,
                     "area_km2": round(float(areas[i] + areas[j]), 4),
                     "parts": f"{areas[i]:.4f} and {areas[j]:.4f} km2", "overlap_km2": overlap,
                     "border_m": round(float(border_m)), "lat": island.centroid.y, "lon": island.centroid.x,
                     "meets_exactly": overlap < 1e-6 and border.length > 0})
    rows.sort(key=lambda r: -r["area_km2"])
    log(f"Islands shared between countries: {len(rows)}. Their two sides meet exactly in "
        f"{sum(r['meets_exactly'] for r in rows)} of them.")
    for r in rows[:25]:
        log(f"  {r['countries']}: {r['name']}, {r['area_km2']:.3f} km2, at {r['lat']:.4f} north, {r['lon']:.4f} east. "
            f"Border across it {r['border_m']:,} m. Meets exactly: {'yes' if r['meets_exactly'] else 'no'}.")
    if len(rows) > 25:
        log(f"  and {len(rows) - 25} more, listed in summary.json.")
    return rows


def far_parts(name: str, geom, regions: list, log: Log) -> list[dict]:
    """Parts more than FAR_KM from the largest part (architecture 6.12, country units)."""
    parts = [p for p in shapely.get_parts(geom)]
    if not parts:
        return []
    areas = areas_km2(parts).tolist()
    # A simplified mainland is plenty for a 1000 km test, and far faster
    # against a coast with millions of points.
    main = shapely.simplify(parts[int(np.argmax(areas))], 0.05)
    groups: dict[str, float] = {}
    out = []
    for p, a in zip(parts, areas):
        if a < 1:
            continue
        # Across the 180 degree line, the shorter way round: the part is also
        # tried moved by 360 degrees each way.
        q = shapely.simplify(p, 0.01)
        d = float("inf")
        for shift in (0.0, 360.0, -360.0):
            moved = shapely.transform(q, lambda c, s=shift: c + np.array([s, 0.0])) if shift else q
            (x1, y1), (x2, y2) = shapely.shortest_line(main, moved).coords
            d = min(d, distance_km(x1, y1, x2, y2))
        if d <= FAR_KM:
            continue
        pt = p.representative_point()
        region = next((english(r) for r, g in regions if shapely.intersects(g, pt)), "no region")
        groups[region] = groups.get(region, 0) + a
        out.append({"region": region, "area_km2": a, "km": d})
    if groups:
        log(f"{name}: land more than {FAR_KM} km from its largest part: "
            + "; ".join(f"{r}, {a:,.0f} km2" for r, a in sorted(groups.items(), key=lambda kv: -kv[1])) + ".")
    else:
        log(f"{name}: no land more than {FAR_KM} km from its largest part.")
    return out


def antimeridian_report(name: str, geom, wikidata_km2: float | None, log: Log) -> dict:
    box = antimeridian.wrap_box(geom)
    naive = geom.bounds
    c = antimeridian.centre(geom, box)
    naive_c = shapely.Point((naive[0] + naive[2]) / 2, (naive[1] + naive[3]) / 2)
    naive_in = bool(shapely.intersects(geom, naive_c))
    edges = antimeridian.line_edges(geom)
    km2 = area_km2(geom)
    row = {"name": name, "area_km2": km2, "wikidata_km2": wikidata_km2,
           "wrap_box": [box.west, box.south, box.east, box.north], "wrap_width": box.width,
           "naive_width": naive[2] - naive[0], "centre": [c.lon, c.lat], "centre_in_shape": c.in_shape,
           "snapped": [c.snapped_lon, c.snapped_lat], "snap_km": c.snap_km,
           "naive_centre": [naive_c.x, naive_c.y], "naive_centre_in_shape": naive_in,
           "edges_east_km": edges.east_km, "edges_west_km": edges.west_km, "pole_edges": edges.pole_edges,
           "unmatched_km": edges.unmatched_km}
    log(f"{name}:")
    if wikidata_km2:
        diff = (km2 - wikidata_km2) / wikidata_km2 * 100
        row["area_diff_percent"] = diff
        log(f"  Area {km2:,.0f} km2 on the ellipsoid; Wikidata gives {wikidata_km2:,.0f} km2, "
            f"a difference of {diff:+.1f}%. Within 1%: {'yes' if abs(diff) <= 1 else 'no'}.")
    else:
        log(f"  Area {km2:,.0f} km2 on the ellipsoid.")
    if box.round_the_world:
        log("  It goes all the way round the pole, so its bounding box covers every longitude.")
    else:
        log(f"  Bounding box allowing for the line: {box.width:.1f} degrees of longitude wide, from {box.west:.2f} to {box.east:.2f}"
            f"{' (crossing the 180 degree line)' if box.crosses else ''}. "
            f"A bounding box worked out without allowing for the line would be {naive[2] - naive[0]:.1f} degrees wide.")
    where = "on the land" if c.in_shape else f"in the sea, {c.snap_km:,.0f} km from the nearest land of {name}"
    log(f"  Centre: {c.lat:.3f} north, {c.lon:.3f} east, {where}."
        f" The centre worked out without allowing for the line, {naive_c.y:.2f} north, {naive_c.x:.2f} east, "
        f"is {'on the land' if naive_in else 'not on the land'}.")
    log(f"  Edges along the 180 degree line, to be marked artificial: {edges.east_km:,.0f} km on the east side, "
        f"{edges.west_km:,.0f} km on the west side; edges on one side only: {edges.unmatched_km:,.1f} km."
        + (f" Edges along the South Pole: {edges.pole_edges}." if edges.pole_edges else ""))
    return row


def _coverage_job(layer_name: str, shapes: list, tolerance: float):
    """One layer's check, in a worker process: (report lines, result without the shapes)."""
    lines: list[str] = []
    result = coverage_report(layer_name, shapes, tolerance, lines.append)
    return lines, {k: v for k, v in result.items() if k != "simplified"}


def _picture_job(out_dir: Path, name: str, bbox, shapes: list):
    """One picture, in a worker process: (report lines, file names)."""
    lines: list[str] = []
    made = pictures(out_dir, {name: (bbox, shapes)}, lines.append)
    return lines, made


def _globe_job(out_dir: Path, views: list, shapes: list):
    """The globe views, in a worker process: (report lines, results)."""
    lines: list[str] = []
    result = globe_pictures(out_dir, views, shapes, lines.append)
    return lines, result


def draw_all(out_dir: Path, views: dict, globe_views, country_shapes: list, workers: int, log) -> tuple[list, list]:
    """Every picture and globe view, each as its own job in a worker process (DP103).

    Each shape is trimmed to its picture's frame before it is sent, so a
    close-up does not carry a whole country to the worker.
    """
    from mapdata import parallel

    jobs = []
    for name, (bbox, shapes) in views.items():
        w, s, e, n = bbox
        pad_x, pad_y = (e - w) * 0.01, (n - s) * 0.01
        trimmed = [shapely.clip_by_rect(g, w - pad_x, s - pad_y, e + pad_x, n + pad_y) for g in shapes]
        jobs.append((_picture_job, (out_dir, name, bbox, [g for g in trimmed if not g.is_empty])))
    if globe_views:
        jobs.insert(0, (_globe_job, (out_dir, globe_views, country_shapes)))  # the longest, so first
    pics, globes, lines_all = [], [], []
    with parallel.pool(min(workers, max(1, len(jobs)))) as executor:
        futures = [(fn, executor.submit(fn, *args)) for fn, args in jobs]
        for fn, future in futures:
            lines, result = future.result()
            lines_all.extend(lines)
            if fn is _globe_job:
                globes = result
            else:
                pics.extend(result)
    for line in lines_all:
        if not line.startswith("Pictures: "):
            log(line)
    log("Pictures: " + ", ".join(pics) + ".")
    return pics, globes


def border_window(raw_shapes: list, width_deg: float):
    """A band reaching about width_deg either side of each border between neighbouring shapes.

    Found from the shapes as read, which have few points. Each shape is
    widened by width_deg, and the band is where two widened shapes
    overlap. (Widening the border lines themselves, as one collection, used
    18 GB of memory for Norway, Sweden and Finland.) Neighbours meet only
    inside this band, so the check of AD-16 looks only there.
    """
    half = width_deg
    grown = np.array([shapely.buffer(shapely.simplify(g, half / 4), half, quad_segs=2) for g in raw_shapes],
                     dtype=object)
    tree = shapely.STRtree(grown)
    bands = []
    for i, j in zip(*tree.query(grown, predicate="intersects")):
        if i < j:
            band = clip.polygonal(shapely.intersection(grown[i], grown[j]))
            if not band.is_empty:
                bands.append(band)
    if not bands:
        return None
    return shapely.union_all(bands)


def window_pieces(shapes: list, window, cell: float = 1.0) -> list:
    """The parts of the shapes inside the window, cut into one-degree squares.

    Intersecting Norway's whole land (7.4 million points) with the window in
    one step used 19 GB of memory. Here each shape is first cut to each
    square with a quick rectangle cut, which needs little memory, and only
    those small pieces are intersected with the window. Every shape is cut
    along the same square edges, so the pieces still fit together exactly,
    which is what the check needs.
    """
    import math

    w, s, e, n = window.bounds
    cells = []
    for i in range(math.floor(w / cell), math.ceil(e / cell)):
        for j in range(math.floor(s / cell), math.ceil(n / cell)):
            box = (i * cell, j * cell, (i + 1) * cell, (j + 1) * cell)
            part = shapely.intersection(window, shapely.box(*box))
            if not part.is_empty:
                cells.append((box, part))
    out = []
    for g in shapes:
        parts = shapely.get_parts(g)
        tree = shapely.STRtree(parts)
        for box, win_part in cells:
            idx = tree.query(shapely.box(*box))
            if len(idx) == 0:
                continue
            for p in parts[idx]:
                piece = shapely.clip_by_rect(p, *box)
                if piece.is_empty:
                    continue
                piece = clip.polygonal(shapely.intersection(piece, win_part))
                if not piece.is_empty:
                    out.append(piece)
    return out


def check_places(places_file: Path, pack_path: Path, log: Log) -> tuple[int, int, list[str]]:
    from mapcore.packs.archive import Pack

    places = yaml.safe_load(places_file.read_text(encoding="utf-8"))["places"]
    pack = Pack(pack_path)
    passed, lines, times = 0, [], []
    try:
        for p in places:
            start = time.perf_counter()
            reads_before = pack.reads
            found = pack.at(p["lon"], p["lat"])
            times.append((time.perf_counter() - start) * 1000)
            names = [f["name"] for f in found]
            known = set(names) | {f.get("local_name") for f in found}
            if p.get("sea"):
                ok, expect = not found, "sea"
            else:
                ok = all(n in known for n in p["includes"])
                expect = ", ".join(p["includes"])
            passed += ok
            heard = ", ".join(names) if names else "sea"
            lines.append(f"{'PASS' if ok else 'FAIL'} {p['name']}: found {heard}. Expected {expect}. "
                         f"{pack.reads - reads_before} pack tiles read.")
    finally:
        pack.close()
    for line in lines:
        log(line)
    log(f"{passed} of {len(places)} places passed. Each lookup took {np.median(times):.1f} ms on average "
        f"(median), at most {max(times):.0f} ms.")
    return passed, len(places), lines


def globe_pictures(out_dir: Path, views: list[dict], shapes: list, log: Log) -> list[dict]:
    """Draw the shapes on the orthographic globe (VIS-5), as the shells will.

    Edges along the 180 degree line and the South Pole are filled but never
    outlined (AD-17). The check: no outlined edge jumps across the globe,
    which is what a shape wrongly joined across the line would do.
    """
    import os
    from types import SimpleNamespace

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen
    from PySide6.QtWidgets import QApplication

    from mapcore.render import globe
    from mapdata.stages import drawing

    QApplication.instance() or QApplication([])
    countries = []
    for k, (cid, g) in enumerate(shapes):
        g = drawing.simplify_parts(g, 0.01)
        polys = []
        parts = shapely.get_parts(g)
        parts = parts[(shapely.get_type_id(parts) == 3) & ~shapely.is_empty(parts)]
        if len(parts):
            # Every ring's points in one call, then split into rings.
            rings_all = shapely.get_rings(parts, return_index=True)
            xy, ring_of = shapely.get_coordinates(rings_all[0], return_index=True)
            ends = np.searchsorted(ring_of, np.arange(len(rings_all[0]) + 1))
            by_poly: dict[int, list] = {}
            for r, p in enumerate(rings_all[1].tolist()):
                c = xy[ends[r]:ends[r + 1] - 1]  # without the closing point
                if len(c) >= 3:
                    by_poly.setdefault(p, []).append(SimpleNamespace(lat=c[:, 1], lon=c[:, 0]))
            polys = [by_poly[p] for p in sorted(by_poly)]
        countries.append(SimpleNamespace(id=cid, polygons=polys, colour=k + 1))
    geometry = globe.GlobeGeometry.from_world(SimpleNamespace(countries=countries))
    out = []
    for v in views:
        size = 900
        scene = globe.build_scene(geometry, globe.View(v["lat"], v["lon"], v.get("scale", 1.0)), size, size)
        coords = scene["coords"].reshape(-1, 2)
        seam = scene["seam"].astype(bool)
        rings = scene["rings"]
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor("#ffffff"))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gl = scene["globe"]
        p.setBrush(QBrush(QColor("#a9cce3")))
        p.setPen(QPen(QColor("#333333"), 1))
        p.drawEllipse(QPointF(gl["cx"], gl["cy"]), gl["r"], gl["r"])
        palette = ["#e8d8a9", "#c9e2b3", "#f2c6b4", "#d6c8e6", "#f6e3a1"]
        coords = coords.astype(float)
        rings = np.asarray(rings, np.intp)
        # Each edge's length on the screen, to the next point of its ring.
        nxt = np.arange(len(coords), dtype=np.intp) + 1
        lengths_r = np.diff(rings)
        full = lengths_r > 0
        nxt[rings[1:][full] - 1] = rings[:-1][full]
        lengths = np.hypot(*(coords[nxt] - coords).T) if len(coords) else np.zeros(0)
        seam_edges = int(seam.sum())
        longest = float(lengths[~seam].max()) if (~seam).any() else 0.0
        # Each shape is filled as one path; then every outline is drawn as
        # one path, lifting the pen at the artificial edges (drawing.py).
        p.setPen(Qt.PenStyle.NoPen)
        shape_starts = scene["shapes"]
        for si in range(len(shape_starts) - 1):
            a, b = rings[shape_starts[si]], rings[shape_starts[si + 1]]
            if b <= a:
                continue
            move = np.zeros(b - a, bool)
            move[rings[shape_starts[si]:shape_starts[si + 1]] - a] = True
            p.setBrush(QBrush(QColor(palette[scene["shape_style"][si] % len(palette)])))
            p.drawPath(drawing.qpath(coords[a:b], move))
        xy, move = drawing.outline_arrays(coords, rings, seam)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#5a4a3a"), 1))
        p.drawPath(drawing.qpath(xy, move))
        p.end()
        file = out_dir / f"globe-{v['name']}.png"
        img.save(str(file))
        share = longest / gl["r"]
        ok = share < 0.15
        log(f"Globe centred on {v['title']}: {scene['points']:,} points drawn, {seam_edges:,} edges along the "
            f"line or the pole filled but not outlined. Longest outlined edge: {share * 100:.1f}% of the globe's "
            f"radius. No edge jumps across the globe: {'yes' if ok else 'no'}. Picture: {file.name}.")
        out.append({"view": v["name"], "longest_edge_share": share, "seam_edges": seam_edges, "ok": ok})
    return out


# The run -----------------------------------------------------------------

def run(stage: int, folders: DataFolders, workers: int = 3) -> int:
    log = Log()
    config = load_config(stage)
    name = config["name"]
    working = folders.working / name
    out_dir = folders.output / name
    out_dir.mkdir(parents=True, exist_ok=True)
    start_memory_guard(log, out_dir / "report.txt")
    plain_heading = log.heading

    def heading(text: str) -> None:
        mine, free = memory_mb()
        if free:
            log(f"(Memory: this build {mine:,.0f} MB, free on the computer {free:,.0f} MB.)")
        plain_heading(text)

    log.heading = heading
    gol = folders.root / config["source_gol"]
    lp = landmod.source_path(folders.downloads)
    log(config["title"])
    log(f"This build uses {workers} worker process{'es' if workers != 1 else ''} for the slowest steps, on a "
        f"computer with {os.cpu_count()} logical processors, so other programs may be slower while it runs.")
    last = out_dir / "summary.json"
    if last.is_file():
        try:
            minutes = json.loads(last.read_text(encoding="utf-8"))["total_seconds"] / 60
            log(f"The last run of this stage took {minutes:.0f} minutes; this one should take no longer, as its "
                f"slow steps are cached or now share the work between processes.")
        except (KeyError, ValueError):
            pass
    log(f"Source: {gol.name}, dated {time.strftime('%d %B %Y', time.localtime(gol.stat().st_mtime))}. "
        f"Land polygons: {lp.name}, dated {time.strftime('%d %B %Y', time.localtime(lp.stat().st_mtime))}.")
    timings: dict[str, float] = {}

    log.heading("Extract")
    t = time.perf_counter()
    cache = extract_cache_path(config, folders, gol)
    if cache.is_file():
        log("Read from the cache of an earlier run; the planet file was not opened.")
    else:
        log("Reading the planet file in a separate process, which ends when it has finished.")
        GUARD["paused"] = True
        try:
            done = subprocess.run([sys.executable, "-m", "mapdata", "--data", str(folders.root),
                                   "spike-s2-extract", str(stage)], cwd=str(ROOT))
        finally:
            GUARD["paused"] = False
        if done.returncode != 0 or not cache.is_file():
            log("The extract process failed.")
            return 2
    ex = pickle.loads(cache.read_bytes())
    for line in ex["lines"]:
        log(line)
    countries: list = ex["countries"]
    divisions: dict = ex["divisions"]
    units: list = ex.get("units", [])
    unit_ids = {u.id for u in units}
    replaced = {u.parent for u in units}
    sovereign_of = sovereigns()
    log(f"Repairs: {len(ex['repairs'])}.")
    for r in ex["repairs"][:30]:
        log(f"  {r}")
    timings["extract"] = time.perf_counter() - t
    by_id = {a.id: a for a in countries}
    settings = {c["id"]: c for c in config["countries"]}
    region_level = config.get("region_level", 4)

    log.heading("Land polygons")
    t = time.perf_counter()
    shapes_for_land = {}
    boxes = []
    for a in countries:
        g = limited(a.geom, settings[a.id].get("land_within"))
        shapes_for_land[a.id] = g
        boxes.extend(part_boxes(g, join=0.5))
    # Join overlapping boxes, so no land tile is read twice.
    boxes = part_boxes(_box_union(boxes), pad=0.0, join=0.0)
    log(f"Reading boxes worked out from the countries' shapes: {len(boxes)}.")
    tiles = landmod.load_boxes(folders.downloads, working, name, boxes, say=log)
    tiles, cap = with_polar_cap(tiles)
    if cap is not None:
        log(f"The land polygons stop at {cap:.2f} degrees south. Antarctica's ice sheet is land all the way to the "
            f"South Pole, so the cap south of that is added as land.")
    land = clip.Land(tiles)
    timings["land"] = time.perf_counter() - t

    log.heading("Cut to the land")
    t = time.perf_counter()
    items = [(a.id, shapes_for_land[a.id]) for a in countries]
    items.extend((u.id, u.geom) for u in units)
    for (cid, level), divs in divisions.items():
        if level == region_level:
            items.extend((d.id, d.geom) for d in divs)
    clipped = clip_all(land, items, working, log, workers)
    timings["clip"] = time.perf_counter() - t
    log(f"Cut {len(items)} areas to the land in {timings['clip']:.0f} seconds.")
    for a in countries:
        log(f"  {english(a)}: {area_km2(shapes_for_land[a.id]):,.0f} km2 before, {area_km2(clipped[a.id]):,.0f} km2 "
            f"of land" + (", in the area read for it" if settings[a.id].get("land_within") else "") + ".")

    log.heading("Counties (discussion point 101)")
    t = time.perf_counter()
    record = countiesmod.load_record(RECORD)
    county_results = {}
    for c in config["countries"]:
        if not c.get("divisions"):
            continue
        country = by_id[c["id"]]
        levels, from_record = countiesmod.levels_for(record, country.id)
        cboxes = c.get("county_boxes")
        country_raw = limited(shapes_for_land[country.id], cboxes)
        regions = [(d, limited(clipped[d.id], cboxes)) for d in divisions[(country.id, region_level)]]
        regions = [(d, g) for d, g in regions if not g.is_empty]
        cands = {lv: divisions.get((country.id, lv), []) for lv in levels}

        def clip_one(g):
            return clip.polygonal(cached(cut_cache_path(working, "county", g), lambda: land.clip(g)))

        res = countiesmod.build(country_raw, regions, cands, clip_one, levels, english=english)
        county_results[country.id] = res
        where = " in the area checked" if cboxes else ""
        log(f"{english(country)}: levels tried {levels}, " + ("from the record" if from_record else "by the general rule")
            + f". Counties{where}: {len(res.counties)}, made from level{'s' if len(res.levels_used) != 1 else ''} "
            f"{', '.join(map(str, res.levels_used)) or 'none'}"
            + (f", and {len(res.regions_used)} regions used as their own county" if res.regions_used else "")
            + f". Land in no county after the rule: {res.left_km2:,.1f} km2.")
        for line in res.filled[:20]:
            log(f"  {line}")
        if len(res.filled) > 20:
            log(f"  and {len(res.filled) - 20} more.")
        region_names = {d.id: english(d) for d, _g in regions}
        countiesmod.update_record(RECORD, country.id, english(country), res, region_names, f"spike S2 stage {stage}")
    log(f"The counties record is updated: {RECORD.relative_to(ROOT).as_posix()}.")
    timings["counties"] = time.perf_counter() - t

    log.heading("Land in no country, and in no region")
    t = time.perf_counter()
    nc_boxes = config.get("no_country_boxes")
    focus = [by_id[c["id"]] for c in config["countries"] if c.get("divisions")]
    near_raw = shapely.union_all([limited(a.geom, nc_boxes) for a in focus]).buffer(0.01)
    no_country = clip.raw_gaps(limited(near_raw, nc_boxes), [shapes_for_land[a.id] for a in countries],
                               [english(a) for a in countries], land)
    log(f"Parts of land within about 1 km of {', '.join(english(a) for a in focus)}"
        + (" in the rectangles checked" if nc_boxes else "")
        + f" that are in no country: {len(no_country)}, {sum(s.area_km2 for s in no_country):.3f} km2 in all.")
    for s in no_country[:15]:
        log(f"  {s.area_km2 * 100:.2f} hectares at {s.centre[1]:.4f} north, {s.centre[0]:.4f} east, beside {s.near}.")
    level_gaps = {}
    for a in focus:
        divs = divisions[(a.id, region_level)]
        g = clip.raw_gaps(shapes_for_land[a.id], [d.geom for d in divs], [english(d) for d in divs], land)
        level_gaps[a.id] = g
        log(f"{english(a)}: land in no level {region_level} area: {len(g)} parts, "
            f"{sum(s.area_km2 for s in g):,.3f} km2." + (f" Largest {g[0].area_km2:,.3f} km2, beside {g[0].near}, "
                                                         f"at {g[0].centre[1]:.3f} north, {g[0].centre[0]:.3f} east."
                                                         if g else ""))
    timings["gaps"] = time.perf_counter() - t

    islands, shared, far = {}, [], {}
    if any(c.get("islands") for c in config["countries"]) or config.get("shared_islands"):
        log.heading("Islands")
        t = time.perf_counter()
        for c in config["countries"]:
            if c.get("islands"):
                islands[c["id"]] = island_report(english(by_id[c["id"]]), ex["named"].get(c["id"], []),
                                                 clipped[c["id"]], log)
        if config.get("shared_islands"):
            named_all = [p for v in ex["named"].values() for p in v]
            shared = shared_islands([(english(by_id[i]), clipped[i], shapes_for_land[i]) for i in config["shared_islands"]],
                                    named_all, log)
        timings["islands"] = time.perf_counter() - t

    log.heading("Parts far apart (country units)")
    for a in focus:
        regs = [(d, clipped[d.id]) for d in divisions[(a.id, region_level)]]
        far[a.id] = far_parts(english(a), clipped[a.id], regs, log)

    log.heading("Neighbours after simplifying (AD-16)")
    t = time.perf_counter()
    cov = []
    tol = config.get("simplify_tolerance", 0.005)
    window_km = config.get("coverage_window_km")
    if window_km:
        log(f"Each layer is checked within about {window_km} km of its land borders, where neighbours meet. "
            f"Checking along every coast as well took too long for Norway's 7.4 million points.")

    def prepare(layer_name, land_shapes, raw_shapes):
        """The layer's shapes to check: inside the border window if one is set."""
        if window_km:
            win = border_window(raw_shapes, window_km / 111.0)
            if win is None:
                log(f"{layer_name}: no land borders inside it to check.")
                return None
            land_shapes = window_pieces(land_shapes, win)
            mine, free = memory_mb()
            log(f"{layer_name}: {len(land_shapes)} parts inside the border window. "
                f"(Memory: this build {mine:,.0f} MB, free {free:,.0f} MB.)")
        return land_shapes

    jobs = []
    if config.get("country_layer_check", True) and len(countries) > 1:
        jobs.append(("Countries", [clipped[a.id] for a in countries], [shapes_for_land[a.id] for a in countries]))
    for a in focus:
        divs = divisions[(a.id, region_level)]
        jobs.append((f"{english(a)} level {region_level}", [clipped[d.id] for d in divs], [d.geom for d in divs]))
        cs = county_results[a.id].counties
        jobs.append((f"{english(a)} counties", [c.geom for c in cs], [c.area.geom for c in cs]))
    from mapdata import parallel
    log(f"The {len(jobs)} layers are checked {min(workers, len(jobs))} at a time.")
    with parallel.pool(min(workers, max(1, len(jobs)))) as executor:
        futures = []
        for layer_name, land_shapes, raw_shapes in jobs:
            shapes = prepare(layer_name, land_shapes, raw_shapes)
            if shapes is not None:
                futures.append(executor.submit(_coverage_job, layer_name, shapes, tol))
        for future in futures:
            lines, result = future.result()
            for line in lines:
                log(line)
            cov.append(result)
    timings["coverage"] = time.perf_counter() - t

    am = []
    if config.get("antimeridian"):
        log.heading("The 180 degree line and the South Pole (architecture 6.13)")
        t = time.perf_counter()
        for cid in config["antimeridian"]:
            am.append(antimeridian_report(english(by_id[cid]), clipped[cid],
                                          config.get("wikidata_km2", {}).get(cid), log))
        timings["antimeridian"] = time.perf_counter() - t
    elif config.get("wikidata_km2"):
        log.heading("Areas against Wikidata")
        for cid, km2 in config["wikidata_km2"].items():
            ours = area_km2(clipped[cid])
            log(f"{english(by_id[cid])}: {ours:,.0f} km2 of land, Wikidata gives {km2:,.0f} km2, "
                f"a difference of {(ours - km2) / km2 * 100:+.1f}%.")

    log.heading("Pack")
    records, geoms = [], []
    # The Countries layer: a country with units is replaced by them (6.12).
    country_layer = [a for a in countries if a.id not in replaced] + units
    for a in country_layer:
        records.append({"id": a.id, "name": a.tags.get("unit_name") or english(a), "local_name": a.name,
                        "layer": "countries", "type": a.tags.get("unit_type", "country"),
                        "sovereign": a.tags.get("sovereign") or sovereign_of.get(a.id, english(a)),
                        "area_km2": round(area_km2(clipped[a.id]), 3)})
        geoms.append(clipped[a.id])
    for a in focus:
        for d in divisions[(a.id, region_level)]:
            if d.id in unit_ids:
                continue  # already in the Countries layer as a unit
            records.append({"id": d.id, "name": english(d), "local_name": d.name, "layer": "regions",
                            "type": f"level {d.level}", "parent": a.id, "area_km2": round(area_km2(clipped[d.id]), 3)})
            geoms.append(clipped[d.id])
        for c in county_results[a.id].counties:
            records.append({"id": c.area.id + ("#county" if c.region_fill else ""), "name": english(c.area),
                            "local_name": c.area.name, "layer": "counties",
                            "type": "region used as county" if c.region_fill else f"level {c.level}",
                            "parent": a.id, "area_km2": round(area_km2(c.geom), 3)})
            geoms.append(c.geom)
    keep = [i for i, g in enumerate(geoms) if not g.is_empty]
    records, geoms = [records[i] for i in keep], [geoms[i] for i in keep]
    manifest = {"name": name, "source": gol.name, "licence": "ODbL 1.0, OpenStreetMap contributors"}
    packs = {}
    t = time.perf_counter()
    packs = pack_write.write_both({e: out_dir / f"{name}-{e}.pack" for e in ("wkb", "compact")}, manifest,
                                  records, geoms, workers, say=log)
    timings["pack"] = time.perf_counter() - t
    log(f"Compact coordinates make the pack {packs['wkb']['bytes'] / packs['compact']['bytes']:.1f} times smaller.")

    log.heading("Coastline places")
    log("Each line looks up one place in the compact pack. \"Pack tiles read\" is how many records the lookup "
        "fetched from the pack. See docs/design/glossary.md.")
    passed, total, _lines = check_places(ACCEPTANCE / config["places"], out_dir / f"{name}-compact.pack", log)

    log.heading("Pictures")
    layers = {"countries": [clipped[a.id] for a in country_layer],
              "regions": [clipped[d.id] for a in focus for d in divisions[(a.id, region_level)]],
              "counties": [c.geom for a in focus for c in county_results[a.id].counties]}
    views = {}
    for pic in config.get("pictures", []):
        views[pic["name"]] = (tuple(pic["box"]), layers[pic["layer"]])
    for cid in config.get("antimeridian", []):
        g = antimeridian.shifted(clipped[cid])
        w, s, e, n = g.bounds
        pad = max(e - w, n - s) * 0.05
        views[f"isolated-{english(by_id[cid]).lower().replace(' ', '-')}"] = ((w - pad, max(-90, s - pad), e + pad,
                                                                             min(90, n + pad)), [g])
    t = time.perf_counter()
    pics, globes = draw_all(out_dir, views, config.get("globe_views"), [(a.id, clipped[a.id]) for a in countries],
                            workers, log)
    timings["pictures"] = time.perf_counter() - t

    log.heading("Measurements")
    total_s = log.elapsed()
    log(f"Total time: {total_s / 60:.1f} minutes. Peak memory: {peak_memory_mb():,.0f} MB.")
    for k, v in timings.items():
        log(f"  {k}: {v:.0f} seconds.")
    working_mb = sum(f.stat().st_size for f in working.rglob("*") if f.is_file()) / 1e6
    log(f"Working folder: {working_mb:,.0f} MB. Packs: WKB {packs['wkb']['bytes'] / 1e6:.1f} MB, "
        f"compact {packs['compact']['bytes'] / 1e6:.1f} MB.")

    summary = {
        "places_passed": passed, "places": total, "islands": islands, "shared_islands": shared,
        "far_parts": far, "antimeridian": am, "globe": globes, "units": sorted(unit_ids),
        "coverage": [{k: v for k, v in c.items() if k != "simplified"} for c in cov],
        "counties": {cid: {"levels_used": r.levels_used, "regions_used": r.regions_used, "left_km2": r.left_km2,
                           "count": len(r.counties), "filled": r.filled} for cid, r in county_results.items()},
        "packs": packs, "timings": timings,
        "no_country": [vars(s) for s in no_country],
        "region_gaps": {k: [vars(s) for s in v] for k, v in level_gaps.items()},
        "repairs": ex["repairs"], "peak_memory_mb": peak_memory_mb(), "total_seconds": total_s, "pictures": pics,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    (out_dir / "report.txt").write_text("\n".join(log.lines) + "\n", encoding="utf-8")
    log(f"Report: {out_dir / 'report.txt'}")
    return 0 if passed == total else 1
