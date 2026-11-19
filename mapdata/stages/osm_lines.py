"""Stage "osm-lines": roads and railways from the planet file's ways, joined into whole lines (P3-T1i, DAT-1).

OpenStreetMap maps a road as many short ways, often two for a motorway, one
for each carriageway. The stage joins them so a road's record is one feature,
not thousands of short lines:

* Each layer in the settings has its queries, each with the type its ways get,
  such as motorway or railway, and a key: ref joins the ways by their number,
  such as "M3", then by name for the ways with no number; name joins them by
  name, then by number. Only the first of several numbers, such as "A 3;IP 1",
  is used.
* The ways of one key are joined per country, so the A1 in France and the A1
  in Italy are two roads. A way's country is the one its middle is in, or the
  nearest, from the countries of the stage before.
* The ways of one key and country are split into separate roads where their
  stretches are far apart, so England's M3 and Belfast's M3 are two roads
  (P3-T28d). Stretches within GAP_KM of each other are always one road: a
  junction, a bridge or a short missing way. Further apart, they stay one road
  only while the gap is at most GAP_SHARE times the shorter stretch's length
  and at most GAP_MOST_KM, so a motorway with an unbuilt stretch, such as the
  A 4 in Germany, stays one, and a short road far from another of the same
  number, such as France's D roads in two departments, is a road of its own.
  Each road keeps the name and takes the id of its smallest way. The ways with
  neither number nor name stay one feature per country.
* A way with neither number nor name takes the key of a way it meets end to
  end, again and again, so a short unnamed link joins its road. The rest are
  one feature per country, named as the layer's unnamed setting says.
* A road with a number is named by the number. Where at least half of its ways
  carry the same name, the name is added: "A-8, Autovia del Cantabrico". A
  railway is named by its name; one with only a number is "Railway line" and
  the number.
* A feature's type is the type most of its ways have, and its Wikidata link the
  link most of them carry, if more than half do.

The lines are simplified to tolerance_m. GeoDesk gives its memory back only
when the process ends (spike S2), so the reading is done in its own short-lived
process, which also does the joining. The features of the stage before are
kept, and the lines added after them.

Settings: source (planet), tolerance_m, box, and layers: a list, each with
layer, queries (each a query and a type), key (ref or name), unnamed (the name
for lines with neither), and number_name (the words before a number alone, for
railways).
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
from mapdata.stages.osm_rivers import join_lines, length_km

READ_VERSION = "osm-lines-2"
REQUEST = "request.json"
READ_FOLDER = "read"
METRES_PER_DEGREE = 111_320.0
TAG_KEYS = ("name", "name:en", "ref", "wikidata")
NAME_SHARE = 0.5     # a road's name is added to its number when this share of its ways carry it
LINK_PASSES = 50     # how many times unnamed ways look for a named way they meet
KM_PER_DEGREE = METRES_PER_DEGREE / 1000
# Splitting a road whose stretches are far apart (P3-T28d), chosen from 487 named roads of the Western Europe trial:
TOUCH_KM = 0.1       # ways this close are one stretch: carriageways side by side, ways end to end
GAP_KM = 10.0        # stretches this close are always one road: a junction, a bridge, a short missing way
GAP_SHARE = 3.0      # further apart, one road while the gap is at most this many times the shorter stretch's length
GAP_MOST_KM = 150.0  # and never across more than this: the A 4's unbuilt 119 km stays, the sea to Belfast does not
PAIRS_MOST = 2000    # a key with more roads than this after the GAP_KM step is not joined further (each two measured)


def first_ref(text: str) -> str:
    """The first of a way's numbers: "A 3;IP 1" is "A 3"."""
    return str(text or "").split(";")[0].strip()


def way_key(tags: dict, key: str) -> tuple[str, str] | None:
    """The key a way is joined by: ("ref", "M3") or ("name", "East Coast Main Line"); None with neither."""
    ref, name = first_ref(tags.get("ref")), (tags.get("name") or "").strip()
    order = (("ref", ref), ("name", name)) if key == "ref" else (("name", name), ("ref", ref))
    for kind, value in order:
        if value:
            return kind, value
    return None


