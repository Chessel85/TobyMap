"""The world build's extra checks: areas against Wikidata, and the 180 degree line (DAT-14)."""
from types import SimpleNamespace

from mapdata.stages import checks, lookup


def fake_ctx(settings):
    lines = []
    progress = SimpleNamespace(line=lines.append, log=lines.append, always=lines.append)
    return SimpleNamespace(settings=settings, progress=progress), lines


def test_area_check_names_the_nearest_figure(test_pack):
    with lookup.open_pack(test_pack) as pack:
        antarctica = next(pack.feature(n) for n in range(pack.manifest["features"]["count"])
                          if pack.feature(n).get("name") == "Antarctica")
        km2 = antarctica["area_km2"]
        ctx, _ = fake_ctx({"area_checks": [{"name": "Antarctica", "wikidata_km2": [km2 * 1.5, km2 * 1.01],
                                            "tolerance_pct": 2},
                                           {"name": "Atlantis", "wikidata_km2": [1]}]})
        done = checks.area_checks(ctx, pack)
    assert done[0]["passed"] and "1.0" in done[0]["text"] or "-1.0" in done[0]["text"]
    assert not done[1]["passed"]


def test_the_180_degree_line_check_runs(test_pack):
    with lookup.open_pack(test_pack) as pack:
        ctx, _ = fake_ctx({})
        done = checks.line_180(ctx, pack, lookup.Lookup(pack))
    jump = next(d for d in done if d["check"].startswith("No edge"))
    assert jump["passed"]
