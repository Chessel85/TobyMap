"""Stage "graticule": lines of latitude and longitude, and the special lines (P2-T10b; DAT-13, SCP-7, AD-11).

The graticule is data, not code (AD-11). Every whole degree of latitude and longitude is
written as a line of the layer "graticule", marked with the intervals it belongs to: the line
for 30 degrees east is in the 1, 5, 10, 15 and 30 degree sets, so the interval a user chooses
is only a filter. Every line has its points at most 1 degree apart, because the map draws
straight between points. The equator (0 degrees latitude), the prime meridian and the 180
degree meridian are special lines, and are not also graticule lines.

The special lines are in the layer "special-lines", each its own named line: the equator,
the prime meridian, the 180 degree meridian, the two tropics, the two polar circles and the
international date line. The tropics and polar circles move slowly, so their latitude is
worked out for the year in the stage's setting "year". The date line is not straight; it is
read from Natural Earth's geographic lines, the source named in the setting "source", and
stored as its two sides where it crosses the 180 degree line.

Settings: year (needed), source (the geographic lines; without it the date line is left out),
layer and special_layer (the layers' ids, graticule and special-lines).

Records carry "exact": true, so the drawing levels keep every point of them: a parallel
simplified to its two ends would be drawn as a great circle, not along the parallel.
"""
from __future__ import annotations

import json
import math

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped

INTERVALS = (1, 5, 10, 15, 30)
STEP = 1.0   # the most between two points of a line, in degrees


def obliquity_degrees(year: float) -> float:
    """The tilt of the Earth's axis in the given year (the IAU 2006 polynomial). It is the
    latitude of the tropics, and 90 degrees less the latitude of the polar circles."""
    t = (year - 2000.0) / 100.0
    return 23.4392794 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t ** 3


def _steps(a: float, b: float) -> np.ndarray:
    n = max(1, int(np.ceil(abs(b - a) / STEP - 1e-9)))
    return np.linspace(a, b, n + 1)


def meridian(lon: float, south: float = -90.0, north: float = 90.0):
    lats = _steps(south, north)
    return shapely.LineString(np.column_stack([np.full(len(lats), float(lon)), lats]))


def parallel(lat: float):
    lons = _steps(-180.0, 180.0)
    return shapely.LineString(np.column_stack([lons, np.full(len(lons), float(lat))]))


def intervals_of(value: int) -> list[int]:
    return [i for i in INTERVALS if value % i == 0]


def degrees_words(value: float, positive: str, negative: str) -> str:
    return f"{abs(value):g} degrees {positive if value > 0 else negative}"


def graticule_lines(layer: str) -> tuple[list[dict], list]:
    records, geoms = [], []
    for lon in range(-179, 180):
        if lon == 0:
            continue
        records.append({"id": f"graticule:lon{abs(lon)}{'e' if lon > 0 else 'w'}", "layer": layer,
                        "type": "meridian", "name": degrees_words(lon, "east", "west"),
                        "intervals": intervals_of(abs(lon)), "exact": True})
        geoms.append(meridian(lon))
    for lat in range(-89, 90):
        if lat == 0:
            continue
        records.append({"id": f"graticule:lat{abs(lat)}{'n' if lat > 0 else 's'}", "layer": layer,
                        "type": "parallel", "name": degrees_words(lat, "north", "south"),
                        "intervals": intervals_of(abs(lat)), "exact": True})
        geoms.append(parallel(lat))
    return records, geoms


