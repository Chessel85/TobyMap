"""Stage "distant-parts": a country's parts on another continent become areas of their own (DP191, DP190, LOC-6).

The product owner decided that France and French Guiana count as separate countries, and that the same rule
separates Hawaii from the United States and the Canary Islands from Spain (DP191, option 1). This stage runs
after the countries are final and before the continents, so every later stage sees the new areas, and every
point is still in exactly one area of the Countries layer (LOC-6).

* A country's parts are put in groups, and each group given a continent, exactly as the continents stage does:
  the same settings, mapdata/config/continents.yaml, and the same code. A group on a different continent from
  the country's main group is a distant part. Alaska stays in the United States, as it is in North America;
  Ceuta and Melilla stay in Spain, as they are within distant_km of it (architecture 6.12). Countries the
  continents settings split, such as Russia, are cut along continent lines instead, and are left whole here.
* The distant land is shared out by the country's regions, then by the counties of those regions: an area with
  at least min_share of its land in the country's distant parts becomes an area of the Countries layer, with its
  name, its Wikidata link and an id made from its own, so a rebuild gives the same id (DMT-1). So the Dutch
  Caribbean islands are Aruba, Curacao and the others, not one area; and Easter Island is named by its own
  county, as its region, Valparaiso, is mostly on the mainland.
  A region or county with the country's own name is passed over, as the Netherlands' region holding only its
  Caribbean municipalities would otherwise name them all "Netherlands".
* Land left over is given to the nearest new area within distant_km; failing that, it is one area for each
  group, named after its largest named island, such as Wake Island, or with none, after its country and
  continent, such as "Norway in Antarctica". The log lists these.
* Each new area records its country as sovereign, as the country units do (DP86), so Details says, for example,
  "region of the United States". It is not inside its country: its country is not its parent, and France's
  neighbours are no longer Brazil and Suriname. A region that became an area of its own has it as its parent.

Settings: min_share, the least share of a region's or county's land in the distant parts, 0.5 by default.
whole: countries whose land is all shared out this way, none kept, each with the country to name as the
sovereign state of the new areas, such as {osm:r2202162: osm:r1403916}: what is left of OpenStreetMap's whole
French state, in Oceania, after the country units (DP86), with metropolitan France as sovereign (DP192). The
country itself is then taken away; anything still naming it as parent names its sovereign state instead.
"""
from __future__ import annotations

import json
import shutil
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

from mapdata.paths import CONFIG_DIR
from mapdata.stages import continents
from mapdata.stages.clip import polygonal

LAYER = "countries"
TYPE = "distant part"
ID_PREFIX = "part:"
# Land the build names itself in the Countries layer, which is not a country with parts of its own (P3-T2c).
OWN_TYPES = ("disputed land", "unclaimed land", "condominium", "territory", TYPE)
NAMING_LAYERS = ("regions", "counties")


def fingerprint_extra(stage: dict) -> dict:
    """The continents settings decide which parts are distant, so they are part of what the stage reads."""
    return {"continents": (CONFIG_DIR / continents.SETTINGS).read_text(encoding="utf-8")}


# Finding the distant parts ---------------------------------------------------------------------------

def distant_groups(geom, zone_geoms: list, tree, distant_km: float,
                   whole: bool = False) -> tuple[list, list[tuple[int, list]]]:
    """A country's parts kept with it, and its distant groups as (zone, parts), using the continents stage's
    rule: the group with the largest part is the main group, and a group whose continent differs is distant.
    With whole, every group is shared out and none kept (DP192)."""
    parts = shapely.get_parts(geom)
    parts = parts[~shapely.is_empty(parts)]
    if len(parts) < 2 and not whole:
        return list(parts), []
    if len(parts) == 0:
        return [], []
    gid = continents.groups(parts, distant_km)
    sh = continents.shares(parts, zone_geoms, tree)
    by_group: dict = defaultdict(lambda: defaultdict(float))
    for g, s in zip(gid, sh):
        for z, a in s.items():
            by_group[g][z] += a
    zone_of = {g: max(t, key=lambda z: (t[z], -z)) for g, t in by_group.items()}
    sizes = [continents.km2(p) for p in parts]
    main_zone = zone_of[gid[int(np.argmax(sizes))]]
    kept, far = [], defaultdict(list)
    for g, p in zip(gid, parts):
        if zone_of[g] == main_zone and not whole:
            kept.append(p)
        else:
            far[g].append(p)
    return kept, sorted(((zone_of[g], ps) for g, ps in far.items()),
                        key=lambda zp: tuple(shapely.get_coordinates(shapely.point_on_surface(zp[1][0]))[0]))


