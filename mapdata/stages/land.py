"""The OSM land polygons, for the boxes a build needs (AD-15).

The full file has about 870,000 land tiles covering the world, in a
shapefile inside the downloaded zip. Reading one box from it scans the whole
file, about 16 seconds each time. So the first build after a download
converts it once into the land index, in the working folder: the bounds of
every land tile in one array, and the land tiles themselves, one after the
other, in one file. A build then finds the land tiles it needs from the
bounds and reads only those, in a second or two.

Each set of reading boxes is still cached in the build's working folder.
"""
from __future__ import annotations

import hashlib
import pickle
import time
from pathlib import Path

import numpy as np
import shapely

ZIP_NAME = "land-polygons-split-4326.zip"
INNER = "land-polygons-split-4326/land_polygons.shp"
INDEX_VERSION = "land-index-v1"
CHUNK = 50_000


def source_path(downloads: Path) -> Path:
    return downloads / "osm-land-polygons" / ZIP_NAME


def _source(downloads: Path) -> tuple[Path, str]:
    zip_path = source_path(downloads)
    if not zip_path.is_file():
        raise SystemExit(f"{zip_path} is missing. Run: python -m mapdata fetch land-polygons")
    return zip_path, f"{zip_path.stat().st_size}-{zip_path.stat().st_mtime_ns}"


def vsi_path(zip_path: Path) -> str:
    return "/vsizip/" + zip_path.as_posix() + "/" + INNER


class LandIndex:
    """The land tiles in a form a build can read in part (see the module's notes).

    The folder holds bounds.npy (west, south, east, north of each land tile),
    offsets.npy (where each land tile starts in shapes.bin, and one more for
    the end) and shapes.bin (each land tile as WKB, in the order of the
    download, so a build reads them in the same order as from the shapefile).
    """

    def __init__(self, folder: Path):
        self.folder = folder
        self.bounds = np.load(folder / "bounds.npy")
        self.offsets = np.load(folder / "offsets.npy")

    def __len__(self) -> int:
        return len(self.bounds)

    def touching(self, boxes: list) -> np.ndarray:
        """The positions of the land tiles whose bounds touch any of the boxes, in file order."""
        b = self.bounds
        hit = np.zeros(len(b), bool)
        for w, s, e, n in boxes:
            hit |= (b[:, 0] <= e) & (b[:, 2] >= w) & (b[:, 1] <= n) & (b[:, 3] >= s)
        return np.nonzero(hit)[0]

    def read(self, positions: np.ndarray) -> np.ndarray:
        """The land tiles at the positions, as shapes."""
        if len(positions) == 0:
            return np.zeros(0, object)
        data = np.memmap(self.folder / "shapes.bin", dtype=np.uint8, mode="r")
        try:
            starts, ends = self.offsets[positions], self.offsets[positions + 1]
            blobs = [data[a:b].tobytes() for a, b in zip(starts.tolist(), ends.tolist())]
        finally:
            del data
        return shapely.from_wkb(np.array(blobs, dtype=object))

    def within(self, mask) -> np.ndarray:
        """Every land tile that touches the mask, as the download's reader would return them."""
        if mask is None or mask.is_empty:
            return np.zeros(0, object)
        parts = shapely.get_parts(mask)
        geoms = self.read(self.touching([p.bounds for p in parts]))
        if len(geoms) == 0:
            return geoms
        shapely.prepare(mask)
        return geoms[shapely.intersects(mask, geoms)]


def index_folder(working_root: Path, stamp: str) -> Path:
    key = hashlib.sha1(f"{stamp}-{INDEX_VERSION}".encode()).hexdigest()[:12]
    return working_root / f"land-index-{key}"


def open_index(downloads: Path, working_root: Path, say=print) -> LandIndex:
    """The land index for the downloaded land polygons, made first if there is none."""
    zip_path, stamp = _source(downloads)
    folder = index_folder(working_root, stamp)
    if (folder / "offsets.npy").is_file():
        return LandIndex(folder)
    build_index(vsi_path(zip_path), folder, say)
    return LandIndex(folder)


def build_index(vsi: str, folder: Path, say=print) -> None:
    """Convert the land polygons once into the land index (about a minute or two)."""
    import pyogrio

    start = time.perf_counter()
    say("Making the land index from the downloaded land polygons. This is done once for each download.")
    _meta, _fids, wkb, _fields = pyogrio.raw.read(vsi, return_fids=True, read_geometry=True)
    tmp = folder.with_name(folder.name + ".tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    lengths = np.fromiter((len(b) for b in wkb), dtype=np.int64, count=len(wkb))
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    bounds = np.zeros((len(wkb), 4))
    for k in range(0, len(wkb), CHUNK):
        bounds[k:k + CHUNK] = shapely.bounds(shapely.from_wkb(wkb[k:k + CHUNK]))
    with open(tmp / "shapes.bin", "wb") as f:
        for b in wkb:
            f.write(b)
    np.save(tmp / "bounds.npy", bounds)
    np.save(tmp / "offsets.npy", offsets)
    tmp.replace(folder)
    say(f"Land index made: {len(wkb):,} land tiles, {offsets[-1] / 1e6:,.0f} MB, "
        f"in {time.perf_counter() - start:.0f} seconds.")


def load(downloads: Path, working: Path, boxes: dict[str, list[float]], say=print) -> np.ndarray:
    """All land tiles touching any of the boxes, as one array of polygons."""
    _zip, stamp = _source(downloads)
    pieces = []
    index = None
    for name, box in boxes.items():
        key = hashlib.sha1(f"{stamp}-{box}".encode()).hexdigest()[:12]
        cache = working / f"land-{name}-{key}.pkl"
        if cache.is_file():
            geoms = pickle.loads(cache.read_bytes())
            say(f"Land polygons for the {name} reading box: {len(geoms)} land tiles, from the cache.")
        else:
            index = index or open_index(downloads, working.parent, say)
            geoms = index.within(shapely.box(*box))
            working.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(pickle.dumps(geoms, protocol=pickle.HIGHEST_PROTOCOL))
            say(f"Land polygons for the {name} reading box: {len(geoms)} land tiles, read from the land index.")
        pieces.append(geoms)
    return np.concatenate(pieces) if pieces else np.zeros(0, object)


def load_boxes(downloads: Path, working: Path, name: str, boxes: list[list[float]], say=print) -> np.ndarray:
    """All land tiles touching any of many reading boxes, each land tile once.

    Used when the reading boxes are worked out from the shapes being built
    (spike S2 stages 2 and 3), which can give many small boxes, such as one
    for each group of atolls in Kiribati.
    """
    _zip, stamp = _source(downloads)
    key = hashlib.sha1(f"{stamp}-{sorted(map(tuple, boxes))}".encode()).hexdigest()[:12]
    cache = working / f"land-{name}-{key}.pkl"
    if cache.is_file():
        geoms = pickle.loads(cache.read_bytes())
        say(f"Land polygons for {len(boxes)} reading boxes: {len(geoms)} land tiles, from the cache.")
        return geoms
    mask = shapely.union_all([shapely.box(*b) for b in boxes])
    geoms = open_index(downloads, working.parent, say).within(mask)
    working.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(geoms, protocol=pickle.HIGHEST_PROTOCOL))
    say(f"Land polygons for {len(boxes)} reading boxes: {len(geoms)} land tiles, read from the land index.")
    return geoms
