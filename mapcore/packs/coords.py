"""Compact coordinates (architecture 6.1, AD-5).

Each point of a shape is stored as a whole number of ten-millionths of a
degree (about 1 cm, the precision OpenStreetMap uses), as the difference from
the point before, written as zig-zag varints. Spike S2 found this makes packs
4.5 to 4.9 times smaller than WKB.

The layout of one encoded shape, all varints:

* the number of polygons;
* for each polygon, its number of rings, then the number of points in each
  ring (the closing point, which repeats the first, is not stored);
* then every point, longitude and latitude, each as the zig-zag difference
  from the point before (the first from 0, 0).

This module needs only NumPy, so it runs in Pyodide without Shapely. The two
functions at the end convert to and from Shapely shapes, and import Shapely
only when called. Arrays of offsets and indexes use np.intp, because NumPy in
Pyodide is 32-bit.
"""
from __future__ import annotations

import numpy as np

SCALE = 10_000_000  # ten-millionths of a degree


def _zigzag(v: np.ndarray) -> np.ndarray:
    return ((v << 1) ^ (v >> 63)).astype(np.uint64)


def varints(values) -> bytes:
    out = bytearray()
    for v in (values.tolist() if isinstance(values, np.ndarray) else values):
        v = int(v)
        while v >= 0x80:
            out.append((v & 0x7F) | 0x80)
            v >>= 7
        out.append(v)
    return bytes(out)


def all_varints(buf: bytes) -> np.ndarray:
    """Every varint in the buffer, decoded in one go with NumPy.

    Spike S4 found that decoding one number at a time in Python took about
    95% of a lookup in the browser.
    """
    a = np.frombuffer(buf, dtype=np.uint8)
    if a.size == 0 or a[-1] >= 0x80:
        raise ValueError("compact coordinates end in the middle of a number")
    ends = np.flatnonzero(a < 0x80).astype(np.intp)
    starts = np.empty_like(ends)
    starts[0] = 0
    starts[1:] = ends[:-1] + 1
    within = np.arange(a.size, dtype=np.intp) - np.repeat(starts, ends - starts + 1)
    parts = (a & 0x7F).astype(np.uint64) << (within * 7).astype(np.uint64)
    return np.bitwise_or.reduceat(parts, starts)


def encode(polygons) -> bytes:
    """Encode polygons given as lists of rings, each ring an (n, 2) array of
    longitude and latitude. Rings may be closed (last point equal to the
    first) or not; the closing point is never stored."""
    header = [len(polygons)]
    coords = []
    for rings in polygons:
        header.append(len(rings))
        for ring in rings:
            c = np.asarray(ring, dtype=np.float64).reshape(-1, 2)
            if len(c) > 1 and c[0, 0] == c[-1, 0] and c[0, 1] == c[-1, 1]:
                c = c[:-1]
            header.append(len(c))
            coords.append(c)
    allc = np.concatenate(coords) if coords else np.zeros((0, 2))
    ints = np.round(allc * SCALE).astype(np.int64)
    deltas = np.diff(ints, axis=0, prepend=np.zeros((1, 2), np.int64)).reshape(-1)
    return varints(header) + varints(_zigzag(deltas))


def _structure(values: np.ndarray) -> tuple[list[int], list[int], int]:
    """Rings per polygon, points per ring, and where the points start."""
    head = values[:4096].tolist()  # enough for most shapes' structure; more is read if needed

    def need(length: int) -> None:
        nonlocal head
        if length > len(head):
            if len(head) < len(values):
                head = values.tolist()
            if length > len(head):
                raise ValueError("compact coordinates are shorter than their header says")

    npoly, pos = head[0], 1
    poly_rings, ring_counts = [], []
    for _ in range(npoly):
        need(pos + 1)
        nrings = head[pos]
        need(pos + 1 + nrings)
        poly_rings.append(nrings)
        ring_counts.extend(head[pos + 1:pos + 1 + nrings])
        pos += 1 + nrings
    return poly_rings, ring_counts, pos


def point_count(buf: bytes) -> int:
    """How many points are stored, without decoding them (closing points not counted)."""
    _poly_rings, ring_counts, _pos = _structure(all_varints(buf))
    return int(sum(ring_counts))


