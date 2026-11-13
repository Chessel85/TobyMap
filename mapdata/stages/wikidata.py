"""Stage "wikidata": facts for every feature with a Wikidata link (P3-T2a, P3-T2b, DAT-7, INF-1).

For each feature with a Wikidata link, its facts are taken from Wikidata (CC0): population with its
date, area, capital, elevation, length, the English Wikipedia article's title, the official name, and
what kind of thing it is (Wikidata's "instance of"), which names each country's tiers (DP181).

The facts are fetched from Wikidata's query service in batches, with a plain client name and nothing
about the person running the build, and kept in the data folder with the date each was fetched, in
<data>/tobymap/downloads/wikidata/facts-<refresh>.jsonl (the source "wikidata"). A rebuild reads them from there and fetches
nothing again, so the pack is the same byte for byte (DMT-1). A new "refresh" in the settings starts a
new file, fetched afresh.

Each line of the file is one item: {"id": "Q142", "fetched": "2026-11-13", "rows": [...]}, where each
row is [what, value, date, rank, label]: the statements as Wikidata gives them. Which statement is
used is chosen when the stage runs (choose_facts), so a change to the rules needs no fetching.

A feature without a Wikidata link, in a layer named in "match", is matched by its name and place: an
item with the same English name, with coordinates within "match_km" of the feature's box. Only where
exactly one item is found is it used, and each match is listed in the build's log and its report.

Settings:

* source: where the facts are kept: wikidata, a folder in the downloads folder, or sample-wikidata, the
  test pack's folder in the repository.
* refresh: a label for the facts file, such as 2026-11, which is read from the source's folder as
  facts-<refresh>.jsonl, and the names looked up as names-<refresh>.jsonl. Required. Part of the fingerprint.
* links: a feature id's Wikidata link given by hand, such as {osm:r1403916: Q142}. Wins over the
  feature's own, and over links.yaml in the source's folder, which gives the test pack's samples theirs.
* match: layers whose features without a link are matched by name and place.
* match_km: how far from the feature's box a match may be, 50 km by default.
* offline: true to fetch nothing; features whose facts are not in the file have none. The test pack
  reads its facts from the repository this way, as tests never use the network.
* batch: items to a query, 200 by default.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from mapdata.pipeline import features
from mapdata.pipeline.errors import BuildStopped

ENDPOINT = "https://query.wikidata.org/sparql"
# A plain client name and nothing about the person running the build (P3-T2a, privacy 10.4).
CLIENT = "TobyMap-mapdata/0.3 (accessible map data build; python urllib)"
BATCH = 200
PAUSE_S = 1.0          # between queries, so as not to overload the service
SOURCE = "Wikidata"

WHATS = ("population", "area", "capital", "elevation", "length", "official_name", "kind", "wikipedia", "label")

QUERY = """SELECT ?item ?what ?value ?date ?precision ?rank ?label WHERE {
  VALUES ?item { %s }
  {
    ?item p:P1082 ?st . ?st ps:P1082 ?value . ?st wikibase:rank ?rank .
    OPTIONAL { ?st pqv:P585 ?dv . ?dv wikibase:timeValue ?date ; wikibase:timePrecision ?precision }
    BIND("population" AS ?what)
  } UNION {
    ?item p:P2046 ?st . ?st psn:P2046/wikibase:quantityAmount ?value . ?st wikibase:rank ?rank .
    OPTIONAL { ?st pqv:P585 ?dv . ?dv wikibase:timeValue ?date ; wikibase:timePrecision ?precision }
    BIND("area" AS ?what)
  } UNION {
    ?item p:P2044 ?st . ?st psn:P2044/wikibase:quantityAmount ?value . ?st wikibase:rank ?rank .
    BIND("elevation" AS ?what)
  } UNION {
    ?item p:P2043 ?st . ?st psn:P2043/wikibase:quantityAmount ?value . ?st wikibase:rank ?rank .
    BIND("length" AS ?what)
  } UNION {
    ?item p:P36 ?st . ?st ps:P36 ?value . ?st wikibase:rank ?rank .
    FILTER NOT EXISTS { ?st pq:P582 ?ended }
    OPTIONAL { ?value rdfs:label ?label FILTER(LANG(?label) = "en") } BIND("capital" AS ?what)
  } UNION {
    ?item p:P31 ?st . ?st ps:P31 ?value . ?st wikibase:rank ?rank .
    FILTER NOT EXISTS { ?st pq:P582 ?ended }
    OPTIONAL { ?value rdfs:label ?label FILTER(LANG(?label) = "en") } BIND("kind" AS ?what)
  } UNION {
    ?item p:P1448 ?st . ?st ps:P1448 ?value . ?st wikibase:rank ?rank .
    FILTER NOT EXISTS { ?st pq:P582 ?ended } BIND(LANG(?value) AS ?label) BIND("official_name" AS ?what)
  } UNION {
    ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?value .
    BIND("wikipedia" AS ?what)
  } UNION {
    ?item rdfs:label ?value FILTER(LANG(?value) = "en") BIND("label" AS ?what)
  }
}"""

NAME_QUERY = """SELECT ?name ?item ?coord WHERE {
  VALUES ?name { %s }
  ?item rdfs:label ?name ; wdt:P625 ?coord .
}"""


# Talking to the query service -------------------------------------------------------------------------

def post(query: str, timeout: float = 120.0, tries: int = 6, sleep=time.sleep, say=print) -> dict:
    """One query to Wikidata's query service. Waits and tries again when the service is busy, as it asks."""
    import http.client
    import urllib.error
    import urllib.parse
    import urllib.request

    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    wait, cut = 5.0, 0
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
            "User-Agent": CLIENT, "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (ValueError, http.client.HTTPException) as e:   # cut off, or the connection dropped part-way
            # An answer cut off part-way, as the service sends when a query runs out of time. Twice is enough:
            # the batch is then asked for in halves (fetch).
            cut += 1
            if cut >= 2 or attempt == tries:
                raise CutOff(str(e)) from None
            say(f"Wikidata's query service sent an answer cut off part-way; waiting {wait:.0f} seconds, then "
                "trying again.")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries:
                raise
            after = e.headers.get("Retry-After")
            wait = max(wait, float(after)) if after and after.isdigit() else wait
            say(f"Wikidata's query service said {e.code}; waiting {wait:.0f} seconds, then trying again.")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == tries:
                raise
            say(f"Wikidata's query service could not be reached ({e}); waiting {wait:.0f} seconds, then trying again.")
        sleep(wait)
        wait = min(wait * 2, 300.0)
    raise RuntimeError("unreachable")


