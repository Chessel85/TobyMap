"""Whole outlines handed to Qt in one step, for the build's pictures (spike S2).

Making one QPointF for every point, and one drawLine for every outlined
edge, took most of the 45 minutes stage 3 spent on pictures. Qt can read a
QPainterPath from its stored form: the number of elements, then each
element as its kind (0 to move, 1 to draw a line to the point) and its x and
y, then the start of the last subpath and the fill rule, all big-endian.
That form is built here with NumPy, for every ring at once.

This is for the build's pictures only. The shells draw from the core's shape
list (AD-6) and are not changed.
"""
from __future__ import annotations

import numpy as np
import shapely

MOVE, LINE = 0, 1
ODD_EVEN, WINDING = 0, 1

_ELEMENT = np.dtype([("kind", ">i4"), ("x", ">f8"), ("y", ">f8")])


def path_bytes(xy: np.ndarray, move: np.ndarray, fill_rule: int = ODD_EVEN) -> bytes:
    """A QPainterPath's stored form: points xy (n by 2), and move[i] True where a new line starts."""
    n = len(xy)
    elements = np.empty(n, _ELEMENT)
    elements["kind"] = np.where(move, MOVE, LINE)
    elements["x"] = xy[:, 0] if n else []
    elements["y"] = xy[:, 1] if n else []
    starts = np.nonzero(move)[0]
    last_start = int(starts[-1]) if len(starts) else 0
    return (np.array([n], ">i4").tobytes() + elements.tobytes()
            + np.array([last_start, fill_rule], ">i4").tobytes())


def qpath(xy: np.ndarray, move: np.ndarray, fill_rule: int = ODD_EVEN):
    """A QPainterPath made from whole arrays of points, in one step."""
    from PySide6.QtCore import QByteArray, QDataStream, QIODevice
    from PySide6.QtGui import QPainterPath

    path = QPainterPath()
    if len(xy) == 0:
        return path
    # The buffer is kept in a name until the path is read: given to the
    # stream as a temporary, it could be freed while Qt still read it, which
    # crashed Python on large outlines.
    data = QByteArray(path_bytes(np.asarray(xy, float), np.asarray(move, bool), fill_rule))
    stream = QDataStream(data, QIODevice.OpenModeFlag.ReadOnly)
    stream >> path
    del stream, data
    return path


def simplify_parts(geom, tolerance: float):
    """Each part of a shape simplified on its own, for drawing.

    Simplifying a whole country keeps every part clear of every other, which
    took most of the time for countries with thousands of islands, such as
    Russia. A picture needs only each part kept valid on its own.
    """
    parts = shapely.get_parts(geom)
    parts = parts[shapely.get_type_id(parts) == 3]
    if len(parts) == 0:
        return shapely.MultiPolygon()
    simple = shapely.simplify(parts, tolerance, preserve_topology=True)
    simple = simple[~shapely.is_empty(simple)]
    return shapely.MultiPolygon(list(simple)) if len(simple) else shapely.MultiPolygon()


def polygon_arrays(geom) -> tuple[np.ndarray, np.ndarray]:
    """Every ring of the polygons in a shape: points, and where each ring starts.

    Rings keep their closing point, so each is drawn closed.
    """
    polys = shapely.get_parts(geom)
    polys = polys[shapely.get_type_id(polys) == 3]
    if len(polys) == 0:
        return np.zeros((0, 2)), np.zeros(0, bool)
    rings = shapely.get_rings(polys)
    xy, which = shapely.get_coordinates(rings, return_index=True)
    move = np.ones(len(xy), bool)
    move[1:] = which[1:] != which[:-1]
    return xy, move


def outline_arrays(coords: np.ndarray, rings: np.ndarray, seam: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The outlined edges of rings given as a flat point list, leaving out seam edges.

    coords: points (n by 2). rings: where each ring starts, with the end last.
    seam[i]: the edge from point i to the next point of its ring is
    artificial (along the 180 degree line or the South Pole) and is not
    outlined (AD-17). Each ring is closed by repeating its first point; the
    pen lifts (a move) after every seam edge.
    """
    rings = np.asarray(rings, np.intp)
    lengths = np.diff(rings)
    keep = lengths > 0
    starts, lengths = rings[:-1][keep], lengths[keep]
    if len(starts) == 0:
        return np.zeros((0, 2)), np.zeros(0, bool)
    # Index of each output point: the ring's points, then its first again.
    out_len = lengths + 1
    ring_of = np.repeat(np.arange(len(starts), dtype=np.intp), out_len)
    first_out = np.concatenate([[0], np.cumsum(out_len)[:-1]]).astype(np.intp)
    k = np.arange(int(out_len.sum()), dtype=np.intp) - first_out[ring_of]
    idx = starts[ring_of] + np.where(k == lengths[ring_of], 0, k)
    xy = coords[idx]
    move = np.zeros(len(idx), bool)
    move[first_out] = True
    # The element after a seam edge starts a new line instead of drawing it.
    prev = idx[:-1]
    after = np.nonzero(k[1:] > 0)[0] + 1
    move[after] |= seam[prev[after - 1]].astype(bool)
    return xy, move
