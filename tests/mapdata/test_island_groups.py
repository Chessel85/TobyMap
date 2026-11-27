"""P4-T13b: groups of islands, each outline grown from its own islands over the sea between them (DAT-1, DAT-3, LOC-3).
The method is P4-T13a's, docs/plan/p4-t13a-island-groups-report.md."""
import json
import types
from pathlib import Path

import numpy as np
import pytest
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.build import STAGES
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import load_pack
from mapdata.stages import island_groups as ig
from mapdata.stages import physical

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "osm"
EMPTY = shapely.GeometryCollection()

# A made-up group at about 49 degrees north, a degree of longitude about 73 km: three islands, A and B 0.4 degrees
# (about 29 km) apart with C between, a mainland to the east 0.5 degrees from B, and an island D far to the west.
A = shapely.box(-3.0, 49.0, -2.9, 49.1)
B = shapely.box(-2.5, 49.0, -2.4, 49.1)
C = shapely.box(-2.72, 49.04, -2.68, 49.06)
D = shapely.box(-6.0, 49.0, -5.9, 49.1)
MAINLAND = shapely.box(-1.9, 48.0, 0.0, 50.0)
ISLANDS = [("osm:wa", "A", A), ("osm:wb", "B", B), ("osm:wc", "C", C), ("osm:wd", "D", D)]
NO_RECORD = {"links": {}, "names": {}, "leave_out": [], "natural_earth_keep": [], "groups": []}


def islands(items=ISLANDS, wikidata=None):
    wikidata = wikidata or {}
    return ig.Islands([{"id": i, "name": n, "layer": "islands", **({"wikidata": wikidata[i]} if i in wikidata else {})}
                       for i, n, _g in items], [g for _i, _n, g in items])


def land(*extra):
    """The countries: each island is land too, as the join stage draws it, with the mainland."""
    return ig.LandParts([shapely.MultiPolygon([A, B, C]), D, MAINLAND, *extra])


def osm_group(gid, name, g=EMPTY, relation="multipolygon", **more):
    return ({"id": gid, "name": name, "relation": relation, **more}, g)


def groups(osm, record=NO_RECORD, ne=(), links=None, isl=None, lands=None, areas=None, countries=(), **s):
    recs, geoms, log = ig.make_groups(list(osm), isl or islands(), lands or land(), areas or {}, list(ne),
                                      links or {}, record, set(countries), {"layer": "island-groups", **s})
    return {r["id"]: (r, g) for r, g in zip(recs, geoms)}, log


def coast_outline(*shapes):
    """An OpenStreetMap group's outline: the coast of its islands, not the sea between them."""
    return shapely.MultiPolygon([s.buffer(0.001) for s in shapes])


def test_a_groups_islands_are_those_inside_its_outline_and_its_outline_covers_the_sea_between_them():
    got, _ = groups([osm_group("osm:r1", "Les Iles", coast_outline(A, B, C), name_en="The Isles", wikidata="Q1")])
    rec, g = got["group:osm:r1"]
    assert rec == {"id": "group:osm:r1", "layer": "island-groups", "name": "The Isles", "type": "group of islands",
                   "local_name": "Les Iles", "wikidata": "Q1"}
    assert g.covers(shapely.Point(-2.95, 49.05)) and g.covers(shapely.Point(-2.70, 49.05))   # on the islands
    assert g.covers(shapely.Point(-2.80, 49.05)) and g.covers(shapely.Point(-2.60, 49.05))   # at sea between them
    assert not g.covers(shapely.Point(-2.65, 49.40))   # 30 km out to sea, north of the group
    assert not g.covers(shapely.Point(-5.95, 49.05))   # D, far away, is no member


def test_the_outer_edge_lies_three_kilometres_off_the_outer_coasts():
    got, _ = groups([osm_group("osm:r1", "Isles", coast_outline(A, B, C))])
    g = got["group:osm:r1"][1]
    north = 49.1 + 2.5 / 111.32
    assert g.covers(shapely.Point(-2.95, north)) and not g.covers(shapely.Point(-2.95, 49.1 + 4 / 111.32))


