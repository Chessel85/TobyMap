"""Stage "write": write the pack in format 3, with its manifest, attribution and checksum (architecture 8.2 stage 16).

Each area is measured on the ellipsoid and given its layer's rank; the pack
writer (pack_write, moved from spike S2) cuts the shapes into pack tiles.
The manifest lists every source with its licence, attribution and date,
and the attribution record credits each of them (DAT-9, DMT-6).
"""
from __future__ import annotations

from mapdata.pipeline import features
from mapdata.pipeline.build import pack_file_name
from mapdata.stages import antimeridian, pack_write
import numpy as np
import shapely

from mapdata.stages.geodesy import areas_km2


def attribution_text(sources: list[dict]) -> str:
    lines = list(dict.fromkeys(s["attribution"] for s in sources))
    lines += [f"{s['name']}: {s['licence']}, {s['date']}." for s in sources]
    return "\n".join(lines) + "\n"


def keep_ids_unique(records: list[dict], say, renamed: dict | None = None) -> int:
    """Every id in a pack is different. Two layers can take an area from one OSM object, such as an island
    that is also a region (the world build of P3-T1d stopped at its last step on osm:r1814783), so an id
    already used by a feature of another layer gets the ending "#as-" and the layer's id, and one used
    twice in the same layer gets "#2", "#3" and so on. Each change is listed in the log. Done here, at the
    start of the last stage that every feature passes through, so no layer, now or later, can stop a
    build at its end with a feature given twice. Returns how many ids were changed; each change is also put in
    renamed, by the old id and the layer, if it is given."""
    seen: set[str] = {r["id"] for r in records}
    first: dict[str, str] = {}
    changed = 0
    for r in records:
        fid, layer = r["id"], r["layer"]
        if fid not in first:
            first[fid] = layer
            continue
        new = f"{fid}#as-{layer}" if first[fid] != layer else f"{fid}#2"
        n = 2
        while new in seen:
            n += 1
            new = f"{fid}#as-{layer}#{n}" if first[fid] != layer else f"{fid}#{n}"
        say(f"The id {fid} is used by the layer {first[fid]} and again by the layer {layer}, "
            f"for {r.get('name', 'a feature')}. The second is written as {new}.")
        r["id"] = new
        if renamed is not None:
            renamed[(fid, layer)] = new
        seen.add(new)
        changed += 1
    return changed


def resolve_within(records: list[dict], renamed: dict) -> None:
    """A place's areas it is in (P3-T1j), held by the stages as layer and id, made plain ids: the id the area is
    written with, after keep_ids_unique."""
    for r in records:
        if "within" in r:
            r["within"] = [renamed.get((w["id"], w["layer"]), w["id"]) for w in r["within"]]


# Fields the stages keep for the build only: Wikidata's kinds of each feature, which name the tiers (DP181),
# whether its Wikidata link was matched by name, which the wikidata stage's log lists (P3-T2a), and how many
# Wikimedia sites have it, which counts towards its importance in search (P3-T8a).
BUILD_ONLY = ("kinds", "wikidata_matched", "sitelinks")


# Tiers (P3-T17, DP165) ------------------------------------------------------------------------------

TIERS_RECORD = "tiers.yaml"
# Land the build names itself in the Countries layer has no tier: it is said by its type (P3-T2c).
OWN_TYPES = ("disputed land", "unclaimed land", "condominium", "territory")


def tiers_path():
    from mapdata.paths import CONFIG_DIR

    return CONFIG_DIR / TIERS_RECORD


