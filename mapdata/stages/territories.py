"""The territories list (P3-T24c, P3-T24d, DP199): each place's legal status and whether its sovereign is said.

The list is mapdata/config/territories.yaml, which the data manager keeps; its header says what each field is.
It is used by the distant-parts stage, which already makes a country's parts on another continent areas of
their own:

* check(): every entry is checked when the stage starts. Each field is present, the status is one of STATUSES,
  and, in a build of the whole world, each identifier is found in the data. A mistake stops the build at once,
  naming the entry, rather than being heard on the map later.
* separate(): a territory OpenStreetMap maps inside its country, as a region of it, such as Puerto Rico, becomes
  an area of the Countries layer of its own, cut from its country, as a distant part is.
* apply(): each area of the Countries layer the list names gets its status, its sovereign state, and whether the
  sovereign state is said after it: say_sovereign. The core says it (P3-T24d).
"""
from __future__ import annotations

import shapely
import yaml

from mapdata.paths import CONFIG_DIR

FILE = "territories.yaml"
STATUSES = ("integral part", "autonomous part", "Crown Dependency", "overseas territory", "freely associated state",
            "disputed")
REQUIRED = ("place", "sovereign", "status", "say_sovereign")
KNOWN = set(REQUIRED) | {"wikidata", "id", "sovereign_wikidata", "separate", "claimed_by", "grey", "note", "source"}
LAYER = "countries"
ID_PREFIX = "part:"
TYPE = "territory"


class TerritoryError(ValueError):
    """A mistake in the territories list, naming the entry."""


def load(path=None) -> list[dict]:
    path = path or CONFIG_DIR / FILE
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("territories") or [])


def text(path=None) -> str:
    """The file's text, for the stage's fingerprint: a change to the list builds again."""
    return (path or CONFIG_DIR / FILE).read_text(encoding="utf-8")


def check(entries: list[dict], records: list[dict] | None = None, whole_world: bool = False) -> list[str]:
    """Check every entry; raise TerritoryError naming the first wrong one. With records and whole_world, each
    identifier must be found: a Countries area, or for separate, a region. Returns the entries not found, which
    in a build of part of the world are only listed."""
    for n, e in enumerate(entries, 1):
        name = e.get("place") or f"entry {n}"
        where = f"territories.yaml, entry {n}, {name}"
        if not isinstance(e, dict):
            raise TerritoryError(f"{where}: is not a block of fields.")
        missing = [f for f in REQUIRED if e.get(f) in (None, "")]
        if missing:
            raise TerritoryError(f"{where}: has no {', '.join(missing)}.")
        unknown = sorted(set(e) - KNOWN)
        if unknown:
            raise TerritoryError(f"{where}: has a field TobyMap does not know: {', '.join(unknown)}.")
        if not e.get("wikidata") and not e.get("id"):
            raise TerritoryError(f"{where}: needs wikidata or id, to be found in the data.")
        if e["status"] not in STATUSES:
            raise TerritoryError(f"{where}: the status {e['status']!r} is not one of: {', '.join(STATUSES)}.")
        for f in ("say_sovereign", "separate", "grey"):
            if f in e and not isinstance(e[f], bool):
                raise TerritoryError(f"{where}: {f} must be yes or no.")
    if records is None:
        return []
    missing = [e for e in entries if _find(e, records, separate=bool(e.get("separate"))) is None
               and _find(e, records) is None]
    if missing and whole_world:
        e = missing[0]
        raise TerritoryError(f"territories.yaml, {e['place']}: {e.get('wikidata') or e.get('id')} is not found in "
                             f"the data" + (", as a region to make an area of its own" if e.get("separate") else "")
                             + ".")
    return [e["place"] for e in missing]


def _find(e: dict, records: list[dict], separate: bool = False) -> int | None:
    layer = "regions" if separate else LAYER
    for i, r in enumerate(records):
        if r.get("layer") != layer:
            continue
        if (e.get("id") and r.get("id") == e["id"]) or (e.get("wikidata") and r.get("wikidata") == e["wikidata"]):
            return i
    return None


def separate(entries: list[dict], records: list[dict], shape_of, line=print) -> tuple[list, dict, dict]:
    """The territories OpenStreetMap maps as a region of their country, each made an area of the Countries layer,
    cut from its country. Returns (new records with their shapes, {country index: its shape left}, {region index:
    its new parent})."""
    from mapdata.stages.distant_parts import colour_apart

    wanted = []
    for e in entries:
        if not e.get("separate"):
            continue
        if _find(e, records) is not None:
            continue   # already an area of its own
        i = _find(e, records, separate=True)
        if i is not None and records[i].get("parent"):
            wanted.append((e, i))
    if not wanted:
        return [], {}, {}
    index_of = {r["id"]: k for k, r in enumerate(records)}
    country_ix = sorted({index_of[records[i]["parent"]] for _e, i in wanted if records[i]["parent"] in index_of})
    all_countries = [k for k, r in enumerate(records) if r.get("layer") == LAYER]
    shapes = shape_of(sorted(set(all_countries) | {i for _e, i in wanted}))
    colours = [(records[k].get("colour"), shapes.get(k)) for k in all_countries]
    new, changed, reparent = [], {}, {}
    for e, i in wanted:
        c = index_of.get(records[i]["parent"])
        if c not in country_ix:
            continue
        country = changed.get(c, shapes[c])
        land = shapely.intersection(shapes[i], country)
        if land.is_empty:
            continue
        changed[c] = shapely.difference(country, land)
        region = records[i]
        fid = ID_PREFIX + region["id"]
        out = {"id": fid, "layer": LAYER, "name": region["name"], "named_from": region["id"], "type": TYPE}
        for k in ("local_name", "wikidata", "source", "source_key"):
            if region.get(k):
                out[k] = region[k]
        out["colour"] = colour_apart(land, colours)
        colours.append((out["colour"], land))
        new.append((out, land))
        reparent[i] = fid
        line(f"Territory: {region['name']} is now an area of its own in the Countries layer, cut from "
             f"{records[c]['name']}, from the territories list (DP199).")
    return new, changed, reparent


def apply(entries: list[dict], records: list[dict], line=print) -> int:
    """Each Countries area the list names: its status, sovereign state, whether that is said, and any claimant.
    The sovereign's own area, found by its Wikidata link or its name, is its sovereign_id, so the world tree puts
    it there. Returns how many areas were given a status."""
    sovereign_ids: dict[str, str] = {}
    for r in records:
        if r.get("layer") == LAYER and r.get("type") in (None, "country", "metropolitan France"):
            if r.get("wikidata"):
                sovereign_ids.setdefault("wd:" + r["wikidata"], r["id"])
            sovereign_ids.setdefault("name:" + str(r.get("name")), r["id"])
    done = 0
    for e in entries:
        i = _find(e, records)
        if i is None:
            continue
        r = records[i]
        r["status"] = e["status"]
        r["sovereign"] = e["sovereign"]
        r["say_sovereign"] = bool(e["say_sovereign"])
        sid = sovereign_ids.get("wd:" + str(e.get("sovereign_wikidata"))) or sovereign_ids.get("name:" + e["sovereign"])
        if sid and sid != r["id"]:
            r["sovereign_id"] = sid
        if e.get("claimed_by"):
            r["claimed_by"] = e["claimed_by"]
        done += 1
    line(f"Territories list: {done} areas given their status and sovereign state, from {len(entries)} entries.")
    return done
