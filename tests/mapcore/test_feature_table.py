"""The compact feature table, pack format 5 (P4-T3f, DP225; NFR-3, NFR-4, DMT-1, PLT-4).

A format 5 pack stores each feature's identifier, layer, width and bounding box as a few records, which the store
reads in place of every feature record. Feature records are then read a group at a time, the last GROUPS_KEPT
kept. A format 4 pack has no table and is read as before. Both give the same answers.
"""
import io
import json
import struct
import zlib

import numpy as np
import pytest

from mapcore.packs import pack, selfcheck, table
from mapcore.packs.source import MemorySource
from mapcore.store import Store

WINCHESTER = (51.0632, -1.3080)
POINTS = [WINCHESTER, (51.2, -1.4), (51.2, 1.2), (49.75, 6.1), (48.85, 2.35), (52.5, 13.4), (-17.0, 179.6),
          (50.72, -1.88), (0.0, 0.0), (51.5, -0.12)]


def as_format_4(path, out):
    """A copy of a format 5 pack as format 4 would have written it: the same records without the feature table,
    and the format number 4 in the header and the manifest."""
    with pack.Pack(path, check_app=False) as p:
        records = {k: p.get(k) for k in p.keys() if k not in table.KEYS}
    manifest = json.loads(records["manifest"])
    manifest["format"] = 4
    records["manifest"] = pack._json(manifest)
    buf = io.BytesIO()
    buf.write(bytes(pack.HEADER_SIZE))
    directory = {}
    for key in sorted(records):
        stored = zlib.compress(records[key], 9)
        directory[key] = [buf.tell(), len(stored), pack.check_number(stored)]
        buf.write(stored)
    listing = zlib.compress(pack._json({"records": directory}), 9)
    offset = buf.tell()
    buf.write(listing)
    head = pack._HEADER.pack(pack.MAGIC, 4, 0, 0, offset, len(listing), pack.check_number(listing), 0)
    head = head[:-4] + struct.pack("<I", pack.check_number(head[:-4]))
    data = bytearray(buf.getvalue())
    data[:pack.HEADER_SIZE] = head
    out.write_bytes(bytes(data))
    return out


@pytest.fixture(scope="module")
def old_packs(test_pack, test_region_pack, tmp_path_factory):
    folder = tmp_path_factory.mktemp("format4")
    return (as_format_4(test_pack, folder / "test.pack"), as_format_4(test_region_pack, folder / "test-region.pack"))


def store_of(*paths):
    return Store([pack.Pack(p, check_app=False) for p in paths])


# The writer ---------------------------------------------------------------------------------------------------

def test_the_selfcheck_pack_has_the_table_and_it_matches_the_records():
    p = pack.Pack(MemorySource(selfcheck.build(), "t.pack"), check_app=False)
    assert p.format == 5 and p.has_table
    t = p.table()
    assert t.count == p.feature_count == 600
    assert set(t.layer_names) == {"countries", "regions"}
    for n in range(p.feature_count):
        rec = p.feature(n)
        assert t.ids[n] == rec["id"]
        assert t.boxes[n].tolist() == rec["bbox"]
        assert t.widths[n] == rec["width_km"]
        assert t.layer_of(n) == rec["layer"]
    assert t.boxes.dtype == np.float64 and t.ids.ends.dtype == np.intp


@pytest.mark.parametrize("boxes, how", [
    ([[-1.5, 50.0, 1.25, 51.5], [179.5, -17.0, -179.5, -16.0], [-180.0, -90.0, 180.0, 90.0], [0.1234567, 1.0, 0.1234567, 1.0]],
     "i4e7"),
    ([[-1.5, 50.0, 1.25, 51.5], [0.123456789, 1.0, 0.2, 2.0]], "f8"),
])
def test_boxes_come_back_exactly_whether_stored_as_whole_numbers_or_not(boxes, how):
    boxes = np.array(boxes, dtype=np.float64)
    stored_as, data = table._boxes_record(boxes)
    assert stored_as == how
    assert np.array_equal(table._read_boxes(stored_as, data, len(boxes)), boxes)


@pytest.mark.parametrize("widths, how", [([0.0, 1.5, 12345.678, np.inf], "i4e3"), ([0.0001, np.inf], "f8")])
def test_widths_come_back_exactly_whether_stored_as_whole_numbers_or_not(widths, how):
    widths = np.array(widths, dtype=np.float64)
    stored_as, data = table._widths_record(widths)
    assert stored_as == how
    assert np.array_equal(table._read_widths(stored_as, data), widths)


def test_the_same_pack_written_twice_is_the_same_bytes():
    assert selfcheck.build() == selfcheck.build()


def test_a_format_4_pack_can_still_be_written_for_tests_and_has_no_table():
    out = io.BytesIO()
    w = pack.PackWriter(out, format=4)
    w.add_features(selfcheck.sample_features())
    w.finish(selfcheck.MANIFEST, selfcheck.ATTRIBUTION, selfcheck.LAYERS)
    p = pack.Pack(MemorySource(out.getvalue(), "old.pack"), check_app=False)
    assert p.format == 4 and p.manifest["format"] == 4 and not p.has_table and p.table() is None
    assert p.feature_number("test:regions:7") is not None
    with pytest.raises(pack.PackWriteError):
        pack.PackWriter(io.BytesIO(), format=3)