def split_at_180(coords: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """A line's parts either side of the 180 degree line. A step of more than 180 degrees
    of longitude is a step across it, the short way round; the line is cut there, with a
    point on 180 or -180 at the latitude where it crosses."""
    parts, current = [], []
    for lon, lat in coords:
        if abs(lon) > 180.0:
            lon = (lon + 180.0) % 360.0 - 180.0
        if current:
            plon, plat = current[-1]
            if abs(lon - plon) > 180.0:
                edge = 180.0 if plon > 0 else -180.0
                span = (lon + 2 * edge) - plon
                f = (edge - plon) / span if span else 0.0
                clat = plat + f * (lat - plat)
                current.append((edge, clat))
                parts.append(current)
                current = [(-edge, clat)]
        current.append((lon, lat))
    if len(current) > 1:
        parts.append(current)
    return [p for p in parts if len(p) > 1]


def densify(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = [coords[0]]
    for (lon0, lat0), (lon1, lat1) in zip(coords, coords[1:]):
        n = max(1, int(np.ceil(max(abs(lon1 - lon0), abs(lat1 - lat0)) / STEP - 1e-9)))
        for k in range(1, n + 1):
            out.append((lon0 + (lon1 - lon0) * k / n, lat0 + (lat1 - lat0) * k / n))
    return out


ON_180 = 0.001     # degrees: an end this close to the 180 degree line is on it
JOIN = 0.02        # degrees, about 2 km: ends of two parts this close are joined


def close_gaps(parts: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Natural Earth's date line is in parts that stop a little short of the 180 degree
    line and of each other: 150 metres at 51 degrees south, 1 km along the 180 degree
    line at 2.5 degrees south (P2-T10d). A step through such a gap would cross without
    meeting the line, so ends near the 180 degree line are put on it, and two ends close
    together are joined by a short segment."""
    parts = [list(p) for p in parts]
    for p in parts:
        for k in (0, -1):
            lon, lat = p[k]
            if abs(abs(lon) - 180.0) < ON_180:
                p[k] = (math.copysign(180.0, lon), lat)
    ends = [(i, k) for i in range(len(parts)) for k in (0, -1)]
    for a, (i, k) in enumerate(ends):
        for j, m in ends[a + 1:]:
            if i == j:
                continue
            (lon1, lat1), (lon2, lat2) = parts[i][k], parts[j][m]
            if abs(lon1) == 180.0 and abs(lon2) == 180.0:
                gap = abs(lat1 - lat2)            # the same meridian, seen from either side
                meet = (lon1, lat2)
            else:
                gap = math.hypot(lon1 - lon2, lat1 - lat2)
                meet = (lon2, lat2)
            if 0.0 < gap < JOIN:
                if k == 0:
                    parts[i].insert(0, meet)
                else:
                    parts[i].append(meet)
    return parts


def date_line(path, say=lambda _line: None):
    """The international date line from Natural Earth's geographic lines (a GeoJSON file), with
    points at most 1 degree apart, in two sides where it crosses the 180 degree line."""
    data = json.loads(path.read_text(encoding="utf-8"))
    parts = []
    for f in data.get("features") or []:
        props = f.get("properties") or {}
        text = " ".join(str(props.get(k) or "") for k in ("featurecla", "name", "NAME", "name_en")).lower()
        if "date line" not in text:
            continue
        geom = f["geometry"]
        lines = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
        for line in lines:
            for part in split_at_180([(c[0], c[1]) for c in line]):
                parts.append(densify(part))
    if not parts:
        raise BuildStopped(f"The file {path.name} has no line called the date line. "
                           "Check the source named in the graticule stage.")
    parts = close_gaps(parts)
    say(f"The international date line: {len(parts)} part(s) from {path.name}.")
    return shapely.MultiLineString(parts) if len(parts) > 1 else shapely.LineString(parts[0])


def special_lines(layer: str, year: int, date_line_geom=None) -> tuple[list[dict], list]:
    tilt = round(obliquity_degrees(year), 4)
    polar = round(90.0 - tilt, 4)
    items = [
        ("special:equator", "equator", "Equator", parallel(0.0)),
        ("special:prime-meridian", "prime-meridian", "Prime meridian", meridian(0.0)),
        ("special:antimeridian", "antimeridian", "180 degree meridian", meridian(180.0)),
        ("special:tropic-of-cancer", "tropic", "Tropic of Cancer", parallel(tilt)),
        ("special:tropic-of-capricorn", "tropic", "Tropic of Capricorn", parallel(-tilt)),
        ("special:arctic-circle", "polar-circle", "Arctic Circle", parallel(polar)),
        ("special:antarctic-circle", "polar-circle", "Antarctic Circle", parallel(-polar)),
    ]
    if date_line_geom is not None:
        items.append(("special:date-line", "date-line", "International date line", date_line_geom))
    records = [{"id": i, "layer": layer, "type": t, "name": n, "exact": True} for i, t, n, _g in items]
    return records, [g for *_x, g in items]


def run(ctx) -> None:
    year = ctx.settings.get("year")
    if not isinstance(year, int) or isinstance(year, bool):
        raise BuildStopped("The graticule stage needs year, such as 2026: the tropics and polar circles are "
                           "worked out for it. Add it to the stage in the pack's settings file.")
    layer = ctx.settings.get("layer", "graticule")
    special = ctx.settings.get("special_layer", "special-lines")
    for need in (layer, special):
        if need not in ctx.pack.layers:
            raise BuildStopped(f"The graticule stage writes to the layer {need}, which the pack's layer groups do "
                               "not define. Add the graticule layer group to the pack.")
    records, geoms = features.load(ctx.previous) if ctx.previous else ([], [])
    line = None
    if ctx.settings.get("source"):
        line = date_line(ctx.source(ctx.settings["source"])[1], ctx.progress.log)
    else:
        ctx.progress.log("No source for the international date line, so it is left out.")
    new_r, new_g = graticule_lines(layer)
    sp_r, sp_g = special_lines(special, year, line)
    features.save(ctx.folder, records + new_r + sp_r, geoms + new_g + sp_g, ctx.claim)
    ctx.progress.line(f"Wrote {len(new_r)} graticule lines and {len(sp_r)} special lines, with the tropics and "
                      f"polar circles for {year}.")
