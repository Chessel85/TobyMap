"""Unclaimed land, tidied (P3-T26b, DP205), called by the enclaves stage, which has the towns.

The join stage makes an area of unclaimed land for each bit of land in no country. Most are slivers left between
countries' borders in OpenStreetMap, not real unclaimed land. So:

* An area of unclaimed land under min_km2 (1) is left out of the pack, unless it is in one of Natural Earth's
  disputed areas, such as Doumera Island. The build report counts what was left out. On the world's data of
  November 2026 these were 26: a few slivers, and many islets in no country in OpenStreetMap, such as some of the
  Spratly Islands, the Senkaku Islands and islets in the Caspian Sea.
* One the join stage could only call "Unclaimed" is named by the nearest named place or island, not an unnamed
  one, and its own point:
  "Unclaimed land near X, 12.3 N, 45.6 E". Named ones, such as Bir Tawil, keep their names.

Settings: min_km2 (1.0); the stage's own settings are under "unclaimed" in the enclaves stage.
"""
from __future__ import annotations

import shapely

TYPE = "unclaimed land"
PLAIN_NAME = "Unclaimed"
NEAR_LAYERS = ("towns", "islands")
SETTINGS = {"min_km2": 1.0}


def _km2(g) -> float:
    from mapdata.stages import continents

    return float(continents.km2(g))


def _coords(lat: float, lon: float) -> str:
    return f"{abs(lat):.1f} {'N' if lat >= 0 else 'S'}, {abs(lon):.1f} {'E' if lon >= 0 else 'W'}"


def tidy(records: list[dict], geoms: list, settings: dict | None = None, log=print) -> tuple[list[dict], list, int]:
    """The records and shapes with small unclaimed land left out and the rest named. Returns (records, shapes,
    how many were left out)."""
    s = {**SETTINGS, **(settings or {})}
    near = [(r, g) for r, g in zip(records, geoms)
            if r.get("layer") in NEAR_LAYERS and g is not None and not g.is_empty
            and _name(r) and not _name(r).startswith("Unnamed") and r.get("type") != TYPE]
    tree = shapely.STRtree([g for _r, g in near]) if near else None
    keep_r, keep_g, left_out = [], [], 0
    for r, g in zip(records, geoms):
        if r.get("type") != TYPE or g is None:
            keep_r.append(r)
            keep_g.append(g)
            continue
        size = _km2(g)
        if size < s["min_km2"] and not r.get("dispute"):
            left_out += 1
            log(f"Left out: unclaimed land of {size:,.3f} km2 at {_coords(*_point(g))}.")
            continue
        if _name(r) == PLAIN_NAME and tree is not None:
            lat, lon = _point(g)
            k = int(tree.query_nearest(shapely.Point(lon, lat))[0])
            place = _name(near[k][0])
            name = f"Unclaimed land near {place}, {_coords(lat, lon)}"
            r = {**r, "name": name}
            log(f"Named: {name}, {size:,.2f} km2.")
        keep_r.append(r)
        keep_g.append(g)
    return keep_r, keep_g, left_out


def _name(r: dict) -> str:
    """A record's name; of OpenStreetMap's names given together, such as "Diaoyu Island;Uotsurijima Island", the
    first."""
    return (r.get("name") or "").split(";")[0].strip()


def _point(g) -> tuple[float, float]:
    p = shapely.point_on_surface(g)
    return float(p.y), float(p.x)
