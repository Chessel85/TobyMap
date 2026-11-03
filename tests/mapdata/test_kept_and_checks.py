"""P1-T16 part 1, the rest: countries kept on their own, areas held twice, inland water and the
wider overlap check, on small made-up shapes. No data folder, no network."""
import pytest
import shapely

from mapdata.stages import held_twice, inland_water, kept, overlaps
from mapdata.stages.boundaries import Area
from mapdata.stages.geodesy import area_km2
from mapdata.stages.s2_stage import border_check, country_print, disputed


# The wider overlap check ---------------------------------------------------

def test_overlaps_finds_the_same_land_one_inside_another_and_partly_overlapping():
    a = shapely.box(0, 0, 1, 1)
    same = shapely.box(0, 0, 1, 1)
    inside = shapely.box(0.2, 0.2, 0.4, 0.4)
    partly = shapely.box(0.9, 0.0, 1.5, 1.0)
    found = overlaps.find([a, same, inside, partly])
    kinds = {(o.first, o.second): o.kind for o in found}
    assert kinds[(0, 1)] == overlaps.SAME_LAND or kinds.get((1, 0)) == overlaps.SAME_LAND
    assert kinds[(2, 0)] == overlaps.INSIDE and kinds[(2, 1)] == overlaps.INSIDE
    assert kinds[(3, 0)] == overlaps.PARTLY
    assert found[0].shared_km2 >= found[-1].shared_km2


def test_overlaps_does_not_count_areas_that_only_touch():
    assert overlaps.find([shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1)]) == []


def test_overlaps_leaves_out_small_partial_overlaps_but_never_one_inside_another():
    big = shapely.box(0, 0, 1, 1)
    sliver = shapely.box(0.99999, 0, 2, 1)
    tiny_inside = shapely.box(0.5, 0.5, 0.50001, 0.50001)
    found = overlaps.find([big, sliver, tiny_inside], min_km2=1.0)
    assert [(o.kind, o.first) for o in found] == [(overlaps.INSIDE, 2)]


def test_same_land_finds_only_matching_pairs():
    a = shapely.box(30, 44, 31, 45)
    found = overlaps.same_land([a, shapely.box(30.5, 44, 31.5, 45), shapely.box(30, 44, 31, 45),
                                shapely.box(30.1, 44.1, 30.2, 44.2)])
    assert [(o.first, o.second) for o in found] in ([(0, 2)], [(2, 0)])


def test_overlap_report_wording():
    lines = []
    found = overlaps.find([shapely.box(0, 0, 1, 1), shapely.box(0.2, 0.2, 0.4, 0.4)])
    rows = overlaps.report("Test level 4", found, ["Big", "Small"], lines.append)
    assert rows[0]["kind"] == overlaps.INSIDE
    assert "1 with one wholly inside the other" in lines[0]
    assert lines[1].startswith("  Small,") and "is wholly inside Big" in lines[1]


# Areas held twice (DP104) ------------------------------------------------

SEVASTOPOL = shapely.box(33.4, 44.4, 33.9, 44.8)
RUSSIA = Area("osm:r60189", "Россия", 2, shapely.box(20, 40, 180, 80), tags={"ISO3166-1": "RU"})


def _area(identifier, code=None, geom=SEVASTOPOL, name="Севастополь"):
    tags = {"name:en": "Sevastopol"}
    if code:
        tags["ISO3166-2"] = code
    return Area(identifier, name, 4, geom, parent=RUSSIA.id, tags=tags)


def test_held_twice_keeps_the_copy_of_the_country_whose_outline_holds_it():
    other = _area("osm:r1", geom=shapely.box(36, 45, 37, 46), name="Краснодарский край")
    ua, ru = _area("osm:r1574364", "UA-40"), _area("osm:r3788485")
    areas, held = held_twice.resolve(RUSSIA, [other, ua, ru])
    assert [a.id for a in areas] == ["osm:r1", "osm:r3788485"]
    assert len(held) == 1 and held[0].dropped.id == "osm:r1574364"
    kept_copy = areas[1]
    assert kept_copy.tags["disputed"] == "yes"
    assert kept_copy.tags["also_held_as"] == {"id": "osm:r1574364", "name": "Севастополь", "name_en": "Sevastopol",
                                              "country_code": "UA"}
    assert "no ISO 3166-2 code" in held[0].decided_by and "UA-40" in held[0].decided_by


