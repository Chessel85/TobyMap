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
    finally:
        pack.close()
    for r in rows:
        if not r["passed"]:
            ctx.progress.always(f"Check place failed: {r['place']}: found {', '.join(r['found']) or 'nothing'}.")
    ctx.progress.line(f"Check places: {passed} of {total} passed. {regional} of them also name a county or other "
                      "area this pack does not hold, which is left as a check for regional packs.")
    ctx.claim(ctx.folder / "checks.json").write_text(json.dumps({"passed": passed, "total": total, "places": rows},
                                                                indent=1, ensure_ascii=False),
                                                     encoding="utf-8", newline="\n")
