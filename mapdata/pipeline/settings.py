"""The settings files (architecture 8.4, DMT-1, DMT-6).

* mapdata/config/sources.yaml: every source, with where it comes from, its
  licence, attribution and refresh interval.
* mapdata/config/layers/<group>.yaml: the layer definitions, one file per
  group of layers.
* mapdata/config/packs/<pack>.yaml: one file per pack: its name, version,
  layer groups, and the stages that build it, in order.

The reference for every setting is docs/data-manager/configuration.md.
A source with no licence stops the build before any work, naming the source
(DMT-6).
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from mapdata.paths import CONFIG_DIR, DataFolders
from mapdata.pipeline.errors import BuildStopped

REPO = CONFIG_DIR.parent.parent


@dataclass
class Source:
    key: str
    name: str
    licence: str
    attribution: str
    about: str = ""
    url: str | None = None          # downloaded by mapdata fetch
    file: str | None = None         # where the download is kept, inside the downloads folder
    find: list[str] = field(default_factory=list)  # a local copy in the data folder, newest first
    repo: str | None = None         # a file or folder in the repository, such as the test samples
    date: str | None = None         # the data's own date, YYYY-MM-DD, when the file's date is not it
    refresh_days: int | None = None

    def path(self, folders: DataFolders | None) -> Path | None:
        """Where the source's file is, or None if it is not there yet."""
        if self.repo:
            p = REPO / self.repo
            return p if p.exists() else None
        if folders is None:
            return None
        if self.file:
            p = folders.downloads / self.file
            if p.exists():
                return p
        found = []
        for pattern in self.find:
            found += [Path(p) for p in glob.glob(str(folders.root / pattern))]
        if found:
            return max(found, key=lambda p: (file_date(p), p.name))
        return None

    def data_date(self, path: Path) -> str:
        return self.date or file_date(path)

    def fingerprint(self, path: Path) -> str:
        """What a stage's fingerprint uses for the source. Files in the repository are small, so their
        bytes are used; downloads are large, so their size and date."""
        h = hashlib.sha256(self.key.encode())
        if self.repo:
            files = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
            for p in files:
                h.update(p.relative_to(path).as_posix().encode() if path.is_dir() else b"")
                h.update(p.read_bytes().replace(b"\r\n", b"\n"))
        else:
            st = path.stat()
            h.update(f"{path.name}-{st.st_size}-{st.st_mtime_ns}".encode())
        return h.hexdigest()


def file_date(path: Path) -> str:
    """A file's date, YYYY-MM-DD: from its name if it has one, such as planet-2026-10-26.gol, otherwise
    from when it was last changed."""
    import re

    m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(path).name)
    if m:
        return m.group(1)
    return dt.datetime.fromtimestamp(Path(path).stat().st_mtime, dt.timezone.utc).date().isoformat()


