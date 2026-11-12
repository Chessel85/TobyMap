"""Stage "osm-layer": named areas from the planet file, into a layer of their own (P3-T1h, DAT-1, DP169).

For P3-T1h, the lakes: OpenStreetMap's named lakes, reservoirs and lagoons of
at least min_km2, each one feature, so "where am I" on Lake Geneva says the
lake, on either side of the border. Each query in the settings gives the OSM
features to read and the type their features get. An area's outline is
simplified to tolerance_m, the base detail of the countries, as the base pack
needs no more.

With check in the settings, the layer is checked against another source for
anything large it is missing: for the lakes, HydroLAKES. Each HydroLAKES lake
of at least check_km2 whose point is not within check_within_km of a lake read
is listed in the log, as a lake OSM may have under another tag, or without a
name.

GeoDesk gives its memory back only when the process ends (spike S2), so the
reading is done in its own short-lived process, as the osm-areas stage does.
The features of the stage before are kept, and the new ones added after them.

Settings:

* source: the planet file's source key, planet.
* layer: the layer, such as lakes.
* queries: a list, each with query (GeoDesk's query language, such as
  "a[natural=water][water=lake][name]") and type (such as lake).
* min_km2: areas smaller than this are left out.
* tolerance_m: how far a simplified outline may move, in metres.
* check: optional, the key of a HydroLAKES source; with check_km2 and
  check_within_km.
* same_as: optional, a list of layers whose names the new features must not
  repeat: the Caspian Sea is a lake in OpenStreetMap, but already in the
  Oceans and seas layer, so it is left out of the lakes.
* box: optional, [west, south, east, north].
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import shapely
import shapely.ops

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages.osm_places import leave_out_repeats, osm_id, place_record

READ_VERSION = "osm-layer-1"
REQUEST = "request.json"
READ_FOLDER = "read"
METRES_PER_DEGREE = 111_320.0


def polygonal(g):
    g = shapely.make_valid(g)
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    parts = [q for p in shapely.get_parts(g) for q in shapely.get_parts(p) if q.geom_type == "Polygon"]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)


def read(gol: Path, request: dict, say=print) -> tuple[list[dict], list]:
    """Every area the queries find of at least min_km2, as records and simplified shapes, in id order. Runs in
    the short-lived process."""
    import geodesk

    world = geodesk.Features(str(gol))
    box = request.get("box")
    gbox = geodesk.Box(west=box[0], south=box[1], east=box[2], north=box[3]) if box else None
    min_m2 = float(request.get("min_km2", 0)) * 1e6
    tol = float(request.get("tolerance_m", 0)) / METRES_PER_DEGREE
    found: dict[str, tuple[dict, object]] = {}
    for q in request["queries"]:
        t = time.perf_counter()
        sel = world(q["query"])
        if gbox is not None:
            sel = sel(gbox)
        n = small = 0
        for f in sel:
            fid = osm_id(f)
            if fid in found:
                continue
            if f.area < min_m2:   # GeoDesk's area is in square metres, on the ellipsoid
                small += 1
                continue
            tags = {k: str(f.tags[k] or "") for k in ("name", "name:en", "wikidata")}
            rec = place_record(fid, tags, request["layer"], q["type"])
            if rec is None:
                continue
            g = geodesk.from_mercator(f.shape)
            if tol:
                g = shapely.simplify(g, tol, preserve_topology=False)
            g = polygonal(g)
            if g is None or g.is_empty:
                continue
            rec["area_m2_osm"] = round(float(f.area))
            found[fid] = (rec, shapely.set_precision(g, 1e-7))
            n += 1
        say(f"Read {n:,} areas for {q['query']}, and left out {small:,} under {request.get('min_km2', 0)} km2, in "
            f"{time.perf_counter() - t:.0f} seconds.")
    ids = sorted(found)
    return [found[i][0] for i in ids], [found[i][1] for i in ids]


def main(folder: Path) -> int:
    """The entry point of the short-lived process: "mapdata read-in-process osm_layer <folder>"."""
    request = json.loads((folder / REQUEST).read_text(encoding="utf-8"))
    lines: list[str] = []

    def say(text):
        lines.append(text)
        print(text, flush=True)

    records, geoms = read(Path(request["gol"]), request, say)
    out = folder / READ_FOLDER
    out.mkdir(exist_ok=True)
    features.save(out, records, geoms)
    (out / "read log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


def hydrolakes(path: Path, box, min_km2: float) -> list[dict]:
    """The HydroLAKES lakes of at least min_km2, with their name, area and point (its pour point, on its edge)."""
    import pyogrio

    vsi = f"/vsizip/{path.as_posix()}/HydroLAKES_points_v10_shp/HydroLAKES_points_v10.shp"
    where = f"Lake_area >= {float(min_km2)}"
    meta, _fids, wkb, fields = pyogrio.raw.read(vsi, columns=["Hylak_id", "Lake_name", "Lake_area"], where=where,
                                                bbox=tuple(box) if box else None, return_fids=True)
    col = {n: fields[i] for i, n in enumerate(meta["fields"])}
    pts = shapely.from_wkb(wkb)
    return [{"id": int(col["Hylak_id"][i]), "name": col["Lake_name"][i] or "", "km2": float(col["Lake_area"][i]),
             "point": pts[i]} for i in range(len(pts))]


NAME_WITHIN_KM = 30   # a lake of the layer this near with the same name is the same lake; farther for a large lake


def plain(text: str) -> str:
    """A name without accents or case, so HydroLAKES's "Vattern" is OSM's "Vättern"."""
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", str(text or "")) if not unicodedata.combining(c)).lower()


def missing(lakes: list[dict], geoms: list, within_km: float, records: list[dict] | None = None) -> list[dict]:
    """The lakes with no shape within within_km of their point, and none with their name within NAME_WITHIN_KM.
    HydroLAKES's point is where the lake flows out, which can be some kilometres down its river. Distances
    are measured in km, east and west at the lake's latitude."""
    if not lakes or not geoms:
        return list(lakes)
    import math

    tree = shapely.STRtree(geoms)
    names = [{plain(r.get(k)) for k in ("name", "local_name") if r.get(k)} for r in (records or [{}] * len(geoms))]
    out = []
    for lk in lakes:
        p = lk["point"]
        cos = max(math.cos(math.radians(p.y)), 0.05)
        found = False
        # A large lake's outlet can be far down its river: Great Slave Lake's is 60 km from its shore.
        name_km = max(NAME_WITHIN_KM, 1.5 * math.sqrt(lk["km2"]))
        for km, by_name in ((within_km, False), (name_km, True)):
            if by_name and not lk["name"]:
                continue
            reach = km * 1000 / METRES_PER_DEGREE
            box = shapely.box(p.x - reach / cos, p.y - reach, p.x + reach / cos, p.y + reach)
            for i in tree.query(box).tolist():
                g = geoms[i]
                q = shapely.ops.nearest_points(g, p)[0]
                d_km = math.hypot((q.x - p.x) * cos, q.y - p.y) * METRES_PER_DEGREE / 1000
                if d_km <= km and (not by_name or any(plain(lk["name"]) in n for n in names[i])):
                    found = True
                    break
            if found:
                break
        if not found:
            out.append(lk)
    return out


