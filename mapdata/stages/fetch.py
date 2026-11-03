"""mapdata fetch: download sources into the data folder's own downloads folder (architecture 8.1, UX 16).

The sources are in mapdata/config/sources.yaml. Only ever writes inside
<data folder>/tobymap/downloads (DP75), and records each file it makes
(DMT-7). A download goes to a ".part" file first and is renamed when
complete, so an interrupted download is never mistaken for a finished one.
Progress is printed as plain lines, at most one every 10 seconds (DMT-2).
"""
from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Source:
    """A download with its own folder, for the tests; the pipeline's sources come from sources.yaml."""
    key: str
    url: str
    folder: str
    licence: str
    note: str

    @property
    def file(self) -> str:
        return f"{self.folder}/{self.url.rsplit('/', 1)[1]}"


def fetch(source, downloads: Path, say=print, clock=time.monotonic, claim=lambda p: p) -> Path:
    target = downloads / source.file
    if target.is_file():
        say(f"{source.key}: already downloaded, {target}, {target.stat().st_size // (1024 * 1024)} MB.")
        return target
    part = claim(target.with_name(target.name + ".part"))
    claim(target)
    target.parent.mkdir(parents=True, exist_ok=True)
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


def fetch_sources(keys: list[str], sources: dict, folders, say=print, clock=time.monotonic) -> int:
    """Fetch each source, or find its local copy: one plain line per source, then a summary (UX 16).

    Returns the number of sources still missing.
    """
    import datetime as dt

    from mapdata.pipeline.ledger import Ledger
    from mapdata.pipeline.settings import file_date

    ledger = Ledger(folders.own)
    ready, missing = [], []
    for key in keys:
        s = sources[key]
        path = s.path(folders)
        if s.repo:
            if path is None:
                say(f"{key}: missing from the repository, {s.repo}. Get a fresh copy of the repository.")
                missing.append(key)
            else:
                say(f"{key}: in the repository, {s.repo}, dated {s.data_date(path)}. Licence: {s.licence}.")
                ready.append(key)
            continue
        if path is None and s.file and s.url:
            try:
                path = fetch(s, folders.downloads, say, clock, ledger.claim)
            except (OSError, RuntimeError) as exc:
                say(f"{key}: the download failed: {exc}. Check the internet connection, then run fetch again.")
                missing.append(key)
                continue
        elif path is None:
            say(f"{key}: no local copy found in the data folder. It is not downloaded automatically, as it is "
                f"very large. Download it by hand from {s.url}. mapdata looks for: {', '.join(s.find)}.")
            missing.append(key)
            continue
        else:
            say(f"{key}: using {path}, dated {s.data_date(path)}. Licence: {s.licence}.")
        ready.append(key)
        if s.refresh_days:
            age = (dt.date.today() - dt.date.fromisoformat(file_date(path))).days
            if age > s.refresh_days:
                say(f"{key}: it is {age} days old, and its refresh interval is {s.refresh_days} days, "
                    "so a newer copy is due.")
    word = "source" if len(keys) == 1 else "sources"
    tail = f"; missing: {', '.join(missing)}." if missing else "."
    say(f"Summary: {len(ready)} of {len(keys)} {word} ready{tail}")
    return len(missing)
