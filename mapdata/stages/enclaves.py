"""Stage "enclaves": enclaves and exclaves, found from the shapes alone (P3-T24g, DP207).

The words, from the definition in docs/design/Discussion points detail - responses.md:

* An exclave is a part of a country with a land border, cut off from its main part by another country: Llivia
  of Spain, Kaliningrad of Russia, Ceuta and Melilla of Spain on the African coast.
* An enclave is an area wholly surrounded by one other country, with no sea: Llivia is an enclave in France; San
  Marino, the Vatican and Lesotho are whole countries that are enclaves.
* Islands and other parts with no land border, such as Hawaii, are neither.

How they are found, for each country of the Countries layer and its distant parts (DP191), which are its own land:

* The country's largest part is its main part. Each other part with a land border with another country is an
  exclave when it is cut off from the main part by another country's land: at least land_share of the shortest
  line between them is over other countries' land, as from Llivia, Alaska or Nakhchivan. A part the sea cuts off,
  such as Northern Ireland or Peninsular Malaysia, is not. A part across the sea is an exclave only when it is a
  small part of a much larger country's coast: no more than sea_km2, and the land it borders at least coast_ratio
  times its size, as for Ceuta, Melilla and Point Roberts. French Guiana, Saint Martin and Sebatik Island are not.
  If an exclave touches only one other country, and no sea, it is also an enclave there.
* An exclave that is part of its country's own area, such as Llivia, becomes an area of the Enclaves and exclaves
  layer, so "where am I" can say it. It is named by the names setting, if one of its points is in it; else after
  the region or county of its country that is most of it and not much more, such as Alaska or Cabinda; else after
  the largest place in it, from the Cities and towns layer; else "Exclave of" its country. An exclave that is
  already an area of its own, such as Ceuta, is marked on its own record.
* A whole country wholly surrounded by one other, with no sea, is an enclave in it.

Each record gets what the core says and lists in Details: on an exclave, sovereign, sovereign_id, beside (the ids
of the countries it borders), coast (whether it touches the sea) and enclave (whether it is one); on a country,
exclaves (the ids of its exclaves) and enclaves (the ids of the enclaves inside it); on a whole country that is
an enclave, enclave_in. The log lists every one found, with its size.

Before that, the stage tidies unclaimed land (mapdata/stages/unclaimed.py, P3-T26b), as it needs the towns: its
setting "unclaimed" holds min_km2.

Settings: min_km2 (0.01), the least land for a part to be looked at; border_km (0.05), the least shared border
for two countries to touch; coast_km (0.2), the least outline left over, once the land borders are taken away,
for a part to be on the coast; land_share (0.5); coast_ratio (100); sea_km2 (1000); names, a list of {point: [lon, lat], name}
or {box: [west, south, east, north], name, of: the country's name}, for exclaves whose largest place is a village,
which the Cities and towns layer does not hold, such as Llivia, or a cluster of them, such as Baarle-Hertog.
"""
from __future__ import annotations

import time

import numpy as np
import shapely

from mapdata.pipeline import features
from mapdata.stages.relationships import lengths_km

LAYER = "countries"
EXCLAVES = "exclaves"
ID_PREFIX = "exclave:"
OWN_TYPES = ("disputed land", "unclaimed land", "condominium")
SETTINGS = {"min_km2": 0.01, "border_km": 0.05, "coast_km": 0.2, "land_share": 0.5, "coast_ratio": 100.0, "sea_km2": 1000.0,
            "names": [], "unclaimed": {}}


def _km2(g) -> float:
    from mapdata.stages import continents

    return float(continents.km2(g))


def _borders(part, others: list[tuple[int, object]], border_km: float) -> dict[int, float]:
    """The km of border a part shares with each of the other countries' shapes it touches."""
    edge = shapely.boundary(part)
    found = {}
    for i, g in others:
        if not shapely.intersects(g, part):   # g is prepared
            continue
        shared = shapely.intersection(edge, shapely.boundary(g))
        km = float(lengths_km([shared])[0]) if not shared.is_empty else 0.0
        if km >= border_km:
            found[i] = km
    return found


