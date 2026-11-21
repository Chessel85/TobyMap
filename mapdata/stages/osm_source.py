"""One way to read OpenStreetMap for the regional pack's stages (P4-T1a, design docs/plan/p4-t1-design.md 3.4).

Every new stage that reads OpenStreetMap (local-areas, osm-water, osm-waterways, osm-streets, osm-land, osm-pois)
reads it through this module, from the planet file (a GeoDesk library) or from the raw samples in the repository
(tests/samples/osm-raw), behind one small interface:

* open_source(ctx, key) or open_path(path): a source whose query(goql, box) yields OsmObject: id ("osm:w123"),
  kind (node, way or area), tags (a dict of strings) and shape (Shapely, in degrees, as GeoDesk's from_mercator
  gives it).
* The query language is the part of GeoDesk's that the stages use: the types n, w and a and their combinations
  (such as na), then filters [key], [!key], [key=a,b], [key!=a,b] and [key>=n]; several such queries may be joined
  with commas. As in GeoDesk, [key] means the tag is there with a value other than "no", and [!key] that it is not.
  Anything else is refused with a clear message, from the planet file too, so no stage can use a query the samples
  do not understand.
* run_reading(ctx, module, request): the reading in a short-lived process, as GeoDesk keeps the memory it maps until
  the process ends. It writes request.json in the stage's folder, then runs "python -m mapdata read-osm <folder>",
  which imports the module named and calls its read_job(source, request, out_folder). With a raw sample, read_job
  runs in the same process. The request carries the coverage's reading boxes (its pack tiles at tile level 8): a
  read_job reads one reading box at a time, with source.query(goql, box, seen), and saves each box's results with
  save_box before the next, so no reading process holds all of Great Britain's streets at once.
* clip_to_coverage(records, geoms, coverage): each shape cut to the coverage, empty ones dropped, partial marked.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

import shapely

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped
from mapdata.stages import coverage as coveragemod

REQUEST = "request.json"
READ_FOLDER = "read"
FINISHED = "finished.json"
READ_VERSION = 1
KINDS = {"n": "node", "w": "way", "a": "area"}


# The query language ---------------------------------------------------------------------------------------------

class QueryRefused(BuildStopped):
    """A query in a form the raw samples' matcher does not understand."""


@dataclass(frozen=True)
class Filter:
    op: str            # has, not, eq, ne, ge
    key: str
    values: tuple = ()


@dataclass(frozen=True)
class Selector:
    kinds: frozenset
    filters: tuple


_KEY = r"[A-Za-z0-9_:\-\.]+"
_VALUE = r"(?:\"[^\"]*\"|'[^']*'|[^,\]\"']+)"
_FILTER = re.compile(
    rf"^\s*(?:(?P<not>!)\s*(?P<nkey>{_KEY})|(?P<key>{_KEY})\s*(?:(?P<op>!=|>=|=)\s*(?P<vals>{_VALUE}(?:\s*,\s*{_VALUE})*))?)\s*$")


def _unquote(v: str) -> str:
    v = v.strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def _split_top(text: str) -> list[str]:
    """The comma-separated queries of a query, commas inside brackets or quotes left alone."""
    out, depth, quote, start = [], 0, None, 0
    for i, ch in enumerate(text):
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append(text[start:i])
            start = i + 1
    out.append(text[start:])
    return out


def parse_query(goql: str) -> tuple[Selector, ...]:
    """A query in the part of GeoDesk's query language the stages use. Refuses anything else, naming it."""
    def refuse(why: str):
        raise QueryRefused(f"The query {goql} cannot be used: {why}. The stages' queries use only the types n, w "
                           "and a, and the filters [key], [!key], [key=a,b], [key!=a,b] and [key>=number] "
                           "(mapdata/stages/osm_source.py).")

    selectors = []
    for part in _split_top(goql):
        part = part.strip()
        m = re.match(r"^([A-Za-z*]+)", part)
        if not m:
            refuse(f"'{part}' does not start with the types n, w or a")
        letters = m.group(1)
        if any(ch not in KINDS for ch in letters):
            refuse(f"the types '{letters}' are not only n, w and a (relations and * are not read)")
        rest = part[m.end():]
        filters = []
        while rest.strip():
            fm = re.match(r"^\s*\[([^\]]*)\]", rest)
            if not fm:
                refuse(f"'{rest.strip()}' is not a filter in square brackets")
            body = fm.group(1)
            f = _FILTER.match(body)
            if not f:
                refuse(f"the filter [{body}] is not one of the forms understood")
            if f.group("not"):
                filters.append(Filter("not", f.group("nkey")))
            elif not f.group("op"):
                filters.append(Filter("has", f.group("key")))
            else:
                vals = tuple(_unquote(v) for v in re.findall(_VALUE, f.group("vals")) if v.strip())
                if any("*" in v for v in vals):
                    refuse(f"the filter [{body}] uses a wildcard")
                op = {"=": "eq", "!=": "ne", ">=": "ge"}[f.group("op")]
                if op == "ge":
                    if len(vals) != 1 or _number(vals[0]) is None:
                        refuse(f"the filter [{body}] needs one number after >=")
                filters.append(Filter(op, f.group("key"), vals))
            rest = rest[fm.end():]
        selectors.append(Selector(frozenset(KINDS[ch] for ch in letters), tuple(filters)))
    return tuple(selectors)