def run(ctx) -> None:
    s = ctx.settings
    layer = s.get("layer")
    if layer not in ctx.pack.layers:
        raise BuildStopped(f"The osm-layer stage writes to the layer {layer}, which the pack's layer groups do not "
                           "define. Add the layer, or correct the stage's settings.")
    if not s.get("queries"):
        raise BuildStopped("The osm-layer stage needs queries, each with query and type.")
    _source, gol = ctx.source(s.get("source", "planet"))
    request = {"gol": str(gol), "queries": s["queries"], "layer": layer, "box": s.get("box"),
               "min_km2": s.get("min_km2", 0), "tolerance_m": s.get("tolerance_m", 0), "version": READ_VERSION}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(request, indent=1), encoding="utf-8", newline="\n")
    out = ctx.folder / READ_FOLDER
    for name in ("features.json", "shapes.wkb", "read log.txt"):
        ctx.claim(out / name)
    ctx.progress.line(f"Reading the layer {layer} from the planet file {gol.name} in a separate process, which "
                      "ends when it has finished.")
    done = subprocess.run([sys.executable, "-m", "mapdata", "--data", str(ctx.folders.root), "read-in-process",
                           "osm_layer", str(ctx.folder)], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    for line in (done.stdout or "").splitlines():
        ctx.progress.line(line)
    if done.returncode != 0 or not (out / "features.json").is_file():
        raise BuildStopped(f"Reading the layer {layer} from the planet file failed. The end of its output was: "
                           + " ".join((done.stderr or done.stdout or "").splitlines()[-5:]))
    n_records, n_geoms = features.load(out)
    for r in n_records:
        r.pop("area_m2_osm", None)
    left: list[str] = []
    if s.get("same_as"):
        layers = set(s["same_as"]) if isinstance(s["same_as"], list) else {s["same_as"]}
        before, _g = features.load_layers(ctx.previous, layers)
        names = {v for r in before for v in (r.get("name"), r.get("local_name")) if v}
        n_records, n_geoms, left = leave_out_repeats(n_records, n_geoms, names)
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(ctx.previous / name, ctx.claim(ctx.folder / name))
    features.append(ctx.folder, n_records, [shapely.to_wkb(g) for g in n_geoms])
    for name in left:
        ctx.progress.line(f"Left out of the layer {layer}, as the layers {', '.join(s['same_as'])} have it: {name}.")
    kinds: dict[str, int] = {}
    for r in n_records:
        kinds[r["type"]] = kinds.get(r["type"], 0) + 1
    ctx.progress.line(f"The layer {layer}: {len(n_records):,} areas: "
                      + ", ".join(f"{n:,} of type {k}" for k, n in sorted(kinds.items())) + ".")
    if s.get("check"):
        source, path = ctx.source(s["check"])
        check_km2 = float(s.get("check_km2", 100))
        lakes = hydrolakes(path, s.get("box"), check_km2)
        gone = missing(lakes, n_geoms, float(s.get("check_within_km", 2)), n_records)
        ctx.progress.line(f"Checked against {source.name}: {len(lakes):,} lakes of {check_km2:g} km2 or more, of "
                          f"which {len(gone)} have no lake of the layer within {s.get('check_within_km', 2)} km. "
                          "The log lists them.")
        for lk in sorted(gone, key=lambda k: -k["km2"]):
            p = lk["point"]
            ctx.progress.log(f"Not in the layer {layer}: {lk['name'] or 'a lake with no name'} in HydroLAKES "
                             f"(number {lk['id']}), {lk['km2']:,.0f} km2, at {p.y:.4f} north, {p.x:.4f} east.")
