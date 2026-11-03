"""Stage "join": join the grid squares into whole areas, and name every place (P1-T4, LOC-6, AD-19, DP114, DP117).

From the grid squares built by the stage before:

1. Each area's parts are joined across the grid squares. Neighbouring grid
   squares meet exactly, so the joins are exact.
2. Land in no country is a sliver if it is thin or tiny: it is given to the
   neighbour it shares the longest border with. Otherwise it is unclaimed
   land, such as Bir Tawil, and is named from the list in the settings, or
   "Unclaimed" if it is not on the list yet (DP114). Every one is reported.
3. Water in no VLIZ ocean is given to the ocean it shares the longest coast
   with. Water with no ocean beside it, such as the Caspian Sea, is named
   from the list of named waters in the settings (DP114). If it is not on the
   list, it is given to the nearest ocean, and the report says so.
4. The layers are made: Countries (with country units, condominiums and
   unclaimed land), Regions, and Oceans and seas.
5. Each area gets a colour number different from every neighbour in its
   layer (AD-19), from the neighbours each grid square found.
6. Every quarter of a degree over the area built is checked to be in a
   country or a sea (LOC-6), one grid square at a time.

Settings:

* sliver_width_m: land thinner than this on average is a sliver, 200 by default.
* sliver_km2: land smaller than this is a sliver, whatever its shape, 0.1 by default.
* unclaimed: known unclaimed land, each with name, point [longitude, latitude] and note.
* named_waters: water with no ocean beside it, each with id, name and point.
"""
from __future__ import annotations

import json
import math
import pickle
from collections import defaultdict

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import grid
from mapdata.stages.geodesy import area_km2
from mapdata.stages.squares import AREAS, SQUARES

SMALL_ISLAND_KM2 = 1.0  # unclaimed islands smaller than this are counted in the report, and listed in the log
GRID_STEP = 0.25  # the no-gaps check, every quarter of a degree (LOC-6)


def key_of(label) -> tuple:
    return tuple(label)


def width_m(g) -> float:
    """Average width: twice the area over the outline's length, in metres, at the shape's latitude."""
    lat = (g.bounds[1] + g.bounds[3]) / 2
    k = math.cos(math.radians(lat))
    # Measured in a frame with longitude shrunk to match latitude.
    h = shapely.transform(g, lambda xy: xy * np.array([k, 1.0]))
    return 2 * h.area / max(h.length, 1e-12) * grid.METRES_PER_DEGREE


def colours(ids: list[str], pairs: set[tuple[str, str]]) -> dict[str, int]:
    """Colour numbers from 1, different for each pair of neighbours: the most neighbours first (AD-19)."""
    near: dict[str, set[str]] = defaultdict(set)
    for a, b in pairs:
        if a != b:
            near[a].add(b)
            near[b].add(a)
    out: dict[str, int] = {}
    for i in sorted(ids, key=lambda i: (-len(near[i]), i)):
        used = {out[n] for n in near[i] if n in out}
        c = 1
        while c in used:
            c += 1
        out[i] = c
    return out


