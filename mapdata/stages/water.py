"""Stage "water": take the land out of the water layers, such as the oceans (P1-T4, data sources 4).

Every area in a layer of kind water loses whatever the land layer named in
the settings ("land_layer", Countries by default) covers, so a point on land
is never also in the sea. This works on the whole of each shape at once,
which suits the test pack; the base pack lite will do it pack tile by pack
tile (architecture 8.2, spike S2's lessons).
"""
from __future__ import annotations

import shapely

from mapdata.pipeline import features
from mapdata.stages.clip import polygonal


def run(ctx) -> None:
    records, geoms = features.load(ctx.previous)
    land_layer = ctx.settings.get("land_layer", "countries")
    water = {k for k, layer in ctx.pack.layers.items() if layer.kind == "water"}
    land = shapely.union_all([g for r, g in zip(records, geoms) if r["layer"] == land_layer])
    shapely.prepare(land)
    out_r, out_g = [], []
    for r, g in zip(records, geoms):
        if r["layer"] in water:
            g = polygonal(shapely.difference(g, land))
            if g is None or g.is_empty:
                ctx.progress.log(f"Left out {r['name']} ({r['id']}): it is all under land.")
                continue
        out_r.append(r)
        out_g.append(g)
    features.save(ctx.folder, out_r, out_g, ctx.claim)
    ctx.progress.line(f"The land is taken out of {sum(r['layer'] in water for r in out_r)} water areas.")