def decode(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decode to (points, ring offsets, polygon offsets).

    points is an (m, 2) float64 array in which every ring is closed again.
    Ring i is points[ring_offsets[i]:ring_offsets[i + 1]], and polygon j is
    rings poly_offsets[j] to poly_offsets[j + 1]. These are the arrays
    Shapely's from_ragged_array takes.
    """
    values = all_varints(buf)
    poly_rings, ring_counts, pos = _structure(values)
    counts = np.asarray(ring_counts, dtype=np.intp)
    total = int(counts.sum())
    z = values[pos:pos + 2 * total]
    if z.size != 2 * total or pos + 2 * total != values.size:
        raise ValueError("compact coordinates do not match their header")
    deltas = ((z >> np.uint64(1)).astype(np.int64)) ^ (-(z & np.uint64(1)).astype(np.int64))
    pts = np.cumsum(deltas.reshape(-1, 2), axis=0) / SCALE
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.intp)
    closed = counts + 1
    ring_offsets = np.concatenate([[0], np.cumsum(closed)]).astype(np.intp)
    index = np.arange(int(closed.sum()), dtype=np.intp) - np.repeat(ring_offsets[:-1] - starts, closed)
    index[ring_offsets[1:] - 1] = starts
    poly_offsets = np.concatenate([[0], np.cumsum(poly_rings)]).astype(np.intp)
    return pts[index].reshape(-1, 2), ring_offsets, poly_offsets


def decode_many(bufs: list[bytes]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Decode several shapes in one go (P2-T14c): the same as decode() on each,
    joined, with a fourth array saying where each shape's polygons start.

    Drawing reads every shape of a tile at once. Decoding them one by one, a
    few thousand small NumPy calls, took most of the time of a drawing in a
    new area. Here only each shape's short header is read in Python.
    """
    if not bufs:
        empty = np.zeros(1, np.intp)
        return np.zeros((0, 2)), empty, empty, np.zeros(1, np.intp)
    values = all_varints(b"".join(bufs))
    sizes = np.fromiter((len(b) for b in bufs), np.intp, len(bufs))
    byte_starts = np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.intp)
    ends = np.frombuffer(b"".join(bufs), np.uint8) < 0x80
    counts_per_shape = np.add.reduceat(ends.astype(np.intp), byte_starts) if len(ends) else np.zeros(len(bufs), np.intp)
    value_starts = np.concatenate([[0], np.cumsum(counts_per_shape)]).astype(np.intp)
    head_all = values.tolist() if len(values) < 1 << 22 else None
    poly_rings: list[int] = []
    ring_counts: list[int] = []
    shape_polys = [0]
    point_value_runs = []   # (start, length) of each shape's point values in `values`
    for k in range(len(bufs)):
        v0, v1 = int(value_starts[k]), int(value_starts[k + 1])
        head = head_all[v0:v1] if head_all is not None else values[v0:v1].tolist()
        npoly, pos = head[0], 1
        before = len(ring_counts)
        for _ in range(npoly):
            nrings = head[pos]
            poly_rings.append(nrings)
            ring_counts.extend(head[pos + 1:pos + 1 + nrings])
            pos += 1 + nrings
        total = sum(ring_counts[before:])
        if pos + 2 * total != v1 - v0:
            raise ValueError("compact coordinates do not match their header")
        point_value_runs.append((v0 + pos, 2 * total))
        shape_polys.append(shape_polys[-1] + npoly)
    run_starts = np.fromiter((s for s, _ in point_value_runs), np.intp, len(bufs))
    run_lengths = np.fromiter((n for _, n in point_value_runs), np.intp, len(bufs))
    pick = np.repeat(run_starts - np.concatenate([[0], np.cumsum(run_lengths)[:-1]]).astype(np.intp), run_lengths) \
        + np.arange(int(run_lengths.sum()), dtype=np.intp)
    z = values[pick]
    deltas = ((z >> np.uint64(1)).astype(np.int64)) ^ (-(z & np.uint64(1)).astype(np.int64))
    deltas = deltas.reshape(-1, 2)
    # Each shape's first point is from 0, 0: restart the running sum at each shape.
    shape_points = run_lengths // 2
    firsts = np.concatenate([[0], np.cumsum(shape_points)[:-1]]).astype(np.intp)
    running = np.cumsum(deltas, axis=0)
    has = shape_points > 0
    base = np.zeros((len(bufs), 2), np.int64)
    base[has] = running[firsts[has]] - deltas[firsts[has]]
    pts = (running - np.repeat(base, shape_points, axis=0)) / SCALE
    counts = np.asarray(ring_counts, dtype=np.intp)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.intp)
    closed = counts + 1
    ring_offsets = np.concatenate([[0], np.cumsum(closed)]).astype(np.intp)
    index = np.arange(int(closed.sum()), dtype=np.intp) - np.repeat(ring_offsets[:-1] - starts, closed)
    index[ring_offsets[1:] - 1] = starts
    poly_offsets = np.concatenate([[0], np.cumsum(poly_rings)]).astype(np.intp)
    return pts[index].reshape(-1, 2), ring_offsets, poly_offsets, np.asarray(shape_polys, np.intp)


def to_shapes(bufs: list[bytes]):
    """Decode several shapes to an array of Shapely MultiPolygons, in one go (P2-T14c)."""
    import shapely

    pts, ring_offsets, poly_offsets, shape_offsets = decode_many(bufs)
    if not bufs:
        return np.empty(0, object)
    return shapely.from_ragged_array(shapely.GeometryType.MULTIPOLYGON, pts, (ring_offsets, poly_offsets, shape_offsets))


# Shapely, only when asked ------------------------------------------------------

def rings_of(geom) -> list[list[np.ndarray]]:
    """A Shapely Polygon or MultiPolygon as lists of ring arrays, for encode()."""
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    return [[np.asarray(r.coords) for r in (p.exterior, *p.interiors)] for p in polys]


def to_shape(buf: bytes):
    """Decode to a Shapely Polygon (one polygon) or MultiPolygon."""
    import shapely

    pts, ring_offsets, poly_offsets = decode(buf)
    npoly = len(poly_offsets) - 1
    geom = shapely.from_ragged_array(shapely.GeometryType.MULTIPOLYGON, pts,
                                     (ring_offsets, poly_offsets, np.array([0, npoly], dtype=np.intp)))[0]
    return geom.geoms[0] if npoly == 1 else geom
