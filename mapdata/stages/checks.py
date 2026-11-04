"""Stage "checks": look up the check places in the pack just written (P1-T4, DAT-3, DAT-14, LOC-6).

Each place in the places files named in the settings (tests/acceptance) is
looked up in the pack, as "where am I" will. A place passes when every name
it expects is among the areas found, and a place marked "sea" passes when
only seas and oceans are found.

A place may expect a name the pack does not hold at all, such as a county in
the base pack lite, which has none: that name is a check for regional packs,
and is listed as such. The place still passes or fails on the names the pack
does hold.

With a box in the settings, only the places inside it are looked up.

Three more checks are made when the settings ask for them (DAT-14, DAT-3):

* area_checks: each country named is compared with Wikidata's figures for its
  area. Each has name, wikidata_km2 (a list: the figures Wikidata gives, the
  preferred one first) and tolerance_pct. It passes when the pack's area is
  within the tolerance of any of the figures, and the report says which one
  it is nearest to, so the definition Wikidata uses for each is seen.
* line_180: along 179.999 east and 179.999 west, every quarter of a degree of
  latitude is in a country or a sea, and where both sides are land, the same
  area is on both sides; differences are listed. Also, no edge of any shape
  in the tiles beside the line jumps more than 180 degrees of longitude,
  which would be drawn across the globe. Edges along the line itself, such as
  Alaska's straight border, are not flagged.

The stage keeps no pack of its own: the build takes the pack from the write
stage before it.
"""
from __future__ import annotations

import json
import time

import yaml

from mapdata.pipeline.build import pack_file_name
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import REPO

WATER_LAYERS = ("oceans",)


def run(ctx) -> None:
    from mapdata.stages.lookup import Lookup, open_pack

    path = ctx.previous / pack_file_name(ctx.pack.name)
    if not path.is_file():
        raise BuildStopped("The checks stage must come straight after the write stage.")
    box = ctx.settings.get("box")
    pack = open_pack(path)
    names = set()
    for n in range(pack.manifest["features"]["count"]):
        f = pack.feature(n)
        names.update(v for v in (f.get("name"), f.get("local_name"), *(f.get("names") or {}).values()) if v)
    look = Lookup(pack)
    rows, passed, total, regional = [], 0, 0, 0
    try:
        for file in ctx.settings.get("places") or []:
            places = yaml.safe_load((REPO / file).read_text(encoding="utf-8"))["places"]
            for p in places:
                if box and not (box[0] <= p["lon"] <= box[2] and box[1] <= p["lat"] <= box[3]):
                    continue
                t = time.perf_counter()
                found = look.at(p["lon"], p["lat"])
                ms = (time.perf_counter() - t) * 1000
                heard = [f["name"] for f in found]
                known = set(heard) | {f.get("local_name") for f in found}
                missing_from_pack = []
                if p.get("sea"):
                    ok = bool(found) and all(f["layer"] in WATER_LAYERS for f in found)
                    expect = "a sea"
                else:
                    wanted = [n for n in p["includes"] if n in names]
                    missing_from_pack = [n for n in p["includes"] if n not in names]
                    ok = bool(wanted) and all(n in known for n in wanted)
                    expect = ", ".join(wanted) or "nothing this pack holds"
                total += 1
                passed += ok
                line = (f"{'PASS' if ok else 'FAIL'} {p['name']}: found {', '.join(heard) or 'nothing'}. "
                        f"Expected {expect}.")
                if missing_from_pack:
                    regional += 1
                    line += (f" For regional packs: {', '.join(missing_from_pack)}, as this pack has no layer "
                             "holding them.")
                ctx.progress.log(line + f" ({ms:.0f} ms)")
                rows.append({"place": p["name"], "passed": bool(ok), "found": heard, "file": file,
                             "regional": missing_from_pack})
        extra = []
        if ctx.settings.get("area_checks"):
            extra += area_checks(ctx, pack)
        if ctx.settings.get("line_180"):
            extra += line_180(ctx, pack, look)
    finally:
        pack.close()
    for r in rows:
        if not r["passed"]:
            ctx.progress.always(f"Check place failed: {r['place']}: found {', '.join(r['found']) or 'nothing'}.")
    ctx.progress.line(f"Check places: {passed} of {total} passed. {regional} of them also name a county or other "
                      "area this pack does not hold, which is left as a check for regional packs.")
    failed = [e for e in extra if not e["passed"]]
    for e in extra:
        ctx.progress.line(f"{'PASS' if e['passed'] else 'FAIL'} {e['check']}: {e['text']}")
    ctx.progress.line(f"Other checks: {len(extra) - len(failed)} of {len(extra)} passed.")
    ctx.claim(ctx.folder / "checks.json").write_text(json.dumps({"passed": passed, "total": total, "places": rows,
                                                                 "other": extra},
                                                                indent=1, ensure_ascii=False),
                                                     encoding="utf-8", newline="\n")


