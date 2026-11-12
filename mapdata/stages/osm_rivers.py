"""Stage "osm-rivers": whole rivers from the planet file's river ways (P3-T1g, DAT-1, DP169).

OpenStreetMap maps a river as many ways, each drawn in the direction the water
flows, and most large rivers also as a waterway relation that lists its ways.
The stage joins them into whole rivers:

* Each waterway relation of type river with a Wikidata link is a river, made
  of all its ways.
* Each river way with a Wikidata link, and not already in such a river, joins
  the river with that Wikidata link, or makes it.
* A river's ways are joined end to end where they meet, keeping the direction
  of flow, so the line runs from source to mouth for Phase 5. A river with
  branches, such as a delta, is one feature with several lines.
* Rivers shorter than min_km, measured along all their lines, are left out
  (DP169: 50 km).

The outlines are simplified to tolerance_m. With check in the settings, the
rivers are checked against Natural Earth's rivers: every Natural Earth river of
check_km or more, measured inside the box, should have a river of the layer
with its Wikidata link or its name, or one within check_within_km of its middle.
Those that do not are listed in the log.

GeoDesk gives its memory back only when the process ends (spike S2), so the
reading is done in its own short-lived process. The features of the stage
before are kept, and the rivers added after them.

Settings: source (planet), layer (rivers), min_km, tolerance_m, box, and check
(the key of the Natural Earth rivers source), check_km, check_within_km.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped

READ_VERSION = "osm-rivers-1"
REQUEST = "request.json"
READ_FOLDER = "read"
METRES_PER_DEGREE = 111_320.0
EARTH_R_KM = 6371.0088
RIVER_WAYS = "w[waterway=river]"
RIVER_RELATIONS = "r[type=waterway][waterway=river]"


def length_km(g) -> float:
    """A line's length along the Earth, in km, by the great circle between each pair of points."""
    if g is None or g.is_empty:
        return 0.0
    total = 0.0
    for part in shapely.get_parts(g):
        xy = np.radians(shapely.get_coordinates(part))
        if len(xy) < 2:
            continue
        lon, lat = xy[:, 0], xy[:, 1]
        a = (np.sin(np.diff(lat) / 2) ** 2
             + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(np.diff(lon) / 2) ** 2)
        total += float((2 * EARTH_R_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))).sum())
    return total


def join_lines(lines: list) -> object:
    """The ways of one river joined end to end where they meet, each kept in the direction it is drawn, which
    in OpenStreetMap is the direction of flow. One LineString, or a MultiLineString for a river with branches."""
    flat = shapely.get_parts(shapely.get_parts(np.array([g for g in lines if g is not None], dtype=object)))
    parts = [q for q in flat if q.geom_type == "LineString" and len(q.coords) >= 2]
    if not parts:
        return None
    merged = shapely.line_merge(shapely.MultiLineString(parts), directed=True)
    return merged


def river_record(fid: str, tags: dict, layer: str) -> dict | None:
    local = tags.get("name") or ""
    name = tags.get("name:en") or local
    if not name:
        return None
    r = {"id": fid, "layer": layer, "name": name, "type": "river"}
    if local and local != name:
        r["local_name"] = local
    if tags.get("wikidata"):
        r["wikidata"] = tags["wikidata"]
    return r