def end_points(wids: list[int], geoms: dict[int, object]) -> dict[int, list[tuple[float, float]]]:
    """The two ends of each line of each way, rounded as the planet file's coordinates are, for all the ways at
    once."""
    if not wids:
        return {}
    parts, index = shapely.get_parts(np.array([geoms[w] for w in wids], dtype=object), return_index=True)
    out: dict[int, list] = {w: [] for w in wids}
    for which in (0, -1):
        xy = np.round(shapely.get_coordinates(shapely.get_point(parts, which)), 7)
        for i, (x, y) in zip(index.tolist(), xy.tolist()):
            out[wids[i]].append((x, y))
    return out


def link_unnamed(keys: dict[int, tuple | None], geoms: dict[int, object]) -> int:
    """Each way with no key takes the key of the ways it meets end to end, the one most of them have, then the
    first in order; repeated, so a chain of unnamed ways joins the road at its end. Changes keys in place, and
    returns how many ways took a key."""
    ends = end_points(sorted(geoms), geoms)
    at: dict[tuple, list[int]] = defaultdict(list)
    for wid in sorted(ends):
        for p in ends[wid]:
            at[p].append(wid)
    took = 0
    for _ in range(LINK_PASSES):
        found = {}
        for wid in sorted(w for w, k in keys.items() if k is None):
            counts: dict[tuple, int] = defaultdict(int)
            for p in ends.get(wid, ()):
                for other in at[p]:
                    if other != wid and keys.get(other) is not None:
                        counts[keys[other]] += 1
            if counts:
                found[wid] = max(sorted(counts), key=lambda k: counts[k])
        if not found:
            break
        keys.update(found)
        took += len(found)
    return took


def countries_of(points: list, countries: list[tuple[str, object]]) -> list[str]:
    """The id of the country each point is in, or of the nearest; "" with no countries. Each country is tested,
    prepared, against only the points in its bounds, all at once: testing each point against a whole outline
    took 104 seconds for Western Europe's 352,000 railway ways."""
    if not countries:
        return [""] * len(points)
    pts = np.array(points, dtype=object)
    xy = shapely.get_coordinates(pts)
    tree = shapely.STRtree(pts)
    out = [""] * len(points)
    for cid, g in countries:
        near = tree.query(shapely.box(*g.bounds))
        if not len(near):
            continue
        shapely.prepare(g)
        inside = near[shapely.intersects_xy(g, xy[near, 0], xy[near, 1])]
        for p in np.sort(inside).tolist():
            if not out[p]:
                out[p] = cid
    rest = [i for i, v in enumerate(out) if not v]
    if rest:
        ctree = shapely.STRtree([g for _i, g in countries])
        near_p, near_c = ctree.query_nearest(pts[rest], all_matches=False)
        for p, c in zip(near_p.tolist(), near_c.tolist()):
            out[rest[p]] = countries[c][0]
    return out


def _connected(left, right, n: int) -> list[list[int]]:
    """The sets of 0..n-1 that the pairs (left, right) connect, each in index order, in the order of their first
    index. All in NumPy: each takes the smallest label of those it meets, then of its label's label, until none
    changes."""
    label = np.arange(n, dtype=np.intp)
    while True:
        before = label.copy()
        np.minimum.at(label, left, label[right])
        label = label[label]
        if np.array_equal(label, before):
            break
    sets: dict[int, list[int]] = defaultdict(list)
    for i, v in enumerate(label.tolist()):
        sets[v].append(i)
    return sorted(sets.values(), key=lambda v: v[0])


