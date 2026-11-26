"""The small-islands stage: every island under 1 km2 (P4-T1c, design docs/plan/p4-t1-design.md 3.6; DAT-1, DAT-3,
LOC-3, DP87).

The join makes the named islands and the unnamed ones of 1 km2 or more. small-islands adds every other landmass in
the coverage that holds no island area: "Unnamed island", with an id from its point rounded to 5 decimals, so it is
the same each build (DMT-1), or the name of an islet OpenStreetMap has only as a point. Made-up shapes test the rules;
the Lymington cooked sample's land, with made-up islets in the Solent, tests the stage; the regional test pack tests
that land cut by the coverage is not taken for an island.

The Lymington cooked sample itself holds no islet: the OSM land polygons there are the mainland and Walhampton, which
the box cuts. Its salt marsh is not land in the land polygons. So the islets here are made up, in its sea.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import shapely

from mapdata.pipeline import features
from mapdata.stages import small_islands

LYMINGTON = shapely.box(-1.56006, 50.73486, -1.51611, 50.75684)
WALHAMPTON = (-1.51848, 50.75525)    # the sample's small part of the mainland, cut by the box


def _islet(lon, lat, d=0.0004):
    return shapely.box(lon - d / 2, lat - d / 2, lon + d / 2, lat + d / 2)


# The rules, on made-up shapes ----------------------------------------------------------------------------------

COVER = shapely.box(0, 50, 0.1, 50.1)
MAINLAND = shapely.box(0, 50, 0.05, 50.1)            # cut by the coverage's west edge, and large
ISLETS = [_islet(0.07, 50.02), _islet(0.08, 50.05)]
NAMED = _islet(0.09, 50.08)                            # holds an island area of the join


def _find(land=None, islands=None, points=()):
    return small_islands.find_islands(land if land is not None else [MAINLAND, *ISLETS, NAMED],
                                      islands if islands is not None else [NAMED.buffer(-0.0001)],
                                      COVER, list(points), "Unnamed island")


def test_islets_become_unnamed_islands_with_ids_from_their_points():
    out, counts = _find()
    assert [r["name"] for r, _g in out] == ["Unnamed island", "Unnamed island"]
    for (r, g), islet in zip(sorted(out, key=lambda rg: rg[1].bounds), ISLETS):
        p = shapely.point_on_surface(islet)
        assert r["id"] == f"island:unnamed:{p.y:.5f}:{p.x:.5f}"
        assert r["layer"] == "islands" and r["type"] == "unnamed island"
        assert shapely.equals(g, islet)
    assert counts["unnamed"] == 2 and counts["holds_island"] == 1


def test_the_ids_are_the_same_when_found_again():
    first, _ = _find()
    again, _ = _find(land=[NAMED, *reversed(ISLETS), MAINLAND])
    assert sorted(r["id"] for r, _g in first) == sorted(r["id"] for r, _g in again)


def test_land_cut_by_the_coverage_is_not_an_island():
    cut = shapely.box(0.099, 50.05, 0.1, 50.051)     # small, on the coverage's east edge
    out, counts = _find(land=[cut], islands=[])
    assert out == [] and counts["cut"] == 1


def test_a_landmass_of_1_km2_or_more_is_left_to_the_join():
    big = shapely.box(0.06, 50.06, 0.08, 50.08)        # about 3 km2
    out, counts = _find(land=[big], islands=[])
    assert out == [] and counts["large"] == 1


def test_touching_parts_are_one_landmass():
    """An islet split by a border is one island, as in the join."""
    a, b = shapely.box(0.07, 50.02, 0.0702, 50.0204), shapely.box(0.0702, 50.02, 0.0704, 50.0204)
    out, _counts = _find(land=[a, b], islands=[])
    assert len(out) == 1 and shapely.equals(out[0][1], shapely.union_all([a, b]))


def test_an_islet_with_an_osm_point_takes_its_name():
    point = {"id": "osm:n42", "name": "Gull Island", "local_name": "Gull Island", "kind": "island point",
             "type": "islet", "wikidata": "Q1", "point": [0.0801, 50.0501]}
    out, counts = _find(points=[point])
    named = [r for r, _g in out if r["id"] == "osm:n42"]
    assert named == [{"id": "osm:n42", "layer": "islands", "name": "Gull Island", "local_name": "Gull Island",
                      "type": "islet", "wikidata": "Q1"}]
    assert counts["point"] == 1 and counts["unnamed"] == 1


def test_a_point_the_join_used_is_not_used_again():
    point = {"id": "osm:n42", "name": "Gull Island", "kind": "island point", "type": "islet",
             "point": [0.0801, 50.0501]}
    out, _counts = small_islands.find_islands([*ISLETS], [], COVER, [point], "Unnamed island",
                                              used={"osm:n42"})
    assert all(r["name"] == "Unnamed island" for r, _g in out)


def test_the_words_come_from_the_templates_and_are_in_the_fingerprint():
    assert small_islands.unnamed_name() == "Unnamed island"
    assert small_islands.fingerprint_extra({"stage": "small-islands"}) == {"unnamed_island": "Unnamed island"}


# The stage, on the Lymington sample's land with made-up islets --------------------------------------------------

def _stage_folder(test_region_pack, kind):
    work = Path(test_region_pack).parents[2] / "working" / "test-region"
    return next(f for f in sorted(work.iterdir()) if f.name.split("-", 1)[1].startswith(f"{kind}-"))


SEA_ISLETS = [_islet(-1.5180, 50.7400), _islet(-1.5200, 50.7365)]


def _run(previous: Path, coverage: Path, folder: Path, earlier: dict | None = None):
    folder.mkdir(parents=True)
    lines = []
    ctx = SimpleNamespace(settings={"stage": "small-islands"}, previous=previous, folder=folder,
                          earlier={"coverage": coverage, **(earlier or {})}, claim=lambda p: p,
                          progress=SimpleNamespace(line=lines.append, log=lines.append))
    small_islands.run(ctx)
    return features.load(folder)


@pytest.fixture(scope="module")
def with_islets(test_region_pack, tmp_path_factory):
    """The stage before small-islands in the test region, with two islets added to the United Kingdom's land in the
    Lymington box's sea."""
    before = _stage_folder(test_region_pack, "local-areas")
    records, geoms = features.load(before)
    uk = next(i for i, r in enumerate(records) if r["layer"] == "countries")
    for islet in SEA_ISLETS:
        assert not geoms[uk].intersects(islet), "a made-up islet must be in the sample's sea"
    geoms[uk] = shapely.union_all([geoms[uk], *SEA_ISLETS])
    folder = tmp_path_factory.mktemp("before")
    features.save(folder, records, geoms)
    return folder, _stage_folder(test_region_pack, "coverage")


