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
    for holder in rel.get("in", ()):
        if holder in rows and holder not in same and rows[holder]["layer"] == "countries":
            add(holder, identifier)
            return
    continents = [i for i in rel.get("in", ()) if i in rows and rows[i]["layer"] == "continents"]
    if not continents:
        across = [(o[1], o[0]) for o in rel.get("overlaps", ()) if o[0] in rows and rows[o[0]]["layer"] == "continents"]
        continents = [c for share, c in across if share >= 0.1] or [c for _s, c in sorted(across, reverse=True)[:1]]
    for continent in continents:
        add(continent, identifier)


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


def holders(rel: dict) -> set[str]:
    """The ids of the areas a feature is inside fully or partly, is the same land as, crosses or overlaps, by its
    stored relationships: the areas whose contents it is in (SRB-4)."""
    out = set(rel.get("in", ())) | set(rel.get("same", ())) | set(rel.get("crosses", ()))
    out.update(x[0] for x in (*rel.get("partly", ()), *rel.get("overlaps", ())))
    return out


def partly_in(rel: dict, holder: str) -> bool:
    """Whether a feature, by its stored relationships, is only partly inside an area: partly inside it or
    overlapping it, not inside it whole or the same land (P3-T25b, DP204): "Kazakhstan, partly in Europe"."""
    if holder in rel.get("in", ()) or holder in rel.get("same", ()):
        return False
    return any(x[0] == holder for x in (*rel.get("partly", ()), *rel.get("overlaps", ())))


def contents(records: list[dict], relationships_of, numbers: dict[str, int],
             holder_layers=HOLDER_LAYERS) -> dict[str, dict[str, tuple[list[int], list[int]]]]:
    """The contents of each area of the holder layers, as {holder id: {layer: (feature numbers, those only partly
    inside)}}, each ascending: every feature inside it fully or partly, the same land, or crossing it."""
    holding = {r["id"] for r in records if r.get("layer") in holder_layers}
    out: dict[str, dict[str, tuple[set, set]]] = {}
    for r in records:
        fid = r["id"]
        rel = relationships_of(fid)
        for h in holders(rel):
            if h in holding and h != fid:
                every, partly = out.setdefault(h, {}).setdefault(r["layer"], (set(), set()))
                every.add(numbers[fid])
                if partly_in(rel, h):
                    partly.add(numbers[fid])
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
