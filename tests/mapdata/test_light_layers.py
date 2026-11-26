"""Light layers and the layers given facts, at street scale (P4-T1k; design docs/plan/p4-t1-design.md 3.12).

A feature of a light layer, such as a street, gets only the areas it is in or partly in and, for a line, the
crossing_areas layers it passes through in order. It has no neighbours, nothing nearly touching, no overlaps, holds
nothing and is not counted in any area's counts. With no light layers, the relationships are as before.
"""
import hashlib
import json
import platform
import types

import numpy as np
import pytest
import shapely

from mapdata.pipeline import features
from mapdata.stages import relationships as rel
from mapdata.stages import wikidata

RANKS = {"counties": 6, "districts": 7, "parishes": 7, "national_parks": 6, "streets": 8, "parks": 8,
         "villages": 8}
LIGHT = {"light_layers": ["streets", "parks", "villages"],
         "crossing_areas": ["countries", "regions", "counties", "districts", "parishes"]}


def _relate(shapes: dict, settings: dict) -> dict:
    """The relationships of made-up features, by name: shapes is {name: (layer, kind, shape)}."""
    names = list(shapes)
    records = [{"id": n, "layer": shapes[n][0], "name": n} for n in names]
    kinds = [shapes[n][1] for n in names]
    geoms = [shapes[n][2] for n in names]
    settings = {**rel.SETTINGS, **settings}
    sums = rel.measure(records, geoms, kinds, settings, say=lambda s: None)
    out = rel.relationships(records, geoms, kinds, sums, RANKS, set(), settings)

    def name(v):
        if isinstance(v, int):
            return names[v]
        if isinstance(v, list) and v and isinstance(v[0], int):
            return [names[v[0]], *v[1:]]
        return v
    return {names[i]: {k: ([name(x) for x in v] if isinstance(v, list) else v) for k, v in r.items()}
            for i, r in out.items()}


def _street_scene():
    A, L, P = rel.AREA, rel.LINE, rel.POINT
    return {
        "Hampshire": ("counties", A, shapely.box(0, 0, 1, 1)),
        "Winchester": ("districts", A, shapely.box(0, 0, 1, 1).difference(shapely.box(0, 0.8, 1, 1))),
        "North District": ("districts", A, shapely.box(0, 0.8, 1, 1)),
        "West Parish": ("parishes", A, shapely.box(0, 0, 0.5, 0.8)),
        "East Parish": ("parishes", A, shapely.box(0.5, 0, 1, 0.8)),
        "Forest": ("national_parks", A, shapely.box(0.6, 0.1, 0.9, 0.3)),
        # From the east parish into the west one: its parishes are east first.
        "High Street": ("streets", L, shapely.LineString([(0.8, 0.5), (0.2, 0.5)])),
        "Short Lane": ("streets", L, shapely.LineString([(0.1, 0.1), (0.2, 0.2)])),
        "Forest Road": ("streets", L, shapely.LineString([(0.55, 0.2), (0.75, 0.2)])),
        "Park One": ("parks", A, shapely.box(0.1, 0.6, 0.2, 0.7)),
        "Park Two": ("parks", A, shapely.box(0.2, 0.6, 0.3, 0.7)),   # shares a border with Park One
        "Across Park": ("parks", A, shapely.box(0.45, 0.6, 0.55, 0.7)),   # half in each parish
        "Hamlet": ("villages", P, shapely.MultiPoint([(0.15, 0.65)])),   # inside Park One
    }


