"""The search index, made by the writing stage (P3-T8a, SRB-1, ACC-9, architecture 7.9 and 8.2 stage 14).

Made in the writing stage, after the feature records, because it needs each feature's final identifier (after
keep_ids_unique), its point, its area, and the names of the areas it is in, from the relationships.

* Names: each feature's English name, its local name and its official name from Wikidata (DP172: English and
  the local name for now). Each made plain by mapcore.search.normalise, so "Sao Paulo" finds São Paulo. A
  feature with no name of its own, such as "Unnamed island", is not in the index.
* Importance, 0 to 1,000: from the population, how many Wikimedia sites have the feature (Wikidata's site
  links, which the wikidata stage keeps), its layer's rank, and its size (its area, length or extent). A place
  with people is weighed by its people as much as by its area and kind, and a feature without people on what it
  has (P3-T33a, importance). The weights are settings. A name with
  ä, ö or ü is filed a second time as it is often typed, with ae, oe and ue, so "muenchen" finds München.
* A description that tells it apart from others of the same name: the name, then the region and the country it
  is in, such as "Paris, Île-de-France, France"; for a country, its continent, or its sovereign state for a
  distant part such as Hawaii; for a line or an area in several countries, up to three, holding most of it
  first; for a sea, the water it is in.
  Where two features of one name still have the same description, the county is added.
* One feature found two ways is listed once: two features of the same name that are the same Wikidata item,
  such as Paris the department and Paris the city, the same land (DP71), or one named from the other, as
  Hawaii the distant part is from Hawaii the region (DP191), or one inside the other and nearly its size, such
  as the Isle of Wight the county and the island, keep only one: a country, region or county first, then the
  larger kind (the lower rank), then the larger.

The rows are spread over the search records by the prefixes of their words (mapcore.search), so a search reads
only a few records, never the whole index. Rows are sorted, so the same features give the same bytes (DMT-1).
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict

from mapcore import search

SETTINGS = {
    # Rows filed in a search record, on average. The records of common prefixes, such as "san", hold more.
    "bucket_rows": 2000,
    # Names that are not a feature's own name.
    "skip_names": ["Unnamed island", "Unnamed road", "Unnamed railway line"],
    # How much each counts towards importance; they add up to 1.
    "weights": {"population": 0.40, "sites": 0.30, "rank": 0.15, "size": 0.15},
    # Layers left out of the index.
    "leave_out": [],
}
SITES_FULL = 300           # Wikimedia sites for full marks
PEOPLE_FULL = 1e9          # people for full marks
SIZE_FULL = 1e7            # square kilometres, or kilometres for a line, for full marks
ADMIN = ("countries", "regions", "counties")
PLACE_RANK = 6             # a feature with people counts at least as a county (P3-T33a)


def settings_of(given: dict | None) -> dict:
    out = {**SETTINGS, **{k: v for k, v in (given or {}).items() if k in SETTINGS}}
    out["weights"] = {**SETTINGS["weights"], **(out.get("weights") or {})}
    return out


def _log_share(value, full: float) -> float:
    if not value or value <= 0:
        return 0.0
    return min(1.0, math.log10(1.0 + float(value)) / math.log10(1.0 + full))


def population_of(rec: dict):
    fact = (rec.get("facts") or {}).get("population")
    return fact["value"] if fact else rec.get("population")


def importance(rec: dict, sites: int | None, weights: dict) -> int:
    """A feature's importance, from 0 to 1,000 (architecture 7.9, P3-T33a).

    * Size: the area; else, for a line, its length from Wikidata; else its extent (width_km), so a long road or
      railway counts for more than a short one.
    * A feature with people is weighed as a place: its size is its people or its area, whichever counts for more,
      and its kind counts at least as a county's. A town or city is a point, with no area, and its layer's rank
      is only the order it is drawn in, so Winchester the city is weighed fairly against Winchester the county.
    * A feature without people, such as a river or a road, is weighed on what it has: the share population would
      have is shared among the others, so a river is not buried under small towns of its name."""
    pop = population_of(rec)
    rank = rec.get("rank", 8)
    length = ((rec.get("facts") or {}).get("length_km") or {}).get("value")
    size = _log_share(rec.get("area_km2") or length or rec.get("width_km"), SIZE_FULL)
    people = _log_share(pop, PEOPLE_FULL)
    if people:
        rank = min(rank, PLACE_RANK)
        size = max(size, people)
    w = dict(weights)
    if not people:
        w["population"] = 0.0
    score = (w["population"] * people
             + w["sites"] * _log_share(sites, SITES_FULL)
             + w["rank"] * max(0.0, min(1.0, (9 - rank) / 8))
             + w["size"] * size)
    return int(round(1000 * score / (sum(w.values()) or 1.0)))


def names_of(rec: dict, skip: set[str]) -> list[tuple[str, str]]:
    """(plain name, name as written) for each of a feature's names, the English first, each plain name once."""
    names = rec.get("names") or {}
    english = names.get("en") or rec.get("name")
    found = [english, names.get("local"),
             ((rec.get("facts") or {}).get("official_name") or {}).get("value")]
    out, seen = [], set()
    for n in found:
        if not n or not isinstance(n, str) or n in skip:
            continue
        for key in dict.fromkeys((search.normalise(n), search.normalise(n.translate(TWO_LETTERS)))):
            if key and key not in seen:
                seen.add(key)
                out.append((key, n))
    return out