def test_an_identifier_is_found_from_the_table_with_no_feature_record_read():
    p = pack.Pack(MemorySource(selfcheck.build(), "t.pack"), check_app=False)
    p.table()
    reads = p.reads
    for f in selfcheck.sample_features():
        n = p.feature_number(f["id"])
        assert n is not None
    assert p.feature_number("test:nowhere") is None and p.feature_number("") is None
    assert p.reads == reads and p.groups_kept == 0
    assert {p.feature(p.feature_number(f["id"]))["id"] for f in selfcheck.sample_features()} == \
        {f["id"] for f in selfcheck.sample_features()}


def test_the_group_and_record_caches_stay_within_their_limits(monkeypatch):
    monkeypatch.setattr(pack, "GROUPS_KEPT", 2)
    monkeypatch.setattr(pack, "FEATURES_KEPT", 10)
    p = pack.Pack(MemorySource(selfcheck.build(), "t.pack"), check_app=False)
    assert len(p.group_starts) == 3
    for n in range(p.feature_count):
        p.feature(n)
        assert p.groups_kept <= 2 and p.records_kept <= 10
    reads = p.reads
    p.feature(p.feature_count - 1)   # the last record is kept: no read
    assert p.reads == reads
    p.feature(0)   # the first record was let go: read again
    assert p.reads == reads + 1
    p.feature(0)   # now kept
    assert p.reads == reads + 1
    for g in range(3):   # groups read whole, as a scan or Nearby's relationships do, are kept within the limit
        p._group(g)
        assert p.groups_kept <= 2


def test_with_a_table_a_feature_record_is_read_alone_and_is_the_groups_own(test_pack, test_region_pack):
    """P4-T3g: a view's features are in many feature groups, so each is read without the rest of its group."""
    for source in (selfcheck.build(), test_pack.read_bytes(), test_region_pack.read_bytes()):
        p = pack.Pack(MemorySource(source, "t.pack"), check_app=False)
        assert p.has_table and p.table() is not None
        whole = [r for g in range(len(p.group_starts)) for r in json.loads(p.get(f"features/{g}"))]
        reads = p.reads
        for n in range(p.feature_count):
            got = p.feature(n)
            assert got == whole[n] and json.dumps(got) == json.dumps(whole[n])
        assert p.groups_kept == 0 and p.reads == reads + p.feature_count


def test_a_record_not_found_alone_is_read_with_its_group():
    p = pack.Pack(MemorySource(selfcheck.build(), "t.pack"), check_app=False)
    p.table()
    p._table.ids.blob = b"x" * len(p._table.ids.blob)   # identifiers no record has
    assert p._one_record(0, 0) is None
    record = p.feature(0)
    assert record == json.loads(p.get("features/0"))[0] and p.groups_kept == 1


def test_the_group_limit_holds_for_an_old_pack_looked_up_by_identifier(monkeypatch):
    monkeypatch.setattr(pack, "GROUPS_KEPT", 1)
    out = io.BytesIO()
    w = pack.PackWriter(out, format=4)
    w.add_features(selfcheck.sample_features())
    w.finish(selfcheck.MANIFEST, selfcheck.ATTRIBUTION, selfcheck.LAYERS)
    p = pack.Pack(MemorySource(out.getvalue(), "old.pack"), check_app=False)
    for f in selfcheck.sample_features():
        assert p.feature_by_id(f["id"]) == f
        assert p.groups_kept <= 1 and len(p._group_ids) <= 1


def test_a_damaged_table_is_noted_and_the_records_are_read_instead():
    data = bytearray(selfcheck.build())
    p = pack.Pack(MemorySource(bytes(data), "t.pack"), check_app=False)
    offset = p.directory["table/boxes"][0]
    data[offset + 2] ^= 0xFF
    p = pack.Pack(MemorySource(bytes(data), "damaged.pack"), check_app=False)
    store = Store([p])
    assert p.table() is None and p.table_problem.record == "table/boxes"
    numbers, boxes = store._indexes[0].boxes
    assert len(numbers) == 600
    assert p.table_problem.message in store.problems
    assert store.feature("test:regions:7").id == "test:regions:7"


def test_a_table_given_twice_in_a_group_out_of_order_is_refused():
    w = pack.PackWriter(io.BytesIO())
    feats = selfcheck.sample_features()[:2]
    with pytest.raises(pack.PackWriteError, match="out of order"):
        w.add_feature_groups([0], [(0, list(reversed(feats)))], {feats[1]["id"]: 0, feats[0]["id"]: 1})


# The store gives the same answers from the table as from the records -----------------------------------------

