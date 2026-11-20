"""Stage "corrections": the correction rules, applied to the features before the pack is written (P4-T4a, DMT-4).

A correction rule fixes a fault in the data without editing a shape. Each names one feature by its identifier, such
as osm:r62149, gives its reason, and does one of four things:

* rename: gives the feature a new name, and with local_name a new local name too.
* leave_out: leaves the feature out of the pack. It is dropped from every other feature's relationships too, and the
  counts of what is inside the areas that held it go down by one.
* change: moves the feature to another layer of the same geometry (areas, lines or places), or changes its kind (the
  record's type, such as bay or strait), or both.
* parent: sets the area the feature belongs to, by that area's identifier. The area becomes the feature's parent,
  and is put first in what it is inside, in place of any other area of the same layer the relationships stage found.

A rule may also give layer, to apply only to the feature of that identifier in that layer, where two layers take a
feature from one OpenStreetMap object, such as an island that is also a region.

The rules are in a YAML file, mapdata/config/corrections.yaml unless the stage's setting file names another (a path
from the repository's top folder), and in the stage's setting rules, a list of the same form, used by the tests. The
rules, as read, are in the stage's fingerprint (fingerprint_extra), so a changed rule runs this stage and those after
it again; a changed comment runs nothing. A rule with no identifier, no reason, or not exactly one of the four things
stops the build before any work, saying which rule and why.

The stage is placed just before the writing stage, so that a changed rule runs only the writing and the checks again,
never the long stages. It reads the files of the stage before (features.json, shapes.wkb and relationships.json,
all by each feature's index), and writes them again with only what the rules change: shapes.wkb is passed on
unchanged, linked where the drive allows, as the shapes' offsets stay the same, and so is relationships.json when no
rule leaves a feature out or sets a parent; a feature left out has its offsets
dropped from features.json, and every index in the relationships is renumbered.

Each rule applied, each rule whose identifier is not in the data, and each that is found but cannot be applied (such
as a layer the pack does not have), is listed in the build's log and in corrections.txt in the stage's folder, which
the quality report (P4-T11a) reads. corrections.json there holds the three counts, which the build's summary says.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import REPO
from mapdata.stages.relationships import FILE as REL_FILE

DEFAULT_FILE = "mapdata/config/corrections.yaml"
KINDS = ("rename", "leave_out", "change", "parent")
REPORT = "corrections.txt"
COUNTS = "corrections.json"

# How the relationships stage holds other features' indexes, by key (as relationships.by_id).
PLAIN_LISTS = ("in", "same", "crossed_by", "along", "crosses", "partly_by")
FIRST_OF_EACH = ("overlaps", "partly", "next", "near", "coast", "shores", "crossed_at")
NO_INDEXES = ("counts", "outline_km")
# What an area holds, for its counts: as the relationships stage counts them.
HOLDING_LISTS = ("in", "same", "crosses")
HOLDING_PAIRS = ("partly", "overlaps")
# Record fields that name another feature by its identifier.
ID_FIELDS = ("parent", "named_from", "sovereign_id")


# The rules ----------------------------------------------------------------------------------------------------------

def rules_path(stage: dict) -> Path:
    """The rules file named by the stage's setting file, from the repository's top folder, or the default."""
    return REPO / (stage.get("file") or DEFAULT_FILE)


def load_rules(stage: dict) -> list[dict]:
    """The rules of the stage's file and its own setting rules, in that order, each checked. Stops the build with
    the reason for a rule that cannot be read."""
    import yaml

    path = rules_path(stage)
    shown = stage.get("file") or DEFAULT_FILE
    if not path.is_file():
        raise BuildStopped(f"The correction rules file {shown} is not there. Make it, or change the corrections "
                           "stage's setting file, then build again.")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise BuildStopped(f"The correction rules file {shown} must start with 'rules:', followed by the rules.")
    out = [check_rule(r, n, shown) for n, r in enumerate(data.get("rules") or [], 1)]
    out += [check_rule(r, n, "the corrections stage's setting rules")
            for n, r in enumerate(stage.get("rules") or [], 1)]
    return out


def check_rule(rule, n: int, where: str) -> dict:
    """A rule as read, checked: an identifier, a reason, and exactly one of the four things a rule does."""
    def stop(why: str):
        raise BuildStopped(f"Correction rule {n} in {where} {why}. Mend it, then build again. "
                           "The header of mapdata/config/corrections.yaml explains each kind of rule.")

    if not isinstance(rule, dict):
        stop("is not a list of settings")
    if not rule.get("id"):
        stop("has no id, the identifier of the feature it corrects")
    if not str(rule.get("reason") or "").strip():
        stop(f"for {rule['id']} has no reason")
    kinds = [k for k in KINDS if k in rule]
    if len(kinds) != 1:
        stop(f"for {rule['id']} must do one thing, by one of: {', '.join(KINDS)}")
    unknown = sorted(set(rule) - {"id", "reason", "layer", "local_name", *KINDS})
    if unknown:
        stop(f"for {rule['id']} has settings mapdata does not know: {', '.join(unknown)}")
    kind = kinds[0]
    value = rule[kind]
    if kind == "rename" and not (isinstance(value, str) and value.strip()):
        stop(f"for {rule['id']} must give the new name after rename")
    if kind == "leave_out" and value is not True:
        stop(f"for {rule['id']} must say leave_out: true")
    if kind == "change" and not (isinstance(value, dict) and value and set(value) <= {"layer", "kind"}):
        stop(f"for {rule['id']} must give, after change, a new layer, a new kind, or both, such as "
             "change: {kind: strait}")
    if kind == "parent" and not (isinstance(value, str) and value.strip()):
        stop(f"for {rule['id']} must give the parent's identifier after parent")
    if "local_name" in rule and kind != "rename":
        stop(f"for {rule['id']} gives local_name, which only a rename rule may give")
    return {k: (str(v).strip() if isinstance(v, str) else v) for k, v in rule.items()}


def fingerprint_extra(stage: dict) -> dict:
    """The rules as read are what this stage uses besides its settings, so a changed rule runs it again. Read here,
    before any stage runs, so a rule that cannot be read stops the build before any work."""
    return {"rules": load_rules(stage)}


def describe(rule: dict) -> str:
    """A rule in plain words, for the log and the report."""
    fid = rule["id"] + (f" in the layer {rule['layer']}" if rule.get("layer") else "")
    if "rename" in rule:
        what = f"rename {fid} to {rule['rename']}"
        if rule.get("local_name"):
            what += f", with the local name {rule['local_name']}"
    elif "leave_out" in rule:
        what = f"leave out {fid}"
    elif "change" in rule:
        parts = [f"its layer to {rule['change']['layer']}"] if rule["change"].get("layer") else []
        parts += [f"its kind to {rule['change']['kind']}"] if rule["change"].get("kind") else []
        what = f"change {fid}: " + " and ".join(parts)
    else:
        what = f"set the parent of {fid} to {rule['parent']}"
    return f"{what}. Reason: {rule['reason']}"


# Applying them ------------------------------------------------------------------------------------------------------

def holders(rel: dict) -> set[int]:
    """The areas a feature counts as inside, for their counts, as the relationships stage counts them."""
    out: set[int] = set()
    for key in HOLDING_LISTS:
        out.update(rel.get(key, ()))
    for key in HOLDING_PAIRS:
        out.update(v[0] for v in rel.get(key, ()))
    return out


def _count(rel: dict[int, dict], area: int, layer: str, by: int) -> None:
    counts = rel.setdefault(area, {}).setdefault("counts", {})
    counts[layer] = counts.get(layer, 0) + by
    if counts[layer] <= 0:
        counts.pop(layer)
    rel[area]["counts"] = dict(sorted(counts.items()))


def apply(rules: list[dict], records: list[dict], rel: dict[int, dict], layers: dict) -> tuple[list[int], dict]:
    """Apply the rules to the records and the relationships, both by index, in place: the renames, changes and
    parents first, then the features left out. Returns the indexes left out and the outcome of each rule:
    {"applied": [lines], "not_found": [lines], "not_applied": [lines]}."""
    by_id: dict[str, list[int]] = {}
    for i, r in enumerate(records):
        by_id.setdefault(r["id"], []).append(i)
    out = {"applied": [], "not_found": [], "not_applied": []}
    leave: set[int] = set()

    def targets(rule) -> list[int]:
        found = by_id.get(rule["id"], [])
        if rule.get("layer"):
            found = [i for i in found if records[i]["layer"] == rule["layer"]]
        return found

    leaving = {i for rule in rules if "leave_out" in rule for i in targets(rule)}
    for rule in sorted(rules, key=lambda r: "leave_out" in r):   # those leaving a feature out last
        words = describe(rule)
        found = targets(rule)
        if not found:
            out["not_found"].append(f"Not found: {words} No feature has the identifier {rule['id']}"
                                    + (f" in the layer {rule['layer']}." if rule.get("layer") else "."))
            continue
        why = None
        if "rename" in rule:
            for i in found:
                records[i]["name"] = rule["rename"]
                if rule.get("local_name"):
                    records[i]["local_name"] = rule["local_name"]
        elif "leave_out" in rule:
            leave.update(found)
        elif "change" in rule:
            new_layer = rule["change"].get("layer")
            if new_layer and new_layer not in layers:
                why = f"the pack has no layer {new_layer}"
            elif new_layer and any(layers[records[i]["layer"]].geometry != layers[new_layer].geometry
                                   for i in found if records[i]["layer"] in layers):
                why = (f"the layer {new_layer} holds {layers[new_layer].geometry}s, and the feature is not one; "
                       "a rule cannot change a feature's shape")
            else:
                for i in found:
                    if new_layer:
                        records[i]["layer"] = new_layer
                    if rule["change"].get("kind"):
                        records[i]["type"] = rule["change"]["kind"]
        else:
            parents = [p for p in by_id.get(rule["parent"], []) if p not in leaving]
            if not parents:
                why = (f"the parent it gives, {rule['parent']}, is left out by another rule"
                       if rule["parent"] in by_id else
                       f"no feature has the identifier {rule['parent']}, given as its parent")
            elif any(p in found for p in parents):
                why = "a feature cannot be its own parent"
            else:
                for i in found:
                    set_parent(i, parents[0], records, rel)
        if why:
            out["not_applied"].append(f"Not applied: {words} It cannot be applied, as {why}.")
        else:
            many = f" It applied to {len(found)} features with that identifier." if len(found) > 1 else ""
            out["applied"].append(f"Applied: {words}{many}")
    return sorted(leave), out


def set_parent(i: int, parent: int, records: list[dict], rel: dict[int, dict]) -> None:
    """Make area `parent` the parent of feature i: its record's parent, first in what it is inside, in place of the
    other areas of the parent's layer it is inside, partly inside or overlapping; the counts of each area changed to
    match. The parent's own parents are not added: give each its own rule if needed."""
    layer = records[parent]["layer"]
    mine = rel.setdefault(i, {})
    before = holders(mine)
    mine["in"] = [parent] + [a for a in mine.get("in", ()) if records[a]["layer"] != layer]
    for key in ("partly", "overlaps"):
        if key in mine:
            kept = [v for v in mine[key] if records[v[0]]["layer"] != layer]
            if kept:
                mine[key] = kept
            else:
                del mine[key]
    after = holders(mine)
    own = records[i]["layer"]
    for area in before - after:
        _count(rel, area, own, -1)
    for area in after - before:
        _count(rel, area, own, +1)
    records[i]["parent"] = records[parent]["id"]
    if "within" in records[i]:   # a place's areas it is in, by layer and identifier (P3-T1j)
        records[i]["within"] = [w for w in records[i]["within"] if w.get("layer") != layer] + [
            {"id": records[parent]["id"], "layer": layer}]