def share_out(far: list[tuple[int, list]], naming: list[tuple[dict, object]], islands: list[tuple[dict, object]],
              min_share: float, distant_km: float):
    """The distant land shared out by the naming areas, regions first, then counties. Returns
    [(naming record or None, zone, shape)]. An area with at least min_share of its land in the land left takes
    it; then each part left within distant_km of an area made goes to the nearest. Land still left is one area
    for each group, named by the largest named island in it, or with no naming record when it has none."""
    land = polygonal(shapely.union_all([p for _z, ps in far for p in ps]))
    zone_at = [(z, shapely.union_all(ps)) for z, ps in far]
    left = land
    units: list[list] = []
    for rec, g in naming:
        if left.is_empty or not shapely.intersects(g, left):
            continue
        got = polygonal(shapely.intersection(g, left))
        size = continents.km2(got)
        if size <= 0 or size < min_share * continents.km2(g):
            continue
        units.append([rec, got])
        left = polygonal(shapely.difference(left, got))
    leftover: dict[int, list] = defaultdict(list)
    reach = distant_km / continents.KM_PER_DEGREE
    for p in shapely.get_parts(left):
        if p.is_empty or continents.km2(p) <= 0:
            continue
        near = [(shapely.distance(p, u[1]), n) for n, u in enumerate(units)]
        d, n = min(near) if near else (None, None)
        if n is not None and d <= reach:
            units[n][1] = polygonal(shapely.union(units[n][1], p))
        else:
            g = next((i for i, (_z, s) in enumerate(zone_at) if shapely.intersects(s, p)), 0)
            leftover[g].append(p)
    out = []
    for rec, shape in units:
        pt = shapely.point_on_surface(shape)
        z = next((z for z, s in zone_at if shapely.intersects(s, pt)), zone_at[0][0])
        out.append((rec, z, shape))
    for g, ps in sorted(leftover.items()):
        shape = polygonal(shapely.union_all(ps))
        sizes = [(continents.km2(shapely.intersection(ig, shape)), rec["name"], n)
                 for n, (rec, ig) in enumerate(islands) if shapely.intersects(ig, shape)]
        best = max(sizes, key=lambda s: (s[0], s[1])) if sizes else None
        out.append((islands[best[2]][0] if best and best[0] > 0 else None, zone_at[g][0], shape))
    return out


def colour_apart(shape, others: list[tuple[int | None, object]]) -> int:
    """A colour number not used by the areas that touch the shape (AD-19)."""
    near = shapely.buffer(shape, 0.01)
    used = {c for c, g in others if g is not None and shapely.intersects(g, near)}
    return next(c for c in range(1, 100) if c not in used)


# Reading only what is needed ---------------------------------------------------------------------------

def read_shapes(folder: Path, offsets: list, indexes) -> dict[int, object]:
    out = {}
    with open(Path(folder) / "shapes.wkb", "rb") as f:
        for i in sorted(indexes):
            a, n = offsets[i]
            f.seek(a)
            out[i] = shapely.from_wkb(f.read(n))
    return out


# The stage ----------------------------------------------------------------------------------------

