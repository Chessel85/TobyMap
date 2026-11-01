"""Spike S2, stage 1: the UK, France and Spain (architecture 12.3, P0-T5).

Runs the countries and coastlines method end to end on the first test area:

1. Extract level 2 countries, the country units, and levels 4 and 6 inside
   the UK, France and Spain, from the planet GOL file.
2. Clip every area to the OSM land polygons.
3. Find land in no country, and land in a country but in none of its divisions.
4. Count the UK's islands, named and unnamed, and how many each drawing level keeps.
5. Check that neighbours still meet exactly after simplification.
6. Write the pack twice, with WKB and with compact coordinates, and compare sizes.
7. Check the coastline places (tests/acceptance/coastline_places.yaml).
8. Draw pictures for sighted reviewers.
9. Write the report: output/s2-stage1/report.txt in the data folder.

Everything it writes is inside the data folder's tobymap folder. Slow results
are cached in working/s2-stage1, so a second run only redoes what changed.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import pickle
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import shapely
import yaml

from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.stages import boundaries, clip, land as landmod, pack_write
from mapdata.stages.geodesy import area_km2

ROOT = Path(__file__).resolve().parents[2]
PLACES_FILE = ROOT / "tests" / "acceptance" / "coastline_places.yaml"
VERSION = "s2-stage1-v2"  # change to discard the land caches
EXTRACT_VERSION = "s2-stage1-v1"  # change to read the planet file again


class Log:
    """Plain lines to the screen and the report (DMT-2)."""

    def __init__(self):
        self.lines: list[str] = []
        self.started = time.perf_counter()

    def __call__(self, text: str = "") -> None:
        print(text, flush=True)
        self.lines.append(text)

    def heading(self, text: str) -> None:
        self("")
        self(f"== {text} ==")

    def elapsed(self) -> float:
        return time.perf_counter() - self.started


def peak_memory_mb() -> float:
    if sys.platform != "win32":
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    # The process handle is pointer-sized; without these declarations ctypes
    # passes it as a 32-bit int and the call fails, which read as 0 MB.
    kernel32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
    psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.PeakWorkingSetSize / (1024 * 1024)


def english(area: boundaries.Area) -> str:
    return area.tags.get("name:en") or area.name


def cached(path: Path, make):
    if path.is_file():
        return pickle.loads(path.read_bytes())
    value = make()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
    return value


# Stage steps ------------------------------------------------------------------

def extract(world, config: dict, units: dict, log: Log):
    repairs: list[str] = []
    countries = []
    for c in config["countries"]:
        countries.append(boundaries.relation(world, c["id"], c["name"], 2, repairs))
    log(f"Countries at level 2: {len(countries)}.")
    unit_areas = []
    for u in units["units"]:
        for part in u["parts"]:
            feature = world.relation(int(part["id"].removeprefix("osm:r")))
            area = boundaries._to_area(feature, int(str(feature.tags["admin_level"]) or 3), u["replaces"], repairs)
            area.tags["unit_name"] = part["name"]
            area.tags["unit_type"] = part["type"]
            area.tags["sovereign"] = u["sovereign"]
            unit_areas.append(area)
    log(f"Country units: {', '.join(a.tags['unit_name'] for a in unit_areas)}.")
    divisions = {}
    boxes = list(config["regions"].values())
    for c in config["countries"]:
        if not c.get("divisions"):
            continue
        country = next(a for a in countries if a.id == c["id"])
        for level in config["levels"]:
            found = boundaries.divisions(world, country, level, repairs, boxes=boxes)
            divisions[(country.id, level)] = found
            log(f"{english(country)}, level {level}: {len(found)} areas.")
    return countries, unit_areas, divisions, repairs


def clip_all(land: clip.Land, areas: list, working: Path, log: Log) -> dict:
    """Clipped shapes by area id, each cached by a fingerprint of its shape."""
    out = {}
    slow = []
    for a in areas:
        key = hashlib.sha1(shapely.to_wkb(a.geom) + VERSION.encode()).hexdigest()[:16]
        start = time.perf_counter()
        # polygonal() again, because shapes cached by an earlier version may be collections.
        out[a.id] = clip.polygonal(cached(working / "clipped" / f"{a.id.replace(':', '_')}-{key}.pkl",
                                          lambda a=a: land.clip(a.geom)))
        took = time.perf_counter() - start
        if took > 20:
            slow.append(f"{english(a)} {took:.0f} s")
    if slow:
        log("Slowest to clip: " + ", ".join(slow) + ".")
    return out


def named_islands(world, uk: boundaries.Area) -> list[tuple[str, object]]:
    """Named islands and islets in OSM inside the UK's box, as (name, point)."""
    import geodesk

    w, s, e, n = uk.geom.bounds
    box = geodesk.Box(west=w, south=s, east=e, north=n)
    named_points = []
    for f in world("na[place=island],na[place=islet]")(box):
        name = str(f.tags["name"])
        if not name:
            continue
        if f.is_node:
            named_points.append((name, shapely.Point(f.lon, f.lat)))
        else:
            named_points.append((name, shapely.point_on_surface(geodesk.from_mercator(f.shape))))
    return named_points


