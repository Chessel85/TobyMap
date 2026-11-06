"""P1-T3: the pipeline skeleton (DMT-1, DMT-2, DMT-6, DMT-7, DAT-9, AD-18)."""
import re
import shutil
from pathlib import Path

import pytest

from mapcore.packs.pack import Pack
from mapdata.__main__ import main
from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.pipeline import ledger as ledgermod
from mapdata.pipeline.build import build
from mapdata.pipeline.check import check
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.progress import Progress
from mapdata.pipeline.settings import load_pack
from mapdata.pipeline.switch import PAUSED_EXIT, Switch

ROOT = Path(__file__).resolve().parents[2]


def run_build(data: Path, workers: int = 1, config_dir: Path = CONFIG_DIR, switch: Switch | None = None,
              clock=None) -> tuple[int, list[str]]:
    lines: list[str] = []
    switch = switch or Switch(data.parent / "no switch here.txt")  # never the data manager's own continue.txt
    extra = {"clock": clock} if clock else {}
    code = build("test", DataFolders(data, "a test"), workers, say=lines.append, config_dir=config_dir,
                 switch=switch, **extra)
    return code, lines


def files_under(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


# DMT-6: licences --------------------------------------------------------------

def test_a_source_with_no_licence_stops_the_build(tmp_path):
    config = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    text = (config / "sources.yaml").read_text(encoding="utf-8")
    start = text.index("  sample-oceans:")
    block_end = text.index("  sample-osm:")
    block = re.sub(r"\n    licence: .*", "", text[start:block_end])
    (config / "sources.yaml").write_text(text[:start] + block + text[block_end:], encoding="utf-8")
    data = tmp_path / "data"
    data.mkdir()
    code, lines = run_build(data, config_dir=config)
    assert code == 1
    assert "sample-oceans has no licence" in lines[-1]
    assert "Add its licence" in lines[-1]
    assert not (data / "tobymap").exists()  # stopped before any work


def test_the_pack_carries_every_source_licence_and_attribution(test_pack):
    with Pack(test_pack, check_app=False) as p:
        names = {s["name"]: s for s in p.manifest["sources"]}
        assert {s["licence"] for s in names.values()} == {"Public domain", "CC-BY 4.0", "ODbL 1.0"}
        assert "© OpenStreetMap contributors" in p.attribution
        assert "Flanders Marine Institute" in p.attribution
        assert "Natural Earth" in p.attribution
        assert "Open Database License" in p.licence
        assert p.manifest["built"] == "2026-11-03"  # the sources' dates, not the clock


# Stage caching (architecture 8.3) ---------------------------------------------

def test_a_second_build_with_nothing_changed_skips_every_stage(tmp_path):
    code, first = run_build(tmp_path)
    assert code == 0
    code, second = run_build(tmp_path)
    assert code == 0
    assert "Stages skipped, as nothing they use had changed: samples, water, write." in second
    assert not any(line.startswith("Stages run") for line in second)


def test_a_changed_setting_runs_its_stage_and_those_after_again(tmp_path):
    config = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    data = tmp_path / "data"
    data.mkdir()
    assert run_build(data, config_dir=config)[0] == 0
    pack_file = config / "packs" / "test.yaml"
    pack_file.write_text(pack_file.read_text(encoding="utf-8").replace("land_layer: countries",
                                                                       "land_layer: countries  # changed"),
                         encoding="utf-8")
    assert run_build(data, config_dir=config)[0] == 0  # a comment changes nothing
    pack_file.write_text(pack_file.read_text(encoding="utf-8").replace("land_layer: countries  # changed",
                                                                       "land_layer: regions"),
                         encoding="utf-8")
    code, lines = run_build(data, config_dir=config)
    assert code == 0
    assert "Stages skipped, as nothing they use had changed: samples." in lines
    assert any(line.startswith("Stages run: water in") and "write in" in line for line in lines)


# SCP-7: layer definitions ----------------------------------------------------------

def test_how_a_layer_is_shown_changes_only_the_pack_writing(tmp_path):
    """The group, zoom range and sounds of a layer go into the pack, but the areas are
    not built again for them, so the world rebuild can use its kept results."""
    config = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    data = tmp_path / "data"
    data.mkdir()
    assert run_build(data, config_dir=config)[0] == 0
    layers = config / "layers" / "base.yaml"
    layers.write_text(layers.read_text(encoding="utf-8").replace(
        "name: Regions, rank: 4, kind: land, group: Boundaries, geometry: area, switched_on: true, max_zoom_m: 1000000",
        "name: Regions, rank: 4, kind: land, group: Boundaries, geometry: area, switched_on: false, "
        "min_zoom_m: 1000, max_zoom_m: 2500000, crossing_earcon: line_crossing"), encoding="utf-8")
    code, lines = run_build(data, config_dir=config)
    assert code == 0
    assert "Stages skipped, as nothing they use had changed: samples, water." in lines
    pack = Pack(data / "tobymap" / "output" / "test" / "test.pack")
    regions = next(d for d in pack.layers if d["id"] == "regions")
    pack.close()
    assert regions == {"id": "regions", "name": "Regions", "rank": 4, "group": "Boundaries", "geometry": "area",
                       "switched_on": False, "min_zoom_m": 1000, "max_zoom_m": 2500000,
                       "crossing_earcon": "line_crossing"}


def test_the_build_fingerprint_of_a_layer_is_what_it_was_before_p2_t3():
    """The stages before the writing see only id, name, rank and kind, exactly as
    before P2-T3, so the kept results of the Phase 1 world build are still used."""
    pack = load_pack("world")
    assert {k: v.build_fields() for k, v in pack.layers.items()}["regions"] == {
        "id": "regions", "name": "Regions", "rank": 4, "kind": "land"}


def test_adding_a_group_of_lines_does_not_make_the_areas_again(tmp_path):
    """The graticule (P2-T10d): the stages that make the countries and divisions, from
    the planet file, are fingerprinted only by the area layers and their groups."""
    from mapdata.pipeline.build import fingerprint

    config = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    world = config / "packs" / "world.yaml"
    world.write_text(world.read_text(encoding="utf-8").replace("layer_groups: [base, graticule]",
                                                               "layer_groups: [base]"), encoding="utf-8")
    without = load_pack("world", config)
    with_lines = load_pack("world", CONFIG_DIR)
    assert "graticule" in with_lines.layers and "graticule" not in without.layers
    prints = {"planet": "p", "land-polygons": "l", "vliz-oceans": "v", "naturalearth-geographic-lines": "n"}
    for name in ("osm-areas", "squares", "join"):
        stage = next(s for s in with_lines.stages if s["stage"] == name)
        assert fingerprint(without, stage, "x", prints) == fingerprint(with_lines, stage, "x", prints)
    write = next(s for s in with_lines.stages if s["stage"] == "write")
    assert fingerprint(without, write, "x", prints) != fingerprint(with_lines, write, "x", prints)


@pytest.mark.parametrize("extra, words", [
    ("colour: red", "a setting mapdata does not know: colour"),
    ("geometry: blob", "use area, line or point"),
    ("switched_on: maybe", "use true or false"),
    ("min_zoom_m: 5000, max_zoom_m: 100", "min_zoom_m larger than max_zoom_m"),
    ("crossing_earcon: trumpet", "not one of the application's sounds"),
])
def test_a_wrong_layer_definition_stops_the_build_with_the_reason(tmp_path, extra, words):
    config = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml"))
    layers = config / "layers" / "base.yaml"
    layers.write_text(layers.read_text(encoding="utf-8").replace(
        "name: Counties, rank: 6, kind: land, group: Boundaries, geometry: area, switched_on: true, max_zoom_m: 100000",
        f"name: Counties, rank: 6, kind: land, group: Boundaries, {extra}"), encoding="utf-8")
    with pytest.raises(BuildStopped, match=words):
        load_pack("test", config)


# DMT-1: the same pack, byte for byte ----------------------------------------------

def test_the_test_pack_built_twice_is_identical(tmp_path, test_pack):
    again = tmp_path / "again"
    again.mkdir()
    assert run_build(again, workers=2)[0] == 0  # worker processes finish in any order
    built = again / "tobymap" / "output" / "test" / "test.pack"
    assert built.read_bytes() == test_pack.read_bytes()
    assert built.with_name("test.pack.sha256").read_text() == test_pack.with_name("test.pack.sha256").read_text()


# DMT-2: progress, summary and log ----------------------------------------------------

def test_progress_lines_are_never_closer_than_10_seconds():
    now = [0.0]
    shown: list[tuple[float, str]] = []
    progress = Progress(say=lambda text: shown.append((now[0], text)), clock=lambda: now[0])
    for step in range(200):
        now[0] = step * 0.7
        progress.line(f"line {step}")
    times = [t for t, _ in shown]
    assert len(shown) > 5
    assert all(b - a >= 10 for a, b in zip(times, times[1:]))
    assert len(progress.lines) == 200  # every line is in the log


def test_the_build_writes_a_summary_and_a_full_log(test_pack):
    log = test_pack.with_name("test build log.txt")
    text = log.read_text(encoding="utf-8")
    assert "Stage 1 of 3: reading the samples." in text
    assert "Source sample-osm: OpenStreetMap, small test samples, ODbL 1.0" in text
    assert "Summary of the build of test:" in text
    assert "Oceans and seas: 2 areas." in text


# DMT-7 and AD-18: where files are written ----------------------------------------------

def test_nothing_is_written_outside_the_tobymap_folder(tmp_path):
    (tmp_path / "planet-2026-10-26.gol").write_bytes(b"the data manager's own file")
    before = files_under(tmp_path)
    assert run_build(tmp_path)[0] == 0
    after = files_under(tmp_path)
    new = after - before
    assert new and all(p.startswith("tobymap/") for p in new)
    assert (tmp_path / "planet-2026-10-26.gol").read_bytes() == b"the data manager's own file"


def recorded_paths(data: Path) -> set[str]:
    text = (data / "tobymap" / ledgermod.LEDGER_NAME).read_text(encoding="utf-8")
    return {line for line in text.splitlines() if line}


def test_every_file_made_is_recorded(tmp_path):
    assert run_build(tmp_path)[0] == 0
    made = files_under(tmp_path / "tobymap") - {ledgermod.LEDGER_NAME}
    assert made == recorded_paths(tmp_path)


def test_a_file_mapdata_did_not_create_is_never_overwritten(tmp_path):
    out = tmp_path / "tobymap" / "output" / "test"
    out.mkdir(parents=True)
    (out / "test.pack").write_bytes(b"someone else's file")
    code, lines = run_build(tmp_path)
    assert code == 1
    assert "did not create it, so it is not overwritten" in lines[-1]
    assert (out / "test.pack").read_bytes() == b"someone else's file"


def test_the_ledger_refuses_a_path_outside_its_folder(tmp_path):
    ledger = ledgermod.Ledger(tmp_path / "tobymap")
    with pytest.raises(BuildStopped):
        ledger.claim(tmp_path / "elsewhere.txt")
    with pytest.raises(BuildStopped):
        ledger.claim(tmp_path / "tobymap" / ".." / "escape.txt")


def test_no_drive_letter_in_code_settings_or_samples():
    """AD-18: no drive letter in mapdata's code, its shared settings, or the samples."""
    drive = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
    paths = list((ROOT / "mapdata").rglob("*.py")) + list((ROOT / "mapdata" / "config").rglob("*.yaml"))
    paths += list((ROOT / "tests" / "samples").rglob("*.*"))
    offenders = []
    for path in paths:
        if path.name == "paths.yaml":  # the local file, not in git
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"https?://\S+", "", text)
        if drive.search(text):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_a_build_stops_before_any_work_if_the_data_folder_is_missing(tmp_path):
    code, lines = run_build(tmp_path / "not-connected")
    assert code == 1
    assert "cannot be reached" in lines[-1] and "connect the drive" in lines[-1]
    assert not (tmp_path / "not-connected").exists()


