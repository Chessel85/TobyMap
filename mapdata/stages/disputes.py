"""Stage "disputes": disputed areas (P3-T2c, ANN-6, DAT-8, DP119, DP28).

Two things, in order:

1. Land held by two countries. OpenStreetMap puts the same land inside two countries in about
   15 places, such as Crimea and Abyei (DP119). The grid squares gave each piece of land to the
   smaller country, which picks a side. Here that land becomes a disputed area of its own, in the
   Countries layer, listing both countries as claimants with equal credit, in the order of their
   names. Each country keeps the rest of its land, so every point is still in one country (LOC-6).
   The land is found from the outlines as read (the osm-areas stage) where the build has them: the
   land in both countries' outlines that a country of the pack holds. Without them, as in the test
   pack, it is the land where two countries of the pack overlap.

2. Natural Earth's breakaway and disputed areas (public domain). Each with a note naming who holds
   and who claims it, such as "Admin. by Russia; Claimed by Ukraine", is matched to the pack's areas:
   an area of the layers in "mark" with at least "share" of its land inside it is marked disputed,
   with Natural Earth's name for it and its note, as the source's view (ANN-6). Areas Natural Earth
   gives no note, named in "include", are matched too, with the view that Natural Earth lists them
   as disputed.

An area that OpenStreetMap holds twice in one layer was marked disputed when it was read (DP104).
Many of those are copies made in mapping, not disputes, such as a town in Alberta held twice; so
here only those in disputed land stay disputed. The others keep the other copy's name, as
also_held_as, but are not said as disputed.

Settings:
* outlines: the stage whose outlines are used, osm-areas by default, if the build has one.
* held_twice: names for the land two countries hold, each with countries (the two ids), id and name.
  Land with no name here is called "Land claimed by" the two countries.
* min_km2: land held twice that is smaller than this is left as it is, 0.01 by default.
* source: the key of Natural Earth's breakaway and disputed areas; without it, step 2 is left out.
* mark: the layers whose areas are matched, countries, regions, islands and counties by default.
* share: the least share of an area's land inside Natural Earth's area, 0.9 by default.
* include: Natural Earth's areas, by name, to use though they have no note, such as Kosovo.
"""
from __future__ import annotations

import json
import re

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.stages.clip import polygonal
from mapdata.stages.geodesy import area_km2

MARK = ("countries", "regions", "islands", "counties")
OWN_KINDS = ("disputed", "unclaimed", "territory", "condominium")   # ids the build gives land it names itself
SOURCE_NAME = "Natural Earth"

# Natural Earth's notes are short; these are said in full, so a screen reader does not say "Admin dot".
WORDS = [(r"\bSelf admin\.", "Self-administered"), (r"\bAdmin\.? [Bb]y\b", "Administered by"),
         (r"\bU\.S\.A\.?", "the United States"), (r"\bU\.K\.", "the United Kingdom"), (r"\bAzer\.", "Azerbaijan"),
         (r"\bIs\.", "Islands"), (r"\bI\.", "Island"), (r"\bUN\b", "the United Nations")]


def plain_note(note: str) -> str:
    """Natural Earth's note in full words, with its parts joined as sentences: "Administered by Russia.
    Claimed by Ukraine." """
    text = note.strip()
    for pattern, words in WORDS:
        text = re.sub(pattern, words, text)
    parts = [p.strip() for p in text.split(";") if p.strip()]
    return " ".join(p[0].upper() + p[1:] + ("" if p.endswith(".") else ".") for p in parts)


def load_ids(folder, ids: set[str]) -> dict[str, object]:
    """The shapes of the features with these ids in a stage's folder, reading only those."""
    data = json.loads((folder / "features.json").read_text(encoding="utf-8"))
    out = {}
    with open(folder / "shapes.wkb", "rb") as f:
        for r, (a, n) in zip(data["records"], data["shapes"]):
            if r.get("id") in ids:
                f.seek(a)
                out[r["id"]] = shapely.from_wkb(f.read(n))
    return out


