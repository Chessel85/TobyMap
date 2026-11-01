"""The Natural Earth world sample, for spike S5 (P0-T8).

A stand-in for the base pack: 177 countries at 1:110 million. It answers
"which country is at this point" and "which countries are nearest", which is
enough to make the globe spike speak. Phase 1 replaces it with real packs read
through mapcore.packs.

Point in polygon uses the even-odd rule over every ring of a country, so holes
(Lesotho inside South Africa) work. Natural Earth already splits shapes at the
180 degree line, so no ring crosses it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from mapcore.geo import sphere

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_FILE = DATA_DIR / "world_110m.json"


@dataclass
class Ring:
    lon: np.ndarray
    lat: np.ndarray
    bbox: tuple[float, float, float, float]  # west, south, east, north


@dataclass
class Country:
    id: str
    name: str
    long_name: str
    sovereign: str
    continent: str
    subregion: str
    population: int
    colour: int
    centre_lon: float
    centre_lat: float
    polygons: list[list[Ring]] = field(repr=False)
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)

    def rings(self):
        for poly in self.polygons:
            yield from poly

    def contains(self, lat: float, lon: float) -> bool:
        w, s, e, n = self.bbox
        if not (s <= lat <= n and w <= lon <= e):
            return False
        inside = False
        for ring in self.rings():
            rw, rs, re_, rn = ring.bbox
            if not (rs <= lat <= rn and rw <= lon <= re_):
                continue
            if _ring_contains(ring.lon, ring.lat, lon, lat):
                inside = not inside
        return inside


def _ring_contains(xs: np.ndarray, ys: np.ndarray, x: float, y: float) -> bool:
    xj, yj = np.roll(xs, 1), np.roll(ys, 1)
    crosses = (ys > y) != (yj > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        x_at = (xj - xs) * (y - ys) / (yj - ys) + xs
    return bool(np.count_nonzero(crosses & (x < x_at)) % 2)


def _make_ring(flat: list[float]) -> Ring:
    arr = np.asarray(flat, dtype=np.float64).reshape(-1, 2)
    lon, lat = arr[:, 0].copy(), arr[:, 1].copy()
    return Ring(lon, lat, (float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())))


class WorldSample:
    def __init__(self, data: dict):
        self.source = data.get("source", "")
        self.countries: list[Country] = []
        for c in data["countries"]:
            polygons = [[_make_ring(r) for r in poly] for poly in c["polygons"]]
            rings = [r for poly in polygons for r in poly]
            bbox = (min(r.bbox[0] for r in rings), min(r.bbox[1] for r in rings),
                    max(r.bbox[2] for r in rings), max(r.bbox[3] for r in rings))
            self.countries.append(Country(
                id=c["id"], name=c["name"], long_name=c["long_name"], sovereign=c["sovereign"],
                continent=c["continent"], subregion=c["subregion"], population=c["population"],
                colour=c["colour"], centre_lon=c["centre"][0], centre_lat=c["centre"][1],
                polygons=polygons, bbox=bbox,
            ))
        self._by_id = {c.id: c for c in self.countries}

    @classmethod
    def load(cls, path: Path | str | None = None) -> "WorldSample":
        path = Path(path) if path else DEFAULT_FILE
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def by_id(self, cid: str) -> Country | None:
        return self._by_id.get(cid)

    def country_at(self, lat: float, lon: float) -> Country | None:
        lon = sphere.wrap_lon(lon)
        for c in self.countries:
            if c.contains(lat, lon):
                return c
        return None

    def nearest(self, lat: float, lon: float, count: int = 8, exclude: str | None = None):
        """The nearest countries by distance to their label point: (country, km, bearing)."""
        found = []
        for c in self.countries:
            if c.id == exclude:
                continue
            km = sphere.distance_km(lat, lon, c.centre_lat, c.centre_lon)
            found.append((km, c.name, c))
        found.sort(key=lambda t: (t[0], t[1]))
        return [(c, km, sphere.bearing_deg(lat, lon, c.centre_lat, c.centre_lon)) for km, _n, c in found[:count]]