def run(ctx) -> None:
    s = ctx.settings
    areas = json.loads((ctx.previous / AREAS).read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in areas["records"]}
    condos = {c["id"]: c for c in areas.get("condominiums") or []}
    paths = sorted((ctx.previous / SQUARES).glob("*.pkl"))
    if not paths:
        raise BuildStopped("The stage before built no grid squares.")

    parts: dict[tuple, list] = defaultdict(list)
    pairs: set[tuple[tuple, tuple]] = set()
    overlaps: dict[tuple, float] = defaultdict(float)
    fills: dict[tuple, float] = defaultdict(float)
    before = after = 0
    for n, p in enumerate(paths, 1):
        r = pickle.loads(p.read_bytes())
        labels = [key_of(x) for x in r["labels"]]
        for lab, b in zip(labels, r["shapes"]):
            parts[lab].append(shapely.from_wkb(b))
        for i, j in r.get("pairs", []):
            pairs.add(tuple(sorted((labels[i], labels[j]), key=str)))
        for o in r["overlaps"]:
            overlaps[(o[0], tuple(o[1]))] += o[2]
        for f in r["fills"]:
            fills[tuple(f[:3])] += f[3]
        before += r["points_before"]
        after += r["points_after"]
        if n % 2000 == 0:
            ctx.progress.line(f"Reading the grid squares: {n} of {len(paths)}.")
    ctx.progress.line(f"Read {len(paths)} grid squares: {before:,} points before simplifying, {after:,} after.")

    # Each area is kept as its parts, one for each grid square, until the end. Neighbours are found
    # among those small parts, never among whole areas: measuring the shared coast against the whole
    # North Atlantic for each of thousands of bits of water took far too long.
    land_labels = sorted((k for k in parts if k[0] == "land" and k != grid.WAITING_LAND), key=str)
    water_labels = sorted((k for k in parts if k[0] == "water" and k != grid.WAITING_WATER), key=str)
    shapes: dict[tuple, list] = {k: list(parts[k]) for k in land_labels + water_labels}
    report: list[str] = []

    def part_tree(labels):
        keys, geoms_ = [], []
        for k in labels:
            for g in parts[k]:
                keys.append(k)
                geoms_.append(g)
        return keys, (shapely.STRtree(geoms_) if geoms_ else None), geoms_

    def best_neighbour(comp, keys, tree, geoms_):
        """The area sharing the longest edge with comp, found among the parts near it."""
        if tree is None:
            return None
        shared: dict[tuple, float] = defaultdict(float)
        edge = comp.boundary
        for i in tree.query(comp, predicate="intersects").tolist():
            shared[keys[i]] += shapely.intersection(edge, geoms_[i].boundary).length
        shared = {k: v for k, v in shared.items() if v > 0}
        if not shared:
            return None
        return max(sorted(shared, key=str), key=lambda k: shared[k])

    # Land in no country.
    unclaimed_list = s.get("unclaimed") or []
    new_records: dict[str, dict] = {}
    waiting = parts.get(grid.WAITING_LAND, [])
    sliver_w, sliver_a = float(s.get("sliver_width_m", 200)), float(s.get("sliver_km2", 0.1))
    l_keys, l_tree, l_geoms = part_tree(land_labels)
    given = 0
    given_km2 = 0.0
    small_islands: list[float] = []
    comps = list(shapely.get_parts(shapely.coverage_union_all(waiting))) if waiting else []
    for comp in comps:
        km2 = area_km2(comp)
        best = best_neighbour(comp, l_keys, l_tree, l_geoms)
        p = shapely.point_on_surface(comp)
        if best is not None and (km2 < sliver_a or width_m(comp) < sliver_w):
            shapes[best].append(comp)
            given += 1
            given_km2 += km2
            continue
        known = next((u for u in unclaimed_list if shapely.intersects(comp, shapely.Point(u["point"]))), None)
        if known:
            uid, name, note = f"unclaimed:{known['name'].lower().replace(' ', '-')}", known["name"], known.get("note")
        else:
            uid, name, note = f"unclaimed:{p.y:.2f}:{p.x:.2f}", "Unclaimed", None
        lab = ("land", uid, None)
        shapes.setdefault(lab, []).append(comp)
        new_records[uid] = {"id": uid, "name": name, "kind": "unclaimed", "note": note}
        if best is not None:
            pairs.add(tuple(sorted((lab, best), key=str)))
        line = (f"Unclaimed land: {name}, {km2:,.2f} km2, at {p.y:.3f} north, {p.x:.3f} east"
                + (f", beside {by_id.get(best[1], {}).get('name', best[1])}" if best else ", an island")
                + ("." if known else ". It is not on the list of unclaimed land in the settings yet."))
        if best is None and not known and km2 < SMALL_ISLAND_KM2:
            small_islands.append(km2)
            ctx.progress.log(line)
        else:
            report.append(line)
    ctx.progress.line(f"Slivers of land in no country given to their neighbour: {given}, {given_km2:,.2f} km2 in all.")
    if small_islands:
        report.append(f"Small islands in no country, each under {SMALL_ISLAND_KM2:g} km2, named Unclaimed: "
                      f"{len(small_islands)}, {sum(small_islands):,.2f} km2 in all. The log lists each one.")

    # Water in no ocean.
    named = s.get("named_waters") or []
    waiting = parts.get(grid.WAITING_WATER, [])
    w_keys, w_tree, w_geoms = part_tree(water_labels)
    given = 0
    given_km2 = 0.0
    comps = list(shapely.get_parts(shapely.coverage_union_all(waiting))) if waiting else []
    ctx.progress.line(f"Water in no VLIZ ocean: {len(comps)} parts, each to be given to the ocean beside it.")
    for comp in comps:
        km2 = area_km2(comp)
        p = shapely.point_on_surface(comp)
        known = next((w for w in named if shapely.intersects(comp, shapely.Point(w["point"]))), None)
        best = None if known else best_neighbour(comp, w_keys, w_tree, w_geoms)
        if known:
            lab = ("water", known["id"], None)
            new_records[known["id"]] = {"id": known["id"], "name": known["name"], "kind": "sea"}
            report.append(f"Water in no VLIZ ocean, named from the settings: {known['name']}, {km2:,.0f} km2.")
        elif best is not None:
            lab = best
            given += 1
            given_km2 += km2
        else:
            if w_tree is None:
                raise BuildStopped(f"Water at {p.y:.3f} north, {p.x:.3f} east is in no ocean, and no ocean was read.")
            lab = w_keys[int(w_tree.query_nearest(comp)[0])]
            report.append(f"Water in no ocean and not beside one, {km2:,.1f} km2 at {p.y:.3f} north, {p.x:.3f} east, "
                          f"is given to the nearest, {by_id[lab[1]]['name']}. Add it to the named waters in the "
                          "settings if it has its own name.")
        shapes.setdefault(lab, []).append(comp)
    ctx.progress.line(f"Water in no VLIZ ocean given to the ocean beside it: {given} parts, {given_km2:,.0f} km2.")

    # The layers: each area joined once, from all its parts.
    layer_parts: dict[tuple[str, str], list] = defaultdict(list)
    region_country: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    label_layers: dict[tuple, list[tuple[str, str]]] = {}
    for lab, gs in shapes.items():
        kind, a, b = lab
        if kind == "water":
            label_layers[lab] = [("oceans", a)]
        else:
            label_layers[lab] = [("countries", a)] + ([("regions", b)] if b else [])
            if b:
                region_country[b][a] += sum(g.area for g in gs)
        for layer_key in label_layers[lab]:
            layer_parts[layer_key].extend(gs)
    records, geoms = [], []
    layer_ids: dict[str, list[str]] = defaultdict(list)
    for (layer, fid), gs in sorted(layer_parts.items()):
        g = gs[0] if len(gs) == 1 else shapely.coverage_union_all(gs)
        src = by_id.get(fid) or new_records.get(fid) or {}
        rec = {"id": fid, "layer": layer}
        if layer == "countries":
            if fid in condos:
                c = condos[fid]
                names = [by_id[i]["name"] for i in c["countries"] if i in by_id]
                rec.update(name=c["name"], type="condominium", sovereign=" and ".join(names))
            elif src.get("kind") == "unclaimed":
                rec.update(name=src["name"], type="unclaimed land")
                if src.get("note"):
                    rec["note"] = src["note"]
            else:
                rec.update(name=src.get("unit_name") or src["name"], local_name=src.get("local_name"),
                           type=src.get("unit_type") or "country")
                sov = src.get("sovereign")
                if sov:
                    rec["sovereign"] = sov
        elif layer == "regions":
            owners = region_country[fid]
            rec.update(name=src["name"], local_name=src.get("local_name"), type="region",
                       level=src.get("level"), parent=max(sorted(owners), key=lambda k: owners[k]))
            for k in ("disputed", "also_held_as", "iso2"):
                if src.get(k):
                    rec[k] = src[k]
        else:
            rec.update(name=src["name"], type=src.get("kind", "ocean"))
        if src.get("wikidata"):
            rec["wikidata"] = src["wikidata"]
        records.append({k: v for k, v in rec.items() if v is not None})
        geoms.append(g)
        layer_ids[layer].append(fid)

    # Colour numbers (AD-19).
    layer_pairs: dict[str, set] = defaultdict(set)
    for la, lb in pairs:
        if la not in label_layers or lb not in label_layers:
            continue
        for (layer_a, ia) in label_layers[la]:
            for (layer_b, ib) in label_layers[lb]:
                if layer_a == layer_b and ia != ib:
                    layer_pairs[layer_a].add((ia, ib))
    colour = {layer: colours(ids, layer_pairs[layer]) for layer, ids in layer_ids.items()}
    for r in records:
        r["colour"] = colour[r["layer"]][r["id"]]
    for layer, ids in sorted(layer_ids.items()):
        n = max(colour[layer].values()) if ids else 0
        ctx.progress.line(f"{layer}: {len(ids)} areas, {len(layer_pairs[layer])} pairs of neighbours, "
                          f"{n} colour numbers.")

    for line in report:
        ctx.progress.line(line)
    for (layer, ids), km2 in sorted(overlaps.items(), key=lambda kv: -kv[1]):
        names = " and ".join(by_id.get(i, {}).get("name", i) for i in ids)
        ctx.progress.line(f"Overlap in {layer}: {names} ({', '.join(ids)}) both hold {km2:,.2f} km2. The smaller "
                          "area keeps it.")
    filled: dict[tuple, float] = defaultdict(float)
    for (country, region, level), km2 in fills.items():
        filled[(country, level)] += km2
    for (country, level), km2 in sorted(filled.items()):
        n = len({r for (c, r, lv) in fills if c == country and lv == level})
        ctx.progress.log(f"Regions filled from level {level} in {by_id.get(country, {}).get('name', country)}: "
                         f"{n} areas, {km2:,.0f} km2.")
    countries_filled = sorted({c for (c, _lv) in filled})
    ctx.progress.line(f"Countries with regions filled from level 3 or 5 where level 4 has none: "
                      f"{len(countries_filled)}. The log lists them.")

    no_gaps(ctx, paths, records, geoms)
    features.save(ctx.folder, records, geoms, ctx.claim)
    summary = {"points_before": before, "points_after": after, "squares": len(paths),
               "overlaps": [[layer, list(ids), km2] for (layer, ids), km2 in overlaps.items()],
               "report": report}
    ctx.claim(ctx.folder / "join.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False),
                                                   encoding="utf-8", newline="\n")