# Settings ----------------------------------------------------------------------------

def test_the_test_pack_settings_name_their_sources_and_layers():
    pack = load_pack("test")
    assert list(pack.sources) == ["sample-world", "sample-oceans", "sample-osm"]
    assert {layer.kind for layer in pack.layers.values()} == {"land", "water"}
    assert [s["stage"] for s in pack.stages] == ["samples", "water", "write"]


def test_an_unknown_pack_lists_the_packs():
    with pytest.raises(BuildStopped) as info:
        load_pack("nowhere")
    assert "test" in info.value.message


# The test pack's contents ---------------------------------------------------------------

def at(pack_path: Path, lat: float, lon: float) -> list[str]:
    from mapdata.stages.lookup import Lookup, open_pack

    with open_pack(pack_path) as p:
        return [f["id"] for f in Lookup(p).at(lon, lat)]


@pytest.mark.parametrize("lat, lon, expected", [
    (50.69, -1.30, ["osm:r154350", "osm:r58447", "osm:r62149"]),      # Isle of Wight, England, UK
    (50.2, -1.0, ["vliz:goas:north-atlantic-ocean"]),                  # the Channel
    (30.0, -40.0, ["vliz:goas:north-atlantic-ocean"]),                 # 30 north 40 west (LOC-6)
    (-17.8, 178.0, ["osm:r13882087", "osm:r4632582", "osm:r571747"]),  # Fiji, east of the line
    (-16.47, -179.97, ["osm:r13881050", "osm:r4632581", "osm:r571747"]),  # Fiji, west of the line
    (65.78, -169.05, ["osm:r1949884", "osm:r151231", "osm:r60189"]),   # Big Diomede, Russia
    (65.755, -168.93, None),                                           # Little Diomede, the USA
    (-89.9, 45.0, ["osm:r2186646"]),                                   # near the South Pole
    (43.08, -79.08, ["osm:r2712312", "osm:r68841", "osm:r1428125"]),   # Niagara Falls, Canada
    (43.08, -79.06, ["osm:r36267", "osm:r61320", "osm:r148838"]),      # Niagara Falls, the USA
])
def test_what_is_at_the_sample_places(test_pack, lat, lon, expected):
    found = at(test_pack, lat, lon)
    if expected is None:
        assert "osm:r148838" in found and "osm:r60189" not in found
    else:
        assert found == expected