def find(records: list[dict], geoms: list, settings: dict | None = None, log=print) -> list[dict]:
    """The enclaves and exclaves, as [{"sovereign": i, "shape": part, "area": index or None, "beside": {i: km},
    "coast": bool, "enclave": bool}]; "area" is the index of an area of its own, such as a distant part, or None
    for a part of the country's own area. Whole countries that are enclaves come with "whole": True."""
    s = {**SETTINGS, **(settings or {})}
    countries = [i for i, r in enumerate(records) if r.get("layer") == LAYER and r.get("type") not in OWN_TYPES
                 and geoms[i] is not None and not geoms[i].is_empty]
    tree = shapely.STRtree([geoms[i] for i in countries])
    for i in countries:
        shapely.prepare(geoms[i])
    parts_of: dict[int, list] = {}   # a sovereign state's index: its parts [(part, area index or None)]
    index_of = {records[i]["id"]: i for i in countries}
    for i in countries:
        r = records[i]
        owner = index_of.get(r.get("sovereign_id"), i) if r.get("sovereign_id") else i
        own = r.get("sovereign_id") is None
        for p in shapely.get_parts(geoms[i]):
            if not p.is_empty:
                parts_of.setdefault(owner, []).append((p, None if own else i))
    found, seen = [], set()
    for owner, parts in parts_of.items():
        own_parts = [p for p, a in parts if a is None]
        main = max(own_parts, key=_km2) if own_parts else None
        mine = {owner} | {a for _p, a in parts if a is not None}
        for part, area in parts:
            if part is main or _km2(part) < s["min_km2"]:
                continue
            # Other countries' boxes first: an island near only its own country costs nothing more.
            near = [countries[k] for k in tree.query(part).tolist() if countries[k] not in mine]
            beside = _borders(part, [(j, geoms[j]) for j in near], s["border_km"]) if near else {}
            if not beside:
                continue   # an island or a part with no land border: neither
            if main is not None and not _cut_off_by_land(part, main, tree, countries, geoms, mine, s["land_share"]) \
                    and not (_km2(part) <= s["sea_km2"] and _on_a_larger_coast(part, beside, geoms, s["coast_ratio"])):
                continue   # the sea cuts it off, and it is not a small part of a much larger country's coast
            key = (owner, round(_km2(part), 3), tuple(np.round(shapely.bounds(part), 5)))
            if key in seen:
                continue   # the same part twice, as when an area of its own repeats its country's land
            seen.add(key)
            outline = float(lengths_km([shapely.boundary(part)])[0])
            coast = outline - sum(beside.values()) >= s["coast_km"]
            found.append({"sovereign": owner, "shape": part, "area": area, "beside": beside, "coast": coast,
                          "enclave": len(beside) == 1 and not coast})
    # Whole countries wholly inside one other, with no sea, such as San Marino.
    for i in countries:
        r = records[i]
        if r.get("sovereign_id") or len(shapely.get_parts(geoms[i])) != 1:
            continue
        near = [countries[k] for k in tree.query(geoms[i]).tolist() if countries[k] != i]
        beside = _borders(geoms[i], [(j, geoms[j]) for j in near], s["border_km"])
        if len(beside) != 1:
            continue
        outline = float(lengths_km([shapely.boundary(geoms[i])])[0])
        if outline - sum(beside.values()) < s["coast_km"]:
            found.append({"sovereign": i, "shape": geoms[i], "area": i, "beside": beside, "coast": False,
                          "enclave": True, "whole": True})
    return found


def _cut_off_by_land(part, main, tree, countries: list[int], geoms: list, mine: set, share: float) -> bool:
    """Whether at least share of the shortest line from a part to its country's main part is over other countries'
    land, so another country cuts it off, not the sea."""
    line = shapely.shortest_line(part, main)
    length = shapely.length(line)
    if length <= 0:
        return False
    over = 0.0
    for k in tree.query(line).tolist():
        j = countries[k]
        if j in mine:
            continue
        over += shapely.length(shapely.intersection(line, geoms[j]))
    return over / length >= share


def _on_a_larger_coast(part, beside: dict, geoms: list, ratio: float) -> bool:
    """Whether the land a part across the sea borders is at least ratio times its size: a small part of a much
    larger country's coast, as Ceuta is of Morocco's, not an island two countries share."""
    size = _km2(part)
    for j in beside:
        touching = [q for q in shapely.get_parts(geoms[j]) if shapely.intersects(q, part)]
        if touching and max(_km2(q) for q in touching) >= ratio * size:
            return True
    return False


def _place_name(part, owner_name: str, named: list[tuple[dict, object]], towns: list[tuple[dict, object]],
                by_hand: list[dict]) -> str | None:
    """An exclave's name: by hand, else its country's region or county that is most of it and not much more,
    else the largest place in it, by population."""
    for n in by_hand:
        if n.get("of") and n["of"] != owner_name:
            continue
        where = shapely.box(*n["box"]) if n.get("box") else shapely.Point(n["point"])
        if shapely.intersects(part, where):
            return n["name"]
    size = _km2(part)
    best = None
    for r, g in named:
        if not shapely.intersects(part, g):
            continue
        share = _km2(shapely.intersection(part, g)) / size if size > 0 else 0.0
        whole = _km2(g)
        if share >= 0.9 and whole <= 2.0 * size and (best is None or whole < best[0]):
            best = (whole, r["name"])
    if best:
        return best[1]
    inside = [(r.get("population") or 0, r["name"]) for r, g in towns if shapely.intersects(part, g)]
    return max(inside)[1] if inside else None


