"""The counties layer, by the rule agreed in discussion point 101 (architecture 6.12).

OSM does not use the same admin level for counties everywhere. The counties
layer uses level 6. Where level 6 leaves land uncovered, the gap is filled by
the next level down that covers it, level 7 and then level 8. Where nothing
below covers it, the region itself is used.

The levels that make up each country's counties are kept in a record,
mapdata/config/county_levels.yaml, so they are not worked out again on every
build. A record can be corrected by hand for one country (for example if it
uses level 9); a corrected record is used as it is and never overwritten.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely
import yaml

from mapdata.stages.geodesy import area_km2, areas_km2

DEFAULT_LEVELS = [6, 7, 8]
GAP_KM2 = 1.0          # gaps smaller than this are slivers, not missing counties
SHARE_IN_GAP = 0.5     # an area fills a gap if at least half of its land lies in the gap


@dataclass
class County:
    area: object          # boundaries.Area
    geom: object          # its land
    level: int            # admin level, or the region's level when the region is used
    region_fill: bool = False


@dataclass
class Result:
    counties: list[County]
    levels_used: list[int]
    regions_used: list[str]
    filled: list[str] = field(default_factory=list)   # lines for the quality report
    left_km2: float = 0.0


METHODS = ("whole-gap", "nearby-gap", "covered-first", "gap-land")
DEFAULT_METHOD = "gap-land"   # the fastest in the build speed trials (P1-T16), with the same counties
GAP_CELL = 0.25        # degrees: the gap is cut into squares this size by the nearby methods


class Timer:
    """Seconds spent in each part of a step, for the build speed trials (P1-T16)."""

    def __init__(self):
        self.seconds: dict[str, float] = {}
        self.calls: dict[str, int] = {}

    def add(self, part: str, seconds: float) -> None:
        self.seconds[part] = self.seconds.get(part, 0.0) + seconds
        self.calls[part] = self.calls.get(part, 0) + 1

    def timed(self, part: str, fn, *args):
        start = time.perf_counter()
        try:
            return fn(*args)
        finally:
            self.add(part, time.perf_counter() - start)


def build(country_raw, regions: list, candidates: dict[int, list], clip, levels: list[int],
          english=lambda a: a.name, region_fill: bool = True, method: str = DEFAULT_METHOD,
          timer: Timer | None = None) -> Result:
    """Choose the counties of one country.

    country_raw: the country's shape as read (in the area checked).
    regions: [(Area, land)] at the region level, used where nothing else covers.
    candidates: {level: [Area]} with their shapes as read, not yet cut to the land.
    clip: a function giving the land of a shape.
    method: how each area is measured against the gap (the build speed trials, P1-T16):
      "whole-gap": against the whole gap, cut to the land (spike S2);
      "nearby-gap": against only the squares of the gap it touches, as read;
      "covered-first": as nearby-gap, but an area wholly inside one already
      chosen is passed over at once, without being cut to the land.
    All three choose the same counties.
    """
    if method not in METHODS:
        raise ValueError(f"No counties method called {method!r}. The methods are {', '.join(METHODS)}.")
    timer = timer or Timer()
    if method == "whole-gap":
        return _build_whole(country_raw, regions, candidates, clip, levels, english, region_fill, timer)
    if method == "gap-land":
        return _build_gap_land(country_raw, regions, candidates, clip, levels, english, region_fill, timer)
    return _build_nearby(country_raw, regions, candidates, clip, levels, english, region_fill, timer,
                         covered_first=method == "covered-first")


def _build_whole(country_raw, regions, candidates, clip, levels, english, region_fill, timer) -> Result:
    """Spike S2's method.

    Gaps are found from the shapes as read, which have few points at sea, and
    only the gap is cut to the land. Joining hundreds of shapes already cut to
    a detailed coast, such as Norway's municipalities, took over half an hour.
    But each area is then measured against the whole gap, and France's gap
    after level 6 has 195,763 parts.
    """
    chosen: list[County] = []
    levels_used: list[int] = []
    filled: list[str] = []

    def gap_now():
        if not chosen:
            return country_raw, clip(country_raw)
        raw = shapely.difference(country_raw, shapely.union_all([c.area.geom for c in chosen]))
        return raw, (clip(raw) if not raw.is_empty else raw)

    for level in levels:
        cands = candidates.get(level, [])
        if not cands:
            continue
        if chosen:
            gap_raw, gap = timer.timed("finding the gap and cutting it to the land", gap_now)
            if gap.is_empty or area_km2(gap) < GAP_KM2:
                gap = None
                break
            shapely.prepare(gap_raw)
        else:
            gap_raw = gap = None
        took = 0
        for a in cands:
            if gap_raw is not None and not shapely.intersects(gap_raw, a.geom):
                continue
            land = timer.timed("cutting areas to the land", clip, a.geom)
            if land.is_empty:
                continue
            if gap is not None:
                t = time.perf_counter()
                inside = area_km2(shapely.intersection(land, gap))
                total = area_km2(land)
                timer.add("measuring areas against the gap", time.perf_counter() - t)
                if total <= 0 or inside < SHARE_IN_GAP * total:
                    continue
                filled.append(f"Level {level} fills a gap: {english(a)}, {inside:,.0f} km2.")
            chosen.append(County(a, land, level))
            took += 1
        if took:
            levels_used.append(level)
    regions_used: list[str] = []
    _raw, gap = timer.timed("finding the gap and cutting it to the land", gap_now)
    t = time.perf_counter()
    left = area_km2(gap) if not gap.is_empty else 0.0
    if region_fill and left >= GAP_KM2:
        for region, land in regions:
            part = shapely.intersection(land, gap)
            if part.is_empty:
                continue
            km2 = area_km2(part)
            if km2 < GAP_KM2:
                continue
            part = _areas(part)
            chosen.append(County(region, part, region.level, region_fill=True))
            regions_used.append(region.id)
            filled.append(f"No county covers {km2:,.0f} km2 of {english(region)}, so the region itself is used there.")
            left -= km2
    timer.add("regions used as their own county", time.perf_counter() - t)
    return Result(chosen, levels_used, regions_used, filled, max(0.0, left))


class GapSquares:
    """The gap as read, cut into squares, with a spatial index.

    Cutting to the land only removes sea. So for a shape already cut to the
    land, its land in the gap is the same as its land in the gap as read, and
    the gap itself never has to be cut to the land in one go. Each area is
    measured only against the squares of the gap it touches.
    """

    def __init__(self, gap_raw, cell: float = GAP_CELL):
        import math

        self.raw = gap_raw
        out = []
        for p in shapely.get_parts(gap_raw):
            if p.is_empty or p.geom_type not in ("Polygon", "MultiPolygon"):
                continue
            w, s, e, n = p.bounds
            i0, i1, j0, j1 = math.floor(w / cell), math.floor(e / cell), math.floor(s / cell), math.floor(n / cell)
            if i0 == i1 and j0 == j1:
                out.append(p)
                continue
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    box = (i * cell, j * cell, (i + 1) * cell, (j + 1) * cell)
                    q = shapely.clip_by_rect(p, *box)
                    if not q.is_empty and not q.is_valid:
                        q = shapely.intersection(p, shapely.box(*box))
                    out.extend(r for r in shapely.get_parts(_areas(q)) if not r.is_empty)
        self.squares = np.array(out, dtype=object)
        self.tree = shapely.STRtree(self.squares)

    def touched(self, geoms: list) -> np.ndarray:
        """Which of the shapes touch the gap."""
        hit = np.zeros(len(geoms), dtype=bool)
        if len(self.squares) and len(geoms):
            idx = self.tree.query(np.array(geoms, dtype=object), predicate="intersects")[0]
            hit[np.unique(idx)] = True
        return hit

    def inside_km2(self, land) -> float:
        """Square kilometres of a shape that are in the gap."""
        idx = self.tree.query(land, predicate="intersects")
        if len(idx) == 0:
            return 0.0
        cut = [_areas(c) for c in shapely.intersection(land, self.squares[idx])]
        return float(areas_km2(np.array(cut, dtype=object)).sum())

    def land_km2(self, clip, stop_above: float | None = None) -> float:
        """Square kilometres of land in the gap, largest squares first.

        With stop_above, it stops once the sum is more than that, which is
        enough to know the gap is more than slivers. A square has no more land
        than its own area, so if all of them together are smaller, none is cut.
        """
        if not len(self.squares):
            return 0.0
        raw = areas_km2(self.squares)
        if stop_above is not None and float(raw.sum()) <= stop_above:
            return float(raw.sum())
        total = 0.0
        for i in np.argsort(-raw):
            land = clip(self.squares[i])
            if not land.is_empty:
                total += area_km2(land)
            if stop_above is not None and total > stop_above:
                break
        return total


def join(geoms: list):
    """The union of shapes as read.

    Areas of one level usually meet only along their edges, and then the
    union made for such shapes (coverage union) is much faster: Belgium's
    provinces in 0.1 seconds instead of 0.9. If any two overlap, its result
    has less area than the shapes together, and the general union is used.
    """
    geoms = [g for g in geoms if not g.is_empty]
    if not geoms:
        return shapely.Polygon()
    if len(geoms) == 1:
        return geoms[0]
    try:
        out = shapely.coverage_union_all(geoms)
        whole = sum(g.area for g in geoms)
        if out.is_valid and abs(out.area - whole) <= 1e-9 * max(whole, 1e-12):
            return out
    except shapely.errors.GEOSException:
        pass
    return shapely.union_all(geoms)


class GapLand:
    """The gap's land, cut to the land a square at a time, with a spatial index.

    An area's land in the gap is found without cutting the area to the land:
    the areas already chosen near it are taken away from it as read, which
    is quick because shapes as read have few points at sea and the result
    is small, and only what is left is measured against the gap's land.
    Cutting to the land only removes sea, so this gives exactly the same
    figure. An area with no land in the gap is passed over at once.

    Each separate part of the gap's land has its own place in the index.
    Mainland France's gap after level 6 is 26 km2 of land, but in 186,891
    slivers along the coast with 1.2 million points.
    """

    def __init__(self, gap_raw, clip, chosen_raw: list, cell: float = GAP_CELL):
        self.raw = gap_raw
        squares = GapSquares(gap_raw, cell).squares
        land = [clip(s) for s in squares]
        parts = [p for g in land if not g.is_empty for p in shapely.get_parts(g)
                 if p.geom_type == "Polygon" and not p.is_empty]
        self.land = np.array(parts, dtype=object)
        self.tree = shapely.STRtree(self.land)
        self.km2 = float(areas_km2(self.land).sum()) if len(self.land) else 0.0
        self.chosen = np.array([g for g in chosen_raw if not g.is_empty], dtype=object)
        self.chosen_tree = shapely.STRtree(self.chosen)

    def touched(self, geoms: list) -> np.ndarray:
        """Which of the shapes touch the gap's land."""
        hit = np.zeros(len(geoms), dtype=bool)
        if len(self.land) and len(geoms):
            idx = self.tree.query(np.array(geoms, dtype=object), predicate="intersects")[0]
            hit[np.unique(idx)] = True
        return hit

    def inside_km2(self, raw) -> float:
        """Square kilometres of the gap's land inside a shape as read."""
        if not len(self.land):
            return 0.0
        rest = raw
        near = self.chosen[self.chosen_tree.query(raw, predicate="intersects")]
        if len(near) > 2:
            # A region, with many areas chosen in it: joining them first is
            # quicker (mainland France's regions in 12 seconds, against 40).
            return self._measure(shapely.difference(raw, join(list(near))))
        # An area with one or two chosen nearby: each is taken away in turn,
        # cut first to a rectangle round what is left, so a whole French
        # département is never handled for one small municipality (31
        # seconds for mainland France's, against 45).
        for g in near:
            if rest.is_empty:
                break
            w, s, e, n = rest.bounds
            pad = 1e-6
            local = shapely.clip_by_rect(g, w - pad, s - pad, e + pad, n + pad)
            if not local.is_valid:
                local = shapely.intersection(g, shapely.box(w - pad, s - pad, e + pad, n + pad))
            rest = shapely.difference(rest, local)
        return self._measure(rest)

    def _measure(self, rest) -> float:
        """Square kilometres of the gap's land in a shape that holds no chosen area."""
        parts = shapely.get_parts(_areas(rest))
        parts = parts[~shapely.is_empty(parts)]
        if not len(parts):
            return 0.0
        i, j = self.tree.query(parts, predicate="intersects")
        if not len(i):
            return 0.0
        cut = [_areas(c) for c in shapely.intersection(parts[i], self.land[j])]
        return float(areas_km2(np.array(cut, dtype=object)).sum())