def test_held_twice_prefers_the_countrys_own_code():
    areas, held = held_twice.resolve(RUSSIA, [_area("osm:r5"), _area("osm:r9", "RU-SEV")])
    assert [a.id for a in areas] == ["osm:r9"]
    assert held[0].decided_by == "its ISO 3166-2 code is the country's own"


def test_held_twice_keeps_the_lower_identifier_when_the_data_cannot_tell():
    areas, held = held_twice.resolve(RUSSIA, [_area("osm:r900"), _area("osm:r80")])
    assert [a.id for a in areas] == ["osm:r80"]
    assert "does not say" in held[0].decided_by


def test_held_twice_leaves_neighbours_alone():
    a, b = _area("osm:r1", geom=shapely.box(0, 0, 1, 1)), _area("osm:r2", geom=shapely.box(1, 0, 2, 1))
    areas, held = held_twice.resolve(RUSSIA, [a, b])
    assert areas == [a, b] and held == [] and "disputed" not in a.tags


def test_held_twice_report_and_pack_record():
    areas, held = held_twice.resolve(RUSSIA, [_area("osm:r1574364", "UA-40"), _area("osm:r3788485")])
    lines = held_twice.report_lines(held, lambda a: a.tags["name:en"], lambda i: "Russia")
    assert lines[0].startswith("Russia: Sevastopol (osm:r3788485) and Sevastopol (osm:r1574364, with the code UA-40)")
    rec = disputed({"id": "osm:r3788485"}, areas[0])
    assert rec["disputed"] is True and rec["also_held_as"]["country_code"] == "UA"
    assert "disputed" not in disputed({"id": "x"}, _area("osm:r7"))


# Inland water in the area check -------------------------------------------

def test_water_on_land_is_counted_once_and_only_on_the_land():
    land = shapely.box(178.0, -18.0, 179.0, -17.0)
    lake = shapely.box(178.2, -17.8, 178.4, -17.6)
    same_lake_as_river = shapely.box(178.3, -17.8, 178.5, -17.6)   # overlaps the lake
    lagoon_at_sea = shapely.box(178.9, -17.5, 179.1, -17.4)          # half on the land
    got = inland_water.on_land(land, [lake, same_lake_as_river, lagoon_at_sea], cell=0.5)
    expected = area_km2(shapely.union_all([lake, same_lake_as_river, shapely.box(178.9, -17.5, 179.0, -17.4)]))
    assert got == pytest.approx(expected, rel=1e-6)
    assert inland_water.on_land(land, []) == 0.0


def test_area_check_takes_the_water_away_before_comparing():
    check = inland_water.AreaCheck("Kiribati", 1097.0, 237.0, 30.0, 811.0, None)
    assert check.without_water_km2 == 860.0
    assert check.diff_percent == pytest.approx(6.04, abs=0.01)
    assert not check.within and not check.passed
    assert "not explained" in check.lines()[-1]
    explained = inland_water.AreaCheck("Fiji", 18757.0, 79.0, 96.0, 18274.0, "Mangroves, accepted by the PO.")
    assert explained.passed and "Mangroves" in explained.lines()[-1]
    assert "Wetlands mapped in OSM, not taken away: 96.0 km2." in explained.lines()[2]
    close = inland_water.AreaCheck("Sweden", 450198.0, 2700.0, 0.0, 447425.0, None)
    assert close.within and close.passed and len(close.lines()) == 2


# Countries kept on their own ------------------------------------------------

def test_store_keeps_each_country_under_its_fingerprint(tmp_path):
    store = kept.Store(tmp_path)
    fp = kept.fingerprint({"settings": {"id": "osm:r1"}, "shapes": kept.shapes_print([shapely.box(0, 0, 1, 1)])})
    assert store.load("osm:r1", fp) is None
    store.save("osm:r1", fp, {"land": {"osm:r1": shapely.box(0, 0, 1, 1)}})
    assert store.load("osm:r1", fp)["land"]["osm:r1"].equals(shapely.box(0, 0, 1, 1))
    other = kept.fingerprint({"settings": {"id": "osm:r1", "land_within": [[0, 0, 1, 1]]},
                              "shapes": kept.shapes_print([shapely.box(0, 0, 1, 1)])})
    assert other != fp and store.load("osm:r1", other) is None


