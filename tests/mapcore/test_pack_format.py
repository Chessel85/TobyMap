"""Pack format 3 (and 2): writer, reader, check numbers, checksum and version checks (P1-T2).

Requirements: PCK-5, DAT-9, NFR-4 (detection), DMT-1, and the format for PCK-1.
"""
import io

import numpy as np
import pytest

from mapcore.packs import coords, pack, selfcheck, tiles
from mapcore.packs.source import MemorySource


class CountingSource(MemorySource):
    """Only size and read: what the browser's private storage offers."""

    def __init__(self, data):
        super().__init__(data, "counted.pack")
        self.calls = 0

    def read(self, offset, length):
        self.calls += 1
        return super().read(offset, length)


@pytest.fixture(scope="module")
def data():
    return selfcheck.build()


def open_bytes(data, name="test.pack", app_version="0.1.0"):
    return pack.Pack(MemorySource(data, name), app_version=app_version)


def test_selfcheck_finds_no_problems():
    assert selfcheck.run() == []


def test_every_kind_of_record_comes_back(data):
    p = open_bytes(data)
    assert p.manifest["format"] == 4
    assert p.manifest["name"] == "selfcheck"
    assert p.manifest["sources"] == selfcheck.MANIFEST["sources"]
    assert p.manifest["coordinates"] == {"encoding": "compact", "scale": 10_000_000}
    assert p.manifest["layers"] == ["countries", "regions"]
    assert p.manifest["tile_levels"] == [3, 4]
    assert p.manifest["drawing_levels"] == selfcheck.MANIFEST["drawing_levels"]
    assert p.attribution == selfcheck.ATTRIBUTION
    assert p.licence == pack.ODBL_NOTICE
    assert p.layers == selfcheck.LAYERS
    for f in selfcheck.sample_features():
        assert p.feature_by_id(f["id"]) == f
    assert p.feature_by_id("test:nowhere") is None
    assert sorted(k for k in p.keys() if not k.startswith(("features/", "tile/", "draw/"))) == \
        ["attribution", "layers", "licence", "manifest"]


def test_feature_records_are_grouped_and_numbered(data):
    p = open_bytes(data)
    assert p.feature_count == 600
    assert p.manifest["features"]["groups"] == 3  # 600 records, about 256 to a group
    ids = [p.feature(n)["id"] for n in range(p.feature_count)]
    assert len(set(ids)) == 600
    for n in (0, 299, 599):
        assert p.feature_number(ids[n]) == n
    with pytest.raises(IndexError):
        p.feature(600)


def test_build_date_comes_from_the_sources_not_the_clock(data):
    # DMT-1: the latest of the sources' dates.
    assert open_bytes(data).manifest["built"] == "2026-11-01"


def test_same_input_gives_identical_bytes(data):
    assert selfcheck.build() == data


