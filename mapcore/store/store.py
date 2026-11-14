"""The store over the installed packs: "where am I" and Nearby (P1-T5).

* at(lat, lon): every area at a point, from every layer, whatever the zoom
  (ANN-7), most specific first: by rank (a higher rank is more specific, such
  as a county above a country), then smallest area first (LOC-2).
* nearby(lat, lon, radius_m): the areas within a radius, each with its
  nearest point, and the distance and bearing to it (INF-3, INF-7).
* feature(id): a feature record by its identifier.

Phase 1 has one pack. The store keeps a list of packs and asks which of them
covers a point, so Phase 4 can add pack tile coverage and let the most
detailed pack win (AD-14).

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
from dataclasses import dataclass

import numpy as np

from mapcore import search
from mapcore.geo import geodesy
from mapcore.packs import tiles
from mapcore.packs.pack import DamagedRecord, Pack
from mapcore.store.cache import TileCache, TileData
from mapcore.store.projection import Flat

NEAR_EXACT_M = 50_000.0
FIRST_SEARCH_M = 2_000.0   # the first search box for an area's nearest point
SEARCH_GROWTH = 3.0
M_PER_DEG_LAT_MIN = 110_574.0  # the shortest degree of latitude, at the equator


@dataclass(frozen=True)
class Area:
    """A feature at a point, with its record (docs/developer/pack-format.md)."""
    pack: int
    number: int
    record: dict

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
    def name(self) -> str:
        names = self.record["names"]
        return names.get("en") or next(iter(names.values()), self.record["id"])


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


def _record_name(rec: dict) -> str:
    names = rec.get("names") or {}
    return names.get("en") or next(iter(names.values()), rec["id"])


TREE_LAYERS = ("continents", "countries", "regions", "counties")   # the layers of the world tree (P3-T9a)


def special_kind(rec: dict) -> str | None:
    """"unclaimed" for land in no country, "disputed" for land more than one party holds or claims, else None
    (P3-T16a, ANN-6, DAT-8, LOC-6)."""
    if rec.get("type") == "unclaimed land":
        return "unclaimed"
    if rec.get("disputed") or rec.get("type") == "disputed land":
        return "disputed"
    return None


def _boxes_meet(a, b) -> bool:
    """Whether two boxes (west, south, east, north) share any ground; west greater than east is a box across
    the 180 degree line (AD-17)."""
    if a[3] < b[1] or b[3] < a[1]:
        return False

    def spans(box):
        return [(box[0], box[2])] if box[0] <= box[2] else [(box[0], 180.0), (-180.0, box[2])]

    return any(x0 <= y1 and y0 <= x1 for x0, x1 in spans(a) for y0, y1 in spans(b))


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
    a = math.radians(lat)
    b = math.radians(plat)
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(plon - lon) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(min(1.0, math.sqrt(h))) <= metres


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


class _PackIndex:
    """What the store keeps about one pack: its features' boxes, and which pack tiles exist."""

    def __init__(self, pack: Pack, problems):
        self.pack = pack
        self.problems = problems
        self._boxes = None
        self._sizes = None
        self._ids = None
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

    def _read_table(self) -> None:
        numbers, box, widths, layer_of, ids = [], [], [], [], []
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
        self._ids = np.array(ids, dtype=object)
        self._sizes = (np.array(widths, dtype=np.float64), np.array(layer_of, dtype=object))
        self._boxes = (np.array(numbers, dtype=np.intp), np.array(box, dtype=np.float64).reshape(-1, 4))

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
        self._tree_children: dict[str, list[tuple[str, str]]] | None = None   # the world tree (P3-T9a)
        # A tile's shapes are shared and prepared, and Shapely builds a prepared shape's index on
        # its first use, which is not safe from two threads at once: the Crossed and passed
        # search and a step's lookup together made Windows stop the program (P2-T17w). Every
        # use of a tile's shape is under this lock, one shape test at a time, so a step never
        # waits for a whole search.
        self._shapes = threading.Lock()
        for p in packs if isinstance(packs, (list, tuple)) else [packs]:
            pack = p if isinstance(p, Pack) else Pack(p)
            self._indexes.append(_PackIndex(pack, self.problems))

    @property
    def packs(self) -> list[Pack]:
        return [i.pack for i in self._indexes]

    def close(self) -> None:
        for i in self._indexes:
            i.pack.close()

    def _note(self, exc: DamagedRecord) -> None:
        if exc.message not in self.problems:
            self.problems.append(exc.message)

    # Reading tiles -------------------------------------------------------------

    def _covering(self, lat: float, lon: float) -> list[int]:
        """The packs that cover a point, the one to use first. Phase 1: a
        world pack covers everywhere, and the first one installed is used."""
        return list(range(len(self._indexes)))

    def _tile(self, p: int, kind: str, level: int, x: int, y: int) -> TileData:
        """The tile entries of a pack tile ("tile") or drawing tile ("draw"), cached."""
        index = self._indexes[p]

        def load() -> TileData:
            try:
                read = index.pack.tile if kind == "tile" else index.pack.drawing_tile
                return TileData(read(level, x, y))
            except DamagedRecord as exc:
                self._note(exc)
                return TileData([])

        return self.cache.get((p, kind, level, x, y), load)

    def warm(self, lat: float, lon: float, around: int = 1) -> int:
        """Read the pack tiles round a point into the cache, at every tile
        level. Returns how many were read."""
        lon = geodesy.wrap_lon(lon)
        count = 0
        for p in self._covering(lat, lon)[:1]:
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

    def feature(self, identifier: str) -> Area | None:
        """The area with this identifier, or None."""
        for p in range(len(self._indexes)):
            pack = self._indexes[p].pack
            try:
                number = pack.feature_number(identifier)
                if number is not None:
                    return Area(p, number, pack.feature(number))
            except DamagedRecord as exc:
                self._note(exc)
        return None

    def relationships(self, identifier: str) -> dict:
        """A feature's stored relationships (P3-T3e, architecture 6.5), from the first pack that has the
        feature: in, same, overlaps, partly, next, near, crosses, crossed_by, along, water_in and counts, by
        the other features' identifiers. docs/developer/pack-format.md, relations/G, says what each holds.
        Empty for a feature with none, one not found, or a pack written before format 4."""
        for p in range(len(self._indexes)):
            pack = self._indexes[p].pack
            try:
                if pack.feature_number(identifier) is not None:
                    return pack.relationships(identifier)
            except DamagedRecord as exc:
                self._note(exc)
                return {}
        return {}

    def _area(self, p: int, number: int) -> Area | None:
        try:
            return Area(p, number, self._indexes[p].pack.feature(number))
        except DamagedRecord as exc:
            self._note(exc)
            return None

    # What is at a point ------------------------------------------------------------

    def at(self, lat: float, lon: float, layers=None) -> list[Area]:
        """Every area at the point, most specific first (LOC-2): by rank, higher
        first, then smallest area. `layers` limits the answer to some layer ids."""
        import shapely

        lon = geodesy.wrap_lon(lon)
        found: dict[tuple[int, int], Area] = {}
        for p in self._covering(lat, lon)[:1]:
            index = self._indexes[p]
            for level in index.pack.tile_levels:
                x, y = tiles.tile_of(lon, lat, level)
                if (x, y) not in self._indexes[p].stored("tile", level):
                    continue
                data = self._tile(p, "tile", level, x, y)
                for i, entry in enumerate(data.entries):
                    if (p, entry.feature) in found or entry.kind not in tiles.AREA_KINDS:
                        continue   # lines and points have no inside, so are never "here"
                    if entry.kind != tiles.COVERED:
                        with self._shapes:
                            inside = shapely.intersects_xy(data.shape(i), lon, lat)
                        if not inside:
                            continue
                    area = self._area(p, entry.feature)
                    if area is not None and (layers is None or area.layer in layers):
                        found[(p, entry.feature)] = area
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
        for p in range(len(self._indexes)):
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
                                along = _along_m(path, point[1], point[0])
                                old = found.get((p, entry.feature))
                                if old is None or along < old.along_m:
                                    found[(p, entry.feature)] = Crossing(area, point[1], point[0], along)
        return sorted(found.values(), key=lambda c: (c.along_m, c.area.id))

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
        ends = {(a.pack, a.number) for a in self.at(*start) + self.at(*end)}
        over: dict[tuple[int, int], Passed] = {}
        near: dict[tuple[int, int], Passed] = {}
        dlat = passed_m / M_PER_DEG_LAT_MIN
        for p in range(len(self._indexes)):
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
        out += over.values()
        out += near.values()
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
        results: list[Near] = []
        for p in self._covering(lat, lon)[:1]:
            numbers, boxes = self._indexes[p].boxes
            bound = self._box_distance_m(boxes, lat, lon)
            order = np.argsort(bound, kind="stable")
            for k in order.tolist():
                if bound[k] > radius_m:
                    break
                if len(results) >= limit and results[limit - 1].distance_m <= bound[k]:
                    break
                area = self._area(p, int(numbers[k]))
                if area is None or area.id in exclude or (layers is not None and area.layer not in layers) \
                        or (accept is not None and not accept(area)):
                    continue
                found = self._nearest(p, area, flat, lat, lon, float(bound[k]), radius_m)
                if found is not None:
                    results.append(found)
                    results.sort(key=lambda n: (n.distance_m, n.area.id))
        return results[:limit]

    # Search (P3-T8b, SRB-1, SRB-2, architecture 7.9) ------------------------------------------------------

    def search(self, text: str, limit: int = 20, layers=None, near: tuple[float, float, float] | None = None,
               inside: str | None = None) -> list[Found]:
        """Features whose names match what was typed, best first: by how well they match, then by importance
        (mapcore.search). Only the search records of the words typed are read, never the whole index.

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
                        order = search.rank_key(level, similar, row[search.IMPORTANCE], row[search.NAME],
                                                row[search.ID])
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
        name (SRB-3): under the world, the continents; under a continent, the countries that are in it or
        lie mostly or partly across it (Russia is under Europe and Asia); under a country, an area of the
        countries, regions or counties layer that has it as a parent, or as the sovereign of a distant
        part (Hawaii under the United States), and under a constituent country, such as England, its own
        areas. The first call scans the feature records of those layers once; the rest take no reading."""
        with self._lock:
            if self._tree_children is None:
                self._tree_children = self._build_tree()
            return list(self._tree_children.get(identifier, ()))

    def _build_tree(self) -> dict[str, list[tuple[str, str]]]:
        rows: dict[str, dict] = {}
        for index in self._indexes:
            try:
                for rec in index.pack.scan(TREE_LAYERS):
                    rows.setdefault(rec["id"], rec)
            except DamagedRecord as exc:
                self._note(exc)
        tree: dict[str, set] = {}

        def add(parent: str, identifier: str) -> None:
            tree.setdefault(parent, set()).add(identifier)

        for identifier, rec in rows.items():
            layer = rec["layer"]
            if layer == "continents":
                add("world", identifier)
            elif layer != "countries":
                for parent in rec.get("parents", ()):
                    if parent in rows:
                        add(parent, identifier)
                    break
            else:
                self._place_country(identifier, rec, rows, add)
        for identifier, rec in rows.items():   # the two lists of land that is not plainly one country's (P3-T16a)
            kind = special_kind(rec)
            if kind:
                add("special:" + kind, identifier)
        return {parent: sorted(((i, _record_name(rows[i])) for i in members),
                               key=lambda t: (t[1].casefold(), t[0]))
                for parent, members in tree.items()}

    def special_areas(self, kind: str, inside: str | None = None) -> list[Found]:
        """The disputed areas or unclaimed areas (kind "disputed" or "unclaimed"), by name, as search results,
        all of them or only those the stored relationships put inside, partly inside or crossing a feature."""
        out = []
        for identifier, name in self.tree_children("special:" + kind):
            rec = self.feature(identifier)
            point = rec.record.get("point") if rec is not None else None
            out.append(Found(0, identifier, name, rec.layer if rec is not None else "countries", 0,
                             point[1] if point else None, point[0] if point else None, name, "", 0, 1.0))
        if inside is None:
            return out
        return self._inside(out, inside, len(out))

    def _place_country(self, identifier: str, rec: dict, rows: dict, add) -> None:
        """An area of the countries layer goes under its sovereign, if it is a distant part; else under the
        country that holds it, if it is a constituent country; else under each continent it is in, or that
        it is mostly or partly across (a tenth of it, or the one with most of it)."""
        sovereign = rec.get("sovereign_id")
        if sovereign and sovereign in rows and sovereign != identifier:
            add(sovereign, identifier)
            return
        rel = self.relationships(identifier)
        same = set(rel.get("same", ()))
        for holder in rel.get("in", ()):
            if holder in rows and holder not in same and rows[holder]["layer"] == "countries":
                add(holder, identifier)
                return
        continents = [i for i in rel.get("in", ()) if i in rows and rows[i]["layer"] == "continents"]
        if not continents:
            across = [(o[1], o[0]) for o in rel.get("overlaps", ()) if o[0] in rows and rows[o[0]]["layer"] == "continents"]
            continents = [c for share, c in across if share >= 0.1] or [c for _s, c in sorted(across, reverse=True)[:1]]
        for continent in continents:
            add(continent, identifier)

    def browse(self, layer: str, identifier: str) -> list[Found]:
        """Every feature of a layer inside a feature, fully or partly, or crossing it (SRB-4), by name, with no
        limit by zoom: such as every lake in Finland. The layer's feature records are read in a scan, each
        first tested against the feature's box, and only the ones that may be inside have their stored
        relationships read."""
        holder = self.feature(identifier)
        if holder is None:
            return []
        box = holder.record.get("bbox")
        out: list[Found] = []
        for p, index in enumerate(self._indexes):
            try:
                for rec in index.pack.scan((layer,)):
                    if rec["id"] == identifier or (box is not None and rec.get("bbox") is not None
                                                   and not _boxes_meet(box, rec["bbox"])):
                        continue
                    rel = self.relationships(rec["id"])
                    if identifier in rel.get("in", ()) or identifier in rel.get("same", ())                             or identifier in rel.get("crosses", ())                             or any(x[0] == identifier for x in (*rel.get("partly", ()), *rel.get("overlaps", ()))):
                        point = rec.get("point")
                        name = _record_name(rec)
                        out.append(Found(p, rec["id"], name, layer, 0, point[1] if point else None,
                                         point[0] if point else None, name, "", 0, 1.0))
            except DamagedRecord as exc:
                self._note(exc)
        out.sort(key=lambda f: (f.name.casefold(), f.id))
        return out

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
            rel = self.relationships(f.id)
            if identifier in rel.get("in", ()) or identifier in rel.get("same", ()) \
                    or identifier in rel.get("crosses", ()) \
                    or any(x[0] == identifier for x in (*rel.get("partly", ()), *rel.get("overlaps", ()))):
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
        best = None
        for west, south, east, north in self._search_box(lat, lon, r, area.record["bbox"]):
            for kind, ident, level in kinds:
                x0, y0 = tiles.tile_of(west, south, level)
                x1, y1 = tiles.tile_of(east, north, level)
                for x, y in index.tiles_in(kind, ident, x0, x1, y0, y1):
                    data = self._tile(p, kind, ident, x, y)
                    for i in data.by_feature.get(area.number, ()):
                        found = self._part_distance(data, i, (x, y, level), flat, lat, lon, origin, border)
                        if found is not None and (best is None or found[0] < best[0]):
                            best = found
        return best

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
