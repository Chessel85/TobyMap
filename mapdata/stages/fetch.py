"""mapdata fetch: download sources into the data folder's own downloads folder (architecture 8.1).

Only ever writes inside <data folder>/tobymap/downloads (DP75). A download goes
to a ".part" file first and is renamed when complete, so an interrupted
download is never mistaken for a finished one. Progress is printed as plain
lines, at most one every 10 seconds (DMT-2).
"""
from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Source:
    key: str
    url: str
    folder: str
    licence: str
    note: str


SOURCES = {
    "land-polygons": Source(
        "land-polygons",
        "https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip",
        "osm-land-polygons",
        "ODbL 1.0, OpenStreetMap contributors",
        "OSM land polygons, split into small pieces, in longitude and latitude (AD-15).",
    ),
    "naturalearth-countries-110m": Source(
        "naturalearth-countries-110m",
        "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson",
        "naturalearth",
        "Public domain",
        "Natural Earth countries at 1:110 million, for the globe spike.",
    ),
}


def fetch(source: Source, downloads: Path, say=print, clock=time.monotonic) -> Path:
    target_dir = downloads / source.folder
    target = target_dir / source.url.rsplit("/", 1)[1]
    if target.is_file():
        say(f"{source.key}: already downloaded, {target}, {target.stat().st_size // (1024 * 1024)} MB.")
        return target
    target_dir.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    say(f"{source.key}: downloading {source.url}")
    say(f"Licence: {source.licence}.")
    request = urllib.request.Request(source.url, headers={"User-Agent": "TobyMap mapdata"})
    with urllib.request.urlopen(request, timeout=120) as response, open(part, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done, last = 0, clock()
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if clock() - last >= 10:
                last = clock()
                share = f", {done * 100 // total} percent" if total else ""
                say(f"{source.key}: {done // (1024 * 1024)} MB{share}.")
    if total and done != total:
        raise RuntimeError(f"{source.key}: download incomplete, {done} of {total} bytes. Run fetch again.")
    part.replace(target)
    say(f"{source.key}: finished, {target}, {done // (1024 * 1024)} MB.")
    return target