@pytest.mark.parametrize("fine", [False, True], ids=["whole boxes", "small boxes"])
def test_a_street_has_its_parish_district_and_county_and_its_parishes_in_order_and_no_neighbours(fine):
    more = {"leaf_points": 0, "min_leaf_deg": 0.1} if fine else {}
    out = _relate(_street_scene(), {**LIGHT, **more})
    lane = out["Short Lane"]
    assert set(lane["in"]) == {"West Parish", "Winchester", "Hampshire"}
    assert set(lane["crosses"]) == {"Hampshire", "Winchester", "West Parish"}
    high = out["High Street"]
    assert set(high["in"]) == {"Winchester", "Hampshire"}
    assert {a: s for a, s in high["partly"]} == pytest.approx({"East Parish": 0.5, "West Parish": 0.5}, abs=0.01)
    parishes = [a for a in high["crosses"] if a.endswith("Parish")]
    assert parishes == ["East Parish", "West Parish"]   # in order from its start
    # A layer not in crossing_areas is not among its crossings, though the street is partly inside it.
    road = out["Forest Road"]
    assert "Forest" in {a for a, _s in road["partly"]}
    assert "Forest" not in road["crosses"]
    for street in ("High Street", "Short Lane", "Forest Road"):
        assert not {"next", "near", "overlaps", "counts", "along", "crossed_at"} & set(out[street]), street


@pytest.mark.parametrize("fine", [False, True], ids=["whole boxes", "small boxes"])
def test_light_areas_have_only_containment_hold_nothing_and_are_not_counted(fine):
    more = {"leaf_points": 0, "min_leaf_deg": 0.1} if fine else {}
    out = _relate(_street_scene(), {**LIGHT, **more})
    park = out["Park One"]
    assert set(park["in"]) == {"West Parish", "Winchester", "Hampshire"}
    assert not {"next", "near", "overlaps", "counts", "same", "crossed_by", "outline_km"} & set(park)
    across = out["Across Park"]
    assert {a: s for a, s in across["partly"]} == pytest.approx({"East Parish": 0.5, "West Parish": 0.5}, abs=0.01)
    assert "overlaps" not in across
    assert "Park One" not in out["Hamlet"].get("in", [])   # a light area holds nothing
    assert "West Parish" in out["Hamlet"]["in"]
    # No area lists a light feature, or counts it.
    for name in ("Hampshire", "Winchester", "West Parish", "East Parish", "Forest"):
        r = out.get(name, {})
        assert not {"streets", "parks", "villages"} & set(r.get("counts", {})), name
        listed = set(r.get("crossed_by", [])) | set(r.get("partly_by", [])) | {v[0] for v in r.get("overlaps", [])} \
            | {v[0] for v in r.get("crossed_at", [])}
        assert not listed & {"High Street", "Short Lane", "Forest Road", "Park One", "Park Two", "Across Park"}, name
    # The areas that are not light keep everything.
    assert {v[0] for v in out["West Parish"]["next"]} == {"East Parish"}
    assert "Winchester" in {v[0] for v in out["North District"]["next"]}


def test_with_no_light_layers_a_street_is_related_as_before():
    out = _relate(_street_scene(), {})
    assert "next" in out["Park One"]
    assert out["West Parish"]["counts"]["streets"] >= 2


# The test pack's relationships with light_layers empty, against the file made before P4-T1k ----------------------

# relationships.json of the test pack, made with the code before P4-T1k, on Windows with these versions. Floating
# point sums may differ in the last place on another system or with another geometry library, so it is compared
# only where the versions are the same.
BEFORE_SHA256 = "7954c3f76adfe084883d803b9216adc6e69cc629196aec518cad48c30de6ebcc"
BEFORE_ON = ("Windows", "3.14.1", "2.5.4", "2.2.0")


def _versions():
    return (platform.system(), shapely.geos_version_string, np.__version__, shapely.__version__)


def _stage_file(pack_path, pack: str, name: str):
    working = pack_path.parents[2] / "working" / pack
    found = sorted(working.glob(f"*-relationships-*/{name}"))
    assert found, f"no relationships stage folder in {working}"
    return found[-1]


@pytest.mark.skipif(_versions() != BEFORE_ON, reason="the file before P4-T1k was made with other versions")
def test_the_test_packs_relationships_are_unchanged_with_no_light_layers(test_pack):
    path = _stage_file(test_pack, "test", rel.FILE)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == BEFORE_SHA256


# The regional test pack, with the light layers of test-region.yaml ------------------------------------------------