def _answers(store):
    out = {"at": [[a.id for a in store.at(lat, lon)] for lat, lon in POINTS],
           "nearby": [[(n.area.id, round(n.distance_m, 3)) for n in store.nearby(lat, lon, 50_000, limit=30)]
                      for lat, lon in POINTS[:4]]}
    index = store._indexes[-1]
    numbers, boxes = index.boxes
    widths, layers = index.sizes
    out["table"] = (numbers.tolist(), boxes.tolist(), widths.tolist(), layers.tolist(), index.ids[numbers].tolist())
    return out


def test_the_store_answers_the_same_from_a_new_pack_and_an_old_one(test_pack, old_packs):
    new, old = store_of(test_pack), store_of(old_packs[0])
    try:
        assert new._indexes[0].pack.has_table and not old._indexes[0].pack.has_table
        assert _answers(new) == _answers(old)
        assert new.layer_of("osm:r172799") == old.layer_of("osm:r172799") is not None
        assert new.layer_of("nowhere:1") is None and old.layer_of("nowhere:1") is None
        for i in (0, 5, len(new._indexes[0].boxes[0]) - 1):
            assert new._indexes[0].layer_of_number(i) == old._indexes[0].layer_of_number(i)
        assert new.search("Winchester") == old.search("Winchester")
    finally:
        new.close()
        old.close()


def test_the_view_is_the_same_from_a_new_pack_and_an_old_one(test_pack, old_packs):
    from mapcore.session import MapSession

    got = []
    for path in (test_pack, old_packs[0]):
        s = MapSession(packs=[path], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000})
        s.start()
        try:
            got.append([sorted(s.visible.features(lat, lon, zoom)) for lat, lon in POINTS
                        for zoom in (10_000, 300_000, 5_000_000)])
        finally:
            s.store.close()
    assert got[0] == got[1]


def test_two_packs_merge_the_same_from_new_packs_and_old_ones(test_pack, test_region_pack, old_packs):
    new, old = store_of(test_pack, test_region_pack), store_of(*old_packs)
    try:
        assert _answers(new) == _answers(old)
        regional = next(new._indexes[p] for p in range(len(new.packs)) if new.coverage(p) is not None)
        for alias, real in list(regional.aliases.items())[:20]:
            assert new.feature(alias).id == old.feature(alias).id == real
        for identifier in ("osm:r172799", "osm:r62149", "vliz:goas:north-atlantic-ocean"):
            a, b = new.feature(identifier), old.feature(identifier)
            assert a is not None and a.record == b.record
            assert new.relationships(identifier) == old.relationships(identifier)
        assert [(f.id, f.name) for f in new.search("Hampshire")] == [(f.id, f.name) for f in old.search("Hampshire")]
    finally:
        new.close()
        old.close()


def test_the_store_reads_no_feature_record_to_make_the_table(test_pack):
    store = store_of(test_pack)
    try:
        p = store.packs[0]
        store._indexes[0].boxes
        assert p.groups_kept == 0
        assert store.layer_of("osm:r172799") is not None and p.groups_kept == 0
    finally:
        store.close()


def _scenes(paths, steps=3):
    from mapcore.session import MapSession

    s = MapSession(packs=list(paths), saved_state={"lat": 51.06, "lon": -1.31, "zoom_m": 5000, "step_m": 500})
    s.start()
    out = []
    try:
        for i in range(steps):
            if i:
                s.run("move.east", held=True)
            scene = s.scene(900, 760)
            out.append({k: v for k, v in scene.items() if not k.endswith("_ms")})
    finally:
        s.store.close()
    return out


def _same(a, b):
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return isinstance(b, (list, tuple)) and len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray):
        return isinstance(b, np.ndarray) and a.dtype == b.dtype and np.array_equal(a, b)
    return a == b


def test_the_drawing_is_the_same_from_new_packs_and_old_ones(test_pack, test_region_pack, old_packs):
    """P4-T3g: from a pack with a table, a drawn feature's record is read only for its colour, intervals or name."""
    assert _same(_scenes([test_pack]), _scenes([old_packs[0]]))
    assert _same(_scenes([test_pack, test_region_pack]), _scenes(list(old_packs)))


def test_nearby_measures_only_the_boxes_it_may_reach(test_pack, monkeypatch):
    """P4-T3g: the same answers as when every box is measured and sorted."""
    from mapcore.store import store as store_mod

    store = store_of(test_pack)
    try:
        asked = [(lat, lon, r) for lat, lon in POINTS for r in (500.0, 20_000.0, 2_000_000.0)]
        got = [[(n.area.id, n.distance_m) for n in store.nearby(lat, lon, r, limit=15)] for lat, lon, r in asked]
        monkeypatch.setattr(store_mod.Store, "_rows_within",
                            staticmethod(lambda boxes, lat, radius_m: np.arange(len(boxes), dtype=np.intp)))
        every = [[(n.area.id, n.distance_m) for n in store.nearby(lat, lon, r, limit=15)] for lat, lon, r in asked]
        assert got == every and any(got)
    finally:
        store.close()
