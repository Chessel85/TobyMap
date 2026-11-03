"""mapdata check: is the data folder ready for a build? (architecture 8.1, UX 16, DMT-7)

Says whether the data folder can be reached, and stops there if it can't.
Then the free space on the drive of each of mapdata's folders; the planet
files and the land polygons, with their dates, and a warning if the planet
file used and the land polygons are far apart in date; and, given a pack,
whether its build fits in the free space.
"""
from __future__ import annotations

import datetime as dt
import glob
from pathlib import Path

from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.pipeline.build import free_mb
from mapdata.pipeline.settings import file_date, load_pack, load_sources

DAYS_APART = 14


def _date_words(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def check(folders: DataFolders, pack: str | None = None, say=print, config_dir: Path = CONFIG_DIR) -> int:
    """Returns 0 if ready, 1 if there is a warning, 2 if the data folder cannot be reached."""
    if not folders.root.is_dir():
        say(f"The data folder, {folders.root}, set by {folders.where_from}, cannot be reached. "
            "If it is on an external drive, connect the drive and run mapdata check again. Nothing else was checked.")
        return 2
    say(f"The data folder, {folders.root}, can be reached. It is set by {folders.where_from}.")
    warnings = 0
    for name, path in (("downloads", folders.downloads), ("working", folders.working), ("output", folders.output)):
        state = "" if path.is_dir() else ", not created yet"
        say(f"The {name} folder, {path}{state}: {free_mb(path) / 1000:,.1f} GB free on its drive.")

    sources = load_sources(config_dir)
    planet = sources["planet"]
    found = []
    for pattern in planet.find:
        found += [Path(p) for p in glob.glob(str(folders.root / pattern))]
    found = sorted(set(found), key=lambda p: (file_date(p), p.name), reverse=True)
    if found:
        for p in found:
            say(f"Planet file: {p.name}, dated {_date_words(file_date(p))}, {p.stat().st_size / 1e9:,.1f} GB.")
        say(f"Builds use the newest, {found[0].name}.")
    else:
        say(f"No planet file was found. mapdata looks for: {', '.join(planet.find)}.")
        warnings += 1
    land = sources["land-polygons"].path(folders)
    if land is None:
        say("The land polygons are not downloaded. Run: python -m mapdata fetch land-polygons")
        warnings += 1
    else:
        say(f"Land polygons: {land.name}, dated {_date_words(file_date(land))}.")
    if found and land is not None:
        apart = abs((dt.date.fromisoformat(file_date(found[0])) - dt.date.fromisoformat(file_date(land))).days)
        if apart > DAYS_APART:
            say(f"Warning: the planet file and the land polygons are {apart} days apart, so coasts and borders may "
                f"not match. Download whichever is older again, so they are within {DAYS_APART} days.")
            warnings += 1
        else:
            say(f"The planet file and the land polygons are {apart} days apart, which is close enough.")

    if pack:
        settings = load_pack(pack, config_dir)
        needed = float(settings.data.get("space_needed_mb", 100))
        free = free_mb(folders.own)
        if free < needed:
            say(f"Warning: the pack {pack} needs about {needed:,.0f} MB, and only {free:,.0f} MB is free. "
                "Free some space before building it.")
            warnings += 1
        else:
            say(f"The pack {pack} needs about {needed:,.0f} MB, which fits.")
    say("Ready to build." if not warnings else f"{warnings} warning{'s' if warnings != 1 else ''}, listed above.")
    return 1 if warnings else 0
