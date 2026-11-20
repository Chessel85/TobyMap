"""Stage "coast-stretches": each area's coast in stretches, with an end at each neighbour (P3-T30b, INF-2).

The design is the Hampshire trial's, docs/plan/p3-t30a-coast-report.md, with the PO's answers of 20 November 2026:

* An area's coast is where its outline meets the outline of the sea, the oceans layer, which holds all the water, as
  the relationships stage measures coast. So the coast found here adds up to the coast the relationships stage stored.
* A neighbour's sliver on the shore counts as sea: a part under sliver_km2 (0.05 square kilometres) of another area of
  the same layer, which has a larger part elsewhere, touching the sea. Portsmouth has about 30 such slivers along the
  north shore of Portsmouth Harbour, where its border and the coast do not quite match; without this rule they break
  Hampshire's coast into dozens of short stretches.
* The coast is joined into lines, and a break under gap_m (100 metres) between two ends is joined over.
* A line with two ends is a stretch of coast. At each end, the neighbour is the area of the same layer that touches
  it, or failing that the nearest within 100 metres. A line that closes on itself is the coast of an island, with no
  ends.
* Lengths are over the Earth, as the relationships stage measures every border.

What it keeps, in relationships.json beside the features, both copied from the stage before unchanged: for each area
with at least one stretch of least_km (1 kilometre) or more, "coast_stretches", an object holding:

* stretches: those of least_km or more, west to east by their west end, each an object: km, its length; ends, its west
  end then its east end, each [lon, lat, the neighbour's index or null]; half, [lon, lat], the point half way along
  it; water, the index of the sea it lies on (the most detailed water of the area's stored coast that touches most of
  it), or null; and line, the stretch simplified to tolerance_m (200 metres), for the application to find its nearest
  point to you, as its first point then the step to each next one, in 1/10,000 degree (about 11 metres).
* islands_km: the length of its coast round islands, with no ends.

Stretches under least_km are not kept, but their length still counts in the Coast heading's whole length, which is
the relationships stage's. The writing stage turns the indexes into identifiers (with_ids).

Checks: each area's coast found here, stretches and islands together, against its stored coast plus the shore along
the slivers counted as sea; and each end with a neighbour against the ends of that neighbour's own coast. The build
report says how many differ, and the log lists each.

Settings: sliver_km2 (0.05), gap_m (100), least_km (1), tolerance_m (200), samples (9, the points along a stretch
tested for its water), end_match_m (200, how near the neighbour's end must be for the check).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import time

import numpy as np
import shapely

from mapcore.packs import coords
from mapdata.pipeline import features
from mapdata.stages.geodesy import areas_km2
from mapdata.stages.relationships import FILE, SETTINGS as REL_SETTINGS, lengths_km, sea_and_land

SETTINGS = {"sliver_km2": 0.05, "gap_m": 100.0, "least_km": 1.0, "tolerance_m": 200.0, "samples": 9,
            "end_match_m": 200.0}
KEY = "coast_stretches"
CHUNK = 200            # points in each short line of the sea's outline, for the spatial index
M_PER_DEG = 111_320.0  # metres in a degree of latitude, near enough for gaps of 100 metres
TOUCH_DEG = 1e-7       # shapes touching, allowing for rounding
WATER_DEG = 1e-5       # a point of the coast on a water's outline, about a metre
BATCH_POINTS = 400_000  # points of outline and sea in one job for a worker


# Finding the stretches of one area: given its outline and the sea's outlines near it only, so it can run in a worker.

def coast_pieces(outline, sea_edges: list, sliver_edges: list) -> tuple[list[np.ndarray], float, float]:
    """The coast of an outline: where it lies on the sea's outline or a sliver's, as lines joined where they meet.
    Returns the lines' points, the km on the sea and the km on slivers."""
    found, kms = [], []
    for edges in (sea_edges, sliver_edges):
        if not edges:
            kms.append(0.0)
            continue
        # One shape of all the lines, not their union: the overlay nodes them itself, and a union costs as much again.
        near = shapely.multilinestrings(np.array(edges, dtype=object))
        try:
            got = shapely.intersection(outline, near)
        except shapely.errors.GEOSException:
            got = shapely.intersection(shapely.set_precision(outline, 1e-9), shapely.set_precision(near, 1e-9))
        lines = _lines(got)
        kms.append(float(lengths_km(lines).sum()) if len(lines) else 0.0)
        found.extend(lines)
    if not found:
        return [], kms[0], kms[1]
    # The pieces never overlap, as each lies on the outline once, so they are joined with no union first.
    merged = shapely.line_merge(shapely.multilinestrings(np.array(found, dtype=object)))
    pieces = [shapely.get_coordinates(p) for p in _lines(merged)]
    return [c for c in pieces if len(c) >= 2], kms[0], kms[1]


