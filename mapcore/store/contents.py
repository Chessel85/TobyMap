"""What is inside each area: the world tree and the contents of its areas (P3-T9, P3-T20c, DP194).

The rules are here, in the core, so the application and the writing stage use the same ones (AD-1):

* The world tree (SRB-3): under the world, the continents; under a continent, the countries that are in it, or
  across it (a tenth of it, or the one with most of it); under a country, the areas of the countries, regions and
  counties layers that have it as their parent, and its distant parts (Hawaii under the United States); under a
  constituent country, such as England, its own areas. And two lists of their own, "special:disputed" and
  "special:unclaimed" (P3-T16a). Disputed areas has one item for each dispute, by Natural Earth's name, such as
  Jammu and Kashmir, which opens to the areas in that dispute; a dispute of one area is that area (P3-T26a, DP205).
* The contents of an area (SRB-4): every feature of any layer inside it fully or partly, the same land, or
  crossing it, by the stored relationships. Browse by category lists them.

The writing stage stores both in the pack (docs/developer/pack-format.md, records tree and holds/G), so the first
opening of the world tree and a browse read a few records instead of every feature record. A pack written before
has neither, and the store works them out from the feature records, as before.

Nothing here reads a pack: each function takes the records and a way to find a feature's relationships.
"""
from __future__ import annotations

TREE_LAYERS = ("continents", "countries", "regions", "counties")   # the layers of the world tree (P3-T9a)
HOLDER_LAYERS = TREE_LAYERS   # the areas whose contents are stored (DP194)
NAME_FIELDS = ("id", "names", "local_lang")   # what the tree keeps of each item, to say its name
DISPUTE_PREFIX = "dispute:"   # an item of Disputed areas that groups the areas of one dispute (P3-T26a)


def special_kind(rec: dict) -> str | None:
    """"unclaimed" for land in no country, "disputed" for land more than one party holds or claims, else None
    (P3-T16a, ANN-6, DAT-8, LOC-6)."""
    if rec.get("type") == "unclaimed land":
        return "unclaimed"
    if rec.get("disputed") or rec.get("type") == "disputed land":
        return "disputed"
    return None


def build_tree(rows: dict[str, dict], relationships_of) -> dict[str, set]:
    """The world tree from the feature records of the tree's layers, by id, as {parent: {child ids}}, with
    "world" at the top. `relationships_of(id)` gives a feature's stored relationships."""
    tree: dict[str, set] = {}

    def add(parent: str, identifier: str) -> None:
        tree.setdefault(parent, set()).add(identifier)

    for identifier, rec in rows.items():
        layer = rec["layer"]
        if layer == "continents":
            add("world", identifier)
        elif layer != "countries":
            for parent in rec.get("parents", ()):
                if parent in rows:
                    add(parent, identifier)
                break
        else:
            _place_country(identifier, rec, rows, relationships_of, add)
    for identifier, rec in rows.items():   # the two lists of land that is not plainly one country's (P3-T16a)
        if special_kind(rec) == "unclaimed":
            add("special:unclaimed", identifier)
    for group in disputes(rows).values():   # one item for each dispute (P3-T26a)
        if len(group["members"]) == 1:
            add("special:disputed", group["members"][0])
            continue
        add("special:disputed", group["id"])
        for member in group["members"]:
            add(group["id"], member)
    return tree


def dispute_of(rec: dict, rows: dict[str, dict]) -> str:
    """The name of the dispute a disputed area is in: Natural Earth's, such as "Jammu and Kashmir", from its own
    record or the area above it; else its own English name, as for the West Bank."""
    for r in (rec, rows.get((rec.get("parents") or [None])[0]) or {}):
        name = (r.get("dispute") or {}).get("name")
        if name:
            return name
    return (rec.get("names") or {}).get("en") or rec["id"]


def disputes(rows: dict[str, dict]) -> dict[str, dict]:
    """The disputes, by their item's id, "dispute:" and the name: {"id", "name", "members": [ids, by id],
    "claimants": [ids], "view": Natural Earth's note, or None}, from the disputed areas among the rows."""
    out: dict[str, dict] = {}
    for identifier in sorted(rows):
        rec = rows[identifier]
        if special_kind(rec) != "disputed":
            continue
        name = dispute_of(rec, rows)
        g = out.setdefault(DISPUTE_PREFIX + name, {"id": DISPUTE_PREFIX + name, "name": name, "members": [],
                                                  "claimants": [], "view": None})
        g["members"].append(identifier)
        for c in rec.get("claimants") or ():
            if c not in g["claimants"]:
                g["claimants"].append(c)
        if g["view"] is None and (rec.get("dispute") or {}).get("view"):
            g["view"] = rec["dispute"]["view"]
    return out