def _read(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BuildStopped(f"The settings file {path} is missing.") from None
    except yaml.YAMLError as exc:
        raise BuildStopped(f"The settings file {path} cannot be read: {exc}. Correct it, then run again.") from None
    if not isinstance(data, dict):
        raise BuildStopped(f"The settings file {path} is empty or not laid out as settings.")
    return data


SOURCE_FIELDS = {"name", "licence", "attribution", "about", "url", "file", "find", "repo", "date", "refresh_days"}


def load_sources(config_dir: Path = CONFIG_DIR) -> dict[str, Source]:
    """Every source in sources.yaml. A source with no licence or attribution stops here (DMT-6)."""
    path = config_dir / "sources.yaml"
    data = _read(path).get("sources") or {}
    out = {}
    for key, s in data.items():
        s = s or {}
        unknown = sorted(set(s) - SOURCE_FIELDS)
        if unknown:
            raise BuildStopped(f"The source {key} in {path.name} has a setting mapdata does not know: "
                               f"{', '.join(unknown)}. Check the spelling against docs/data-manager/configuration.md.")
        for needed in ("licence", "attribution"):
            if not str(s.get(needed) or "").strip():
                raise BuildStopped(f"The source {key} has no {needed} in {path.name}, so nothing can be built "
                                   f"(DMT-6). Add its {needed}, then build again.")
        if not s.get("name"):
            raise BuildStopped(f"The source {key} has no name in {path.name}. Add one, then build again.")
        if not (s.get("url") or s.get("find") or s.get("repo")):
            raise BuildStopped(f"The source {key} in {path.name} says neither where to download it (url), "
                               "where to find a local copy (find), nor where it is in the repository (repo).")
        if s.get("date") is not None:
            s["date"] = str(s["date"])
        out[key] = Source(key=key, **{k: v for k, v in s.items()})
    return out


@dataclass(frozen=True)
class Layer:
    id: str
    name: str
    rank: int
    kind: str  # land or water


def load_layers(groups: list[str], config_dir: Path = CONFIG_DIR) -> dict[str, Layer]:
    out: dict[str, Layer] = {}
    for group in groups:
        path = config_dir / "layers" / f"{group}.yaml"
        for item in _read(path).get("layers") or []:
            for needed in ("id", "name", "rank", "kind"):
                if needed not in item:
                    raise BuildStopped(f"A layer in {path.name} has no {needed}. Add it, then build again.")
            if item["kind"] not in ("land", "water"):
                raise BuildStopped(f"The layer {item['id']} in {path.name} has kind {item['kind']}; "
                                   "use land or water.")
            if item["id"] in out:
                raise BuildStopped(f"The layer {item['id']} is defined twice. Keep one, then build again.")
            out[item["id"]] = Layer(item["id"], item["name"], int(item["rank"]), item["kind"])
    return out


@dataclass
class PackSettings:
    name: str
    path: Path
    data: dict
    stages: list[dict]
    layers: dict[str, Layer]
    sources: dict[str, Source]   # the sources this pack uses, in the order first named

    @property
    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")


PACK_NEEDS = ("name", "title", "version", "app_versions", "coverage", "layer_groups", "stages")


def load_pack(name: str, config_dir: Path = CONFIG_DIR) -> PackSettings:
    path = config_dir / "packs" / f"{name}.yaml"
    if not path.is_file():
        known = sorted(p.stem for p in (config_dir / "packs").glob("*.yaml"))
        raise BuildStopped(f"There is no pack called {name}. The packs are: {', '.join(known) or 'none'}. "
                           "Each is a file in mapdata/config/packs.")
    data = _read(path)
    missing = [k for k in PACK_NEEDS if k not in data]
    if missing:
        raise BuildStopped(f"The pack settings {path.name} have no {', '.join(missing)}. Add them, then build again.")
    if data["name"] != name:
        raise BuildStopped(f"The pack settings {path.name} give the name {data['name']}; it must match the file "
                           f"name, {name}.")
    all_sources = load_sources(config_dir)
    layers = load_layers(list(data["layer_groups"]), config_dir)
    used: dict[str, Source] = {}
    stages = []
    for n, stage in enumerate(data["stages"], 1):
        if not isinstance(stage, dict) or "stage" not in stage:
            raise BuildStopped(f"Stage {n} in {path.name} has no 'stage:' line naming what it does.")
        stages.append(stage)
        for key in stage_sources(stage):
            if key not in all_sources:
                raise BuildStopped(f"Stage {n}, {stage['stage']}, in {path.name} uses the source {key}, which is "
                                   "not in sources.yaml. Add the source there, with its licence, then build again.")
            used.setdefault(key, all_sources[key])
    return PackSettings(name, path, data, stages, layers, used)


def stage_sources(stage: dict) -> list[str]:
    """The source keys a stage's settings name: "source", "sources", and "source" inside "samples"."""
    keys = []
    if stage.get("source"):
        keys.append(stage["source"])
    keys += list(stage.get("sources") or [])
    keys += [s["source"] for s in stage.get("samples") or [] if isinstance(s, dict) and s.get("source")]
    return keys