# A name with ä, ö or ü is also filed as it is often typed without them: "muenchen" finds München.
TWO_LETTERS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


class Describer:
    """The words after a feature's name that tell it apart (architecture 7.9)."""

    def __init__(self, by_id: dict[str, dict], relationships: dict[str, dict]):
        self.by_id = by_id
        self.rel = relationships

    def _name(self, fid: str) -> str | None:
        r = self.by_id.get(fid)
        return None if r is None else (r.get("names") or {}).get("en") or r.get("name")

    def _layer(self, fid: str) -> str | None:
        r = self.by_id.get(fid)
        return None if r is None else r.get("layer")

    def _first(self, ids, layer: str) -> str | None:
        return next((i for i in ids if self._layer(i) == layer), None)

    def parts(self, rec: dict, more: bool = False) -> list[str]:
        """The names after the feature's own: [region, country], or with more, [county, region, country]."""
        rel = self.rel.get(rec["id"], {})
        inside = list(rel.get("in", ()))
        layer = rec["layer"]
        out: list[str | None] = []
        if layer == "countries":
            if rec.get("sovereign_id"):
                out.append(self._name(rec["sovereign_id"]))
            else:
                out.append(self._name(self._first(inside, "continents") or ""))
        else:
            countries = [i for i in inside if self._layer(i) == "countries"][:1]
            if not countries:
                # Partly inside several: those holding most of it first. Not the order a line crosses them in,
                # which for a river with branches, such as the Rhine, does not run from its source.
                shared = sorted((*rel.get("partly", ()), *([x[0], x[1]] for x in rel.get("overlaps", ()))),
                                key=lambda x: -x[1])
                countries = list(dict.fromkeys(x[0] for x in shared if self._layer(x[0]) == "countries"))[:3]
            if len(countries) == 1:   # a region says its country; a county its region too; the rest may add the county
                if more and layer not in ("regions", "counties"):
                    out.append(self._name(self._first(inside, "counties") or ""))
                if layer != "regions":
                    out.append(self._name(self._first(inside, "regions") or ""))
            out += [self._name(c) for c in countries]
            if not countries:   # at sea: the water it is in
                water = rel.get("water_in") or next(
                    (i for i in inside if (self.by_id.get(i) or {}).get("layer") in ("seas", "oceans")), None)
                if water:
                    out.append(self._name(water))
        own = (rec.get("names") or {}).get("en") or rec.get("name")
        kept: list[str] = []
        for n in out:
            if n and n != own and n not in kept:
                kept.append(n)
        return kept

    def text(self, rec: dict, more: bool = False) -> str:
        own = (rec.get("names") or {}).get("en") or rec.get("name")
        return ", ".join([own, *self.parts(rec, more)])


def _better(a: dict, b: dict) -> bool:
    """Whether feature a is kept before b when both are one thing found two ways: a country, region or county
    first, so Brittany the region wins over Brittany the physical region; then the larger kind (lower rank),
    then the larger, then by identifier."""
    def key(r):
        return (r.get("layer") not in ADMIN, r.get("rank", 8), -(r.get("area_km2") or 0.0), r["id"])
    return key(a) < key(b)


SAME_SIZE = 0.95   # an area inside another of the same name, and at least this share of its size, is the same


def _nearly_same_size(a: dict, b: dict) -> bool:
    x, y = a.get("area_km2") or 0.0, b.get("area_km2") or 0.0
    return x > 0 and y > 0 and min(x, y) >= SAME_SIZE * max(x, y)


class _Found:
    """What the index keeps of a feature while it is made (P4-T1m): only what the rows and the choice between two
    features of one name need, not the whole record, as England has millions."""

    __slots__ = ("id", "english", "layer", "wikidata", "order", "area", "same", "named_from", "inside",
                 "importance", "lon", "lat", "parts", "parts_more")


class _Names:
    """Describer's by_id, read through lookup(identifier) and kept short: each area's name and layer only."""

    def __init__(self, lookup):
        self.lookup = lookup
        self.seen: dict[str, dict | None] = {}

    def get(self, fid, default=None):
        if fid not in self.seen:
            r = self.lookup(fid)
            self.seen[fid] = None if r is None else {
                "name": (r.get("names") or {}).get("en") or r.get("name"), "layer": r.get("layer")}
        got = self.seen[fid]
        return default if got is None else got


