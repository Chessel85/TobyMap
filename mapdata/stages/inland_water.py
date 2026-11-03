"""Inland water in the area check (P1-T16, architecture 8.2 stage 17, spike S2).

The OSM land polygons treat only the sea as water, so lakes, lagoons, ponds,
reservoirs and wide rivers inside the coast count as land. Published land
areas leave most of them out: spike S2 found Kiribati 35% larger than
Wikidata's figure, mostly lagoons and salt ponds.

So before a country's land is compared with Wikidata's area, the inland
water mapped in OSM is taken away, and reported on its own line. Wetlands
are measured and reported too, but not taken away: they are partly land,
and published areas differ on them.

Reading the water is done in the planet file's own short-lived process,
like the rest of the extract, because GeoDesk gives its memory back only
when the process ends (spike S2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely

from mapdata.stages.clip import polygonal
from mapdata.stages.geodesy import area_km2

# What counts as inland water, as GeoDesk queries. natural=water covers
# lakes, lagoons, ponds, reservoirs and rivers mapped as areas; the other
# two are older ways of tagging rivers and reservoirs.
WATER_QUERY = "a[natural=water], a[waterway=riverbank], a[landuse=reservoir]"
WETLAND_QUERY = "a[natural=wetland]"
ALLOWED_PERCENT = 1.0


def read(world, country_geom, boxes: list[list[float]]) -> dict:
    """The inland water and wetlands inside one country's outline, as read: {"water": [...], "wetland": [...]}.

    Runs in the extract process. Only shapes inside the outline's parts are
    kept, tested with a point on each one's surface, as for divisions.
    """
    import geodesk

    prepared = country_geom
    shapely.prepare(prepared)
    out: dict[str, list] = {"water": [], "wetland": []}
    for kind, query in (("water", WATER_QUERY), ("wetland", WETLAND_QUERY)):
        seen = set()
        for w, s, e, n in boxes:
            box = geodesk.Box(west=w, south=s, east=e, north=n)
            for f in world(query)(box):
                key = (f.is_relation, f.id)
                if key in seen:
                    continue
                seen.add(key)
                g = geodesk.from_mercator(f.shape)
                if not g.is_valid:
                    g = shapely.make_valid(g, method="structure")
                g = polygonal(g)
                if g is None or g.is_empty:
                    continue
                if shapely.intersects(prepared, shapely.point_on_surface(g)):
                    out[kind].append(g)
    return out


def on_land(land, shapes: list, cell: float = 1.0) -> float:
    """How much of the land the shapes cover, in km2, with overlapping shapes counted once.

    Worked out one grid square at a time, so each step joins only the water
    and land near it, never a whole country's at once.
    """
    if land is None or land.is_empty or not shapes:
        return 0.0
    arr = np.array(shapes, dtype=object)
    tree = shapely.STRtree(arr)
    parts = shapely.get_parts(land)
    land_tree = shapely.STRtree(parts)
    w, s, e, n = shapely.total_bounds(arr)
    total = 0.0
    for i in range(math.floor(w / cell), math.ceil(e / cell)):
        for j in range(math.floor(s / cell), math.ceil(n / cell)):
            box = (i * cell, j * cell, (i + 1) * cell, (j + 1) * cell)
            near = tree.query(shapely.box(*box))
            if len(near) == 0:
                continue
            land_near = land_tree.query(shapely.box(*box))
            if len(land_near) == 0:
                continue
            water = shapely.union_all(shapely.clip_by_rect(arr[near], *box))
            ground = shapely.union_all(shapely.clip_by_rect(parts[land_near], *box))
            both = polygonal(shapely.intersection(water, ground))
            if both is not None and not both.is_empty:
                total += area_km2(both)
    return total


@dataclass
class AreaCheck:
    name: str
    land_km2: float          # the land as cut to the land polygons
    water_km2: float         # inland water mapped in OSM on that land
    wetland_km2: float       # wetlands, reported only
    wikidata_km2: float
    explained: str | None    # the reason in the settings, if the difference is known

    @property
    def without_water_km2(self) -> float:
        return self.land_km2 - self.water_km2

    @property
    def diff_percent(self) -> float:
        return (self.without_water_km2 - self.wikidata_km2) / self.wikidata_km2 * 100

    @property
    def before_percent(self) -> float:
        return (self.land_km2 - self.wikidata_km2) / self.wikidata_km2 * 100

    @property
    def within(self) -> bool:
        return abs(self.diff_percent) <= ALLOWED_PERCENT

    @property
    def passed(self) -> bool:
        return self.within or bool(self.explained)

    def lines(self) -> list[str]:
        out = [f"{self.name}: {self.land_km2:,.0f} km2 of land in the land polygons. Inland water mapped in OSM on "
               f"it: {self.water_km2:,.1f} km2. Without that water: {self.without_water_km2:,.0f} km2.",
               f"  Wikidata gives {self.wikidata_km2:,.0f} km2: a difference of {self.diff_percent:+.1f}% without the "
               f"water, and {self.before_percent:+.1f}% with it. Within {ALLOWED_PERCENT:.0f}%: "
               f"{'yes' if self.within else 'no'}."]
        if self.wetland_km2:
            out.append(f"  Wetlands mapped in OSM, not taken away: {self.wetland_km2:,.1f} km2.")
        if not self.within:
            out.append(f"  The difference is explained in the settings: {self.explained}" if self.explained
                       else "  The difference is not explained in the settings, so this check fails.")
        return out

    def row(self) -> dict:
        return {"name": self.name, "land_km2": self.land_km2, "water_km2": self.water_km2,
                "wetland_km2": self.wetland_km2, "without_water_km2": self.without_water_km2,
                "wikidata_km2": self.wikidata_km2, "diff_percent": self.diff_percent,
                "diff_percent_with_water": self.before_percent, "within": self.within,
                "explained": self.explained, "passed": self.passed}
