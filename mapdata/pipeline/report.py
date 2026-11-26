"""The quality report (P4-T11a, DMT-3): what a data manager reads to judge a build without looking at a map.

Every finished build writes, in the pack's output folder, "<pack> quality report.txt" and CSV files named
"<pack> quality <section>.csv". `mapdata report <pack>` makes them again from the kept stage folders and the pack.

Nothing here changes a stage. The report gathers what the stages already keep in their folders in the working
folder, and the pack itself:

* repaired shapes: the "Repair:" lines in each reading stage's "read log.txt", and the repairs named in this build's log;
* features without names: the pack's feature records;
* gaps in coverage and gaps filled by the counties record: the report of the joining stage (join.json);
* matches made by name for Wikidata: the records of the last stage that kept them (features.json), which flag each;
* the correction rules applied: the corrections stage's corrections.txt;
* matches with the world pack, for a regional pack: the match stage's matches.csv and match.json (P4-T1h);
* size by layer: the pack, measured as tools/pack_layers.py does (mapdata/pipeline/pack_size.py);
* differences from the last build: a small summary of each build, kept beside the pack, compared with the one the
  build before kept.

A section whose facts no stage keeps says "Not recorded by this build yet", and says which facts. The text is plain
lines for a screen reader (DMT-2): counts first, at most EXAMPLES example lines in each section, and the name of the
CSV file that holds the full list.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
from pathlib import Path

from mapdata.pipeline.ledger import Ledger

EXAMPLES = 20
NOT_RECORDED = "Not recorded by this build yet"
CSV_BOM = "utf-8-sig"   # a byte order mark, so a spreadsheet shows accents correctly


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def mb(n: float) -> str:
    return f"{n / 1e6:,.2f} MB"


def file_names(pack: str) -> dict[str, str]:
    base = f"{pack} quality"
    return {
        "report": f"{pack} quality report.txt",
        "repairs": f"{base} repaired shapes.csv",
        "nameless": f"{base} features without names.csv",
        "gaps": f"{base} gaps in coverage.csv",
        "filled": f"{base} gaps filled by the counties record.csv",
        "matches": f"{base} wikidata matches by name.csv",
        "rules": f"{base} correction rules.csv",
        "world matches": f"{base} matches with the world pack.csv",
        "size": f"{base} size by layer.csv",
        "by layer": f"{base} differences by layer.csv",
        "by feature": f"{base} differences by feature.csv",
        "summary": f"{base} summary of this build.json.gz",
        "previous": f"{base} summary of the build before.json.gz",
    }


# What the stages kept ---------------------------------------------------------------------------------------------

def read_logs(stage_folders: list[tuple[int, str, Path]]) -> list[tuple[str, str]]:
    """Each line of each stage's reading log, as (stage, line): the log beside a stage's results, and the log of a
    reading kept in its "read" folder."""
    out = []
    for _, kind, folder in stage_folders:
        for path in (folder / "read log.txt", folder / "read" / "read log.txt"):
            if path.is_file():
                out += [(kind, line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return out


REPAIR = re.compile(r"^Repair: (\S+) (.*?): (.*)$")


def gather_repairs(stage_folders, build_log: list[str]) -> dict:
    rows, counts, other = [], [], []
    for kind, line in read_logs(stage_folders):
        m = REPAIR.match(line)
        if m:
            rows.append({"stage": kind, "identifier": m[1], "name": m[2], "what was done": m[3]})
        elif line.startswith("Repair:"):
            rows.append({"stage": kind, "identifier": "", "name": "", "what was done": line[len("Repair:"):].strip()})
        elif re.search(r"\(\d[\d,]* repaired\)", line):
            counts.append(f"{kind}: {line}")
    for line in build_log:
        if "repair" in line.lower() and not line.startswith("Repair"):
            other.append(line)
    # A stage that reads a log of repairs: the planet-file stage. Without one in the pack's stages, none is kept.
    keeps = any(kind == "osm-areas" for _, kind, _ in stage_folders)
    return {"rows": rows, "counts": counts, "other": other, "keeps": keeps}


def join_report(stage_folders) -> list[str] | None:
    for _, kind, folder in reversed(stage_folders):
        if kind == "join" and (folder / "join.json").is_file():
            return json.loads((folder / "join.json").read_text(encoding="utf-8")).get("report", [])
    return None


FILLED = re.compile(r"^Counties in (.+?): (.*)$")
FILL_PART = re.compile(r"gaps filled by level (\d+), ([\d,]+) areas?, ([\d,]+) km2")
NO_COUNTY = re.compile(r"^No county covers ([\d,]+) km2 of (.+), ([^,]+), so the region itself is used there\.$")
LEVEL_PART = re.compile(r"^level (\d+), ([\d,]+) areas?, ([\d,]+) km2")


def to_int(text: str) -> int:
    return int(text.replace(",", ""))


def gather_gaps(report: list[str] | None, build_log: list[str]) -> dict:
    """The gaps in coverage and the gaps the counties record filled, from the joining stage's report."""
    gaps, filled = [], []
    if report is None:
        return {"gaps": None, "filled": None, "check": None}
    for line in report:
        m = NO_COUNTY.match(line)
        if m:
            gaps.append({"kind": "land no county covers, so the region itself is used", "area": m[2],
                         "country": m[3], "km2": to_int(m[1]), "detail": line})
        elif line.startswith("Small islands in no country"):
            gaps.append({"kind": "small islands in no country", "area": "", "country": "", "km2": "", "detail": line})
        m = FILLED.match(line)
        if m:
            for part in m[2].split("; "):
                f = FILL_PART.search(part)
                if f:
                    filled.append({"country": m[1], "level": int(f[1]), "areas": to_int(f[2]), "km2": to_int(f[3])})
    check = [line for line in build_log if "no-gaps check" in line.lower()]
    return {"gaps": gaps, "filled": filled, "check": check}