def road_parts(geoms: list, gap_km: float = GAP_KM, share: float = GAP_SHARE,
               most_km: float = GAP_MOST_KM) -> list[list[int]]:
    """The indexes of one road's ways in the separate roads they make (P3-T28d), each in index order, in the order
    of their first index. Ways within TOUCH_KM are one stretch, and stretches within gap_km one road. Further apart,
    the nearest stretches are joined first, while the gap is at most share times the shorter one's length (the
    diagonal of its bounds) and at most most_km. Distances are measured with each longitude shortened by the cosine
    of its latitude, near enough for these gaps. Only the near ways are paired: pairing every way within gap_km took
    40 seconds for 487 roads, as a road in a city has many ways within a few km of each other."""
    n = len(geoms)
    if n < 2:
        return [list(range(n))]

    def flatten(xy):
        xy = xy.copy()
        xy[:, 0] *= np.cos(np.radians(xy[:, 1]))
        return xy

    flat = shapely.transform(np.array(geoms, dtype=object), flatten)
    left, right = shapely.STRtree(flat).query(flat, predicate="dwithin", distance=TOUCH_KM / KM_PER_DEGREE)
    stretches = _connected(left, right, n)
    if len(stretches) == 1:
        return stretches
    parts = np.array([shapely.multilinestrings(list(flat[s])) for s in stretches], dtype=object)
    left, right = shapely.STRtree(parts).query(parts, predicate="dwithin", distance=gap_km / KM_PER_DEGREE)
    roads = [sorted(w for k in s for w in stretches[k]) for s in _connected(left, right, len(parts))]
    if len(roads) == 1 or not share or len(roads) > PAIRS_MOST:
        # Above PAIRS_MOST, measuring each two would take too long and too much memory: such a key is reused far
        # and wide, so the stretches 10 km apart are already separate roads.
        return sorted(roads, key=lambda v: v[0])
    parts = np.array([shapely.multilinestrings(list(flat[r])) for r in roads], dtype=object)
    bounds = shapely.bounds(parts)
    m = len(roads)
    a, b = np.triu_indices(m, 1)
    dist = shapely.distance(parts[a], parts[b]) * KM_PER_DEGREE
    root = list(range(m))

    def find(x):
        while root[x] != x:
            root[x] = root[root[x]]
            x = root[x]
        return x

    def size(x):
        return float(np.hypot(bounds[x, 2] - bounds[x, 0], bounds[x, 3] - bounds[x, 1]) * KM_PER_DEGREE)

    for e in np.argsort(dist, kind="stable").tolist():
        x, y = find(int(a[e])), find(int(b[e]))
        if x == y or dist[e] > most_km:
            continue
        if dist[e] <= share * min(size(x), size(y)):
            x, y = min(x, y), max(x, y)
            root[y] = x
            bounds[x] = [min(bounds[x, 0], bounds[y, 0]), min(bounds[x, 1], bounds[y, 1]),
                         max(bounds[x, 2], bounds[y, 2]), max(bounds[x, 3], bounds[y, 3])]
    out: dict[int, list[int]] = defaultdict(list)
    for k, r in enumerate(roads):
        out[find(k)].extend(r)
    return sorted((sorted(v) for v in out.values()), key=lambda v: v[0])


def simplify_line(g, tol: float):
    """A line simplified to tol degrees, at the pack's precision. A closed line, such as a roundabout or a ring
    road, can shrink to a point when simplified plainly: in Western Europe, 641 roads did. It keeps its ring."""
    if tol:
        simple = shapely.set_precision(shapely.simplify(g, tol, preserve_topology=False), 1e-7)
        if simple.length > 0:
            return simple
        g = shapely.simplify(g, tol, preserve_topology=True)
    return shapely.set_precision(g, 1e-7)


def most(values: list[str]) -> tuple[str, int]:
    """The value most of the list has, the first in order on a tie, with how many; ("", 0) for none."""
    counts: dict[str, int] = defaultdict(int)
    for v in values:
        if v:
            counts[v] += 1
    if not counts:
        return "", 0
    best = max(sorted(counts), key=lambda k: counts[k])
    return best, counts[best]


def line_record(fid: str, layer: dict, key: tuple | None, ways: list[dict], kinds: list[str]) -> dict:
    """One line's record from its ways' tags."""
    n = len(ways)
    kind, _ = most(kinds)
    rec = {"id": fid, "layer": layer["layer"], "type": kind}
    names = [w.get("name:en") or w.get("name") or "" for w in ways]
    name, name_n = most(names)
    ref, _ = most([first_ref(w.get("ref")) for w in ways])
    if key is None:
        rec["name"] = layer.get("unnamed") or "Unnamed"
    elif key[0] == "ref" and layer.get("key", "ref") == "ref":
        rec["name"] = key[1] + (f", {name}" if name and name_n >= NAME_SHARE * n else "")
        rec["ref"] = key[1]
    elif key[0] == "ref":
        rec["name"] = f"{layer.get('number_name') or 'Line'} {key[1]}"
        rec["ref"] = key[1]
    else:
        en, _ = most([w.get("name:en") or "" for w in ways if (w.get("name") or "").strip() == key[1]])
        rec["name"] = en or key[1]
        if en and en != key[1]:
            rec["local_name"] = key[1]
        if ref and layer.get("key", "ref") == "ref":
            rec["ref"] = ref
    q, q_n = most([w.get("wikidata") or "" for w in ways])
    if q and q_n * 2 > n:
        rec["wikidata"] = q
    return rec


