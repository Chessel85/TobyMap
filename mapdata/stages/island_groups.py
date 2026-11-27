"""Stage "island-groups": groups of islands, such as the Channel Islands, a layer of their own (P4-T13b, DAT-1, DAT-3,
LOC-3). The method is P4-T13a's, in docs/plan/p4-t13a-island-groups-report.md.

Which islands belong to a group, each step adding to the one before:

1. OpenStreetMap: every feature tagged place=archipelago that is an area, or a relation of type group,
   multipolygon or boundary, read from the planet file in a short-lived process, as the osm-places stage reads.
   Its member islands are the islands of the islands layer whose point lies inside its outline, or within
   near_m of it, and, for a relation, the islands it lists by id, as the Cyclades are. Relations of the other
   types, land_area, site and cluster, are left out: "Guernsey (land mass)" is a land_area wrongly tagged as a
   group.
2. Groups inside groups: a group a relation lists (OpenStreetMap's subareas, such as the Frisian Islands' three
   parts), or whose Wikidata item is a part of another group's item (Wikidata's "part of", P361, or "has part",
   P527, such as Santorini in the Cyclades). The inner group's islands are members of the outer group too. Only
   the links between groups are taken from Wikidata, never single islands, as its lists of islands are uneven.
   The links are fetched once, from Wikidata's own interface, and kept in the data folder beside the facts, in
   groups-<refresh>.jsonl, so a rebuild fetches nothing and the pack is the same byte for byte (DMT-1).
3. Our own record, mapdata/config/island_groups.yaml: the groups the sources lack, such as the Balearic Islands
   (the islands inside a region of the pack) and the British Isles (the islands inside Natural Earth's outline,
   islands named by their Wikidata items, and groups named by id); a Wikidata link or an English name where
   OpenStreetMap has none or another; and any group to leave out.
4. Natural Earth: its groups of islands that match no group above by Wikidata link or name. The islands inside
   its outline become members; its outline is not used, as it is too rough to say "you are in". A Natural Earth
   group that is one island or a country, such as Maui or Japan, is left out: one whose largest member island
   holds more than one_island_share of its land, or whose name is a country's, unless the record keeps it.
5. A group is kept when it has at least min_islands member islands and at least min_land_km2 of land, so the many
   small groups of rocks do not crowd the layer. Two groups with one Wikidata item are one group.

The outline, worked in kilometres about the group's middle:

1. The member islands joined into one shape.
2. The reach that joins the group into one part: the smallest distance that, growing every island by it, makes
   them touch, at most half of most_reach_km.
3. The islands grown by twice that reach, at least least_reach_km and at most most_reach_km, then shrunk back by
   that less edge_km. The gaps between the islands fill, and the outer edge lies edge_km off the outer coasts. A
   group whose islands lie further apart, such as the Azores, stays in parts.
4. Simplified to tolerance_m, then the land that is not in the group cut away: each part of the land layer (the
   countries, as the join stage drew them) that crosses the outline's edge, such as France near the Channel
   Islands, less the member islands. A land part wholly inside the outline stays in, as an island the sources
   forgot. The cut coast is the pack's own (DP220). The outline is cut to the box, if any, and only its parts
   that hold a member island are kept.

Names: the record's, then OpenStreetMap's English name, then Wikidata's English label, then OpenStreetMap's own
name, which is kept as the local name when it differs. Each group is of type "group of islands", with the id
group: and its source's id, such as group:osm:r6031891.

The groups overlap each other (the Hebrides hold the Inner and Outer Hebrides), so the layer is not painted as
one coverage (its fill is none). The features of the stage before are kept, and the groups added after them.

Settings: source (the planet file, planet), sources ([naturalearth-physical-regions, wikidata]), natural_earth
(naturalearth-physical-regions), wikidata (wikidata), refresh (the label of the links file, such as 2026-11),
offline (true: fetch nothing from Wikidata), record (mapdata/config/island_groups.yaml), layer (island-groups),
islands_layer (islands), land_layer (countries), area_layers ([regions], where the record's islands_in looks),
near_m (300), min_islands (2), min_land_km2 (1), one_island_share (0.5), edge_km (3), least_reach_km (10),
most_reach_km (60), tolerance_m (100) and box.
"""
from __future__ import annotations