def split_countries(records: list[dict], shape_of, settings: dict, min_share: float, line=print, log=print,
                    whole: dict[str, str] | None = None):
    """The work of the stage on records and their shapes, for the stage and its tests. shape_of(indexes) gives
    {index: shape}. whole gives countries whose land is all shared out, each with the country to name as the
    sovereign state of its new areas (DP192). Returns (new records with their shapes, {index: new shape, or
    None for a country with no land left} for countries that lost land, {index: new parent} for regions)."""
    whole = whole or {}
    zs = continents.zones(settings)
    zone_geoms = [g for _c, g in zs]
    tree = shapely.STRtree(zone_geoms)
    split_ids = {s["wikidata"] for s in settings.get("split") or []}
    distant_km = float(settings.get("distant_km", 300))
    countries = [i for i, r in enumerate(records)
                 if r.get("layer") == LAYER and r.get("type") not in OWN_TYPES and r.get("wikidata") not in split_ids]
    all_countries = [i for i, r in enumerate(records) if r.get("layer") == LAYER]
    shapes = shape_of(all_countries)
    found: dict[int, tuple[list, list]] = {}
    for i in countries:
        g = shapes.get(i)
        if g is None or g.is_empty:
            continue
        kept, far = distant_groups(g, zone_geoms, tree, distant_km, whole=records[i]["id"] in whole)
        if far:
            found[i] = (kept, far)
    if not found:
        return [], {}, {}
    # The regions of those countries, and the counties of those regions, are the names to share out by.
    country_ids = {records[i]["id"]: i for i in found}
    region_of = {i: records[i]["parent"] for i, r in enumerate(records)
                 if r.get("layer") == "regions" and r.get("parent") in country_ids}
    region_ids = {records[i]["id"]: c for i, c in region_of.items()}
    county_of = {i: region_ids[r["parent"]] for i, r in enumerate(records)
                 if r.get("layer") == "counties" and r.get("parent") in region_ids}
    # Named islands, which have no parent, last: they name land in no region or county, such as Wake Island.
    islands = [i for i, r in enumerate(records) if r.get("layer") == "islands" and r.get("name")
               and not str(r.get("type", "")).startswith("unnamed")]
    named_shapes = shape_of(list(region_of) + list(county_of) + islands)
    island_tree = shapely.STRtree([named_shapes[i] for i in islands]) if islands else None
    index_of = {records[i]["id"]: i for i in region_of}
    naming: dict[str, list] = defaultdict(list)
    for i, c in list(region_of.items()) + list(county_of.items()):
        naming[c].append((NAMING_LAYERS.index(records[i]["layer"]), records[i].get("name") or "", i))
    new, changed, reparent = [], {}, {}
    colours = [(records[i].get("colour"), shapes.get(i)) for i in all_countries]
    for i, (kept, far) in found.items():
        country = records[i]
        order = list(naming.get(country["id"], []))
        isles = []
        if island_tree is not None:
            hit = island_tree.query(shapely.union_all([p for _z, ps in far for p in ps]), predicate="intersects")
            isles = sorted((records[islands[k]]["name"], islands[k]) for k in hit.tolist())
        # An area with the country's own name, such as the Netherlands' region holding only its Caribbean
        # municipalities, would give the part its country's name: its counties name the land instead.
        made = share_out(far, [(records[k], named_shapes[k]) for _l, n, k in sorted(order) if n != country["name"]],
                         [(records[k], named_shapes[k]) for n, k in isles if n != country["name"]],
                         min_share, distant_km)
        changed[i] = shapely.MultiPolygon(list(kept)) if len(kept) > 1 else (kept[0] if kept else None)
        colours = [(c, changed[i] if g is shapes.get(i) else g) for c, g in colours]
        sovereign = country
        if country["id"] in whole:
            sovereign = next((r for r in records if r["id"] == whole[country["id"]]), None)
            if sovereign is None:
                raise ValueError(f"distant-parts: whole: {whole[country['id']]}, the sovereign state given for "
                                 f"{country['id']}, is not in the Countries layer.")
        counts: dict[int, int] = defaultdict(int)
        for rec, z, shape in made:
            cont = zs[z][0]
            if rec is not None:
                fid = ID_PREFIX + rec["id"]
                out = {"id": fid, "layer": LAYER, "name": rec["name"], "named_from": rec["id"]}
                for k in ("local_name", "wikidata"):
                    if rec.get(k):
                        out[k] = rec[k]
                if rec["layer"] == "regions":
                    reparent[index_of[rec["id"]]] = fid
                elif rec["layer"] == "islands":
                    log(f"{country['name']}: land in {cont['name']} in no region or county of its own, "
                        f"{continents.km2(shape):,.1f} km2, is named after its largest named island, {rec['name']}.")
            else:
                counts[z] += 1
                fid = f"{ID_PREFIX}{country['id']}:{cont['id']}" + (f":{counts[z]}" if counts[z] > 1 else "")
                out = {"id": fid, "layer": LAYER, "name": f"{country['name']} in {cont['name']}"}
                log(f"{country['name']}: land in {cont['name']} in no region or county of its own, "
                    f"{continents.km2(shape):,.1f} km2, is named {out['name']}.")
            out.update(type=TYPE, sovereign=sovereign.get("sovereign") or sovereign["name"],
                       sovereign_id=sovereign["id"])
            for k in ("source", "source_key"):
                if country.get(k):
                    out[k] = country[k]
            out["colour"] = colour_apart(shape, colours)
            colours.append((out["colour"], shape))
            new.append((out, shape))
            line(f"Distant part: {out['name']}, {continents.km2(shape):,.0f} km2, in {cont['name']}, "
                 f"is now an area of its own, with {out['sovereign']} as its sovereign state.")
    return new, changed, reparent