def _place_country(identifier: str, rec: dict, rows: dict, relationships_of, add) -> None:
    """An area of the countries layer goes under its sovereign, if it is a distant part; else under the country
    that holds it, if it is a constituent country; else under each continent it is in, or that it is mostly or
    partly across (a tenth of it, or the one with most of it)."""
    sovereign = rec.get("sovereign_id")
    if sovereign and sovereign in rows and sovereign != identifier:
        add(sovereign, identifier)
        return
    rel = relationships_of(identifier)
    same = set(rel.get("same", ()))
    # Under every country that holds it: one for a constituent country, both owners for a condominium (P3-T28f).
    held = [h for h in rel.get("in", ()) if h in rows and h not in same and rows[h]["layer"] == "countries"]
    for holder in held:
        add(holder, identifier)
    if held:
        return
    continents = [i for i in rel.get("in", ()) if i in rows and rows[i]["layer"] == "continents"]
    if not continents:
        across = [(o[1], o[0]) for o in rel.get("overlaps", ()) if o[0] in rows and rows[o[0]]["layer"] == "continents"]
        continents = [c for share, c in across if share >= 0.1] or [c for _s, c in sorted(across, reverse=True)[:1]]
    for continent in continents:
        add(continent, identifier)


def share_condominiums(records: list[dict], relationships: dict[str, dict]) -> int:
    """A condominium, such as the Moselle condominium, is land its owners hold together, not a country of its own
    (P3-T28f, the PO's answer to R1). Its land is in neither owner's area, so the build finds it inside only its
    continent; here it is put inside each owner as well, in the stored relationships: the world tree lists it under
    Germany and under Luxembourg, not among Europe's countries; Up from it offers both; Down from each, and
    Contains, list it. Each owner's counts take it in. Changes `relationships` in place; returns how many."""
    by_id = {r["id"]: r for r in records}
    n = 0
    for r in records:
        if r.get("type") != "condominium":
            continue
        owners = [o for o in r.get("owners") or () if o in by_id and o != r["id"]]
        rel = relationships.setdefault(r["id"], {})
        inside = rel.get("in", [])
        new = [o for o in owners if o not in inside]
        if not new:
            continue
        rel["in"] = new + inside   # smallest first, as the build sorts them: an owner is smaller than a continent
        for o in new:
            counts = relationships.setdefault(o, {}).setdefault("counts", {})
            counts[r["layer"]] = counts.get(r["layer"], 0) + 1
            relationships[o]["counts"] = dict(sorted(counts.items()))
        n += 1
    return n


def tree_names(rows: dict[str, dict], tree: dict[str, set]) -> dict[str, dict]:
    """What the tree keeps of each of its items, to say its name: only that, as the whole records of every county
    would take much memory in the browser."""
    members = {i for ids in tree.values() for i in ids}
    out = {}
    for i in members:
        if i in rows:
            out[i] = {k: rows[i][k] for k in NAME_FIELDS if k in rows[i]}
            if rows[i].get("type") == "condominium":   # said with its owners (P3-T26c)
                out[i].update(type="condominium", sovereign=rows[i].get("sovereign"))
    for g in disputes(rows).values():   # a dispute's item, with what its label says (P3-T26a)
        if g["id"] in members:
            out[g["id"]] = {"id": g["id"], "names": {"en": g["name"]}, "claimants": g["claimants"],
                            "view": g["view"], "count": len(g["members"])}
    return out


WATER_HOLDERS = ("oceans", "seas", "lakes")   # the layers whose areas are water (P3-T29d)
WATER_HELD = {"oceans": ("oceans", "seas", "sea-places", "islands"),
              "seas": ("oceans", "seas", "sea-places", "islands"),
              "lakes": ("sea-places", "islands")}   # a bay on a lake, kept by P3-T28c


def water_may_hold(holder_layer: str, layer: str) -> bool:
    """Whether an area of `holder_layer` may list features of `layer` as its contents (P3-T29d, INF-4, DAT-4).
    Water holds only water features and islands: a sea or ocean holds seas, bays and straits (the area layer and
    the places layer) and islands; a lake holds its islands, and the bays on it, which P3-T28c keeps. Rivers, roads, railways and towns are never inside
    water, even where the sea's rough outline overlaps the coast. Any other holder is unchanged (True)."""
    allowed = WATER_HELD.get(holder_layer)
    return True if allowed is None else layer in allowed


