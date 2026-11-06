"""Make tests/samples/osm/southampton-itchen.geojson from the planet file (P2-T10c; ANN-2).

The River Itchen through Southampton (a line), Longbridge Lake near it (an area) and
Southampton Central station (a point), read with GeoDesk, simplified to 0.0001 degrees
(about 10 metres). They are for the automatic tests of Crossed and passed only: the world
pack gets rivers and railways in Phase 3.

    .venv\\Scripts\\python.exe tools\\make_itchen_samples.py

The planet file is the newest in the data folder, found as `mapdata check` finds it. The
read takes under a second. Runs in its own short-lived process, as the GeoDesk notes ask.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "tests" / "samples" / "osm" / "southampton-itchen.geojson"
BOX = (-1.50, 50.88, -1.28, 51.02)   # west, south, east, north: Winchester's edge to Southampton Water
RIVER, LAKE, STATION = 7703089, 10303325, 638908005
TOLERANCE = 0.0001
LICENCE = ("Contains information from OpenStreetMap, which is made available under the Open Database "
           "License (ODbL): https://opendatacommons.org/licenses/odbl/1.0/. © OpenStreetMap contributors.")


def planet() -> Path:
    """The newest planet file in the data folder's downloads."""
    from mapdata.paths import resolve_data_folder

    found = sorted(resolve_data_folder().downloads.glob("planet-*/planet-*.gol"))
    if not found:
        raise SystemExit("No planet file in the data folder's downloads. Run: python -m mapdata fetch planet")
    return found[-1]


def main() -> int:
    import geodesk
    import shapely

    gol = planet()
    world = geodesk.Features(str(gol))
    box = geodesk.Box(west=BOX[0], south=BOX[1], east=BOX[2], north=BOX[3])
    clip = shapely.box(*BOX)

    def shape(f):
        return geodesk.from_mercator(f.shape)

    features = []
    river = next(iter(world(f"r[waterway=river][name=\"River Itchen\"]")(box)))
    assert river.id == RIVER, river.id
    lines = []
    for m in river.members:
        if m.is_way and str(m.tags["waterway"]) in ("river", "stream"):
            part = shapely.intersection(shapely.LineString(shape(m).coords), clip)
            lines.extend(shapely.get_parts(part))
    lines = [g for g in lines if g.geom_type == "LineString" and not g.is_empty]
    merged = shapely.line_merge(shapely.MultiLineString(lines))
    merged = shapely.simplify(merged, TOLERANCE)
    features.append({"type": "Feature", "properties": {"id": f"osm:r{RIVER}", "name": "River Itchen",
                                                         "layer": "rivers", "type": "river"},
                     "geometry": json.loads(shapely.to_geojson(merged))})

    lake = next(iter(world("a[natural=water][name=\"Longbridge Lake\"]")(box)))
    assert lake.id == LAKE, lake.id
    area = shapely.simplify(shape(lake), TOLERANCE)
    features.append({"type": "Feature", "properties": {"id": f"osm:r{LAKE}", "name": "Longbridge Lake",
                                                         "layer": "lakes", "type": "lake"},
                     "geometry": json.loads(shapely.to_geojson(area))})

    station = next(iter(world("n[railway=station][name=\"Southampton Central\"]")(box)))
    assert station.id == STATION, station.id
    features.append({"type": "Feature", "properties": {"id": f"osm:n{STATION}", "name": "Southampton Central",
                                                         "layer": "stations", "type": "station"},
                     "geometry": {"type": "Point", "coordinates": [round(station.lon, 7), round(station.lat, 7)]}})

    data = {"type": "FeatureCollection",
            "about": f"The River Itchen, Longbridge Lake and Southampton Central station from the planet file "
                     f"{gol.name}, read with GeoDesk, simplified to {TOLERANCE} degrees. For the tests of Crossed "
                     "and passed (ANN-2).",
            "licence": LICENCE, "features": features}
    OUT.write_text("\n".join(["{" + ", ".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}"
                                              for k, v in data.items() if k != "features") + ", \"features\": [",
                              ",\n".join(json.dumps(f, ensure_ascii=False, separators=(",", ":")) for f in features),
                              "]}"]) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: the river as {shapely.get_num_geometries(merged)} line(s), "
          f"the lake, the station. {OUT.stat().st_size // 1024} KB.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