def test_one_damaged_byte_names_the_record_and_the_rest_still_reads(data):
    p = open_bytes(data)
    for key in ("tile/4/7/11", "features/1", "draw/0/1/1", "attribution"):
        offset, length, _check = p.directory[key]
        damaged = bytearray(data)
        damaged[offset + length // 2] ^= 0x01
        q = open_bytes(bytes(damaged))
        assert q.check() == [key]
        with pytest.raises(pack.DamagedRecord) as caught:
            q.get(key)
        assert caught.value.record == key
        assert caught.value.message == (
            "Part of test.pack is damaged, and TobyMap is carrying on without it. "
            f"Download the pack again. The damaged record is {key}.")
        assert len(q.tile(3, 3, 5)) == 2 or key == "tile/3/3/5"


@pytest.mark.parametrize("where", ["header", "directory", "manifest"])
def test_damage_to_what_holds_the_pack_together_refuses_it(data, where):
    p = open_bytes(data)
    if where == "header":
        offset = 20
    elif where == "directory":
        offset = len(data) - 3
    else:
        offset = p.directory["manifest"][0] + 2
    damaged = bytearray(data)
    damaged[offset] ^= 0x10
    with pytest.raises(pack.DamagedPack) as caught:
        open_bytes(bytes(damaged))
    assert caught.value.message == (
        f"test.pack is damaged, so it was not opened. Download it again. The damage is in its {where}.")


def test_a_cut_short_pack_is_refused(data):
    with pytest.raises(pack.PackError):
        open_bytes(data[:len(data) // 2])


def test_a_pack_for_a_later_application_is_refused_with_the_approved_message():
    later = selfcheck.build({**selfcheck.MANIFEST, "app_versions": {"from": "0.2.0"}})
    with pytest.raises(pack.AppTooOld) as caught:
        open_bytes(later, "world.pack", app_version="0.1.4")
    assert caught.value.message == ("world.pack needs TobyMap 0.2.0 or later, and this is TobyMap 0.1.4, "
                                    "so it was not opened. Update TobyMap to use it.")
    assert open_bytes(later, app_version="0.2").manifest["name"] == "selfcheck"


def test_a_pack_for_earlier_applications_only_is_refused():
    old = selfcheck.build({**selfcheck.MANIFEST, "app_versions": {"from": "0.0.1", "before": "0.1.0"}})
    assert open_bytes(old, app_version="0.0.9").manifest["name"] == "selfcheck"
    with pytest.raises(pack.AppTooNew) as caught:
        open_bytes(old, "old.pack", app_version="0.1.0")
    assert caught.value.message == ("old.pack was made for versions of TobyMap before 0.1.0, and this is "
                                    "TobyMap 0.1.0, so it was not opened. Download the current pack instead.")


def test_an_unknown_application_version_is_not_checked():
    later = selfcheck.build({**selfcheck.MANIFEST, "app_versions": {"from": "99.0"}})
    assert open_bytes(later, app_version="unknown").manifest["name"] == "selfcheck"
    assert pack.Pack(MemorySource(later), check_app=False).manifest["name"] == "selfcheck"


def test_this_application_version_is_used_by_default(data):
    assert pack.Pack(MemorySource(data)).manifest["name"] == "selfcheck"  # from 0.0.1, no end


def test_a_newer_format_is_refused(data):
    newer = bytearray(data)
    newer[8:10] = (pack.FORMAT + 1).to_bytes(2, "little")
    with pytest.raises(pack.NewerFormat) as caught:
        open_bytes(bytes(newer), "future.pack")
    assert caught.value.message == ("future.pack needs a newer version of TobyMap, so it was not opened. "
                                    "Update TobyMap to use it.")


def test_a_format_2_pack_is_still_read(data):
    """Format 3 only adds line and point tile entries, so a pack built before P2-T10a,
    such as the Phase 1 world pack, is read as it is."""
    older = bytearray(data)
    older[8:10] = (2).to_bytes(2, "little")
    older[36:40] = pack.check_number(bytes(older[:36])).to_bytes(4, "little")
    p = open_bytes(bytes(older), "phase1.pack")
    assert p.format == 2 and p.manifest["name"] == "selfcheck"
    assert open_bytes(data).format == 4


def test_a_format_3_pack_is_still_read(data):
    """Format 4 only adds facts to feature records (P3-T2b), so the world pack of P3-T1 is read as it is."""
    older = bytearray(data)
    older[8:10] = (3).to_bytes(2, "little")
    older[36:40] = pack.check_number(bytes(older[:36])).to_bytes(4, "little")
    p = open_bytes(bytes(older), "p3t1.pack")
    assert p.format == 3 and p.manifest["name"] == "selfcheck"


def test_something_else_is_not_a_pack():
    with pytest.raises(pack.NotAPack) as caught:
        open_bytes(b"PK\x03\x04" + bytes(100), "holiday.zip")
    assert caught.value.message == "holiday.zip is not a TobyMap pack, so it was not opened."
    with pytest.raises(pack.NotAPack):
        open_bytes(b"", "empty.pack")


def test_the_spike_format_is_not_read(data):
    # Format 1 was spike S2's pack. It is dropped, so such a file is not a TobyMap pack.
    spike = bytearray(data)
    spike[8:10] = (1).to_bytes(2, "little")
    with pytest.raises(pack.NotAPack) as caught:
        open_bytes(bytes(spike), "s2.pack")
    assert caught.value.message == "s2.pack is not a TobyMap pack, so it was not opened."


def test_reading_uses_only_the_byte_source(data):
    source = CountingSource(data)
    p = pack.Pack(source, app_version="0.1.0")
    opened = source.calls
    assert opened == 4  # header, directory, manifest, layers
    p.tile(3, 3, 5)
    p.feature(0)
    p.feature(1)  # same group: no second read
    assert source.calls == opened + 2 == p.reads + 2


def test_written_to_a_file_with_its_checksum_beside_it(tmp_path, data):
    path = tmp_path / "world.pack"
    writer = pack.PackWriter(path)
    numbers = writer.add_features(selfcheck.sample_features())
    shape = coords.encode(selfcheck.sample_shape())
    writer.add_tile(3, 3, 5, [(numbers["test:regions:7"], tiles.COMPACT, shape),
                              (numbers["test:countries:7"], tiles.COVERED, b"")])
    writer.add_tile(4, 7, 11, [(numbers["test:countries:1"], tiles.COMPACT, shape)])
    writer.add_drawing_tile(0, 1, 1, [(numbers["test:countries:7"], tiles.COMPACT, shape)])
    checksum = writer.finish(selfcheck.MANIFEST, selfcheck.ATTRIBUTION, selfcheck.LAYERS)
    assert path.read_bytes() == data  # the same bytes as written to memory
    assert pack.checksum_path(path).read_text(encoding="ascii") == f"{checksum} *world.pack\n"
    assert pack.verify_checksum(path)
    pack.require_checksum(path)
    with pack.Pack(path, app_version="0.1.0") as p:
        assert p.name == "world.pack" and p.check() == []
    damaged = bytearray(data)
    damaged[100] ^= 1
    path.write_bytes(bytes(damaged))
    assert not pack.verify_checksum(path)
    with pytest.raises(pack.ChecksumWrong) as caught:
        pack.require_checksum(path)
    assert caught.value.message == ("world.pack does not match its checksum, so it may be damaged or "
                                    "incomplete. Download it again.")


# The writer refuses what the format does not allow --------------------------------

def writer_with_features():
    w = pack.PackWriter(io.BytesIO())
    return w, w.add_features(selfcheck.sample_features()[:3])


def square(points):
    angles = np.linspace(0, 2 * np.pi, points, endpoint=False)
    return coords.encode([[np.column_stack([np.cos(angles), np.sin(angles)])]])


def test_tile_entries_over_the_limits_are_refused():
    w, numbers = writer_with_features()
    n = numbers["test:countries:0"]
    w.add_tile(5, 1, 1, [(n, tiles.COMPACT, square(4000))])
    with pytest.raises(pack.PackWriteError, match="4000"):
        w.add_tile(5, 1, 2, [(n, tiles.COMPACT, square(4001))])
    w.add_tile(18, 1, 2, [(n, tiles.COMPACT, square(4001))])  # nothing smaller to cut into
    with pytest.raises(pack.PackWriteError, match="20000"):
        w.add_tile(5, 1, 3, [(i, tiles.COMPACT, square(3500)) for i in range(3)] * 2)
    w.add_drawing_tile(0, 0, 0, [(n, tiles.COMPACT, square(30000))])  # drawing tiles have no limit


@pytest.mark.parametrize("call, words", [
    (lambda w, n: w.add_tile(3, 8, 0, [(n, tiles.COVERED, b"")]), "not in the grid"),
    (lambda w, n: w.add_tile(3, 0, 0, [(99, tiles.COVERED, b"")]), "feature number 99"),
    (lambda w, n: w.add_tile(3, 0, 0, [(n, 1, b"wkb")]), "kind 1"),
    (lambda w, n: w.add_tile(3, 0, 0, [(n, tiles.COVERED, b"x")]), "no bytes"),
    (lambda w, n: w.add_tile(3, 0, 0, []), "empty"),
    (lambda w, n: (w.add_tile(3, 0, 0, [(n, tiles.COVERED, b"")]),
                   w.add_tile(3, 0, 0, [(n, tiles.COVERED, b"")])), "twice"),
])
def test_tiles_the_format_does_not_allow_are_refused(call, words):
    w, numbers = writer_with_features()
    with pytest.raises(pack.PackWriteError, match=words):
        call(w, numbers["test:countries:0"])


def test_features_must_hold_the_phase_1_fields_once_each():
    w = pack.PackWriter(io.BytesIO())
    f = selfcheck.sample_features()[0]
    with pytest.raises(pack.PackWriteError, match="has no bbox"):
        w.add_features([{k: v for k, v in f.items() if k != "bbox"}])
    with pytest.raises(pack.PackWriteError, match="twice"):
        pack.PackWriter(io.BytesIO()).add_features([f, f])


@pytest.mark.parametrize("change, words", [
    ({"sources": []}, "at least one source"),
    ({"sources": [{"name": "OSM", "licence": "ODbL 1.0"}]}, "has no date"),
    ({"sources": [{"name": "OSM", "licence": "ODbL 1.0", "date": "26 October"}]}, "YYYY-MM-DD"),
    ({"app_versions": {"from": "soon"}}, "app_versions"),
    ({"built": "2026-11-03"}, "sets built itself"),
    ({"drawing_levels": []}, "drawing level 0"),
    ({"drawing_levels": [{"id": 0, "tile_level": 0}]}, "not in tile level 0"),
])
def test_manifests_the_format_does_not_allow_are_refused(change, words):
    w, numbers = writer_with_features()
    w.add_drawing_tile(0, 1, 1, [(numbers["test:countries:0"], tiles.COVERED, b"")])
    with pytest.raises(pack.PackWriteError, match=words):
        w.finish({**selfcheck.MANIFEST, **change}, selfcheck.ATTRIBUTION, selfcheck.LAYERS)


def test_attribution_and_layers_are_required():
    w, _numbers = writer_with_features()
    with pytest.raises(pack.PackWriteError, match="DAT-9"):
        w.finish(selfcheck.MANIFEST, "  ", selfcheck.LAYERS)
    w = pack.PackWriter(io.BytesIO())
    w.add_features(selfcheck.sample_features())
    with pytest.raises(pack.PackWriteError, match="not defined: regions"):
        w.finish(selfcheck.MANIFEST, selfcheck.ATTRIBUTION, selfcheck.LAYERS[:1])


def test_an_empty_pack_can_be_written_and_read():
    out = io.BytesIO()
    pack.PackWriter(out).finish(selfcheck.MANIFEST, selfcheck.ATTRIBUTION, selfcheck.LAYERS)
    p = open_bytes(out.getvalue())
    assert p.feature_count == 0 and p.tile_levels == [] and p.check() == []


# Compact coordinates and tile entries ---------------------------------------

def test_compact_coordinates_count_and_decode_without_shapely():
    blob = coords.encode(selfcheck.sample_shape())
    assert coords.point_count(blob) == 4 + 4 + 3  # closing points are not stored
    pts, rings, polys = coords.decode(blob)
    assert list(rings) == [0, 5, 10, 14] and list(polys) == [0, 2, 3]
    assert np.array_equal(pts[4], pts[0]) and np.array_equal(pts[13], pts[10])


def test_damaged_compact_coordinates_raise_rather_than_return_nonsense():
    blob = coords.encode(selfcheck.sample_shape())
    with pytest.raises(ValueError):
        coords.decode(blob[:-1] + b"\x80")
    with pytest.raises(ValueError):
        coords.decode(blob[:-6])


def test_tile_entries_round_trip_in_order():
    entries = [(5, tiles.COMPACT, b"\x01\x02"), (2, tiles.COVERED, b""), (5, tiles.COMPACT, b"\x00")]
    back = tiles.decode_entries(tiles.encode_entries(entries))
    assert back == sorted(tiles.TileEntry(*e) for e in entries)
    with pytest.raises(ValueError):
        tiles.decode_entries(tiles.encode_entries(entries) + b"\x00")


def test_a_manifest_missing_a_field_is_refused_not_crashed_on(data):
    # NFR-4: a pack written wrongly, with good check numbers, still gets a message.
    import json
    import zlib

    p = open_bytes(data)
    manifest = dict(p.manifest)
    del manifest["features"]
    stored = zlib.compress(json.dumps(manifest).encode(), 9)
    directory = {k: list(v) for k, v in p.directory.items()}
    directory["manifest"] = [len(data), len(stored), pack.check_number(stored)]
    packed_dir = zlib.compress(json.dumps({"records": directory}).encode(), 9)
    head = pack._HEADER.pack(pack.MAGIC, 2, 0, 0, len(data) + len(stored), len(packed_dir),
                             pack.check_number(packed_dir), 0)
    head = head[:-4] + pack.check_number(head[:-4]).to_bytes(4, "little")
    broken = head + data[pack.HEADER_SIZE:] + stored + packed_dir
    with pytest.raises(pack.DamagedPack) as caught:
        open_bytes(broken)
    assert caught.value.message.endswith("The damage is in its manifest.")
