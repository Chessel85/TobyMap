"""P4-T12a: territorial waters, the sea part of each OpenStreetMap country area, as a layer of its own (DAT-15)."""
import types

import numpy as np
import pytest
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.build import STAGES
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import load_pack
from mapdata.stages import physical, territorial_waters as tw

# A made-up coast at about 48 degrees north. France's land is west of 1 degree east; OpenStreetMap's France reaches
# 0.2 degrees out to sea, to the east. Switzerland has no coast. Jersey, an island off France, has waters that
# overlap France's.
FRANCE_LAND = shapely.box(0, 48, 1, 49)
FRANCE_AREA = shapely.box(0, 48, 1.2, 49)
SWISS_LAND = shapely.box(-1, 48, 0, 49)
JERSEY_LAND = shapely.box(1.5, 48.4, 1.6, 48.5)
JERSEY_AREA = shapely.box(1.1, 48.2, 2.0, 48.7)


class Lines:
    def __init__(self):
        self.lines, self.logged = [], []

    def line(self, text):
        self.lines.append(text)

    def log(self, text):
        self.logged.append(text)


def make_ctx(tmp_path, countries, outlines, settings=None):
    before, read, out = tmp_path / "join", tmp_path / "osm-areas", tmp_path / "here"
    for f in (before, read, out):
        f.mkdir()
    features.save(before, [{"id": "ocean", "layer": "oceans", "name": "Atlantic Ocean"}] +
                  [{"id": i, "layer": "countries", "name": n} for i, n, _g in countries],
                  [shapely.box(-2, 47, 3, 50)] + [g for _i, _n, g in countries])
    features.save(read, [r for r, _g in outlines], [g for _r, g in outlines])
    pack = types.SimpleNamespace(layers={"territorial-waters": object(), "countries": object()})
    return types.SimpleNamespace(settings={"tolerance_m": 0, **(settings or {})}, previous=before, folder=out,
                                 earlier={"osm-areas": read}, pack=pack, progress=Lines(), claim=lambda p: p)


def country(i, name, kind="country", **more):
    return {"id": i, "name": name, "kind": kind, "level": 2 if kind == "country" else 3, **more}


def run(ctx):
    tw.run(ctx)
    records, geoms = features.load(ctx.folder)
    return {r["id"]: (r, g) for r, g in zip(records, geoms)}, records


def test_a_countrys_territorial_waters_are_its_area_less_the_land_as_drawn(tmp_path):
    ctx = make_ctx(tmp_path, [("osm:fr", "France", FRANCE_LAND)], [(country("osm:fr", "France"), FRANCE_AREA)])
    got, records = run(ctx)
    rec, sea = got["territorial-waters:osm:fr"]
    assert rec == {"id": "territorial-waters:osm:fr", "layer": "territorial-waters",
                   "name": "Territorial waters of France", "type": "territorial waters", "country": "osm:fr"}
    assert shapely.intersection(sea, FRANCE_LAND).area < 1e-12          # at sea you are never in France
    assert abs(sea.area - shapely.box(1, 48, 1.2, 49).area) < 1e-12     # its inner edge is the drawn coast
    assert sea.covers(shapely.Point(1.05, 48.5)) and not sea.covers(shapely.Point(0.95, 48.5))
    # The features of the stage before are kept, first.
    assert [r["id"] for r in records[:2]] == ["ocean", "osm:fr"]


def test_a_country_with_no_sea_part_has_none(tmp_path):
    ctx = make_ctx(tmp_path, [("osm:ch", "Switzerland", SWISS_LAND), ("osm:fr", "France", FRANCE_LAND)],
                   [(country("osm:ch", "Switzerland"), SWISS_LAND), (country("osm:fr", "France"), FRANCE_AREA)])
    got, _ = run(ctx)
    assert "territorial-waters:osm:ch" not in got and "territorial-waters:osm:fr" in got
    assert "1 had no sea part" in ctx.progress.lines[-1]


def test_land_the_build_named_itself_has_no_outline_so_no_waters(tmp_path):
    ctx = make_ctx(tmp_path, [("unclaimed:1", "Unclaimed", shapely.box(5, 48, 5.1, 48.1))], [])
    got, _ = run(ctx)
    assert not any(k.startswith("territorial-waters:") for k in got)


def test_the_land_of_every_country_is_taken_out_not_only_its_own(tmp_path):
    """France's area as read reaches over Jersey; Jersey's land is still land, so not French waters."""
    big = shapely.box(0, 48, 2.0, 49)
    ctx = make_ctx(tmp_path, [("osm:fr", "France", FRANCE_LAND), ("osm:je", "Jersey", JERSEY_LAND)],
                   [(country("osm:fr", "France"), big), (country("osm:je", "Jersey"), JERSEY_AREA)])
    got, _ = run(ctx)
    assert shapely.intersection(got["territorial-waters:osm:fr"][1], JERSEY_LAND).area < 1e-12