def area_checks(ctx, pack) -> list[dict]:
    """Each named country's area against Wikidata's figures (DAT-14)."""
    wanted = {c["name"]: c for c in ctx.settings["area_checks"]}
    found: dict[str, float] = {}
    for n in range(pack.manifest["features"]["count"]):
        f = pack.feature(n)
        if f.get("layer") == "countries" and f.get("name") in wanted:
            found[f["name"]] = found.get(f["name"], 0.0) + float(f.get("area_km2") or 0)
    out = []
    for name, c in wanted.items():
        if name not in found:
            out.append({"check": f"Area of {name}", "passed": False, "text": "the pack has no such country."})
            continue
        figures = list(c["wikidata_km2"])
        nearest = min(figures, key=lambda v: abs(found[name] - v))
        diff = (found[name] - nearest) / nearest * 100
        ok = abs(diff) <= float(c.get("tolerance_pct", 5))
        out.append({"check": f"Area of {name}", "passed": ok,
                    "text": f"{found[name]:,.0f} km2 in the pack; nearest Wikidata figure {nearest:,.0f} km2 "
                            f"({diff:+.1f}%); Wikidata gives {', '.join(f'{v:,.0f}' for v in figures)}. "
                            + (c.get("note") or "")})
    return out


def line_180(ctx, pack, look) -> list[dict]:
    """Both sides of the 180 degree line are named and agree, and no edge jumps across the globe (DAT-14)."""
    import numpy as np

    from mapcore.packs import coords, tiles

    empty, differ = [], []
    for lat in np.arange(-89.75, 90, 0.25):
        east = look.at(179.999, float(lat))
        west = look.at(-179.999, float(lat))
        if not east or not west:
            empty.append(float(lat))
            continue
        e = {(f["layer"], f["name"]) for f in east}
        w = {(f["layer"], f["name"]) for f in west}
        if e != w:
            differ.append((float(lat), sorted(x[1] for x in e - w), sorted(x[1] for x in w - e)))
    out = [{"check": "Both sides of the 180 degree line named", "passed": not empty,
            "text": "every quarter of a degree of latitude is in a country or a sea on both sides." if not empty
            else f"{len(empty)} latitudes have nothing on one side, such as {empty[0]:.2f}."}]
    land = [d for d in differ if d[1] or d[2]]
    for lat, a, b in land[:20]:
        ctx.progress.log(f"Different areas either side of the 180 degree line at {lat:.2f}: east side only "
                         f"{', '.join(a) or 'none'}; west side only {', '.join(b) or 'none'}.")
    ctx.progress.line(f"At the 180 degree line, {len(land)} of 720 latitudes have an area on one side and not the "
                      "other (a border or a coast that meets the line). The log lists up to 20.")
    jumps = 0
    looked = 0
    for key in pack.keys():
        if not key.startswith("tile/"):
            continue
        level, x, _y = (int(v) for v in key.split("/")[1:])
        if x not in (0, 2 ** level - 1):
            continue
        for e in pack.tile(level, x, _y):
            if e.kind != tiles.COMPACT:
                continue
            geom = coords.to_shape(e.data)
            for ring in coords_rings(geom):
                dx = np.abs(np.diff(ring[:, 0]))
                jumps += int((dx > 180).sum())
                looked += len(dx)
    out.append({"check": "No edge across the globe at the 180 degree line", "passed": jumps == 0,
                "text": f"{looked:,} edges in the tiles beside the line looked at; {jumps} jump more than 180 degrees."})
    return out


def coords_rings(geom):
    import shapely

    for poly in shapely.get_parts(geom):
        yield shapely.get_coordinates(poly.exterior)
        for hole in poly.interiors:
            yield shapely.get_coordinates(hole)