import datetime
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import REPO
from mapdata.stages.physical import natural_earth_regions, polygonal

READ_VERSION = "island-groups-1"
REQUEST = "request.json"
READ_FOLDER = "read"
RECORD = "mapdata/config/island_groups.yaml"
TYPE = "group of islands"
ID_PREFIX = "group:"
KEPT_RELATIONS = ("multipolygon", "boundary", "group")   # land_area, site and cluster are left out
NE_CLASS = "Island group"
KM_PER_DEGREE = 111.32
API = "https://www.wikidata.org/w/api.php"
API_BATCH = 50
RECORD_KEYS = {"links", "names", "leave_out", "natural_earth_keep", "groups"}
GROUP_KEYS = {"id", "name", "wikidata", "islands_in", "natural_earth", "islands", "groups"}
DEFAULTS = {"near_m": 300.0, "min_islands": 2, "min_land_km2": 1.0, "one_island_share": 0.5, "edge_km": 3.0,
            "least_reach_km": 10.0, "most_reach_km": 60.0, "tolerance_m": 100.0}


# The record ---------------------------------------------------------------------------------------------------

def record_path(stage: dict) -> Path:
    return REPO / stage.get("record", RECORD)


def load_record(path: Path) -> dict:
    """The record of our own, checked, so a mistake in it stops the build before any work."""
    import yaml

    if not path.is_file():
        raise BuildStopped(f"The island-groups stage's record {path} is missing. Put it back, or name another in "
                           "the stage's record setting.")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    extra = set(data) - RECORD_KEYS
    if extra:
        raise BuildStopped(f"The record {path.name} has {', '.join(sorted(extra))}, which the island-groups stage "
                           f"does not know. It knows: {', '.join(sorted(RECORD_KEYS))}.")
    for g in data.get("groups") or []:
        bad = set(g) - GROUP_KEYS
        if bad or not g.get("id") or not g.get("name"):
            raise BuildStopped(f"A group in the record {path.name}, {g.get('name') or g.get('id') or 'unnamed'}, "
                               f"needs an id and a name, and may give only {', '.join(sorted(GROUP_KEYS))}.")
    return {"links": {str(k): str(v) for k, v in (data.get("links") or {}).items()},
            "names": {str(k): str(v) for k, v in (data.get("names") or {}).items()},
            "leave_out": [str(v) for v in data.get("leave_out") or []],
            "natural_earth_keep": [str(v) for v in data.get("natural_earth_keep") or []],
            "groups": list(data.get("groups") or [])}


def fingerprint_extra(stage: dict) -> dict:
    """The record is part of what the stage reads, so a change to it runs the stage again."""
    return {"record": load_record(record_path(stage))}


# Reading the planet file, in its own short-lived process --------------------------------------------------------

def osm_id(f) -> str:
    return f"osm:{'n' if f.is_node else 'w' if f.is_way else 'r'}{f.id}"


def read(gol: Path, box, say=print) -> tuple[list[dict], list]:
    """Every group tagged place=archipelago that is an area or a relation, with its tags, the ids a relation lists
    and its outline (empty for a relation with no area), in id order."""
    import geodesk

    world = geodesk.Features(str(gol))
    gbox = geodesk.Box(west=box[0], south=box[1], east=box[2], north=box[3]) if box else None
    found: dict[str, tuple[dict, object]] = {}
    t = time.perf_counter()
    for q in ("a[place=archipelago]", "r[place=archipelago]"):
        sel = world(q)
        if gbox is not None:
            sel = sel(gbox)
        for f in sel:
            fid = osm_id(f)
            if fid in found:
                continue
            rec = {"id": fid, "relation": str(f.tags["type"] or "") if f.is_relation else "way"}
            for key, tag in (("name", "name"), ("name_en", "name:en"), ("wikidata", "wikidata")):
                v = str(f.tags[tag] or "").strip()
                if v:
                    rec[key] = v
            if f.is_relation:
                rec["members"] = sorted({osm_id(m) for m in f.members})
            g = None
            if f.is_area:
                try:
                    g = polygonal(shapely.set_precision(geodesk.from_mercator(f.shape), 1e-7))
                except Exception as e:   # a broken outline: kept as a relation, by its members
                    say(f"The outline of {fid} could not be read: {e}.")
            found[fid] = (rec, g if g is not None else shapely.GeometryCollection())
    say(f"Read {len(found):,} groups tagged place=archipelago in {time.perf_counter() - t:.0f} seconds.")
    ids = sorted(found)
    return [found[i][0] for i in ids], [found[i][1] for i in ids]


