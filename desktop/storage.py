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
PACKS_KEY = "packs_folder"   # in settings.json: the packs folder you chose, when not the default (P4-T6b, AD-18)


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


def packs_folder(folder: Path | None = None) -> Path:
    """The packs folder in use: the one chosen in the settings (P4-T6b; P4-T6g lets you move it), else the
    default one in the application data folder. Downloads go here."""
    chosen = load(folder).get(PACKS_KEY)
    return Path(chosen) if isinstance(chosen, str) and chosen else pack_folder(folder)


def set_packs_folder(path: Path | None, folder: Path | None = None) -> None:
    """Choose the packs folder, or None for the default. The rest of the settings are kept."""
    data = load(folder)
    if path is None:
        data.pop(PACKS_KEY, None)
    else:
        data[PACKS_KEY] = str(path)
    save(data, folder, keep_packs_folder=False)


def find_packs(folder: Path | None = None, override: str | None = None) -> list[Path]:
    """The pack files to open: TOBYMAP_PACKS if set, else the packs folder."""
    given = override if override is not None else os.environ.get(PACK_ENV)
    if given:
        path = Path(given)
        return [path] if path.is_file() else sorted(path.glob("*.pack"))
    return sorted(packs_folder(folder).glob("*.pack"))


def set_aside_pack(path: Path) -> Path | None:
    """A damaged pack renamed, never deleted: name.pack.damaged, or .damaged-2 and so on when taken, so
    find_packs no longer sees it. Returns the new name, or None when the file is not there."""
    path = Path(path)
    if not path.is_file():
        return None
    aside = path.with_name(path.name + ".damaged")
    n = 2
    while aside.exists():
        aside = path.with_name(f"{path.name}.damaged-{n}")
        n += 1
    os.replace(path, aside)
    return aside


def load(folder: Path | None = None) -> dict:
    """The saved settings, keys and place. A missing or damaged file gives nothing, and the defaults are used."""
    try:
        data = json.loads(settings_file(folder).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data: dict, folder: Path | None = None, keep_packs_folder: bool = True) -> Path:
    """The settings written. The packs folder chosen is the desktop's own, not the core's, so it is kept
    when the data has none, as when the session saves or settings are imported."""
    if keep_packs_folder and PACKS_KEY not in data:
        chosen = load(folder).get(PACKS_KEY)
        if chosen:
            data = {**data, PACKS_KEY: chosen}
    path = settings_file(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)
    return path


# The bookmarks file (P4-T8a, USR-5, DP219) ---------------------------------------------------------
# All the bookmark lists, in one GeoJSON file beside settings.json. The core makes its text; this only
# reads and writes it. Reset all settings never touches it (DP209).

def bookmarks_file(folder: Path | None = None) -> Path:
    return Path(folder or app_data_folder()) / "bookmarks.geojson"


def load_bookmarks(folder: Path | None = None) -> str | None:
    """The bookmarks file's text, for the core to read, or None when there is none yet. Bytes that are not
    UTF-8 are passed on as they are, marked, so the core finds the file damaged and it is set aside."""
    try:
        return bookmarks_file(folder).read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None


def save_bookmarks(text: str, folder: Path | None = None) -> Path:
    """Written safely, so a crash never loses the bookmarks: the new text goes to a temporary file beside
    the old one, which is flushed to the disk, and then put in the old one's place in one step."""
    path = bookmarks_file(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    return path


def set_aside_bookmarks(folder: Path | None = None) -> Path | None:
    """A damaged bookmarks file renamed, so it is kept: bookmarks-damaged.geojson, or -2, -3 and so on
    when that is taken. Returns the new name, or None when there was no file."""
    path = bookmarks_file(folder)
    if not path.is_file():
        return None
    aside = path.with_name("bookmarks-damaged.geojson")
    n = 2
    while aside.exists():
        aside = path.with_name(f"bookmarks-damaged-{n}.geojson")
        n += 1
    os.replace(path, aside)
    return aside


def export_to(data: dict, target: Path) -> None:
    """Settings to a file you choose, to keep or move to another computer (PLT-5)."""
    Path(target).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def import_from(source: Path) -> dict:
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("not a TobyMap settings file")
    return data
