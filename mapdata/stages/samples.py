"""Stage "samples": read small shape files kept in the repository, for the test pack (architecture 11.1).

Each sample is a GeoJSON file. Each feature's properties give its id, name,
layer and type, and may give local_name, parent, sovereign and replaces.
A sample may also give "box", a list of rectangles [west, south, east,
north]: the area it covers in more detail than the samples before it.

The samples are read in the order the pack's settings list them, least
detailed first. Each sample with a box cuts its box out of the areas read
before it, in the layers it has itself, so the more detailed sample wins
there, as the most detailed pack will (AD-14). An area with the same id as
one read before, or that names it in "replaces", takes over what is left of
that area outside the box, so it stays one area: for example the USA from
Natural Earth, with Niagara Falls from OSM.

Shapes that are not valid are repaired, and each repair is logged. A feature in a line or
point layer (P2-T10c) keeps its lines or points, and is never cut by a box.
"""
from __future__ import annotations

import json

import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages.clip import polygonal

NEEDED = ("id", "name", "layer", "type")
# population: a town's, from OpenStreetMap, as the osm-places stage keeps it (P3-T1j), for search's importance.
KEPT = ("id", "name", "local_name", "layer", "type", "parent", "sovereign", "population")


def as_lines_or_points(geom, shape: str, props: dict, filename: str):
    """A line layer's feature as a multi-part line, a point layer's as a multi-part point (P2-T10c)."""
    kinds = {"line": (("LineString", "MultiLineString"), shapely.MultiLineString),
             "point": (("Point", "MultiPoint"), shapely.MultiPoint)}[shape]
    if geom.geom_type not in kinds[0] or geom.is_empty:
        raise BuildStopped(f"The feature {props['id']}, {props['name']}, in the sample {filename} is in a {shape} "
                           f"layer but its shape is {geom.geom_type}. Use {' or '.join(kinds[0])}.")
    return geom if geom.geom_type == kinds[0][1] else kinds[1]([geom])


def read_sample(path, layers: dict, say) -> tuple[list[dict], list, object | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    box = None
    if data.get("box"):
        box = shapely.union_all([shapely.box(*b) for b in data["box"]])
    records, geoms = [], []
    for n, f in enumerate(data.get("features") or [], 1):
        props = f.get("properties") or {}
        missing = [k for k in NEEDED if not props.get(k)]
        if missing:
            raise BuildStopped(f"Feature {n} in the sample {path.name} ({props.get('id') or 'no id'}) has no "
                               f"{', '.join(missing)}. Add them to the sample, then build again.")
        if props["layer"] not in layers:
            raise BuildStopped(f"The feature {props['id']}, {props['name']}, in the sample {path.name}, is in the "
                               f"layer {props['layer']}, which the pack's layer groups do not define.")
        geom = shapely.from_geojson(json.dumps(f["geometry"]))
        shape = getattr(layers[props["layer"]], "geometry", "area")
        if shape in ("line", "point"):   # a river or a station: kept as it is, not made into an area
            geom = as_lines_or_points(geom, shape, props, path.name)
            records.append({"replaces": [], **{k: props[k] for k in KEPT if props.get(k)}})
            geoms.append(geom)
            continue
        if not geom.is_valid:
            reason = shapely.is_valid_reason(geom)
            geom = polygonal(shapely.make_valid(geom))
            say(f"Repaired {props['name']} ({props['id']}) in {path.name}: {reason}.")
        geom = polygonal(geom)
        if geom is None or geom.is_empty:
            say(f"Left out {props['name']} ({props['id']}) in {path.name}: it has no area.")
            continue
        record = {k: props[k] for k in KEPT if props.get(k)}
        record["replaces"] = list(props.get("replaces") or [])
        records.append(record)
        geoms.append(geom)
    return records, geoms, box


def combine(samples: list[tuple[list[dict], list, object | None]]) -> tuple[list[dict], list]:
    """Join the samples, the later and more detailed winning inside their boxes."""
    held: dict[str, tuple[dict, object]] = {}
    for records, geoms, box in samples:
        if box is not None:
            layers = {r["layer"] for r in records}
            for key, (r, g) in list(held.items()):
                if r["layer"] in layers and g.geom_type in ("Polygon", "MultiPolygon"):
                    left = polygonal(shapely.difference(g, box))
                    if left is None or left.is_empty:
                        del held[key]
                    else:
                        held[key] = (r, left)
        for r, g in zip(records, geoms):
            parts = [g]
            for old in [r["id"], *r["replaces"]]:
                if old in held:
                    parts.append(held.pop(old)[1])
            r = {k: v for k, v in r.items() if k != "replaces"}
            held[r["id"]] = (r, polygonal(shapely.union_all(parts)) if len(parts) > 1 and g.geom_type in ("Polygon", "MultiPolygon") else g)
    ids = sorted(held)
    return [held[i][0] for i in ids], [held[i][1] for i in ids]


def run(ctx) -> None:
    samples = []
    for item in ctx.settings["samples"]:
        source, path = ctx.source(item["source"])
        if item.get("file"):
            path = path / item["file"]
        if not path.is_file():
            raise BuildStopped(f"The sample {path} for the source {source.key} is missing from the repository.")
        records, geoms, box = read_sample(path, ctx.pack.layers, ctx.progress.log)
        for r in records:
            r["source_key"] = source.key
        samples.append((records, geoms, box))
        ctx.progress.line(f"Read the sample {path.name}: {len(records)} areas.")
    records, geoms = combine(samples)
    features.save(ctx.folder, records, geoms, ctx.claim)
    ctx.progress.line(f"{len(records)} areas from {len(samples)} samples.")