def test_land_that_is_not_in_the_group_is_cut_away_at_its_own_coast():
    """A mainland 0.03 degrees (about 2 km) east of B, inside the 3 km edge: the grown outline reaches it, and it is
    cut off at its coast exactly."""
    near = shapely.box(-2.37, 48.0, 0.0, 50.0)
    got, _ = groups([osm_group("osm:r1", "Isles", coast_outline(A, B, C))],
                    lands=ig.LandParts([shapely.MultiPolygon([A, B, C]), near]))
    g = got["group:osm:r1"][1]
    assert g.intersects(near.buffer(0.01))   # it reached the mainland
    assert shapely.intersection(g, near).area < 1e-12
    assert g.covers(shapely.Point(-2.385, 49.05))   # the sea between B and the mainland


def test_a_relation_with_no_outline_takes_the_islands_it_lists_and_its_inner_groups():
    """As the Cyclades: a list of islands, and Santorini's group, joined through Wikidata (P361)."""
    osm = [osm_group("osm:r1", "Cyclades", relation="group", members=["osm:wa", "osm:wb"], wikidata="Q10"),
           osm_group("osm:r2", "Santorini", relation="group", members=["osm:wc", "osm:n9"], wikidata="Q20")]
    links = {"Q10": {"parts": [], "part_of": []}, "Q20": {"parts": [], "part_of": ["Q10"]}}
    got, log = groups(osm, links=links, min_islands=1, min_land_km2=0)
    assert got["group:osm:r1"][1].covers(shapely.Point(-2.70, 49.05))   # C, Santorini's, is in the Cyclades
    assert "Groups inside groups found through Wikidata: 1." in log


def test_a_group_a_relation_lists_is_inside_it():
    osm = [osm_group("osm:r1", "Frisian Islands", relation="group", members=["osm:r2", "osm:r3"]),
           osm_group("osm:r2", "West", coast_outline(A)), osm_group("osm:r3", "East", coast_outline(B))]
    got, _ = groups(osm, min_islands=1, min_land_km2=0)
    whole = got["group:osm:r1"][1]
    assert whole.covers(shapely.Point(-2.95, 49.05)) and whole.covers(shapely.Point(-2.45, 49.05))


def test_land_area_site_and_cluster_relations_are_left_out():
    osm = [osm_group("osm:r1", "Guernsey (land mass)", coast_outline(A, C), relation="land_area"),
           osm_group("osm:r2", "Site", coast_outline(A, C), relation="site")]
    got, log = groups(osm)
    assert not got
    assert "Left out: 1 relations of type land_area, not a group of islands." in log


def test_a_group_needs_two_islands_and_its_least_land():
    osm = [osm_group("osm:r1", "One", coast_outline(A)), osm_group("osm:r2", "Rocks", coast_outline(C, B))]
    got, log = groups(osm, min_land_km2=100)   # C and B: about 82 km2 of land
    assert not got
    assert log[-1].startswith("Groups too small to keep") and log[-1].endswith(": 2.")
    got, _ = groups(osm, min_land_km2=50)
    assert set(got) == {"group:osm:r2"}


def test_the_record_gives_groups_links_names_and_leaves_out():
    record = {**NO_RECORD, "links": {"osm:r1": "Q5"}, "names": {"osm:r1": "Outer Isles"}, "leave_out": ["osm:r2"],
              "groups": [{"id": "record:all", "name": "All Isles", "wikidata": "Q9", "islands_in": "osm:region",
                          "islands": ["Q40"], "groups": ["osm:r1"]}]}
    osm = [osm_group("osm:r1", "Western Isles", coast_outline(A, C)), osm_group("osm:r2", "Wrong", coast_outline(B, C))]
    got, _ = groups(osm, record=record, isl=islands(wikidata={"osm:wd": "Q40"}),
                    areas={"osm:region": shapely.box(-2.6, 48.9, -2.3, 49.2)})
    assert set(got) == {"group:osm:r1", "group:record:all"}
    assert got["group:osm:r1"][0]["name"] == "Outer Isles" and got["group:osm:r1"][0]["wikidata"] == "Q5"
    every = got["group:record:all"][1]
    for x in (-2.95, -2.70, -2.45, -5.95):   # A and C from its group, B from the region, D by its Wikidata item
        assert every.covers(shapely.Point(x, 49.05))
    assert got["group:record:all"][0]["wikidata"] == "Q9"


