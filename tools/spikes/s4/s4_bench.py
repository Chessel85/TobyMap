"""Spike S4: the timings, run the same way on the desktop and in Pyodide (P0-T7).

Only the core's pack reader, NumPy and Shapely are used, so this file runs
unchanged in CPython and in the browser's worker. The page copies it into
Pyodide next to the core.

What is timed (architecture 12.5, NFR-1):

* "Where am I" at each check place: one lookup in the pack, with nothing
  cached, as the core does today.
* Walks of steps: each step moves a set distance and looks up the new
  point. Done twice: with nothing cached, and with a pack tile cache that keeps
  each pack tile's decoded shapes, as Phase 1's store will (P1-T5).
* Where the time goes: reading and unzipping pack tiles, decoding shapes,
  and testing the point against them.
"""
from __future__ import annotations

import math
import time

import numpy as np
import shapely

from mapcore.packs import archive

KM_PER_DEGREE = 111.32


def walk_points(start_lat: float, start_lon: float, bearing_deg: float, step_km: float, steps: int) -> list:
    """The points of a straight walk, step by step, the start included."""
    out = [(start_lat, start_lon)]
    lat, lon = start_lat, start_lon
    b = math.radians(bearing_deg)
    for _ in range(steps):
        lat += step_km * math.cos(b) / KM_PER_DEGREE
        lon += step_km * math.sin(b) / (KM_PER_DEGREE * math.cos(math.radians(lat)))
        out.append((lat, lon))
    return out


class Lookup:
    """Pack.at, with each part timed, and an optional pack tile cache.

    It gives the same answers as Pack.at (checked by a test), but records how
    long reading, decoding and testing took.
    """

    def __init__(self, pack: archive.Pack, cache: bool):
        self.pack = pack
        self.cache = {} if cache else None
        self.read_ms = self.decode_ms = self.test_ms = 0.0
        self.tiles_read = 0

    def _entries(self, key: str):
        if self.cache is not None and key in self.cache:
            return self.cache[key]
        t0 = time.perf_counter()
        data = self.pack.get(key)
        t1 = time.perf_counter()
        self.read_ms += (t1 - t0) * 1000
        if data is None:
            entries = None
        else:
            self.tiles_read += 1
            entries = []
            for index, kind, blob in archive.decode_tile(data):
                if kind == archive.COVERED:
                    entries.append((index, None))
                else:
                    geom = shapely.from_wkb(blob) if kind == archive.WKB else archive.decode_compact(blob)
                    entries.append((index, geom))
            self.decode_ms += (time.perf_counter() - t1) * 1000
        if self.cache is not None:
            self.cache[key] = entries
        return entries

    def at(self, lon: float, lat: float) -> list[dict]:
        point = shapely.Point(lon, lat)
        found = []
        for level in self.pack.levels:
            entries = self._entries(archive.tile_key(level, *archive.tile_of(lon, lat, level)))
            if not entries:
                continue
            t0 = time.perf_counter()
            for index, geom in entries:
                if geom is None or shapely.intersects(geom, point):
                    found.append(self.pack.features[index])
            self.test_ms += (time.perf_counter() - t0) * 1000
        found.sort(key=lambda f: (f["area_km2"], f["id"]))
        return found


def summary(times: list[float]) -> dict:
    a = np.asarray(times, dtype=float)
    return {"count": int(a.size), "median_ms": round(float(np.median(a)), 2),
            "p90_ms": round(float(np.percentile(a, 90)), 2), "max_ms": round(float(a.max()), 2),
            "mean_ms": round(float(a.mean()), 2)}


def place_ok(place: dict, found: list[dict]) -> bool:
    if place.get("sea"):
        return not found
    known = {f["name"] for f in found} | {f.get("local_name") for f in found}
    return all(n in known for n in place.get("includes", []))