def no_gaps(ctx, paths, records, geoms) -> None:
    """Every quarter of a degree in the grid squares built is in a country or a sea (LOC-6)."""
    named = [g for r, g in zip(records, geoms) if r["layer"] in ("countries", "oceans")]
    shapely.prepare(named)  # each point is tested against whole areas, so they are prepared once
    tree = shapely.STRtree(named)
    missing = []
    total = 0
    for p in paths:
        r = pickle.loads(p.read_bytes())
        w, s, e, n = shapely.total_bounds(shapely.from_wkb(np.array(r["shapes"], dtype=object)))
        xs = np.arange(math.ceil(w / GRID_STEP) * GRID_STEP, e, GRID_STEP)
        ys = np.arange(math.ceil(s / GRID_STEP) * GRID_STEP, n, GRID_STEP)
        if len(xs) == 0 or len(ys) == 0:
            continue
        gx, gy = np.meshgrid(xs, ys)
        pts = shapely.points(gx.ravel(), gy.ravel())
        total += len(pts)
        hit = np.zeros(len(pts), bool)
        found = tree.query(pts, predicate="intersects")[0]
        hit[found] = True
        missing.extend(pts[~hit].tolist())
    if missing:
        where = "; ".join(f"{q.y:.2f} north, {q.x:.2f} east" for q in missing[:10])
        raise BuildStopped(f"The no-gaps check failed (LOC-6): {len(missing)} of {total:,} points are in no "
                           f"country and no sea, such as {where}. This is a fault in the build; please report it.")
    ctx.progress.line(f"The no-gaps check passed (LOC-6): all {total:,} points, every quarter of a degree, are in a "
                      "country or a sea.")
