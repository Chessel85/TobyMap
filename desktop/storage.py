"""Where the desktop keeps your settings, your place and the packs (PLT-5, AD-18).

Everything is in your own application data folder, never in the program's
folder. Nothing here asks where the computer is (SCP-1).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PACK_ENV = "TOBYMAP_PACKS"   # a folder (or a pack file) to use instead of the default


def app_data_folder() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "TobyMap"


def settings_file(folder: Path | None = None) -> Path:
    return Path(folder or app_data_folder()) / "settings.json"


def pack_folder(folder: Path | None = None) -> Path:
    return Path(folder or app_data_folder()) / "packs"


def find_packs(folder: Path | None = None, override: str | None = None) -> list[Path]:
    """The pack files to open: TOBYMAP_PACKS if set, else the packs folder."""
    given = override if override is not None else os.environ.get(PACK_ENV)
    if given:
        path = Path(given)
        return [path] if path.is_file() else sorted(path.glob("*.pack"))
    return sorted(pack_folder(folder).glob("*.pack"))


def load(folder: Path | None = None) -> dict:
    """The saved settings, keys and place. A missing or damaged file gives nothing, and the defaults are used."""
    try:
        data = json.loads(settings_file(folder).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data: dict, folder: Path | None = None) -> Path:
    path = settings_file(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)
    return path


def export_to(data: dict, target: Path) -> None:
    """Settings to a file you choose, to keep or move to another computer (PLT-5)."""
    Path(target).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def import_from(source: Path) -> dict:
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("not a TobyMap settings file")
    return data