def held_twice_pairs(ctx, records, geoms) -> tuple[list[tuple[str, str]], dict[str, object]]:
    """The pairs of countries that hold the same land, and the outlines to find it with. From the join's list
    and the outlines as read, where the build has them; otherwise from the pack's own countries overlapping."""
    join = ctx.earlier.get("join")
    outlines_stage = ctx.earlier.get(ctx.settings.get("outlines", "osm-areas"))
    if join is not None and (join / "join.json").is_file() and outlines_stage is not None:
        listed = json.loads((join / "join.json").read_text(encoding="utf-8")).get("overlaps") or []
        pairs = sorted({tuple(sorted(o[1])) for o in listed if o[0] == "countries" and len(o[1]) == 2})
        return pairs, load_ids(outlines_stage, {i for p in pairs for i in p})
    idx = [i for i, r in enumerate(records) if r["layer"] == "countries"]
    arr = np.array([geoms[i] for i in idx], dtype=object)
    tree = shapely.STRtree(arr)
    left, right = tree.query(arr, predicate="intersects")
    pairs = set()
    for a, b in zip(left, right):
        if a < b and shapely.relate_pattern(arr[a], arr[b], "T********"):
            pairs.add(tuple(sorted((records[idx[a]]["id"], records[idx[b]]["id"]))))
    return sorted(pairs), {records[i]["id"]: geoms[i] for i in idx}


def colour_apart(records, geoms, shape, layer: str) -> int:
    """A colour number not used by the areas of the layer that touch the shape (AD-19)."""
    near = shapely.buffer(shape, 0.01)
    used = {records[i].get("colour") for i, g in enumerate(geoms)
            if records[i]["layer"] == layer and shapely.intersects(g, near)}
    return next(c for c in range(1, 100) if c not in used)


def make_held_twice(ctx, records, geoms) -> list[str]:
    """Step 1: land two countries hold becomes a disputed area of its own. Returns the new areas' ids."""
    s, line, log = ctx.settings, ctx.progress.line, ctx.progress.log
    names = {tuple(sorted(h["countries"])): h for h in s.get("held_twice") or []}
    min_km2 = float(s.get("min_km2", 0.01))
    pairs, outlines = held_twice_pairs(ctx, records, geoms)
    by_id = {r["id"]: i for i, r in enumerate(records)}
    country_name = {r["id"]: r["name"] for r in records if r["layer"] == "countries"}
    countries = [i for i, r in enumerate(records) if r["layer"] == "countries"]
    made = []
    for a, b in pairs:
        if a not in outlines or b not in outlines:
            log(f"Held twice: {a} and {b}, but the outline of one is missing; left as it is.")
            continue
        both = polygonal(shapely.intersection(outlines[a], outlines[b]))
        if both is None or both.is_empty:
            continue
        shapely.prepare(both)
        parts, holders = [], []
        for i in countries:
            if records[i].get("disputed_made") or not shapely.intersects(geoms[i], both):
                continue
            got = polygonal(shapely.intersection(geoms[i], both))
            if got is not None and not got.is_empty and area_km2(got) > 0:
                parts.append(got)
                holders.append(i)
        if not parts:
            continue
        land = polygonal(shapely.union_all(parts))
        km2 = area_km2(land)
        # A claimant not in the Countries layer, such as France, whose land there is metropolitan France, is the
        # area of it that held the land.
        held_ids = [records[i]["id"] for i in holders]
        claimants = []
        for c, other in ((a, b), (b, a)):
            if c in country_name:
                claimants.append(c)
            else:
                claimants.append(next((h for h in held_ids if h != other and h not in claimants), c))
        claimants = [x for _n, x in sorted((country_name.get(c, c), c) for c in claimants)]
        who = [country_name.get(c, c) for c in claimants]
        if km2 < min_km2:
            log(f"Held twice by {who[0]} and {who[1]}: {km2:.4f} km2, under {min_km2} km2, so left as it is.")
            continue
        named = names.get((a, b)) or {}
        fid = named.get("id") or f"disputed:{a.split(':')[-1]}-{b.split(':')[-1]}"
        name = named.get("name") or f"Land claimed by {who[0]} and {who[1]}"
        for i in holders:
            rest = polygonal(shapely.difference(geoms[i], land))
            geoms[i] = rest if rest is not None else shapely.MultiPolygon()
        rec = {"id": fid, "name": name, "layer": "countries", "type": "disputed land", "disputed": True,
               "claimants": claimants,
               "disputed_made": True}
        if named.get("wikidata"):
            rec["wikidata"] = named["wikidata"]
        if any(r.get("source_key") for r in records):
            rec["source_key"] = records[holders[0]].get("source_key")
        rec["colour"] = colour_apart(records, geoms, land, "countries")
        records.append(rec)
        geoms.append(land)
        by_id[fid] = len(records) - 1
        made.append(fid)
        line(f"Held twice: {name}, {km2:,.2f} km2, which {who[0]} and {who[1]} both hold, is now a disputed area "
             f"of its own, with both as claimants; it was in {', '.join(records[i]['name'] for i in holders)}.")
    # A place's areas (P3-T1j): where it is in the disputed land, its country is now that land.
    for fid in made:
        land = geoms[by_id[fid]]
        shapely.prepare(land)
        for r, g in zip(records, geoms):
            if r.get("within") and shapely.intersects(land, shapely.point_on_surface(g)):
                r["within"] = [{"id": fid, "layer": "countries"} if w.get("layer") == "countries" else w
                               for w in r["within"]]
    return made


