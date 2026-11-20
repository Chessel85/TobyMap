"""P4-T4a: the correction rules (DMT-4, DMT-3).

A rule in the test pack's settings renames, leaves out, changes or sets the parent of a feature in the pack, and is
listed in the build's log, its summary and the corrections stage's report; a rule for an identifier not in the data
is reported, not silently ignored. A changed rule runs only the corrections and the writing again.
"""
import shutil
from pathlib import Path

import pytest
import yaml

from mapcore import search
from mapcore.packs.pack import Pack
from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.pipeline.build import build
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.switch import Switch
from mapdata.stages import corrections

PORTSMOUTH, SOUTHAMPTON, HAMPSHIRE, ISLE_OF_WIGHT = "osm:r127167", "osm:r127864", "osm:r172799", "osm:r154350"
STATION, ITCHEN, ENGLAND, WILTSHIRE = "osm:n638908005", "osm:r7703089", "osm:r58447", "osm:r57533"

RULES = [
    {"id": PORTSMOUTH, "rename": "Pompey", "local_name": "Pompey", "reason": "A test of renaming."},
    {"id": SOUTHAMPTON, "leave_out": True, "reason": "A test of leaving out."},
    {"id": HAMPSHIRE, "change": {"kind": "shire county"}, "reason": "A test of changing the kind."},
    {"id": ISLE_OF_WIGHT, "layer": "counties", "parent": WILTSHIRE, "reason": "A test of setting the parent."},
    {"id": "osm:r999999999", "rename": "Nowhere", "reason": "A test of a feature not in the data."},
    {"id": ENGLAND, "change": {"layer": "rivers"}, "reason": "A test of a rule that cannot be applied."},
]


def with_rules(tmp_path: Path, rules: list) -> Path:
    """A copy of the settings, with the rules in the test pack's corrections stage."""
    config = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    set_rules(config, rules)
    return config


def set_rules(config: Path, rules: list) -> None:
    path = config / "packs" / "test.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    stage = next(s for s in data["stages"] if s["stage"] == "corrections")
    stage["rules"] = rules
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def run(data: Path, config: Path) -> tuple[int, list[str]]:
    lines: list[str] = []
    code = build("test", DataFolders(data, "a test"), say=lines.append, config_dir=config,
                 switch=Switch(data.parent / "no switch here.txt"))
    return code, lines