def load_tiers(path=None) -> dict:
    """The tiers record, mapdata/config/tiers.yaml, checked: every tier it gives is one of its tiers."""
    import yaml

    data = yaml.safe_load((path or tiers_path()).read_text(encoding="utf-8")) or {}
    order = list(data.get("tiers") or [])
    given = list((data.get("layers") or {}).values())
    for entry in (data.get("countries") or {}).values():
        given += [v for k, v in entry.items() if k in ("countries", "regions", "counties")]
    given += [e["tier"] for e in (data.get("areas") or {}).values()]
    unknown = sorted({t for t in given if t not in order})
    if unknown:
        raise ValueError(f"The tiers record gives the tiers {', '.join(unknown)}, which are not in its list of "
                         f"tiers: {', '.join(order)}.")
    return {"tiers": order, "layers": dict(data.get("layers") or {}),
            "countries": dict(data.get("countries") or {}), "areas": dict(data.get("areas") or {}),
            "names": {str(k): names_entry(v) for k, v in (data.get("names") or {}).items()}}


def names_entry(entry) -> dict:
    """A country's tier names (DP181), with its areas named one by one as {area id: name}: the record groups them
    as {name: [area ids]}."""
    from mapdata.stages.tier_names import from_record

    return from_record(entry)


def fingerprint_extra(stage: dict) -> dict:
    """The tiers record is part of what the writing stage reads, so changing it writes the pack again."""
    return {"tiers": tiers_path().read_text(encoding="utf-8")}


def give_tiers(records: list[dict], tiers: dict) -> dict[str, int]:
    """Give each area of the layers in the tiers record its tier (P3-T17): its own from the record's areas, or
    its country's for its layer, or its layer's. A region used as its own county takes its region's tier.
    Returns how many areas have each tier."""
    by_id = {r["id"]: r for r in records}

    def country_of(r):
        for _ in range(4):   # a county's parent is its region, whose parent is its country
            if r is None or r["layer"] == "countries":
                break
            r = by_id.get(r.get("parent"))
        # A country's distant part, such as Hawaii, keeps its country's tiers and their names (DP191).
        return (r.get("sovereign_id") or r["id"]) if r is not None and r["layer"] == "countries" else None

    counts: dict[str, int] = {}
    order = {"countries": 0, "regions": 1, "counties": 2}
    for r in sorted((r for r in records if r["layer"] in tiers["layers"] and r.get("type") not in OWN_TYPES),
                    key=lambda r: order.get(r["layer"], 3)):
        own = tiers["areas"].get(r["id"])
        if own:
            tier = own["tier"]
        elif r.get("type") == "region used as county" and by_id.get(r.get("parent"), {}).get("tier"):
            tier = by_id[r["parent"]]["tier"]
        else:
            country = tiers["countries"].get(country_of(r)) or {}
            tier = country.get(r["layer"]) or tiers["layers"][r["layer"]]
        r["tier"] = tier
        counts[tier] = counts.get(tier, 0) + 1
        # The tier's name in its country, from Wikidata (DP181), such as "state" for Kansas.
        named = tiers.get("names", {}).get(country_of(r)) or {}
        word = (named.get("areas") or {}).get(r["id"]) or (named.get(r["layer"]) if not own else None)
        if word and r.get("type") != "region used as county":
            r["tier_name"] = word
        elif r.get("type") == "region used as county" and by_id.get(r.get("parent"), {}).get("tier_name"):
            r["tier_name"] = by_id[r["parent"]]["tier_name"]
    # A country's distant part takes the tier of the area it is named from, so Hawaii is said as a state of the
    # United States (DP191); the regions and counties are given theirs above, after the countries.
    for r in records:
        named = by_id.get(r.get("named_from")) if r["layer"] == "countries" else None
        if named is None or not named.get("tier"):
            continue
        counts[r["tier"]] -= 1
        r["tier"] = named["tier"]
        counts[r["tier"]] = counts.get(r["tier"], 0) + 1
        r.pop("tier_name", None)
        if named.get("tier_name"):
            r["tier_name"] = named["tier_name"]
    return counts


AREA_BATCH = 200_000   # parts measured together