def island_report(named_points: list, uk_land, log: Log) -> dict:
    parts = shapely.get_parts(uk_land)
    areas = np.array([area_km2(p) for p in parts])
    order = np.argsort(-areas)
    tree = shapely.STRtree(parts)
    named_parts = set()
    for _name, pt in named_points:
        for i in tree.query(pt, predicate="intersects"):
            named_parts.add(int(i))
    biggest = int(order[0])
    named_parts.discard(biggest)  # Great Britain itself
    total = len(parts)
    report = {
        "parts": total,
        "named_features": len(named_points),
        "named_parts": len(named_parts),
        "unnamed_parts": total - 1 - len(named_parts),
        "at_least_1_hectare": int((areas >= 0.01).sum()),
        "at_least_1_km2": int((areas >= 1).sum()),
        "at_least_20_km2": int((areas >= 20).sum()),
        "at_least_2000_km2": int((areas >= 2000).sum()),
        "unnamed_at_least_1_hectare": int(sum(1 for i in range(total)
                                               if i != biggest and i not in named_parts and areas[i] >= 0.01)),
        "points": int(shapely.get_num_coordinates(uk_land)),
        "largest": [(round(float(areas[i]), 1)) for i in order[:5]],
    }
    log(f"The UK's land is in {total} separate parts: Great Britain, Ireland's northern part and the islands.")
    log(f"Named islands and islets in OSM inside the UK's box: {len(named_points)}. "
        f"Land parts with a name: {len(named_parts)}. Without a name: {report['unnamed_parts']}.")
    log(f"Parts of 1 hectare or more: {report['at_least_1_hectare']}, of which unnamed: "
        f"{report['unnamed_at_least_1_hectare']}. Of 1 km2 or more: {report['at_least_1_km2']}. "
        f"Of 20 km2 or more: {report['at_least_20_km2']}. Of 2000 km2 or more: {report['at_least_2000_km2']}.")
    return report


DRAWING_LEVELS = [  # spike values: tolerance in degrees, smallest part kept
    {"name": "world", "tolerance": 0.05, "min_km2": 2000},
    {"name": "country", "tolerance": 0.005, "min_km2": 20},
    {"name": "1 km", "tolerance": 0.00002, "min_km2": 0},
]


def drawing_report(uk_land, log: Log) -> list[dict]:
    parts = shapely.get_parts(uk_land)
    areas = np.array([area_km2(p) for p in parts])
    out = []
    for level in DRAWING_LEVELS:
        start = time.perf_counter()
        kept = parts[areas >= level["min_km2"]] if level["min_km2"] else parts
        simplified = shapely.simplify(kept, level["tolerance"], preserve_topology=True)
        points = int(shapely.get_num_coordinates(simplified).sum())
        took = time.perf_counter() - start
        row = {**level, "parts": int(len(kept)), "points": points, "simplify_seconds": round(took, 2)}
        if level["name"] == "1 km":
            # At 1 km zoom only the view is drawn: a 2 km square on Skye.
            view = shapely.box(-6.27, 57.29, -6.23, 57.31)
            in_view = shapely.intersection(simplified[shapely.intersects(simplified, view)], view)
            row["points_in_view"] = int(shapely.get_num_coordinates(in_view).sum())
        out.append(row)
        log(f"Drawing level {level['name']}: {row['parts']} parts, {points:,} points"
            + (f", {row['points_in_view']} of them in a 2 km view on Skye" if "points_in_view" in row else "")
            + f". Simplifying took {took:.1f} seconds.")
    return out


