"""World sample: Natural Earth countries as a small file for the globe (spike S5, P0-T8).

This is a stand-in for the base pack until Phase 1. It reads a Natural Earth
"admin 0 countries" GeoJSON file and writes compact JSON: one entry per
country with its name, sovereign state, continent, population estimate,
Natural Earth's own colour number (so neighbours differ, AD-19) and its
polygons as flat lists of longitude and latitude.

Natural Earth is public domain, so the 1:110 million file is small enough to
keep in git, at mapcore/data/world_110m.json.
"""
from __future__ import annotations

import json
from typing import Any

FORMAT = "tobymap-world-sample-1"
DECIMALS = 3  # about 100 metres, finer than any Natural Earth scale


def _round(value: float) -> float:
    rounded = round(float(value), DECIMALS)
    return int(rounded) if rounded == int(rounded) else rounded


def _ring(coords: list[list[float]]) -> list[float]:
    points = coords[:-1] if len(coords) > 1 and coords[0] == coords[-1] else coords
    flat: list[float] = []
    for lon, lat, *_ in points:
        flat.append(_round(lon))
        flat.append(_round(lat))
    return flat


def _polygons(geometry: dict[str, Any]) -> list[list[list[float]]]:
    kind = geometry["type"]
    if kind == "Polygon":
        polys = [geometry["coordinates"]]
    elif kind == "MultiPolygon":
        polys = geometry["coordinates"]
    else:
        return []
    return [[_ring(ring) for ring in poly] for poly in polys]


def convert(source: dict[str, Any], source_name: str) -> dict[str, Any]:
    countries = []
    for feature in source["features"]:
        p = feature["properties"]
        polygons = _polygons(feature["geometry"])
        if not polygons:
            continue
        countries.append({
            "id": f"ne:{p.get('ADM0_A3') or p['NAME']}",
            "name": p["NAME"],
            "long_name": p.get("NAME_LONG") or p["NAME"],
            "sovereign": p.get("SOVEREIGNT") or p["NAME"],
            "continent": p.get("CONTINENT") or "",
            "subregion": p.get("SUBREGION") or "",
            "population": int(p.get("POP_EST") or 0),
            "colour": int(p.get("MAPCOLOR7") or 1),
            "centre": [_round(p.get("LABEL_X", 0)), _round(p.get("LABEL_Y", 0))],
            "polygons": polygons,
        })
    countries.sort(key=lambda c: (c["name"], c["id"]))
    return {
        "format": FORMAT,
        "source": source_name,
        "licence": "Public domain (Natural Earth)",
        "countries": countries,
    }


def dumps(sample: dict[str, Any]) -> str:
    """Compact, repeatable JSON: the same input always gives the same bytes."""
    return json.dumps(sample, ensure_ascii=False, separators=(",", ":"), sort_keys=False) + "\n"