def test_each_country_from_osm_is_one_area_with_natural_earth_beyond_its_box(test_pack):
    with Pack(test_pack, check_app=False) as p:
        assert p.feature_by_id("ne:USA") is None
        assert p.feature_by_id("ne:GBR") is None
        assert at(test_pack, 39.0, -100.0) == ["osm:r148838"]  # Kansas, from Natural Earth
        assert at(test_pack, 48.85, 2.35) == ["osm:r1403916"]  # Paris, metropolitan France


# The commands ----------------------------------------------------------------------------

def test_inspect_gives_the_manifest_and_a_feature(test_pack, capsys):
    assert main(["inspect", str(test_pack), "manifest"]) == 0
    out = capsys.readouterr().out
    assert "Pack test, version 0.1.0, format 3" in out
    assert "Layers: Countries, Oceans and seas, Regions, Counties." in out
    assert main(["inspect", str(test_pack), "feature", "osm:r154350"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Isle of Wight: osm:r154350."
    assert "parents: osm:r58447." in out
    assert main(["inspect", str(test_pack), "at", "43.08", "-79.06"]) == 0
    assert "United States: countries" in capsys.readouterr().out
    assert main(["inspect", str(test_pack), "feature", "osm:r0"]) == 1
    assert "There is no feature osm:r0" in capsys.readouterr().out


def test_check_stops_if_the_data_folder_cannot_be_reached(tmp_path):
    lines: list[str] = []
    assert check(DataFolders(tmp_path / "gone", "a test"), say=lines.append) == 2
    assert len(lines) == 1 and "cannot be reached" in lines[0]


def test_check_reports_space_and_dates(tmp_path):
    land = tmp_path / "tobymap" / "downloads" / "osm-land-polygons" / "land-polygons-split-4326.zip"
    land.parent.mkdir(parents=True)
    land.write_bytes(b"")
    import os
    import time

    stamp = time.mktime((2026, 10, 31, 12, 0, 0, 0, 0, -1))
    os.utime(land, (stamp, stamp))
    (tmp_path / "planet-2025-10-20.gol").write_bytes(b"")
    lines: list[str] = []
    assert check(DataFolders(tmp_path, "a test"), pack="test", say=lines.append) == 1
    text = "\n".join(lines)
    assert "GB free on its drive" in text
    assert "Planet file: planet-2025-10-20.gol, dated 20 October 2025" in text
    assert "Land polygons: land-polygons-split-4326.zip, dated 31 October 2026." in text
    assert "376 days apart" in text
    assert "The pack test needs about 50 MB, which fits." in text


def test_fetch_finds_the_samples_in_the_repository(tmp_path, capsys):
    assert main(["--data", str(tmp_path), "fetch", "--pack", "test"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("sample-world: in the repository, tests/samples/world-naturalearth-110m.geojson")
    assert out[-1] == "Summary: 3 of 3 sources ready."


# The run switch, continue.txt -------------------------------------------------------------

class SwitchAfter:
    """A switch that says yes for the first few reads, then no."""

    def __init__(self, yes_reads: int):
        self.left = yes_reads
        self.path = Path("continue.txt")

    def says_no(self) -> bool:
        self.left -= 1
        return self.left < 0

    def check(self, where: str) -> None:
        Switch.check(self, where)


def test_continue_txt_saying_no_pauses_the_build_and_keeps_finished_stages(tmp_path):
    code, lines = run_build(tmp_path, switch=SwitchAfter(1))  # stage 1 runs, then the switch says no
    assert code == PAUSED_EXIT
    assert lines[-1].startswith("Paused before stage 2 of 3, taking the land out of the water layers, as "
                                "continue.txt says no.")
    assert "run the same command again" in lines[-1]
    assert not (tmp_path / "tobymap" / "output" / "test" / "test.pack").exists()
    code, lines = run_build(tmp_path)
    assert code == 0
    assert "Stages skipped, as nothing they use had changed: samples." in lines


def test_the_switch_reads_the_first_line_only(tmp_path):
    f = tmp_path / "continue.txt"
    assert not Switch(f).says_no()  # no file: carry on
    f.write_text("no\nnotes below\n", encoding="utf-8")
    assert Switch(f).says_no()
    f.write_text(" No \n", encoding="utf-8")
    assert Switch(f).says_no()
    f.write_text("yes\nno\n", encoding="utf-8")
    assert not Switch(f).says_no()


def test_wait_for_yes_starts_the_build_again_when_the_switch_says_yes():
    from mapdata.pipeline.build import build_waiting

    answers = iter([False, True, True, False, False])  # yes; then no, no (waiting), yes, yes
    switch = type("S", (), {"path": Path("continue.txt"), "says_no": lambda self: next(answers)})()
    results = iter([PAUSED_EXIT, 0])
    runs, sleeps, said = [], [], []
    code = build_waiting([], switch, say=said.append, sleep=sleeps.append,
                         run=lambda: runs.append(1) or next(results))
    assert code == 0 and len(runs) == 2 and len(sleeps) == 1
    assert said[0].startswith("Waiting, as continue.txt says no.")
