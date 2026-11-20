"""P4-T11a: the quality report (DMT-3). Every build writes a text report and CSV files beside the pack, in plain
lines; `mapdata report <pack>` makes them again; the report names the differences from the build before."""
import csv
import shutil
from pathlib import Path

import pytest

from mapdata.__main__ import main
from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.pipeline import report
from mapdata.pipeline.build import build
from mapdata.pipeline.switch import Switch
from tests.mapdata.test_corrections import PORTSMOUTH, set_rules

RENAME = {"id": PORTSMOUTH, "rename": "Pompey", "local_name": "Pompey", "reason": "A test of renaming."}


def run(data: Path, config: Path) -> tuple[int, list[str]]:
    lines: list[str] = []
    code = build("test", DataFolders(data, "a test"), say=lines.append, config_dir=config,
                 switch=Switch(data.parent / "no switch here.txt"))
    return code, lines


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def two_builds(tmp_path_factory):
    """The test pack built without a rule, then with a rule renaming Portsmouth: the second is compared with the first."""
    tmp = tmp_path_factory.mktemp("report")
    config = tmp / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    data = tmp / "data"
    data.mkdir()
    set_rules(config, [])
    code, first = run(data, config)
    assert code == 0, "\n".join(first)
    out = data / "tobymap" / "output" / "test"
    first_report = (out / "test quality report.txt").read_text(encoding="utf-8")
    set_rules(config, [RENAME])
    code, second = run(data, config)
    assert code == 0, "\n".join(second)
    return data, out, first_report, second


def test_the_first_build_says_there_is_no_earlier_build(two_builds):
    text = two_builds[2]
    assert "there is no earlier build to compare with" in text.lower()


def test_the_report_lists_a_feature_renamed_in_the_settings(two_builds):
    _, out, _, _ = two_builds
    text = (out / "test quality report.txt").read_text(encoding="utf-8")
    assert f"Applied: rename {PORTSMOUTH} to Pompey, with the local name Pompey. Reason: A test of renaming." in text
    assert "Renamed in " in text and f"{PORTSMOUTH} from Portsmouth to Pompey." in text
    rows = read_csv(out / "test quality differences by feature.csv")
    assert {"change": "renamed", "layer": "Counties", "identifier": PORTSMOUTH, "name before": "Portsmouth",
            "name now": "Pompey"} in rows
    rules = read_csv(out / "test quality correction rules.csv")
    assert rules[0]["result"] == "applied" and "Pompey" in rules[0]["rule"]


def test_the_report_has_every_section_with_counts_first(two_builds):
    text = (two_builds[1] / "test quality report.txt").read_text(encoding="utf-8")
    for heading in ("In short", "Repaired shapes", "Features without names", "Gaps in coverage",
                    "Gaps filled by the counties record", "Matches made by name for Wikidata",
                    "Correction rules applied", "Size by layer", "Differences from the last build"):
        assert f"\n{heading}\n" in text
    assert "Features without names: 0 of" in text
    assert "Not recorded by this build yet" in text   # the test pack has no planet reading to keep repairs from
    assert "|" not in text   # no tables


def test_the_csv_files_and_the_summary_are_beside_the_pack(two_builds):
    _, out, _, _ = two_builds
    for name in report.file_names("test").values():
        if name.endswith("summary of the build before.json.gz") or "repaired shapes" in name or "gaps" in name:
            continue   # a pack without those stages' reports has no such file
        assert (out / name).is_file(), name
    sizes = read_csv(out / "test quality size by layer.csv")
    assert sizes[-1]["layer"] == "the pack's own records"
    assert (out / "test quality summary of the build before.json.gz").is_file()


def test_the_build_summary_says_where_the_report_is(two_builds):
    assert any(line.startswith("The quality report is ") and line.endswith("quality report.txt. Its full lists are CSV files beside it.")
               for line in two_builds[3])


def test_the_report_command_makes_it_again_and_keeps_the_build_before(two_builds):
    data, out, _, _ = two_builds
    before = (out / "test quality report.txt").read_text(encoding="utf-8")
    (out / "test quality report.txt").write_text("", encoding="utf-8")
    assert report.report_command("test", DataFolders(data, "a test"), config_dir=two_builds_config(data)) == 0
    assert (out / "test quality report.txt").read_text(encoding="utf-8") == before   # the same pack: nothing new to compare


def two_builds_config(data: Path) -> Path:
    return data.parent / "config"


def test_the_command_is_known_and_stops_plainly_without_a_pack(tmp_path, capsys):
    code = main(["--data", str(tmp_path), "report", "test"])
    assert code == 1
    assert "There is no pack" in capsys.readouterr().out
