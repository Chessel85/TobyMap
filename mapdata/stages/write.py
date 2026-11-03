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
from mapdata.stages.geodesy import area_km2


def attribution_text(sources: list[dict]) -> str:
    lines = list(dict.fromkeys(s["attribution"] for s in sources))
    lines += [f"{s['name']}: {s['licence']}, {s['date']}." for s in sources]
    return "\n".join(lines) + "\n"


def run(ctx) -> None:
    records, geoms = features.load(ctx.previous)
    used = {r.pop("source_key") for r in records if "source_key" in r} or set(ctx.pack.sources)
    sources = [{"name": s.name, "licence": s.licence, "attribution": s.attribution,
                "date": s.data_date(ctx.source_paths[k])}
               for k, s in ctx.pack.sources.items() if k in used]
    for r, g in zip(records, geoms):
        r["rank"] = ctx.pack.layers[r["layer"]].rank
        r["area_km2"] = round(area_km2(antimeridian.shifted(g)), 3)
    data = ctx.pack.data
    manifest = {"name": data["name"], "title": data["title"], "version": str(data["version"]),
                "coverage": data["coverage"], "app_versions": data["app_versions"],
                "drawing_levels": [], "sources": sources}
    layers = [{"id": k, "name": layer.name} for k, layer in ctx.pack.layers.items()
              if any(r["layer"] == k for r in records)]
    path = ctx.folder / pack_file_name(data["name"])
    from mapcore.packs.pack import checksum_path

    ctx.claim(path)
    ctx.claim(checksum_path(path))
    pack_write.write(path, manifest, records, geoms, ctx.workers, say=ctx.progress.line, layers=layers,
                     attribution=attribution_text(sources))