def test_the_name_falls_back_to_wikidatas_label_then_openstreetmaps_own():
    osm = [osm_group("osm:r1", "Arquipélago dos Açores", coast_outline(A, C), wikidata="Q7")]
    got, _ = groups(osm, links={"Q7": {"parts": [], "part_of": [], "label": "Azores"}})
    assert got["group:osm:r1"][0]["name"] == "Azores"
    got, _ = groups(osm)
    assert got["group:osm:r1"][0]["name"] == "Arquipélago dos Açores" and "local_name" not in got["group:osm:r1"][0]


def test_two_groups_with_one_wikidata_item_are_one():
    osm = [osm_group("osm:r1", "Isles", coast_outline(A, C), wikidata="Q3"),
           osm_group("osm:r2", "Isles", relation="group", members=["osm:wa", "osm:wb", "osm:wc"], wikidata="Q3")]
    got, log = groups(osm)
    assert list(got) == ["group:osm:r2"]
    assert any("is the same Wikidata item, Q3" in t for t in log)


def ne_group(i, name, g, wikidata=None):
    return ({"id": f"ne:region:{i}", "name": name, "type": "group of islands",
             **({"wikidata": wikidata} if wikidata else {})}, g)


def test_natural_earths_groups_count_only_where_openstreetmap_has_none():
    rough = shapely.box(-3.1, 48.9, -2.3, 49.2)
    osm = [osm_group("osm:r1", "Isles", coast_outline(A, C), wikidata="Q1")]
    got, _ = groups(osm, ne=[ne_group(1, "Isles", rough), ne_group(2, "Other", rough, "Q1")])
    assert set(got) == {"group:osm:r1"}   # matched by name, and by Wikidata link
    got, _ = groups([], ne=[ne_group(3, "Far Isles", rough)])
    rec, g = got["group:ne:3"]
    assert rec["name"] == "Far Isles" and g.covers(shapely.Point(-2.6, 49.05))
    assert not g.covers(shapely.Point(-3.08, 49.15))   # Natural Earth's rough outline is not used


def test_a_natural_earth_group_that_is_one_island_or_a_country_is_left_out():
    rough = shapely.box(-3.1, 48.9, -2.3, 49.2)
    big = [("osm:wa", "A", shapely.box(-3.0, 49.0, -2.6, 49.1)), ("osm:wc", "C", C)]
    got, log = groups([], ne=[ne_group(1, "Maui", rough)], isl=islands(big),
                      lands=ig.LandParts([g for _i, _n, g in big]))
    assert not got and any("its largest island holds" in t for t in log)
    record = {**NO_RECORD, "natural_earth_keep": ["Maui"]}
    got, _ = groups([], ne=[ne_group(1, "Maui", rough)], isl=islands(big), record=record,
                    lands=ig.LandParts([g for _i, _n, g in big]))
    assert "group:ne:1" in got
    got, log = groups([], ne=[ne_group(2, "Japan", rough)], countries={"Japan"})
    assert not got and any("a country's name" in t for t in log)


def test_a_trial_box_cuts_a_group_and_does_not_drop_it():
    got, _ = groups([osm_group("osm:r1", "Isles", coast_outline(A, B, C))], box=[-2.8, 48.0, 0.0, 50.0])
    g = got["group:osm:r1"][1]
    assert g.bounds[0] >= -2.8 and g.covers(shapely.Point(-2.45, 49.05))


def test_the_joining_reach_is_found_by_halving():
    two = shapely.MultiPolygon([shapely.box(0, 0, 1, 1), shapely.box(11, 0, 12, 1)])   # kilometres, 10 apart
    assert 4.9 <= ig.joining_reach(two, 30) <= 5.3
    assert ig.joining_reach(shapely.box(0, 0, 1, 1), 30) == 0
    assert ig.joining_reach(two, 3) == 3


def test_a_group_either_side_of_the_180_degree_line_stays_whole():
    east, west = shapely.box(179.8, -17.0, 179.9, -16.9), shapely.box(-179.9, -17.0, -179.8, -16.9)
    g, _reach = ig.outline([east, west], ig.LandParts([east, west]), {**ig.DEFAULTS})
    assert g.bounds[0] >= -180 and g.bounds[2] <= 180
    assert g.covers(shapely.Point(179.99, -16.95)) and g.covers(shapely.Point(-179.99, -16.95))


# The Channel Islands, from the test pack's sample (P4-T13b) ------------------------------------------------------

def sample(name):
    data = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
    return [(f["properties"], shapely.geometry.shape(f["geometry"])) for f in data["features"]]


