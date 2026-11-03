"""Pack tiles and drawing tiles: the grid, and the tile entries in each (architecture 6.3).

The world is split into a grid on longitude and latitude that divides by four
at each tile level. At tile level z there are 2**z columns of 360 / 2**z
degrees and 2**z rows of 180 / 2**z degrees; column 0 starts at 180 degrees
west and row 0 at the South Pole.

A pack tile or drawing tile is stored as one record holding its tile entries:
uint32 count, then for each entry uint32 feature number, uint8 kind, uint32
length, and that many bytes. All numbers are little-endian. Entries are in
order of feature number, then of their bytes.

Kinds:

* COVERED (0): a covered note. The area covers the whole pack tile; no bytes.
* COMPACT (2): part of the area's shape, in compact coordinates (coords.py).

Kind 1 was WKB in the spike S2 packs and is refused.
"""
from __future__ import annotations

import struct
from typing import NamedTuple

COVERED, COMPACT = 0, 2
KINDS = (COVERED, COMPACT)
MAX_TILE_LEVEL = 18
# AD-5, from spike S2: a tile entry holds at most this many points, and a
# pack tile at most TILE_POINTS in all its tile entries together, except at
# MAX_TILE_LEVEL, where nothing can be split further.
ENTRY_POINTS = 4000
TILE_POINTS = 20000


class TileEntry(NamedTuple):
    feature: int  # the feature number in this pack
    kind: int
    data: bytes


def tile_of(lon: float, lat: float, level: int) -> tuple[int, int]:
    n = 2 ** level
    x = min(n - 1, max(0, int((lon + 180) / 360 * n)))
    y = min(n - 1, max(0, int((lat + 90) / 180 * n)))
    return x, y


def tile_box(level: int, x: int, y: int) -> tuple[float, float, float, float]:
    """West, south, east and north edges of a pack tile, in degrees."""
    n = 2 ** level
    return (x * 360 / n - 180, y * 180 / n - 90, (x + 1) * 360 / n - 180, (y + 1) * 180 / n - 90)


def tile_key(level: int, x: int, y: int) -> str:
    return f"tile/{level}/{x}/{y}"


def drawing_key(drawing_level: int, x: int, y: int) -> str:
    return f"draw/{drawing_level}/{x}/{y}"


def in_grid(level: int, x: int, y: int) -> bool:
    return 0 <= level <= MAX_TILE_LEVEL and 0 <= x < 2 ** level and 0 <= y < 2 ** level


_ENTRY = struct.Struct("<IBI")


def encode_entries(entries) -> bytes:
    entries = sorted(TileEntry(*e) for e in entries)
    out = [struct.pack("<I", len(entries))]
    for feature, kind, data in entries:
        out.append(_ENTRY.pack(feature, kind, len(data)))
        out.append(bytes(data))
    return b"".join(out)


def decode_entries(buf: bytes) -> list[TileEntry]:
    (count,) = struct.unpack_from("<I", buf, 0)
    pos, out = 4, []
    for _ in range(count):
        feature, kind, length = _ENTRY.unpack_from(buf, pos)
        pos += _ENTRY.size
        if pos + length > len(buf):
            raise ValueError("a tile entry runs past the end of its record")
        out.append(TileEntry(feature, kind, bytes(buf[pos:pos + length])))
        pos += length
    if pos != len(buf):
        raise ValueError("a tile record has bytes after its last tile entry")
    return out
