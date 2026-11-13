"""Names for each country's tiers, from Wikidata (DP181, P3-T17, P3-T2a).

Every region is "region" and every county "county" unless the tiers record names them. The PO
chose (DP181, option 1) to take the names from Wikidata's kind of each area ("instance of"), and to
store them in the tiers record, so they are worked out once and then read from there.

`mapdata tier-names <pack>` reads the features the pack's wikidata stage kept, with each area's
kinds, and for each country and layer:

* each area's kinds are cut to the words before " of " or " in ", and a leading "U.S." is dropped,
  so "state of the United States", "U.S. state" and "state of Brazil" are all "state";
* kinds that say nothing of the tier, such as "administrative territorial entity", are left out;
* the word most of the country's areas in the layer share names the layer for that country, if at
  least half have it: Kansas is a "state of the United States";
* an area without that word, but with another, keeps its own, so Yukon is a "territory of Canada"
  among Canada's provinces.

It writes them under "names" in mapdata/config/tiers.yaml, by country, keeping every country already
there, so a name corrected by hand is never overwritten. Countries with their own tiers in the
record, such as the United Kingdom, are left to it. The report lists every name given.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

LAYERS = ("regions", "counties")
# Kinds that say nothing about which tier an area is.
VAGUE = re.compile(r"administrative|subdivision|entity|disputed|historical|former|ISO 3166|territorial unit|"
                   r"^(big |largest )?city$|^town$|capital|^island|exclave|enclave|human settlement|populated place|"
                   r"car-free|^list|^lake|^metropolis|^global city|^megacity", re.I)
MARKER = "# Names of each country's tiers"


def word_of(kind: str) -> str | None:
    """A kind as a tier's name: "state of the United States" is "state", "U.S. state" is "state"."""
    text = re.sub(r"^U\.S\.\s+", "", kind.strip())
    text = re.split(r"\s+(?:of|in)\s+", text, maxsplit=1)[0].strip()
    if not text or VAGUE.search(kind) or VAGUE.search(text):
        return None
    return text[0].lower() + text[1:] if not text[:2].isupper() else text


def country_of(r: dict, by_id: dict) -> str | None:
    for _ in range(4):
        if r is None or r["layer"] == "countries":
            break
        r = by_id.get(r.get("parent"))
    return r["id"] if r is not None and r["layer"] == "countries" else None


def work_out(records: list[dict], skip: set[str] = frozenset()) -> dict[str, dict]:
    """{country id: {"name": its name, layer: word, "areas": {area id: word}}} for the countries with names."""
    by_id = {r["id"]: r for r in records}
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        if r["layer"] in LAYERS and r.get("type") != "region used as county":
            c = country_of(r, by_id)
            if c and c not in skip:
                groups.setdefault((c, r["layer"]), []).append(r)
    out: dict[str, dict] = {}
    for (country, layer), areas in sorted(groups.items()):
        words_each = [sorted({w for w in (word_of(k) for k in r.get("kinds") or []) if w}) for r in areas]
        counts = Counter(w for ws in words_each for w in ws)
        if not counts:
            continue
        top, n = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        entry = out.setdefault(country, {"name": by_id[country]["name"]})
        if n * 2 >= len(areas):
            entry[layer] = top
        else:
            top = None
        for r, ws in zip(areas, words_each):
            if ws and top not in ws:
                own = min(ws, key=lambda w: (-counts[w], w))
                if counts[own] >= 2:   # a kind no other area of the country shares is taken as noise
                    entry.setdefault("areas", {})[r["id"]] = own
        if len(entry) == 1:
            del out[country]
    # An area does not take, as its own, the name its country uses for another layer: Spain's single-province
    # communities link their province to the community in Wikidata, so Madrid's county would be "autonomous
    # community of Community of Madrid".
    for entry in out.values():
        others = {entry.get(layer) for layer in LAYERS}
        if entry.get("areas"):
            entry["areas"] = {a: w for a, w in entry["areas"].items() if w not in others}
            if not entry["areas"]:
                del entry["areas"]
    return {c: e for c, e in out.items() if len(e) > 1}