def test_neighbours_are_countries_whose_shapes_touch():
    ids = ["a", "b", "c"]
    raw = [shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1), shapely.box(5, 5, 6, 6)]
    assert kept.neighbours(ids, raw) == [("a", "b")]


def _recheck(tmp_path, matches_by_call, rebuilt, prints=None):
    store = kept.Store(tmp_path)
    prints = prints or {"a": "1", "b": "2"}
    calls, rebuilds = [], []

    def check(x, y):
        calls.append((x, y))
        return {"matches": matches_by_call[min(len(calls), len(matches_by_call)) - 1]}

    def rebuild(cid):
        rebuilds.append(cid)
        return prints[cid]

    rows = kept.recheck_borders([("a", "b")], prints, set(rebuilt), store, check, rebuild)
    return rows, calls, rebuilds, store


def test_a_border_is_checked_again_only_when_a_side_was_rebuilt(tmp_path):
    rows, calls, _r, _s = _recheck(tmp_path, [True], rebuilt={"a"})
    assert rows[0].matches and len(calls) == 1 and not rows[0].from_store
    rows, calls, _r, _s = _recheck(tmp_path, [False], rebuilt=set())
    assert rows[0].from_store and rows[0].matches and calls == []
    rows, calls, _r, _s = _recheck(tmp_path, [True], rebuilt={"b"})
    assert not rows[0].from_store and len(calls) == 1


def test_a_neighbour_whose_border_no_longer_matches_is_rebuilt(tmp_path):
    rows, calls, rebuilds, _s = _recheck(tmp_path, [False, True], rebuilt={"a"})
    assert rebuilds == ["b"] and len(calls) == 2
    assert rows[0].matches and rows[0].rebuilt == ["b"] and not rows[0].still_wrong


def test_a_border_still_wrong_after_rebuilding_is_reported(tmp_path):
    rows, calls, rebuilds, _s = _recheck(tmp_path, [False, False], rebuilt={"a"})
    assert rebuilds == ["b"] and not rows[0].matches and rows[0].still_wrong


def test_border_check_on_neighbours_that_meet_and_that_overlap():
    a, b = shapely.box(4.0, 50.0, 5.0, 51.0), shapely.box(5.0, 50.0, 6.0, 51.0)
    good = border_check(a, b, a, b, window_km=5, tolerance=0.001)
    assert good["border"] and good["matches"] and good["in_both_km2"] == 0.0
    overlapping = shapely.box(4.9, 50.0, 6.0, 51.0)   # about 780 km2 in both
    bad = border_check(a, overlapping, a, overlapping, window_km=5, tolerance=0.001)
    assert not bad["matches"] and bad["in_both_km2"] > 100


def test_country_print_changes_only_for_the_country_changed(tmp_path):
    gol, lp = tmp_path / "planet.gol", tmp_path / "land"
    gol.write_bytes(b"x")
    lp.write_bytes(b"y")
    shapes = {"osm:r1": shapely.box(0, 0, 1, 1), "osm:r2": shapely.box(1, 0, 2, 1)}
    config = {"region_level": 4}
    settings = {"osm:r1": {"id": "osm:r1", "divisions": True}, "osm:r2": {"id": "osm:r2"}}
    divs = {("osm:r1", 4): [Area("osm:r10", "A", 4, shapely.box(0, 0, 1, 1))]}

    def prints(settings_, record):
        return {c: country_print(c, config, settings_, record, shapes, divs, [], gol, lp) for c in shapes}

    first = prints(settings, {})
    changed = prints({**settings, "osm:r2": {"id": "osm:r2", "land_within": [[1, 0, 2, 1]]}}, {})
    assert changed["osm:r1"] == first["osm:r1"] and changed["osm:r2"] != first["osm:r2"]
    worked_out = prints(settings, {"osm:r1": {"levels": [6, 7], "how": "worked out by spike S2"}})
    assert worked_out == first
    corrected = prints(settings, {"osm:r1": {"levels": [9], "how": "corrected: level 9 is used"}})
    assert corrected["osm:r1"] != first["osm:r1"] and corrected["osm:r2"] == first["osm:r2"]
    divs[("osm:r1", 4)][0].tags = {"disputed": "yes"}
    assert prints(settings, {})["osm:r1"] != first["osm:r1"]