def _lines(g) -> np.ndarray:
    """The lines in a shape, each part on its own; points left out."""
    parts = shapely.get_parts(shapely.get_parts(shapely.get_parts(g)))
    t = shapely.get_type_id(parts)
    parts = parts[(t == 1) | (t == 2)]
    return parts[shapely.length(parts) > 0]


def _metres(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distance between points (lon, lat) in metres, flat, near enough for gaps of tens of metres."""
    lat = np.radians((a[..., 1] + b[..., 1]) / 2.0)
    dx = (b[..., 0] - a[..., 0]) * np.cos(lat) * M_PER_DEG
    dy = (b[..., 1] - a[..., 1]) * M_PER_DEG
    return np.hypot(dx, dy)


def join_gaps(pieces: list[np.ndarray], gap_m: float) -> list[tuple[np.ndarray, bool, float]]:
    """Lines joined over breaks under gap_m, nearest first, each end joined once. Returns each line as (points,
    closed, km), its km the coast's own length, not the breaks'. A line whose ends join is closed: an island's coast."""
    kms = lengths_km(np.array([shapely.LineString(c) for c in pieces], dtype=object)) if pieces else []
    out, open_ = [], []
    for c, km in zip(pieces, kms):
        if len(c) > 3 and _metres(c[0], c[-1]) == 0.0:
            out.append((c, True, float(km)))
        else:
            open_.append((c, float(km)))
    if not open_:
        return out
    n = len(open_)
    ends = np.array([[c[0], c[-1]] for c, _km in open_]).reshape(2 * n, 2)   # end e is piece e // 2, side e % 2
    pairs = []
    if n <= 1500:
        d = _metres(ends[:, None, :], ends[None, :, :])
        a, b = np.nonzero(np.triu(d <= gap_m, 1))
        pairs = sorted(zip(d[a, b].tolist(), a.tolist(), b.tolist()))
    else:
        tree = shapely.STRtree(shapely.points(ends))
        reach = gap_m / M_PER_DEG / max(0.05, math.cos(math.radians(min(85.0, float(np.abs(ends[:, 1]).max())))))
        a, b = tree.query(shapely.points(ends), predicate="dwithin", distance=reach)
        keep = a < b
        a, b = a[keep], b[keep]
        d = _metres(ends[a], ends[b])
        ok = d <= gap_m
        pairs = sorted(zip(d[ok].tolist(), a[ok].tolist(), b[ok].tolist()))
    link: dict[int, int] = {}
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ring = set()
    for _d, a, b in pairs:
        if a in link or b in link:
            continue
        pa, pb = find(a // 2), find(b // 2)
        if pa == pb:   # the last join closes a line on itself
            ring.add(pa)
        else:
            parent[pa] = pb
        link[a], link[b] = b, a
    seen = set()

    def walk(e):   # enter piece e // 2 at end e; follow the joins
        pts, km, at = [], 0.0, e
        while True:
            k = at // 2
            if k in seen:
                break
            seen.add(k)
            c, length = open_[k]
            pts.append(c if at % 2 == 0 else c[::-1])
            km += length
            nxt = link.get(at ^ 1)
            if nxt is None:
                break
            at = nxt
        return np.concatenate(pts), km

    for e in range(2 * n):   # open lines first, from a free end
        if e // 2 not in seen and e not in link:
            pts, km = walk(e)
            out.append((pts, False, km))
    for k in range(n):   # the rest are closed
        if k not in seen:
            pts, km = walk(2 * k)
            out.append((np.concatenate([pts, pts[:1]]), True, km))
    return out


def area_job(job) -> list:
    """A worker's job: several areas, each (index, outline, sea edges, sliver edges) in well-known binary. Returns,
    for each, (index, [(points, closed, km)], km on the sea, km on slivers)."""
    areas, gap_m = job
    out = []
    for i, outline, sea, slivers in areas:
        pieces, sea_km, sliver_km = coast_pieces(shapely.from_wkb(outline), list(shapely.from_wkb(sea)),
                                                 list(shapely.from_wkb(slivers)) if slivers is not None else [])
        out.append((i, join_gaps(pieces, gap_m), sea_km, sliver_km))
    return out


# What is kept for each stretch ------------------------------------------------------------------------------------

def _along(c: np.ndarray) -> np.ndarray:
    """Distance along a line at each point, in km over the Earth."""
    lon, lat = np.radians(c[:, 0]), np.radians(c[:, 1])
    a = np.sin((lat[1:] - lat[:-1]) / 2) ** 2 + np.cos(lat[1:]) * np.cos(lat[:-1]) * np.sin((lon[1:] - lon[:-1]) / 2) ** 2
    seg = 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    return np.concatenate([[0.0], np.cumsum(seg)])


def at_share(c: np.ndarray, along: np.ndarray, share: float) -> tuple[float, float]:
    """The point (lon, lat) at a share of the way along a line."""
    total = along[-1]
    if total <= 0:
        return float(c[0][0]), float(c[0][1])
    want = share * total
    k = int(np.searchsorted(along, want, side="right")) - 1
    k = min(max(k, 0), len(c) - 2)
    seg = along[k + 1] - along[k]
    f = 0.0 if seg <= 0 else (want - along[k]) / seg
    p = c[k] + f * (c[k + 1] - c[k])
    return float(p[0]), float(p[1])


def encode_line(c: np.ndarray, tolerance_m: float) -> list[int]:
    """A line simplified to about tolerance_m, stored as mapcore.packs.coords.encode_stretch: its first point and the
    step to each next, in 1/10,000 degree."""
    line = shapely.simplify(shapely.LineString(c), tolerance_m / M_PER_DEG, preserve_topology=False)
    values = coords.encode_stretch(shapely.get_coordinates(line))
    return values if len(values) >= 4 else coords.encode_stretch(np.array([c[0], c[-1]]))


def decode_line(values: list[int]) -> np.ndarray:
    """The points (lon, lat) of a stored line (encode_line)."""
    return coords.decode_stretch(values)


# The stage -------------------------------------------------------------------------------------------------------

def _load(folder, layers: set[str], also: set[int]) -> tuple[list[dict], dict[int, object]]:
    """Every record, and by their index the shapes of the named layers and of the features numbered in also."""
    data = json.loads((folder / "features.json").read_text(encoding="utf-8"))
    shapes = {}
    with open(folder / "shapes.wkb", "rb") as f:
        for i, (r, (a, n)) in enumerate(zip(data["records"], data["shapes"])):
            if r.get("layer") in layers or i in also:
                f.seek(a)
                shapes[i] = shapely.from_wkb(f.read(n))
    return data["records"], shapes


def edge_lines(shapes: list, chunk: int = CHUNK) -> tuple[np.ndarray, np.ndarray]:
    """The outlines of shapes cut into short lines, for a spatial index, with the index in shapes of each."""
    out, owner = [], []
    for k, g in enumerate(shapes):
        for ring in shapely.get_parts(shapely.get_parts(shapely.boundary(g))):
            c = shapely.get_coordinates(ring)
            for a in range(0, len(c) - 1, chunk):
                out.append(shapely.LineString(c[a:a + chunk + 1]))
                owner.append(k)
    return np.array(out, dtype=object), np.array(owner, dtype=np.intp)


def find_slivers(layer_shapes: dict[int, object], sea_tree, km2: float) -> list[tuple[int, object]]:
    """The bits of one layer that may be slivers on the shore: each part of an area under km2, touching the sea, as
    (the area's index, the part). A whole area that small counts too, such as a rock beside a larger island. Only those
    on another area's outline are counted as sea for it."""
    keys = list(layer_shapes)
    if not keys:
        return []
    parts, which = shapely.get_parts(np.array([layer_shapes[i] for i in keys], dtype=object), return_index=True)
    small = np.nonzero(areas_km2(parts) < km2)[0]
    if not len(small):
        return []
    hits, _ = sea_tree.query(parts[small], predicate="dwithin", distance=TOUCH_DEG)
    return [(keys[int(which[small[k]])], parts[small[k]]) for k in sorted(set(hits.tolist()))]


def neighbour_at(lon: float, lat: float, own: int, tree, ids: np.ndarray, shapes: list) -> int | None:
    """The area of the layer touching an end, else the nearest within about 100 metres; None if there is none."""
    pt = shapely.Point(lon, lat)
    for reach in (1e-6, 1e-4, 1e-3):
        cand = [k for k in tree.query(shapely.box(lon - reach, lat - reach, lon + reach, lat + reach))
                if ids[k] != own]
        if not cand:
            continue
        d = [float(shapely.distance(shapes[k], pt)) for k in cand]
        best = min(range(len(cand)), key=lambda j: (d[j], int(ids[cand[j]])))
        if d[best] <= reach:
            return int(ids[cand[best]])
    return None


def water_of(c: np.ndarray, along: np.ndarray, allowed: dict[int, float], water_tree, water_owner, water_ids,
             detail: dict[int, tuple], samples: int) -> int | None:
    """The sea a stretch lies on: of the waters of the area's stored coast (allowed, with their km of it), the most
    detailed touching at least half the points tested along it, else the one touching most. A stretch touching none,
    as one wholly along a neighbour's slivers, takes the area's own sea: the water with most of its coast, the most
    detailed of those."""
    counts: dict[int, int] = {}
    for s in range(samples):
        lon, lat = at_share(c, along, (s + 0.5) / samples)
        hits = water_tree.query(shapely.Point(lon, lat), predicate="dwithin", distance=WATER_DEG)
        for w in {int(water_ids[water_owner[h]]) for h in hits}:
            if w in allowed:
                counts[w] = counts.get(w, 0) + 1
    if not counts:
        known = [w for w in allowed if w in detail]
        return min(known, key=lambda w: (-allowed[w], -detail[w][0], detail[w][1], w)) if known else None
    half = [w for w, n in counts.items() if 2 * n >= samples]
    if half:
        return min(half, key=lambda w: (-detail[w][0], detail[w][1], w))
    return max(counts, key=lambda w: (counts[w], detail[w][0], -w))


def _copy(src, dst) -> None:
    """A file of the stage before, unchanged: linked where the drive allows, else copied."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def stored_coast_km(rel: dict, sea_ids: set[int]) -> float:
    """An area's coast as the relationships stage stored it: its coast on the sea, the oceans layer."""
    return float(sum(km for w, km in rel.get("coast", ()) if w in sea_ids))


def run(ctx) -> None:
    t0 = time.perf_counter()
    settings = {**SETTINGS, **{k: v for k, v in ctx.settings.items() if k in SETTINGS}}
    layers = ctx.pack.layers
    sea_layers, _land = sea_and_land(layers)
    land_layers = [k for k in ctx.settings.get("coast_land", REL_SETTINGS["coast_land"]) if k in layers]
    if not (ctx.previous / FILE).is_file():
        from mapdata.pipeline.errors import BuildStopped

        raise BuildStopped("The coast-stretches stage needs the relationships stage just before it.")
    rel = json.loads((ctx.previous / FILE).read_text(encoding="utf-8"))
    rel = {int(k): v for k, v in rel.items()}
    coast_waters = {w for r in rel.values() for w, _km in r.get("coast", ())}
    records, shapes = _load(ctx.previous, set(land_layers) | set(sea_layers), coast_waters)
    sea_ids = {i for i in shapes if records[i]["layer"] in sea_layers}
    ctx.progress.line(f"Read the land areas and the sea in {time.perf_counter() - t0:.0f} seconds.")

    t = time.perf_counter()
    sea_list = sorted(sea_ids)
    sea_edges, _owner = edge_lines([shapes[i] for i in sea_list])
    sea_tree = shapely.STRtree(sea_edges)
    water_list = sorted(w for w in coast_waters if w in shapes)
    water_edges, water_owner = edge_lines([shapes[i] for i in water_list])
    water_tree = shapely.STRtree(water_edges)
    water_ids = np.array(water_list, dtype=np.intp)
    detail = {w: (layers[records[w]["layer"]].rank, float(shapely.area(shapes[w]))) for w in water_list}
    ctx.progress.line(f"Put the sea's outline in an index, {int(shapely.get_num_coordinates(sea_edges).sum()):,} "
                      f"points, in {time.perf_counter() - t:.0f} seconds.")

    stored: dict[int, dict] = {}
    found_all: dict[int, list] = {}    # each area's lines, for the check of the ends
    checks = {"areas": 0, "differ": 0, "ends": 0, "unmatched": 0}
    differ_lines, unmatched_lines = [], []
    from mapdata import parallel

    with parallel.pool(ctx.workers) as executor:
        for layer in land_layers:
            ctx.check_switch(f"the stretches of coast of the {layers[layer].name}")
            t = time.perf_counter()
            own = {i: g for i, g in shapes.items() if records[i]["layer"] == layer}
            coasted = sorted(i for i in own if stored_coast_km(rel.get(i, {}), sea_ids) > 0)
            if not coasted:
                continue
            slivers = find_slivers(own, sea_tree, settings["sliver_km2"])
            sliver_tree = shapely.STRtree(np.array([shapely.boundary(p) for _o, p in slivers], dtype=object)) \
                if slivers else None
            ids = np.array(sorted(own), dtype=np.intp)
            layer_shapes = [own[i] for i in ids]
            tree = shapely.STRtree(np.array(layer_shapes, dtype=object))
            used = set()
            # Jobs of several areas, each with only the sea's outline and the slivers along its own outline.
            # Each job is started as soon as it is made, so the workers start while the rest are being made.
            futures, batch, points = [], [], 0
            for i in coasted:
                outline = shapely.boundary(own[i])
                hits = sea_tree.query(outline, predicate="intersects")
                sl = []
                if sliver_tree is not None:
                    near = [int(k) for k in sliver_tree.query(outline, predicate="intersects") if slivers[k][0] != i]
                    used.update(near)
                    sl = [shapely.boundary(slivers[k][1]) for k in near]
                edges = sea_edges[np.sort(hits)]
                batch.append((i, shapely.to_wkb(outline), shapely.to_wkb(edges),
                              shapely.to_wkb(np.array(sl, dtype=object)) if sl else None))
                points += int(shapely.get_num_coordinates(outline)) + len(hits) * CHUNK
                if points >= BATCH_POINTS:
                    futures.append(executor.submit(area_job, (batch, settings["gap_m"])))
                    batch, points = [], 0
            if batch:
                futures.append(executor.submit(area_job, (batch, settings["gap_m"])))
            n_listed = 0
            for fut in futures:
                for i, lines, sea_km, sliver_km in fut.result():
                    found_all[i] = lines
                    total = sum(km for _c, _closed, km in lines)
                    want = stored_coast_km(rel[i], sea_ids) + sliver_km
                    checks["areas"] += 1
                    if abs(total - want) > max(0.1, 0.01 * want):
                        checks["differ"] += 1
                        differ_lines.append(f"{records[i]['name']} ({layer}): coast found {total:.2f} km, stored "
                                            f"{want - sliver_km:.2f} km and {sliver_km:.2f} km along slivers.")
                    kept = []
                    islands = 0.0
                    for c, closed, km in lines:
                        if closed:
                            islands += km
                            continue
                        if km < settings["least_km"]:
                            continue
                        if c[0][0] > c[-1][0]:
                            c = c[::-1]
                        along = _along(c)
                        ends = [[round(float(lon), 5), round(float(lat), 5), neighbour_at(lon, lat, i, tree, ids, layer_shapes)]
                                for lon, lat in (c[0], c[-1])]
                        hx, hy = at_share(c, along, 0.5)
                        allowed = {w: km for w, km in rel[i].get("coast", ())}
                        kept.append({"km": round(km, 2), "ends": ends, "half": [round(hx, 5), round(hy, 5)],
                                     "water": water_of(c, along, allowed, water_tree, water_owner, water_ids, detail,
                                                       int(settings["samples"])),
                                     "line": encode_line(c, settings["tolerance_m"])})
                    if kept:
                        kept.sort(key=lambda s: (s["ends"][0][0], s["ends"][0][1]))
                        stored[i] = {"stretches": kept, "islands_km": round(islands, 2)}
                        n_listed += len(kept)
            ctx.progress.line(f"Stretches of coast of the {layers[layer].name}: {len(coasted):,} areas with a coast, "
                              f"{n_listed:,} stretches of {settings['least_km']:g} kilometre or more, "
                              f"{len(used):,} slivers on the shore counted as sea, "
                              f"in {time.perf_counter() - t:.0f} seconds.")

    # Each end with a neighbour against the ends of the neighbour's own coast.
    for i, entry in stored.items():
        for s in entry["stretches"]:
            for lon, lat, other in s["ends"]:
                if other is None:
                    continue
                checks["ends"] += 1
                theirs = [e for c, closed, _km in found_all.get(other, ()) if not closed for e in (c[0], c[-1])]
                if not theirs or float(_metres(np.array([lon, lat]), np.array(theirs)).min()) > settings["end_match_m"]:
                    checks["unmatched"] += 1
                    unmatched_lines.append(f"{records[i]['name']}: the end where {records[other]['name']} meets its "
                                           f"coast, at {lat:.4f} {lon:.4f}, has no end of {records[other]['name']}'s "
                                           f"own coast within {settings['end_match_m']:g} metres.")
    for line in differ_lines + unmatched_lines:
        ctx.progress.log(line)
    ctx.progress.line(f"Checked the coast of {checks['areas']:,} areas against the coast stored by the relationships "
                      f"stage: {checks['differ']:,} differ by more than 1 percent. Checked {checks['ends']:,} ends of "
                      f"stretches of coast against the neighbour's: {checks['unmatched']:,} have no end of the "
                      f"neighbour's coast near them. The log lists each.")

    for i, entry in stored.items():
        rel.setdefault(i, {})[KEY] = entry
    for name in ("features.json", "shapes.wkb"):
        _copy(ctx.previous / name, ctx.claim(ctx.folder / name))
    text = json.dumps({str(i): r for i, r in sorted(rel.items())}, sort_keys=True, separators=(",", ":"))
    ctx.claim(ctx.folder / FILE).write_text(text, encoding="utf-8", newline="\n")
    size = len(json.dumps({str(i): e for i, e in stored.items()}, separators=(",", ":")).encode())
    ctx.progress.line(f"Kept {sum(len(e['stretches']) for e in stored.values()):,} stretches of coast for "
                      f"{len(stored):,} areas, {size / 1e6:.2f} MB before compression, in "
                      f"{time.perf_counter() - t0:.0f} seconds.")


def with_ids(rel_by_id: dict[str, dict], ids: list[str]) -> None:
    """The stored stretches with each neighbour's and water's index made the identifier it is written with, in place."""
    for rel in rel_by_id.values():
        entry = rel.get(KEY)
        if not entry:
            continue
        for s in entry["stretches"]:
            s["ends"] = [[lon, lat, None if o is None else ids[o]] for lon, lat, o in s["ends"]]
            if s.get("water") is not None:
                s["water"] = ids[s["water"]]
