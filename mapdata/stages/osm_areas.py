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
* counties: true to read the areas for the counties layer as well (DP101,
  P3-T1c): for each country, the levels in the counties record,
  mapdata/config/county_levels.yaml, or 6, 7 and 8 where it has none. The
  planet file is read once, and each county area is set aside on disk in a
  file for its country. Then, a country at a time, in the worker processes,
  an area at a level after the country's first that has less than 1 km2
  outside the levels before it can fill no gap, so it is left out. So the
  whole world's level 7 and 8 areas are never in memory at once.
* counties_record: optional, another counties record, as a path from the
  repository's top folder; used by the tests.
* islands: true to read the named islands and islets as well (P3-T1d,
  DP169): each OSM area tagged place=island or place=islet with a name, as
  an area of kind "island", which the squares stage cuts to the land; and
  each such island that OSM has only as a point, as a record of kind
  "island point" with its point and no shape, which the join stage uses to
  name a landmass that no island area covers.
"""
from __future__ import annotations

import json
import pickle
import subprocess
import sys
import time
from pathlib import Path

import shapely
import yaml

from mapdata.paths import CONFIG_DIR
from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped

READ_VERSION = "osm-areas-2"
ISLAND_PLACES = ("island", "islet")
REQUEST = "request.json"
SET_ASIDE = "county areas"       # the folder of county areas set aside, one file for each country
SET_ASIDE_INDEX = "index.json"
FLUSH_BYTES = 200_000_000        # county areas held before they are written to their countries' files


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


def fingerprint_extra(stage: dict) -> dict | None:
    """What the stage reads besides its settings and the planet file: each country's levels in the counties
    record, so that correcting the record reads the planet file again (P3-T1c)."""
    if not stage.get("counties"):
        return None
    from mapdata.stages import counties as countiesmod

    return {"county_levels": countiesmod.record_levels(countiesmod.record_path(stage))}


def osm_id(feature) -> str:
    """The canonical identifier of any OSM feature (AD-13): osm:n, osm:w or osm:r and its number."""
    kind = "r" if feature.is_relation else ("w" if feature.is_way else "n")
    return f"osm:{kind}{feature.id}"


def island_record(fid: str, tags: dict, place: str) -> dict:
    """The record of a named island or islet (P3-T1d), from its OSM tags."""
    local = str(tags.get("name") or "")
    r = {"id": fid, "name": str(tags.get("name:en") or local), "local_name": local, "kind": "island",
         "type": place, "level": None, "country": None}
    if tags.get("wikidata"):
        r["wikidata"] = str(tags["wikidata"])
    return r


def read_islands(world, gbox, say=print) -> tuple[list[dict], list]:
    """The named islands and islets (P3-T1d): the areas with their shapes, then the ones OSM has only as a
    point, kind "island point", with the point in the record and an empty shape."""
    import geodesk

    from mapdata.stages.grid import polygonal

    records, geoms, repairs = [], [], 0
    t = time.perf_counter()
    for place in ISLAND_PLACES:
        q = world(f"a[place={place}][name]")
        for f in (q(gbox) if gbox is not None else q):
            g = geodesk.from_mercator(f.shape)
            if not g.is_valid:
                g = shapely.make_valid(g, method="structure")
                repairs += 1
            g = polygonal(g)
            if g is None or g.is_empty:
                continue
            tags = {k: f.tags[k] for k in ("name", "name:en", "wikidata") if f.tags[k]}
            records.append(island_record(osm_id(f), tags, place))
            geoms.append(g)
    areas = len(records)
    for place in ISLAND_PLACES:
        q = world(f"n[place={place}][name]")
        for f in (q(gbox) if gbox is not None else q):
            tags = {k: f.tags[k] for k in ("name", "name:en", "wikidata") if f.tags[k]}
            r = island_record(osm_id(f), tags, place)
            r["kind"] = "island point"
            r["point"] = [round(float(f.lon), 7), round(float(f.lat), 7)]
            records.append(r)
            geoms.append(shapely.Polygon())
    order = sorted(range(len(records)), key=lambda i: records[i]["id"])
    say(f"Read {areas} named islands and islets as areas ({repairs} repaired), and {len(records) - areas} as "
        f"points only, in {time.perf_counter() - t:.0f} seconds.")
    return [records[i] for i in order], [geoms[i] for i in order]


def set_aside_name(country_id: str) -> str:
    return country_id.replace(":", "_") + ".pkl"


def read(gol: Path, levels: list[int], box: list[float] | None, say=print, counties: dict | None = None,
         folder: Path | None = None, claim=lambda p: p, islands: bool = False) -> tuple[list[dict], list]:
    """Everything the stage reads, as feature records and shapes. Runs in the short-lived process.

    counties: {"levels": {country id: levels}, "how": {country id: how}} from the counties record, to read
    the county areas too; each is set aside in folder / SET_ASIDE, in a file for its country, and not
    returned."""
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
    from mapdata.stages import counties as countiesmod

    def county_levels_of(cid):
        return list((counties or {}).get("levels", {}).get(cid) or countiesmod.DEFAULT_LEVELS)

    region_levels = set(levels)
    extra = sorted({lv for cid in by_id for lv in county_levels_of(cid)} - region_levels) if counties is not None         else []
    aside_dir = Path(folder) / SET_ASIDE if folder is not None else None
    buffers: dict[str, list] = {}
    held_bytes = 0
    aside_counts: dict[str, int] = {}

    def flush():
        nonlocal held_bytes
        aside_dir.mkdir(parents=True, exist_ok=True)
        for cid, items in buffers.items():
            if items:
                with open(claim(aside_dir / set_aside_name(cid)), "ab") as out:
                    pickle.dump(items, out, protocol=pickle.HIGHEST_PROTOCOL)
        buffers.clear()
        held_bytes = 0

    for level in [*levels, *extra]:
        t = time.perf_counter()
        found = 0
        aside = level not in region_levels
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
            repairs.extend(local)
            if aside:
                if level not in county_levels_of(area.parent):
                    continue
                from mapdata.stages.grid import polygonal

                blob = shapely.to_wkb(polygonal(area.geom) or shapely.Polygon())
                buffers.setdefault(area.parent, []).append((area.id, area.name, level, dict(area.tags or {}), blob))
                aside_counts[area.parent] = aside_counts.get(area.parent, 0) + 1
                held_bytes += len(blob)
                if held_bytes > FLUSH_BYTES:
                    flush()
            else:
                divisions.setdefault((area.parent, level), []).append(area)
            found += 1
        what = "county areas set aside" if aside else "divisions"
        say(f"Read {found} {what} at level {level} in {time.perf_counter() - t:.0f} seconds.")
    if counties is not None:
        flush()
        index = {}
        for a in countries:
            index[a.id] = {"levels": county_levels_of(a.id), "how": counties.get("how", {}).get(a.id, "the rule"),
                           "file": set_aside_name(a.id) if a.id in aside_counts else None,
                           "count": aside_counts.get(a.id, 0), "iso": (a.tags or {}).get("ISO3166-1"),
                           "name": english(a)}
            if box is not None:
                w, s, e, n = a.geom.bounds
                index[a.id]["whole"] = w >= box[0] and s >= box[1] and e <= box[2] and n <= box[3]
            else:
                index[a.id]["whole"] = True
        aside_dir.mkdir(parents=True, exist_ok=True)
        claim(aside_dir / SET_ASIDE_INDEX).write_text(json.dumps(index, indent=0, ensure_ascii=False, sort_keys=True),
                                                 encoding="utf-8", newline="\n")

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
    if islands:
        i_records, i_geoms = read_islands(world, gbox, say)
        records += i_records
        geoms += i_geoms
    return records, geoms


def main(folder: Path) -> int:
    """The entry point of the short-lived process: "mapdata read-planet <folder>"."""
    request = json.loads((folder / REQUEST).read_text(encoding="utf-8"))
    lines: list[str] = []

    def say(text):
        lines.append(text)
        print(text, flush=True)

    claim = (lambda p: p)
    if request.get("counties"):
        # The county areas' files are named only as they are found, so this process claims them itself.
        from mapdata.pipeline import ledger as ledgermod

        claim = ledgermod.Ledger(Path(request["counties"]["own"])).claim
    records, geoms = read(Path(request["gol"]), request["levels"], request.get("box"), say,
                          counties=request.get("counties"), folder=folder, claim=claim,
                          islands=bool(request.get("islands")))
    # Written by the stage's own process, so the files are claimed there as well (see run).
    features.save(folder, records, geoms)
    (folder / "read log.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


def run(ctx) -> None:
    _source, gol = ctx.source(ctx.settings.get("source", "planet"))
    request = {"gol": str(gol), "levels": list(ctx.settings.get("levels") or [4]), "box": ctx.settings.get("box"),
               "version": READ_VERSION}
    if ctx.settings.get("islands"):
        request["islands"] = True
    if ctx.settings.get("counties"):
        from mapdata.stages import counties as countiesmod

        record = countiesmod.load_record(countiesmod.record_path(ctx.settings))
        request["counties"] = {"levels": countiesmod.record_levels(countiesmod.record_path(ctx.settings)),
                               "how": {cid: countiesmod.how_of(e) for cid, e in record.items()},
                               "record": str(countiesmod.record_path(ctx.settings)),
                               "own": str(ctx.folders.own)}
    ctx.claim(ctx.folder / REQUEST).write_text(json.dumps(request, indent=1), encoding="utf-8", newline="\n")
    for name in ("features.json", "shapes.wkb", "read log.txt"):
        ctx.claim(ctx.folder / name)
    aside = ctx.folder / SET_ASIDE
    if aside.is_dir():   # left by a reading that was stopped: the files are added to, so they start empty
        for p in aside.iterdir():
            if ctx.ledger.created(p):
                p.unlink()
    ctx.progress.line(f"Reading the planet file {gol.name} in a separate process, which ends when it has finished. "
                      "It maps much of the file into memory while it runs.")
    done = subprocess.run([sys.executable, "-m", "mapdata", "--data", str(ctx.folders.root), "read-planet",
                           str(ctx.folder)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (done.stdout or "").splitlines():
        ctx.progress.log(line)
    if done.returncode != 0 or not (ctx.folder / "features.json").is_file():
        raise BuildStopped("Reading the planet file failed. The end of its output was: "
                           + " ".join((done.stderr or done.stdout or "").splitlines()[-5:]))
    if ctx.settings.get("counties"):
        sort_counties(ctx)
    records, _ = features.load(ctx.folder)
    kinds = {}
    for r in records:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    ctx.progress.line(f"Read {kinds.get('country', 0)} countries, {kinds.get('unit', 0)} country units and "
                      f"{kinds.get('division', 0)} divisions."
                      + (f" Named islands: {kinds.get('island', 0)} as areas and {kinds.get('island point', 0)} as "
                         "points only." if ctx.settings.get("islands") else ""))


def sort_country(job):
    """One country's county areas, set aside by the reading (P3-T1c), in a worker process: each area held
    twice kept once (DP104), and an area at a level after the first that has less than 1 km2 outside the
    levels before it left out, as it can fill no gap (DP101). Returns the country, the areas kept as
    (record, shape in well-known binary), lines for the log, and for each level: areas read, left out."""
    from mapdata.stages import boundaries, counties as countiesmod, held_twice

    cid, name, iso, levels, path, known = job
    by_level: dict[int, list] = {}
    if path:
        with open(path, "rb") as f:
            while True:
                try:
                    items = pickle.load(f)
                except EOFError:
                    break
                for aid, local, level, tags, blob in items:
                    by_level.setdefault(level, []).append(
                        boundaries.Area(aid, local, level, shapely.from_wkb(blob), cid, tags))
    country = boundaries.Area(cid, name, 2, None, None, {"ISO3166-1": iso} if iso else {})
    lines: list[str] = []
    earlier: list = []
    kept_rows: list = []
    counts: dict[int, list[int]] = {}
    for n, level in enumerate(levels):
        if str(level) in known:   # read as a region level: already among the divisions, and only measured against
            here_geoms = [shapely.from_wkb(b) for b in known[str(level)]]
            earlier += here_geoms
            counts[level] = [len(here_geoms), 0]
            continue
        divs = sorted(by_level.get(level, []), key=lambda a: a.id)
        divs, held = held_twice.resolve(country, divs)
        for line in held_twice.report_lines(held, english, lambda _i: name):
            lines.append(f"Level {level}. {line}")
        drop = countiesmod.cannot_fill_a_gap([a.geom for a in divs], earlier) if n else set()
        keep = [a for i, a in enumerate(divs) if i not in drop]
        earlier += [a.geom for a in keep]
        counts[level] = [len(divs), len(drop)]
        kept_rows += [(record_of(a, "division", cid), shapely.to_wkb(a.geom)) for a in keep]
    return cid, kept_rows, lines, counts


def sort_counties(ctx) -> None:
    """The county areas set aside by the reading, sorted a country at a time in the worker processes, and the
    ones kept added to the stage's areas (P3-T1c)."""
    from mapdata import parallel
    from mapdata.stages.pack_write import executor_map

    t = time.perf_counter()
    aside = ctx.folder / SET_ASIDE   # its files were claimed by the reading process, which wrote them
    index = json.loads((aside / SET_ASIDE_INDEX).read_text(encoding="utf-8"))
    data = json.loads((ctx.folder / "features.json").read_text(encoding="utf-8"))
    known: dict[str, dict[str, list]] = {}
    with open(ctx.folder / "shapes.wkb", "rb") as shapes_file:
        for r, (at, size) in zip(data["records"], data["shapes"]):
            if r["kind"] != "division" or r["country"] not in index:
                continue
            if r["level"] in index[r["country"]]["levels"]:
                shapes_file.seek(at)
                known.setdefault(r["country"], {}).setdefault(str(r["level"]), []).append(shapes_file.read(size))
    jobs = []
    for cid, e in sorted(index.items()):
        path = aside / e["file"] if e.get("file") else None
        if path is None and cid not in known:
            continue
        jobs.append((cid, e["name"], e.get("iso"), e["levels"], str(path) if path else None, known.get(cid, {})))
    jobs.sort(key=lambda j: -(Path(j[4]).stat().st_size if j[4] else 0))
    ctx.progress.line(f"Counties: sorting the county areas of {len(jobs)} countries, a country at a time, the "
                      "largest first.")
    results = {}
    with parallel.pool(min(ctx.workers, max(1, len(jobs)))) as ex:
        for n, (cid, rows, lines, counts) in enumerate(executor_map(ex, sort_country, jobs, ctx.workers), 1):
            results[cid] = rows
            e = index[cid]
            for line in lines:
                ctx.progress.log(line)
            parts = []
            for level in e["levels"]:
                got, dropped = counts.get(level, [0, 0])
                parts.append(f"level {level}, {got:,} areas" + (f", {dropped:,} of them inside the levels before, "
                                                                "left out" if dropped else ""))
            how = {"corrected": "as corrected in the counties record", "worked out": "as worked out in the counties "
                   "record"}.get(e["how"], "by the rule")
            ctx.progress.log(f"County areas read in {e['name']}, at the levels {how}: " + "; ".join(parts) + ".")
            if n % 20 == 0:
                ctx.progress.line(f"Counties: {n} of {len(jobs)} countries sorted.")
            ctx.check_switch(f"after {n} of {len(jobs)} countries' county areas")
    rows = [row for cid in sorted(results) for row in results[cid]]
    features.append(ctx.folder, [r for r, _b in rows], [b for _r, b in rows])
    read = sum(e["count"] for e in index.values())
    ctx.progress.line(f"Counties: {read:,} county areas read at the levels after the regions'; {len(rows):,} kept, "
                      f"and the rest, inside the levels before them, left out. Took "
                      f"{time.perf_counter() - t:.0f} seconds.")
    for e in index.values():
        if e.get("file"):
            (aside / e["file"]).unlink()