@pytest.fixture(scope="module")
def channel_islands():
    feats = sample("channel-islands.geojson")
    isl = [(p["id"], p["name"], g) for p, g in feats if p["layer"] == "islands"]
    countries = [g for p, g in feats if p["layer"] == "countries"]
    france = [g for p, g in sample("england-france-channel.geojson") if p["layer"] == "countries"]
    group = shapely.union_all([g for _i, _n, g in isl]).buffer(0.002)   # OpenStreetMap's outline: the coasts
    got, _ = groups([osm_group("osm:r6031891", "Channel Islands", group, wikidata="Q42314")], isl=islands(isl),
                    lands=ig.LandParts(countries + france))
    return got["group:osm:r6031891"][1], [g for p, g in feats if p["layer"] == "island-groups"][0]


SARK = (-2.36, 49.43)
BETWEEN_GUERNSEY_AND_JERSEY = (-2.35, 49.33)
OPEN_CHANNEL = (-3.0, 49.4)          # 35 km west of Guernsey
OFF_COTENTIN = (-1.95, 49.45)        # 5 km off the coast of France


def test_sark_and_the_sea_between_guernsey_and_jersey_are_in_the_channel_islands(channel_islands):
    for g in channel_islands:   # as the stage makes it here, and as the sample keeps it
        assert g.covers(shapely.Point(*SARK)) and g.covers(shapely.Point(*BETWEEN_GUERNSEY_AND_JERSEY))


def test_the_open_channel_and_the_sea_off_france_are_not(channel_islands):
    for g in channel_islands:
        assert not g.covers(shapely.Point(*OPEN_CHANNEL)) and not g.covers(shapely.Point(*OFF_COTENTIN))


# Fetching the links, the stage and the packs' settings -----------------------------------------------------------

def test_the_links_between_groups_come_from_wikidatas_own_interface():
    asked = []

    def get(url):
        asked.append(url)
        claim = lambda q: {"mainsnak": {"datavalue": {"value": {"id": q}}}}   # noqa: E731
        return {"entities": {"Q10": {"labels": {"en": {"value": "Cyclades"}}, "claims": {"P527": [claim("Q20")]}},
                             "Q20": {"claims": {"P361": [claim("Q10")]}}}}

    kept = {}
    got = ig.fetch_links(["Q10", "Q20", "Q99"], get=get, say=lambda t: None, keep=kept.update, today="2026-11-21")
    assert got["Q10"] == {"id": "Q10", "fetched": "2026-11-21", "parts": ["Q20"], "part_of": [], "label": "Cyclades"}
    assert got["Q20"]["part_of"] == ["Q10"] and got["Q99"]["parts"] == [] and kept == got
    assert len(asked) == 1 and "wbgetentities" in asked[0] and "Q10%7CQ20%7CQ99" in asked[0]


class Lines:
    def __init__(self):
        self.lines, self.logged = [], []

    def line(self, text):
        self.lines.append(text)

    def log(self, text):
        self.logged.append(text)


def test_the_stage_keeps_the_features_before_and_adds_the_groups_after_them(tmp_path, monkeypatch):
    before, out = tmp_path / "before", tmp_path / "here"
    before.mkdir()
    out.mkdir()
    features.save(before, [{"id": "c", "layer": "countries", "name": "Land"}] +
                  [{"id": i, "layer": "islands", "name": n} for i, n, _g in ISLANDS],
                  [shapely.MultiPolygon([A, B, C, D])] + [g for _i, _n, g in ISLANDS])
    monkeypatch.setattr(ig, "read_planet", lambda ctx, gol: ([{"id": "osm:r1", "name": "Isles",
                                                                "relation": "multipolygon"}], [coast_outline(A, B, C)]))
    ctx = types.SimpleNamespace(settings={}, previous=before, folder=out, progress=Lines(), claim=lambda p: p,
                                pack=types.SimpleNamespace(layers={"island-groups": object()}),
                                source=lambda key: (None, tmp_path / "planet.gol"))
    ig.run(ctx)
    records, _geoms = features.load(out)
    assert [r["id"] for r in records] == ["c", "osm:wa", "osm:wb", "osm:wc", "osm:wd", "group:osm:r1"]
    assert ctx.progress.lines[-1].startswith("Groups of islands: 1 groups")