def coverage_report(layer_name: str, shapes: list, tolerance: float, log: Log) -> dict:
    """Clean a layer, simplify it as one coverage, and check neighbours still meet exactly.

    Cleaning (GEOS coverage cleaning) closes tiny gaps and gives each overlap
    to the neighbour with the longer shared border. It is needed for two
    reasons found in spike S2: where a border meets the coast, cutting to the
    land can leave the neighbours a few metres apart; and OSM's own borders
    sometimes overlap, as Burgos and Soria do in Spain.
    """
    arr = np.array([s for s in shapes if not s.is_empty], dtype=object)
    start = time.perf_counter()
    valid_before = bool(shapely.coverage_is_valid(arr))
    cleaned = shapely.coverage_clean(arr)
    moved = float(sum(abs(area_km2(a) - area_km2(b)) for a, b in zip(arr, cleaned)))
    valid_cleaned = bool(shapely.coverage_is_valid(cleaned))
    simplified = shapely.coverage_simplify(cleaned, tolerance)
    valid_after = bool(shapely.coverage_is_valid(simplified))
    overlap = 0.0
    tree = shapely.STRtree(simplified)
    for i, j in zip(*tree.query(simplified, predicate="overlaps")):
        if i < j:
            overlap += area_km2(shapely.intersection(simplified[i], simplified[j]))
    took = time.perf_counter() - start
    before = int(shapely.get_num_coordinates(arr).sum())
    after = int(shapely.get_num_coordinates(simplified).sum())
    log(f"{layer_name}: {len(arr)} areas. Valid coverage before cleaning: {'yes' if valid_before else 'no'}, "
        f"after cleaning: {'yes' if valid_cleaned else 'no'} ({moved:.3f} km2 moved), "
        f"after simplifying: {'yes' if valid_after else 'no'}. Overlap after: {overlap:.3f} km2. "
        f"Points {before:,} to {after:,}. {took:.0f} seconds.")
    return {"layer": layer_name, "areas": len(arr), "valid_before": valid_before, "valid_cleaned": valid_cleaned,
            "cleaning_moved_km2": moved, "valid_after": valid_after,
            "overlap_km2": overlap, "points_before": before, "points_after": after, "seconds": took,
            "simplified": simplified}


def check_places(pack_path: Path, log: Log) -> tuple[int, int, list[str]]:
    from mapcore.packs.archive import Pack

    places = yaml.safe_load(PLACES_FILE.read_text(encoding="utf-8"))["places"]
    pack = Pack(pack_path)
    passed, lines, times = 0, [], []
    try:
        for p in places:
            start = time.perf_counter()
            reads_before = pack.reads
            found = pack.at(p["lon"], p["lat"])
            times.append((time.perf_counter() - start) * 1000)
            names = [f["name"] for f in found]
            known = set(names) | {f.get("local_name") for f in found}  # English or local name
            if p.get("sea"):
                ok = not found
                expect = "sea"
            else:
                ok = all(n in known for n in p["includes"])
                expect = ", ".join(p["includes"])
            passed += ok
            heard = ", ".join(names) if names else "sea"
            lines.append(f"{'PASS' if ok else 'FAIL'} {p['name']}: found {heard}. Expected {expect}. "
                         f"{pack.reads - reads_before} pieces read.")
    finally:
        pack.close()
    for line in lines:
        log(line)
    log(f"{passed} of {len(places)} places passed. Each lookup took {np.median(times):.1f} ms on average "
        f"(median), at most {max(times):.0f} ms.")
    return passed, len(places), lines


