"""P4-T5b, P4-T5c: the space a build needs and the data folder, both checked before any work (DMT-7)."""
import shutil
from collections import namedtuple

import pytest

from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.pipeline import space
from mapdata.pipeline.build import build
from mapdata.pipeline.check import check
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import load_pack
from mapdata.pipeline.switch import Switch

Usage = namedtuple("Usage", "total used free")


def fake_free(monkeypatch, mb: float) -> None:
    monkeypatch.setattr(shutil, "disk_usage", lambda path: Usage(10**12, 0, int(mb * 1e6)))


def run(tmp_path, folders):
    lines: list[str] = []
    switch = Switch(tmp_path / "no switch here.txt")
    code = build("test", folders, 1, say=lines.append, switch=switch)
    return code, lines


def test_a_build_with_too_little_space_stops_before_its_first_stage(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    fake_free(monkeypatch, 5)
    code, lines = run(tmp_path, DataFolders(data, "a test"))
    assert code == 1
    assert "The build stopped." in lines[-1] and "MB free" in lines[-1] and "biggest being" in lines[-1]
    assert not (data / "tobymap").exists()


def test_a_data_folder_that_does_not_exist_stops_the_build_naming_its_setting(tmp_path):
    code, lines = run(tmp_path, DataFolders(tmp_path / "gone", "the --data option"))
    assert code == 1
    text = lines[-1]
    assert "set by the --data option" in text and "cannot be reached" in text
    assert "MAPDATA_ROOT" in text and "paths.yaml" in text
    assert not (tmp_path / "gone").exists()


def test_the_estimate_grows_with_the_area_and_is_zero_when_nothing_is_to_run():
    world = load_pack("world")
    trial = load_pack("trial-western-europe")
    kinds = [s["stage"] for s in world.stages]
    assert space.pack_area_mkm2(world) == space.EARTH_MKM2
    assert 5 < space.pack_area_mkm2(trial) < 15
    assert space.estimate_mb(world, kinds) > 5 * space.estimate_mb(trial, [s["stage"] for s in trial.stages])
    assert space.estimate_mb(world, []) == 0
    assert space.estimate_mb(world, kinds[:2]) < space.estimate_mb(world, kinds)


def test_a_pack_made_from_samples_needs_only_the_fixed_parts():
    test = load_pack("test")
    assert space.pack_area_mkm2(test) == 0
    assert space.estimate_mb(test, [s["stage"] for s in test.stages]) < 2000


def test_finished_stages_need_no_space(monkeypatch):
    world = load_pack("world")
    fake_free(monkeypatch, 10)
    space.stop_if_too_little(world, [], space.Path("."))   # nothing to run: no stop
    with pytest.raises(BuildStopped):
        space.stop_if_too_little(world, ["osm-areas"], space.Path("."))


def test_check_says_the_estimate_for_a_pack(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    fake_free(monkeypatch, 3)
    lines: list[str] = []
    assert check(DataFolders(data, "a test"), "world", say=lines.append) == 1
    assert any("needs about" in t and "only 3 MB is free" in t for t in lines)