def group_ways(relations: list[tuple[str, dict, list[int]]], ways: dict[int, tuple[dict, object]]) \
        -> list[tuple[dict, list[int]]]:
    """The rivers, as (tags and id, way ids): each relation with its ways, then the ways with a Wikidata link
    in no relation, by that link. A way's link to a river already made by a relation joins it to that river."""
    rivers: dict[str, tuple[str, dict, list[int]]] = {}
    in_relation: set[int] = set()
    for fid, tags, way_ids in relations:
        q = tags.get("wikidata")
        if not q:   # the link most of its ways carry, if they carry one
            links = defaultdict(int)
            for w in way_ids:
                if w in ways and ways[w][0].get("wikidata"):
                    links[ways[w][0]["wikidata"]] += 1
            if links and max(links.values()) * 2 > len(way_ids):
                q = max(links, key=lambda k: (links[k], k))
                tags = {**tags, "wikidata": q}
        if not q:   # a relation with no Wikidata link is a river of its own; read keeps it if long enough
            rivers[fid] = (fid, {**tags, "unlinked": True}, list(way_ids))
            in_relation.update(way_ids)
            continue
        if q in rivers:   # two relations for one river: one river
            rivers[q][2].extend(w for w in way_ids if w not in rivers[q][2])
        else:
            rivers[q] = (fid, tags, list(way_ids))
        in_relation.update(way_ids)
    by_q: dict[str, list[int]] = defaultdict(list)
    for wid, (tags, _g) in sorted(ways.items()):
        q = tags.get("wikidata")
        if q and wid not in in_relation:
            by_q[q].append(wid)
    for q, wids in sorted(by_q.items()):
        if q in rivers:
            rivers[q][2].extend(wids)
        else:
            tags = dict(ways[wids[0]][0])
            # The name most of its ways have.
            names = defaultdict(int)
            for w in wids:
                if ways[w][0].get("name"):
                    names[(ways[w][0].get("name"), ways[w][0].get("name:en", ""))] += 1
            if names:
                (tags["name"], tags["name:en"]) = max(names, key=lambda k: (names[k], k))
            rivers[q] = (f"osm:w{min(wids)}", tags, wids)
    return [({"id": fid, **tags}, wids) for _q, (fid, tags, wids) in sorted(rivers.items(), key=lambda kv: kv[1][0])]


SECTION_SHARE = 0.9   # a river with this share of its ways in a larger river is a section of it


def leave_out_sections(rivers: list[tuple[dict, list[int]]]) -> tuple[list[tuple[dict, list[int]]], list[str]]:
    """The rivers less those that are a section of another, such as the Upper Rhine inside the Rhine: a river
    with SECTION_SHARE of its ways in one river with more ways. Returns the rivers kept and the names left."""
    owner: dict[int, list[int]] = defaultdict(list)
    for i, (_t, wids) in enumerate(rivers):
        for w in wids:
            owner[w].append(i)
    keep, left = [], []
    for i, (tags, wids) in enumerate(rivers):
        counts: dict[int, int] = defaultdict(int)
        for w in wids:
            for j in owner[w]:
                if j != i and len(rivers[j][1]) > len(wids):
                    counts[j] += 1
        if counts and max(counts.values()) >= SECTION_SHARE * len(wids):
            j = max(counts, key=lambda k: (counts[k], -k))
            left.append(f"{tags.get('name:en') or tags.get('name')} ({tags['id']}), a section of "
                        f"{rivers[j][0].get('name:en') or rivers[j][0].get('name')} ({rivers[j][0]['id']})")
            continue
        keep.append((tags, wids))
    return keep, left


