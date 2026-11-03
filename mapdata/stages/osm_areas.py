"""Stage "osm-areas": read the countries and their divisions from the planet file (P1-T4, architecture 8.2 stages 1 and 4).

Reads, from the GeoDesk library of the planet file:

* every country, OSM level 2, with its outline checked to be closed
  (AD-15) and Antarctica's taken to the South Pole;
* the country units in mapdata/config/country_units.yaml (architecture 6.12);
* the divisions at the levels in the settings, 3, 4 and 5 for the base pack
  lite (DP114, DP116), each placed in the country holding a point inside it.

Areas held twice in one level of one country, such as Sevastopol, are kept
once and marked disputed (DP104). Every repair is listed in the log.

GeoDesk gives its memory back only when the process ends (spike S2), so the
reading is done in its own short-lived process: "mapdata read-planet", which
this stage starts and waits for.

Settings:

* source: the planet file's source key, planet.
* levels: the division levels to read, such as [3, 4, 5].
* box: optional, [west, south, east, north]. Only countries touching it, and
  divisions inside it, are read. Used for the detail trials and the timing
  run on one continent; the world build has no box.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import shapely
import yaml

from mapdata.paths import CONFIG_DIR
from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped

READ_VERSION = "osm-areas-1"
REQUEST = "request.json"


def english(area) -> str:
    return area.tags.get("name:en") or area.name


def record_of(area, kind: str, country: str | None) -> dict:
    tags = area.tags or {}
    r = {"id": area.id, "name": english(area), "local_name": area.name, "kind": kind, "level": area.level,
         "country": country}
    for key, out in (("ISO3166-1", "iso"), ("ISO3166-2", "iso2"), ("wikidata", "wikidata"),
                     ("unit_name", "unit_name"), ("unit_type", "unit_type"), ("sovereign", "sovereign")):
        if tags.get(key):
            r[out] = tags[key]
    if tags.get("disputed") == "yes":
        r["disputed"] = True
        r["also_held_as"] = tags["also_held_as"]
    return r


def outline_to_the_pole(geom):
    """An outline that goes all the way round the South Pole, taken to the pole (AD-15)."""
    west, south, east, _ = geom.bounds
    if south <= -89.999 or south > -80 or east - west < 359.9:
        return geom, None
    return shapely.union(geom, shapely.box(-180.0, -90.0, 180.0, south + 0.0005)), south


def read(gol: Path, levels: list[int], box: list[float] | None, say=print) -> tuple[list[dict], list]:
    """Everything the stage reads, as feature records and shapes. Runs in the short-lived process."""
    import geodesk

    from mapdata.stages import boundaries, held_twice

    world = geodesk.Features(str(gol))
    gbox = geodesk.Box(west=box[0], south=box[1], east=box[2], north=box[3]) if box else None

    def query(level):
        q = world(f"a[boundary=administrative][admin_level={level}]")
        return q(gbox) if gbox is not None else q

    repairs: list[str] = []
    countries = []
    t = time.perf_counter()
    for f in query(2):
        if not f.is_relation or not str(f.tags["name"] or ""):
            continue
        area = boundaries._to_area(f, 2, None, repairs)
        closed = boundaries.close_gaps(f, repairs)
        if closed is not None:
            area.geom = closed
        area.geom, stopped = outline_to_the_pole(area.geom)
        if stopped is not None:
            repairs.append(f"{area.id} {english(area)}: the outline stops at {stopped:.2f} degrees south, so it "
                           "is taken to the South Pole.")
        if area.geom.is_empty:
            continue
        countries.append(area)
    countries.sort(key=lambda a: a.id)
    say(f"Read {len(countries)} countries in {time.perf_counter() - t:.0f} seconds.")
    by_id = {a.id: a for a in countries}

    units = []
    data = yaml.safe_load((CONFIG_DIR / "country_units.yaml").read_text(encoding="utf-8"))
    for u in data.get("units") or []:
        if u["replaces"] not in by_id:
            continue
        for part in u["parts"]:
            f = world.relation(int(part["id"].removeprefix("osm:r")))
            if f is None:
                raise SystemExit(f"The country unit {part['id']} ({part['name']}) is not in the planet file. "
                                 "Correct mapdata/config/country_units.yaml.")
            area = boundaries._to_area(f, int(str(f.tags["admin_level"] or 3)), u["replaces"], repairs)
            area.tags.update(unit_name=part["name"], unit_type=part["type"], sovereign=u["sovereign"])
            units.append(area)
    for cid, sovereign in (data.get("sovereigns") or {}).items():
        if cid in by_id:
            by_id[cid].tags["sovereign"] = sovereign

    shapes = [a.geom for a in countries]
    tree = shapely.STRtree(shapes)
    for g in shapes:
        shapely.prepare(g)
    sizes = [g.area for g in shapes]
    divisions: dict[tuple[str, int], list] = {}
    unit_ids = {u.id for u in units}
    country_ids = set(by_id)
    for level in levels:
        t = time.perf_counter()
        found = 0
        for f in query(level):
            if not f.is_relation or not str(f.tags["name"] or ""):
                continue
            rid = f"osm:r{f.id}"
            if rid in unit_ids or rid in country_ids:
                continue
            local: list[str] = []
            area = boundaries._to_area(f, level, None, local)
            if area.geom.is_empty:
                continue
            p = shapely.point_on_surface(area.geom)
            hits = [i for i in tree.query(p, predicate="within")]
            if not hits:
                continue
            i = min(hits, key=lambda i: (sizes[i], countries[i].id))
            area.parent = countries[i].id
            divisions.setdefault((area.parent, level), []).append(area)
            repairs.extend(local)
            found += 1
        say(f"Read {found} divisions at level {level} in {time.perf_counter() - t:.0f} seconds.")

    from mapdata.stages.grid import polygonal

    for a in [*countries, *units, *(d for divs in divisions.values() for d in divs)]:
        a.geom = polygonal(a.geom) or shapely.Polygon()  # a repair can leave stray lines beside the areas
    records, geoms = [], []
    for a in countries:
        records.append(record_of(a, "country", None))
        geoms.append(a.geom)
    for a in units:
        records.append(record_of(a, "unit", a.parent))
        geoms.append(a.geom)
    for (cid, level), divs in sorted(divisions.items()):
        divs.sort(key=lambda a: a.id)
        kept, held = held_twice.resolve(by_id[cid], divs)
        for line in held_twice.report_lines(held, english, lambda i: english(by_id[i])):
            say(f"Level {level}. {line}")
        for a in kept:
            records.append(record_of(a, "division", cid))
            geoms.append(a.geom)
    for line in repairs:
        say(f"Repair: {line}")
    say(f"Repairs: {len(repairs)}.")
    return records, geoms


def main(folder: Path) -> int:
    """The entry point of the short-lived process: "mapdata read-planet <folder>"."""
    request = json.loads((folder / REQUEST).read_text(encoding="utf-8"))
    lines: list[str] = []

    def say(text):
        lines.append(text)
        print(text, flush=True)

    records, geoms = read(Path(request["gol"]), request["levels"], request.get("box"), say)
    # Written by the stage's own process, so the files are claimed there as well (see run).
    features.save(folder, records, geoms)
    (folder / "read log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


def run(ctx) -> None:
    _source, gol = ctx.source(ctx.settings.get("source", "planet"))
    request = {"gol": str(gol), "levels": list(ctx.settings.get("levels") or [4]), "box": ctx.settings.get("box"),
               "version": READ_VERSION}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(request, indent=1), encoding="utf-8", newline="\n")
    for name in ("features.json", "shapes.wkb", "read log.txt"):
        ctx.claim(ctx.folder / name)
    ctx.progress.line(f"Reading the planet file {gol.name} in a separate process, which ends when it has finished. "
                      "It maps much of the file into memory while it runs.")
    done = subprocess.run([sys.executable, "-m", "mapdata", "--data", str(ctx.folders.root), "read-planet",
                           str(ctx.folder)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (done.stdout or "").splitlines():
        ctx.progress.log(line)
    if done.returncode != 0 or not (ctx.folder / "features.json").is_file():
        raise BuildStopped("Reading the planet file failed. The end of its output was: "
                           + " ".join((done.stderr or done.stdout or "").splitlines()[-5:]))
    records, _ = features.load(ctx.folder)
    kinds = {}
    for r in records:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    ctx.progress.line(f"Read {kinds.get('country', 0)} countries, {kinds.get('unit', 0)} country units and "
                      f"{kinds.get('division', 0)} divisions.")