def apply(records: list[dict], geoms: list, found: list[dict], settings: dict | None = None, log=print) -> list:
    """Mark the records, and make an area of the Enclaves and exclaves layer for each exclave that is part of its
    country's own area. Returns the new (record, shape)s."""
    s = {**SETTINGS, **(settings or {})}
    towns = [(r, g) for r, g in zip(records, geoms) if r.get("layer") == "towns" and g is not None and r.get("name")]
    named = {}   # the regions and counties of each country that has exclaves, by country id
    owners = {records[f["sovereign"]]["id"] for f in found}
    regions = {r["id"]: r for r in records if r.get("layer") == "regions" and r.get("parent") in owners}
    for r, g in zip(records, geoms):
        if g is None or not r.get("name"):
            continue
        if r.get("layer") == "regions" and r.get("parent") in owners:
            named.setdefault(r["parent"], []).append((r, g))
        elif r.get("layer") == "counties" and r.get("parent") in regions:
            named.setdefault(regions[r["parent"]]["parent"], []).append((r, g))
    new = []
    order = sorted(found, key=lambda f: (records[f["sovereign"]]["id"],
                                         tuple(np.round(shapely.get_coordinates(shapely.point_on_surface(f["shape"]))[0], 5))))
    counts: dict[int, int] = {}
    for f in order:
        owner = records[f["sovereign"]]
        beside_ids = [records[j]["id"] for j in sorted(f["beside"], key=lambda j: -f["beside"][j])]
        where = ", ".join(records[j]["name"] for j in sorted(f["beside"], key=lambda j: -f["beside"][j]))
        if f.get("whole"):
            owner["enclave_in"] = beside_ids
            records[next(iter(f["beside"]))].setdefault("enclaves", []).append(owner["id"])
            log(f"Enclave: {owner['name']}, a whole country, {_km2(f['shape']):,.2f} km2, inside {where}.")
            continue
        info = {"sovereign": owner.get("sovereign") or owner["name"], "sovereign_id": owner["id"],
                "beside": beside_ids, "coast": f["coast"], "enclave": f["enclave"]}
        if f["area"] is not None:   # an area of its own, such as Ceuta
            rec = records[f["area"]]
            rec["exclave"] = info
            fid = rec["id"]
            name = rec["name"]
        else:
            counts[f["sovereign"]] = counts.get(f["sovereign"], 0) + 1
            name = _place_name(f["shape"], owner["name"], named.get(owner["id"], []), towns, s["names"]) \
                or f"Exclave of {owner['name']}"
            pt = shapely.get_coordinates(shapely.point_on_surface(f["shape"]))[0]
            fid = f"{ID_PREFIX}{owner['id']}:{pt[1]:.3f}:{pt[0]:.3f}"
            rec = {"id": fid, "layer": EXCLAVES, "name": name, "type": "enclave" if f["enclave"] else "exclave",
                   "parent": owner["id"], "exclave": info}
            new.append((rec, f["shape"]))
        owner.setdefault("exclaves", []).append(fid)
        if f["enclave"]:
            records[next(iter(f["beside"]))].setdefault("enclaves", []).append(fid)
        kind = "Enclave and exclave" if f["enclave"] else "Exclave"
        log(f"{kind}: {name}, of {owner['name']}, {_km2(f['shape']):,.2f} km2, beside {where}"
            + (", on the coast." if f["coast"] else "."))
    return new


def run(ctx) -> None:
    t = time.perf_counter()
    records, geoms = features.load(ctx.previous)
    settings = {k: v for k, v in ctx.settings.items() if k in SETTINGS}
    # Unclaimed land tidied first, with the towns this stage has (P3-T26b, DP205): slivers left out, the rest named.
    from mapdata.stages import unclaimed

    records, geoms, left_out = unclaimed.tidy(records, geoms, settings.get("unclaimed"), ctx.progress.log)
    ctx.progress.line(f"Unclaimed land: {left_out} areas under "
                      f"{(settings.get('unclaimed') or {}).get('min_km2', unclaimed.SETTINGS['min_km2'])} km2 left out. "
                      f"The log lists each one.")
    found = find(records, geoms, settings, ctx.progress.log)
    new = apply(records, geoms, found, settings, ctx.progress.log)
    for rec, g in new:
        records.append(rec)
        geoms.append(g)
    features.save(ctx.folder, records, geoms, ctx.claim)
    whole = sum(1 for f in found if f.get("whole"))
    ctx.progress.line(f"Enclaves and exclaves: {len(found) - whole} exclaves, of which "
                      f"{sum(1 for f in found if f['enclave'] and not f.get('whole'))} are enclaves, and {whole} whole "
                      f"countries that are enclaves, found in {time.perf_counter() - t:.0f} seconds. "
                      f"{len(new)} are new areas of the Enclaves and exclaves layer. The log lists each one.")
