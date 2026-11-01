"""Extract administrative areas from a GOL file with GeoDesk (architecture 8.2, stage 1).

GeoDesk (LGPL-3.0) answers queries on the GOL files in the data folder, which
are only read. Shapes come back in GeoDesk's Mercator units and are converted
to longitude and latitude, then repaired if invalid (stage 4), with each repair
recorded.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import shapely


@dataclass
class Area:
    id: str                    # canonical identifier, such as osm:r62149 (AD-13)
    name: str
    level: int                 # OSM admin_level; 3 is used for metropolitan France
    geom: object               # Shapely geometry in longitude and latitude
    parent: str | None = None  # the level 2 country it was found in
    tags: dict = field(default_factory=dict)
    repaired: bool = False


KEEP_TAGS = ("name", "name:en", "admin_level", "ISO3166-1", "ISO3166-2", "wikidata", "place", "border_type")


def _tags(feature) -> dict:
    out = {}
    for key in KEEP_TAGS:
        value = feature.tags[key]
        if value:
            out[key] = str(value)
    return out


def _to_area(feature, level: int, parent: str | None, repairs: list[str]) -> Area:
    import geodesk

    geom = geodesk.from_mercator(feature.shape)
    repaired = False
    if not geom.is_valid:
        reason = shapely.is_valid_reason(geom)
        geom = shapely.make_valid(geom, method="structure")
        repaired = True
        repairs.append(f"osm:r{feature.id} {feature.tags['name']}: repaired, {reason}")
    return Area(id=f"osm:r{feature.id}", name=str(feature.tags["name"]), level=level, geom=geom,
                parent=parent, tags=_tags(feature), repaired=repaired)


def relation(world, cid: str, expected_name: str, level: int, repairs: list[str], parent: str | None = None) -> Area:
    """One relation by id. Stops if its name is not the one expected."""
    feature = world.relation(int(cid.removeprefix("osm:r")))
    if feature is None:
        raise SystemExit(f"{cid} ({expected_name}) is not in the GOL file.")
    name = str(feature.tags["name"])
    if name != expected_name:
        raise SystemExit(f"{cid} is named {name!r}, but the configuration expects {expected_name!r}. Check the id.")
    return _to_area(feature, level, parent, repairs)


def divisions(world, country: Area, level: int, repairs: list[str],
              boxes: list[list[float]] | None = None) -> list[Area]:
    """Areas at one admin level whose inside point lies in the country.

    Testing a point inside each area, rather than containment of the whole
    area, avoids losing divisions whose boundary goes slightly outside the
    country's, and avoids picking up neighbours that only touch it.

    boxes limits the search to the build's regions. France's level 2 area
    reaches round the world, so its own box would mean searching everywhere.
    """
    import geodesk

    cw, cs, ce, cn = country.geom.bounds
    search = []
    for w, s, e, n in boxes or [[cw, cs, ce, cn]]:
        w, s, e, n = max(w, cw), max(s, cs), min(e, ce), min(n, cn)
        if w < e and s < n:
            search.append(geodesk.Box(west=w, south=s, east=e, north=n))
    prepared = country.geom
    shapely.prepare(prepared)
    found, seen = [], set()
    for box in search:
        for feature in world(f"a[boundary=administrative][admin_level={level}]")(box):
            if feature.id in seen or not feature.is_relation or feature.id == int(country.id.removeprefix("osm:r")):
                continue
            seen.add(feature.id)
            local_repairs: list[str] = []
            area = _to_area(feature, level, country.id, local_repairs)
            if area.geom.is_empty:
                continue
            if shapely.contains(prepared, shapely.point_on_surface(area.geom)):
                found.append(area)
                repairs.extend(local_repairs)  # only areas that are kept count as repairs
    found.sort(key=lambda a: (a.name, a.id))
    return found