def leave_out(leave: list[int], records: list[dict], shapes: list, rel: dict[int, dict]
              ) -> tuple[list[dict], list, dict[int, dict]]:
    """The records, their shapes' offsets and the relationships with the features at the indexes in leave taken
    out: every index renumbered, references to a feature left out dropped, and the counts of the areas that held it
    one less."""
    gone = set(leave)
    if not gone:
        return records, shapes, rel
    for i in gone:   # the areas that held it count one less of its layer
        for area in holders(rel.get(i, {})):
            if area not in gone:
                _count(rel, area, records[i]["layer"], -1)
    new = {}
    for i in range(len(records)):
        if i not in gone:
            new[i] = len(new)
    gone_ids = {records[i]["id"] for i in gone} - {records[i]["id"] for i in new}

    def fix(key, v):
        if key in PLAIN_LISTS:
            return [new[j] for j in v if j in new]
        if key in FIRST_OF_EACH:
            return [[new[x[0]], *x[1:]] for x in v if x[0] in new]
        if key == "water_in":
            return new.get(v)
        if key == "coast_stretches":
            for s in v["stretches"]:
                s["ends"] = [[lon, lat, None if o is None else new.get(o)] for lon, lat, o in s["ends"]]
                if s.get("water") is not None:
                    s["water"] = new.get(s["water"])
            return v
        if key in NO_INDEXES:
            return v
        raise ValueError(f"The corrections stage does not know how the relationship {key} names other features, "
                         "so cannot leave a feature out. Add it to mapdata/stages/corrections.py.")

    out_rel = {}
    for i, r in rel.items():
        if i in gone:
            continue
        fixed = {k: fix(k, v) for k, v in r.items()}
        out_rel[new[i]] = {k: v for k, v in fixed.items() if v not in ([], None)}
    out_records = [r for i, r in enumerate(records) if i not in gone]
    for r in out_records:
        for key in ID_FIELDS:
            if r.get(key) in gone_ids:
                del r[key]
        if "within" in r:
            r["within"] = [w for w in r["within"] if w.get("id") not in gone_ids]
    return out_records, [s for i, s in enumerate(shapes) if i not in gone], out_rel