def main(folder: Path) -> int:
    """The entry point of the short-lived process: python -m mapdata.stages.island_groups <folder>."""
    request = json.loads((folder / REQUEST).read_text(encoding="utf-8"))
    lines: list[str] = []

    def say(text):
        lines.append(text)
        print(text, flush=True)

    records, geoms = read(Path(request["gol"]), request.get("box"), say)
    out = folder / READ_FOLDER
    out.mkdir(exist_ok=True)
    features.save(out, records, geoms)
    (out / "read log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


def read_planet(ctx, gol: Path) -> tuple[list[dict], list]:
    request = {"gol": str(gol), "box": ctx.settings.get("box"), "version": READ_VERSION}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(request, indent=1), encoding="utf-8", newline="\n")
    out = ctx.folder / READ_FOLDER
    for name in ("features.json", "shapes.wkb", "read log.txt"):
        ctx.claim(out / name)
    ctx.progress.line(f"Reading the groups of islands from the planet file {gol.name} in a separate process, which "
                      "ends when it has finished.")
    done = subprocess.run([sys.executable, "-m", "mapdata.stages.island_groups", str(ctx.folder)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (done.stdout or "").splitlines():
        ctx.progress.log(line)
    if done.returncode != 0 or not (out / "features.json").is_file():
        raise BuildStopped("Reading the groups of islands from the planet file failed. The end of its output was: "
                           + " ".join((done.stderr or done.stdout or "").splitlines()[-5:]))
    return features.load(out)


# The links between groups, from Wikidata --------------------------------------------------------------------------

def links_path(folder: Path, refresh: str) -> Path:
    return Path(folder) / f"groups-{refresh}.jsonl"


def _get_json(url: str, timeout: float = 60.0, tries: int = 6, sleep=time.sleep, say=print, open_url=None) -> dict:
    """One request to Wikidata's interface. Waits and tries again when it is busy (429) or failing for a moment,
    as the wikidata stage's queries do: the world build of 27 November stopped on a 429 here."""
    import urllib.error
    import urllib.request

    from mapdata.stages.wikidata import CLIENT

    open_url = open_url or urllib.request.urlopen
    wait = 5.0
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": CLIENT, "Accept": "application/json"})
        try:
            with open_url(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries:
                raise
            after = e.headers.get("Retry-After") if e.headers else None
            wait = max(wait, float(after)) if after and after.isdigit() else wait
            say(f"Wikidata said {e.code}; waiting {wait:.0f} seconds, then trying again.")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == tries:
                raise
            say(f"Wikidata could not be reached ({e}); waiting {wait:.0f} seconds, then trying again.")
        sleep(wait)
        wait = min(wait * 2, 300.0)
    raise RuntimeError("unreachable")


def _claim_ids(entity: dict, prop: str) -> list[str]:
    out = []
    for c in (entity.get("claims") or {}).get(prop) or []:
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v, dict) and v.get("id"):
            out.append(str(v["id"]))
    return sorted(set(out))


def fetch_links(qids: list[str], get=_get_json, say=print, pause_s: float = 1.0, sleep=time.sleep,
                keep=None, today: str | None = None) -> dict[str, dict]:
    """For each item: its parts (P527), what it is part of (P361) and its English label, from Wikidata's own
    interface, API_BATCH items to a request. An item Wikidata no longer has is kept with none, so it is not
    asked for again."""
    import urllib.parse

    today = today or datetime.date.today().isoformat()
    out: dict[str, dict] = {}
    for n in range(0, len(qids), API_BATCH):
        part = qids[n:n + API_BATCH]
        url = API + "?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(part),
                                                  "props": "claims|labels", "languages": "en", "format": "json"})
        data = get(url)
        entities = data.get("entities") or {}
        got = {}
        for q in part:
            e = entities.get(q) or {}
            label = ((e.get("labels") or {}).get("en") or {}).get("value") or ""
            got[q] = {"id": q, "fetched": today, "parts": _claim_ids(e, "P527"), "part_of": _claim_ids(e, "P361"),
                      "label": label}
        out.update(got)
        if keep is not None:
            keep(got)
        say(f"Fetched the links of {min(n + API_BATCH, len(qids)):,} of {len(qids):,} groups from Wikidata.")
        if n + API_BATCH < len(qids):
            sleep(pause_s)
    return out