def run(pack: archive.Pack, places: list[dict], walks: list[dict]) -> dict:
    """All the timings, as plain values (so the worker can pass them to the page)."""
    out = {"places": [], "walks": []}

    # Where am I: one fresh lookup per place, nothing cached.
    times = []
    for p in places:
        lk = Lookup(pack, cache=False)
        t0 = time.perf_counter()
        found = lk.at(p["lon"], p["lat"])
        ms = (time.perf_counter() - t0) * 1000
        times.append(ms)
        out["places"].append({"name": p["name"], "ms": round(ms, 2), "ok": place_ok(p, found),
                              "tiles_read": lk.tiles_read, "read_ms": round(lk.read_ms, 2),
                              "decode_ms": round(lk.decode_ms, 2), "test_ms": round(lk.test_ms, 2),
                              "found": [f["name"] for f in found] or ["sea"]})
    out["where_am_i"] = summary(times)
    out["places_passed"] = sum(1 for r in out["places"] if r["ok"])

    # Walks: every step looked up, without and then with the pack tile cache.
    for w in walks:
        pts = walk_points(w["lat"], w["lon"], w["bearing"], w["step_km"], w["steps"])
        row = {"name": w["name"], "steps": w["steps"], "step_km": w["step_km"]}
        for label, cache in (("no_cache", False), ("tile_cache", True)):
            lk = Lookup(pack, cache=cache)
            times = []
            for lat, lon in pts[1:] if cache is False else pts:
                t0 = time.perf_counter()
                lk.at(lon, lat)
                times.append((time.perf_counter() - t0) * 1000)
            if cache:
                times = times[1:]  # the first lookup fills the cache; the steps follow it
            row[label] = {**summary(times), "tiles_read": lk.tiles_read, "read_ms": round(lk.read_ms, 1),
                          "decode_ms": round(lk.decode_ms, 1), "test_ms": round(lk.test_ms, 1)}
        out["walks"].append(row)
    return out


# The check places' walks: straight lines of steps, along coasts and across borders.
WALKS = [
    {"name": "West from Svolvær, along Lofoten, 1 km steps", "lat": 68.2343, "lon": 14.5683, "bearing": 250,
     "step_km": 1.0, "steps": 40},
    {"name": "West from Bergen, out through the islands to the sea, 0.5 km steps", "lat": 60.3913, "lon": 5.3221,
     "bearing": 270, "step_km": 0.5, "steps": 40},
    {"name": "East from Halden, across the Swedish border, 1 km steps", "lat": 59.1230, "lon": 11.3870,
     "bearing": 90, "step_km": 1.0, "steps": 40},
    {"name": "North from Stockholm, through the archipelago, 2 km steps", "lat": 59.3293, "lon": 18.0686,
     "bearing": 45, "step_km": 2.0, "steps": 40},
]


def report_lines(result: dict, where: str) -> list[str]:
    """The results as plain lines for a screen reader (no tables)."""
    lines = [f"== {where} =="]
    w = result["where_am_i"]
    lines.append(f"Where am I, at {w['count']} places, nothing cached: median {w['median_ms']} ms, "
                 f"90% within {w['p90_ms']} ms, slowest {w['max_ms']} ms. "
                 f"Places with the expected answer: {result['places_passed']} of {w['count']}.")
    for r in result["places"]:
        lines.append(f"  {'PASS' if r['ok'] else 'FAIL'} {r['name']}: {r['ms']} ms, {r['tiles_read']} pack tiles read "
                     f"(reading {r['read_ms']} ms, decoding {r['decode_ms']} ms, testing {r['test_ms']} ms). "
                     f"Found {', '.join(r['found'])}.")
    for row in result["walks"]:
        lines.append(f"Walk: {row['name']}, {row['steps']} steps.")
        for label, text in (("no_cache", "nothing cached"), ("tile_cache", "with the pack tile cache")):
            s = row[label]
            lines.append(f"  {text}: median {s['median_ms']} ms a step, 90% within {s['p90_ms']} ms, "
                         f"slowest {s['max_ms']} ms. Pack tiles read: {s['tiles_read']}. In all: reading "
                         f"{s['read_ms']} ms, decoding {s['decode_ms']} ms, testing {s['test_ms']} ms.")
    return lines
