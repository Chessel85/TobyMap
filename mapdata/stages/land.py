"""The OSM land polygons, for the boxes a build needs (AD-15).

The full file has about 870,000 small pieces of land covering the world. GDAL
reads it straight from the downloaded zip. Reading one box scans the whole
file, about 16 seconds, so each box's pieces are cached in the working folder.
"""
from __future__ import annotations

import hashlib
import pickle
from pathlib import Path

import numpy as np
import shapely

ZIP_NAME = "land-polygons-split-4326.zip"
INNER = "land-polygons-split-4326/land_polygons.shp"


def source_path(downloads: Path) -> Path:
    return downloads / "osm-land-polygons" / ZIP_NAME


def load(downloads: Path, working: Path, boxes: dict[str, list[float]], say=print) -> np.ndarray:
    """All land pieces touching any of the boxes, as one array of polygons."""
    import pyogrio

    zip_path = source_path(downloads)
    if not zip_path.is_file():
        raise SystemExit(f"{zip_path} is missing. Run: python -m mapdata fetch land-polygons")
    vsi = "/vsizip/" + zip_path.as_posix() + "/" + INNER
    stamp = f"{zip_path.stat().st_size}-{zip_path.stat().st_mtime_ns}"
    pieces = []
    for name, box in boxes.items():
        key = hashlib.sha1(f"{stamp}-{box}".encode()).hexdigest()[:12]
        cache = working / f"land-{name}-{key}.pkl"
        if cache.is_file():
            geoms = pickle.loads(cache.read_bytes())
            say(f"Land polygons for the {name} reading box: {len(geoms)} land tiles, from the cache.")
        else:
            _meta, _fids, wkb, _fields = pyogrio.raw.read(vsi, bbox=tuple(box), return_fids=True, read_geometry=True)
            geoms = shapely.from_wkb(wkb)
            working.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(pickle.dumps(geoms, protocol=pickle.HIGHEST_PROTOCOL))
            say(f"Land polygons for the {name} reading box: {len(geoms)} land tiles, read from the download.")
        pieces.append(geoms)
    return np.concatenate(pieces) if pieces else np.zeros(0, object)


def load_boxes(downloads: Path, working: Path, name: str, boxes: list[list[float]], say=print) -> np.ndarray:
    """All land tiles touching any of many reading boxes, read in one pass of the file.

    Used when the reading boxes are worked out from the shapes being built
    (spike S2 stages 2 and 3), which can give many small boxes, such as one
    for each group of atolls in Kiribati.
    """
    import pyogrio

    zip_path = source_path(downloads)
    if not zip_path.is_file():
        raise SystemExit(f"{zip_path} is missing. Run: python -m mapdata fetch land-polygons")
    vsi = "/vsizip/" + zip_path.as_posix() + "/" + INNER
    stamp = f"{zip_path.stat().st_size}-{zip_path.stat().st_mtime_ns}"
    key = hashlib.sha1(f"{stamp}-{sorted(map(tuple, boxes))}".encode()).hexdigest()[:12]
    cache = working / f"land-{name}-{key}.pkl"
    if cache.is_file():
        geoms = pickle.loads(cache.read_bytes())
        say(f"Land polygons for {len(boxes)} reading boxes: {len(geoms)} land tiles, from the cache.")
        return geoms
    mask = shapely.union_all([shapely.box(*b) for b in boxes])
    _meta, _fids, wkb, _fields = pyogrio.raw.read(vsi, mask=mask, return_fids=True, read_geometry=True)
    geoms = shapely.from_wkb(wkb)
    working.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(geoms, protocol=pickle.HIGHEST_PROTOCOL))
    say(f"Land polygons for {len(boxes)} reading boxes: {len(geoms)} land tiles, read from the download.")
    return geoms
