"""The search index, made by the writing stage (P3-T8a, SRB-1, ACC-9, architecture 7.9 and 8.2 stage 14).

Made in the writing stage, after the feature records, because it needs each feature's final identifier (after
keep_ids_unique), its point, its area, and the names of the areas it is in, from the relationships.

* Names: each feature's English name, its local name and its official name from Wikidata (DP172: English and
  the local name for now). Each made plain by mapcore.search.normalise, so "Sao Paulo" finds São Paulo. A
  feature with no name of its own, such as "Unnamed island", is not in the index.
* Importance, 0 to 1,000: from the population, how many Wikimedia sites have the feature (Wikidata's site
  links, which the wikidata stage keeps), its layer's rank, and its size. The weights are settings. A name with
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
    """A feature's importance, from 0 to 1,000 (architecture 7.9)."""
    rank = rec.get("rank", 8)
    size = rec.get("area_km2") or ((rec.get("facts") or {}).get("length_km") or {}).get("value")
    score = (weights["population"] * _log_share(population_of(rec), PEOPLE_FULL)
             + weights["sites"] * _log_share(sites, SITES_FULL)
             + weights["rank"] * max(0.0, min(1.0, (9 - rank) / 8))
             + weights["size"] * _log_share(size, SIZE_FULL))
    return int(round(1000 * score))


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


def rows(made: list[dict], relationships: dict[str, dict] | None, sites: dict[str, int],
         settings: dict | None = None) -> list[list]:
    """The search index's rows (mapcore.search.ROW), sorted."""
    s = settings_of(settings)
    skip = set(s["skip_names"])
    leave_out = set(s["leave_out"])
    rel = relationships or {}
    by_id = {r["id"]: r for r in made}
    describe = Describer(by_id, rel)
    by_key: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    for rec in made:
        if rec["layer"] in leave_out:
            continue
        for key, written in names_of(rec, skip):
            by_key[key].append((rec, written))

    out = []
    for key in sorted(by_key):
        found = by_key[key]
        # One thing found two ways: the same Wikidata item, or the same land (DP71), under the same name.
        dropped: set[str] = set()
        recs = {rec["id"]: rec for rec, _w in found}
        by_item: dict[str, dict] = {}
        for rec, _w in found:
            q = rec.get("wikidata")
            if q:
                if q in by_item:
                    worse = rec if _better(by_item[q], rec) else by_item[q]
                    dropped.add(worse["id"])
                    if worse is by_item[q]:
                        by_item[q] = rec
                else:
                    by_item[q] = rec
        ids = {rec["id"] for rec, _w in found}
        for rec, _w in found:
            # The same land (DP71), or an area named from the other, as a country's distant part is from its
            # region (DP191): Hawaii the region and Hawaii the area of the Countries layer.
            # Also an area inside another of the same name and nearly its size: the Isle of Wight the island and
            # the Isle of Wight the county.
            mine = rel.get(rec["id"], {})
            others = [*mine.get("same", ()), rec.get("named_from"),
                      *(o for o in mine.get("in", ()) if o in recs and _nearly_same_size(rec, recs[o]))]
            for other in others:
                if other and other in ids and other != rec["id"]:
                    dropped.add(rec["id"] if _better(recs[other], rec) else other)
        kept = [(rec, w) for rec, w in found if rec["id"] not in dropped]
        texts = {rec["id"]: describe.text(rec) for rec, _w in kept}
        counts: dict[str, int] = defaultdict(int)
        for t in texts.values():
            counts[t] += 1
        for rec, written in kept:
            text = texts[rec["id"]]
            if counts[text] > 1:
                text = describe.text(rec, more=True)
            english = (rec.get("names") or {}).get("en") or rec.get("name")
            point = rec.get("point") or [None, None]
            out.append([key, english, rec["id"], rec["layer"],
                        importance(rec, sites.get(rec["id"]), s["weights"]),
                        None if point[0] is None else round(point[0], 3),
                        None if point[1] is None else round(point[1], 3),
                        text, "" if written == english or search.normalise(english) == key else written])
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
    filings = [(row, search.filed_under(row[search.KEY])) for row in rows_]
    total = sum(len(p) for _r, p in filings)
    n = max(1, math.ceil(total / max(1, bucket_rows)))
    out: dict[int, list[list]] = defaultdict(list)
    for row, prefixes in filings:
        for b in sorted({search.bucket(p, n) for p in prefixes}):
            out[b].append(stored(row))
    return n, dict(out)