ISLE_LAYERS = ("islands",)   # the layers whose areas are in the water round them (P3-T32g)
SHORE_SHARE = 0.5   # an island is in a water when at least this share of its outline is shore on it (P3-T32g)


def waters_round(rel: dict) -> set[str]:
    """The waters an island is in by its shore (P3-T32g, INF-4, DAT-4): those on which at least SHORE_SHARE of its
    outline is shore, by its stored "coast" on the seas and oceans and "lake_shore" on the lakes, against its
    "outline_km". An island is a hole in the sea's outline, so the stored "in" never holds the sea. Jersey, all
    round in the English Channel, is in it, and in the ocean the Channel is in, as its coast is on both; Great
    Britain, a seventh of whose coast is on the Channel, is not; nor is an island joined to the mainland for most
    of its outline, nor one in a lake on another island, whose shore is all on the lake."""
    outline = float(rel.get("outline_km") or 0.0)
    if outline <= 0.0:
        return set()
    return {w for w, km in (*rel.get("coast", ()), *rel.get("lake_shore", ())) if km >= SHORE_SHARE * outline}


def holders(rel: dict, layer: str | None = None) -> set[str]:
    """The ids of the areas a feature is inside fully or partly, is the same land as, crosses or overlaps, by its
    stored relationships: the areas whose contents it is in (SRB-4). For an island (its `layer` given), the waters
    round it too (waters_round, P3-T32g)."""
    out = set(rel.get("in", ())) | set(rel.get("same", ())) | set(rel.get("crosses", ()))
    out.update(x[0] for x in (*rel.get("partly", ()), *rel.get("overlaps", ())))
    if layer in ISLE_LAYERS:
        out |= waters_round(rel)
    return out


def wholly_in(rel: dict, holder: str, layer: str | None = None) -> bool:
    """Whether a feature is wholly inside an area, as Contains lists (P3-T29c): the stored "in", or, for an island,
    a water round it (P3-T32g)."""
    return holder in rel.get("in", ()) or (layer in ISLE_LAYERS and holder in waters_round(rel))


def partly_in(rel: dict, holder: str, layer: str | None = None) -> bool:
    """Whether a feature, by its stored relationships, is only partly inside an area: partly inside it or
    overlapping it, not inside it whole or the same land (P3-T25b, DP204): "Kazakhstan, partly in Europe"."""
    if holder in rel.get("in", ()) or holder in rel.get("same", ()):
        return False
    if layer in ISLE_LAYERS and holder in waters_round(rel):
        return False
    return any(x[0] == holder for x in (*rel.get("partly", ()), *rel.get("overlaps", ())))


def contents(records: list[dict], relationships_of, numbers: dict[str, int],
             holder_layers=HOLDER_LAYERS) -> dict[str, dict[str, tuple[list[int], list[int]]]]:
    """The contents of each area of the holder layers, as {holder id: {layer: (feature numbers, those only partly
    inside)}}, each ascending: every feature inside it fully or partly, the same land, or crossing it."""
    holding = {r["id"] for r in records if r.get("layer") in holder_layers}
    # Lists, not sets: holders() gives each area once, so a feature is added to each list at most once, and a
    # list of the same numbers takes a fraction of a set's memory on a pack of millions of features (P4-T1m).
    out: dict[str, dict[str, tuple[list, list]]] = {}
    for r in records:
        fid = r["id"]
        rel = relationships_of(fid)
        number = None
        for h in holders(rel, r["layer"]):
            if h in holding and h != fid:
                if number is None:
                    number = numbers[fid]
                every, partly = out.setdefault(h, {}).setdefault(r["layer"], ([], []))
                every.append(number)
                if partly_in(rel, h, r["layer"]):
                    partly.append(number)
    return {h: {layer: (sorted(every), sorted(partly)) for layer, (every, partly) in by_layer.items()}
            for h, by_layer in out.items()}


def to_steps(numbers: list[int]) -> list[int]:
    """Ascending feature numbers as the first and then each step from the one before, which take far fewer digits
    in the pack."""
    return [n - p for p, n in zip([0, *numbers[:-1]], numbers)]


def from_steps(steps: list[int]) -> list[int]:
    out, n = [], 0
    for s in steps:
        n += s
        out.append(n)
    return out
