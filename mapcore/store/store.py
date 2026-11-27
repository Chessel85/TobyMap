"""The store over the installed packs: "where am I" and Nearby (P1-T5).

* at(lat, lon): every area at a point, from every layer, whatever the zoom
  (ANN-7), most specific first: by rank (a higher rank is more specific, such
  as a county above a country), then smallest area first (LOC-2).
* nearby(lat, lon, radius_m): the areas within a radius, each with its
  nearest point, and the distance and bearing to it (INF-3, INF-7).
* feature(id): a feature record by its identifier.

Several packs may be open together (P4-T3a, AD-14, mapcore/store/packs_combined.py): regional packs first,
the finest coverage first, then the world pack. Inside a regional pack's covered pack tiles it answers for its
layers, and the world pack's features of those layers are left out there, for where am I, Nearby, the places
near a point, and Crossed and passed. Elsewhere, and for every other layer, the world pack answers, and nothing
is said about missing detail (PLT-4). A feature both packs hold, by the same identifier, is given once.

A feature both packs hold is one feature (P4-T3b): feature(), relationships() and every Area the store gives
merge its records, the whole feature's record first (mapcore/store/packs_combined.py), so Within, Contains and
Bordering give one Hampshire, and a parish only the regional pack holds sits under the world pack's county. An
identifier a regional feature had before matching, kept as an alias, finds it too.

A damaged record is noted in `problems` and the store carries on without it
(NFR-4).

Exact shapes are used for an area up to NEAR_EXACT_M away. Further away the
simplified drawing shapes are used when the pack has them, because a few
hundred metres of difference matters little against a distance of hundreds of
kilometres. An area the drawing shapes left out for being small uses its exact
shapes within the search box.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field, replace

import numpy as np

from mapcore import memory
from mapcore import names as names_mod
from mapcore import search
from mapcore.describe import say
from mapcore.geo import geodesy
from mapcore.packs import tiles
from mapcore.packs.pack import DamagedRecord, Pack
from mapcore.store import contents
from mapcore.store.packs_combined import coverage_of, detail_order, merge_records, merge_relationships
from mapcore.store.contents import TREE_LAYERS, special_kind  # noqa: F401 (special_kind is used by the session)
from mapcore.store.cache import TileCache, TileData
from mapcore.store.projection import Flat

NEAR_EXACT_M = 50_000.0
DRAWN_SHARE = 0.02   # nearest_many reads the coarsest drawing level whose tolerance is at most this share of the distance
VIEW_SHARE = 0.1     # ... or of this share of the view's radius, whichever is more
FIRST_SEARCH_M = 2_000.0   # the first search box for an area's nearest point
SEARCH_GROWTH = 3.0
PART_SKIP_MARGIN = 1.1   # a part whose box is a tenth further than the best point found is not measured
M_PER_DEG_LAT_MIN = 110_574.0  # the shortest degree of latitude, at the equator
JOIN_M = 100.0   # parts of a shared border whose ends are closer than this are one border (P3-T32c)
PARTED_M = 100.0   # an unnamed island bigger land comes this close to is barely parted from it (P3-T32e)
MAINLAND_KM2 = 1.0   # land with no island, this big within MAINLAND_M of the gap, is a continent's (P3-T32e, DP169)
MAINLAND_M = 1_500.0
MERGED_KEPT = 4096   # the merged relationships kept, the oldest let go first (P4-T3b)


@dataclass(frozen=True)
class Area:
    """A feature at a point, with its record (docs/developer/pack-format.md)."""
    pack: int
    number: int
    record: dict
    naming: names_mod.Naming = field(default=names_mod.DEFAULT, compare=False, repr=False)   # the store's (P3-T12a)

    @property
    def id(self) -> str:
        return self.record["id"]

    @property
    def layer(self) -> str:
        return self.record["layer"]

    @property
    def rank(self) -> int:
        return self.record["rank"]

    @property
    def area_km2(self) -> float:
        return self.record["area_km2"]

    @property
    def names(self) -> dict:
        return self.record["names"]

    @property
    def name(self) -> names_mod.Name:
        """The name the Names setting chooses, with its language (P3-T12, mapcore.names)."""
        return self.naming.name_of(self.record)


@dataclass(frozen=True)
class Near:
    """An area near the location: its nearest point, and the distance and
    bearing to it, measured on the ellipsoid. An area the location is inside
    has distance 0, the location as its nearest point, bearing 0 (there
    is no direction to take) and inside True."""
    area: Area
    distance_m: float
    bearing_deg: float
    lat: float
    lon: float
    inside: bool


@dataclass(frozen=True)
class Crossing:
    """A line feature a path crosses (P2-T10a, for Crossed and passed, ANN-2): where
    it is first crossed, and how far along the path that is, measured roughly on
    the mean sphere, which is enough to put the crossings in order."""
    area: Area
    lat: float
    lon: float
    along_m: float


def path_pieces(path) -> list[np.ndarray]:
    """A move's path, (lat, lon) points whose longitudes carry on past the 180 degree
    line, as (lon, lat) arrays that each stay within -180 to 180 degrees.

    Between two points more than 90 degrees of longitude apart the path went over
    a pole, so it is cut there, each side running to the pole on its own meridian.
    """
    import shapely

    pts = np.asarray(path, dtype=np.float64).reshape(-1, 2)[:, ::-1].tolist()
    if len(pts) < 2:
        return []
    runs, current = [], [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        if abs(b[0] - a[0]) > 90.0:
            pole = 90.0 if a[1] + b[1] > 0 else -90.0
            current.append([a[0], pole])
            runs.append(current)
            current = [[b[0], pole], b]
        else:
            current.append(b)
    runs.append(current)
    out = []
    for run in (np.asarray(r) for r in runs):
        if len(run) < 2:
            continue
        line = shapely.LineString(run)
        low, high = math.floor((run[:, 0].min() + 180.0) / 360.0), math.floor((run[:, 0].max() + 180.0) / 360.0)
        for k in range(int(low), int(high) + 1):
            piece = shapely.clip_by_rect(line, -180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
            for part in shapely.get_parts(shapely.line_merge(piece) if piece.geom_type == "MultiLineString" else piece):
                c = shapely.get_coordinates(part)
                if len(c) >= 2:
                    c[:, 0] -= 360.0 * k
                    out.append(c)
    return out


@dataclass(frozen=True)
class Found:
    """A search result (P3-T8b): the feature's identifier, English name, layer and importance, its point, the
    description that tells it apart, the name it was found by when not the English (via, else ""), and how
    well it matched (mapcore.search: level and similarity)."""
    pack: int
    id: str
    name: str
    layer: str
    importance: int
    lat: float | None
    lon: float | None
    description: str
    via: str
    level: int
    similarity: float


def _boxes_meet(a, b) -> bool:
    """Whether two boxes (west, south, east, north) share any ground; west greater than east is a box across
    the 180 degree line (AD-17)."""
    if a[3] < b[1] or b[3] < a[1]:
        return False

    def spans(box):
        return [(box[0], box[2])] if box[0] <= box[2] else [(box[0], 180.0), (-180.0, box[2])]

    return any(x0 <= y1 and y0 <= x1 for x0, x1 in spans(a) for y0, y1 in spans(b))


def _grown_boxes(bbox, metres: float) -> list[tuple[float, float, float, float]]:
    """A feature's box (west, south, east, north; west greater than east across the 180 degree line) grown by
    `metres` on every side, as boxes that do not cross the 180 degree line (P3-T10a). Near a pole, or grown
    past half the world, it reaches every longitude."""
    west, south, east, north = bbox
    dlat = metres / M_PER_DEG_LAT_MIN
    s, n = max(-90.0, south - dlat), min(90.0, north + dlat)
    worst = math.cos(math.radians(min(89.9, max(abs(s), abs(n)))))
    dlon = math.degrees(metres / (geodesy.A_M * worst)) if worst > 1e-6 else 360.0
    width = (east - west) % 360.0 if west > east else east - west
    if max(abs(s), abs(n)) >= 89.0 or width + 2 * dlon >= 360.0:
        return [(-180.0, s, 180.0, n)]
    return [(w, s, e, n) for w, e in _intervals(geodesy.wrap_lon(west - dlon), geodesy.wrap_lon(east + dlon))]


def _boxes_reach(boxes: np.ndarray, reach) -> np.ndarray:
    """For an array of boxes (west, south, east, north, west greater than east across the 180 degree line),
    whether each meets any of the boxes in `reach`, none of which crosses the 180 degree line."""
    west, south, east, north = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    crosses = west > east
    out = np.zeros(len(boxes), dtype=bool)
    for w, s, e, n in reach:
        lat_ok = (south <= n) & (north >= s)
        plain = (west <= e) & (east >= w)
        across = (w <= east) | (e >= west)   # the box is [west, 180] and [-180, east]
        out |= lat_ok & np.where(crosses, across, plain)
    return out


def _meet_boxes(box, own) -> list[tuple[float, float, float, float]]:
    """Where a box that does not cross the 180 degree line meets a feature's own box, which may."""
    w, s, e, n = box
    s, n = max(s, own[1]), min(n, own[3])
    if s > n:
        return []
    return [(a, s, b, n) for a, b in _meet([(w, e)], _intervals(own[0], own[2]))]


def _in_box(lat: float, lon: float, box) -> bool:
    west, south, east, north = box
    if not south <= lat <= north:
        return False
    return west <= lon <= east if west <= east else (lon >= west or lon <= east)


def _within(row: list, near: tuple[float, float, float]) -> bool:
    """Whether a search row's point is within near's distance of near's point, on the mean sphere, which is
    close enough to narrow a search (SRB-2)."""
    lat, lon = row[search.LAT], row[search.LON]
    if lat is None:
        return False
    plat, plon, metres = near
    return search.sphere_m(plat, plon, lat, row[search.LON]) <= metres


@dataclass(frozen=True)
class Passed:
    """Something a move went over or near (P2-T5, ANN-2, architecture 7.5): a line it
    crossed ("crossed"), an area it entered and left with neither end in it ("passed
    over"), or a point within the passed nearby distance of the path ("passed"). lat
    and lon are where: the crossing, the last point of the path in the area, or the
    point itself. closest_m is the least distance from the path; along_m how far along
    the path that is, which puts the list in order."""
    area: Area
    kind: str
    lat: float
    lon: float
    closest_m: float
    along_m: float


class Cancelled(Exception):
    """A search along a path was given up, because a newer move made it out of date."""


def _along_m(path, lat: float, lon: float) -> float:
    """How far along the path, in metres on the mean sphere, its nearest point to (lat, lon) is."""
    return _closest_m(path, lat, lon)[1]