def test_overlapping_waters_are_each_kept_and_the_log_lists_them(tmp_path):
    ctx = make_ctx(tmp_path, [("osm:fr", "France", FRANCE_LAND), ("osm:je", "Jersey", JERSEY_LAND)],
                   [(country("osm:fr", "France"), FRANCE_AREA), (country("osm:je", "Jersey"), JERSEY_AREA)])
    got, _ = run(ctx)
    fr, je = got["territorial-waters:osm:fr"][1], got["territorial-waters:osm:je"][1]
    assert shapely.intersection(fr, je).area > 0
    assert any("Overlapping territorial waters: Territorial waters of France and Territorial waters of Jersey"
               in t for t in ctx.progress.logged)
    assert "1 pairs overlap at sea" in ctx.progress.lines[-1]


def test_a_whole_country_split_into_units_keeps_the_waters_of_what_is_left(tmp_path):
    """DP86: OpenStreetMap's whole French state is not in the Countries layer, its units are. The waters of what is
    left, such as New Caledonia's, are named after the whole country."""
    caledonia = shapely.box(10, 48, 10.2, 48.2)
    whole = shapely.union_all([FRANCE_AREA, shapely.box(9.8, 47.8, 10.4, 48.4)])
    ctx = make_ctx(tmp_path, [("osm:metro", "France", FRANCE_LAND), ("part:nc", "New Caledonia", caledonia)],
                   [(country("osm:whole", "France"), whole),
                    (country("osm:metro", "France", kind="unit", country="osm:whole"), FRANCE_AREA)])
    got, _ = run(ctx)
    rest = got["territorial-waters:osm:whole"]
    assert rest[0]["name"] == "Territorial waters of France"
    assert shapely.intersection(rest[1], FRANCE_AREA).area < 1e-12   # metropolitan France's waters are its own
    assert abs(rest[1].area - (0.6 * 0.6 - 0.2 * 0.2)) < 1e-9


def test_a_trial_box_cuts_the_waters():
    land = physical.DrawnLand([FRANCE_LAND])
    sea = tw.waters(FRANCE_AREA, land, [-1, 48, 1.1, 48.5], 0, 0.1)
    assert sea.bounds == (1.0, 48.0, 1.1, 48.5)


def wiggly_coast(n=2000, amp=0.004):
    xs = np.linspace(48, 49, n)
    east = [(1 + amp * (1 if i % 2 else -1), y) for i, y in enumerate(xs)]
    return shapely.Polygon([(0, 48), *east, (0, 49)])


def test_the_sea_is_cut_a_box_at_a_time_and_joins_up_exactly():
    coast = wiggly_coast()
    land = physical.DrawnLand([coast], most=100)
    direct = shapely.difference(FRANCE_AREA, coast)
    sea = tw.sea_of(FRANCE_AREA, land, most_points=300)
    assert sea.is_valid and sea.geom_type == "Polygon"
    assert abs(sea.area - direct.area) < 1e-12
    assert shapely.intersection(sea, coast).area < 1e-12


def test_slivers_are_left_out():
    sliver = shapely.box(5, 48, 5.001, 48.001)   # about 0.008 square kilometres
    big = shapely.box(6, 48, 6.1, 48.1)
    kept = tw.drop_small(shapely.MultiPolygon([sliver, big]), 0.1)
    assert kept.equals(big)
    assert tw.drop_small(sliver, 0.1) is None


def test_the_stage_stops_with_the_reason_when_the_outlines_are_missing(tmp_path):
    ctx = make_ctx(tmp_path, [("osm:fr", "France", FRANCE_LAND)], [])
    ctx.earlier = {}
    with pytest.raises(BuildStopped, match="osm-areas"):
        tw.run(ctx)


def test_the_world_and_the_trial_make_territorial_waters_just_after_the_physical_stage():
    for name in ("world", "trial-western-europe"):
        pack = load_pack(name)
        kinds = [s["stage"] for s in pack.stages]
        assert kinds[kinds.index("physical") + 1] == "territorial-waters"
        stage = pack.stages[kinds.index("territorial-waters")]
        assert stage.get("tolerance_m", 100) == 100
        layer = pack.layers["territorial-waters"]
        assert layer.made_by == "territorial-waters"   # adding it never builds the countries again
        assert dict(layer.shown)["fill"] == "none"     # its areas overlap, so not simplified as one coverage
    assert STAGES["territorial-waters"].module == "mapdata.stages.territorial_waters"
    assert set(STAGES["territorial-waters"].code) == {"mapdata.stages.territorial_waters", "mapdata.stages.physical",
                                                      "mapcore.describe.words"}


def test_a_name_after_of_takes_the_as_the_application_says_it():
    assert tw.name_of(tw.NAME, "France") == "Territorial waters of France"
    assert tw.name_of(tw.NAME, "United Kingdom") == "Territorial waters of the United Kingdom"
    assert tw.name_of(tw.NAME, "Isle of Man") == "Territorial waters of the Isle of Man"
    assert "Kingdom" in tw.fingerprint_extra({})["the_words"]