class CutOff(Exception):
    """The query service's answer was cut off part-way, every time it was asked."""


def _plain(binding: dict | None):
    if binding is None:
        return None
    v = binding["value"]
    if binding.get("type") == "uri" and v.startswith("http://www.wikidata.org/entity/"):
        return v.rsplit("/", 1)[1]
    if binding.get("datatype", "").endswith("#decimal") or binding.get("datatype", "").endswith("#integer") \
            or binding.get("datatype", "").endswith("#double"):
        f = float(v)
        return int(f) if f.is_integer() and abs(f) < 2 ** 53 else f
    if binding.get("datatype", "").endswith("#dateTime"):
        return v[:10] if not v.startswith("-") else v[:11]
    return v


def date_at(date: str | None, precision) -> str | None:
    """A date cut to Wikidata's precision for it: 9 is a year, "2020"; 10 a month, "2020-03"; 11 a day."""
    if not date:
        return None
    if precision is None or int(precision) >= 11:
        return date
    if date.startswith("-"):   # before the common era: kept whole, as no feature's facts are dated so
        return date
    return date[:7] if int(precision) == 10 else date[:4] if int(precision) >= 9 else None


RANKS = {"http://wikiba.se/ontology#PreferredRank": "preferred", "http://wikiba.se/ontology#NormalRank": "normal",
         "http://wikiba.se/ontology#DeprecatedRank": "deprecated"}