def _closest_m(path, lat: float, lon: float) -> tuple[float, float]:
    """How far (lat, lon) is from the path, and how far along the path its nearest point is,
    in metres on the mean sphere. Exact enough for the short distances it is used for."""
    p = np.radians(np.asarray(path, dtype=np.float64).reshape(-1, 2))
    lat1, lon1, lat2, lon2 = p[:-1, 0], p[:-1, 1], p[1:, 0], p[1:, 1]
    seg = 2 * np.arcsin(np.sqrt(np.sin((lat2 - lat1) / 2) ** 2
                                + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2))
    # Each segment in a flat view round the point (x east, y north, in radians of the
    # sphere), and the nearest point of each to it.
    q_lat, q_lon = math.radians(lat), math.radians(lon)
    x = ((p[:, 1] - q_lon + math.pi) % (2 * math.pi) - math.pi) * math.cos(q_lat)
    y = p[:, 0] - q_lat
    ax, ay, dx, dy = x[:-1], y[:-1], np.diff(x), np.diff(y)
    length2 = dx * dx + dy * dy
    t = np.clip(-(ax * dx + ay * dy) / np.where(length2 > 0, length2, 1.0), 0.0, 1.0)
    d = np.hypot(ax + t * dx, ay + t * dy)
    k = int(np.argmin(d))
    return float(d[k]) * geodesy.R_MEAN_M, float(seg[:k].sum() + t[k] * seg[k]) * geodesy.R_MEAN_M


def most_specific_first(areas, tiers: list[str] = ()) -> list[Area]:
    """Areas in the order "where am I" says them (LOC-2): by rank, higher first; then by tier, lower first,
    so where two tiers share a rank, a county comes before a region, and a region before a constituent
    country (P3-T17); then the smallest. An area with no tier comes after those with one."""
    place = {t: n for n, t in enumerate(tiers)}

    def tier_key(a: Area) -> int:
        n = place.get(a.record.get("tier"))
        return 1 if n is None else -n   # the lowest tier first, then the higher, then no tier

    return sorted(areas, key=lambda a: (-a.rank, tier_key(a), a.area_km2, a.id))


def _intervals(west: float, east: float) -> list[tuple[float, float]]:
    """A span of longitude, possibly across the 180 degree line, as spans that do not."""
    if west <= east:
        return [(west, east)]
    return [(west, 180.0), (-180.0, east)]