# Measures ------------------------------------------------------------------------------------------------------

def rough_km2(g) -> float:
    if g is None or g.is_empty:
        return 0.0
    lat = shapely.centroid(g).y
    return float(g.area) * KM_PER_DEGREE ** 2 * math.cos(math.radians(lat))


class Frame:
    """Kilometres east and north of a group's middle, near enough to grow and shrink its islands by. A group whose
    islands lie either side of the 180 degree line is worked with its western longitudes moved 360 degrees east."""

    def __init__(self, bounds):
        x0, y0, x1, y1 = bounds
        self.wrap = x1 - x0 > 180
        if self.wrap:
            x0, x1 = 0.0, 360.0
        self.lon0, self.lat0 = (x0 + x1) / 2, (y0 + y1) / 2
        self.kx = KM_PER_DEGREE * max(0.05, math.cos(math.radians(self.lat0)))

    def to_km(self, g):
        def f(c):
            x = np.where(c[:, 0] < 0, c[:, 0] + 360, c[:, 0]) if self.wrap else c[:, 0]
            return np.column_stack([(x - self.lon0) * self.kx, (c[:, 1] - self.lat0) * KM_PER_DEGREE])
        return shapely.transform(g, f)

    def to_degrees(self, g):
        g = shapely.transform(g, lambda c: np.column_stack([c[:, 0] / self.kx + self.lon0,
                                                             c[:, 1] / KM_PER_DEGREE + self.lat0]))
        if not self.wrap:
            return polygonal(g)
        east = polygonal(shapely.clip_by_rect(g, -180.0, -90.0, 180.0, 90.0))
        west = polygonal(shapely.clip_by_rect(g, 180.0, -90.0, 540.0, 90.0))
        if west is not None:
            west = shapely.transform(west, lambda c: np.column_stack([c[:, 0] - 360.0, c[:, 1]]))
        parts = [p for g in (east, west) if g is not None for p in shapely.get_parts(g)]
        return polygonal(shapely.MultiPolygon(parts)) if parts else None


def count_parts(g) -> int:
    return 0 if g is None or g.is_empty else int(shapely.get_num_geometries(g))


def joining_reach(shape_km, most_km: float) -> float:
    """The smallest distance, in kilometres, that grows the islands until they touch, found by halving; at most
    most_km. 0 for a group already in one part."""
    if count_parts(shape_km) <= 1:
        return 0.0
    if count_parts(shapely.buffer(shape_km, most_km, quad_segs=4)) > 1:
        return most_km
    lo, hi = 0.0, most_km
    while hi - lo > 0.25:
        mid = (lo + hi) / 2
        if count_parts(shapely.buffer(shape_km, mid, quad_segs=4)) > 1:
            lo = mid
        else:
            hi = mid
    return hi