def read(gol: Path, request: dict, say=print) -> tuple[list[dict], list]:
    """Every river of at least min_km, as records and simplified lines, in id order. Runs in the short-lived
    process."""
    import geodesk

    world = geodesk.Features(str(gol))
    box = request.get("box")
    gbox = geodesk.Box(west=box[0], south=box[1], east=box[2], north=box[3]) if box else None
    tol = float(request.get("tolerance_m", 0)) / METRES_PER_DEGREE
    keys = ("name", "name:en", "wikidata")

    def tags_of(f):
        return {k: str(f.tags[k]) for k in keys if f.tags[k]}

    t = time.perf_counter()
    ways: dict[int, tuple[dict, object]] = {}

    def add_way(f):
        if f.id not in ways:
            g = geodesk.from_mercator(f.shape)
            ways[f.id] = (tags_of(f), g)

    sel = world(RIVER_WAYS)
    for f in (sel(gbox) if gbox is not None else sel):
        if f.tags["wikidata"]:
            add_way(f)
    say(f"Read {len(ways):,} river ways with a Wikidata link in {time.perf_counter() - t:.0f} seconds.")
    t = time.perf_counter()
    min_km_unlinked = float(request.get("min_km_unlinked", 0))
    relations = []
    sel = world(RIVER_RELATIONS)
    for r in (sel(gbox) if gbox is not None else sel):
        if not r.tags["wikidata"] and not (r.tags["name"] and min_km_unlinked):
            continue
        ids = []
        for m in r.members:
            if m.is_way:
                add_way(m)
                ids.append(m.id)
        relations.append((f"osm:r{r.id}", tags_of(r), ids))
    say(f"Read {len(relations):,} river relations, with {len(ways):,} ways in all, in "
        f"{time.perf_counter() - t:.0f} seconds.")
    t = time.perf_counter()
    min_km = float(request.get("min_km", 0))
    records, geoms, short, unlinked = [], [], 0, 0
    rivers, sections = leave_out_sections(group_ways(relations, ways))
    for name in sections:
        say(f"Left out, as a section of a river: {name}.")
    clip = shapely.box(*box) if box else None
    for tags, wids in rivers:
        fid = tags.pop("id")
        is_unlinked = tags.pop("unlinked", False)
        rec = river_record(fid, tags, request["layer"])
        if rec is None:
            continue
        g = join_lines([ways[w][1] for w in wids])
        if g is None:
            continue
        km = length_km(g)
        if km < min_km or (is_unlinked and km < min_km_unlinked):
            short += 1
            continue
        unlinked += is_unlinked
        if clip is not None:   # a trial with a box keeps only the rivers' lines inside it
            g = join_lines([shapely.intersection(g, clip)])
            if g is None or g.is_empty:
                continue
        if tol:
            g = shapely.simplify(g, tol, preserve_topology=False)
        rec["length_km"] = round(length_km(g), 1)
        records.append(rec)
        geoms.append(shapely.set_precision(g, 1e-7))
    say(f"Joined {len(records):,} rivers of {min_km:g} km or more, {unlinked:,} of them relations with no Wikidata "
        f"link, of {min_km_unlinked:g} km or more, and left out {short:,} shorter, in "
        f"{time.perf_counter() - t:.0f} seconds.")
    order = sorted(range(len(records)), key=lambda i: records[i]["id"])
    return [records[i] for i in order], [geoms[i] for i in order]


def main(folder: Path) -> int:
    """The entry point of the short-lived process: "mapdata read-in-process osm_rivers <folder>"."""
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


# The check against Natural Earth's rivers ------------------------------------------------------------

def natural_earth_rivers(path: Path, box, min_km: float) -> list[dict]:
    """Natural Earth's rivers, each name's lines joined, of at least min_km inside the box."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    clip = shapely.box(*box) if box else None
    by_name: dict[str, dict] = {}
    for f in data["features"]:
        p = f["properties"]
        if p.get("featurecla") not in ("River", "River (Intermittent)") or not f.get("geometry"):
            continue
        name = p.get("name_en") or p.get("name") or ""
        if not name:
            continue
        g = shapely.geometry.shape(f["geometry"])
        if clip is not None:
            g = shapely.intersection(g, clip)
            if g.is_empty:
                continue
        r = by_name.setdefault(name, {"name": name, "wikidata": p.get("wikidataid") or "", "lines": []})
        r["lines"].append(g)
        if not r["wikidata"] and p.get("wikidataid"):
            r["wikidata"] = p["wikidataid"]
    out = []
    for r in by_name.values():
        g = shapely.union_all(r["lines"])
        km = length_km(g)
        if km >= min_km:
            out.append({"name": r["name"], "wikidata": r["wikidata"], "km": km, "shape": g})
    return sorted(out, key=lambda r: -r["km"])


NAME_WITHIN_KM = 50   # a river of the layer this near with the same name is the same river
RIVER_WORDS = {"river", "rio", "rivier", "riviere", "fleuve", "fluss", "sungai", "nahr", "nehri", "reka", "rzeka",
               "the", "de", "do", "da", "das", "dos", "la", "le", "el"}


def name_words(text: str) -> str:
    """A river's name without accents, case or words such as River and Rio: "Rio das Velhas" is "velhas"."""
    import unicodedata

    plain = "".join(c for c in unicodedata.normalize("NFKD", str(text or "")) if not unicodedata.combining(c))
    words = [w for w in "".join(c if c.isalnum() else " " for c in plain.lower()).split() if w not in RIVER_WORDS]
    return " ".join(words)


def same_name(ne_name: str, record: dict) -> bool:
    want = name_words(ne_name)
    if not want:
        return False
    for n in (record.get("name"), record.get("local_name")):
        have = f" {name_words(n)} "
        if f" {want} " in have:
            return True
    return False