def test_the_regional_test_packs_streets_have_their_parishes_and_no_neighbours(test_region_pack):
    path = _stage_file(test_region_pack, "test-region", rel.FILE)
    records, geoms = features.load(path.parent)
    out = {int(k): v for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
    layer = [r["layer"] for r in records]
    light = {"main-roads", "streets", "paths", "streams", "land-use", "parks", "school-grounds", "stops",
             "shops-food", "services", "street-furniture", "villages"}
    streets = [i for i, l in enumerate(layer) if l == "streets"]
    assert streets
    km = dict(zip(streets, rel.lengths_km([geoms[i] for i in streets])))
    with_parish = 0
    for i in streets:
        r = out.get(i, {})
        assert not {"next", "near", "overlaps", "counts", "along", "crossed_at"} & set(r)
        holders = set(r.get("in", [])) | {v[0] for v in r.get("partly", [])}
        assert all(layer[a] not in light for a in holders)
        crossed = [layer[a] for a in r.get("crosses", [])]
        assert set(crossed) <= {"countries", "regions", "counties", "districts", "parishes"}
        if any(layer[a] == "parishes" for a in holders):
            with_parish += 1
            if km[i] >= 0.1:   # a street shorter than cross_km (50 metres) crosses nothing
                assert "parishes" in crossed, records[i]["id"]
    assert with_parish >= len(streets) * 0.9
    for r in out.values():
        assert not light & set(r.get("counts", {}))


# The wikidata stage's layers -----------------------------------------------------------------------------------

def test_facts_are_fetched_only_for_the_layers_named_and_for_every_layer_by_default():
    records = [{"id": "a", "layer": "counties", "wikidata": "Q1"}, {"id": "b", "layer": "streets", "wikidata": "Q2"},
               {"id": "c", "layer": "parks", "wikidata": "Q3"}]
    assert wikidata.given_facts(records, None) == [True, True, True]
    assert wikidata.given_facts(records, ["counties", "parks"]) == [True, False, True]


def test_the_regional_packs_fetch_facts_only_for_areas_lakes_rivers_parks_and_national_parks():
    import yaml

    from mapdata.paths import CONFIG_DIR

    for name in ("great-britain", "england", "hampshire-isle-of-wight"):
        stages = yaml.safe_load((CONFIG_DIR / "packs" / f"{name}.yaml").read_text(encoding="utf-8"))["stages"]
        layers = next(s for s in stages if s["stage"] == "wikidata")["layers"]
        assert {"lakes", "rivers", "parks", "national_parks", "parishes", "districts", "counties"} <= set(layers)
        assert not {"streets", "paths", "main-roads", "shops-food", "services", "stops", "street-furniture",
                    "land-use", "villages"} & set(layers)
        light = next(s for s in stages if s["stage"] == "relationships")["light_layers"]
        assert set(light) == {"main-roads", "streets", "paths", "streams", "land-use", "parks", "school-grounds",
                              "stops", "shops-food", "services", "street-furniture", "villages"}


def test_a_wikidata_run_with_layers_gives_facts_only_to_those_layers(tmp_path, monkeypatch):
    src, out = tmp_path / "src", tmp_path / "out"
    src.mkdir()
    out.mkdir()
    facts = tmp_path / "facts"
    facts.mkdir()
    records = [{"id": "a", "layer": "counties", "name": "A", "wikidata": "Q1"},
               {"id": "b", "layer": "streets", "name": "B", "wikidata": "Q2"}]
    features.save(src, records, [shapely.Point(0, 0), shapely.Point(1, 1)])
    entry = {"fetched": "2026-11-01", "rows": [["population", 100, None, "normal", None]]}
    (facts / "facts-x.jsonl").write_text("\n".join(json.dumps({"id": q, **entry}) for q in ("Q1", "Q2")) + "\n",
                                         encoding="utf-8")
    lines: list[str] = []
    ctx = types.SimpleNamespace(settings={"source": "s", "refresh": "x", "offline": True, "layers": ["counties"]},
                                previous=src, folder=out, claim=lambda p: p, source=lambda k: (k, str(facts)),
                                progress=types.SimpleNamespace(line=lines.append, log=lines.append),
                                pack=types.SimpleNamespace(layers={}))
    wikidata.run(ctx)
    got, _g = features.load(out)
    assert "facts" in got[0]
    assert "facts" not in got[1] and "sitelinks" not in got[1]