def natural_earth(ctx, path) -> list[dict]:
    """Natural Earth's disputed areas to match: those with a note naming a claim, and those named in include."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    include = {str(n) for n in ctx.settings.get("include") or []}
    out = []
    for f in data["features"]:
        p = f["properties"]
        name = (p.get("BRK_NAME") or p.get("NAME") or "").strip().lstrip("﻿")
        note = (p.get("NOTE_BRK") or "").strip()
        if "laim" not in note and name not in include:
            continue
        geom = polygonal(shapely.make_valid(shapely.from_geojson(json.dumps(f["geometry"]))))
        if geom is None or geom.is_empty:
            continue
        view = plain_note(note) if note else f"{SOURCE_NAME} lists {name} as disputed."
        out.append({"name": name, "view": view, "geom": geom, "wikidata": p.get("WIKIDATAID")})
    return out


def mark_natural_earth(ctx, records, geoms, areas: list[dict]) -> int:
    """Step 2: mark the pack's areas inside Natural Earth's disputed areas. Returns how many were marked."""
    layers = set(ctx.settings.get("mark") or MARK)
    share = float(ctx.settings.get("share", 0.9))
    idx = [i for i, r in enumerate(records) if r["layer"] in layers and geoms[i] is not None
           and geoms[i].geom_type in ("Polygon", "MultiPolygon") and not geoms[i].is_empty]
    tree = shapely.STRtree(np.array([geoms[i] for i in idx], dtype=object))
    marked, found = 0, []
    for d in areas:
        shapely.prepare(d["geom"])
        hits = 0
        for j in tree.query(d["geom"], predicate="intersects"):
            i = idx[j]
            whole = area_km2(geoms[i])
            if whole <= 0:
                continue
            inside = polygonal(shapely.intersection(geoms[i], d["geom"]))
            if inside is None or area_km2(inside) < share * whole:
                continue
            r = records[i]
            r["disputed"] = True
            r["dispute"] = {"name": d["name"], "source": SOURCE_NAME, "view": d["view"]}
            hits += 1
            ctx.progress.log(f"Disputed, by {SOURCE_NAME}'s {d['name']}: {r['name']} ({r['id']}, {r['layer']}). "
                             f"{d['view']}")
        marked += hits
        found.append((d["name"], hits))
    missing = [n for n, h in found if h == 0]
    ctx.progress.line(f"{SOURCE_NAME}'s disputed areas: {len(areas)} used, {marked:,} areas of the pack marked "
                      f"disputed. With no area of the pack mostly inside: "
                      f"{', '.join(missing) if missing else 'none'}.")
    return marked


def run(ctx) -> None:
    records, geoms = features.load(ctx.previous)
    made = make_held_twice(ctx, records, geoms)
    if ctx.settings.get("source"):
        _src, path = ctx.source(ctx.settings["source"])
        mark_natural_earth(ctx, records, geoms, natural_earth(ctx, path))
    # Held twice in one layer (DP104): disputed only where the land is disputed.
    disputed_land = [g for r, g in zip(records, geoms) if r.get("disputed_made") or r.get("dispute")]
    tree = shapely.STRtree(np.array(disputed_land, dtype=object)) if disputed_land else None
    cleared = 0
    for r, g in zip(records, geoms):
        if r.get("also_held_as") and r.get("disputed") and not r.get("dispute"):
            p = shapely.point_on_surface(g)
            if tree is None or not len(tree.query(p, predicate="intersects")):
                del r["disputed"]
                cleared += 1
                ctx.progress.log(f"Held twice in one layer, but not in disputed land, so not said as disputed: "
                                 f"{r['name']} ({r['id']}); the other copy is {r['also_held_as'].get('name')}.")
    if cleared:
        ctx.progress.line(f"Areas held twice in one layer that are not in disputed land, so not said as disputed: "
                          f"{cleared}. The log lists them.")
    for r in records:
        r.pop("disputed_made", None)
        # Land the build names itself, such as Crimea, the West Bank or Bir Tawil, is OpenStreetMap's land.
        if r["layer"] == "countries" and r["id"].split(":")[0] in OWN_KINDS and "source" not in r:
            r["source"] = "osm"
    keep = [i for i, g in enumerate(geoms) if g is not None and not g.is_empty]
    features.save(ctx.folder, [records[i] for i in keep], [geoms[i] for i in keep], ctx.claim)
    ctx.progress.line(f"Disputed areas made from land held twice: {len(made)}.")
