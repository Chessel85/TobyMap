"""AD-18 and DMT-7: the data folder is a setting, never a built-in drive letter."""
from pathlib import Path

import pytest

from mapdata.__main__ import main
from mapdata.paths import ENV_VAR, DataFolderNotSet, resolve_data_folder


def test_command_line_wins(tmp_path):
    local = tmp_path / "paths.yaml"
    local.write_text("data_folder: from_file\n", encoding="utf-8")
    folders = resolve_data_folder("from_cli", {ENV_VAR: "from_env"}, local)
    assert folders.root == Path("from_cli")
    assert folders.where_from == "the --data option"


def test_environment_beats_local_file(tmp_path):
    local = tmp_path / "paths.yaml"
    local.write_text("data_folder: from_file\n", encoding="utf-8")
    folders = resolve_data_folder(None, {ENV_VAR: "from_env"}, local)
    assert folders.root == Path("from_env")


def test_local_file_used_last(tmp_path):
    local = tmp_path / "paths.yaml"
    local.write_text("# comment\ndata_folder: 'some folder'  # trailing\n", encoding="utf-8")
    folders = resolve_data_folder(None, {}, local)
    assert folders.root == Path("some folder")
    assert folders.downloads == Path("some folder") / "tobymap" / "downloads"
    assert folders.output == Path("some folder") / "tobymap" / "output"


def test_nothing_set_explains_how(tmp_path):
    with pytest.raises(DataFolderNotSet) as info:
        resolve_data_folder(None, {}, tmp_path / "missing.yaml")
    assert "--data" in str(info.value)
    assert ENV_VAR in str(info.value)
    assert "paths.example.yaml" in str(info.value)


def test_no_drive_letter_in_shared_code_or_config():
    """No drive letter or personal folder in mapdata's code or shared configuration."""
    root = Path(__file__).resolve().parents[2]
    offenders = []
    for path in list((root / "mapdata").rglob("*.py")) + list((root / "mapdata" / "config").rglob("*.yaml")):
        if path.name == "paths.yaml":  # the local file, not in git
            continue
        text = path.read_text(encoding="utf-8")
        for bad in ("E:\\", "E:/", "C:\\Users", "C:/Users"):
            if bad in text:
                offenders.append(f"{path.name}: {bad}")
    assert offenders == []


def test_status_reports_missing_setting(capsys, monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr("mapdata.paths.LOCAL_PATHS_FILE", tmp_path / "none.yaml")
    assert main(["status"]) == 2
    assert "not set" in capsys.readouterr().out


def test_status_reports_folders(capsys, tmp_path):
    (tmp_path / "tobymap" / "downloads").mkdir(parents=True)
    assert main(["--data", str(tmp_path), "status"]) == 0
    out = capsys.readouterr().out
    assert "Downloads folder" in out and "present" in out
    assert "Working folder" in out and "not created yet" in out