def rows_of(result: dict) -> dict[str, list[list]]:
    """The query's answer as rows for each item: [what, value, date, rank, label], sorted, so the same answer
    always gives the same file."""
    out: dict[str, list[list]] = {}
    for b in result["results"]["bindings"]:
        item = _plain(b["item"])
        rank = RANKS.get(b.get("rank", {}).get("value"), "normal")
        if rank == "deprecated":
            continue
        row = [b["what"]["value"], _plain(b["value"]), date_at(_plain(b.get("date")), _plain(b.get("precision"))),
               rank, _plain(b.get("label"))]
        out.setdefault(item, []).append(row)
    for rows in out.values():
        rows.sort(key=lambda r: json.dumps(r, sort_keys=True, ensure_ascii=False))
    return out


def fetch(qids: list[str], query=post, batch: int = BATCH, say=print, pause_s: float = PAUSE_S,
          sleep=time.sleep, today: str | None = None, keep=None) -> dict[str, dict]:
    """The rows of each item, fetched in batches. keep(entries) is called after each batch, so what is fetched
    is saved as it comes, and a stopped fetch carries on where it stopped."""
    import datetime as dt

    today = today or dt.date.today().isoformat()
    out: dict[str, dict] = {}
    started = time.monotonic()
    def ask(part: list[str]) -> dict:
        """The rows of a batch; a batch whose answer is cut off every time is asked again in halves, so one item
        with very many statements cannot stop the fetch."""
        try:
            return rows_of(query(QUERY % " ".join(f"wd:{q}" for q in part)))
        except CutOff:
            if len(part) == 1:
                say(f"Wikidata's answer for {part[0]} was cut off every time; it is kept with no facts.")
                return {}
            half = len(part) // 2
            say(f"Asking for {len(part)} items in two halves, as the answer was cut off every time.")
            return {**ask(part[:half]), **ask(part[half:])}

    for n in range(0, len(qids), batch):
        part = qids[n:n + batch]
        got = ask(part)
        entries = {q: {"id": q, "fetched": today, "rows": got.get(q, [])} for q in part}
        out.update(entries)
        if keep is not None:
            keep(entries)
        done = min(n + batch, len(qids))
        if done < len(qids):
            took = time.monotonic() - started
            say(f"Fetched the facts of {done:,} of {len(qids):,} Wikidata items; about "
                f"{(len(qids) - done) * took / done / 60:.0f} minutes to go.")
            sleep(pause_s)
    return out


# The facts file ---------------------------------------------------------------------------------------

def read_file(path: Path) -> dict[str, dict]:
    """The items kept. A last line not yet finished, as when a fetch is still adding to the file, or one cut off
    when a fetch was stopped, is left out, so that item is fetched again."""
    out: dict[str, dict] = {}
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    out[e["id"]] = e
    return out


