"""The pipeline writes packs in format 2, and its lookup finds what is at a point (AD-5, DMT-1)."""
import shapely

from mapcore.packs import pack, tiles
from mapcore.packs.source import MemorySource
from mapdata.stages import lookup, pack_write

SOURCES = [{"name": "Test", "licence": "ODbL 1.0", "date": "2026-10-26"}]


def write(path, records, geoms, workers=1):
    return pack_write.write(path, {"name": "test", "sources": SOURCES}, records, geoms, workers, say=lambda s: None)


def big_and_small():
    big = shapely.box(-10, 40, 10, 60).difference(shapely.box(-1, 49, 1, 51))  # a hole
    small = shapely.box(-0.5, 49.5, 0.5, 50.5)                                 # inside the hole
    records = [{"id": "t:big", "name": "Big", "layer": "countries", "type": "country", "area_km2": 2.0},
               {"id": "t:small", "name": "Small", "local_name": "Klein", "layer": "regions", "type": "level 4",
                "parent": "t:big", "area_km2": 1.0}]
    return records, [big, small]


def test_pack_answers_what_is_here(tmp_path):
    records, geoms = big_and_small()
    stats = write(tmp_path / "t.pack", records, geoms)
    assert stats["entries"] > 0 and stats["tiles"] > 0
    with lookup.open_pack(tmp_path / "t.pack") as p:
        look = lookup.Lookup(p)
        assert [f["id"] for f in look.at(0, 50)] == ["t:small"]
        assert [f["id"] for f in look.at(5, 45)] == ["t:big"]
        assert look.at(-0.8, 50.8) == []        # in the hole, outside the small box
        assert look.at(30, 50) == []            # elsewhere
        assert p.manifest["coordinates"]["encoding"] == "compact"
        assert p.manifest["built"] == "2026-10-26"
        assert p.layers == [{"id": "countries", "name": "Countries"}, {"id": "regions", "name": "Regions"}]
        assert "© OpenStreetMap contributors" in p.attribution
        assert p.check() == []
    assert pack.verify_checksum(tmp_path / "t.pack")


def test_feature_records_gain_the_format_2_fields(tmp_path):
    records, geoms = big_and_small()
    write(tmp_path / "t.pack", records, geoms)
    with lookup.open_pack(tmp_path / "t.pack") as p:
        small = p.feature_by_id("t:small")
        big = p.feature_by_id("t:big")
    assert small["names"] == {"en": "Small", "local": "Klein"} and big["names"] == {"en": "Big"}
    assert small["rank"] == 4 and big["rank"] == 2
    assert small["parents"] == ["t:big"] and big["parents"] == []
    assert small["bbox"] == [-0.5, 49.5, 0.5, 50.5]
    assert 110 < small["width_km"] < 112  # one degree of latitude
    assert small["colour"] is None  # worked out from P1-T4
    assert shapely.Point(*small["point"]).within(geoms[1])
    assert shapely.Point(*big["point"]).within(geoms[0])
    assert small["name"] == "Small" and small["local_name"] == "Klein"  # kept for the S2 checks


def test_a_shape_across_the_180_degree_line_has_a_narrow_box(tmp_path):
    fiji = shapely.MultiPolygon([shapely.box(177, -19, 180, -16), shapely.box(-180, -19, -178, -16)])
    write(tmp_path / "t.pack", [{"id": "t:fiji", "name": "Fiji", "layer": "countries", "type": "country",
                                 "area_km2": 1.0}], [fiji])
    with lookup.open_pack(tmp_path / "t.pack") as p:
        assert p.feature_by_id("t:fiji")["bbox"] == [177.0, -19.0, -178.0, -16.0]


def test_pack_reads_through_a_byte_source(tmp_path):
    records, geoms = big_and_small()
    write(tmp_path / "t.pack", records, geoms)
    data = (tmp_path / "t.pack").read_bytes()
    with lookup.open_pack(tmp_path / "t.pack") as from_file:
        from_memory = pack.Pack(MemorySource(data), check_app=False)
        for lon, lat in ((0, 50), (5, 45), (-0.8, 50.8), (30, 50)):
            assert lookup.at(from_memory, lon, lat) == lookup.at(from_file, lon, lat)
        assert from_memory.reads == from_file.reads


def test_whole_tiles_are_stored_as_covered(tmp_path):
    # A detailed edge (like a coastline) makes the writer cut finer pack
    # tiles, and the pack tiles wholly inside are then stored as covered notes.
    big = shapely.segmentize(shapely.box(-40, 10, 40, 80), 0.01)
    write(tmp_path / "covered.pack", [{"id": "t:big", "name": "Big", "layer": "countries", "type": "country",
                                       "area_km2": 1.0}], [big])
    with lookup.open_pack(tmp_path / "covered.pack") as p:
        kinds = {e.kind for key in p.keys() if key.startswith("tile/")
                 for e in p.tile(*map(int, key.split("/")[1:]))}
        assert tiles.COVERED in kinds
        assert [f["id"] for f in lookup.at(p, 0, 45)] == ["t:big"]


def test_the_same_pack_with_one_worker_or_two(tmp_path):
    # DMT-1: the bytes do not depend on how the work was shared out.
    records, geoms = big_and_small()
    geoms[0] = shapely.segmentize(geoms[0], 0.005)
    write(tmp_path / "one.pack", records, geoms, workers=1)
    write(tmp_path / "two.pack", records, geoms, workers=2)
    assert (tmp_path / "one.pack").read_bytes() == (tmp_path / "two.pack").read_bytes()


def test_a_cache_gives_the_same_answers(tmp_path):
    records, geoms = big_and_small()
    write(tmp_path / "t.pack", records, geoms)
    with lookup.open_pack(tmp_path / "t.pack") as p:
        plain, cached = lookup.Lookup(p), lookup.Lookup(p, cache=True)
        for lon, lat in ((0, 50), (5, 45), (0.1, 50.1), (5, 45)):
            assert cached.at(lon, lat) == plain.at(lon, lat)