def pictures(out_dir: Path, layers: dict, log: Log) -> list[str]:
    """PNG pictures for sighted reviewers, drawn with Qt offscreen."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    made = []
    palette = ["#e8d8a9", "#c9e2b3", "#f2c6b4", "#d6c8e6", "#f6e3a1", "#b9dcd2", "#e5c1d3"]
    for name, (bbox, shapes) in layers.items():
        w, s, e, n = bbox
        width = 1400
        scale_x = np.cos(np.radians((s + n) / 2))
        height = int(width * (n - s) / ((e - w) * scale_x))
        img = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor("#a9cce3"))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for k, g in enumerate(shapes):
            g = shapely.simplify(g, (e - w) / width / 2)
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            for poly in shapely.get_parts(g):
                if poly.geom_type != "Polygon":
                    continue
                for ring in [poly.exterior, *poly.interiors]:
                    c = np.asarray(ring.coords)
                    xs = (c[:, 0] - w) / (e - w) * width
                    ys = (n - c[:, 1]) / (n - s) * height
                    path.addPolygon(QPolygonF([QPointF(x, y) for x, y in zip(xs.tolist(), ys.tolist())]))
                    path.closeSubpath()
            p.setBrush(QBrush(QColor(palette[k % len(palette)])))
            p.setPen(QPen(QColor("#5a4a3a"), 1))
            p.drawPath(path)
        p.end()
        file = out_dir / f"{name}.png"
        img.save(str(file))
        made.append(file.name)
    log("Pictures: " + ", ".join(made) + ".")
    return made


# The run -----------------------------------------------------------------

def run(folders: DataFolders) -> int:
    import geodesk

    log = Log()
    config = yaml.safe_load((CONFIG_DIR / "s2_stage1.yaml").read_text(encoding="utf-8"))
    units = yaml.safe_load((CONFIG_DIR / "country_units.yaml").read_text(encoding="utf-8"))
    working = folders.working / "s2-stage1"
    out_dir = folders.output / "s2-stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    gol = folders.root / config["source_gol"]
    log("Spike S2, stage 1: the United Kingdom, France and Spain.")
    log(f"Source: {gol.name}, dated {time.strftime('%d %B %Y', time.localtime(gol.stat().st_mtime))}. "
        f"Land polygons: {landmod.source_path(folders.downloads).name}, dated "
        f"{time.strftime('%d %B %Y', time.localtime(landmod.source_path(folders.downloads).stat().st_mtime))}.")
    timings = {}

    log.heading("Extract")
    t = time.perf_counter()
    # Everything read from the planet file is cached, and the file is closed
    # before the land work starts. GeoDesk maps the file into memory, and on
    # the PO's laptop that mapping grew to about 24 GB and left the system
    # short of memory for the steps after it.
    stamp = f"{gol.stat().st_size}-{gol.stat().st_mtime_ns}"
    extract_key = hashlib.sha1(json.dumps([config, units, stamp, EXTRACT_VERSION], sort_keys=True,
                                          default=str).encode()).hexdigest()[:16]
    extract_cache = working / f"extract-{extract_key}.pkl"
    from_cache = extract_cache.is_file()

    def read_planet():
        lines: list[str] = []
        world = geodesk.Features(str(gol))
        try:
            found = extract(world, config, units, lines.append)
            uk_area = next(a for a in found[0] if a.id == config["countries"][0]["id"])
            named = named_islands(world, uk_area)
        finally:
            del world
            import gc
            gc.collect()
        return (*found, named, lines)

    countries, unit_areas, divisions, repairs, island_names, extract_lines = cached(extract_cache, read_planet)
    for line in extract_lines:
        log(line)
    if from_cache:
        log("Read from the cache of an earlier run; the planet file was not opened.")
    timings["extract"] = time.perf_counter() - t
    log(f"Repairs: {len(repairs)}.")
    for r in repairs:
        log(f"  {r}")

    log.heading("Land polygons")
    t = time.perf_counter()
    land = clip.Land(landmod.load(folders.downloads, working, config["regions"], say=log))
    timings["land"] = time.perf_counter() - t

    log.heading("Clip to the land")
    t = time.perf_counter()
    every = countries + unit_areas + [a for v in divisions.values() for a in v]
    clipped = clip_all(land, every, working, log)
    timings["clip"] = time.perf_counter() - t
    raw_km2 = sum(area_km2(a.geom) for a in countries[:3])
    land_km2 = sum(area_km2(clipped[a.id]) for a in countries[:3])
    log(f"Clipped {len(every)} areas in {timings['clip']:.0f} seconds. The UK, France and Spain cover "
        f"{raw_km2:,.0f} km2 with their territorial waters, and {land_km2:,.0f} km2 of land.")
    for a in countries[:3] + [x for x in countries if x.id in ("osm:r1278736", "osm:r9407")]:
        log(f"  {english(a)}: {area_km2(a.geom):,.0f} km2 before, {area_km2(clipped[a.id]):,.0f} km2 of land.")

    # The Countries layer: France is replaced by its units (6.12).
    france = "osm:r2202162"
    country_layer = [a for a in countries if a.id != france] + unit_areas

    log.heading("Land in no country")
    t = time.perf_counter()
    near = shapely.union_all([a.geom for a in countries[:3]]).buffer(0.01)
    near_land = land.clip(near)
    no_country = clip.gaps(near_land, [clipped[a.id] for a in countries], [english(a) for a in countries])
    log(f"Pieces of land within about 1 km of the UK, France and Spain that are in no country: {len(no_country)}, "
        f"{sum(s.area_km2 for s in no_country):.3f} km2 in all.")
    for s in no_country[:15]:
        log(f"  {s.area_km2 * 100:.2f} hectares at {s.centre[1]:.4f} north, {s.centre[0]:.4f} east, beside {s.near}.")
    level_gaps = {}
    for (cid, level), divs in divisions.items():
        country = next(a for a in countries if a.id == cid)
        container = clipped[cid]
        if cid == france:
            container = shapely.union_all([clipped[u.id] for u in unit_areas])
        g = clip.gaps(container, [clipped[d.id] for d in divs], [english(d) for d in divs])
        level_gaps[(cid, level)] = g
        log(f"{english(country)}: land in no level {level} area: {len(g)} pieces, "
            f"{sum(s.area_km2 for s in g):.3f} km2." + (f" Largest {g[0].area_km2 * 100:.2f} hectares, "
                                                      f"beside {g[0].near}." if g else ""))
    timings["gaps"] = time.perf_counter() - t

    log.heading("The UK's islands")
    t = time.perf_counter()
    uk = countries[0]
    islands = island_report(island_names, clipped[uk.id], log)
    drawing = drawing_report(clipped[uk.id], log)
    timings["islands"] = time.perf_counter() - t

    log.heading("Neighbours after simplifying (AD-16)")
    t = time.perf_counter()
    cov = []
    for (cid, level), divs in divisions.items():
        if cid == france and level == 4:
            continue  # France's regions include the overseas regions far away; level 6 is the test
        country = next(a for a in countries if a.id == cid)
        cov.append(coverage_report(f"{english(country)} level {level}", [clipped[d.id] for d in divs], 0.005, log))
    # Across levels: dissolve the simplified level 6 areas of the UK into the
    # level 4 areas and compare with the level 4 areas simplified on their own.
    uk4 = divisions[(uk.id, 4)]
    uk6 = divisions[(uk.id, 6)]
    simplified6 = next(c for c in cov if c["layer"].startswith("United Kingdom level 6"))["simplified"]
    simplified4 = next(c for c in cov if c["layer"].startswith("United Kingdom level 4"))["simplified"]
    mismatch = 0.0
    for d4, s4 in zip([d for d in uk4 if not clipped[d.id].is_empty], simplified4):
        members = [s6 for d6, s6 in zip([d for d in uk6 if not clipped[d.id].is_empty], simplified6)
                   if shapely.contains(clipped[d4.id], shapely.point_on_surface(clipped[d6.id]))]
        if members:
            dissolved = shapely.union_all(members)
            mismatch += area_km2(shapely.symmetric_difference(dissolved, s4))
    log(f"Across levels: the UK's level 6 areas, simplified then joined, differ from its level 4 areas "
        f"simplified on their own by {mismatch:.2f} km2 in all.")
    timings["coverage"] = time.perf_counter() - t

    log.heading("Pack")
    records, geoms = [], []
    layer_of = {2: "countries", 3: "countries", 4: "regions", 6: "counties"}
    for a in country_layer:
        records.append({"id": a.id, "name": a.tags.get("unit_name") or english(a), "local_name": a.name,
                        "layer": "countries", "type": a.tags.get("unit_type", "country"),
                        "sovereign": a.tags.get("sovereign") or units["sovereigns"].get(a.id, english(a)),
                        "area_km2": round(area_km2(clipped[a.id]), 3)})
        geoms.append(clipped[a.id])
    for (cid, level), divs in divisions.items():
        for d in divs:
            if any(d.id == u.id for u in unit_areas):
                continue  # already in the Countries layer as a unit
            records.append({"id": d.id, "name": english(d), "local_name": d.name, "layer": layer_of[level],
                            "type": f"level {level}", "parent": cid, "area_km2": round(area_km2(clipped[d.id]), 3)})
            geoms.append(clipped[d.id])
    keep = [i for i, g in enumerate(geoms) if not g.is_empty]
    records = [records[i] for i in keep]
    geoms = [geoms[i] for i in keep]
    manifest = {"name": config["name"], "source": gol.name, "licence": "ODbL 1.0, OpenStreetMap contributors"}
    packs = {}
    for encoding in ("wkb", "compact"):
        path = out_dir / f"s2-stage1-{encoding}.pack"
        packs[encoding] = pack_write.write(path, manifest, records, geoms, encoding, say=log)
    saving = packs["wkb"]["bytes"] / packs["compact"]["bytes"]
    log(f"Compact coordinates make the pack {saving:.1f} times smaller.")

    log.heading("Coastline places")
    passed, total, place_lines = check_places(out_dir / "s2-stage1-compact.pack", log)

    log.heading("Pictures")
    def bbox(geom_list):
        return shapely.union_all([g.envelope for g in geom_list]).bounds
    uk_divs = [clipped[d.id] for d in divisions[(uk.id, 6)]]
    fr_metro = next(u for u in unit_areas if u.tags["unit_type"] == "metropolitan France")
    fr_divs = [clipped[d.id] for d in divisions[(france, 6)]
               if shapely.intersects(clipped[d.id], clipped[fr_metro.id].envelope)]
    es = countries[2]
    es_divs = [clipped[d.id] for d in divisions[(es.id, 6)]]
    pics = pictures(out_dir, {
        "uk-counties": ((-8.7, 49.8, 2.0, 61.0), uk_divs),
        "france-departements": ((-5.3, 41.2, 9.8, 51.2), fr_divs),
        "spain-provinces": ((-9.5, 35.8, 4.5, 44.0), es_divs),
        "canary-islands": ((-18.3, 27.5, -13.3, 29.5), es_divs),
        "gibraltar-ceuta": ((-5.7, 35.75, -5.15, 36.3),
                            [clipped[a.id] for a in countries if a.id in ("osm:r1311341", "osm:r1278736",
                                                                         "osm:r3630439")]),
        "llivia-andorra": ((1.35, 42.35, 2.15, 42.7),
                           [clipped[a.id] for a in countries if a.id in ("osm:r1311341", "osm:r9407")]
                           + [clipped[fr_metro.id]]),
    }, log)

    log.heading("Measurements")
    total_s = log.elapsed()
    log(f"Total time: {total_s / 60:.1f} minutes. Peak memory: {peak_memory_mb():,.0f} MB.")
    for k, v in timings.items():
        log(f"  {k}: {v:.0f} seconds.")
    working_mb = sum(f.stat().st_size for f in working.rglob("*") if f.is_file()) / 1e6
    log(f"Working folder: {working_mb:,.0f} MB. Packs: WKB {packs['wkb']['bytes'] / 1e6:.1f} MB, "
        f"compact {packs['compact']['bytes'] / 1e6:.1f} MB.")

    summary = {
        "places_passed": passed, "places": total, "islands": islands, "drawing": drawing,
        "coverage": [{k: v for k, v in c.items() if k != "simplified"} for c in cov],
        "cross_level_mismatch_km2": mismatch, "packs": packs, "timings": timings,
        "no_country": [asdict(s) for s in no_country],
        "level_gaps": {f"{k[0]} level {k[1]}": [asdict(s) for s in v] for k, v in level_gaps.items()},
        "repairs": repairs, "peak_memory_mb": peak_memory_mb(), "total_seconds": total_s, "pictures": pics,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    (out_dir / "report.txt").write_text("\n".join(log.lines) + "\n", encoding="utf-8")
    log(f"Report: {out_dir / 'report.txt'}")
    return 0 if passed == total else 1
