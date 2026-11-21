"""Shared test set-up.

Rules this file enforces (architecture 3.5):

1. No window ever opens: QT_QPA_PLATFORM is forced to "offscreen" before
   anything imports PySide6.
2. No network connection is opened: sockets are blocked, except for the local
   web server the browser tests start (tests/web has its own conftest).
3. No audio device is opened: audio backends take a stand-in engine. There are
   none yet; the guard is added with the first backend.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import pytest  # noqa: E402


def _build_pack(tmp_path_factory, name: str, config_dir: Path | None = None) -> Path:
    from mapdata.paths import CONFIG_DIR, DataFolders
    from mapdata.pipeline.build import build
    from mapdata.pipeline.switch import Switch

    data = tmp_path_factory.mktemp("data")
    lines: list[str] = []
    switch = Switch(data.parent / "no switch here.txt")  # never the data manager's own continue.txt
    assert build(name, DataFolders(data, "a test"), say=lines.append, switch=switch,
                 config_dir=config_dir or CONFIG_DIR) == 0, "\n".join(lines)
    return data / "tobymap" / "output" / name / f"{name}.pack"


@pytest.fixture(scope="session")
def test_pack(tmp_path_factory) -> Path:
    """The test pack, built once per test run from the samples in tests/samples (architecture 11.1)."""
    return _build_pack(tmp_path_factory, "test")


@pytest.fixture(scope="session")
def continents_pack(tmp_path_factory) -> Path:
    """The test pack with the continents stage, built once per run, for the world tree (P3-T9a). The plain
    test pack has no continents, and adding them changed 88 other tests."""
    return _build_pack(tmp_path_factory, "test-continents")


@pytest.fixture(scope="session")
def test_region_pack(tmp_path_factory, test_pack) -> Path:
    """The regional test pack, test-region (P4-T1, design 5.4), built once per run from the samples, after the test
    pack. Its settings are read from a copy of mapdata/config in which the world-pack source is the test pack just
    built, so its match stage (P4-T1h) gives features the test pack's identifiers."""
    import shutil

    import yaml

    from mapdata.paths import CONFIG_DIR

    config = tmp_path_factory.mktemp("config") / "config"
    shutil.copytree(CONFIG_DIR, config, ignore=shutil.ignore_patterns("paths.yaml", "__pycache__"))
    sources = yaml.safe_load((config / "sources.yaml").read_text(encoding="utf-8"))
    world = sources["sources"]["world-pack"]
    world.pop("find", None)
    world["repo"] = str(test_pack)   # an absolute path: the repository's folder joined to it is the path itself
    (config / "sources.yaml").write_text(yaml.safe_dump(sources, allow_unicode=True, sort_keys=False),
                                         encoding="utf-8")
    return _build_pack(tmp_path_factory, "test-region", config)