class LandParts:
    """The land layer's areas in parts, each a whole area of land, such as an island, or a mainland cut at a
    border: a part crossing a group's outline is cut away, a part wholly inside it stays."""

    def __init__(self, geoms):
        parts = [p for g in geoms if g is not None for p in shapely.get_parts(polygonal(g) or shapely.Polygon())
                 if not p.is_empty]
        self.parts = np.array(parts, dtype=object)
        self.tree = shapely.STRtree(self.parts)

    def crossing(self, outline) -> list:
        """The parts that cross the outline's edge, cut to a box a little larger than the outline."""
        idx = self.tree.query(outline, predicate="intersects")
        if not len(idx):
            return []
        x0, y0, x1, y1 = outline.bounds
        shapely.prepare(outline)
        out = []
        for i in idx.tolist():
            p = self.parts[i]
            px0, py0, px1, py1 = p.bounds
            if px0 >= x0 and py0 >= y0 and px1 <= x1 and py1 <= y1 and outline.contains(p):
                continue   # wholly inside: it stays, as an island the sources forgot
            out.append(shapely.clip_by_rect(p, x0 - 0.01, y0 - 0.01, x1 + 0.01, y1 + 0.01))
        return [g for g in out if not g.is_empty]


def outline(members: list, land: LandParts, s: dict, box=None):
    """A group's outline from its member islands (see the module's notes), with its reach; None when nothing is
    left. members are the islands' shapes in degrees."""
    frame = Frame(shapely.total_bounds(np.array(members, dtype=object)))
    joined = shapely.union_all([shapely.simplify(frame.to_km(g), 0.25, preserve_topology=True) for g in members])
    most = float(s["most_reach_km"])
    reach = joining_reach(shapely.simplify(joined, 1.0, preserve_topology=True), most / 2)
    grow = min(most, max(float(s["least_reach_km"]), 2 * reach))
    edge = float(s["edge_km"])
    closed = shapely.buffer(shapely.buffer(joined, grow, quad_segs=8), -(grow - edge), quad_segs=8)
    closed = shapely.simplify(closed, float(s["tolerance_m"]) / 1000.0, preserve_topology=True)
    g = frame.to_degrees(closed)
    if g is None:
        return None, reach
    g = polygonal(shapely.set_precision(g, 1e-7))
    if g is None:
        return None, reach
    other = land.crossing(g)
    if other:
        cut = shapely.union_all(other)
        arr = np.array(members, dtype=object)
        hit = arr[shapely.intersects(arr, cut)]
        if len(hit):   # a member island that is part of a land part crossing the edge, as one joined by a causeway
            cut = shapely.difference(cut, shapely.union_all(hit))
        g = polygonal(shapely.difference(g, cut))
    if g is not None and box:
        g = polygonal(shapely.clip_by_rect(g, *box))
    if g is None:
        return None, reach
    points = shapely.point_on_surface(np.array(members, dtype=object))
    kept = [p for p in shapely.get_parts(g) if shapely.intersects(p, points).any()]
    if not kept:
        return None, reach
    g = kept[0] if len(kept) == 1 else shapely.MultiPolygon(kept)
    return polygonal(shapely.set_precision(g, 1e-7)), reach


# Which islands belong ------------------------------------------------------------------------------------------

class Islands:
    """The islands layer: each island's shape, its point, its land in square kilometres, and an index of the
    points."""

    def __init__(self, records: list[dict], geoms: list):
        self.records = records
        self.geoms = np.array(geoms, dtype=object)
        self.points = shapely.point_on_surface(self.geoms) if len(geoms) else np.array([], dtype=object)
        self.xy = shapely.get_coordinates(self.points) if len(geoms) else np.zeros((0, 2))
        self.km2 = np.array([rough_km2(g) for g in geoms])
        self.tree = shapely.STRtree(self.points)
        self.by_id = {r["id"]: i for i, r in enumerate(records)}
        self.by_wikidata: dict[str, list[int]] = {}
        for i, r in enumerate(records):
            if r.get("wikidata"):
                self.by_wikidata.setdefault(r["wikidata"], []).append(i)

    def inside(self, shape, near_deg: float = 0.0) -> set[int]:
        if shape is None or shape.is_empty:
            return set()
        x0, y0, x1, y1 = shape.bounds
        idx = self.tree.query(shapely.box(x0 - near_deg, y0 - near_deg, x1 + near_deg, y1 + near_deg))
        if not len(idx):
            return set()
        shapely.prepare(shape)
        hit = shapely.contains_xy(shape, self.xy[idx, 0], self.xy[idx, 1])
        rest = idx[~hit]
        found = set(idx[hit].tolist())
        if near_deg and len(rest):
            found |= set(rest[shapely.dwithin(shape, self.points[rest], near_deg)].tolist())
        return found


