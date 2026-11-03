"""Areas held twice in one layer, such as Sevastopol (P1-T16, DP104, architecture 6.12).

OSM sometimes holds two areas with the same outline in one layer, one for
each side of a dispute. Spike S2 found Sevastopol twice among Russia's
regions: Ukraine's city (ISO 3166-2 code UA-40) and Russia's federal city,
with no code. Cleaning cannot let two areas share land, so it dropped one of
them without saying so.

As the PO agreed in DP104, the build:

* lists the areas in one layer that cover the same land;
* keeps the one in the country whose outline holds it, and marks it disputed;
* keeps the other's name, identifier and country for its details (ANN-6).

Every area in a country's list was found inside that country's outline
(boundaries.divisions), so "the one in the country" is the copy that belongs
to that country. That is told from the ISO 3166-2 code: a code starting with
the country's own ISO 3166-1 code first, then no code, then a code for
another country. If that does not decide it, the lower identifier is kept
and the report says the choice could not be told from the data.
"""
from __future__ import annotations

from dataclasses import dataclass

from mapdata.stages import overlaps


@dataclass
class Held:
    kept: object            # the Area kept, now marked disputed
    dropped: object         # the other copy
    country_id: str
    decided_by: str         # plain words: how the copy kept was chosen
    shared_km2: float


def country_code(area) -> str | None:
    """The ISO 3166-1 code that an area's own ISO 3166-2 code names, such as UA for UA-40."""
    code = (area.tags or {}).get("ISO3166-2") or ""
    return code.split("-")[0].upper() if "-" in code else None


def _rank(area, own: str | None) -> int:
    code = country_code(area)
    if own and code == own:
        return 0
    if code is None:
        return 1
    return 2


def resolve(country, areas: list) -> tuple[list, list[Held]]:
    """One country's areas at one level, with each area held twice kept once.

    Returns the areas to use, in their order, and what was found. The copy
    kept has tags disputed=yes and also_held_as, the other copy's identifier,
    name and country code.
    """
    if len(areas) < 2:
        return list(areas), []
    own = (country.tags or {}).get("ISO3166-1")
    own = own.upper() if own else None
    found = overlaps.same_land([a.geom for a in areas])
    dropped: set[int] = set()
    held = []
    for o in found:
        if o.first in dropped or o.second in dropped:
            continue  # held three times: each further copy is listed against the one kept
        a, b = areas[o.first], areas[o.second]
        ra, rb = _rank(a, own), _rank(b, own)
        if ra != rb:
            keep, drop = (o.first, o.second) if ra < rb else (o.second, o.first)
            k = areas[keep]
            reason = ("its ISO 3166-2 code is the country's own" if _rank(k, own) == 0 else
                      f"it has no ISO 3166-2 code, and the other's code, {areas[drop].tags.get('ISO3166-2')}, "
                      f"is another country's")
        else:
            keep, drop = sorted((o.first, o.second), key=lambda n: _id_number(areas[n].id))
            reason = "the data does not say which belongs to the country, so the lower identifier is kept"
        dropped.add(drop)
        k, d = areas[keep], areas[drop]
        k.tags = dict(k.tags or {})
        k.tags["disputed"] = "yes"
        k.tags["also_held_as"] = {"id": d.id, "name": d.name, "name_en": (d.tags or {}).get("name:en"),
                                  "country_code": country_code(d)}
        held.append(Held(k, d, country.id, reason, o.shared_km2))
    return [a for n, a in enumerate(areas) if n not in dropped], held


def _id_number(identifier: str) -> tuple[str, int]:
    kind, _, rest = identifier.partition(":")
    digits = "".join(ch for ch in rest if ch.isdigit())
    return kind, int(digits) if digits else 0


def report_lines(held: list[Held], english, country_name) -> list[str]:
    out = []
    for h in held:
        code = country_code(h.dropped)
        other = f", with the code {h.dropped.tags.get('ISO3166-2')}" if code else ", with no ISO 3166-2 code"
        out.append(f"{country_name(h.country_id)}: {english(h.kept)} ({h.kept.id}) and {english(h.dropped)} "
                   f"({h.dropped.id}{other}) have the same outline, holding {h.shared_km2:,.0f} km2 as read, "
                   f"including any sea inside it. Kept {h.kept.id}, "
                   f"marked disputed, because {h.decided_by}. The other's name and country are kept for its details.")
    return out