# The stage ----------------------------------------------------------------------------------------------------------

def _copy(src, dst) -> None:
    """A file of the stage before, unchanged: linked where the drive allows, else copied."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def run(ctx) -> None:
    rules = load_rules(ctx.settings)
    shown = ctx.settings.get("file") or DEFAULT_FILE
    data = json.loads((ctx.previous / "features.json").read_text(encoding="utf-8"))
    records, shapes = data["records"], data["shapes"]
    rel_path = ctx.previous / REL_FILE
    rel = ({int(k): v for k, v in json.loads(rel_path.read_text(encoding="utf-8")).items()}
           if rel_path.is_file() else {})
    leave, outcome = apply(rules, records, rel, ctx.pack.layers)
    records, shapes, rel = leave_out(leave, records, shapes, rel)

    _copy(ctx.previous / "shapes.wkb", ctx.claim(ctx.folder / "shapes.wkb"))
    text = json.dumps({"records": records, "shapes": shapes}, ensure_ascii=False, sort_keys=True, indent=0)
    ctx.claim(ctx.folder / "features.json").write_text(text, encoding="utf-8", newline="\n")
    if rel_path.is_file() and not (leave or any("parent" in r for r in rules)):
        _copy(rel_path, ctx.claim(ctx.folder / REL_FILE))   # no rule changes a relationship: passed on unchanged
    elif rel_path.is_file():
        text = json.dumps({str(i): r for i, r in sorted(rel.items())}, sort_keys=True, separators=(",", ":"))
        ctx.claim(ctx.folder / REL_FILE).write_text(text, encoding="utf-8", newline="\n")

    n = {k: len(v) for k, v in outcome.items()}
    head = summary_line(n)
    lines = [f"Correction rules, from {shown}" + (" and the stage's own settings" if ctx.settings.get("rules") else "")
             + ".", head, *outcome["applied"], *outcome["not_found"], *outcome["not_applied"]]
    if leave:
        lines.append(f"Features left out: {len(leave)}.")
    ctx.claim(ctx.folder / REPORT).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    ctx.claim(ctx.folder / COUNTS).write_text(json.dumps(n, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    for line in outcome["applied"] + outcome["not_found"] + outcome["not_applied"]:
        ctx.progress.log(line)
    ctx.progress.line(head + (" The log lists each." if any(n.values()) else ""))


def summary_line(n: dict) -> str:
    """How many correction rules applied, were not found and could not be applied, in a sentence."""
    def rules(k):
        return f"{k} rule{'' if k == 1 else 's'}"

    line = f"Correction rules: {rules(n['applied'])} applied, {rules(n['not_found'])} whose feature was not found"
    if n.get("not_applied"):
        line += f", {rules(n['not_applied'])} found but not applied"
    return line + "."
