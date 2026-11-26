"""The stages that pass every feature through, made kinder to memory for England (P4-T1l, design docs/plan/p4-t1-design.md
7.4).

* The relationships of the light layers are worked out in batches of features near each other, after the other
  layers, and must be the same as when every feature is related at once.
* relationships.json, features.json and shapes.wkb are written as before, byte for byte.
* The Wikidata stage reads the records alone, and keeps the shapes file as it is.
"""
import json
import types

import numpy as np
import pytest
import shapely

from mapdata.pipeline import features
from mapdata.pipeline.peak import PeakWatch
from mapdata.stages import relationships as rel
from mapdata.stages import wikidata

from tests.mapdata.test_light_layers import LIGHT, RANKS, _street_scene


def _by_name(out: dict, names: list[str]) -> dict:
    def name(v):
        if isinstance(v, int):
            return names[v]
        if isinstance(v, list) and v and isinstance(v[0], int):
            return [names[v[0]], *v[1:]]
        return v
    return {names[i]: {k: ([name(x) for x in v] if isinstance(v, list) else v) for k, v in r.items()}
            for i, r in out.items()}


def _at_once(scene: dict, settings: dict) -> dict:
    names = list(scene)
    records = [{"id": n, "layer": scene[n][0], "name": n} for n in names]
    kinds = [scene[n][1] for n in names]
    geoms = [scene[n][2] for n in names]
    sums = rel.measure(records, geoms, kinds, settings, say=lambda s: None)
    return _by_name(rel.relationships(records, geoms, kinds, sums, RANKS, set(), settings), names)


def _in_batches(scene: dict, settings: dict, folder) -> dict:
    """As the stage does it: the layers that are not light first, then the light ones in batches."""
    names = list(scene)
    records = [{"id": n, "layer": scene[n][0], "name": n} for n in names]
    kinds = [scene[n][1] for n in names]
    features.save(folder, records, [scene[n][2] for n in names])
    offsets = features.read_index(folder)["shapes"]
    light = set(settings["light_layers"])
    geoms = [None if records[i]["layer"] in light else scene[n][2] for i, n in enumerate(names)]
    sums = rel.measure(records, geoms, kinds, settings, say=lambda s: None)
    out = rel.relationships(records, geoms, kinds, sums, RANKS, set(), settings)
    lit = [i for i, r in enumerate(records) if r["layer"] in light]
    texts, _counts = rel.light_relationships(folder, offsets, lit, records, kinds, geoms, sums, RANKS, set(), settings,
                                             None, 1, say=lambda s: None)
    out.update({i: json.loads(t) for i, t in texts.items()})
    return _by_name(out, names)


def _close(a, b):
    """Two relationships the same but for floating point in the last places of a share."""
    if isinstance(a, float) or isinstance(b, float):
        return a == pytest.approx(b, abs=1e-3)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    return a == b


@pytest.mark.parametrize("batch_points", [1, 3, 1_000_000], ids=["one feature a batch", "small", "one batch"])
@pytest.mark.parametrize("fine", [False, True], ids=["whole boxes", "small boxes"])
def test_light_features_related_in_batches_are_as_when_related_at_once(tmp_path, batch_points, fine):
    more = {"leaf_points": 0, "min_leaf_deg": 0.1} if fine else {}
    settings = {**rel.SETTINGS, **LIGHT, **more, "batch_points": batch_points}
    scene = _street_scene()
    # A street wholly outside every area, and a light area reaching beyond the county, so batches see edges too.
    scene["Lost Lane"] = ("streets", rel.LINE, shapely.LineString([(2, 2), (2.1, 2.1)]))
    scene["Edge Park"] = ("parks", rel.AREA, shapely.box(0.9, 0.4, 1.1, 0.5))
    at_once = _at_once(scene, settings)
    batched = _in_batches(scene, settings, tmp_path)
    assert set(batched) == set(at_once)
    for name in at_once:
        assert _close(batched[name], at_once[name]), (name, batched[name], at_once[name])
    assert {a: s for a, s in batched["Edge Park"]["partly"]}["Hampshire"] == pytest.approx(0.5, abs=0.01)


