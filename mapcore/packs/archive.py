"""The pack archive, spike S2 version (AD-5, architecture 6.1 to 6.3).

One file: a header, the pieces, and a directory of named pieces at the end.
Each piece is compressed with zlib, so a reader fetches only the pieces it
needs, from a disk now, and over the internet later.

Layout:

* 16-byte header: b"TOBYPACK", format version (uint16), flags (uint16),
  reserved (uint32).
* the pieces, one after another.
* the directory: zlib-compressed JSON, {key: [offset, length]}.
* 16-byte footer: directory offset (uint64), directory length (uint64).

Keys used by the spike:

* "manifest": JSON, including the coordinate encoding and the tile levels.
* "features": JSON list of feature records.
* "tile/<level>/<x>/<y>": the exact shapes of every feature cut to that tile:
  JSON list of [feature index, "covered"] or [feature index, encoded shape].

Shapes are encoded either as WKB (hex in JSON is wasteful, so pieces with
shapes are stored as a small binary format, below), or in compact
coordinates: whole numbers of ten-millionths of a degree, each point stored
as the difference from the one before, as zig-zag varints (architecture 6.1).

Tile piece binary format: uint32 count, then for each entry: uint32 feature
index, uint8 kind (0 covered, 1 WKB, 2 compact), uint32 length, bytes.

Tiles: the world is split into a quadtree on longitude and latitude. At level
z there are 2**z columns of 360 / 2**z degrees and 2**z rows of 180 / 2**z
degrees.
"""
from __future__ import annotations

import io
import json
import struct
import zlib
from pathlib import Path

import numpy as np
import shapely

MAGIC = b"TOBYPACK"
VERSION = 1
COVERED, WKB, COMPACT = 0, 1, 2
SCALE = 10_000_000  # ten-millionths of a degree, about 1 cm


# Tiles ---------------------------------------------------------------------

def tile_of(lon: float, lat: float, level: int) -> tuple[int, int]:
    n = 2 ** level
    x = min(n - 1, max(0, int((lon + 180) / 360 * n)))
    y = min(n - 1, max(0, int((lat + 90) / 180 * n)))
    return x, y


def tile_box(level: int, x: int, y: int) -> tuple[float, float, float, float]:
    n = 2 ** level
    return (x * 360 / n - 180, y * 180 / n - 90, (x + 1) * 360 / n - 180, (y + 1) * 180 / n - 90)


def tile_key(level: int, x: int, y: int) -> str:
    return f"tile/{level}/{x}/{y}"


# Compact coordinates ----------------------------------------------------------

def _zigzag(v: np.ndarray) -> np.ndarray:
    return ((v << 1) ^ (v >> 63)).astype(np.uint64)


def _varints(values: np.ndarray) -> bytes:
    out = bytearray()
    for v in values.tolist():
        while v >= 0x80:
            out.append((v & 0x7F) | 0x80)
            v >>= 7
        out.append(v)
    return bytes(out)


def _read_varints(buf: bytes, pos: int, count: int) -> tuple[list[int], int]:
    out = []
    for _ in range(count):
        shift = result = 0
        while True:
            b = buf[pos]
            pos += 1
            result |= (b & 0x7F) << shift
            if b < 0x80:
                break
            shift += 7
        out.append(result)
    return out, pos


def encode_compact(geom) -> bytes:
    """Polygons and multipolygons only: count of polygons, rings per polygon,
    points per ring, then all points as zig-zag varint deltas."""
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    header = [len(polys)]
    coords = []
    for p in polys:
        rings = [p.exterior, *p.interiors]
        header.append(len(rings))
        for r in rings:
            c = np.asarray(r.coords)[:-1]  # the closing point is implied
            header.append(len(c))
            coords.append(c)
    allc = np.concatenate(coords) if coords else np.zeros((0, 2))
    ints = np.round(allc * SCALE).astype(np.int64)
    deltas = np.diff(ints, axis=0, prepend=np.zeros((1, 2), np.int64)).reshape(-1)
    return _varints(np.asarray(header, np.uint64)) + _varints(_zigzag(deltas))