def _key(name) -> str:
    return " ".join(str(name or "").lower().split())


def make_groups(osm: list[tuple[dict, object]], islands: Islands, land: LandParts, areas: dict[str, object],
                ne: list[tuple[dict, object]], links: dict[str, dict], record: dict, countries: set[str], s: dict,
                say=print, box=None) -> tuple[list[dict], list, list[str]]:
    """The groups of islands as records and outlines, in id order, with the lines for the build's log."""
    s = {**DEFAULTS, **s}
    if box is None:
        box = s.get("box")
    near = float(s["near_m"]) / 111_320.0
    log: list[str] = []
    leave = set(record["leave_out"])
    groups: dict[str, dict] = {}   # id: {"rec", "own": set of island indexes, "inner": set of group ids}

    # 1. OpenStreetMap's groups.
    left_types: dict[str, int] = {}
    for r, g in osm:
        if r["relation"] not in KEPT_RELATIONS and r["relation"] != "way":
            left_types[r["relation"] or "none"] = left_types.get(r["relation"] or "none", 0) + 1
            continue
        if r["id"] in leave:
            log.append(f"Left out, as the record says: {r.get('name_en') or r.get('name') or r['id']} ({r['id']}).")
            continue
        own = islands.inside(g, near) if g is not None and not g.is_empty else set()
        own |= {islands.by_id[m] for m in r.get("members") or [] if m in islands.by_id}
        groups[r["id"]] = {"rec": r, "own": own, "inner": {m for m in r.get("members") or []},
                           "wikidata": record["links"].get(r["id"]) or r.get("wikidata") or ""}
    for kind, n in sorted(left_types.items()):
        log.append(f"Left out: {n:,} relations of type {kind}, not a group of islands.")
    for gid, g in groups.items():
        g["inner"] = {m for m in g["inner"] if m in groups and m != gid}

    # 3. Our own record's groups.
    for c in record["groups"]:
        own: set[int] = set()
        if c.get("islands_in"):
            area = areas.get(str(c["islands_in"]))
            if area is None:
                log.append(f"{c['name']}: the area {c['islands_in']} is not in this pack, so it gives no islands.")
            own |= islands.inside(area, near)
        if c.get("natural_earth"):
            for r, g in ne:
                if _key(r["name"]) == _key(c["natural_earth"]):
                    own |= islands.inside(g, near)
        for q in c.get("islands") or []:
            own |= set(islands.by_wikidata.get(str(q), []))
        groups[str(c["id"])] = {"rec": {"id": str(c["id"]), "name": str(c["name"]), "relation": "record"},
                                "own": own, "inner": {str(m) for m in c.get("groups") or [] if str(m) in groups},
                                "wikidata": str(c.get("wikidata") or ""), "record": True}

    # 2. Groups inside groups, through Wikidata's links between their items.
    by_q: dict[str, list[str]] = {}
    for gid, g in groups.items():
        if g["wikidata"]:
            by_q.setdefault(g["wikidata"], []).append(gid)
    joined = 0
    for gid, g in groups.items():
        q = g["wikidata"]
        if not q:
            continue
        entry = links.get(q) or {}
        inner = {i for p in entry.get("parts") or [] for i in by_q.get(p, [])}
        outer = {i for p in entry.get("part_of") or [] for i in by_q.get(p, [])}
        for i in inner - {gid} - g["inner"]:
            g["inner"].add(i)
            joined += 1
        for o in outer - {gid}:
            if gid not in groups[o]["inner"]:
                groups[o]["inner"].add(gid)
                joined += 1
    if joined:
        log.append(f"Groups inside groups found through Wikidata: {joined:,}.")

    # 4. Natural Earth's groups that no group above has, as lists of islands.
    known_q = set(by_q)
    known_names = {_key(v) for g in groups.values() for v in (g["rec"].get("name"), g["rec"].get("name_en"),
                                                             record["names"].get(g["rec"]["id"])) if v}
    used_ne = {_key(c["natural_earth"]) for c in record["groups"] if c.get("natural_earth")}
    keep_ne = {_key(n) for n in record["natural_earth_keep"]}
    country_names = {_key(n) for n in countries}
    for r, g in ne:
        k = _key(r["name"])
        if (r.get("wikidata") and r["wikidata"] in known_q) or k in known_names or _key(r.get("local_name")) in \
                known_names or k in used_ne:
            continue
        own = islands.inside(g, near)
        if not own:
            continue
        km2 = islands.km2[sorted(own)]
        if k not in keep_ne:
            if k in country_names:
                log.append(f"Left out, Natural Earth's group {r['name']}: it has a country's name.")
                continue
            if km2.sum() > 0 and km2.max() > float(s["one_island_share"]) * km2.sum():
                log.append(f"Left out, Natural Earth's group {r['name']}: its largest island holds "
                           f"{100 * km2.max() / km2.sum():.0f} percent of its land.")
                continue
        gid = r["id"].replace("ne:region:", "ne:")
        groups[gid] = {"rec": {"id": gid, "name": r["name"], "relation": "natural earth"}, "own": own,
                       "inner": set(), "wikidata": r.get("wikidata") or ""}
        if r.get("local_name"):
            groups[gid]["rec"]["local"] = r["local_name"]

    # Every member, with the members of the groups inside, however deep.
    def all_members(gid, seen=()):
        g = groups[gid]
        out = set(g["own"])
        for i in sorted(g["inner"]):
            if i not in seen and i != gid:
                out |= all_members(i, (*seen, gid))
        return out

    members = {gid: all_members(gid) for gid in groups}

    # Two groups with one Wikidata item are one: the one with the most islands, then the first by id, takes both.
    for q, ids in sorted(by_q.items()):
        ids = [i for i in ids if i in groups]
        if len(ids) < 2:
            continue
        ids.sort(key=lambda i: (-len(members[i]), i))
        for other in ids[1:]:
            members[ids[0]] |= members.pop(other)
            log.append(f"{groups[other]['rec'].get('name') or other} ({other}) is the same Wikidata item, {q}, as "
                       f"{ids[0]}: one group.")
            del groups[other]

    records, geoms = [], []
    small = 0
    for gid in sorted(groups):
        g = groups[gid]
        m = sorted(members[gid])
        land_km2 = float(islands.km2[m].sum()) if m else 0.0
        if len(m) < int(s["min_islands"]) or land_km2 < float(s["min_land_km2"]):
            small += 1
            continue
        shape, reach = outline([islands.geoms[i] for i in m], land, s, box)
        if shape is None:
            log.append(f"{gid}: no outline left.")
            continue
        r = g["rec"]
        if r["relation"] in ("record", "natural earth"):
            local = r.get("local")
            name = record["names"].get(gid) or r.get("name")
        else:   # OpenStreetMap's: its English name, then Wikidata's English label, then its own name
            local = r.get("name")
            label = (links.get(g["wikidata"]) or {}).get("label") if g["wikidata"] else ""
            name = record["names"].get(gid) or r.get("name_en") or label or r.get("name")
        if not name:
            log.append(f"{gid}: no name, left out.")
            continue
        rec = {"id": ID_PREFIX + gid, "layer": s["layer"], "name": name, "type": TYPE}
        if local and local != name:
            rec["local_name"] = local
        if g["wikidata"]:
            rec["wikidata"] = g["wikidata"]
        records.append(rec)
        geoms.append(shape)
        log.append(f"{name} ({gid}): {len(m):,} islands, {land_km2:,.0f} km2 of land, reach {reach:.1f} km, "
                   f"{rough_km2(shape):,.0f} km2 in all, {count_parts(shape):,} parts, "
                   f"{shapely.get_num_coordinates(shape):,} points.")
    log.append(f"Groups too small to keep, with fewer than {int(s['min_islands'])} islands or under "
               f"{float(s['min_land_km2']):g} km2 of land: {small:,}.")
    return records, geoms, log