def by_name(areas: dict[str, str]) -> dict[str, list[str]]:
    """{area id: name} as {name: [area ids]}."""
    out: dict[str, list[str]] = {}
    for a, w in areas.items():
        out.setdefault(w, []).append(a)
    return out


def from_record(entry: dict) -> dict:
    """A country's names as the record holds them, with areas as {name: [ids]}, made {area id: name}."""
    out = {k: v for k, v in (entry or {}).items() if k != "areas"}
    areas = (entry or {}).get("areas") or {}
    out["areas"] = {str(a): str(w) for w, ids in areas.items() for a in (ids or [])} if areas else {}
    if not out["areas"]:
        del out["areas"]
    return out


def names_block(names: dict[str, dict]) -> str:
    """The names section of the tiers record, as YAML text, a country to a line or two."""
    lines = [MARKER + ", from Wikidata's kind of each area (DP181), written by mapdata tier-names.",
             "# Each country has the name of its regions' tier and of its counties' tier, and any area named on its",
             "# own. A country already here is kept as it is, so correct a name here by hand. A name is said in",
             "# Details in place of the tier's word: Kansas, \"state of the United States\".",
             "names:"]
    if not names:
        lines[-1] = "names: {}"
    for cid in sorted(names, key=lambda c: (names[c].get("name", ""), c)):
        e = names[cid]
        lines.append(f"  {cid}:   # {e.get('name', '')}")
        for layer in LAYERS:
            if e.get(layer):
                lines.append(f"    {layer}: {json.dumps(e[layer], ensure_ascii=False)}")
        if e.get("areas"):   # grouped by name, a name to a line: the areas that have it
            lines.append("    areas:")
            for word, ids in sorted(by_name(e["areas"]).items()):
                lines.append(f"      {json.dumps(word, ensure_ascii=False)}: [{', '.join(sorted(ids))}]")
    return "\n".join(lines) + "\n"


def write_names(path: Path, found: dict[str, dict]) -> tuple[dict, list[str]]:
    """Merge the names found into the tiers record, keeping every country already named. Returns the names and
    the countries added."""
    import yaml

    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    have = {str(k): from_record(v) for k, v in (data.get("names") or {}).items()}
    added = [c for c in sorted(found) if c not in have]
    for c in added:
        have[c] = found[c]
    for c, e in have.items():   # the country's name, for the comment, if it was lost
        e.setdefault("name", found.get(c, {}).get("name", ""))
    head = text.split(MARKER)[0].rstrip("\n")
    if "\nnames:" in head:   # a names section written by hand, without the marker
        head = head.split("\nnames:")[0].rstrip("\n")
    path.write_text(head + "\n\n" + names_block(have), encoding="utf-8", newline="\n")
    return have, added


def run(pack: str, folders, tiers_path: Path, say=print) -> int:
    from mapdata.stages.write import load_tiers

    found = sorted((p.parent for p in (folders.working / pack).glob("*-wikidata-*/finished.json")),
                   key=lambda p: p.stat().st_mtime)
    if not found:
        say(f"The pack {pack} has no finished wikidata stage in the working folder. Build it first.")
        return 1
    folder = found[-1]
    records = json.loads((folder / "features.json").read_text(encoding="utf-8"))["records"]
    tiers = load_tiers(tiers_path)
    names = work_out(records, skip=set(tiers["countries"]))
    have, added = write_names(tiers_path, names)
    say(f"Read the kinds of each area from {folder}.")
    for c in added:
        e = have[c]
        parts = [f"{layer} are called {e[layer]}" for layer in LAYERS if e.get(layer)]
        if e.get("areas"):
            parts.append(f"{len(e['areas'])} areas have their own: " + ", ".join(
                sorted(set(e["areas"].values()))))
        say(f"{e['name']}: {'; '.join(parts)}.")
    say(f"Names written for {len(added)} countries into {tiers_path.name}; {len(have) - len(added)} were there "
        "already and are kept as they are.")
    return 0