def unmatched(ne: list[dict], records: list[dict], geoms: list, within_km: float) -> list[dict]:
    """The Natural Earth rivers with no river of the layer: none with its Wikidata link, none with its name within
    NAME_WITHIN_KM, ignoring accents and words such as River, and none within within_km of the middle of its
    longest line."""
    qs = {r.get("wikidata") for r in records if r.get("wikidata")}
    tree = shapely.STRtree(geoms) if geoms else None
    d = within_km * 1000 / METRES_PER_DEGREE
    near = NAME_WITHIN_KM * 1000 / METRES_PER_DEGREE
    out = []
    for r in ne:
        if r["wikidata"] and r["wikidata"] in qs:
            continue
        if tree is not None and any(same_name(r["name"], records[i])
                                    for i in tree.query(r["shape"], predicate="dwithin", distance=near).tolist()):
            continue
        longest = max(shapely.get_parts(r["shape"]), key=lambda g: g.length)
        mid = shapely.line_interpolate_point(longest, 0.5, normalized=True)
        if tree is not None and len(tree.query(mid, predicate="dwithin", distance=d)):
            continue
        out.append(r)
    return out


def run(ctx) -> None:
    s = ctx.settings
    layer = s.get("layer", "rivers")
    if layer not in ctx.pack.layers:
        raise BuildStopped(f"The osm-rivers stage writes to the layer {layer}, which the pack's layer groups do not "
                           "define. Add the layer, or correct the stage's settings.")
    _source, gol = ctx.source(s.get("source", "planet"))
    request = {"gol": str(gol), "layer": layer, "box": s.get("box"), "min_km": s.get("min_km", 0),
               "min_km_unlinked": s.get("min_km_unlinked", 0),
               "tolerance_m": s.get("tolerance_m", 0), "version": READ_VERSION}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(request, indent=1), encoding="utf-8", newline="\n")
    out = ctx.folder / READ_FOLDER
    for name in ("features.json", "shapes.wkb", "read log.txt"):
        ctx.claim(out / name)
    ctx.progress.line(f"Reading the rivers from the planet file {gol.name} in a separate process, which ends when "
                      "it has finished.")
    done = subprocess.run([sys.executable, "-m", "mapdata", "--data", str(ctx.folders.root), "read-in-process",
                           "osm_rivers", str(ctx.folder)], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    for line in (done.stdout or "").splitlines():
        ctx.progress.line(line)
    if done.returncode != 0 or not (out / "features.json").is_file():
        raise BuildStopped("Reading the rivers from the planet file failed. The end of its output was: "
                           + " ".join((done.stderr or done.stdout or "").splitlines()[-5:]))
    r_records, r_geoms = features.load(out)
    lengths = {r["id"]: r.pop("length_km", 0) for r in r_records}   # all its lines, branches too: for the log only
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(ctx.previous / name, ctx.claim(ctx.folder / name))
    features.append(ctx.folder, r_records, [shapely.to_wkb(g) for g in r_geoms])
    total = sum(lengths.values())
    ctx.progress.line(f"The layer {layer}: {len(r_records):,} rivers, {total:,.0f} km in all.")
    longest = sorted(r_records, key=lambda r: -lengths[r["id"]])[:10]
    ctx.progress.log("The rivers with the most line: " + "; ".join(f"{r['name']} {lengths[r['id']]:,.0f} km"
                                                              for r in longest) + ".")
    if s.get("check"):
        source, path = ctx.source(s["check"])
        check_km = float(s.get("check_km", 500))
        ne = natural_earth_rivers(path, s.get("box"), check_km)
        gone = unmatched(ne, r_records, r_geoms, float(s.get("check_within_km", 5)))
        ctx.progress.line(f"Checked against {source.name}: {len(ne)} rivers of {check_km:g} km or more, of which "
                          f"{len(gone)} have no river of the layer. The log lists them.")
        for r in gone:
            ctx.progress.log(f"Not in the layer {layer}: {r['name']} in Natural Earth"
                             + (f" ({r['wikidata']})" if r["wikidata"] else "") + f", {r['km']:,.0f} km.")