def append_file(path: Path, entries: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for q in sorted(entries, key=qid_order):
            f.write(json.dumps(entries[q], ensure_ascii=False, sort_keys=True) + "\n")


def qid_order(q: str):
    return (len(q), q)


def valid_qid(q) -> bool:
    return isinstance(q, str) and len(q) > 1 and q[0] == "Q" and q[1:].isdigit()


# Choosing the facts -----------------------------------------------------------------------------------

def _best(rows: list[list]) -> list[list]:
    """The preferred statements if there are any, else all of them (Wikidata's own rule for the best)."""
    preferred = [r for r in rows if r[3] == "preferred"]
    return preferred or rows


def _latest(rows: list[list]) -> list | None:
    """The statement with the latest date, then the largest value; one with no date counts as oldest."""
    if not rows:
        return None
    return max(rows, key=lambda r: (r[2] or "", r[1] if isinstance(r[1], (int, float)) else 0))


def choose_facts(entry: dict) -> dict:
    """An item's facts, each with its source and date (INF-1): the date is the statement's own, such as a
    population's census date, or else the date fetched. Also the Wikipedia title, the English label and
    the kinds (instance of), which are not facts said in Details but are used by the build."""
    rows: dict[str, list[list]] = {}
    for r in entry.get("rows") or []:
        rows.setdefault(r[0], []).append(r)
    fetched = entry.get("fetched")
    facts: dict = {}

    def fact(value, date=None, **more):
        out = {"value": value, "source": SOURCE, "fetched": fetched, **more}
        if date:   # the statement's own date, such as a census's; else only the date fetched
            out["date"] = date
        return out

    pop = _latest(_best(rows.get("population", [])))
    if pop is not None and isinstance(pop[1], (int, float)) and pop[1] >= 0:
        facts["population"] = fact(int(pop[1]), pop[2])
    area = _latest(_best(rows.get("area", [])))
    if area is not None and isinstance(area[1], (int, float)) and area[1] > 0:
        facts["area_km2"] = fact(round(area[1] / 1e6, 3), area[2])
    elev = [r for r in _best(rows.get("elevation", [])) if isinstance(r[1], (int, float))]
    if elev:
        facts["elevation_m"] = fact(round(max(r[1] for r in elev), 1))
    length = _best([r for r in rows.get("length", []) if isinstance(r[1], (int, float)) and r[1] > 0])
    if length:
        facts["length_km"] = fact(round(max(r[1] for r in length) / 1000, 1))
    caps = _best(rows.get("capital", []))
    caps = sorted({(r[4] or r[1], r[1]) for r in caps if r[1]})
    if caps:
        facts["capital"] = fact([c[0] for c in caps], wikidata=[c[1] for c in caps])
    names = _best(rows.get("official_name", []))
    if names:
        en = sorted(r[1] for r in names if (r[4] or "").startswith("en"))
        facts["official_name"] = fact(en[0] if en else sorted(r[1] for r in names)[0])
    out = {"facts": facts}
    wiki = sorted(r[1] for r in rows.get("wikipedia", []) if r[1])
    if wiki:
        out["wikipedia"] = wiki[0]
    label = sorted(r[1] for r in rows.get("label", []) if r[1])
    if label:
        out["label"] = label[0]
    kinds = sorted({r[4] for r in _best(rows.get("kind", [])) if r[4]})
    if kinds:
        out["kinds"] = kinds
    return out


# Matching by name and place ---------------------------------------------------------------------------

def _sparql_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"@en'


def parse_point(wkt: str) -> tuple[float, float] | None:
    """Wikidata's "Point(lon lat)" as (lon, lat); None for a point on another body, such as the Moon."""
    if not wkt.startswith("Point("):
        return None
    lon, lat = wkt[6:-1].split()
    return float(lon), float(lat)


def fetch_names(names: list[str], query=post, batch: int = BATCH, say=print, pause_s: float = PAUSE_S,
                sleep=time.sleep, today: str | None = None, keep=None) -> dict[str, dict]:
    """The items with each English name and their coordinates: {name: {"name", "fetched", "items": [[q, lon,
    lat], ...]}}."""
    import datetime as dt

    today = today or dt.date.today().isoformat()
    out: dict[str, dict] = {}
    for n in range(0, len(names), batch):
        part = names[n:n + batch]
        result = query(NAME_QUERY % " ".join(_sparql_string(s) for s in part))
        got: dict[str, set] = {s: set() for s in part}
        for b in result["results"]["bindings"]:
            p = parse_point(b["coord"]["value"])
            if p is not None and b["name"]["value"] in got:
                got[b["name"]["value"]].add((_plain(b["item"]), round(p[0], 5), round(p[1], 5)))
        entries = {s: {"name": s, "fetched": today, "items": sorted([list(t) for t in got[s]])} for s in part}
        out.update(entries)
        if keep is not None:
            keep(entries)
        if n + batch < len(names):
            say(f"Looked up {n + batch:,} of {len(names):,} names in Wikidata.")
            sleep(pause_s)
    return out


def near_box(lon: float, lat: float, bbox, km: float) -> bool:
    """Whether a point is within km of a box (west, south, east, north; west > east across the 180 line)."""
    west, south, east, north = bbox
    pad_lat = km / 111.32
    if lat < south - pad_lat or lat > north + pad_lat:
        return False
    pad_lon = km / max(1e-6, 111.32 * math.cos(math.radians(min(89.0, max(abs(south), abs(north), abs(lat))))))
    if pad_lon >= 180:
        return True
    if west <= east:
        return west - pad_lon <= lon <= east + pad_lon or west - pad_lon <= lon - 360 or lon + 360 <= east + pad_lon
    return lon >= west - pad_lon or lon <= east + pad_lon


def match_by_name(records: list[dict], boxes: list, named: dict[str, dict], km: float) -> list[tuple[int, str]]:
    """(record index, Wikidata item) for each record whose name has exactly one item near it."""
    out = []
    for i, r in enumerate(records):
        entry = named.get(r["name"])
        if not entry:
            continue
        near = {q for q, lon, lat in entry["items"] if near_box(lon, lat, boxes[i], km)}
        if len(near) == 1:
            out.append((i, near.pop()))
    return out


# The stage --------------------------------------------------------------------------------------------

def facts_path(ctx) -> Path:
    """The facts file: facts-<refresh>.jsonl in the source's folder."""
    s = ctx.settings
    if not s.get("source"):
        raise BuildStopped("The wikidata stage needs a source, such as source: wikidata.")
    if not s.get("refresh"):
        raise BuildStopped("The wikidata stage needs a refresh label in its settings, such as refresh: 2026-11.")
    return Path(ctx.source(s["source"])[1]) / f"facts-{s['refresh']}.jsonl"


def links_given(ctx, folder: Path) -> dict[str, str]:
    """Links given by hand: links.yaml in the source's folder, if there is one, then the stage's own links."""
    import yaml

    out: dict[str, str] = {}
    path = folder / "links.yaml"
    if path.is_file():
        out.update({str(k): str(v) for k, v in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).items()})
    out.update({str(k): str(v) for k, v in (ctx.settings.get("links") or {}).items()})
    bad = sorted(k for k, v in out.items() if not valid_qid(v))
    if bad:
        raise BuildStopped(f"The Wikidata links given by hand for {', '.join(bad)} are not Wikidata items, which "
                           "look like Q followed by a number.")
    return out