def group_layer(layer: dict, ways: dict[int, tuple[dict, str, object]], country: dict[int, str],
                say=print) -> tuple[list[dict], list]:
    """One layer's ways joined into lines: by key and country, after unnamed ways have taken their neighbours'
    keys, then split where their stretches are far apart (road_parts). Returns the records and lines, in id
    order."""
    keys = {wid: way_key(t, layer.get("key", "ref")) for wid, (t, _k, _g) in ways.items()}
    unnamed = sum(1 for k in keys.values() if k is None)
    took = link_unnamed(keys, {wid: g for wid, (_t, _k, g) in ways.items()})
    say(f"The layer {layer['layer']}: {len(ways):,} ways, {unnamed:,} with neither number nor name, of which "
        f"{took:,} joined a line they meet.")
    by_key: dict[tuple, list[int]] = defaultdict(list)
    for wid in sorted(ways):
        by_key[(country.get(wid, ""), keys[wid])].append(wid)
    groups: list[tuple[tuple, list[int]]] = []
    split, made = 0, 0
    for (c, key), wids in by_key.items():
        sets = road_parts([ways[w][2] for w in wids]) if key is not None else [list(range(len(wids)))]
        if len(sets) > 1:
            split += 1
            made += len(sets)
        groups.extend(((c, key), [wids[i] for i in s]) for s in sets)
    say(f"Split {split:,} lines of the layer {layer['layer']} whose stretches are far apart into {made:,}.")
    records, geoms = [], []
    for (_c, key), wids in sorted(groups, key=lambda kv: min(kv[1])):
        g = join_lines([ways[w][2] for w in wids])
        if g is None:
            continue
        rec = line_record(f"osm:w{min(wids)}", layer, key, [ways[w][0] for w in wids], [ways[w][1] for w in wids])
        if country.get(wids[0]):
            rec["country"] = country[wids[0]]
        records.append(rec)
        geoms.append(g)
    return records, geoms


def read(gol: Path, request: dict, countries: list[tuple[str, object]], say=print) -> tuple[list[dict], list]:
    """Every layer's lines, as records and simplified lines, in id order. Runs in the short-lived process."""
    import geodesk

    world = geodesk.Features(str(gol))
    box = request.get("box")
    gbox = geodesk.Box(west=box[0], south=box[1], east=box[2], north=box[3]) if box else None
    tol = float(request.get("tolerance_m", 0)) / METRES_PER_DEGREE
    clip = shapely.box(*box) if box else None
    records, geoms = [], []
    taken: set[int] = set()
    for layer in request["layers"]:
        t = time.perf_counter()
        ways: dict[int, tuple[dict, str, object]] = {}
        for q in layer["queries"]:
            sel = world(q["query"])
            n = 0
            for f in (sel(gbox) if gbox is not None else sel):
                if f.id in ways or f.id in taken:
                    continue
                g = geodesk.from_mercator(f.shape)
                if g is None or g.is_empty:
                    continue
                ways[f.id] = ({k: str(f.tags[k]) for k in TAG_KEYS if f.tags[k]}, q["type"], g)
                n += 1
            say(f"Read {n:,} ways for {q['query']}.")
        taken.update(ways)
        say(f"Read the layer {layer['layer']} in {time.perf_counter() - t:.0f} seconds.")
        t = time.perf_counter()
        wids = sorted(ways)
        mids = [shapely.line_interpolate_point(ways[w][2], 0.5, normalized=True) for w in wids]
        country = dict(zip(wids, countries_of(mids, countries)))
        say(f"Found the country of each way in {time.perf_counter() - t:.0f} seconds.")
        recs, lines = group_layer(layer, ways, country, say)
        km, empty = 0.0, 0
        for rec, g in zip(recs, lines):
            if clip is not None:   # a trial with a box keeps only the lines inside it
                g = join_lines([shapely.intersection(g, clip)])
                if g is None or g.is_empty:
                    continue
            g = simplify_line(g, tol)
            if g is None or g.is_empty:   # a stub shorter than the coordinates' precision
                empty += 1
                continue
            rec["length_km"] = round(length_km(g), 1)
            km += rec["length_km"]
            records.append(rec)
            geoms.append(g)
        say(f"Joined the layer {layer['layer']} into {len(recs) - empty:,} lines, {km:,.0f} km of line in all, in "
            f"{time.perf_counter() - t:.0f} seconds." + (f" Left out {empty:,} shorter than a centimetre." if empty
                                                         else ""))
    order = sorted(range(len(records)), key=lambda i: records[i]["id"])
    return [records[i] for i in order], [geoms[i] for i in order]