def rows(made, relationships: dict[str, dict] | None, sites: dict[str, int],
         settings: dict | None = None, lookup=None) -> list[list]:
    """The search index's rows (mapcore.search.ROW), sorted. made gives the feature records, in order, once;
    lookup(identifier), if given, finds a feature's record for the descriptions, else made is a list and is read
    twice. relationships may be a spill.RelStore (P4-T1m)."""
    s = settings_of(settings)
    skip = set(s["skip_names"])
    leave_out = set(s["leave_out"])
    rel = relationships or {}
    if lookup is None:
        by_id = {r["id"]: r for r in made}
        lookup = by_id.get
    describe = Describer(_Names(lookup), rel)
    by_key: dict[str, list[tuple[_Found, str]]] = defaultdict(list)
    for rec in made:
        if rec["layer"] in leave_out:
            continue
        names = names_of(rec, skip)
        if not names:
            continue
        mine = rel.get(rec["id"]) or {}
        f = _Found()
        f.id, f.layer, f.wikidata = rec["id"], rec["layer"], rec.get("wikidata")
        f.english = (rec.get("names") or {}).get("en") or rec.get("name")
        f.area = rec.get("area_km2") or 0.0
        f.order = (rec.get("layer") not in ADMIN, rec.get("rank", 8), -f.area, rec["id"])
        f.same = tuple(mine.get("same", ()))
        f.named_from = rec.get("named_from")
        # Only an area can be nearly the size of an area it is in (_nearly_same_size), so only an area keeps "in".
        f.inside = tuple(sys.intern(o) for o in mine.get("in", ())) if f.area > 0 else ()
        f.importance = importance(rec, sites.get(rec["id"]), s["weights"])
        point = rec.get("point") or [None, None]
        f.lon = None if point[0] is None else round(point[0], 3)
        f.lat = None if point[1] is None else round(point[1], 3)
        f.parts = sys.intern(", ".join(describe.parts(rec)))
        f.parts_more = sys.intern(", ".join(describe.parts(rec, more=True)))
        for key, written in names:
            by_key[sys.intern(key)].append((f, written))

    def text(f: _Found, more: bool = False) -> str:   # Describer.text, from what was kept
        parts = f.parts_more if more else f.parts
        return f"{f.english}, {parts}" if parts else f.english

    def better(a: _Found, b: _Found) -> bool:   # _better
        return a.order < b.order

    def nearly_same_size(a: _Found, b: _Found) -> bool:   # _nearly_same_size
        x, y = a.area, b.area
        return x > 0 and y > 0 and min(x, y) >= SAME_SIZE * max(x, y)

    out = []
    for key in sorted(by_key):
        found = by_key.pop(key)
        # One thing found two ways: the same Wikidata item, or the same land (DP71), under the same name.
        dropped: set[str] = set()
        recs = {f.id: f for f, _w in found}
        by_item: dict[str, _Found] = {}
        for f, _w in found:
            q = f.wikidata
            if q:
                if q in by_item:
                    worse = f if better(by_item[q], f) else by_item[q]
                    dropped.add(worse.id)
                    if worse is by_item[q]:
                        by_item[q] = f
                else:
                    by_item[q] = f
        for f, _w in found:
            # The same land (DP71), or an area named from the other, as a country's distant part is from its
            # region (DP191): Hawaii the region and Hawaii the area of the Countries layer.
            # Also an area inside another of the same name and nearly its size: the Isle of Wight the island and
            # the Isle of Wight the county.
            others = [*f.same, f.named_from, *(o for o in f.inside if o in recs and nearly_same_size(f, recs[o]))]
            for other in others:
                if other and other in recs and other != f.id:
                    dropped.add(f.id if better(recs[other], f) else other)
        kept = [(f, w) for f, w in found if f.id not in dropped]
        texts = {f.id: text(f) for f, _w in kept}
        counts: dict[str, int] = defaultdict(int)
        for t in texts.values():
            counts[t] += 1
        for f, written in kept:
            t = texts[f.id]
            if counts[t] > 1:
                t = text(f, more=True)
            out.append([key, f.english, f.id, f.layer, f.importance, f.lon, f.lat, sys.intern(t),
                        "" if written == f.english or search.normalise(f.english) == key else written])
    out.sort(key=lambda r: (r[search.KEY], r[search.ID]))
    return out


def stored(row: list) -> list:
    """A row as the pack keeps it (docs/developer/pack-format.md, search/B), a quarter smaller: the plain name
    left out ("") when it is the English name made plain, and the description without the name it starts with.
    mapcore.packs.pack.Pack.search_rows puts them back."""
    out = list(row)
    if out[search.KEY] == search.normalise(out[search.NAME]):
        out[search.KEY] = ""
    text, name = out[search.DESCRIPTION], out[search.NAME]
    out[search.DESCRIPTION] = text[len(name) + 2:] if text.startswith(name + ", ") else ("" if text == name else text)
    return out


def buckets(rows_: list[list], bucket_rows: int = SETTINGS["bucket_rows"]) -> tuple[int, dict[int, list[list]]]:
    """(how many search records, {record number: its rows as stored}), each row filed under each of its
    prefixes once."""
    total = sum(len(search.filed_under(row[search.KEY])) for row in rows_)
    n = max(1, math.ceil(total / max(1, bucket_rows)))
    out: dict[int, list[list]] = defaultdict(list)
    for row in rows_:
        prefixes = search.filed_under(row[search.KEY])
        kept = stored(row)   # one list, filed in each of its records: the same bytes, a fraction of the memory
        for b in sorted({search.bucket(p, n) for p in prefixes}):
            out[b].append(kept)
    return n, dict(out)