@pytest.fixture(scope="module")
def corrected(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("corrected")
    data = tmp / "data"
    data.mkdir()
    config = with_rules(tmp, RULES)
    code, lines = run(data, config)
    assert code == 0, "\n".join(lines)
    return data, config, lines


@pytest.fixture(scope="module")
def pack(corrected):
    with Pack(corrected[0] / "tobymap" / "output" / "test" / "test.pack", check_app=False) as p:
        yield p


def report(data: Path) -> str:
    (folder,) = (data / "tobymap" / "working" / "test").glob("*-corrections-*")
    return (folder / corrections.REPORT).read_text(encoding="utf-8")


def test_a_rule_renames_a_feature_in_the_pack_and_its_search(pack):
    rec = pack.feature_by_id(PORTSMOUTH)
    assert rec["name"] == "Pompey"
    assert rec["names"]["en"] == "Pompey"
    rows = [row for b in range(pack.search_buckets) for row in pack.search_rows(b) if row[search.ID] == PORTSMOUTH]
    names = {row[search.NAME] for row in rows}
    assert "Pompey" in names
    # Its official name from Wikidata is still found, as a rule renames only the feature's own name.
    assert names <= {"Pompey", "Portsmouth"}


def test_the_rules_applied_and_not_found_are_in_the_report_the_log_and_the_summary(corrected):
    data, _config, lines = corrected
    text = report(data)
    assert f"Applied: rename {PORTSMOUTH} to Pompey, with the local name Pompey. Reason: A test of renaming." in text
    assert (f"Not found: rename osm:r999999999 to Nowhere. Reason: A test of a feature not in the data. "
            "No feature has the identifier osm:r999999999.") in text
    assert f"Not applied: change {ENGLAND}: its layer to rivers." in text
    summary = ("Correction rules: 4 rules applied, 1 rule whose feature was not found, 1 rule found but not "
               "applied.")
    assert summary in text
    assert any(line.startswith(summary + " Each is listed in") for line in lines)   # the build's summary
    log = (data / "tobymap" / "output" / "test" / "test build log.txt").read_text(encoding="utf-8")
    assert f"Applied: rename {PORTSMOUTH} to Pompey" in log
    assert "Not found: rename osm:r999999999" in log


def test_a_feature_left_out_is_gone_from_the_pack_and_from_the_others_relationships(pack):
    assert pack.feature_by_id(SOUTHAMPTON) is None
    assert pack.relationships(STATION)["in"][0] != SOUTHAMPTON
    assert SOUTHAMPTON not in pack.relationships(STATION)["in"]
    assert SOUTHAMPTON not in pack.relationships(ITCHEN)["crosses"]
    assert SOUTHAMPTON not in [i for i, _km in pack.relationships(HAMPSHIRE).get("near", ())]
    for n in range(pack.manifest["features"]["count"]):   # every identifier in a relationship is a feature
        fid = pack.feature(n)["id"]
        rel = pack.relationships(fid)
        for key in ("in", "same", "crosses", "crossed_by", "along", "partly_by"):
            assert all(pack.feature_number(i) is not None for i in rel.get(key, ())), (fid, key)
        for key in ("next", "near", "overlaps", "partly", "coast", "shores"):
            assert all(pack.feature_number(v[0]) is not None for v in rel.get(key, ())), (fid, key)


def test_a_rule_changes_a_features_kind(pack):
    assert pack.feature_by_id(HAMPSHIRE)["type"] == "shire county"


def test_a_rule_sets_a_features_parent(pack):
    rec = pack.feature_by_id(ISLE_OF_WIGHT)
    assert rec["parents"] == [WILTSHIRE]
    assert pack.relationships(ISLE_OF_WIGHT)["in"][0] == WILTSHIRE
    assert pack.relationships(WILTSHIRE)["counts"]["counties"] >= 1


def test_a_changed_rule_runs_only_the_corrections_and_the_writing_again(tmp_path):
    config = with_rules(tmp_path, [RULES[0]])
    data = tmp_path / "data"
    data.mkdir()
    assert run(data, config)[0] == 0
    set_rules(config, [{**RULES[0], "rename": "Portsmouth again"}])
    code, lines = run(data, config)
    assert code == 0, "\n".join(lines)
    assert ("Stages skipped, as nothing they use had changed: samples, distant-parts, water, disputes, enclaves, "
            "wikidata, relationships, coast-stretches.") in lines
    assert any(line.startswith("Stages run: corrections in") and "write in" in line for line in lines)
    with Pack(data / "tobymap" / "output" / "test" / "test.pack", check_app=False) as p:
        assert p.feature_by_id(PORTSMOUTH)["name"] == "Portsmouth again"


def test_a_rule_with_no_reason_stops_the_build_before_any_work(tmp_path):
    config = with_rules(tmp_path, [{"id": PORTSMOUTH, "rename": "Pompey"}])
    data = tmp_path / "data"
    data.mkdir()
    code, lines = run(data, config)
    assert code == 1
    assert "Correction rule 1 in the corrections stage's setting rules for osm:r127167 has no reason." in lines[-1]
    assert not (data / "tobymap" / "working").exists()


@pytest.mark.parametrize("rule, words", [
    ({"rename": "X", "reason": "r"}, "has no id"),
    ({"id": "a", "reason": "r"}, "must do one thing"),
    ({"id": "a", "rename": "X", "leave_out": True, "reason": "r"}, "must do one thing"),
    ({"id": "a", "leave_out": "yes", "reason": "r"}, "must say leave_out: true"),
    ({"id": "a", "change": {"colour": "red"}, "reason": "r"}, "a new layer, a new kind, or both"),
    ({"id": "a", "rename": "X", "reason": "r", "nmae": "Y"}, "settings mapdata does not know: nmae"),
])
def test_a_rule_that_cannot_be_read_says_why(rule, words):
    with pytest.raises(BuildStopped, match=words):
        corrections.check_rule(rule, 1, "a test")


def test_the_rules_file_is_read_and_its_dp221_rule_is_valid():
    rules = corrections.load_rules({"stage": "corrections"})
    hebrides = next(r for r in rules if r["id"] == "ne:marine:1159115921")
    assert hebrides["rename"] == "Inner Seas off the West Coast of Scotland"
    assert "DP221" in hebrides["reason"]


def test_leaving_out_renumbers_every_index():
    records = [{"id": "a", "layer": "countries"}, {"id": "b", "layer": "countries", "parent": "a"},
               {"id": "c", "layer": "towns", "within": [{"id": "a", "layer": "countries"},
                                                        {"id": "b", "layer": "countries"}]}]
    rel = {0: {"next": [[1, 5.0]], "counts": {"towns": 1}},
           1: {"next": [[0, 5.0]], "counts": {"towns": 1},
               "coast_stretches": {"stretches": [{"ends": [[0, 0, 0], [1, 1, 2]], "water": 0}], "islands_km": 0}},
           2: {"in": [0, 1]}}
    out_records, shapes, out_rel = corrections.leave_out([0], records, [[0, 1], [1, 1], [2, 1]], rel)
    assert [r["id"] for r in out_records] == ["b", "c"]
    assert shapes == [[1, 1], [2, 1]]
    assert "parent" not in out_records[0]
    assert out_records[1]["within"] == [{"id": "b", "layer": "countries"}]
    assert out_rel[0] == {"counts": {"towns": 1},
                          "coast_stretches": {"stretches": [{"ends": [[0, 0, None], [1, 1, 1]], "water": None}],
                                              "islands_km": 0}}
    assert out_rel[1] == {"in": [0]}