def gather_corrections(stage_folders) -> list[dict] | None:
    for _, kind, folder in reversed(stage_folders):
        if kind == "corrections" and (folder / "corrections.txt").is_file():
            rows = []
            for line in (folder / "corrections.txt").read_text(encoding="utf-8").splitlines():
                for result in ("Applied", "Not found", "Not applied"):
                    if line.startswith(result + ": "):
                        rows.append({"result": result.lower(), "rule": line[len(result) + 2:]})
                if line.startswith("Features left out:"):
                    rows.append({"result": "left out", "rule": line})
            return rows
    return None


def gather_matches(stage_folders) -> list[dict] | None:
    """The features Wikidata gave a link to by name and place, from the records of the last stage that kept them."""
    for _, kind, folder in reversed(stage_folders):
        path = folder / "features.json"
        if kind in ("corrections", "wikidata", "relationships", "coast-stretches") and path.is_file():
            records = json.loads(path.read_text(encoding="utf-8"))["records"]
            return [{"identifier": r["id"], "layer": r["layer"], "name": r["name"], "wikidata item": r["wikidata"]}
                    for r in records if r.get("wikidata_matched")]
    return None


WORLD_MATCH_COLUMNS = ["how", "layer", "world identifier", "world name", "regional identifier", "regional name",
                       "overlap %"]