def _build_gap_land(country_raw, regions, candidates, clip, levels, english, region_fill, timer) -> Result:
    """The gap-land method: the gap is cut to the land once, and areas are
    measured as read against it (P1-T16)."""
    chosen: list[County] = []
    levels_used: list[int] = []
    filled: list[str] = []
    gap = None

    def gap_land():
        raw = country_raw
        chosen_raw = [c.area.geom for c in chosen]
        if chosen:
            raw = timer.timed("joining the chosen areas", join, chosen_raw)
            raw = timer.timed("finding the gap", shapely.difference, country_raw, raw)
        return timer.timed("cutting the gap to the land", GapLand, raw, clip, chosen_raw)

    for level in levels:
        cands = candidates.get(level, [])
        if not cands:
            continue
        hit = None
        if chosen:
            if gap is None:
                gap = gap_land()
            if gap.km2 < GAP_KM2:
                break
            hit = timer.timed("finding areas that touch the gap", gap.touched, [a.geom for a in cands])
        took = 0
        for i, a in enumerate(cands):
            if hit is not None and not hit[i]:
                continue
            if hit is not None:
                inside = timer.timed("measuring areas against the gap", gap.inside_km2, a.geom)
                if inside <= 0:
                    continue
            land = timer.timed("cutting areas to the land", clip, a.geom)
            if land.is_empty:
                continue
            if hit is not None:
                total = area_km2(land)
                if total <= 0 or inside < SHARE_IN_GAP * total:
                    continue
                filled.append(f"Level {level} fills a gap: {english(a)}, {inside:,.0f} km2.")
            chosen.append(County(a, land, level))
            took += 1
        if took:
            levels_used.append(level)
            gap = None   # the gap has changed
    regions_used: list[str] = []
    if gap is None:
        gap = gap_land()
    left = gap.km2
    t = time.perf_counter()
    if region_fill and left >= GAP_KM2:
        for region, land in regions:
            if shapely.is_empty(land):
                continue
            km2 = gap.inside_km2(region.geom)
            if km2 < GAP_KM2:
                continue
            # The shape is cut from the gap as read, so it has no edges along the squares.
            part = _areas(shapely.intersection(land, gap.raw))
            if part.is_empty:
                continue
            chosen.append(County(region, part, region.level, region_fill=True))
            regions_used.append(region.id)
            filled.append(f"No county covers {km2:,.0f} km2 of {english(region)}, so the region itself is used there.")
            left -= km2
    timer.add("regions used as their own county", time.perf_counter() - t)
    return Result(chosen, levels_used, regions_used, filled, max(0.0, left))