def _areas_batch(geoms: list) -> list[float]:
    """Each shape's area: its parts measured together, and each shape's added in order, so the sums are the
    same as measuring each shape's parts on their own."""
    geoms = [shapely.from_wkb(g) if isinstance(g, bytes) else g for g in geoms]
    parts, which = shapely.get_parts(np.array(geoms, dtype=object), return_index=True)
    each = areas_km2(parts)
    bounds = np.searchsorted(which, np.arange(len(geoms) + 1))
    return [float(each[bounds[i]:bounds[i + 1]].sum()) for i in range(len(geoms))]


ALONE_POINTS = 50_000   # a shape with more points has its parts measured in jobs of their own


def part_chunks(g):
    """A large shape's parts in chunks to measure: up to about ALONE_POINTS points, each invalid part alone. Gives
    (index of the first part, the parts, whether they are valid, their points)."""
    parts = shapely.get_parts(g)
    valid = shapely.is_valid(parts)
    first, n = 0, 0
    for k in range(len(parts) + 1):
        if k == len(parts) or (k > first and (not valid[k] or not valid[k - 1] or n > ALONE_POINTS)):
            yield first, parts[first:k], bool(valid[first:k].all()), n
            first, n = k, 0
        if k < len(parts):
            n += int(shapely.get_num_coordinates(parts[k]))


def start_slow_areas(geoms: list, executor) -> dict:
    """Start measuring, at once, each invalid part of more than ALONE_POINTS points, which GEOS repairs as it
    measures: the world's Indian Ocean has one, of 575,739 points and 22,037 holes, which takes 12 minutes on
    its own. The areas are needed only for the feature records, at the end, so the other steps go on beside it
    in the other workers. Returns the jobs started, by feature and first part, for feature_areas_km2."""
    if executor is None:
        return {}
    early = {}
    for i, g in enumerate(geoms):
        if shapely.get_num_coordinates(g) > ALONE_POINTS:
            for first, parts, valid, n in part_chunks(g):
                if not valid and n > ALONE_POINTS:
                    early[(i, first)] = executor.submit(_areas_job, ("parts", i, first,
                                                                     [shapely.to_wkb(q) for q in parts]))
    return early


def finish_areas(out: list, pending: dict, early: dict) -> list[float]:
    """The areas of feature_areas_km2, with the parts started early by start_slow_areas added in, each shape's
    parts' areas summed in order."""
    for (i, first), future in early.items():
        _w, _i, _first, areas = future.result()
        pending[i][first] = areas
    for i, pieces in pending.items():
        each = np.concatenate([pieces[k] for k in sorted(pieces)]) if pieces else np.zeros(0)
        out[i] = float(each.sum())
    return out


