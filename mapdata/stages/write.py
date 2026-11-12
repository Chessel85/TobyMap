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
import shapely

from mapdata.stages.geodesy import areas_km2


def attribution_text(sources: list[dict]) -> str:
    lines = list(dict.fromkeys(s["attribution"] for s in sources))
    lines += [f"{s['name']}: {s['licence']}, {s['date']}." for s in sources]
    return "\n".join(lines) + "\n"


def keep_ids_unique(records: list[dict], say) -> int:
    """Every id in a pack is different. Two layers can take an area from one OSM object, such as an island
    that is also a region (the world build of P3-T1d stopped at its last step on osm:r1814783), so an id
    already used by a feature of another layer gets the ending "#as-" and the layer's id, and one used
    twice in the same layer gets "#2", "#3" and so on. Each change is listed in the log. Done here, at the
    start of the last stage that every feature passes through, so no layer, now or later, can stop a
    build at its end with a feature given twice. Returns how many ids were changed."""
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
        seen.add(new)
        changed += 1
    return changed


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


def drawing_shapes(records, geoms, levels, say, apart=frozenset(), held=None) -> dict[int, list]:
    """The simplified shape of every feature at each drawing level, each layer simplified as one coverage,
    except the layers in apart, whose areas are simplified one by one. A layer a level does not hold, by
    held, has no shapes there."""
    import time

    from mapdata.stages import drawing_levels

    out = {}
    for lv in levels:
        t = time.perf_counter()
        shapes = [None] * len(geoms)
        for layer in dict.fromkeys(r["layer"] for r in records):
            if held is not None and layer not in held[lv["id"]]:
                continue
            idx = [i for i, r in enumerate(records) if r["layer"] == layer]
            for i, g in zip(idx, drawing_levels.simplify_layer([geoms[i] for i in idx], lv["tolerance_m"],
                                                               lv["min_km2"], together=layer not in apart)):
                shapes[i] = geoms[i] if records[i].get("exact") else g   # exact: every point kept (P2-T10b)
        out[lv["id"]] = shapes
        per_layer = ", ".join(
            f"{layer} {drawing_levels.points([g for g, r in zip(shapes, records) if r['layer'] == layer]):,}"
            for layer in dict.fromkeys(r["layer"] for r in records))
        say(f"Drawing level {lv['id']}: simplified to {lv['tolerance_m']:g} metres, parts under {lv['min_km2']:g} "
            f"km2 left out: {drawing_levels.points(geoms):,} points down to {drawing_levels.points(shapes):,} "
            f"({per_layer}), in {time.perf_counter() - t:.0f} seconds.")
    return out


def run(ctx) -> None:
    records, geoms = features.load(ctx.previous)
    changed = keep_ids_unique(records, ctx.progress.log)
    if changed:
        ctx.progress.line(f"Ids used twice, written with an ending so every id is different: {changed}. "
                          "The log lists them.")
    used = {r.pop("source_key") for r in records if "source_key" in r} or set(ctx.pack.sources)
    sources = [{"name": s.name, "licence": s.licence, "attribution": s.attribution,
                "date": s.data_date(ctx.source_paths[k])}
               for k, s in ctx.pack.sources.items() if k in used]
    for r, g in zip(records, geoms):
        r["rank"] = ctx.pack.layers[r["layer"]].rank
        # Each part is measured about its own centre and the areas added: no need to move parts across the 180
        # degree line first, which took hours for an ocean of 400,000 parts.
        r["area_km2"] = round(float(areas_km2(shapely.get_parts(g)).sum()), 3)
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
    drawing_geoms = drawing_shapes(records, geoms, levels, ctx.progress.line, apart, held) if levels else None
    manifest = {"name": data["name"], "title": data["title"], "version": str(data["version"]),
                "coverage": data["coverage"], "app_versions": data["app_versions"],
                "drawing_levels": levels, "sources": sources}
    layers = [layer.definition() for k, layer in ctx.pack.layers.items()
              if any(r["layer"] == k for r in records)]
    path = ctx.folder / pack_file_name(data["name"])
    from mapcore.packs.pack import checksum_path

    ctx.claim(path)
    ctx.claim(checksum_path(path))
    pack_write.write(path, manifest, records, geoms, ctx.workers, say=ctx.progress.line, layers=layers,
                     attribution=attribution_text(sources), drawing_geoms=drawing_geoms)