def test_the_stage_stops_with_the_reason_when_there_are_no_islands(tmp_path):
    features.save(tmp_path, [{"id": "c", "layer": "countries", "name": "Land"}], [MAINLAND])
    ctx = types.SimpleNamespace(settings={}, previous=tmp_path, progress=Lines(),
                                pack=types.SimpleNamespace(layers={"island-groups": object()}))
    with pytest.raises(BuildStopped, match="islands of the layer islands"):
        ig.run(ctx)


def test_the_record_is_checked_before_any_work(tmp_path):
    bad = tmp_path / "groups.yaml"
    bad.write_text("groups:\n  - {id: x, name: X, outline: here}\n", encoding="utf-8")
    with pytest.raises(BuildStopped, match="may give only"):
        ig.load_record(bad)
    assert ig.fingerprint_extra({})["record"]["groups"]   # the repository's record, read whole


def test_natural_earths_groups_of_islands_are_gone_from_the_physical_layer(tmp_path):
    path = tmp_path / "regions.geojson"
    feats = [{"type": "Feature", "properties": {"FEATURECLA": c, "NAME": n, "NAME_EN": n, "NE_ID": i},
              "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}
             for i, (c, n) in enumerate([("Desert", "Sahara"), ("Island group", "British Isles")], 1)]
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    before, out = tmp_path / "before", tmp_path / "here"
    before.mkdir()
    out.mkdir()
    features.save(before, [{"id": "c", "layer": "countries", "name": "Land"}], [shapely.box(0, 0, 1, 1)])
    ctx = types.SimpleNamespace(
        settings={"regions": {"source": "ne", "layer": "physical-regions",
                              "classes": {"Desert": "desert", "Island group": "group of islands"}}},
        previous=before, folder=out, progress=Lines(), claim=lambda p: p,
        pack=types.SimpleNamespace(layers={"physical-regions": object()}), source=lambda key: (types.SimpleNamespace(
            name="Natural Earth"), path))
    physical.run(ctx)
    records, _ = features.load(out)
    assert [r["name"] for r in records if r["layer"] == "physical-regions"] == ["Sahara"]
    assert any("Island group is left out" in t for t in ctx.progress.lines)
    for name in ("world", "trial-western-europe"):
        stage = next(s for s in load_pack(name).stages if s["stage"] == "physical")
        assert "Island group" not in stage["regions"]["classes"]


def test_the_world_and_the_trial_make_the_groups_just_after_the_territorial_waters():
    for name in ("world", "trial-western-europe"):
        pack = load_pack(name)
        kinds = [s["stage"] for s in pack.stages]
        assert kinds[kinds.index("territorial-waters") + 1] == "island-groups"
        stage = pack.stages[kinds.index("island-groups")]
        assert stage["source"] == "planet" and stage["refresh"] and not stage.get("offline")
        layer = pack.layers["island-groups"]
        assert layer.made_by == "island-groups" and dict(layer.shown)["group"] == "Physical features"
        assert dict(layer.shown)["fill"] == "none"   # groups overlap, so not simplified as one coverage
        wikidata = next(s for s in pack.stages if s["stage"] == "wikidata")
        assert "island-groups" in wikidata["match"]
    assert STAGES["island-groups"].module == "mapdata.stages.island_groups"
    assert np.all([m.startswith("mapdata.stages.") for m in STAGES["island-groups"].code])


def test_a_busy_wikidata_is_asked_again_after_a_wait():
    """The world build of 27 November stopped on Wikidata's 429, Too Many Requests: the links are asked for again,
    after the wait it names."""
    import email.message
    import io
    import urllib.error

    calls, waits = [], []

    class Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def open_url(req, timeout):
        calls.append(req.full_url)
        if len(calls) < 3:
            headers = email.message.Message()
            headers["Retry-After"] = "7"
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", headers, None)
        return Answer(b'{"entities": {}}')

    got = ig._get_json("https://example.org/w/api.php", sleep=waits.append, say=lambda t: None, open_url=open_url)
    assert got == {"entities": {}}
    assert len(calls) == 3
    assert waits == [7.0, 14.0]


def test_a_request_wikidata_refuses_is_not_asked_again():
    import urllib.error

    calls = []

    def open_url(req, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", None, None)

    with pytest.raises(urllib.error.HTTPError):
        ig._get_json("https://example.org/w/api.php", sleep=lambda s: None, say=lambda t: None, open_url=open_url)
    assert len(calls) == 1