def decode_compact(buf: bytes):
    pos = 0
    (npoly,), pos = _read_varints(buf, pos, 1)
    structure = []
    total = 0
    for _ in range(npoly):
        (nrings,), pos = _read_varints(buf, pos, 1)
        counts, pos = _read_varints(buf, pos, nrings)
        structure.append(counts)
        total += sum(counts)
    raw, pos = _read_varints(buf, pos, total * 2)
    z = np.asarray(raw, np.uint64)
    deltas = ((z >> np.uint64(1)).astype(np.int64)) ^ (-(z & np.uint64(1)).astype(np.int64))
    pts = np.cumsum(deltas.reshape(-1, 2), axis=0) / SCALE
    polys, k = [], 0
    for counts in structure:
        rings = []
        for c in counts:
            ring = pts[k:k + c]
            k += c
            rings.append(np.vstack([ring, ring[:1]]))
        polys.append(shapely.Polygon(rings[0], rings[1:]))
    return polys[0] if len(polys) == 1 else shapely.MultiPolygon(polys)


# Writing -------------------------------------------------------------------

def encode_tile(entries: list[tuple[int, int, bytes]]) -> bytes:
    out = io.BytesIO()
    out.write(struct.pack("<I", len(entries)))
    for index, kind, data in entries:
        out.write(struct.pack("<IBI", index, kind, len(data)))
        out.write(data)
    return out.getvalue()


def decode_tile(buf: bytes) -> list[tuple[int, int, bytes]]:
    (count,) = struct.unpack_from("<I", buf, 0)
    pos, out = 4, []
    for _ in range(count):
        index, kind, length = struct.unpack_from("<IBI", buf, pos)
        pos += 9
        out.append((index, kind, buf[pos:pos + length]))
        pos += length
    return out


class Writer:
    def __init__(self, path: Path, level: int = 6):
        self.path = Path(path)
        self.out = open(self.path, "wb")
        self.out.write(MAGIC + struct.pack("<HHI", VERSION, 0, 0))
        self.directory: dict[str, list[int]] = {}
        self.level = level

    def put(self, key: str, data: bytes) -> None:
        packed = zlib.compress(data, 9)
        self.directory[key] = [self.out.tell(), len(packed)]
        self.out.write(packed)

    def put_json(self, key: str, value) -> None:
        self.put(key, json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    def close(self) -> None:
        offset = self.out.tell()
        directory = zlib.compress(json.dumps(self.directory, sort_keys=True, separators=(",", ":")).encode(), 9)
        self.out.write(directory)
        self.out.write(struct.pack("<QQ", offset, len(directory)))
        self.out.close()


# Reading -------------------------------------------------------------------

class Pack:
    """Reads pieces on demand from a pack file."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.file = open(self.path, "rb")
        head = self.file.read(16)
        if head[:8] != MAGIC:
            raise ValueError(f"{path} is not a TobyMap pack")
        self.version = struct.unpack_from("<H", head, 8)[0]
        self.reads = 0
        self.file.seek(-16, 2)
        offset, length = struct.unpack("<QQ", self.file.read(16))
        self.file.seek(offset)
        self.directory = json.loads(zlib.decompress(self.file.read(length)))
        self.manifest = self.get_json("manifest")
        self.features = self.get_json("features")
        self.levels = self.manifest["tile_levels"]
        self.reads = 0

    def close(self) -> None:
        self.file.close()

    def get(self, key: str) -> bytes | None:
        entry = self.directory.get(key)
        if entry is None:
            return None
        self.file.seek(entry[0])
        self.reads += 1
        return zlib.decompress(self.file.read(entry[1]))

    def get_json(self, key: str):
        data = self.get(key)
        return None if data is None else json.loads(data)

    def at(self, lon: float, lat: float) -> list[dict]:
        """Every feature containing the point, smallest first (LOC-2)."""
        point = shapely.Point(lon, lat)
        found = []
        for level in self.levels:
            data = self.get(tile_key(level, *tile_of(lon, lat, level)))
            if data is None:
                continue
            for index, kind, blob in decode_tile(data):
                if kind == COVERED:
                    found.append(self.features[index])
                    continue
                geom = shapely.from_wkb(blob) if kind == WKB else decode_compact(blob)
                if shapely.intersects(geom, point):
                    found.append(self.features[index])
        found.sort(key=lambda f: (f["area_km2"], f["id"]))
        return found
