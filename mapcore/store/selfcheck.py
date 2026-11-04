"""A self-check of the store, run where the core runs (P1-T5).

It writes a small pack in memory and asks the store the questions the
application asks: what is at a point, in the right order; either side of the
180 degree line; and the nearest point of an area, with its distance and
bearing. It needs Shapely, so the browser tests run it in Pyodide, in Chromium
and Firefox (tests/web/test_store_page.py). Diagnostics can run it too
(P1-T15).

run() returns a list of problems, empty when all is well.
"""
from __future__ import annotations

import io

import numpy as np

from mapcore.geo import geodesy
from mapcore.packs import coords, pack, tiles
from mapcore.packs.source import MemorySource
from mapcore.store import Store

LAYERS = [{"id": "countries", "name": "Countries"}, {"id": "regions", "name": "Regions"}]
MANIFEST = {"name": "store-selfcheck", "version": "1", "coverage": {"kind": "world"},
            "app_versions": {"from": "0.0.1"},
            "sources": [{"name": "Test", "licence": "ODbL 1.0", "date": "2026-11-04"}],
            "drawing_levels": []}


def _box(west, south, east, north):
    return np.array([[west, south], [east, south], [east, north], [west, north], [west, south]])


def _feature(identifier, layer, name, rank, box, area):
    west, south, east, north = box
    return {"id": identifier, "source": "test", "layer": layer, "type": layer, "names": {"en": name},
            "rank": rank, "area_km2": area, "bbox": list(box), "width_km": 100.0, "colour": 0,
            "point": [(west + east) / 2, (south + north) / 2], "parents": []}


def build() -> bytes:
    country = (1.0, 50.0, 3.0, 52.0)
    region = (1.5, 50.5, 2.5, 51.5)
    island_east = (179.5, -17.0, 180.0, -16.0)
    island_west = (-180.0, -17.0, -179.5, -16.0)
    features = [
        _feature("t:country", "countries", "Country", 2, country, 40000.0),
        _feature("t:region", "regions", "Region", 4, region, 10000.0),
        # Stored split at the 180 degree line, so its box is the one across the line (AD-17).
        _feature("t:island", "countries", "Island", 2, (179.5, -17.0, -179.5, -16.0), 6000.0),
    ]
    out = io.BytesIO()
    writer = pack.PackWriter(out)
    n = writer.add_features(features)
    for level in (3,):
        writer.add_tile(level, *tiles.tile_of(2.0, 51.0, level),
                        [(n["t:country"], tiles.COMPACT, coords.encode([[_box(*country)]])),
                         (n["t:region"], tiles.COMPACT, coords.encode([[_box(*region)]]))])
        writer.add_tile(level, *tiles.tile_of(179.8, -16.5, level),
                        [(n["t:island"], tiles.COMPACT, coords.encode([[_box(*island_east)]]))])
        writer.add_tile(level, *tiles.tile_of(-179.8, -16.5, level),
                        [(n["t:island"], tiles.COMPACT, coords.encode([[_box(*island_west)]]))])
    writer.finish(MANIFEST, "© OpenStreetMap contributors. Test.", LAYERS)
    return out.getvalue()


def run() -> list[str]:
    problems = []

    def expect(ok, text):
        if not ok:
            problems.append(text)

    store = Store([pack.Pack(MemorySource(build(), "store-selfcheck.pack"))])

    def ids(lat, lon):
        return [a.id for a in store.at(lat, lon)]

    expect(ids(51.0, 2.0) == ["t:region", "t:country"], "the region is not listed before its country")
    expect(ids(50.2, 1.2) == ["t:country"], "a point in the country only is wrong")
    expect(ids(40.0, 2.0) == [], "a point in no area is not empty")
    expect(ids(-16.5, 179.8) == ["t:island"], "the island east of the 180 degree line is not found")
    expect(ids(-16.5, -179.8) == ["t:island"], "the island west of the 180 degree line is not found")
    expect(ids(-16.5, 180.0) == ["t:island"], "the 180 degree line itself is not in the island")
    expect(store.feature("t:region").name == "Region", "a feature record is not found by its identifier")
    expect(store.feature("t:none") is None, "a feature that is not there is found")

    near = {n.area.id: n for n in store.nearby(50.5, 0.5, 200_000)}
    expect(set(near) == {"t:country", "t:region"}, "Nearby did not find the country and the region")
    if "t:country" in near:
        want = geodesy.distance_m(50.5, 0.5, 50.5, 1.0)
        expect(abs(near["t:country"].distance_m - want) < 1.0, "the distance to the country's nearest point is wrong")
        expect(80.0 < near["t:country"].bearing_deg < 100.0, "the bearing to the country is not east")
        expect(not near["t:country"].inside, "outside a country is reported inside")
    inside = {n.area.id: n for n in store.nearby(51.0, 2.0, 1000)}
    expect(inside.keys() == {"t:country", "t:region"} and all(n.inside and n.distance_m == 0 for n in inside.values()),
           "an area the point is inside is not at distance 0")
    across = store.nearby(-16.5, 179.0, 200_000)
    expect([n.area.id for n in across] == ["t:island"] and across[0].distance_m < 60_000,
           "Nearby did not reach the island from the west of the line")

    bad = bytearray(build())
    probe = pack.Pack(MemorySource(bytes(bad), "probe.pack"))
    offset = probe.directory[tiles.tile_key(3, *tiles.tile_of(2.0, 51.0, 3))][0]
    bad[offset + 3] ^= 0xFF
    broken = Store([pack.Pack(MemorySource(bytes(bad), "damaged.pack"))])
    expect(broken.at(51.0, 2.0) == [] and len(broken.problems) == 1, "a damaged pack tile was not reported once")
    expect([a.id for a in broken.at(-16.5, 179.8)] == ["t:island"], "the store did not carry on past a damaged pack tile")
    return problems