def _build_nearby(country_raw, regions, candidates, clip, levels, english, region_fill, timer,
                  covered_first: bool) -> Result:
    """The nearby methods: no step works on the whole gap at once (DP107)."""
    chosen: list[County] = []
    levels_used: list[int] = []
    filled: list[str] = []

    def gap_squares():
        raw = country_raw
        if chosen:
            raw = shapely.difference(country_raw, shapely.union_all([c.area.geom for c in chosen]))
        return GapSquares(raw)

    for level in levels:
        cands = candidates.get(level, [])
        if not cands:
            continue
        gap = hit = None
        if chosen:
            gap = timer.timed("finding the gap", gap_squares)
            if timer.timed("measuring the gap's land", gap.land_km2, clip, GAP_KM2) < GAP_KM2:
                break
            hit = timer.timed("finding areas that touch the gap", gap.touched, [a.geom for a in cands])
            if covered_first:
                t = time.perf_counter()
                tree = shapely.STRtree(np.array([c.area.geom for c in chosen], dtype=object))
                idx = tree.query(np.array([a.geom for a in cands], dtype=object), predicate="covered_by")[0]
                hit[np.unique(idx)] = False
                timer.add("passing over areas inside one already chosen", time.perf_counter() - t)
        took = 0
        for i, a in enumerate(cands):
            if hit is not None and not hit[i]:
                continue
            land = timer.timed("cutting areas to the land", clip, a.geom)
            if land.is_empty:
                continue
            if gap is not None:
                t = time.perf_counter()
                inside = gap.inside_km2(land)
                total = area_km2(land)
                timer.add("measuring areas against the gap", time.perf_counter() - t)
                if total <= 0 or inside < SHARE_IN_GAP * total:
                    continue
                filled.append(f"Level {level} fills a gap: {english(a)}, {inside:,.0f} km2.")
            chosen.append(County(a, land, level))
            took += 1
        if took:
            levels_used.append(level)
    regions_used: list[str] = []
    gap = timer.timed("finding the gap", gap_squares)
    left = timer.timed("measuring the gap's land", gap.land_km2, clip)
    t = time.perf_counter()
    if region_fill and left >= GAP_KM2:
        for region, land in regions:
            km2 = gap.inside_km2(land)
            if km2 < GAP_KM2:
                continue
            # The shape is cut from the gap as read, not from its squares,
            # so it has no edges along the squares.
            part = _areas(shapely.intersection(land, gap.raw))
            if part.is_empty:
                continue
            chosen.append(County(region, part, region.level, region_fill=True))
            regions_used.append(region.id)
            filled.append(f"No county covers {km2:,.0f} km2 of {english(region)}, so the region itself is used there.")
            left -= km2
    timer.add("regions used as their own county", time.perf_counter() - t)
    return Result(chosen, levels_used, regions_used, filled, max(0.0, left))