def run(ctx) -> None:
    t = time.perf_counter()
    settings = continents.load_settings()
    min_share = float(ctx.settings.get("min_share", 0.5))
    whole = dict(ctx.settings.get("whole") or {})
    data = json.loads((ctx.previous / "features.json").read_text(encoding="utf-8"))
    records, offsets = data["records"], data["shapes"]
    new, changed, reparent = split_countries(records, lambda idx: read_shapes(ctx.previous, offsets, idx),
                                             settings, min_share, ctx.progress.line, ctx.progress.log, whole)
    gone = {i for i, g in changed.items() if g is None}
    changed = {i: g for i, g in changed.items() if g is not None}
    shapes_out = ctx.claim(ctx.folder / "shapes.wkb")
    shutil.copyfile(ctx.previous / "shapes.wkb", shapes_out)
    if new or changed:
        at = shapes_out.stat().st_size
        with open(shapes_out, "ab") as out:
            def put(geom) -> list[int]:
                nonlocal at
                blob = shapely.to_wkb(geom)
                out.write(blob)
                place, at = [at, len(blob)], at + len(blob)
                return place

            for i, g in sorted(changed.items()):
                offsets[i] = put(g)
            for rec, g in new:
                records.append(rec)
                offsets.append(put(g))
        for i, parent in reparent.items():
            records[i]["parent"] = parent
        update_within(ctx.folder, records, offsets, [(r["id"], g) for r, g in new])
    if gone:
        for i in sorted(gone):
            ctx.progress.line(f"{records[i]['name']} ({records[i]['id']}) is shared out whole, so it is no longer an "
                              f"area of its own (DP192).")
        records, offsets = take_away(records, offsets, gone, whole)
    text = json.dumps({"records": records, "shapes": offsets}, ensure_ascii=False, sort_keys=True, indent=0)
    ctx.claim(ctx.folder / "features.json").write_text(text, encoding="utf-8", newline="\n")
    ctx.progress.line(f"Distant parts made areas of their own: {len(new)}, from {len(changed)} countries, in "
                      f"{time.perf_counter() - t:.0f} seconds. The log lists any named after their continent.")


def take_away(records: list[dict], offsets: list, gone: set[int], whole: dict[str, str]) -> tuple[list, list]:
    """The records and shape offsets without the countries shared out whole (DP192). Anything still naming one
    as its parent, such as a region too small to be an area of its own, names its sovereign state instead; a
    place still within one is within its sovereign state."""
    to = {records[i]["id"]: whole.get(records[i]["id"]) for i in gone}
    kept_records, kept_offsets = [], []
    for i, (r, o) in enumerate(zip(records, offsets)):
        if i in gone:
            continue
        if r.get("parent") in to:
            r["parent"] = to[r["parent"]]
        if r.get("within"):
            r["within"] = [dict(w, id=to[w["id"]]) if w.get("id") in to else w for w in r["within"]]
        kept_records.append(r)
        kept_offsets.append(o)
    return kept_records, kept_offsets


def update_within(folder: Path, records: list[dict], offsets: list, made: list[tuple[str, object]]) -> None:
    """A place's areas (P3-T1j): where it is in a new area, its country is now that area."""
    which = [i for i, r in enumerate(records) if r.get("within")]
    if not which or not made:
        return
    shapes = read_shapes(folder, offsets, which)
    for fid, land in made:
        shapely.prepare(land)
        for i, g in shapes.items():
            if shapely.intersects(land, shapely.point_on_surface(g)):
                records[i]["within"] = [{"id": fid, "layer": LAYER} if w.get("layer") == LAYER else w
                                        for w in records[i]["within"]]
