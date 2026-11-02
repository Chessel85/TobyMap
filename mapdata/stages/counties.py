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

import shapely
import yaml

from mapdata.stages.geodesy import area_km2

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


def build(country_raw, regions: list, candidates: dict[int, list], clip, levels: list[int],
          english=lambda a: a.name, region_fill: bool = True) -> Result:
    """Choose the counties of one country.

    country_raw: the country's shape as read (in the area checked).
    regions: [(Area, land)] at the region level, used where nothing else covers.
    candidates: {level: [Area]} with their shapes as read, not yet cut to the land.
    clip: a function giving the land of a shape.

    Gaps are found from the shapes as read, which have few points at sea, and
    only the gap is cut to the land. Joining hundreds of shapes already cut to
    a detailed coast, such as Norway's municipalities, took over half an hour.
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
            gap_raw, gap = gap_now()
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
            land = clip(a.geom)
            if land.is_empty:
                continue
            if gap is not None:
                inside = area_km2(shapely.intersection(land, gap))
                total = area_km2(land)
                if total <= 0 or inside < SHARE_IN_GAP * total:
                    continue
                filled.append(f"Level {level} fills a gap: {english(a)}, {inside:,.0f} km2.")
            chosen.append(County(a, land, level))
            took += 1
        if took:
            levels_used.append(level)
    regions_used: list[str] = []
    _raw, gap = gap_now()
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
    record = load_record(path)
    entry = record.get(country_id)
    if entry and str(entry.get("how", "")).startswith("corrected"):
        return
    record[country_id] = {
        "name": name,
        "levels": result.levels_used,
        "regions_used": [region_names.get(r, r) for r in result.regions_used],
        "how": f"worked out by {source} on {time.strftime('%d %B %Y').lstrip('0')}",
    }
    text = HEADER + "\n" + yaml.safe_dump({"countries": dict(sorted(record.items()))}, allow_unicode=True,
                                          sort_keys=False, width=120)
    path.write_text(text, encoding="utf-8", newline="\n")