def test_batches_hold_near_features_together_and_each_feature_once():
    rng = np.random.default_rng(1)
    centres = rng.uniform(0, 1, (200, 2))
    bounds = np.column_stack([centres, centres + 0.001])
    idx = np.arange(200, dtype=np.intp) * 3
    batches = rel.light_batches(idx, bounds, np.full(200, 10), most=200, cell_deg=0.05)
    got = np.concatenate(batches)
    assert sorted(got.tolist()) == idx.tolist()
    assert all(len(b) <= 20 for b in batches)   # about most points each
    assert all((np.diff(b) > 0).all() for b in batches)   # in order within a batch
    # Near features come together: a batch's box is much smaller than for features taken in their own order, which
    # is random here (about 0.8 of the square).
    where = {int(i): k for k, i in enumerate(idx)}
    boxes = [np.prod(np.ptp(centres[[where[int(i)] for i in b]], axis=0)) for b in batches]
    assert np.mean(boxes) < 0.3


def test_relationships_file_is_written_as_before(tmp_path):
    out = {2: {"in": [0, 1], "partly": [[3, 0.25]]}, 10: {"counts": {"b": 1, "a": 2}}, 1: {"outline_km": 3.5}}
    rel.write_file(tmp_path / "a.json", out)
    before = json.dumps({str(i): r for i, r in sorted(out.items())}, sort_keys=True, separators=(",", ":"))
    assert (tmp_path / "a.json").read_text(encoding="utf-8") == before
    texts = {2: json.dumps(out.pop(2), sort_keys=True, separators=(",", ":"))}
    rel.write_file(tmp_path / "b.json", out, texts)
    assert (tmp_path / "b.json").read_text(encoding="utf-8") == before


def test_records_saved_with_the_shapes_kept_are_as_saved_with_the_shapes(tmp_path):
    records = [{"id": "a", "layer": "streets", "name": "Footpath"}, {"id": "b", "layer": "streets", "name": "Café"}]
    geoms = [shapely.LineString([(0, 0), (1, 1)]), shapely.Polygon([(0, 0), (1, 0), (1, 1)])]
    for name in ("before", "after", "again"):
        (tmp_path / name).mkdir()
    features.save(tmp_path / "before", records, geoms)
    index = features.read_index(tmp_path / "before")
    assert index["records"] == records
    assert index["records"][0]["layer"] is index["records"][1]["layer"]   # a repeated short string held once
    features.save(tmp_path / "again", *features.load(tmp_path / "before"))
    features.save_records(tmp_path / "after", index["records"], tmp_path / "before", index["shapes"])
    for name in ("features.json", "shapes.wkb"):
        assert (tmp_path / "after" / name).read_bytes() == (tmp_path / "again" / name).read_bytes()
    got = features.read_shapes(tmp_path / "before", index["shapes"], [1])
    assert list(got) == [1] and got[1].equals(geoms[1])


def test_the_wikidata_stage_keeps_the_shapes_file_and_reads_only_the_shapes_it_matches(tmp_path, monkeypatch):
    src, out = tmp_path / "src", tmp_path / "out"
    src.mkdir()
    out.mkdir()
    records = [{"id": "a", "layer": "lakes", "name": "Lake A"}, {"id": "b", "layer": "streets", "name": "B"}]
    features.save(src, records, [shapely.box(0, 0, 1, 1), shapely.LineString([(0, 0), (1, 1)])])
    read = []
    real = features.read_shapes
    monkeypatch.setattr(features, "read_shapes", lambda f, o, which: read.append(sorted(which)) or real(f, o, which))
    facts = tmp_path / "facts"
    facts.mkdir()
    lines: list[str] = []
    ctx = types.SimpleNamespace(settings={"source": "s", "refresh": "x", "offline": True, "match": ["lakes"]},
                                previous=src, folder=out, claim=lambda p: p, source=lambda k: (k, str(facts)),
                                progress=types.SimpleNamespace(line=lines.append, log=lines.append),
                                pack=types.SimpleNamespace(layers={}))
    wikidata.run(ctx)
    assert read == [[0]]   # the lake, to be matched by name and place; not the street
    assert (out / "shapes.wkb").read_bytes() == (src / "shapes.wkb").read_bytes()
    assert features.load_records(out) == records


def test_the_peak_memory_watch_says_nothing_where_it_cannot_measure():
    with PeakWatch(interval=0.05) as watch:
        _big = b"x" * (50 * 2 ** 20)
    text = watch.sentence()
    if text:
        assert text.startswith("Peak memory: the build's own process ") and watch.main_mb >= 50
    else:
        assert watch.main_mb == 0