# The stage ------------------------------------------------------------------------------------------------------

def run(ctx) -> None:
    s = {**DEFAULTS, **ctx.settings}
    t0 = time.perf_counter()
    layer = s.setdefault("layer", "island-groups")
    if layer not in ctx.pack.layers:
        raise BuildStopped(f"The island-groups stage writes to the layer {layer}, which the pack's layer groups do "
                           "not define. Add the layer, or correct the stage's settings.")
    islands_layer = s.get("islands_layer", "islands")
    land_layer = s.get("land_layer", "countries")
    area_layers = set(s.get("area_layers") or ["regions"])
    record = load_record(record_path(s))
    records, geoms = features.load_layers(ctx.previous, {islands_layer, land_layer, *area_layers})
    isl = [(r, g) for r, g in zip(records, geoms) if r["layer"] == islands_layer]
    if not isl:
        raise BuildStopped(f"The island-groups stage makes the groups from the islands of the layer {islands_layer}, "
                           "which the stage before has none of. Put the stage after the join stage, or correct its "
                           "islands_layer setting.")
    islands = Islands([r for r, _g in isl], [g for _r, g in isl])
    land = LandParts([g for r, g in zip(records, geoms) if r["layer"] == land_layer])
    countries = {r["name"] for r in records if r["layer"] == land_layer}
    areas = {r["id"]: g for r, g in zip(records, geoms) if r["layer"] in area_layers}
    del records, geoms, isl
    ctx.progress.line(f"{len(islands.records):,} islands and {len(land.parts):,} parts of land made ready in "
                      f"{time.perf_counter() - t0:.0f} seconds.")
    _src, gol = ctx.source(s.get("source", "planet"))
    o_records, o_geoms = read_planet(ctx, gol)
    box = s.get("box")
    ne: list = []
    if s.get("natural_earth"):
        _src, path = ctx.source(s["natural_earth"])
        n_records, n_geoms = natural_earth_regions(path, box, {NE_CLASS: TYPE})
        ne = list(zip(n_records, n_geoms))
    links: dict[str, dict] = {}
    if s.get("wikidata"):
        if not s.get("refresh"):
            raise BuildStopped("The island-groups stage needs a refresh label for the links between groups, such "
                               "as refresh: 2026-11.")
        from mapdata.stages.wikidata import append_file, qid_order, read_file, valid_qid

        path = links_path(ctx.source(s["wikidata"])[1], s["refresh"])
        links = read_file(path)
        wanted = {r.get("wikidata") for r in o_records} | set(record["links"].values()) | \
            {str(c.get("wikidata")) for c in record["groups"] if c.get("wikidata")}
        missing = sorted((q for q in wanted if valid_qid(q) and q not in links), key=qid_order)
        if missing and not s.get("offline"):
            ctx.progress.line(f"Fetching the links between {len(missing):,} groups from Wikidata; the rest were "
                              f"fetched before and kept in {path}.")
            links.update(fetch_links(missing, say=ctx.progress.log, keep=lambda e: append_file(ctx.claim(path), e)))
        elif missing:
            ctx.progress.line(f"{len(missing):,} groups' links are not in {path}, and the stage is offline: they "
                              "have none.")
    new_records, new_geoms, log = make_groups(list(zip(o_records, o_geoms)), islands, land, areas, ne, links,
                                              record, countries, s, box=box)
    for line in log:
        ctx.progress.log(line)
    for name in ("features.json", "shapes.wkb"):
        shutil.copyfile(ctx.previous / name, ctx.claim(ctx.folder / name))
    features.append(ctx.folder, new_records, [shapely.to_wkb(g) for g in new_geoms])
    points = sum(int(shapely.get_num_coordinates(g)) for g in new_geoms)
    ctx.progress.line(f"Groups of islands: {len(new_records):,} groups, {points:,} points, from {len(o_records):,} "
                      f"read from OpenStreetMap, {len(record['groups']):,} in the record and {len(ne):,} from "
                      f"Natural Earth. {log[-1]} In {time.perf_counter() - t0:.0f} seconds.")


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