def test_the_lymington_samples_islets_become_unnamed_islands_with_the_same_ids_each_build(with_islets, tmp_path):
    previous, coverage = with_islets
    first = _run(previous, coverage, tmp_path / "first")
    again = _run(previous, coverage, tmp_path / "again")
    added = [r for r in first[0] if r["layer"] == "islands"]
    assert len(added) == 2 and all(r["name"] == "Unnamed island" for r in added)
    assert [r["id"] for r in added] == [r["id"] for r in again[0] if r["layer"] == "islands"]
    ids = {f"island:unnamed:{shapely.point_on_surface(i).y:.5f}:{shapely.point_on_surface(i).x:.5f}"
           for i in SEA_ISLETS}
    assert {r["id"] for r in added} == ids
    assert first[0][:len(first[0]) - 2] == features.load(previous)[0]    # the stage before's features kept, first
    report = json.loads((tmp_path / "first" / small_islands.REPORT).read_text(encoding="utf-8"))
    assert report["counts"]["unnamed"] == 2


def test_an_islet_named_by_an_osm_point_of_osm_areas(with_islets, tmp_path):
    previous, coverage = with_islets
    areas = tmp_path / "osm-areas"
    areas.mkdir()
    p = shapely.point_on_surface(SEA_ISLETS[0])
    point = {"id": "osm:n7", "name": "Made-up Islet", "local_name": "Made-up Islet", "kind": "island point",
             "type": "islet", "level": None, "country": None, "point": [p.x, p.y]}
    features.save(areas, [point], [shapely.Polygon()])
    records, _g = _run(previous, coverage, tmp_path / "out", {"osm-areas": areas})
    names = sorted(r["name"] for r in records if r["layer"] == "islands")
    assert names == ["Made-up Islet", "Unnamed island"]


def test_the_regional_test_pack_has_no_island_made_of_land_the_coverage_cuts(test_region_pack):
    records, geoms = features.load(_stage_folder(test_region_pack, "small-islands"))
    at = shapely.Point(*WALHAMPTON)
    assert not [r for r, g in zip(records, geoms) if r["layer"] == "islands" and g.intersects(at)]
    report = json.loads((_stage_folder(test_region_pack, "small-islands") / small_islands.REPORT)
                        .read_text(encoding="utf-8"))
    assert report["counts"]["cut"] >= 1
