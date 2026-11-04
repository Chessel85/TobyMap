"""Stage "write": write the pack in format 2, with its manifest, attribution and checksum (architecture 8.2 stage 16).

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


def drawing_shapes(records, geoms, levels, say) -> dict[int, list]:
    """The simplified shape of every feature at each drawing level, each layer simplified as one coverage."""
    import time

    from mapdata.stages import drawing_levels

    out = {}
    for lv in levels:
        t = time.perf_counter()
        shapes = [None] * len(geoms)
        for layer in dict.fromkeys(r["layer"] for r in records):
            idx = [i for i, r in enumerate(records) if r["layer"] == layer]
            for i, g in zip(idx, drawing_levels.simplify_layer([geoms[i] for i in idx], lv["tolerance_m"],
                                                               lv["min_km2"])):
                shapes[i] = g
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
    drawing_geoms = drawing_shapes(records, geoms, levels, ctx.progress.line) if levels else None
    manifest = {"name": data["name"], "title": data["title"], "version": str(data["version"]),
                "coverage": data["coverage"], "app_versions": data["app_versions"],
                "drawing_levels": levels, "sources": sources}
    layers = [{"id": k, "name": layer.name} for k, layer in ctx.pack.layers.items()
              if any(r["layer"] == k for r in records)]
    path = ctx.folder / pack_file_name(data["name"])
    from mapcore.packs.pack import checksum_path

    ctx.claim(path)
    ctx.claim(checksum_path(path))
    pack_write.write(path, manifest, records, geoms, ctx.workers, say=ctx.progress.line, layers=layers,
                     attribution=attribution_text(sources), drawing_geoms=drawing_geoms)