def _areas(geom):
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    polys = [q for p in shapely.get_parts(geom) if p.geom_type in ("Polygon", "MultiPolygon")
             for q in shapely.get_parts(p)]
    return polys[0] if len(polys) == 1 else shapely.MultiPolygon(polys)


# The record ------------------------------------------------------------------

HEADER = """\
# The counties record (discussion point 101, architecture 6.12).
#
# For each country: which admin levels make up its counties layer, in order,
# and which regions are used as their own county where no level covers them.
# The build works a country out once and writes it here, marked "worked out".
# To correct a country, change its levels and set "how" to "corrected: " and
# the reason. A corrected record is used as it is and never overwritten.
"""


def load_record(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("countries", {}) or {}


def levels_for(record: dict, country_id: str) -> tuple[list[int], bool]:
    """The levels to try for a country, and whether they come from the record."""
    entry = record.get(country_id)
    if entry and entry.get("levels"):
        return list(entry["levels"]), True
    return list(DEFAULT_LEVELS), False


def update_record(path: Path, country_id: str, name: str, result: Result, region_names: dict, source: str) -> None:
    write_record(path, {country_id: (name, result.levels_used,
                                     [region_names.get(r, r) for r in result.regions_used])}, source)


def is_corrected(entry: dict | None) -> bool:
    return bool(entry) and str(entry.get("how", "")).startswith("corrected")


def how_of(entry: dict | None) -> str:
    """How a country's levels were chosen, in a word for the build log: corrected, worked out, or the rule."""
    if is_corrected(entry):
        return "corrected"
    return "worked out" if entry and entry.get("levels") else "the rule"


def write_record(path: Path, found: dict[str, tuple[str, list[int], list[str]]], source: str,
                 today: str | None = None) -> dict[str, list[str]]:
    """Write what a build found for each country into the record (P3-T1c): {id: (name, levels, regions used)}.

    A corrected entry is never overwritten. An entry that says the same as what was found keeps its date, so
    the record changes only when OSM does. Returns the country names written, left as corrected, and
    unchanged."""
    record = load_record(path)
    today = today or time.strftime('%d %B %Y').lstrip('0')
    out: dict[str, list[str]] = {"written": [], "corrected": [], "unchanged": []}
    for cid, (name, levels, regions) in sorted(found.items()):
        entry = record.get(cid)
        if is_corrected(entry):
            out["corrected"].append(name)
            continue
        if entry and list(entry.get("levels") or []) == list(levels) and \
                list(entry.get("regions_used") or []) == list(regions):
            out["unchanged"].append(name)
            continue
        record[cid] = {"name": name, "levels": list(levels), "regions_used": list(regions),
                       "how": f"worked out by {source} on {today}"}
        out["written"].append(name)
    if out["written"]:
        text = HEADER + "\n" + yaml.safe_dump({"countries": dict(sorted(record.items()))}, allow_unicode=True,
                                              sort_keys=False, width=120)
        path.write_text(text, encoding="utf-8", newline="\n")
    return out


def record_path(settings: dict | None = None) -> Path:
    """The counties record a stage uses: its setting counties_record, a path from the repository's top
    folder, or mapdata/config/county_levels.yaml."""
    from mapdata.paths import CONFIG_DIR

    given = (settings or {}).get("counties_record")
    if given:
        return Path(given) if Path(given).is_absolute() else CONFIG_DIR.parent.parent / given
    return CONFIG_DIR / "county_levels.yaml"


def record_levels(path: Path) -> dict[str, list[int]]:
    """Each country's levels in the record, as the planet reading uses them: what goes in its fingerprint."""
    return {cid: list(e["levels"]) for cid, e in sorted(load_record(path).items()) if e and e.get("levels")}


def cannot_fill_a_gap(here: list, earlier: list) -> set[int]:
    """Of the areas `here` (shapes as read) at one county level, the positions of those with less than GAP_KM2
    outside the areas `earlier`, of the levels tried before: they can fill no gap, so they are left out
    (P3-T1a). Each is measured only against the earlier areas it touches, cut to its own bounds."""
    if not here or not earlier:
        return set()
    arr = np.array(earlier, dtype=object)
    tree = shapely.STRtree(arr)
    drop = set()
    for n, g in enumerate(here):
        rest = g
        for j in tree.query(g, predicate="intersects").tolist():
            if rest.is_empty:
                break
            w, s, e, nn = rest.bounds
            local = shapely.clip_by_rect(arr[j], w - 1e-6, s - 1e-6, e + 1e-6, nn + 1e-6)
            try:
                rest = shapely.difference(rest, local)
            except shapely.errors.GEOSException:
                rest = shapely.difference(shapely.make_valid(rest), shapely.make_valid(local))
        from mapdata.stages.grid import polygonal

        if rest.is_empty or area_km2(polygonal(rest) or shapely.Polygon()) < GAP_KM2:
            drop.add(n)
    return drop