def _number(value) -> float | None:
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)", str(value))
    return float(m.group(1)) if m else None


def _passes(f: Filter, tags: dict) -> bool:
    value = tags.get(f.key)
    if f.op == "has":
        return value is not None and value != "no"
    if f.op == "not":
        return value is None or value == "no"
    if f.op == "eq":
        return value is not None and value in f.values
    if f.op == "ne":
        return value is None or value not in f.values
    n = _number(value) if value is not None else None
    return n is not None and n >= float(f.values[0])


def matches(selectors: tuple[Selector, ...], kind: str, tags: dict) -> bool:
    return any(kind in s.kinds and all(_passes(f, tags) for f in s.filters) for s in selectors)


# The sources ----------------------------------------------------------------------------------------------------

@dataclass
class OsmObject:
    id: str          # "osm:n123", "osm:w123" or "osm:r123"
    kind: str        # node, way or area
    tags: dict       # every tag, as strings
    shape: object    # Shapely, in degrees


def _box_meets(bounds, box) -> bool:
    return not (bounds[2] < box[0] or bounds[0] > box[2] or bounds[3] < box[1] or bounds[1] > box[3])


class RawSamples:
    """The raw samples (tests/samples/osm-raw): GeoJSON FeatureCollections whose features' properties are osm
    ("n123", "w123" or "r123"), kind and tags. An object in two sample files is read once."""

    planet = False

    def __init__(self, path: Path, say=print):
        self.path = Path(path)
        self.say = say
        files = sorted(self.path.glob("*.geojson")) if self.path.is_dir() else [self.path]
        held: dict[str, OsmObject] = {}
        for p in files:
            data = json.loads(p.read_text(encoding="utf-8"))
            for f in data.get("features") or []:
                props = f.get("properties") or {}
                oid = f"osm:{props['osm']}"
                if oid in held:
                    continue
                held[oid] = OsmObject(oid, props["kind"], dict(props.get("tags") or {}),
                                      shapely.from_geojson(json.dumps(f["geometry"])))
        self.objects = [held[k] for k in sorted(held)]
        self.bounds = shapely.bounds([o.shape for o in self.objects]) if self.objects else []

    def query(self, goql: str, box=None, seen: set | None = None):
        selectors = parse_query(goql)
        for o, b in zip(self.objects, self.bounds):
            if box is not None and not _box_meets(b, box):
                continue
            if seen is not None and o.id in seen:
                continue
            if matches(selectors, o.kind, o.tags):
                if seen is not None:
                    seen.add(o.id)
                yield o


class Planet:
    """The planet file, a GeoDesk library, read in the short-lived process only."""

    planet = True

    def __init__(self, path: Path, say=print):
        import geodesk

        self.path = Path(path)
        self.say = say
        self._geodesk = geodesk
        self.world = geodesk.Features(str(path))

    def query(self, goql: str, box=None, seen: set | None = None):
        parse_query(goql)   # the same queries as the samples, or none
        gd = self._geodesk
        sel = self.world(goql)
        if box is not None:
            sel = sel(gd.Box(west=box[0], south=box[1], east=box[2], north=box[3]))
        for f in sel:
            if f.is_node:
                kind, letter = "node", "n"
            elif f.is_way:
                kind, letter = ("area" if f.is_area else "way"), "w"
            elif f.is_area:
                kind, letter = "area", "r"
            else:
                continue   # a relation that is not an area has no shape
            oid = f"osm:{letter}{f.id}"
            if seen is not None:
                if oid in seen:
                    continue
                seen.add(oid)
            g = gd.from_mercator(f.shape)
            if g is None or g.is_empty:
                continue
            yield OsmObject(oid, kind, {str(k): str(v) for k, v in dict(f.tags).items()}, g)


def open_path(path: Path, say=print):
    """The planet file (.gol) or raw samples (a .geojson file, or a folder of them) at path."""
    path = Path(path)
    if path.suffix.lower() == ".gol":
        return Planet(path, say)
    if path.is_dir() or path.suffix.lower() == ".geojson":
        return RawSamples(path, say)
    raise BuildStopped(f"{path} is neither a GeoDesk library (.gol) nor raw samples (.geojson), so OpenStreetMap "
                       "cannot be read from it.")


def open_source(ctx, key: str):
    """The source named key in the pack's sources, opened in this process. Only raw samples should be: the planet
    file is read with run_reading, in its own process."""
    _source, path = ctx.source(key)
    return open_path(path, ctx.progress.line)


def is_planet(path: Path) -> bool:
    return Path(path).suffix.lower() == ".gol"


# Reading, a reading box at a time -------------------------------------------------------------------------------