def _meet(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for w1, e1 in a:
        for w2, e2 in b:
            w, e = max(w1, w2), min(e1, e2)
            if w <= e:
                out.append((w, e))
    return out


def _ends_apart_m(p, q) -> np.ndarray:
    """Metres between points in longitude and latitude, near enough for a few hundred metres."""
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    dx = (p[..., 0] - q[..., 0] + 180.0) % 360.0 - 180.0
    dx = dx * np.cos(np.radians((p[..., 1] + q[..., 1]) / 2.0)) * 111_320.0
    dy = (p[..., 1] - q[..., 1]) * M_PER_DEG_LAT_MIN
    return np.hypot(dx, dy)


def join_parts(lines: list, metres: float = JOIN_M) -> list:
    """Parts of one shared border joined where their ends meet (P3-T32c): two areas' outlines can miss each other
    by a metre or so, which leaves the border in parts, and the ends where they meet are not ends. The closest
    pair of ends under `metres` apart is joined first, until none is left; then a line whose own two ends meet,
    and that is longer than the gap many times over, is closed into a ring. Lines in longitude and latitude."""
    import shapely

    rings = [g for g in lines if shapely.is_closed(g)]
    parts = [shapely.get_coordinates(g) for g in lines if not shapely.is_closed(g)]
    parts = [c for c in parts if len(c) >= 2]
    while len(parts) > 1:
        ends = np.array([[c[0], c[-1]] for c in parts])   # part, which end, (lon, lat)
        flat = ends.reshape(-1, 2)
        apart = _ends_apart_m(flat[:, None, :], flat[None, :, :])
        owner = np.repeat(np.arange(len(parts), dtype=np.intp), 2)
        apart[owner[:, None] == owner[None, :]] = np.inf
        k = int(np.argmin(apart))
        i, j = divmod(k, len(flat))
        if apart[i, j] >= metres:
            break
        (pi, ei), (pj, ej) = divmod(i, 2), divmod(j, 2)
        a = parts[pi] if ei == 1 else parts[pi][::-1]   # runs to the meeting end
        b = parts[pj] if ej == 0 else parts[pj][::-1]   # runs from it
        if np.array_equal(a[-1], b[0]):
            b = b[1:]
        parts = [c for n, c in enumerate(parts) if n not in (pi, pj)] + [np.concatenate([a, b])]
    out = list(rings)
    for c in parts:
        length = float(_ends_apart_m(c[:-1], c[1:]).sum())
        if len(c) >= 3 and _ends_apart_m(c[0], c[-1]) < metres and length > 10.0 * metres:
            c = np.concatenate([c, c[:1]])
        out.append(shapely.LineString(c))
    return out


def _first_by_id(found, last: bool = False) -> list:
    """Crossings or passings, one for each feature by its identifier, though two packs hold it (P4-T3a): the
    first along the path, or with last the last (where the path leaves an area)."""
    best: dict = {}
    for c in found:
        old = best.get(c.area.id)
        if old is None or (c.along_m > old.along_m if last else c.along_m < old.along_m):
            best[c.area.id] = c
    return list(best.values())


class _PackIndex:
    """What the store keeps about one pack: its features' boxes, and which pack tiles exist."""

    def __init__(self, pack: Pack, problems):
        self.pack = pack
        self.problems = problems
        self._boxes = None
        self._sizes = None
        self._ids = None
        self._layer_by_id = None
        self._layer_by_number = None
        self._aliases: dict[str, str] | None = None
        self._points: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._tile_index: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
        by_kind: dict[tuple[str, int], list[tuple[int, int]]] = {}
        for key in pack.keys():
            parts = key.split("/")
            if parts[0] in ("tile", "draw") and len(parts) == 4:
                by_kind.setdefault((parts[0], int(parts[1])), []).append((int(parts[2]), int(parts[3])))
        for k, xy in by_kind.items():
            arr = np.array(xy, dtype=np.intp).reshape(-1, 2)
            self._tile_index[k] = (arr[:, 0], arr[:, 1])
        levels = sorted(pack.drawing_levels.values(), key=lambda d: d.get("view_km", 0))
        self.finest_drawing = levels[0] if levels else None
        self._stored_sets: dict[tuple[str, int], set] = {}

    def stored(self, kind: str, level: int) -> set:
        """The (x, y) of the pack tiles ("tile") or drawing tiles ("draw") that exist at a level."""
        key = (kind, level)
        if key not in self._stored_sets:
            found = self._tile_index.get(key)
            self._stored_sets[key] = set() if found is None else set(zip(found[0].tolist(), found[1].tolist()))
        return self._stored_sets[key]

    @property
    def boxes(self):
        """Arrays of the features' numbers and boxes: west, south, east, north."""
        if self._boxes is None:
            self._read_table()
        return self._boxes

    @property
    def sizes(self):
        """In the order of `boxes`: each feature's width in kilometres (infinity where the
        record has none) and its layer id, for the visible rule (P2-T4a)."""
        if self._boxes is None:
            self._read_table()
        return self._sizes

    @property
    def ids(self):
        """In the order of `boxes`: each feature's identifier."""
        if self._boxes is None:
            self._read_table()
        return self._ids

    @property
    def layer_by_id(self) -> dict:
        """Each feature's layer by its identifier, from the feature table, so a list of identifiers can be
        narrowed to a layer without reading their records (P3-T10a)."""
        if self._layer_by_id is None:
            self._layer_by_id = dict(zip(self.ids.tolist(), self.sizes[1].tolist()))
        return self._layer_by_id

    @property
    def aliases(self) -> dict:
        """Each alias in the pack's feature records, with the identifier it stands for (P4-T3b)."""
        if self._aliases is None:
            self._read_table()
        return self._aliases

    def layer_of_number(self, number: int) -> str:
        """A feature's layer by its number, from the feature table, with no record read (P4-T3a)."""
        if self._layer_by_number is None:
            numbers, _boxes = self.boxes
            self._layer_by_number = dict(zip(numbers.tolist(), self.sizes[1].tolist()))
        return self._layer_by_number.get(number, "")

    def _read_table(self) -> None:
        numbers, box, widths, layer_of, ids = [], [], [], [], []
        aliases: dict[str, str] = {}
        for g, start in enumerate(self.pack.group_starts):
            try:
                group = self.pack._group(g)
            except DamagedRecord as exc:
                self.problems.append(exc.message)
                continue
            for i, record in enumerate(group):
                numbers.append(start + i)
                box.append(record["bbox"])
                width = record.get("width_km")
                widths.append(math.inf if width is None else float(width))
                layer_of.append(record.get("layer", ""))
                ids.append(record.get("id"))
                for alias in record.get("aliases") or ():   # only a regional pack's matched features have them
                    aliases.setdefault(alias, record.get("id"))
        self._aliases = aliases
        self._ids = np.array(ids, dtype=object)
        self._sizes = (np.array(widths, dtype=np.float64), np.array(layer_of, dtype=object))
        self._boxes = (np.array(numbers, dtype=np.intp), np.array(box, dtype=np.float64).reshape(-1, 4))

    def points_of(self, layer: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The features of a layer that are one point: their numbers, latitudes and longitudes, worked out once
        from the feature table (P3-T28p)."""
        if layer not in self._points:
            numbers, boxes = self.boxes
            keep = (self.sizes[1] == layer) & (boxes[:, 0] == boxes[:, 2]) & (boxes[:, 1] == boxes[:, 3])
            self._points[layer] = (numbers[keep], boxes[keep, 1].copy(), boxes[keep, 0].copy())
        return self._points[layer]

    def tiles_in(self, kind: str, level: int, x0: int, x1: int, y0: int, y1: int):
        """The (x, y) of stored tiles at a level within the ranges, both ends included."""
        found = self._tile_index.get((kind, level))
        if found is None:
            return []
        xs, ys = found
        keep = (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)
        return list(zip(xs[keep].tolist(), ys[keep].tolist()))


class Store:
    """Questions about the places in the installed packs.

    `packs` are Pack objects or paths. Questions may come from any thread.
    """

    def __init__(self, packs, cache_bytes: int | None = None):
        self.problems: list[str] = []
        self.cache = TileCache(cache_bytes) if cache_bytes else TileCache()
        self._indexes: list[_PackIndex] = []
        self._lock = threading.RLock()
        # The world tree (P3-T9a): each branch's members, and their records for their names.
        self._tree_children: dict[str, set] | None = None
        self._tree_rows: dict[str, dict] = {}
        # Which name is said and shown (P3-T12a), shared with every Area this store makes.
        self.naming = names_mod.Naming()
        # A tile's shapes are shared and prepared, and Shapely builds a prepared shape's index on
        # its first use, which is not safe from two threads at once: the Crossed and passed
        # search and a step's lookup together made Windows stop the program (P2-T17w). Every
        # use of a tile's shape is under this lock, one shape test at a time, so a step never
        # waits for a whole search.
        self._shapes = threading.Lock()
        self._parted: dict[str, bool] = {}   # barely_parted's answers, by island
        # water_islands' answers, by water: (the islands in it by their shore, how many of them the stored "held"
        # leaves out, and how many the stored "counts" leaves out) (P3-T32g)
        self._isles: dict[str, tuple[list[str], int, int]] = {}
        opened = [p if isinstance(p, Pack) else Pack(p)
                  for p in (packs if isinstance(packs, (list, tuple)) else [packs])]
        # The most detailed first (P4-T3a): regional packs, the finest coverage first, then the world pack.
        for k in detail_order(opened):
            self._indexes.append(_PackIndex(opened[k], self.problems))
        self._coverages = [coverage_of(i.pack) for i in self._indexes]
        world = [p for p, cov in enumerate(self._coverages) if cov is None]
        self._world = world[0] if world else None   # the world pack that answers where no regional pack does
        # Each layer's packs, so a feature of a layer only one pack holds is never looked for in another (P4-T3b).
        self._layer_packs: dict[str, list[int]] = {}
        for p, index in enumerate(self._indexes):
            for layer in (index.pack.manifest or {}).get("layers") or ():
                self._layer_packs.setdefault(layer, []).append(p)
        # A feature several packs hold: its merged record, by id; and the merged relationships given, by id.
        self._merged: dict[str, tuple] = {}
        self._merged_rel: dict[str, dict] = {}

    @property
    def packs(self) -> list[Pack]:
        return [i.pack for i in self._indexes]

    def close(self) -> None:
        for i in self._indexes:
            i.pack.close()

    def set_names(self, choice: str) -> None:
        """Which name is said and shown: "english" or "local" (P3-T12a). Every Area this store made follows it."""
        self.naming.choice = choice if choice in names_mod.CHOICES else names_mod.ENGLISH

    def _name(self, rec: dict) -> names_mod.Name:
        return self.naming.name_of(rec)

    def _note(self, exc: DamagedRecord) -> None:
        if exc.message not in self.problems:
            self.problems.append(exc.message)

    # Reading tiles -------------------------------------------------------------

    def _covering(self, lat: float, lon: float) -> list[int]:
        """The packs that answer at a point, most detailed first (P4-T3a): each regional pack whose coverage
        holds it, then the world pack. A second world pack is not asked, as before Phase 4."""
        out = [p for p, cov in enumerate(self._coverages) if cov is not None and cov.covers(lat, lon)]
        if self._world is not None:
            out.append(self._world)
        return out

    def _used(self) -> list[int]:
        """Every pack a question over a path may ask: the regional packs and the world pack."""
        return [p for p, cov in enumerate(self._coverages) if cov is not None or p == self._world]

    def _hidden(self, p: int, layer: str, lat: float, lon: float) -> bool:
        """Whether pack p's features of a layer are left out at a point, because a more detailed pack covers
        the point and answers for that layer there (P4-T3a)."""
        for q in range(p):
            cov = self._coverages[q]
            if cov is not None and layer in cov.layers and cov.covers(lat, lon):
                return True
        return False

    def _taken(self, packs) -> list[frozenset]:
        """For each of the packs, in order, the layers the packs before it answer for: those it leaves out."""
        out, taken = [], frozenset()
        for p in packs:
            out.append(taken)
            cov = self._coverages[p]
            if cov is not None:
                taken = taken | cov.layers
        return out

    def drawn_packs(self, zoom_km: float, boxes) -> list[int]:
        """The packs a view draws, most detailed first (P4-T3a): each regional pack whose coverage meets one of
        the view's boxes (west, south, east, north), when the view is narrower than the pack's draw_below_km,
        then the world pack. A wider view is drawn by the world pack alone."""
        out = []
        for p, cov in enumerate(self._coverages):
            if cov is not None and zoom_km < cov.draw_below_km and any(cov.meets_box(b) for b in boxes):
                out.append(p)
        if self._world is not None:
            out.append(self._world)
        return out

    def coverage(self, p: int):
        """Pack p's coverage (mapcore.store.packs_combined.Coverage), or None for the world pack."""
        return self._coverages[p]

    def _tile(self, p: int, kind: str, level: int, x: int, y: int) -> TileData:
        """The tile entries of a pack tile ("tile") or drawing tile ("draw"), cached."""
        index = self._indexes[p]

        def load() -> TileData:
            try:
                read = index.pack.tile if kind == "tile" else index.pack.drawing_tile
                data = TileData(read(level, x, y))
                memory.settle()   # its entries stay while it is cached, out of full garbage collections (P3-T24a)
                return data
            except DamagedRecord as exc:
                self._note(exc)
                return TileData([])

        return self.cache.get((p, kind, level, x, y), load)

    def warm(self, lat: float, lon: float, around: int = 1) -> int:
        """Read the pack tiles round a point into the cache, at every tile
        level. Returns how many were read."""
        lon = geodesy.wrap_lon(lon)
        count = 0
        for p in self._covering(lat, lon):
            for level in self._indexes[p].pack.tile_levels:
                x, y = tiles.tile_of(lon, lat, level)
                n = 2 ** level
                for dx in range(-around, around + 1):
                    for dy in range(-around, around + 1):
                        tx, ty = (x + dx) % n, y + dy
                        if 0 <= ty < n and (tx, ty) in self._indexes[p].stored("tile", level):
                            self._tile(p, "tile", level, tx, ty)
                            count += 1
        return count

    def prefetch(self, lat: float, lon: float):
        """Warm the cache round a point in the background, where threads exist
        (not in the browser, where the caller warms it between steps).
        Returns the thread, or None."""
        try:
            thread = threading.Thread(target=self.warm, args=(lat, lon), daemon=True)
            thread.start()
            return thread
        except (RuntimeError, OSError):
            return None

    # Feature records -------------------------------------------------------------

    def _holding(self, identifier: str, layer: str | None = None) -> list[tuple[int, int]]:
        """Every pack holding a feature, most detailed first, as (pack, feature number). With its layer known,
        only the packs that have that layer are asked."""
        out = []
        packs = self._layer_packs.get(layer, ()) if layer is not None else range(len(self._indexes))
        for p in packs:
            try:
                number = self._indexes[p].pack.feature_number(identifier)
            except DamagedRecord as exc:
                self._note(exc)
                continue
            if number is not None:
                out.append((p, number))
        return out

    def _merge(self, identifier: str, layer: str | None = None):
        """A feature from every pack holding it (P4-T3b), as (pack, number, record, others), or None. The first
        is the most detailed pack's whole record (not partial), else the world pack's, else the most detailed
        pack's; `record` is it merged with the others (packs_combined.merge_records); `others` are the other
        packs' records, as (pack, record), empty when one pack holds it."""
        got = self._merged.get(identifier)
        if got is not None:
            return got
        records = []
        for p, number in self._holding(identifier, layer):
            try:
                records.append((p, number, self._indexes[p].pack.feature(number)))
            except DamagedRecord as exc:
                self._note(exc)
        if not records:
            return None
        whole = [r for r in records if not r[2].get("partial")]
        world = [r for r in records if r[0] == self._world]
        first = (whole or world or records)[0]
        others = [(p, rec) for p, _n, rec in records if p != first[0]]
        record = merge_records(first[2], [rec for _p, rec in others]) if others else first[2]
        got = (first[0], first[1], record, others)
        if others:
            self._merged[identifier] = got   # few: the features both packs hold
        return got

    def _alias(self, identifier: str) -> str | None:
        """The identifier an alias stands for, or None (P4-T3b)."""
        for p, index in enumerate(self._indexes):
            if self._coverages[p] is None:
                continue   # a world pack's features have no aliases
            real = index.aliases.get(identifier)
            if real is not None:
                return real
        return None

    def _merge_or_alias(self, identifier: str):
        got = self._merge(identifier)
        if got is None:
            real = self._alias(identifier)
            if real is not None:
                got = self._merge(real)
                return (real, got) if got is not None else (identifier, None)
        return identifier, got

    def feature(self, identifier: str) -> Area | None:
        """The area with this identifier, or None: one feature, merged from every pack holding it (P4-T3b). An
        alias, a regional feature's own identifier before matching, finds it too."""
        _identifier, got = self._merge_or_alias(identifier)
        if got is None:
            return None
        p, number, record, _others = got
        return Area(p, number, record, self.naming)

    def layer_of(self, identifier: str) -> str | None:
        """A feature's layer, from the feature table held in memory, with no record read; None if not found."""
        for index in self._indexes:
            found = index.layer_by_id.get(identifier)
            if found is not None:
                return found
        return None

    def relationships(self, identifier: str) -> dict:
        """A feature's stored relationships (P3-T3e, architecture 6.5): in, same, overlaps, partly, next, near,
        crosses, crossed_by, along, water_in and counts, by the other features' identifiers.
        docs/developer/pack-format.md, relations/G, says what each holds. Empty for a feature with none, one not
        found, or a pack written before format 4.

        A feature several packs hold has their relationships merged (P4-T3b, packs_combined.merge_relationships):
        the whole record's pack answers for the layers it is the authority on, and the others add what concerns
        other layers. A regional pack's feature is put inside the world's holders of the top of its "in": a parish
        is in its district, its county and its country, then in whatever holds the country in the world pack."""
        got = self._merged_rel.get(identifier)
        if got is not None:
            return got
        asked = identifier
        identifier, merged = self._merge_or_alias(identifier)
        if merged is None:
            return {}
        p, _number, record, others = merged
        try:
            rel = self._indexes[p].pack.relationships(identifier)
        except DamagedRecord as exc:
            self._note(exc)
            return {}
        cov = self._coverages[p]
        if not others and cov is None:
            return rel   # a feature of the world pack alone, as before Phase 4
        if others:
            authority = self._authority(p, record)
            rest = []
            for q, rec in others:
                try:
                    rest.append((self._indexes[q].pack.relationships(identifier), bool(rec.get("partial"))))
                except DamagedRecord as exc:
                    self._note(exc)
            rel = merge_relationships(rel, rest, authority, self.layer_of)
        if cov is not None:
            rel = self._held_above(identifier, rel)
        with self._lock:
            if len(self._merged_rel) >= MERGED_KEPT:
                self._merged_rel.pop(next(iter(self._merged_rel)))   # the oldest
            self._merged_rel[asked] = rel
        return rel

    def _authority(self, p: int, record: dict) -> frozenset:
        """The layers pack p answers for alone about its feature (P4-T3b): a regional pack holding all of it, its
        coverage's layers; the world pack, or a pack holding only part of it, every layer it has."""
        cov = self._coverages[p]
        if cov is not None and not record.get("partial"):
            return cov.layers
        return frozenset((self._indexes[p].pack.manifest or {}).get("layers") or ())

    def _held_above(self, identifier: str, rel: dict) -> dict:
        """A regional pack's feature's relationships with "in" carried on above the pack's own areas (P4-T3b): the
        merged "in" of the top of its own "in", such as the world's holders of the United Kingdom, added after
        it. The top's own "in" is carried on in the same way, so this reaches the top of the world's."""
        held = rel.get("in")
        if not held or held[-1] == identifier:
            return rel
        above = self.relationships(held[-1]).get("in", ())
        mentioned = {i if isinstance(i, str) else i[0] for k in ("in", "same", "overlaps", "partly")
                     for i in rel.get(k, ())}
        more = [i for i in above if i not in mentioned and i != identifier]
        if not more:
            return rel
        rel = dict(rel)
        rel["in"] = [*held, *more]
        return rel

    def _area(self, p: int, number: int, merged: bool = True) -> Area | None:
        """Pack p's feature: one feature, its records merged when other packs hold it too (P4-T3b), so its pack
        and number may be another pack's. With merged False, pack p's own, to measure on pack p's shapes."""
        try:
            record = self._indexes[p].pack.feature(number)
        except DamagedRecord as exc:
            self._note(exc)
            return None
        if merged and len(self._layer_packs.get(record.get("layer"), ())) > 1:   # another pack has its layer
            got = self._merge(record["id"], record.get("layer"))
            if got is not None and got[3]:
                return Area(got[0], got[1], got[2], self.naming)
        return Area(p, number, record, self.naming)

    # What is at a point ------------------------------------------------------------

    def at(self, lat: float, lon: float, layers=None) -> list[Area]:
        """Every area at the point, most specific first (LOC-2): by rank, higher
        first, then smallest area. `layers` limits the answer to some layer ids."""
        import shapely

        lon = geodesy.wrap_lon(lon)
        found: dict[tuple[int, int], Area] = {}
        seen: set = set()
        covering = self._covering(lat, lon)
        for p, taken in zip(covering, self._taken(covering)):
            index = self._indexes[p]
            for level in index.pack.tile_levels:
                x, y = tiles.tile_of(lon, lat, level)
                if (x, y) not in self._indexes[p].stored("tile", level):
                    continue
                data = self._tile(p, "tile", level, x, y)
                for i, entry in enumerate(data.entries):
                    if (p, entry.feature) in found or entry.kind not in tiles.AREA_KINDS:
                        continue   # lines and points have no inside, so are never "here"
                    if taken and index.layer_of_number(entry.feature) in taken:
                        continue   # a more detailed pack answers for this layer here (P4-T3a)
                    if entry.kind != tiles.COVERED:
                        with self._shapes:
                            inside = shapely.intersects_xy(data.shape(i), lon, lat)
                        if not inside:
                            continue
                    area = self._area(p, entry.feature)
                    if area is not None and (layers is None or area.layer in layers) and area.id not in seen:
                        found[(p, entry.feature)] = area
                        seen.add(area.id)
        return most_specific_first(found.values(), self.tiers)

    @property
    def tiers(self) -> list[str]:
        """The tiers, highest first, from the first pack that lists them (P3-T17): a pack written before
        tiers lists none."""
        for index in self._indexes:
            found = (index.pack.manifest or {}).get("tiers")
            if found:
                return list(found)
        return []

    # Lines along a path (P2-T10a) ---------------------------------------------------

    def crossed_lines(self, path, layers=None, accept=None) -> list[Crossing]:
        """The line features a move's path crosses, in the order it crosses them, each
        once, where it is first crossed (ANN-2, for Crossed and passed). `path` is the
        move's (lat, lon) points (geodesy.Move.path). `layers` limits the answer to
        some layer ids. Only layers whose definition says geometry: line are looked
        at, so a pack with none reads nothing. `accept`, when given, is a function of an
        area that says whether to count it."""
        import shapely

        pieces = [shapely.LineString(c) for c in path_pieces(path)]
        if not pieces:
            return []
        found: dict[tuple[int, int], Crossing] = {}
        for p in self._used():
            index = self._indexes[p]
            line_layers = {d["id"] for d in index.pack.layers or [] if d.get("geometry") == "line"}
            if layers is not None:
                line_layers &= set(layers)
            if not line_layers:
                continue
            for piece in pieces:
                west, south, east, north = piece.bounds
                shapely.prepare(piece)
                for level in index.pack.tile_levels:
                    x0, y0 = tiles.tile_of(west, south, level)
                    x1, y1 = tiles.tile_of(east, north, level)
                    for x, y in index.tiles_in("tile", level, x0, x1, y0, y1):
                        if not piece.intersects(shapely.box(*tiles.tile_box(level, x, y))):
                            continue
                        data = self._tile(p, "tile", level, x, y)
                        for i, entry in enumerate(data.entries):
                            if entry.kind != tiles.LINES:
                                continue
                            with self._shapes:
                                met = shapely.intersection(data.shape(i), piece)
                            if met.is_empty:
                                continue
                            area = self._area(p, entry.feature)
                            if area is None or area.layer not in line_layers or (
                                    accept is not None and not accept(area)):
                                continue
                            for point in shapely.get_coordinates(met).tolist():
                                if self._hidden(p, area.layer, point[1], point[0]):
                                    continue   # a more detailed pack answers for this layer here (P4-T3a)
                                along = _along_m(path, point[1], point[0])
                                old = found.get((p, entry.feature))
                                if old is None or along < old.along_m:
                                    found[(p, entry.feature)] = Crossing(area, point[1], point[0], along)
        return sorted(_first_by_id(found.values()), key=lambda c: (c.along_m, c.area.id))

    def along_path(self, path, passed_m: float, layers=None, accept=None, cancelled=None) -> list[Passed]:
        """Crossed and passed (P2-T5, ANN-2, architecture 7.5): what a move's path went over
        or near, in the order along the path. Lines it crosses; areas it enters and leaves
        with neither its start nor its end in them; points within passed_m of it. `layers`
        and `accept` limit the answer as in nearby(); the view does not, because a long step
        can reach beyond it. `cancelled`, when given, is asked between pack tiles, and when
        it says yes the search stops with Cancelled.

        It works across the 180 degree line and over the poles, through path_pieces()."""
        import shapely

        def check():
            if cancelled is not None and cancelled():
                raise Cancelled()

        path = [tuple(p) for p in path]
        pieces = [shapely.LineString(c) for c in path_pieces(path)]
        if not pieces:
            return []
        out: list[Passed] = [Passed(c.area, "crossed", c.lat, c.lon, 0.0, c.along_m)
                             for c in self.crossed_lines(path, layers=layers, accept=accept)]
        check()
        start, end = path[0], path[-1]
        ends = set()
        for a in self.at(*start) + self.at(*end):
            # The same feature in every pack that holds it, so a feature you start or end in is never "passed
            # over" because another pack holds it too (P4-T3a).
            for q in self._used():
                number = a.number if q == a.pack else self._indexes[q].pack.feature_number(a.id)
                if number is not None:
                    ends.add((q, number))
        over: dict[tuple[int, int], Passed] = {}
        near: dict[tuple[int, int], Passed] = {}
        dlat = passed_m / M_PER_DEG_LAT_MIN
        for p in self._used():
            index = self._indexes[p]
            kinds = {d["id"]: d.get("geometry", "area") for d in index.pack.layers or []}
            wanted = {k for k, g in kinds.items() if g in ("area", "point") and (layers is None or k in layers)}
            if not wanted:
                continue
            for piece in pieces:
                shapely.prepare(piece)
                west, south, east, north = piece.bounds
                worst = math.cos(math.radians(min(89.0, max(abs(south), abs(north)) + dlat)))
                dlon = passed_m / (111_320.0 * worst)
                reach = (max(-180.0, west - dlon), max(-90.0, south - dlat),
                         min(180.0, east + dlon), min(90.0, north + dlat))
                wide = shapely.buffer(piece, max(dlat, dlon)) if passed_m > 0 else piece
                for level in index.pack.tile_levels:
                    x0, y0 = tiles.tile_of(reach[0], reach[1], level)
                    x1, y1 = tiles.tile_of(reach[2], reach[3], level)
                    for x, y in index.tiles_in("tile", level, x0, x1, y0, y1):
                        box = shapely.box(*tiles.tile_box(level, x, y))
                        if not wide.intersects(box):
                            continue
                        check()
                        data = self._tile(p, "tile", level, x, y)
                        for i, entry in enumerate(data.entries):
                            if entry.kind == tiles.LINES:
                                continue
                            key = (p, entry.feature)
                            if entry.kind == tiles.POINTS:
                                self._passed_point(data, i, key, path, passed_m, wanted, accept, near)
                            elif key not in ends:
                                self._passed_over(data, i, box, key, piece, path, wanted, accept, over)
        out += _first_by_id(over.values(), last=True)
        out += _first_by_id(near.values())
        return sorted(out, key=lambda c: (c.along_m, c.area.id))

    def _passed_point(self, data, i, key, path, passed_m, wanted, accept, near) -> None:
        import shapely

        old = near.get(key)
        with self._shapes:
            points = shapely.get_coordinates(data.shape(i)).tolist()
        for lon, lat in points:
            closest, along = _closest_m(path, lat, lon)
            if closest > passed_m or (old is not None and old.closest_m <= closest):
                continue
            area = self._area(*key)
            if area is None or area.layer not in wanted or (accept is not None and not accept(area)):
                return
            if self._hidden(key[0], area.layer, lat, lon):
                continue   # a more detailed pack answers for this layer here (P4-T3a)
            old = near[key] = Passed(area, "passed", lat, lon, closest, along)

    def _passed_over(self, data, i, box, key, piece, path, wanted, accept, over) -> None:
        import shapely

        with self._shapes:
            shape = box if data.entries[i].kind == tiles.COVERED else data.shape(i)
            met = shapely.intersection(shape, piece)
        if met.is_empty:
            return
        area = self._area(*key)
        if area is None or area.layer not in wanted or (accept is not None and not accept(area)):
            return
        # Where the path leaves it, the last point inside along the path.
        old = over.get(key)
        for lon, lat in shapely.get_coordinates(met).tolist():
            if self._hidden(key[0], area.layer, lat, lon):
                continue   # a more detailed pack answers for this layer here (P4-T3a)
            along = _along_m(path, lat, lon)
            if old is None or along > old.along_m:
                old = over[key] = Passed(area, "passed over", lat, lon, 0.0, along)

    # Nearby ------------------------------------------------------------------------

    def nearby(self, lat: float, lon: float, radius_m: float, limit: int = 20,
               layers=None, exclude=(), accept=None) -> list[Near]:
        """The areas within radius_m of the point, nearest first, at most `limit`.

        Each has its nearest point, found in a flat view round the location
        and then measured on the ellipsoid (INF-3, INF-7). Areas the point is
        inside come first with distance 0; callers that want only the
        surroundings leave them out. `exclude` is a collection of identifiers.
        `accept`, when given, is a function of an area that says whether to count it
        (the visible rule's size test, NAV-13).
        """
        lon = geodesy.wrap_lon(lon)
        flat = Flat(lat, lon)
        best: dict[str, Near] = {}
        # Every pack the radius may reach (P4-T3a). A pack's feature of a layer a more detailed pack answers
        # for is left out when its nearest point is in that pack's coverage; one both packs hold is given once,
        # at the nearer of its two nearest points, the more detailed pack's on a tie.
        packs = self._used() if any(c is not None for c in self._coverages) else self._covering(lat, lon)[:1]
        for p in packs:
            results: list[Near] = []
            numbers, boxes = self._indexes[p].boxes
            bound = self._box_distance_m(boxes, lat, lon)
            order = np.argsort(bound, kind="stable")
            for k in order.tolist():
                if bound[k] > radius_m:
                    break
                if len(results) >= limit and results[limit - 1].distance_m <= bound[k]:
                    break
                area = self._area(p, int(numbers[k]), merged=False)   # measured on pack p's own shapes
                if area is None or area.id in exclude or (layers is not None and area.layer not in layers) \
                        or (accept is not None and not accept(area)):
                    continue
                found = self._nearest(p, area, flat, lat, lon, float(bound[k]), radius_m)
                if found is not None and not self._hidden(p, area.layer, found.lat, found.lon):
                    whole = self._area(p, int(numbers[k]))   # given as one feature (P4-T3b)
                    results.append(replace(found, area=whole) if whole is not None else found)
                    results.sort(key=lambda n: (n.distance_m, n.area.id))
            for found in results[:limit]:
                old = best.get(found.area.id)
                if old is None or found.distance_m < old.distance_m:
                    best[found.area.id] = found
        return sorted(best.values(), key=lambda n: (n.distance_m, n.area.id))[:limit]

    def points_near(self, lat: float, lon: float, radius_m: float, layer: str) -> list[Near]:
        """The places of one point in a layer within radius_m of the point, nearest first, measured on the
        ellipsoid, as Nearby measures a place (P3-T28p, for the town Where am I names). Only the points of
        that layer are looked at, from arrays kept in memory, so it is quick enough for every press of Space."""
        lon = geodesy.wrap_lon(lon)
        out: list[Near] = []
        seen: set = set()
        packs = self._used() if any(c is not None for c in self._coverages) else self._covering(lat, lon)[:1]
        for p in packs:
            numbers, lats, lons = self._indexes[p].points_of(layer)
            if not len(numbers):
                continue
            dlat = radius_m / M_PER_DEG_LAT_MIN
            keep = np.abs(lats - lat) <= dlat
            worst = math.cos(math.radians(min(89.9, abs(lat) + dlat)))
            dlon = math.degrees(radius_m / (geodesy.A_M * worst)) if worst > 1e-6 else 360.0
            if dlon < 180.0:
                keep &= np.abs((lons - lon + 180.0) % 360.0 - 180.0) <= dlon
            rows = np.nonzero(keep)[0]
            if not len(rows):
                continue
            dist, bear = geodesy.inverse_many(lat, lon, lats[rows], lons[rows])
            for k, d, b in zip(rows.tolist(), dist.tolist(), bear.tolist()):
                if d > radius_m or self._hidden(p, layer, float(lats[k]), float(lons[k])):
                    continue
                area = self._area(p, int(numbers[k]))
                if area is not None and area.id not in seen:
                    seen.add(area.id)
                    out.append(Near(area, d, 0.0 if d == 0.0 else b, float(lats[k]), float(lons[k]), d == 0.0))
        out.sort(key=lambda n: (n.distance_m, n.area.id))
        return out

    # Search (P3-T8b, SRB-1, SRB-2, architecture 7.9) ------------------------------------------------------

    def search(self, text: str, limit: int = 20, layers=None, near: tuple[float, float, float] | None = None,
               inside: str | None = None, here: tuple[float, float] | None = None) -> list[Found]:
        """Features whose names match what was typed, best first: by how well they match, then by importance
        and, given `here` (lat, lon), nearness to it (mapcore.search, P3-T32f). Only the search records of the
        words typed are read, never the whole index.

        Narrowing (SRB-2): `layers`, a collection of layer ids; `near`, (lat, lon, metres), the feature's point
        within that distance; `inside`, an identifier: the feature itself, or one the stored relationships put
        inside it, fully or partly, or crossing it. A pack written before the search index finds nothing.
        One feature found by two of its names is listed once, by the better."""
        query = search.Query(text)
        if not query.key:
            return []
        wanted = None if layers is None else set(layers)
        best: dict[str, tuple[tuple, Found]] = {}
        with self._lock:
            for p, index in enumerate(self._indexes):
                pack = index.pack
                n = pack.search_buckets
                if not n:
                    continue
                for pref in query.prefixes:
                    try:
                        rows = pack.search_rows(search.bucket(pref, n))
                    except DamagedRecord as exc:
                        self._note(exc)
                        continue
                    lead = " " + pref
                    for row in rows:
                        key = row[search.KEY]
                        # A record holds the rows of several prefixes; only this prefix's are looked at, so what
                        # is found never depends on which prefixes share a record.
                        if not (key.startswith(pref) or lead in key):
                            continue
                        if wanted is not None and row[search.LAYER] not in wanted:
                            continue
                        got = query.match(key)
                        if got is None:
                            continue
                        if near is not None and not _within(row, near):
                            continue
                        level, similar = got
                        near_points = 0
                        if here is not None and row[search.LAT] is not None:
                            near_points = search.nearness(search.sphere_m(here[0], here[1], row[search.LAT],
                                                                          row[search.LON]))
                        order = search.rank_key(level, similar, row[search.IMPORTANCE], row[search.NAME],
                                                row[search.ID], near_points)
                        old = best.get(row[search.ID])
                        if old is None or order < old[0]:
                            best[row[search.ID]] = (order, Found(
                                p, row[search.ID], row[search.NAME], row[search.LAYER], row[search.IMPORTANCE],
                                row[search.LAT], row[search.LON], row[search.DESCRIPTION], row[search.VIA],
                                level, similar))
        ranked = [f for _o, f in sorted(best.values(), key=lambda t: t[0])]
        if inside is None:
            return ranked[:limit]
        return self._inside(ranked, inside, limit)

    # The world tree and browsing by category (P3-T9; SRB-3, SRB-4) -------------------------------------------

    def tree_children(self, identifier: str = "world") -> list[tuple[str, str]]:
        """The next level of the world tree under "world" or a feature, as (identifier, English name), by
        name (SRB-3), by the rules of mapcore.store.contents: Russia is under Europe and Asia, Hawaii under the
        United States, and a constituent country, such as England, holds its own areas. A pack that stores the
        tree gives it in one read (P3-T20c, DP194); else the first call scans the feature records of the tree's
        layers once. The rest take no reading."""
        with self._lock:
            if self._tree_children is None:
                self._tree_children = self._read_tree() or self._build_tree()
            named = [(i, self._name(self._tree_rows[i])) for i in self._tree_children.get(identifier, ())]
        return sorted(named, key=lambda t: (t[1].casefold(), t[0]))

    def has_tree_children(self, identifier: str) -> bool:
        """Whether an item of the world tree has anything under it, so the tree can show it as a branch or not."""
        with self._lock:
            if self._tree_children is None:
                self._tree_children = self._read_tree() or self._build_tree()
            return bool(self._tree_children.get(identifier))

    def _read_tree(self) -> dict[str, set] | None:
        """The world tree stored in the packs, each pack's joined; None if any pack has none."""
        if not self._indexes or not all(index.pack.has_contents for index in self._indexes):
            return None
        tree: dict[str, set] = {}
        rows: dict[str, dict] = {}
        for index in self._indexes:
            try:
                stored = index.pack.tree() or {}
            except DamagedRecord as exc:
                self._note(exc)
                return None
            for parent, ids in (stored.get("children") or {}).items():
                tree.setdefault(parent, set()).update(ids)
            for identifier, row in (stored.get("names") or {}).items():
                rows.setdefault(identifier, row)
        if any(i not in rows for ids in tree.values() for i in ids):
            return None
        self._tree_rows = rows
        return tree

    def _build_tree(self) -> dict[str, set]:
        rows: dict[str, dict] = {}
        for index in self._indexes:
            try:
                for rec in index.pack.scan(TREE_LAYERS):
                    rows.setdefault(rec["id"], rec)
            except DamagedRecord as exc:
                self._note(exc)
        tree = contents.build_tree(rows, self.relationships)
        self._tree_rows = contents.tree_names(rows, tree)
        return tree

    def tree_row(self, identifier: str) -> dict | None:
        """What the world tree keeps of an item: for a dispute's item (P3-T26a), its name, claimants, Natural
        Earth's note and how many areas it holds."""
        self.tree_children("world")
        return self._tree_rows.get(identifier)

    def special_areas(self, kind: str, inside: str | None = None) -> list[Found]:
        """The disputed areas or unclaimed areas (kind "disputed" or "unclaimed"), by name, as search results,
        all of them or only those the stored relationships put inside, partly inside or crossing a feature.
        Disputed areas are one for each dispute (P3-T26a, DP205): the largest of its areas there, named and
        described by the dispute, so Enter goes to that area."""
        out = []
        for identifier, name in self.tree_children("special:" + kind):
            members = self.tree_children(identifier) if identifier.startswith(contents.DISPUTE_PREFIX) else [(identifier, name)]
            for member, member_name in members:
                rec = self.feature(member)
                point = rec.record.get("point") if rec is not None else None
                out.append(Found(0, member, member_name, rec.layer if rec is not None else "countries", 0,
                                 point[1] if point else None, point[0] if point else None, name, "", 0, 1.0))
        if inside is not None:
            out = self._inside(out, inside, len(out))
        if kind != "disputed":
            return out
        largest: dict[str, tuple[float, Found]] = {}
        for f in out:
            rec = self.feature(f.id)
            size = rec.area_km2 if rec is not None else 0.0
            if f.description not in largest or size > largest[f.description][0]:
                largest[f.description] = (size, f)
        grouped = [replace(f, name=dispute) for dispute, (_s, f) in largest.items()]
        return sorted(grouped, key=lambda f: (f.name.casefold(), f.id))

    def browse(self, layer: str, identifier: str) -> list[Found]:
        """Every feature of a layer inside a feature, fully or partly, or crossing it (SRB-4), by name, with no
        limit by zoom: such as every lake in Finland. For an area of the tree's layers, a pack that stores what
        each holds gives their feature numbers in one read (P3-T20c, DP194). Otherwise the layer's feature records
        are read in a scan, each first tested against the feature's box, and only the ones that may be inside
        have their stored relationships read."""
        holder = self.feature(identifier)
        if holder is None:
            return []
        if not contents.water_may_hold(holder.layer, layer):   # water holds only water and islands (P3-T29d)
            return []
        box = holder.record.get("bbox")
        out: list[Found] = []
        seen: set[str] = set()

        def found(p: int, rec: dict, partly: bool) -> None:
            if rec["id"] in seen:
                return
            seen.add(rec["id"])
            point = rec.get("point")
            name = self._name(rec)
            # A feature only partly inside says so: "Kazakhstan, partly in Europe" (P3-T25b, DP204).
            description = say("contains.partly_name", name=name, holder=holder.name) if partly else name
            out.append(Found(p, rec["id"], name, layer, 0, point[1] if point else None,
                             point[0] if point else None, description, "", 0, 1.0))

        isles = holder.layer in contents.WATER_HOLDERS and layer in contents.ISLE_LAYERS
        if isles:
            # The islands in a water by their shore come from its shores (P3-T32g); the layer is read through only
            # for islands inside its area by the stored relationships, such as those a lake's outline leaves in.
            for i in self.water_islands(identifier):
                rec = self.feature(i)
                if rec is not None and rec.layer == layer:
                    found(rec.pack, rec.record, False)
            if not self.relationships(identifier).get("counts", {}).get(layer):
                out.sort(key=lambda f: (f.name.casefold(), f.id))
                return out
        # Another pack's features of a layer the holder's own pack answers for are not listed (P4-T3b): what
        # Contains counts is what browsing lists.
        others = len(self._holding(identifier)) > 1
        authority = self._authority(holder.pack, holder.record) if others else frozenset()
        for p, index in enumerate(self._indexes):
            pack = index.pack
            if p != holder.pack and layer in authority:
                continue
            try:
                held = pack.holds(identifier) if holder.layer in contents.HOLDER_LAYERS else None
                if held is not None:
                    numbers, partly = held.get(layer, ((), set()))
                    for number in numbers:
                        rec = pack.feature(number)
                        if rec["layer"] == layer and rec["id"] != identifier:
                            found(p, rec, number in partly)
                    continue
                for rec in pack.scan((layer,)):
                    if rec["id"] == identifier or (box is not None and rec.get("bbox") is not None
                                                   and not _boxes_meet(box, rec["bbox"])):
                        continue
                    rel = self.relationships(rec["id"])
                    if identifier in contents.holders(rel, layer):
                        found(p, rec, contents.partly_in(rel, identifier, layer))
            except DamagedRecord as exc:
                self._note(exc)
        out.sort(key=lambda f: (f.name.casefold(), f.id))
        return out

    def water_islands(self, identifier: str) -> list[str]:
        """The islands in a sea, an ocean or a lake by their shore (P3-T32g, contents.waters_round), in the order of
        its stored "shores": the islands on its shores at least SHORE_SHARE of whose outline is on it. Worked out
        once for each water, then remembered. Empty for land."""
        return self._water_isles(identifier)[0]

    def _water_isles(self, identifier: str) -> tuple[list[str], int, int]:
        got = self._isles.get(identifier)
        if got is not None:
            return got
        if self.layer_of(identifier) not in contents.WATER_HOLDERS:
            return [], 0, 0
        ids = [i for i, _km in self.relationships(identifier).get("shores", ())
               if self.layer_of(i) in contents.ISLE_LAYERS]
        rels = self._relationships_many(ids)
        isles, not_held, not_counted = [], 0, 0
        for i in ids:
            rel = rels.get(i, {})
            if identifier in contents.waters_round(rel):
                isles.append(i)
                not_held += identifier not in rel.get("in", ())
                not_counted += identifier not in contents.holders(rel)   # what the stored counts took in
        got = self._isles[identifier] = (isles, not_held, not_counted)
        return got

    def _relationships_many(self, identifiers) -> dict[str, dict]:
        """relationships() of many features, without keeping every pack record they are in (Pack.relationships_passing)."""
        out: dict[str, dict] = {}
        left = list(identifiers)
        if len(self._indexes) > 1:   # several packs: each as relationships() gives it, merged (P4-T3b)
            return {i: self.relationships(i) for i in left}
        for index in self._indexes:
            pack = index.pack
            try:
                known = index.layer_by_id   # held in memory: no feature record is read
                mine = [i for i in left if i in known]
                out.update(pack.relationships_passing(mine))
            except DamagedRecord as exc:
                self._note(exc)
                continue
            left = [i for i in left if i not in out]
        return out

    def contents_counts(self, identifier: str) -> tuple[dict, dict | None]:
        """How many features of each layer a feature holds, as Ctrl+Shift+F and hierarchy mode's Down say them: the
        stored "counts" (inside fully or partly) and "held" (wholly inside; None for a pack written before it), with
        the islands in a water by their shore added (P3-T32g), which a pack written before it leaves out; a pack
        whose manifest says islands_in_water has them already."""
        rel = self.relationships(identifier)
        counts, held = dict(rel.get("counts", {})), (dict(rel["held"]) if "held" in rel else None)
        if all(index.pack.manifest.get("islands_in_water") for index in self._indexes):
            return counts, held   # a pack written from P3-T32g on stores them so
        isles, not_held, not_counted = self._water_isles(identifier)
        if isles:
            layer = contents.ISLE_LAYERS[0]
            if not_counted:
                counts[layer] = counts.get(layer, 0) + not_counted
            if held is not None and not_held:
                held[layer] = held.get(layer, 0) + not_held
        return counts, held

    # Within a distance of a feature (P3-T10a, INF-9) ---------------------------------------------------------

    def within_distance(self, layer: str, identifier: str, metres: float) -> list[tuple[Found, float]]:
        """Every feature of a layer within `metres` of a feature, with its distance, nearest first, then by name
        (INF-9: "towns within 10 km of Hampshire"). A feature inside it, crossing it, overlapping it or sharing a
        border with it is at 0 by the stored relationships, with no shape read. For the rest, only the features
        whose boxes come within reach of the feature's box are looked at, and only the pack tiles there are read:
        a point is measured to the feature's nearest point on the ellipsoid, as Nearby measures; a line or an
        area by the nearest points of the two shapes in a flat view round them, then on the ellipsoid."""
        holder = self.feature(identifier)
        if holder is None or metres < 0:
            return []
        mine = self.relationships(identifier)
        touching = set(mine.get("in", ())) | set(mine.get("same", ())) | set(mine.get("crosses", ())) \
            | set(mine.get("crossed_by", ())) | set(mine.get("along", ())) \
            | {x[0] for x in (*mine.get("partly", ()), *mine.get("overlaps", ()), *mine.get("next", ()))}
        near_km = {i: km for i, km in mine.get("near", ())}
        reach = _grown_boxes(holder.record["bbox"], metres)
        point_layer = self._geometry_of(layer) == "point"
        out: list[tuple[Found, float]] = []
        seen: set = set()   # a feature both packs hold, once (P4-T3b)
        for p, index in enumerate(self._indexes):
            numbers, boxes = index.boxes
            _widths, layers = index.sizes
            keep = (layers == layer) & _boxes_reach(boxes, reach)
            for k in np.nonzero(keep)[0].tolist():
                area = self._area(p, int(numbers[k]), merged=False)   # measured on pack p's own shapes
                if area is None or area.id == identifier or area.id in seen:
                    continue
                seen.add(area.id)
                distance = self._distance_to(p, holder, area, metres, touching, near_km, point_layer, reach)
                if distance is None or distance > metres:
                    continue
                rec = (self._area(p, int(numbers[k])) or area).record   # one feature's record (P4-T3b)
                point = rec.get("point")
                name = self._name(rec)
                out.append((Found(p, area.id, name, layer, 0, point[1] if point else None,
                                  point[0] if point else None, name, "", 0, 1.0), distance))
        out.sort(key=lambda t: (t[1], t[0].name.casefold(), t[0].id))
        return out

    def barely_parted(self, identifier: str) -> bool:
        """Whether an unnamed island is land that bigger land of its own country comes within PARTED_M of, across
        a canal or a creek, so it is not said as "Unnamed island" (P3-T32e, DP87, DP169). Ceuta's old town, cut
        off by a moat 20 metres wide, the Peloponnese, cut off by the Corinth Canal, and Cape Ann are; an unnamed
        island 1 kilometre off the coast, or with only rocks beside it, is not. The bigger land is an island
        bigger than this one, or land with no island that has MAINLAND_KM2 or more within MAINLAND_M of the
        gap, which is a continent's, as smaller land with no name has no island (DP169). Worked out from the pack
        tiles round the island once, then remembered. A named island is never barely parted."""
        found = self._parted.get(identifier)
        if found is None:
            found = self._parted[identifier] = self._barely_parted(identifier)
        return found

    def _barely_parted(self, identifier: str) -> bool:
        """barely_parted, worked out from the pack tiles, without joining any shape: a country such as Greece is
        large, and joining it made the Peloponnese take 2 seconds. Each pack tile part of the country near the
        island, the biggest first, less the island's parts beside it, gives pieces of land; one within PARTED_M
        of the island is bigger land if it is in a bigger island, or if it has no island and is MAINLAND_KM2 or
        more, or has that much round the gap (_mainland_at). Rocks of under a hectare are passed over."""
        import shapely

        isl = self.feature(identifier)
        if isl is None or isl.layer != "islands" or isl.record.get("type") != "unnamed island":
            return False
        own_km2 = float(isl.record.get("area_km2") or 0.0)
        west, south, east, north = isl.record["bbox"]
        k = math.cos(math.radians((south + north) / 2))
        scale = np.array([k * M_PER_DEG_LAT_MIN, M_PER_DEG_LAT_MIN])

        def flat(g):   # metres, near enough for a gap of tens of metres
            return shapely.transform(g, lambda c: c * scale)

        countries = [a for a in (self.feature(i) for i in self.relationships(identifier).get("in", ()))
                     if a is not None and a.layer == "countries"]
        slack = PARTED_M / (M_PER_DEG_LAT_MIN * max(k, 1e-3))   # PARTED_M or more, in degrees
        for box in _grown_boxes(isl.record["bbox"], PARTED_M):
            own = [g for g in (shapely.clip_by_rect(q, *box) for q in self._parts(isl, [box])) if not g.is_empty]
            if not own:
                continue
            tree = shapely.STRtree(own)
            parts = []
            for country in countries:
                for part, tbox in self._pieces_with_tiles(country, [box]):
                    part = shapely.clip_by_rect(part, *box)
                    if not part.is_empty:
                        parts.append((part, tbox))
            parts.sort(key=lambda t: -t[0].area)   # the biggest first: the mainland, if it is there
            for part, tbox in parts:
                w, s, e, n = part.bounds
                beside = tree.query(shapely.box(w - slack, s - slack, e + slack, n + slack)).tolist()
                if not beside:
                    continue
                rest = part
                for j in beside:
                    rest = shapely.difference(rest, own[j])
                edge = shapely.box(max(tbox[0], box[0]), max(tbox[1], box[1]), min(tbox[2], box[2]),
                                   min(tbox[3], box[3])).exterior   # where the land may go on
                pieces = sorted((g for g in shapely.get_parts(rest) if not g.is_empty and g.area > 0),
                                key=lambda g: -g.area)
                for g in pieces:
                    m2 = g.area * scale[0] * scale[1]
                    reaches_edge = shapely.intersects(g, edge)
                    if m2 < 1e4 and not reaches_edge:
                        continue   # a rock of under a hectare
                    near = [own[j] for j in beside if shapely.dwithin(own[j], g, slack)]
                    if not near or min(shapely.distance(flat(q), flat(g)) for q in near) > PARTED_M:
                        continue
                    p = shapely.point_on_surface(g)
                    there = [a for a in self.at(p.y, p.x, layers=["islands"]) if a.id != identifier]
                    if there:
                        if max(float(a.record.get("area_km2") or 0.0) for a in there) > own_km2:
                            return True
                    elif m2 >= MAINLAND_KM2 * 1e6 or (reaches_edge and self._mainland_at(
                            countries, isl, shapely.shortest_line(shapely.union_all(near), g).coords[-1], flat)):
                        return True
        return False

    def _mainland_at(self, countries: list, isl: Area, q, flat) -> bool:
        """Whether the land at q, a point on its edge, has MAINLAND_KM2 or more within MAINLAND_M, the island
        left out."""
        import shapely

        at = shapely.Point(q)
        for box in _grown_boxes([q[0], q[1], q[0], q[1]], MAINLAND_M):
            own = self._land_in(isl, box)
            for country in countries:
                land = shapely.difference(self._land_in(country, box), own)
                if any(not w.is_empty and shapely.distance(w, at) < 1e-5 and shapely.area(flat(w)) >= MAINLAND_KM2 * 1e6
                       for w in shapely.get_parts(land)):
                    return True
        return False

    def _land_in(self, area: Area, box):
        """A feature's land within a box (west, south, east, north, not across the 180 degree line), as one
        shape: each part cut to the box before they are joined, as a country's parts can be large."""
        import shapely

        parts = [shapely.clip_by_rect(g, *box) for g in self._parts(area, [box])]
        return shapely.union_all([g for g in parts if not g.is_empty])

    def _distance_to(self, p: int, holder: Area, area: Area, metres: float, touching: set, near_km: dict,
                     point_layer: bool, reach) -> float | None:
        """How far a feature is from the holder, or None when beyond `metres`: 0 for one the stored
        relationships put in, across or beside it; else measured from the pack tiles near both."""
        if area.id in touching:
            return 0.0
        rel = self.relationships(area.id)
        if holder.id in rel.get("in", ()) or holder.id in rel.get("same", ()) or holder.id in rel.get("crosses", ()) \
                or any(x[0] == holder.id for x in (*rel.get("partly", ()), *rel.get("overlaps", ()))):
            return 0.0
        if area.id in near_km:   # an area of the holder's own layer that nearly touches it, measured in the build
            return near_km[area.id] * 1000.0
        if point_layer:
            best = None
            for lon, lat in self._points_of(area, reach):
                found = self._nearest(holder.pack, holder, Flat(lat, lon), lat, lon,
                                      float(self._box_distance_m(np.asarray([holder.record["bbox"]], dtype=np.float64),
                                                                 lat, lon)[0]), metres)
                if found is not None and (best is None or found.distance_m < best):
                    best = found.distance_m
            return best
        return self._shapes_apart(p, holder, area, metres)

    def _points_of(self, area: Area, reach) -> list[tuple[float, float]]:
        """A point feature's points (lon, lat) within reach: its own point, or each of its points in the pack
        tiles there, for a feature of several points."""
        import shapely

        found = []
        for kind_data in self._parts(area, reach):
            found += [tuple(c) for c in shapely.get_coordinates(kind_data).tolist()]
        if not found and area.record.get("point"):
            found = [tuple(area.record["point"])]
        return found

    def _parts(self, area: Area, boxes) -> list:
        """The shapes of a feature's parts, in longitude and latitude, from its pack tiles meeting the boxes
        (west, south, east, north, none across the 180 degree line). A pack tile it wholly covers is the tile's
        own box."""
        import shapely

        index = self._indexes[area.pack]
        own = area.record["bbox"]
        out = []
        seen = set()
        for box in boxes:
            for w, s, e, n in [b for b in _meet_boxes(box, own)]:
                for level in index.pack.tile_levels:
                    x0, y0 = tiles.tile_of(w, s, level)
                    x1, y1 = tiles.tile_of(e, n, level)
                    for x, y in index.tiles_in("tile", level, x0, x1, y0, y1):
                        if (level, x, y) in seen:
                            continue
                        seen.add((level, x, y))
                        data = self._tile(area.pack, "tile", level, x, y)
                        for i in data.by_feature.get(area.number, ()):
                            if data.entries[i].kind == tiles.COVERED:
                                out.append(shapely.box(*tiles.tile_box(level, x, y)))
                            else:
                                with self._shapes:
                                    out.append(data.shape(i))
        return out

    def _pieces_with_tiles(self, area: Area, boxes) -> list[tuple]:
        """Like _parts, each with the box of its pack tile: [(shape, tile box)]."""
        import shapely

        index = self._indexes[area.pack]
        out, seen = [], set()
        for box in boxes:
            for w, s, e, n in _meet_boxes(box, area.record["bbox"]):
                for level in index.pack.tile_levels:
                    x0, y0 = tiles.tile_of(w, s, level)
                    x1, y1 = tiles.tile_of(e, n, level)
                    for x, y in index.tiles_in("tile", level, x0, x1, y0, y1):
                        if (level, x, y) in seen:
                            continue
                        seen.add((level, x, y))
                        data = self._tile(area.pack, "tile", level, x, y)
                        tbox = tiles.tile_box(level, x, y)
                        for i in data.by_feature.get(area.number, ()):
                            if data.entries[i].kind == tiles.COVERED:
                                out.append((shapely.box(*tbox), tbox))
                            else:
                                with self._shapes:
                                    out.append((data.shape(i), tbox))
        return out

    def shared_border(self, a: Area, b: Area) -> list:
        """The border two areas share, as lines in longitude and latitude, each stretch whole (P3-T24f, DP201):
        a stretch with two ends, or a closed ring with none, as round an enclave. Only the pack tiles where both
        have shapes are read, and the cuts along pack tile edges are left out."""
        import shapely

        boxes_a = _grown_boxes(b.record["bbox"], 1000.0)
        boxes_b = _grown_boxes(a.record["bbox"], 1000.0)
        mine = self._pieces_with_tiles(a, boxes_a)
        theirs = self._pieces_with_tiles(b, boxes_b)
        if not mine or not theirs:
            return []
        # Only the pieces whose tiles meet a tile of the other: the border is there.
        tiles_b = shapely.STRtree([shapely.box(*t) for _g, t in theirs])
        tiles_a = shapely.STRtree([shapely.box(*t) for _g, t in mine])
        mine = [m for m in mine if len(tiles_b.query(shapely.box(*m[1]), predicate="intersects"))]
        theirs = [t for t in theirs if len(tiles_a.query(shapely.box(*t[1]), predicate="intersects"))]
        if not mine or not theirs:
            return []
        ua = shapely.union_all([g for g, _t in mine])
        ub = shapely.union_all([g for g, _t in theirs])
        shared = shapely.intersection(shapely.boundary(ua), shapely.boundary(ub))
        # The edges of the pack tiles read are cuts, not borders.
        frame = shapely.union_all([shapely.boundary(shapely.union_all([shapely.box(*t) for _g, t in mine])),
                                   shapely.boundary(shapely.union_all([shapely.box(*t) for _g, t in theirs]))])
        shared = shapely.difference(shared, shapely.buffer(frame, 1e-9))
        lines = [g for g in shapely.get_parts(shared) if shapely.get_type_id(g) in (1, 2, 5)]
        if not lines:
            return []
        merged = shapely.line_merge(shapely.union_all(lines))
        return [g for g in shapely.get_parts(merged) if shapely.length(g) > 0]

    def _shapes_apart(self, p: int, holder: Area, area: Area, metres: float) -> float | None:
        """The least distance between two features' shapes, from the pack tiles where each comes within reach of
        the other: the nearest points are found in a flat view round the middle of that ground, then measured on
        the ellipsoid. None when either has no shape there."""
        import shapely

        theirs = self._parts(area, _grown_boxes(holder.record["bbox"], metres))
        if not theirs:
            return None
        mine = self._parts(holder, _grown_boxes(area.record["bbox"], metres))
        if not mine:
            return None
        a, b = shapely.union_all(theirs), shapely.union_all(mine)
        if a.intersects(b):
            return 0.0
        west, south, east, north = shapely.union_all([a, b]).bounds
        flat = Flat((south + north) / 2.0, (west + east) / 2.0)
        line = shapely.shortest_line(flat.transform(a), flat.transform(b))
        (x1, y1), (x2, y2) = shapely.get_coordinates(line).tolist()
        lat1, lon1 = (float(v) for v in flat.inverse(x1, y1))
        lat2, lon2 = (float(v) for v in flat.inverse(x2, y2))
        return geodesy.inverse(lat1, lon1, lat2, lon2)[0]

    def _inside(self, ranked: list[Found], identifier: str, limit: int) -> list[Found]:
        """The results that are the feature, or inside it, partly inside or crossing it, by the stored
        relationships, in their order, at most limit. Each result's point is first tested against the
        feature's box, so the relationships of most are never read."""
        holder = self.feature(identifier)
        if holder is None:
            return []
        box = holder.record.get("bbox")
        out = []
        for f in ranked:
            if len(out) >= limit:
                break
            if f.id == identifier:
                out.append(f)
                continue
            if box is not None and f.lat is not None and not _in_box(f.lat, f.lon, box):
                # A line or an area may reach into the box with its point outside it.
                if f.layer and self._geometry_of(f.layer) == "point":
                    continue
            # By the rule of Browse, so an island is found in the sea round it too (P3-T32g).
            if identifier in contents.holders(self.relationships(f.id), f.layer):
                out.append(f)
        return out

    def _geometry_of(self, layer: str) -> str:
        for index in self._indexes:
            for d in index.pack.layers:
                if d.get("id") == layer:
                    return d.get("geometry", "area")
        return "area"

    @staticmethod
    def _box_distance_m(boxes: np.ndarray, lat: float, lon: float) -> np.ndarray:
        """About how far each box is from the point: the least it can be, to
        within a few percent. Used to choose which areas to look at, and in
        what order."""
        west, south, east, north = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        dlat = np.maximum(np.maximum(south - lat, lat - north), 0.0)
        crosses = west > east
        inside = np.where(crosses, (lon >= west) | (lon <= east), (lon >= west) & (lon <= east))
        gap = np.minimum((west - lon) % 360.0, (lon - east) % 360.0)
        gap = np.where(inside, 0.0, np.minimum(gap, 180.0))
        near_lat = np.clip(lat, south, north)
        east_west = gap * 111_320.0 * np.cos(np.radians(near_lat)) * 0.9
        return np.hypot(dlat * M_PER_DEG_LAT_MIN, east_west)

    def _search_box(self, lat: float, lon: float, r: float, bbox) -> list[tuple[float, float, float, float]]:
        """The boxes (west, south, east, north), not crossing the 180 degree
        line, where tiles are looked at: a box round the point of half-width r
        metres, meeting the area's own box."""
        dlat = r / M_PER_DEG_LAT_MIN
        south, north = max(-90.0, lat - dlat), min(90.0, lat + dlat)
        worst = math.cos(math.radians(min(89.9, max(abs(south), abs(north)))))
        dlon = math.degrees(r / (geodesy.A_M * worst)) if worst > 1e-6 else 360.0
        if dlon >= 180.0 or max(abs(south), abs(north)) >= 89.0:
            spans = [(-180.0, 180.0)]
        else:
            spans = _intervals(geodesy.wrap_lon(lon - dlon), geodesy.wrap_lon(lon + dlon))
        w, s, e, n = bbox
        both = _meet(spans, _intervals(w, e))
        s, n = max(s, south), min(n, north)
        if s > n:
            return []
        return [(sw, s, se, n) for sw, se in both]

    def measure(self, area: Area, lat: float, lon: float, border: bool = False) -> Near | None:
        """The nearest point of one feature to the point, measured on the ellipsoid (INF-3, INF-8). With
        border, an area the point is inside gives its nearest point on the area's own boundary, not
        distance 0 (INF-3). A feature in no tile near it gives None."""
        lon = geodesy.wrap_lon(lon)
        flat = Flat(lat, lon)
        p = area.pack
        numbers, boxes = self._indexes[p].boxes
        where = np.nonzero(numbers == area.number)[0]
        if not len(where):
            return None
        lower = float(self._box_distance_m(boxes[where[:1]], lat, lon)[0])
        return self._nearest(p, area, flat, lat, lon, lower, geodesy.A_M * math.pi, border)

    def nearest_many(self, areas, lat: float, lon: float, radius_m: float) -> dict[str, Near]:
        """The nearest point of each of many features to the point, measured on the ellipsoid, for those within
        radius_m of it, by identifier: what Contains lists and how far each is (P3-T29c, INF-4). The answers are
        Store.measure's, found four ways, cheapest first:

        * a place of one point: its point, all measured together (geodesy.inverse_many);
        * an area you are in: distance 0, by the exact test "where am I" uses (Store.at);
        * a line, or an area you are not in, from a drawing level's tiles within radius_m, each tile read once for
          all the features measured from it: the nearest point of each part is found together in an azimuthal
          equidistant view round the point (whose distances from its centre are true on the sphere), the nearest
          part of each feature kept, and measured on the ellipsoid. The level is the coarsest that holds the
          feature whose tolerance is at most DRAWN_SHARE of the least distance its box allows, or of VIEW_SHARE of
          radius_m, whichever is more; beyond NEAR_EXACT_M, else the finest, as _search does. So for Contains
          Europe at 2,500 kilometres, a road 1,000 kilometres away is measured on the map's own 1,000 kilometre
          drawing, within 8 kilometres, and one nearby on the 150 kilometre drawing, within 1.5 kilometres;
        * any other, such as a road near you at 500 kilometres zoom, or an area smaller than every level keeps:
          from the exact pack tiles, one at a time, by _nearest, as Nearby measures it.

        A feature with no part within radius_m is left out, however near its box comes."""
        lon = geodesy.wrap_lon(lon)
        out: dict[str, Near] = {}
        areas = [a for a in areas if a.record.get("bbox") is not None]
        if not areas:
            return out
        boxes = np.array([a.record["bbox"] for a in areas], dtype=np.float64).reshape(-1, 4)
        lower = self._box_distance_m(boxes, lat, lon)
        single_point = (boxes[:, 0] == boxes[:, 2]) & (boxes[:, 1] == boxes[:, 3])
        geometry: dict[str, str] = {}
        levels: dict[int, list] = {}
        here = None
        points, exact, drawn = [], [], {}
        for k, a in enumerate(areas):
            if lower[k] > radius_m:
                continue
            if single_point[k]:
                points.append(k)
                continue
            if a.layer not in geometry:
                geometry[a.layer] = self._geometry_of(a.layer)
            is_area = geometry[a.layer] == "area"
            if is_area and lower[k] == 0.0:
                if here is None:
                    here = {f.id for f in self.at(lat, lon)}
                if a.id in here:
                    out[a.id] = Near(a, 0.0, 0.0, lat, lon, True)
                    continue
            if a.pack not in levels:   # coarsest first
                levels[a.pack] = sorted(self._indexes[a.pack].pack.drawing_levels.values(),
                                        key=lambda d: -d.get("tolerance_m", 0.0))
            allowed = DRAWN_SHARE * max(float(lower[k]), VIEW_SHARE * radius_m)
            fits = [d for d in levels[a.pack] if ("layers" not in d or a.layer in d["layers"])
                    and (not is_area or a.area_km2 >= d.get("min_km2", 0))]
            draw = next((d for d in fits if d.get("tolerance_m", 0.0) <= allowed), None)
            if draw is None and lower[k] > NEAR_EXACT_M and fits:
                draw = fits[-1]
            if draw is not None:
                drawn.setdefault((a.pack, draw["id"]), (draw, {}))[1][a.number] = a
            else:
                exact.append(k)
        if points:
            rows = np.array(points, dtype=np.intp)
            dist, bear = geodesy.inverse_many(lat, lon, boxes[rows, 1], boxes[rows, 0])
            for k, d, b in zip(points, dist.tolist(), bear.tolist()):
                if d <= radius_m:
                    out[areas[k].id] = Near(areas[k], d, 0.0 if d == 0.0 else b, float(boxes[k, 1]),
                                            float(boxes[k, 0]), d == 0.0)
        row = {a.id: k for k, a in enumerate(areas)}
        for (p, _ident), (draw, wanted) in drawn.items():
            for identifier, near in self._nearest_drawn(p, draw, wanted, lat, lon, radius_m).items():
                if near.distance_m == 0.0 and geometry[near.area.layer] == "area":
                    exact.append(row[identifier])   # a drawn outline round you, of an area you are not in
                else:
                    out[identifier] = near
        flat = Flat(lat, lon)
        for k in exact:
            found = self._nearest(areas[k].pack, areas[k], flat, lat, lon, float(lower[k]), radius_m)
            if found is not None:
                out[found.area.id] = found
        return out

    def _nearest_drawn(self, p: int, draw: dict, wanted: dict, lat: float, lon: float,
                       radius_m: float) -> dict[str, Near]:
        """nearest_many's third way: the features by number, from one drawing level's tiles."""
        import shapely

        index = self._indexes[p]
        level = draw["tile_level"]
        boxes = np.array([a.record["bbox"] for a in wanted.values()], dtype=np.float64).reshape(-1, 4)
        shapes, owners = [], []
        seen = set()
        for west, south, east, north in self._search_box(lat, lon, radius_m, (-180.0, -90.0, 180.0, 90.0)):
            x0, y0 = tiles.tile_of(west, south, level)
            x1, y1 = tiles.tile_of(east, north, level)
            for x, y in index.tiles_in("draw", draw["id"], x0, x1, y0, y1):
                if (x, y) in seen:
                    continue
                seen.add((x, y))
                if not _boxes_reach(boxes, [tiles.tile_box(level, x, y)]).any():
                    continue   # none of the features is there: the tile is not read
                data = self._tile(p, "draw", draw["id"], x, y)
                # Whichever is fewer is gone through: a tile may hold thousands of roads.
                if len(wanted) < len(data.by_feature):
                    here = [n for n in wanted if n in data.by_feature]
                else:
                    here = [n for n in data.by_feature if n in wanted]
                if not here:
                    continue
                entries = [i for n in here for i in data.by_feature[n]]
                geoms = data.shapes_of(entries, tiles.tile_box(level, x, y))
                for n in here:
                    for i in data.by_feature[n]:
                        shapes.append(geoms[i])
                        owners.append(n)
        if not shapes:
            return {}
        view = Flat(lat, lon, azimuthal=True)
        projected = view.transform(np.array(shapes, dtype=object))
        origin = shapely.Point(0.0, 0.0)
        gap = np.nan_to_num(shapely.distance(origin, projected), nan=np.inf)
        owners = np.array(owners, dtype=np.intp)
        order = np.lexsort((gap, owners))
        _numbers, first = np.unique(owners[order], return_index=True)
        best = order[first]
        best = best[np.isfinite(gap[best])]
        if not len(best):
            return {}
        ends = shapely.get_coordinates(shapely.shortest_line(origin, projected[best]))[1::2]
        n_lat, n_lon = (np.asarray(v, dtype=np.float64) for v in view.inverse(ends[:, 0], ends[:, 1]))
        dist, bear = geodesy.inverse_many(lat, lon, n_lat, n_lon)
        out = {}
        for b, d, bearing, a_lat, a_lon in zip(owners[best].tolist(), dist.tolist(), bear.tolist(), n_lat.tolist(),
                                               n_lon.tolist()):
            if d <= radius_m:
                area = wanted[b]
                out[area.id] = Near(area, d, bearing, a_lat, a_lon, False)
        return out

    def _nearest(self, p: int, area: Area, flat: Flat, lat: float, lon: float,
                 lower: float, radius_m: float, border: bool = False) -> Near | None:
        r = max(lower * 1.25, FIRST_SEARCH_M)
        while True:
            r = min(r, radius_m)
            best = self._search(p, area, flat, lat, lon, r, lower, border)
            if best is not None and best[0] <= r:
                break
            if r >= radius_m:
                return None
            r *= SEARCH_GROWTH
        _, x, y, on_border = best
        inside = best[0] == 0.0 or on_border
        if best[0] == 0.0:
            n_lat, n_lon = lat, lon
        else:
            n_lat, n_lon = (float(v) for v in flat.inverse(x, y))
        distance, bearing, _arrival = geodesy.inverse(lat, lon, n_lat, n_lon)
        if distance > radius_m:
            return None
        return Near(area, distance, 0.0 if best[0] == 0.0 else bearing, n_lat, n_lon, inside)

    def _search(self, p: int, area: Area, flat: Flat, lat: float, lon: float, r: float, lower: float,
                border: bool = False):
        """The nearest point of the area's shapes in tiles within r metres:
        (distance in the flat view, x, y), or None if there is none."""
        import shapely

        index = self._indexes[p]
        draw = index.finest_drawing
        if draw is not None and lower > NEAR_EXACT_M and area.area_km2 >= draw.get("min_km2", 0):
            kinds = [("draw", draw["id"], draw["tile_level"])]
        else:
            kinds = [("tile", level, level) for level in index.pack.tile_levels]
        origin = shapely.Point(0.0, 0.0)
        parts = []   # (data, entry, where, box)
        for west, south, east, north in self._search_box(lat, lon, r, area.record["bbox"]):
            for kind, ident, level in kinds:
                x0, y0 = tiles.tile_of(west, south, level)
                x1, y1 = tiles.tile_of(east, north, level)
                for x, y in index.tiles_in(kind, ident, x0, x1, y0, y1):
                    data = self._tile(p, kind, ident, x, y)
                    for i in data.by_feature.get(area.number, ()):
                        parts.append((data, i, (x, y, level)))
        if not parts:
            return None
        # Each part's box first, nearest first: a part whose box is further than the best point found so far
        # cannot hold a nearer one, so it is never put into the flat view, which was most of the time Nearby
        # took at wide zooms, refilled after every move (17 November 2026). The bound and the flat view each
        # differ from the true distance by a few percent, so a part is skipped only with a tenth to spare.
        boxes = np.array([self._part_box(data, i, where) for data, i, where in parts], dtype=np.float64)
        bound = self._box_distance_m(boxes, lat, lon)
        best = None
        for k in np.argsort(bound, kind="stable").tolist():
            if best is not None and bound[k] > best[0] * PART_SKIP_MARGIN:
                break
            data, i, where = parts[k]
            found = self._part_distance(data, i, where, flat, lat, lon, origin, border)
            if found is not None and (best is None or found[0] < best[0]):
                best = found
        return best

    def _part_box(self, data: TileData, i: int, where) -> tuple[float, float, float, float]:
        """A part's box (west, south, east, north): the pack tile's for a covered note, else its shape's."""
        import shapely

        if data.entries[i].kind == tiles.COVERED:
            x, y, level = where
            return tiles.tile_box(level, x, y)
        with self._shapes:
            shape = data.shape(i)
        return tuple(shapely.bounds(shape).tolist())

    def _part_distance(self, data: TileData, i: int, where, flat: Flat, lat: float, lon: float, origin,
                       border: bool = False):
        import shapely

        x, y, level = where
        entry = data.entries[i]
        if entry.kind == tiles.COVERED:
            if border:   # a tile wholly inside the area has no border in it
                return None
            west, south, east, north = tiles.tile_box(level, x, y)
            n_lat = min(max(lat, south), north)
            if west <= lon <= east:
                n_lon = lon
            else:
                n_lon = west if ((west - lon) % 360.0) <= ((lon - east) % 360.0) else east
            px, py = (float(v) for v in flat.forward(n_lat, n_lon))
            return math.hypot(px, py), px, py, False
        with self._shapes:
            shape = data.shape(i)
            inside = shapely.intersects_xy(shape, lon, lat)
        if inside and not border:
            return 0.0, 0.0, 0.0, False
        if border:   # the area's own boundary: not the cuts along the tile's edges
            import shapely.geometry as sg
            west, south, east, north = tiles.tile_box(level, x, y)
            cuts = sg.box(west, south, east, north).boundary.buffer(1e-6)
            shape = shapely.difference(shape.boundary, cuts)
            if shape.is_empty:
                return None
        projected = flat.transform(shape)
        distance = float(shapely.distance(origin, projected))
        line = shapely.shortest_line(origin, projected)
        x1, y1 = shapely.get_coordinates(line)[-1]
        return distance, float(x1), float(y1), bool(border and inside)
