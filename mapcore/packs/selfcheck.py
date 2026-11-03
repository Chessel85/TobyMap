"""A self-check of the pack format, run where the core runs (P1-T2).

It writes a small pack in memory, reads it back through a byte source, and
checks what the format promises: every kind of record comes back as written,
a damaged record is found while the rest can still be read, a pack for later
application versions is refused, and the same pack written twice is the same
bytes. It needs only the standard library and NumPy, so the browser tests
run it in Pyodide, where NumPy is 32-bit. Diagnostics can run it too (P1-T15).

run() returns a list of problems, empty when all is well.
"""
from __future__ import annotations

import io

import numpy as np

from mapcore.packs import coords, pack, tiles
from mapcore.packs.source import MemorySource


def sample_features() -> list[dict]:
    def feature(i, layer, name, parents=()):
        return {"id": f"test:{layer}:{i}", "source": "test", "layer": layer, "type": "test area",
                "names": {"en": name}, "rank": 2 if layer == "countries" else 4, "area_km2": 1000.0 + i,
                "bbox": [-1.0 - i, 50.0, 1.0 + i, 51.5], "width_km": 140.5, "colour": i % 5,
                "point": [0.25, 50.5], "parents": list(parents)}
    out = [feature(i, "countries", f"Country {i}") for i in range(300)]
    out += [feature(i, "regions", f"Région {i}", [f"test:countries:{i % 300}"]) for i in range(300)]
    return out


def sample_shape() -> list[list[np.ndarray]]:
    """A square with a hole, and an island across the 180 degree line's east side."""
    outer = np.array([[-1.0, 50.0], [1.0, 50.0], [1.0, 51.5], [-1.0, 51.5], [-1.0, 50.0]])
    hole = np.array([[-0.2, 50.4], [0.2, 50.4], [0.2, 50.6], [-0.2, 50.6]])
    island = np.array([[179.9999999, -16.0], [179.5, -16.5], [179.9, -17.1]])
    return [[outer, hole], [island]]


MANIFEST = {
    "name": "selfcheck",
    "version": "1",
    "coverage": {"kind": "world"},
    "app_versions": {"from": "0.0.1"},
    "sources": [{"name": "Test source", "licence": "ODbL 1.0", "date": "2026-10-26"},
                {"name": "Second source", "licence": "CC-BY 4.0", "date": "2026-11-01"}],
    "drawing_levels": [{"id": 0, "tile_level": 1, "zooms": [1, 3]}],
}
LAYERS = [{"id": "countries", "name": "Countries", "style": "country", "zooms": [1, 10]},
          {"id": "regions", "name": "Regions", "style": "region", "zooms": [4, 14]}]
ATTRIBUTION = "© OpenStreetMap contributors. Test source, Second source."


def build(manifest: dict | None = None) -> bytes:
    out = io.BytesIO()
    writer = pack.PackWriter(out)
    numbers = writer.add_features(sample_features())
    shape = coords.encode(sample_shape())
    writer.add_tile(3, 3, 5, [(numbers["test:regions:7"], tiles.COMPACT, shape),
                              (numbers["test:countries:7"], tiles.COVERED, b"")])
    writer.add_tile(4, 7, 11, [(numbers["test:countries:1"], tiles.COMPACT, shape)])
    writer.add_drawing_tile(0, 1, 1, [(numbers["test:countries:7"], tiles.COMPACT, shape)])
    writer.finish(manifest or MANIFEST, ATTRIBUTION, LAYERS)
    return out.getvalue()


def run(app_version: str = "0.1.0") -> list[str]:
    problems = []

    def expect(ok, text):
        if not ok:
            problems.append(text)

    data = build()
    expect(build() == data, "the same pack written twice is not the same bytes")
    source = MemorySource(data, "selfcheck.pack")
    p = pack.Pack(source, app_version=app_version)
    expect(p.manifest["built"] == "2026-11-01", "the build date is not the latest source date")
    expect(p.attribution == ATTRIBUTION, "the attribution did not come back")
    expect("Open Database License" in p.licence, "the licence notice is missing")
    expect(p.layers == LAYERS, "the layer definitions did not come back")
    features = sample_features()
    for f in features:
        expect(p.feature_by_id(f["id"]) == f, f"feature {f['id']} did not come back")
    numbers = {p.feature(n)["id"]: n for n in range(p.feature_count)}
    expect(len(numbers) == len(features), "feature numbers are not one to one")
    entries = p.tile(3, 3, 5)
    expect([(e.feature, e.kind) for e in entries] ==
           sorted([(numbers["test:regions:7"], tiles.COMPACT), (numbers["test:countries:7"], tiles.COVERED)]),
           "pack tile 3/3/5 did not come back")
    shape = next(e.data for e in entries if e.kind == tiles.COMPACT)
    pts, rings, polys = coords.decode(shape)
    want = np.concatenate([np.vstack([r, r[:1]]) if not np.array_equal(r[0], r[-1]) else r
                           for poly in sample_shape() for r in poly])
    expect(pts.shape == want.shape and bool(np.allclose(pts, want, atol=1e-7)),
           "compact coordinates did not come back to a centimetre")
    expect(rings.dtype == np.intp and polys.dtype == np.intp, "offsets are not NumPy's index type")
    expect(list(polys) == [0, 2, 3], "the polygons' rings did not come back")
    expect(p.tile(5, 0, 0) == [], "a missing pack tile is not empty")
    expect(len(p.drawing_tile(0, 1, 1)) == 1, "the drawing tile did not come back")
    expect(p.check() == [], "an undamaged pack reported damage")
    expect(p.reads > 0, "the reads were not counted")

    # One damaged byte in one pack tile: that record is reported, the rest still read.
    offset = p.directory["tile/4/7/11"][0]
    damaged = bytearray(data)
    damaged[offset + 3] ^= 0xFF
    q = pack.Pack(MemorySource(bytes(damaged), "damaged.pack"), app_version=app_version)
    expect(q.check() == ["tile/4/7/11"], "the damaged pack tile was not the one reported")
    try:
        q.tile(4, 7, 11)
        problems.append("reading the damaged pack tile did not report it")
    except pack.DamagedRecord as exc:
        expect(exc.record == "tile/4/7/11", "the wrong record was reported damaged")
    expect(len(q.tile(3, 3, 5)) == 2, "an undamaged pack tile could not be read beside a damaged one")

    # A pack for later application versions is refused.
    later = build({**MANIFEST, "app_versions": {"from": "99.0"}})
    try:
        pack.Pack(MemorySource(later, "later.pack"), app_version=app_version)
        problems.append("a pack for a later application version was opened")
    except pack.AppTooOld:
        pass
    return problems