def coverage_of(ctx) -> coveragemod.Coverage:
    folder = ctx.earlier.get("coverage")
    if folder is None:
        raise BuildStopped(f"The stage {ctx.settings['stage']} reads OpenStreetMap within the coverage, but no "
                           "coverage stage ran before it. Put the coverage stage after the join (or the samples).")
    return coveragemod.load(folder)


def run_reading(ctx, module: str, request: dict, source_key: str | None = None) -> Path:
    """Run module's read_job(source, request, out_folder) on the source (the stage's setting "source", or
    source_key), in its own process for the planet file, in this one for raw samples. The request is given the
    source's path, the coverage (its file and reading boxes) and the data folder's own folder, so read_job can claim
    what it writes. Returns the folder read_job wrote into, whose files are in the ledger."""
    key = source_key or ctx.settings.get("source") or "planet"
    _source, path = ctx.source(key)
    cov_folder = ctx.earlier.get("coverage")
    cov = coverage_of(ctx)
    name = module if module.startswith("mapdata.stages.") else f"mapdata.stages.{module}"
    full = {**request, "module": name, "source_key": key, "source_path": str(path),
            "coverage": str(Path(cov_folder) / coveragemod.COVERAGE_FILE),
            "reading_boxes": coveragemod.reading_boxes(cov.tiles),
            "own": str(ctx.folders.own) if ctx.folders is not None else "", "version": READ_VERSION}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(full, indent=1), encoding="utf-8", newline="\n")
    out = ctx.folder / READ_FOLDER
    if not is_planet(path):
        ctx.progress.line(f"Reading {Path(path).name} in this process, {len(full['reading_boxes'])} reading boxes.")
        _run(ctx.folder, say=ctx.progress.line)
        return out
    ctx.progress.line(f"Reading from the planet file {Path(path).name} in a separate process, which ends when it has "
                      f"finished: {len(full['reading_boxes'])} reading boxes.")
    cmd = [sys.executable, "-m", "mapdata"]
    if ctx.folders is not None:
        cmd += ["--data", str(ctx.folders.root)]
    done = subprocess.Popen([*cmd, "read-osm", str(ctx.folder)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace")
    for line in done.stdout:   # each line as it comes, so a long read is seen to move (DMT-2)
        ctx.progress.line(line.rstrip())
    err = done.stderr.read()
    if done.wait() != 0 or not (out / FINISHED).is_file():
        raise BuildStopped(f"Reading from the planet file for the stage {ctx.settings['stage']} failed. The end of "
                           "its output was: " + " ".join((err or "").splitlines()[-5:]))
    return out


def _run(folder: Path, say=print) -> int:
    request = json.loads((Path(folder) / REQUEST).read_text(encoding="utf-8"))
    name = request["module"]
    if not name.startswith("mapdata.stages."):
        raise BuildStopped(f"read-osm runs only the stages' own modules, not {name}.")
    module = import_module(name)
    out = Path(folder) / READ_FOLDER
    claim = claimer(request)
    if out.is_dir():   # a reading stopped part-way: started again from the first reading box
        for p in sorted(out.rglob("*"), reverse=True):
            if p.is_file():
                claim(p)
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    source = open_path(Path(request["source_path"]), say)
    module.read_job(source, request, out)
    claim(out / FINISHED).write_text(json.dumps({"module": name}) + "\n", encoding="utf-8", newline="\n")
    return 0


def main(folder: Path) -> int:
    """The entry point of the short-lived process: "mapdata read-osm <folder>"."""
    def say(text):
        print(text, flush=True)

    return _run(Path(folder), say)


def claimer(request: dict):
    """A function that claims a path in the data folder's list of created files (DMT-7) before it is written."""
    own = request.get("own")
    if not own:
        return lambda p: Path(p)
    from mapdata.pipeline.ledger import Ledger

    ledger = Ledger(Path(own))
    return ledger.claim


def box_folder(out: Path, n: int) -> Path:
    return Path(out) / f"box-{n:04d}"


def save_box(request: dict, out: Path, n: int, records: list[dict], geoms: list) -> Path:
    """One reading box's results, saved before the next box is read: records and shapes, as a stage keeps them."""
    folder = box_folder(out, n)
    claim = claimer(request)
    folder.mkdir(parents=True, exist_ok=True)
    features.save(folder, records, geoms, claim)
    return folder


def load_boxes(out: Path) -> tuple[list[dict], list]:
    """Every reading box's results, in box order."""
    records, geoms = [], []
    for folder in sorted(Path(out).glob("box-*")):
        r, g = features.load(folder)
        records += r
        geoms += g
    return records, geoms


def load_request_coverage(request: dict) -> coveragemod.Coverage:
    return coveragemod.load(Path(request["coverage"]))


def clip_to_coverage(records: list[dict], geoms: list, coverage) -> tuple[list[dict], list, dict]:
    """Each shape cut to the coverage (a Coverage, or its shape): empty ones dropped, and partial: true on each left
    with less than 99.9 percent of its area or length. Returns the records, the shapes, and counts: kept, partial,
    dropped."""
    shape = coverage.shape if isinstance(coverage, coveragemod.Coverage) else coverage
    return coveragemod.cut_to_coverage(records, geoms, shape)