def names_path(facts: Path) -> Path:
    return facts.with_name(facts.name.replace("facts-", "names-", 1))


def _bbox(geom):
    from mapdata.stages import antimeridian

    b = antimeridian.wrap_box(geom)
    return (b.west, b.south, b.east, b.north)


def run(ctx) -> None:
    s = ctx.settings
    records, geoms = features.load(ctx.previous)
    say, line = ctx.progress.log, ctx.progress.line
    path = facts_path(ctx)
    offline = bool(s.get("offline"))
    by_hand = links_given(ctx, path.parent)
    for r in records:
        if r["id"] in by_hand:
            r["wikidata"] = by_hand[r["id"]]
        elif r.get("wikidata") and not valid_qid(r["wikidata"]):
            say(f"{r['name']} ({r['id']}) has the Wikidata link {r['wikidata']!r}, which is not an item; left out.")
            del r["wikidata"]

    # Matching by name and place, for the layers named, where there is no link.
    layers = set(s.get("match") or [])
    unlinked = [i for i, r in enumerate(records) if r["layer"] in layers and not r.get("wikidata") and r.get("name")]
    if unlinked:
        npath = names_path(path)
        named = read_file_names(npath)
        wanted = sorted({records[i]["name"] for i in unlinked} - set(named))
        if wanted and not offline:
            line(f"Looking up {len(wanted):,} names in Wikidata, for features with no Wikidata link.")
            named.update(fetch_names(wanted, say=line, batch=int(s.get("batch", BATCH)),
                                     keep=lambda e: append_names(ctx.claim(npath), e)))
        km = float(s.get("match_km", 50))
        boxes = {i: _bbox(geoms[i]) for i in unlinked}
        sub = [records[i] for i in unlinked]
        found = match_by_name(sub, [boxes[i] for i in unlinked], named, km)
        for j, q in found:
            r = sub[j]
            r["wikidata"] = q
            r["wikidata_matched"] = True
            say(f"Matched by name and place: {r['name']} ({r['id']}, {r['layer']}) is Wikidata's {q}.")
        line(f"Matched by name and place, where exactly one Wikidata item has the name near the feature: "
             f"{len(found):,} of {len(unlinked):,} features with no link. The log lists each.")

    wanted = sorted({r["wikidata"] for r in records if r.get("wikidata")}, key=qid_order)
    held = read_file(path)
    missing = [q for q in wanted if q not in held]
    if missing and not offline:
        line(f"Fetching the facts of {len(missing):,} Wikidata items, of {len(wanted):,}; the rest were fetched "
             f"before and kept in {path}.")
        held.update(fetch(missing, say=line, batch=int(s.get("batch", BATCH)),
                          keep=lambda e: append_file(ctx.claim(path), e)))
    elif missing:
        say(f"Offline: the facts of {len(missing)} Wikidata items are not in {path.name}, so those features have none.")

    # Each capital's id becomes the pack's feature, where the pack has it, so Details can go there.
    with_facts = 0
    for r in records:
        q = r.get("wikidata")
        if not q or q not in held:
            continue
        got = choose_facts(held[q])
        if got["facts"]:
            r["facts"] = got["facts"]
            with_facts += 1
            if "population" in got["facts"]:   # Wikidata's, with its date, replaces OSM's (P3-T1j)
                r.pop("population", None)
                r.pop("population_source", None)
        if got.get("wikipedia"):
            r["wikipedia"] = got["wikipedia"]
        if got.get("kinds"):
            r["kinds"] = got["kinds"]
    line(f"Facts from Wikidata for {with_facts:,} features of {len(records):,}; {len(wanted):,} have a "
         "Wikidata link.")
    for text in coverage_lines(records, ctx.pack.layers):
        line(text)
    features.save(ctx.folder, records, geoms, ctx.claim)


