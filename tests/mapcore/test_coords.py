"""Compact coordinates and the pack tile grid (AD-5, architecture 6.1 and 6.3)."""
import numpy as np
import pytest

from mapcore.packs import coords, tiles

shapely = pytest.importorskip("shapely")


def test_tiles():
    assert tiles.tile_of(-180, -90, 3) == (0, 0)
    assert tiles.tile_of(179.999, 89.999, 3) == (7, 7)
    assert tiles.tile_box(1, 1, 1) == (0, 0, 180, 90)
    x, y = tiles.tile_of(-1.3, 50.7, 10)
    w, s, e, n = tiles.tile_box(10, x, y)
    assert w <= -1.3 < e and s <= 50.7 < n


def test_compact_coordinates_round_trip_to_a_centimetre():
    outer = [(-1.0, 50.0), (-0.9, 50.0), (-0.9, 50.1), (-1.0, 50.1), (-1.0, 50.0)]
    hole = [(-0.96, 50.04), (-0.94, 50.04), (-0.94, 50.06), (-0.96, 50.06), (-0.96, 50.04)]
    island = shapely.box(-0.85, 50.0, -0.8, 50.05)
    geom = shapely.MultiPolygon([shapely.Polygon(outer, [hole]), island])
    blob = coords.encode(coords.rings_of(geom))
    back = coords.to_shape(blob)
    assert back.geom_type == "MultiPolygon" and len(back.geoms) == 2
    assert np.allclose(shapely.get_coordinates(back), shapely.get_coordinates(geom), atol=1e-7)
    assert len(blob) < len(shapely.to_wkb(geom)) / 2


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


def _decode_one_by_one(buf: bytes):
    """The first decoder (spike S2), one number at a time: the reference for the faster one."""
    pos = 0
    (npoly,), pos = _read_varints(buf, pos, 1)
    structure, total = [], 0
    for _ in range(npoly):
        (nrings,), pos = _read_varints(buf, pos, 1)
        counts, pos = _read_varints(buf, pos, nrings)
        structure.append(counts)
        total += sum(counts)
    raw, pos = _read_varints(buf, pos, total * 2)
    z = np.asarray(raw, np.uint64)
    deltas = ((z >> np.uint64(1)).astype(np.int64)) ^ (-(z & np.uint64(1)).astype(np.int64))
    pts = np.cumsum(deltas.reshape(-1, 2), axis=0) / coords.SCALE
    polys, k = [], 0
    for counts in structure:
        rings = []
        for c in counts:
            ring = pts[k:k + c]
            k += c
            rings.append(np.vstack([ring, ring[:1]]))
        polys.append(shapely.Polygon(rings[0], rings[1:]))
    return polys[0] if len(polys) == 1 else shapely.MultiPolygon(polys)


def test_fast_decoder_gives_exactly_what_the_first_one_did():
    # Spike S4: decoding was 95% of a lookup's time in the browser, so it is
    # done with NumPy in one go. It must give exactly the same shapes.
    rng = np.random.default_rng(4)
    shapes = [
        shapely.box(-1, 50, -0.9, 50.1),
        shapely.Polygon([(-179.9999999, -89.5), (179.9999999, -89.5), (0, 89.9999999)]),
        shapely.MultiPolygon([shapely.box(0, 0, 1, 1).difference(shapely.box(0.2, 0.2, 0.4, 0.4)
                                                                 ).difference(shapely.box(0.6, 0.6, 0.8, 0.8)),
                              shapely.box(5, 5, 6, 6)]),
        # many islands with random coastlines, as in Norway
        shapely.MultiPolygon([shapely.Point(x, y).buffer(r, quad_segs=int(q)) for x, y, r, q in
                              zip(rng.uniform(0, 30, 300), rng.uniform(55, 71, 300), rng.uniform(1e-5, 0.01, 300),
                                  rng.integers(1, 40, 300))]),
    ]
    for geom in shapes:
        blob = coords.encode(coords.rings_of(geom))
        old, new = _decode_one_by_one(blob), coords.to_shape(blob)
        assert new.geom_type == old.geom_type
        assert shapely.equals_exact(new, old, tolerance=0)


def test_negative_and_large_deltas():
    geom = shapely.Polygon([(-179.9999999, -89.5), (179.9999999, -89.5), (0, 89.9999999)])
    back = coords.to_shape(coords.encode(coords.rings_of(geom)))
    assert np.allclose(shapely.get_coordinates(back), shapely.get_coordinates(geom), atol=1e-7)