def gather_world_matches(stage_folders) -> dict | None:
    """A regional pack's matches with the world pack (P4-T1h): the match stage's counts (match.json) and its rows
    (matches.csv), each match made by Wikidata or by name and each world feature left unmatched. None for a pack
    with no match stage."""
    for _, kind, folder in reversed(stage_folders):
        if kind == "match" and (folder / "matches.csv").is_file():
            with open(folder / "matches.csv", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            counts = {}
            if (folder / "match.json").is_file():
                counts = json.loads((folder / "match.json").read_text(encoding="utf-8")).get("counts") or {}
            return {"counts": counts, "rows": rows}
    return None


def world_matches_section(got: dict | None, csv_name: str) -> tuple[str, list[str]]:
    """The short line and the lines of the section "Matches with the world pack". Matches made by name come first,
    as a wrong match is most likely among them (design 3.11, Risks), then those made by Wikidata, then the world
    features in the coverage left unmatched."""
    if got is None:
        return ("Matches with the world pack: none, as this pack has no match stage.",
                ["This pack has no match stage: only a regional pack is matched with the world pack."])
    rows, counts = got["rows"], got["counts"]
    by = {how: [r for r in rows if r["how"] == how] for how in ("name", "wikidata", "unmatched")}
    short = (f"Matches with the world pack: {counts.get('id', 0):,} by id, {len(by['wikidata']):,} by Wikidata, "
             f"{len(by['name']):,} by name; {len(by['unmatched']):,} world features with no match.")
    lines = [f"{plural(counts.get('id', 0), 'feature')} kept the world pack's id, as both packs gave it the same.",
             f"{plural(len(by['wikidata']), 'feature')} matched by Wikidata and {len(by['name']):,} by name, type "
             f"and overlap, each taking the world's id and keeping its own as an alias.",
             f"{plural(counts.get('as_layer', 0), 'id')} the world uses in another layer given the ending of its "
             f"layer.",
             f"{plural(len(by['unmatched']), 'world feature')} in the coverage with no match, to be hidden there "
             f"when the packs are combined.",
             "Check each match made by name: a wrong one joins two features."]

    def said(r: dict) -> str:
        if r["how"] == "unmatched":
            return f"No match: {r['world name'] or 'no name'} ({r['world identifier']}, {r['layer']})."
        how = "by name" if r["how"] == "name" else "by Wikidata"
        overlap = f", overlap {r['overlap %']}%" if r.get("overlap %") else ""
        return (f"Matched {how}: {r['regional name'] or 'no name'} ({r['regional identifier']}) is the world's "
                f"{r['world name'] or 'no name'} ({r['world identifier']}, {r['layer']}){overlap}.")

    lines += examples([said(r) for r in by["name"] + by["wikidata"] + by["unmatched"]], csv_name)
    return short, lines


# The pack -----------------------------------------------------------------------------------------------------------

def read_pack(target: Path) -> dict:
    """The pack's features by layer, and what is wrong with their names. Reads the feature records only."""
    from mapcore.packs.pack import Pack

    with Pack(target, check_app=False) as p:
        layers = {layer["id"]: {"name": layer["name"], "geometry": layer.get("geometry", "area"), "features": {}}
                  for layer in p.layers}
        nameless = []
        for n in range(p.manifest["features"]["count"]):
            f = p.feature(n)
            layers.setdefault(f["layer"], {"name": f["layer"], "geometry": "area", "features": {}})
            name = (f.get("name") or "").strip()
            layers[f["layer"]]["features"][f["id"]] = name
            if not name or name == f["id"]:
                nameless.append({"identifier": f["id"], "layer": layers[f["layer"]]["name"], "kind": f.get("type", "")})
        built = p.manifest["built"]
    return {"layers": layers, "nameless": nameless, "built": built}


def pack_identity(target: Path) -> str:
    from mapcore.packs.pack import checksum_path

    path = checksum_path(target)
    return path.read_text(encoding="utf-8").strip() if path.is_file() else f"size {target.stat().st_size}"


def sizes(target: Path) -> dict:
    from mapdata.pipeline.pack_size import measure

    m = measure(target)
    by_layer = {layer: sum(v["bytes"] for v in parts.values()) for layer, parts in m["parts"].items()}
    points = {layer: sum(v["points"] for v in parts.values()) for layer, parts in m["parts"].items()}
    return {"bytes": m["bytes"], "own": m["own_bytes"], "by layer": by_layer, "points": points}


# Differences from the build before ------------------------------------------------------------------------------------

def summary_of(pack: str, identity: str, built: str, data: dict, size: dict) -> dict:
    return {"pack": pack, "identity": identity, "built": built, "bytes": size["bytes"],
            "layers": {layer: {"name": d["name"], "geometry": d["geometry"], "bytes": round(size["by layer"].get(layer, 0)),
                               "features": d["features"]} for layer, d in data["layers"].items()}}


def load_summary(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def keep_summary(summary: dict, out_dir: Path, names: dict, ledger: Ledger) -> dict | None:
    """Keep this build's summary, and return the one kept by the build before, or None. Where the summary already
    kept is of this same pack, as when the report is made again, the build before stays what it was."""
    current, before = out_dir / names["summary"], out_dir / names["previous"]
    kept = load_summary(current)
    if kept is not None and kept.get("identity") != summary["identity"]:
        before_bytes = current.read_bytes()
        ledger.claim(before).write_bytes(before_bytes)
    with gzip.open(ledger.claim(current), "wt", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, separators=(",", ":"))
    return load_summary(before)


def compare(now: dict, before: dict) -> tuple[list[dict], list[dict]]:
    """Differences by layer and by feature between two summaries."""
    by_layer, by_feature = [], []
    for layer in list(now["layers"]) + [k for k in before["layers"] if k not in now["layers"]]:
        a = now["layers"].get(layer, {"name": before["layers"].get(layer, {}).get("name", layer), "features": {}, "bytes": 0})
        b = before["layers"].get(layer, {"name": a["name"], "features": {}, "bytes": 0})
        added = [i for i in a["features"] if i not in b["features"]]
        removed = [i for i in b["features"] if i not in a["features"]]
        renamed = [i for i in a["features"] if i in b["features"] and a["features"][i] != b["features"][i]]
        by_layer.append({"layer": a["name"], "features before": len(b["features"]), "features now": len(a["features"]),
                         "added": len(added), "left out": len(removed), "renamed": len(renamed),
                         "bytes before": b["bytes"], "bytes now": a["bytes"]})
        by_feature += [{"change": "added", "layer": a["name"], "identifier": i, "name before": "",
                        "name now": a["features"][i]} for i in added]
        by_feature += [{"change": "left out", "layer": a["name"], "identifier": i, "name before": b["features"][i],
                        "name now": ""} for i in removed]
        by_feature += [{"change": "renamed", "layer": a["name"], "identifier": i, "name before": b["features"][i],
                        "name now": a["features"][i]} for i in renamed]
    return by_layer, by_feature


# The files ----------------------------------------------------------------------------------------------------------

def write_csv(path: Path, columns: list[str], rows: list[dict], ledger: Ledger) -> None:
    with open(ledger.claim(path), "w", encoding=CSV_BOM, newline="") as f:
        out = csv.DictWriter(f, fieldnames=columns, lineterminator="\r\n", extrasaction="ignore")
        out.writeheader()
        out.writerows(rows)


def examples(lines: list[str], csv_name: str | None) -> list[str]:
    out = lines[:EXAMPLES]
    if csv_name and len(lines) > EXAMPLES:
        out.append(f"{len(lines) - EXAMPLES:,} more are not shown here.")
    if csv_name and lines:
        out.append(f"The full list is in {csv_name}.")
    return out


def not_recorded(what: str) -> list[str]:
    return [f"{NOT_RECORDED}: {what}"]


def make_report(pack_name: str, title: str, target: Path, stage_folders: list[tuple[int, str, Path]],
                build_log_path: Path | None, ledger: Ledger, say=print) -> Path:
    """Write the report and its CSV files beside the pack, and return the report's path. stage_folders are the
    finished stages' (number, kind, folder), in order."""
    out_dir = target.parent
    names = file_names(pack_name)
    build_log = (build_log_path.read_text(encoding="utf-8").splitlines()
                 if build_log_path is not None and build_log_path.is_file() else [])

    data = read_pack(target)
    identity = pack_identity(target)
    size = sizes(target)
    repairs = gather_repairs(stage_folders, build_log)
    coverage = gather_gaps(join_report(stage_folders), build_log)
    rules = gather_corrections(stage_folders)
    matches = gather_matches(stage_folders)
    world_matches = gather_world_matches(stage_folders)
    summary = summary_of(pack_name, identity, data["built"], data, size)
    before = keep_summary(summary, out_dir, names, ledger)
    by_layer, by_feature = compare(summary, before) if before else ([], [])

    total = sum(len(d["features"]) for d in data["layers"].values())
    short, body = [], []   # the list of counts at the top, and the sections

    def section(heading: str, lines: list[str]) -> None:
        body.extend(["", heading, "", *lines])

    # 1 Repaired shapes
    if repairs["keeps"]:
        n = len(repairs["rows"])
        short.append(f"Repaired shapes: {n:,}.")
        lines = [f"{plural(n, 'shape')} had to be repaired when it was read from the planet file."]
        lines += repairs["counts"]
        lines += examples([f"{r['name']} ({r['identifier']}): {r['what was done']}" for r in repairs["rows"]],
                          names["repairs"])
        write_csv(out_dir / names["repairs"], ["stage", "identifier", "name", "what was done"], repairs["rows"], ledger)
    else:
        short.append(f"Repaired shapes: {NOT_RECORDED}.")
        lines = not_recorded("this pack's stages keep no list of the shapes they repaired.")
    if repairs["other"]:
        lines += [f"Repairs named in this build's log, from the stages that ran in it ({len(repairs['other'])}):"]
        lines += repairs["other"][:EXAMPLES]
    lines.append("Repairs made by the joining, the continents and the writing stages are kept only in the log of the "
                 "build in which that stage ran.")
    section("Repaired shapes", lines)

    # 2 Features without names
    n = len(data["nameless"])
    short.append(f"Features without names: {n:,} of {total:,}.")
    lines = [f"{plural(n, 'feature')} of {total:,} in the pack has no name." if n == 1 else
             f"{plural(n, 'feature')} of {total:,} in the pack have no name."]
    lines += examples([f"{r['layer']}: {r['identifier']}, a {r['kind'] or 'feature'}" for r in data["nameless"]],
                      names["nameless"])
    write_csv(out_dir / names["nameless"], ["identifier", "layer", "kind"], data["nameless"], ledger)
    section("Features without names", lines)

    # 3 Gaps in coverage
    if coverage["gaps"] is None:
        short.append(f"Gaps in coverage: {NOT_RECORDED}.")
        lines = not_recorded("this pack has no joining stage, which is the stage that keeps its report of gaps.")
    else:
        gaps = coverage["gaps"]
        areas = [g for g in gaps if g["kind"].startswith("land no county")]
        short.append(f"Gaps in coverage: {len(gaps):,}.")
        lines = [f"{plural(len(areas), 'area')} of land that no county covers, where the region itself is used as "
                 f"its county."]
        lines += [g["detail"] for g in gaps if g["kind"].startswith("small")]
        lines += examples([g["detail"] for g in sorted(areas, key=lambda g: -g["km2"])], names["gaps"])
        write_csv(out_dir / names["gaps"], ["kind", "area", "country", "km2", "detail"], gaps, ledger)
        if coverage["check"]:
            lines += coverage["check"][:5]
        else:
            lines += not_recorded("the result of the no-gaps check (LOC-6), which is only in the log of the build "
                                  "in which the joining stage ran.")
    section("Gaps in coverage", lines)

    # 4 Gaps filled by the counties record
    if coverage["filled"] is None:
        short.append(f"Gaps filled by the counties record: {NOT_RECORDED}.")
        lines = not_recorded("this pack has no joining stage.")
    else:
        filled = coverage["filled"]
        countries = len({f["country"] for f in filled})
        short.append(f"Gaps filled by the counties record: {len(filled):,} fills in {plural(countries, 'country', 'countries')}.")
        lines = [f"{plural(len(filled), 'fill')} of a gap in the counties, in {plural(countries, 'country', 'countries')}."]
        lines += examples([f"{f['country']}: gaps filled by level {f['level']}, {plural(f['areas'], 'area')}, "
                           f"{f['km2']:,} km2." for f in sorted(filled, key=lambda f: -f["km2"])], names["filled"])
        write_csv(out_dir / names["filled"], ["country", "level", "areas", "km2"], filled, ledger)
    section("Gaps filled by the counties record", lines)

    # 5 Matches by name for Wikidata
    if matches is None:
        short.append(f"Matches made by name for Wikidata: {NOT_RECORDED}.")
        lines = not_recorded("no stage's records of this pack say which features Wikidata matched by name.")
    else:
        short.append(f"Matches made by name for Wikidata: {len(matches):,}.")
        lines = [f"{plural(len(matches), 'feature')} with no Wikidata link in OpenStreetMap "
                 f"{'was' if len(matches) == 1 else 'were'} matched by name and place."]
        lines += examples([f"{m['name']} ({m['identifier']}, {m['layer']}) is Wikidata's {m['wikidata item']}."
                           for m in matches], names["matches"])
        write_csv(out_dir / names["matches"], ["identifier", "layer", "name", "wikidata item"], matches, ledger)
    section("Matches made by name for Wikidata", lines)

    # 6 Correction rules
    if rules is None:
        short.append(f"Correction rules applied: {NOT_RECORDED}.")
        lines = not_recorded("this pack has no corrections stage.")
    else:
        applied = [r for r in rules if r["result"] == "applied"]
        other = [r for r in rules if r["result"] in ("not found", "not applied")]
        short.append(f"Correction rules applied: {len(applied):,} of {len([r for r in rules if r['result'] != 'left out']):,}.")
        lines = [f"{plural(len(applied), 'correction rule')} applied, {len([r for r in rules if r['result'] == 'not found'])} "
                 f"whose feature was not found, {len([r for r in rules if r['result'] == 'not applied'])} found but not applied."]
        lines += examples([f"{r['result'].capitalize()}: {r['rule']}" for r in rules if r["result"] != "left out"]
                          + [r["rule"] for r in rules if r["result"] == "left out"], names["rules"])
        if other:
            lines.append("Mend or remove each rule not found or not applied in mapdata/config/corrections.yaml.")
        write_csv(out_dir / names["rules"], ["result", "rule"], rules, ledger)
    section("Correction rules applied", lines)

    # 6b Matches with the world pack (P4-T1h)
    line, lines = world_matches_section(world_matches, names["world matches"])
    short.append(line)
    order = {"name": 0, "wikidata": 1, "unmatched": 2}
    write_csv(out_dir / names["world matches"], WORLD_MATCH_COLUMNS,   # only the headings, for a pack not matched
              sorted(world_matches["rows"] if world_matches else [], key=lambda r: order.get(r["how"], 3)), ledger)
    section("Matches with the world pack", lines)

    # 7 Size by layer
    rows = sorted(({"layer": d["name"], "features": len(d["features"]), "megabytes": round(size["by layer"].get(k, 0) / 1e6, 3),
                    "share of the pack %": round(100 * size["by layer"].get(k, 0) / size["bytes"], 1),
                    "points": size["points"].get(k, 0)} for k, d in data["layers"].items()),
                  key=lambda r: -r["megabytes"])
    rows.append({"layer": "the pack's own records", "features": "", "megabytes": round(size["own"] / 1e6, 3),
                 "share of the pack %": round(100 * size["own"] / size["bytes"], 1), "points": ""})
    short.append(f"Size: {mb(size['bytes'])} in {plural(len(data['layers']), 'layer')}.")
    lines = [f"The pack is {mb(size['bytes'])}. Largest layers first:"]
    lines += examples([f"{r['layer']}: {r['megabytes']:,.2f} MB, {r['share of the pack %']}% of the pack"
                       + (f", {r['features']:,} features" if r["features"] != "" else "") for r in rows], names["size"])
    write_csv(out_dir / names["size"], ["layer", "features", "megabytes", "share of the pack %", "points"], rows, ledger)
    section("Size by layer", lines)

    # 8 Differences from the last build
    if before is None:
        short.append("Differences from the last build: there is no earlier build to compare with.")
        lines = ["There is no earlier build to compare with. This build's summary is kept beside the pack, "
                 "and the next build is compared with it."]
    else:
        changed = [r for r in by_layer if r["added"] or r["left out"] or r["renamed"] or r["bytes before"] != r["bytes now"]]
        short.append(f"Differences from the last build: {len(by_feature):,} features changed in "
                     f"{plural(len([r for r in by_layer if r['added'] or r['left out'] or r['renamed']]), 'layer')}.")
        lines = [f"Compared with the build before, which was of sources dated up to {before['built']}, "
                 f"and the pack was {mb(before['bytes'])}; it is now {mb(size['bytes'])}.",
                 f"{plural(len([c for c in by_feature if c['change'] == 'added']), 'feature')} added, "
                 f"{len([c for c in by_feature if c['change'] == 'left out'])} left out, "
                 f"{len([c for c in by_feature if c['change'] == 'renamed'])} renamed."]
        lines += examples([f"{r['layer']}: {r['features before']:,} before, {r['features now']:,} now; {r['added']:,} added, "
                           f"{r['left out']:,} left out, {r['renamed']:,} renamed; size "
                           f"{mb(r['bytes before'])} before, {mb(r['bytes now'])} now." for r in changed], names["by layer"])
        order = {"renamed": 0, "left out": 1, "added": 2}
        shown = sorted(by_feature, key=lambda c: order[c["change"]])
        lines.append("Features that changed, renamed first:")
        lines += examples([(f"Renamed in {c['layer']}: {c['identifier']} from {c['name before']} to {c['name now']}."
                            if c["change"] == "renamed" else
                            f"{c['change'].capitalize()} in {c['layer']}: {c['identifier']}, "
                            f"{c['name now'] or c['name before']}.") for c in shown], names["by feature"])
        write_csv(out_dir / names["by layer"], ["layer", "features before", "features now", "added", "left out", "renamed",
                                                "bytes before", "bytes now"], by_layer, ledger)
        write_csv(out_dir / names["by feature"], ["change", "layer", "identifier", "name before", "name now"],
                  by_feature, ledger)
    section("Differences from the last build", lines)

    head = [f"Quality report for the pack {pack_name}: {title}", "",
            f"Built from sources dated up to {data['built']}. {plural(total, 'feature')} in {plural(len(data['layers']), 'layer')}.",
            "", "In short", "", *short,
            "", "The sections follow, each with its count first. Where a section lists examples, the full list is in a "
            "CSV file beside this report, named with the pack and the section."]
    path = ledger.claim(out_dir / names["report"])
    path.write_text("\n".join(head + body) + "\n", encoding="utf-8", newline="\n")
    say(f"The quality report is {path}. Its full lists are CSV files beside it.")
    return path


def stage_folders_of(plan: list[tuple]) -> list[tuple[int, str, Path]]:
    """The finished stages of a plan from build.plan_stages, as (number, kind, folder)."""
    return [(n, stage["stage"], folder) for n, stage, _fp, folder, _done in plan if (folder / "finished.json").is_file()]


def report_command(name: str, folders, say=print, config_dir=None) -> int:
    """mapdata report <pack>: the report again, from the kept stage folders and the pack in the output folder."""
    from mapdata.paths import CONFIG_DIR
    from mapdata.pipeline.build import plan_stages, resolve_sources
    from mapdata.pipeline.errors import BuildStopped
    from mapdata.pipeline.settings import load_pack

    try:
        pack = load_pack(name, config_dir or CONFIG_DIR)
        target = folders.output / name / f"{name}.pack"
        if not target.is_file():
            raise BuildStopped(f"There is no pack {target}. Build it first: python -m mapdata build {name}")
        paths = resolve_sources(pack, folders)
        plan = plan_stages(pack, folders, {k: pack.sources[k].fingerprint(p) for k, p in paths.items()})
        kept = stage_folders_of(plan)
        if len(kept) < len(plan):
            say(f"Only {len(kept)} of the {len(plan)} stages have kept results for the settings now in "
                f"{name}.yaml, so the report may say less. Build the pack again to keep them all.")
        make_report(name, pack.data["title"], target, kept, folders.output / name / f"{name} build log.txt",
                    Ledger(folders.own), say)
    except BuildStopped as stop:
        say(stop.message)
        return 1
    return 0