def read_file_names(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    out[e["name"]] = e
    return out


def append_names(path: Path, entries: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for name in sorted(entries):
            f.write(json.dumps(entries[name], ensure_ascii=False, sort_keys=True) + "\n")


CITY_PEOPLE = 100_000   # DAT-7: cities over this many people
OWN_TYPES = ("disputed land", "unclaimed land", "condominium", "territory")


def coverage_lines(records: list[dict], layers: dict) -> list[str]:
    """For the build's report: each layer's share with a Wikidata link, with facts and with a Wikipedia
    article; and DAT-7's two measures, countries, and cities over 100,000 people."""
    out = []
    counts: dict[str, list[int]] = {}
    for r in records:
        c = counts.setdefault(r["layer"], [0, 0, 0, 0])
        c[0] += 1
        c[1] += bool(r.get("wikidata"))
        c[2] += bool(r.get("facts"))
        c[3] += bool(r.get("wikipedia"))
    for layer, (n, linked, facts, wiki) in counts.items():
        name = layers[layer].name if layer in layers else layer
        out.append(f"{name}: {n:,} features, {linked:,} with a Wikidata link, {facts:,} with facts, "
                   f"{wiki:,} with a Wikipedia article.")
    # Countries only: not the land the build names itself, such as unclaimed islets, the West Bank or Antarctica.
    countries = [r for r in records if r["layer"] == "countries" and r.get("type") not in OWN_TYPES]
    if countries:
        good = sum(1 for r in countries if "population" in (r.get("facts") or {}) and r.get("wikipedia"))
        out.append(f"DAT-7, countries with a population and a Wikipedia article: {good} of {len(countries)}, "
                   f"{100 * good / len(countries):.0f} percent; at least 95 percent is needed.")
    cities = [r for r in records if r["layer"] == "towns" and max(
        (r.get("population") or 0), ((r.get("facts") or {}).get("population") or {}).get("value") or 0) > CITY_PEOPLE]
    if cities:
        good = sum(1 for r in cities if "population" in (r.get("facts") or {}) and r.get("wikipedia"))
        out.append(f"DAT-7, cities over 100,000 people with a population and a Wikipedia article: {good} of "
                   f"{len(cities)}, {100 * good / len(cities):.0f} percent; at least 80 percent is needed.")
    return out