def feature_areas_km2(geoms: list, executor=None, workers: int = 1, batch: int = AREA_BATCH,
                      early: dict | None = None) -> tuple[list, dict]:
    """Each shape's area on the ellipsoid, in batches of about `batch` parts, in the workers when there is an
    executor. One shape at a time took 49 seconds for the Western Europe trial's 161,000 features (P3-T1k).

    With workers, a shape of more than ALONE_POINTS points has its parts measured in jobs of their own, a few
    parts to a job and each invalid part alone, the largest first; its parts' areas are then added in order, as
    when measured together, so the sums are the same. Parts started early by start_slow_areas are left out: then the areas of the shapes
    they belong to are None, and finish_areas, given the second value returned, completes them. GEOS repairs an invalid polygon as it measures it, which
    is slow: one shape at a time, the world's Indian Ocean took 714 seconds, the South Pacific 194 and the
    South Atlantic 53, of about 1,170 seconds for all the world's features."""
    if executor is not None:   # enough batches to keep every worker busy
        batch = max(1, min(batch, sum(max(1, shapely.get_num_geometries(g)) for g in geoms) // (workers * 4) + 1))
    points = [int(shapely.get_num_coordinates(g)) for g in geoms]
    big = {i for i, n in enumerate(points) if n > ALONE_POINTS} if executor is not None else set()
    spans, start = [], 0
    while start < len(geoms):
        end, n = start, 0
        while end < len(geoms) and end not in big and (n == 0 or n < batch):
            n += max(1, shapely.get_num_geometries(geoms[end]))
            end += 1
        if end > start:
            spans.append((start, end))
        start = max(end, start + 1) if end == start else end
    if executor is None:
        return [a for s, e in spans for a in _areas_batch(geoms[s:e])], {}
    early = early or {}
    from mapdata.stages.pack_write import run_within_budget

    jobs, cost = [], []
    for s, e in spans:
        jobs.append(("shapes", s, e))
        cost.append(sum(points[s:e]))
    for i in sorted(big):
        for first, parts, valid, n in part_chunks(geoms[i]):
            if (i, first) not in early:
                jobs.append(("parts", i, first, parts))
                cost.append(n + (0 if valid else 10 * n))
    order = sorted(range(len(jobs)), key=lambda j: -cost[j])

    def make(job):
        if job[0] == "shapes":
            return ("shapes", job[1], [shapely.to_wkb(g) for g in geoms[job[1]:job[2]]])
        return ("parts", job[1], job[2], [shapely.to_wkb(g) for g in job[3]])

    out: list = [None] * len(geoms)
    part_areas: dict[int, dict[int, np.ndarray]] = {i: {} for i in big}
    for result in run_within_budget(executor, _areas_job, [jobs[j] for j in order], make, [0] * len(jobs), 0,
                                    workers):
        if result[0] == "shapes":
            _w, s, areas = result
            out[s:s + len(areas)] = areas
        else:
            _w, i, first, areas = result
            part_areas[i][first] = areas
    if not early:
        return finish_areas(out, part_areas, {}), {}
    return out, part_areas


def _areas_job(job):
    if job[0] == "shapes":
        _w, s, blobs = job
        return "shapes", s, _areas_batch(blobs)
    _w, i, first, blobs = job
    return "parts", i, first, areas_km2(np.array([shapely.from_wkb(b) for b in blobs], dtype=object))


def held_layers(levels: list[dict], max_zoom_km: dict[str, float | None]) -> dict[int, set[str]]:
    """The layers each drawing level holds. The application draws a zoom from the drawing level with the
    smallest view_km at or above it, and from the exact pack tiles at EXACT_BELOW_KM or closer, so a level
    serves the zooms above the next finer level's view_km. A layer whose zoom range ends at or below that
    can never be seen from the level, and is left out of it: in the world pack, the 98,000 bays and straits
    that are places, visible only to 100 km, were decoded with every map at a wide zoom, which took seconds."""
    from mapcore.render.scene import EXACT_BELOW_KM

    out, below = {}, EXACT_BELOW_KM
    for lv in sorted(levels, key=lambda d: d["view_km"]):
        out[lv["id"]] = {k for k, top in max_zoom_km.items() if top is None or top > below}
        below = lv["view_km"]
    return out


def _simplify_job(job) -> tuple[int, str, list]:
    """One layer at one drawing level, simplified in a worker: (level id, layer, WKB or None for each shape)."""
    from mapdata.stages import drawing_levels

    level_id, layer, blobs, tolerance_m, min_km2, together = job
    shapes = drawing_levels.simplify_layer([shapely.from_wkb(b) for b in blobs], tolerance_m, min_km2,
                                           together=together)
    return level_id, layer, [None if g is None else shapely.to_wkb(g) for g in shapes]


def drawing_shapes(records, geoms, levels, say, apart=frozenset(), held=None, executor=None,
                   workers: int = 1) -> dict[int, list]:
    """The simplified shape of every feature at each drawing level, each layer simplified as one coverage,
    except the layers in apart, whose areas are simplified one by one. A layer a level does not hold, by
    held, has no shapes there. With an executor, each layer at each level is a job for the workers, the
    largest first: one after another, they took 54 seconds of the Western Europe trial's writing (P3-T1k)."""
    import time

    from mapdata.stages import drawing_levels

    t = time.perf_counter()
    order = list(dict.fromkeys(r["layer"] for r in records))
    members = {layer: [i for i, r in enumerate(records) if r["layer"] == layer] for layer in order}
    out = {lv["id"]: [None] * len(geoms) for lv in levels}
    jobs = [(lv, layer) for lv in levels for layer in order if held is None or layer in held[lv["id"]]]

    def place(level_id, layer, simplified):
        for i, g in zip(members[layer], simplified):
            out[level_id][i] = geoms[i] if records[i].get("exact") else g   # exact: every point kept (P2-T10b)

    if executor is None:
        for lv, layer in jobs:
            place(lv["id"], layer, drawing_levels.simplify_layer([geoms[i] for i in members[layer]],
                                                                 lv["tolerance_m"], lv["min_km2"],
                                                                 together=layer not in apart))
    else:
        from mapdata.stages.pack_write import run_within_budget

        size = {layer: sum(int(shapely.get_num_coordinates(geoms[i])) for i in members[layer]) for layer in order}
        jobs.sort(key=lambda j: -size[j[1]])

        def make(job):   # each job's copy of its shapes is made only when it starts, to save memory
            lv, layer = job
            return (lv["id"], layer, [shapely.to_wkb(geoms[i]) for i in members[layer]], lv["tolerance_m"],
                    lv["min_km2"], layer not in apart)

        # Simplifying a layer takes several times its shapes' memory, so the layers simplified at once hold no
        # more points together than the largest layer: the world's counties are simplified alone, as before.
        budget = max(size.values(), default=0)
        for level_id, layer, simplified in run_within_budget(executor, _simplify_job, jobs, make,
                                                             [size[j[1]] for j in jobs], budget, workers):
            place(level_id, layer, [None if b is None else shapely.from_wkb(b) for b in simplified])
    for lv in levels:
        shapes = out[lv["id"]]
        per_layer = ", ".join(
            f"{layer} {drawing_levels.points([shapes[i] for i in members[layer]]):,}" for layer in order)
        say(f"Drawing level {lv['id']}: simplified to {lv['tolerance_m']:g} metres, parts under {lv['min_km2']:g} "
            f"km2 left out: {drawing_levels.points(geoms):,} points down to {drawing_levels.points(shapes):,} "
            f"({per_layer}).")
    say(f"Simplified the {len(levels)} drawing levels in {time.perf_counter() - t:.0f} seconds.")
    return out


def run(ctx) -> None:
    records, geoms = features.load(ctx.previous)
    from mapdata.stages import relationships as relmod

    rel = relmod.load(ctx.previous)   # from the relationships stage, by each feature's index (P3-T3)
    renamed: dict = {}
    changed = keep_ids_unique(records, ctx.progress.log, renamed)
    resolve_within(records, renamed)
    if changed:
        ctx.progress.line(f"Ids used twice, written with an ending so every id is different: {changed}. "
                          "The log lists them.")
    tiers = load_tiers()
    counts = give_tiers(records, tiers)
    if counts:
        ctx.progress.line("Tiers given, from the tiers record: " + "; ".join(
            f"{t.replace('_', ' ')}, {counts[t]:,}" for t in tiers["tiers"] if t in counts) + ".")
    # The search index (P3-T8a) is made with the feature records; the sites are kept for it first.
    search = {"sites": {r["id"]: int(r["sitelinks"]) for r in records if r.get("sitelinks")},
              "settings": ctx.settings.get("search") or {}}
    for r in records:   # what earlier stages kept for the build only, not for the pack
        for key in BUILD_ONLY:
            r.pop(key, None)
    used = {r.pop("source_key") for r in records if "source_key" in r} or set(ctx.pack.sources)
    # Wikidata's facts are added to features made from other sources, so it is credited when any feature has them.
    if any(r.get("facts") for r in records):
        used |= {st["source"] for st in ctx.pack.stages if st["stage"] == "wikidata" and st.get("source")}
    sources = [{"name": s.name, "licence": s.licence, "attribution": s.attribution,
                "date": s.data_date(ctx.source_paths[k])}
               for k, s in ctx.pack.sources.items() if k in used]
    # Each part is measured about its own centre and the areas added: no need to move parts across the 180
    # degree line first, which took hours for an ocean of 400,000 parts.
    from mapdata import parallel

    with parallel.pool(ctx.workers) as executor:
        pool = None if ctx.workers == 1 else executor
        write_with(ctx, records, geoms, sources, pool, tiers["tiers"],
                   relmod.by_id(rel, [r["id"] for r in records]) if rel else None, search)


def write_with(ctx, records, geoms, sources, executor, tiers: list[str] | None = None,
               relationships: dict | None = None, search: dict | None = None) -> None:
    """The rest of the writing stage, with the pool of workers open for all of it (P3-T1k)."""
    import time

    t = time.perf_counter()
    early = start_slow_areas(geoms, executor)
    if early:
        ctx.progress.line(f"Measuring {len(early)} large invalid parts of features on the ellipsoid in the "
                          "background, as GEOS repairs them as it measures them, which is slow.")
    areas, pending = feature_areas_km2(geoms, executor, ctx.workers, early=early)
    for r in records:
        r["rank"] = ctx.pack.layers[r["layer"]].rank
    ctx.progress.line(f"Measured {len(records):,} features on the ellipsoid in {time.perf_counter() - t:.0f} seconds"
                      + (", but for the parts in the background." if early else "."))

    def set_areas():
        waited = time.perf_counter()
        for r, km2 in zip(records, finish_areas(areas, pending, early) if early else areas):
            r["area_km2"] = round(km2, 3)
        if early:
            ctx.progress.line(f"The parts measured in the background were ready after waiting "
                              f"{time.perf_counter() - waited:.0f} seconds.")

    data = ctx.pack.data
    levels = [{"id": n, **lv} for n, lv in enumerate(ctx.settings.get("drawing_levels") or [])]
    # A layer that is not painted, such as the continents or the mountain ranges, may have areas that overlap,
    # so its areas are simplified one by one, not as a coverage (P3-T1e).
    apart = frozenset(k for k, layer in ctx.pack.layers.items() if dict(layer.shown).get("fill") == "none")
    present = list(dict.fromkeys(r["layer"] for r in records))
    tops = {k: (None if dict(ctx.pack.layers[k].shown).get("max_zoom_m") is None
                else dict(ctx.pack.layers[k].shown)["max_zoom_m"] / 1000.0) for k in present}
    held = held_layers(levels, tops)
    for lv in levels:   # in the manifest, so the application knows to look elsewhere for a layer left out
        lv["layers"] = [k for k in present if k in held[lv["id"]]]
        left = [k for k in present if k not in held[lv["id"]]]
        if left:
            ctx.progress.line(f"Drawing level {lv['id']} leaves out {', '.join(left)}, as they cannot be seen "
                              f"at the zooms it serves.")
    drawing_geoms = (drawing_shapes(records, geoms, levels, ctx.progress.line, apart, held, executor, ctx.workers)
                     if levels else None)
    manifest = {"name": data["name"], "title": data["title"], "version": str(data["version"]),
                "coverage": data["coverage"], "app_versions": data["app_versions"],
                "drawing_levels": levels, "sources": sources}
    if tiers:   # the order of the tiers, highest first, for the order of the areas at a point (P3-T17)
        manifest["tiers"] = list(tiers)
    layers = [layer.definition() for k, layer in ctx.pack.layers.items()
              if any(r["layer"] == k for r in records)]
    path = ctx.folder / pack_file_name(data["name"])
    from mapcore.packs.pack import checksum_path

    ctx.claim(path)
    ctx.claim(checksum_path(path))
    pack_write.write(path, manifest, records, geoms, ctx.workers, say=ctx.progress.line, layers=layers,
                     attribution=attribution_text(sources), drawing_geoms=drawing_geoms, executor=executor,
                     before_records=set_areas, relationships=relationships, search=search)
