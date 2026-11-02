"""The spike S2 pack archive: compact coordinates, tiles, and point queries (AD-5, architecture 6.1 to 6.3)."""
import numpy as np
import pytest
import shapely

from mapcore.packs import archive

pytest.importorskip("mapdata")
from mapdata.stages import pack_write  # noqa: E402


def test_tiles():
    assert archive.tile_of(-180, -90, 3) == (0, 0)
    assert archive.tile_of(179.999, 89.999, 3) == (7, 7)
    assert archive.tile_box(1, 1, 1) == (0, 0, 180, 90)
    x, y = archive.tile_of(-1.3, 50.7, 10)
    w, s, e, n = archive.tile_box(10, x, y)
    assert w <= -1.3 < e and s <= 50.7 < n


def test_compact_coordinates_round_trip_to_a_centimetre():
    outer = [(-1.0, 50.0), (-0.9, 50.0), (-0.9, 50.1), (-1.0, 50.1), (-1.0, 50.0)]
    hole = [(-0.96, 50.04), (-0.94, 50.04), (-0.94, 50.06), (-0.96, 50.06), (-0.96, 50.04)]
    island = shapely.box(-0.85, 50.0, -0.8, 50.05)
    geom = shapely.MultiPolygon([shapely.Polygon(outer, [hole]), island])
    back = archive.decode_compact(archive.encode_compact(geom))
    assert back.geom_type == "MultiPolygon" and len(back.geoms) == 2
    assert np.allclose(shapely.get_coordinates(back), shapely.get_coordinates(geom), atol=1e-7)
    assert len(archive.encode_compact(geom)) < len(shapely.to_wkb(geom)) / 2


def _decode_compact_one_by_one(buf: bytes):
    """The first decoder (spike S2), one number at a time: the reference for the faster one."""
    pos = 0
    (npoly,), pos = archive._read_varints(buf, pos, 1)
    structure, total = [], 0
    for _ in range(npoly):
        (nrings,), pos = archive._read_varints(buf, pos, 1)
        counts, pos = archive._read_varints(buf, pos, nrings)
        structure.append(counts)
        total += sum(counts)
    raw, pos = archive._read_varints(buf, pos, total * 2)
    z = np.asarray(raw, np.uint64)
    deltas = ((z >> np.uint64(1)).astype(np.int64)) ^ (-(z & np.uint64(1)).astype(np.int64))
    pts = np.cumsum(deltas.reshape(-1, 2), axis=0) / archive.SCALE
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
        blob = archive.encode_compact(geom)
        old, new = _decode_compact_one_by_one(blob), archive.decode_compact(blob)
        assert new.geom_type == old.geom_type
        assert shapely.equals_exact(new, old, tolerance=0)


def test_negative_and_large_deltas():
    geom = shapely.Polygon([(-179.9999999, -89.5), (179.9999999, -89.5), (0, 89.9999999)])
    back = archive.decode_compact(archive.encode_compact(geom))
    assert np.allclose(shapely.get_coordinates(back), shapely.get_coordinates(geom), atol=1e-7)


@pytest.mark.parametrize("encoding", ["wkb", "compact"])
def test_pack_answers_what_is_here(tmp_path, encoding):
    big = shapely.box(-10, 40, 10, 60).difference(shapely.box(-1, 49, 1, 51))  # a hole
    small = shapely.box(-0.5, 49.5, 0.5, 50.5)                                 # inside the hole
    records = [{"id": "t:big", "name": "Big", "area_km2": 2.0}, {"id": "t:small", "name": "Small", "area_km2": 1.0}]
    path = tmp_path / f"t-{encoding}.pack"
    stats = pack_write.write(path, {"name": "test"}, records, [big, small], encoding, say=lambda s: None)
    assert stats["pieces"] > 0
    pack = archive.Pack(path)
    try:
        assert [f["id"] for f in pack.at(0, 50)] == ["t:small"]
        assert [f["id"] for f in pack.at(5, 45)] == ["t:big"]
        assert pack.at(-0.8, 50.8) == []        # in the hole, outside the small box
        assert pack.at(30, 50) == []            # elsewhere
        assert pack.manifest["encoding"] == encoding
    finally:
        pack.close()


def test_pack_reads_through_a_byte_source(tmp_path):
    # The web version reads packs from the browser's private storage, not a
    # file (spike S4, DP102), so the reader takes anything with size and read.
    big = shapely.box(-10, 40, 10, 60).difference(shapely.box(-1, 49, 1, 51))
    small = shapely.box(-0.5, 49.5, 0.5, 50.5)
    records = [{"id": "t:big", "name": "Big", "area_km2": 2.0}, {"id": "t:small", "name": "Small", "area_km2": 1.0}]
    path = tmp_path / "t.pack"
    pack_write.write(path, {"name": "test"}, records, [big, small], "compact", say=lambda s: None)
    data = path.read_bytes()

    class Bytes:
        size = len(data)
        calls = 0

        def read(self, offset, length):
            Bytes.calls += 1
            return data[offset:offset + length]

    from_file, from_source = archive.Pack(path), archive.Pack(Bytes())
    try:
        for lon, lat in ((0, 50), (5, 45), (-0.8, 50.8), (30, 50)):
            assert from_source.at(lon, lat) == from_file.at(lon, lat)
        assert Bytes.calls > 0 and from_source.reads == from_file.reads
    finally:
        from_file.close()
        from_source.close()


def test_whole_tiles_are_stored_as_covered(tmp_path):
    # A detailed edge (like a coastline) makes the writer cut finer tiles,
    # and the tiles wholly inside are then stored as "covered".
    big = shapely.segmentize(shapely.box(-40, 10, 40, 80), 0.01)
    path = tmp_path / "covered.pack"
    pack_write.write(path, {"name": "test"}, [{"id": "t:big", "name": "Big", "area_km2": 1.0}], [big],
                     "compact", say=lambda s: None)
    pack = archive.Pack(path)
    try:
        kinds = set()
        for key in pack.directory:
            if key.startswith("tile/"):
                kinds |= {kind for _i, kind, _b in archive.decode_tile(pack.get(key))}
        assert archive.COVERED in kinds
        assert [f["id"] for f in pack.at(0, 45)] == ["t:big"]
    finally:
        pack.close()