def main(folder: Path) -> int:
    """The entry point of the short-lived process: "mapdata read-in-process osm_lines <folder>"."""
    request = json.loads((folder / REQUEST).read_text(encoding="utf-8"))
    lines: list[str] = []

    def say(text):
        lines.append(text)
        print(text, flush=True)

    countries: list[tuple[str, object]] = []
    if request.get("countries_from"):
        c_records, c_geoms = features.load_layers(Path(request["countries_from"]), {"countries"})
        countries = [(r["id"], g) for r, g in zip(c_records, c_geoms)]
    records, geoms = read(Path(request["gol"]), request, countries, say)
    out = folder / READ_FOLDER
    out.mkdir(exist_ok=True)
    features.save(out, records, geoms)
    (out / "read log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


def run(ctx) -> None:
    s = ctx.settings
    layers = s.get("layers") or []
    if not layers:
        raise BuildStopped("The osm-lines stage needs layers, each with layer, queries and key.")
    for layer in layers:
        if layer.get("layer") not in ctx.pack.layers:
            raise BuildStopped(f"The osm-lines stage writes to the layer {layer.get('layer')}, which the pack's layer "
                               "groups do not define. Add the layer, or correct the stage's settings.")
        if layer.get("key", "ref") not in ("ref", "name"):
            raise BuildStopped(f"The layer {layer['layer']}'s key is {layer['key']}; it must be ref or name.")
    _source, gol = ctx.source(s.get("source", "planet"))
    request = {"gol": str(gol), "layers": layers, "box": s.get("box"), "tolerance_m": s.get("tolerance_m", 0),
               "countries_from": str(ctx.previous) if ctx.previous else "", "version": READ_VERSION}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(request, indent=1), encoding="utf-8", newline="\n")
    out = ctx.folder / READ_FOLDER
    for name in ("features.json", "shapes.wkb", "read log.txt"):
        ctx.claim(out / name)
    ctx.progress.line(f"Reading the roads and railways from the planet file {gol.name} in a separate process, which "
                      "ends when it has finished.")
    done = subprocess.Popen([sys.executable, "-m", "mapdata", "--data", str(ctx.folders.root), "read-in-process",
                             "osm_lines", str(ctx.folder)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace")
    for line in done.stdout:   # each line as it comes, so a long read is seen to move (DMT-2)
        ctx.progress.line(line.rstrip())
    err = done.stderr.read()
    if done.wait() != 0 or not (out / "features.json").is_file():
        raise BuildStopped("Reading the roads and railways from the planet file failed. The end of its output was: "
                           + " ".join((err or "").splitlines()[-5:]))
    l_records, l_geoms = features.load(out)
    lengths = {r["id"]: r.pop("length_km", 0) for r in l_records}
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(ctx.previous / name, ctx.claim(ctx.folder / name))
    features.append(ctx.folder, l_records, [shapely.to_wkb(g) for g in l_geoms])
    for layer in layers:
        mine = [r for r in l_records if r["layer"] == layer["layer"]]
        kinds: dict[str, int] = defaultdict(int)
        for r in mine:
            kinds[r["type"]] += 1
        ctx.progress.line(f"The layer {layer['layer']}: {len(mine):,} lines, "
                          f"{sum(lengths[r['id']] for r in mine):,.0f} km in all: "
                          + ", ".join(f"{n:,} of type {k}" for k, n in sorted(kinds.items())) + ".")
        longest = sorted(mine, key=lambda r: -lengths[r["id"]])[:10]
        ctx.progress.log(f"The longest in the layer {layer['layer']}: "
                         + "; ".join(f"{r['name']} {lengths[r['id']]:,.0f} km" for r in longest) + ".")
